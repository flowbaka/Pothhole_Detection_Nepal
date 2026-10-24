from pathlib import Path

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import ListCreateAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .input_checks import check_session_inputs
from .models import CaptureSession, GPSReading
from .serializers import CaptureSessionSerializer, GPSBatchSerializer


class CaptureSessionListCreateView(ListCreateAPIView):
    serializer_class = CaptureSessionSerializer

    def get_queryset(self):
        return CaptureSession.objects.filter(owner=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CaptureSessionUploadStatusView(APIView):
    def get(self, request, session_id):
        session = get_object_or_404(CaptureSession, pk=session_id, owner=request.user)
        return Response(
            {
                "session_id": str(session.pk),
                "video_uploaded": bool(session.video),
                "gps_reading_count": session.gps_readings.count(),
            }
        )


class CaptureSessionInputCheckView(APIView):
    def get(self, request, session_id):
        session = get_object_or_404(CaptureSession, pk=session_id, owner=request.user)
        return Response(check_session_inputs(session))


MAX_VIDEO_BYTES = 300 * 1024 * 1024
MAX_MULTIPART_OVERHEAD_BYTES = 1024 * 1024


class CaptureVideoUploadView(APIView):
    parser_classes = [MultiPartParser]

    def put(self, request, session_id):
        get_object_or_404(CaptureSession, pk=session_id, owner=request.user)
        raw_length = request.META.get("CONTENT_LENGTH")
        try:
            declared_size = int(raw_length) if raw_length else None
        except (TypeError, ValueError):
            return Response({"error": "Invalid request length."}, status=400)
        if declared_size is not None and declared_size < 0:
            return Response({"error": "Invalid request length."}, status=400)
        if declared_size is not None and declared_size > MAX_VIDEO_BYTES + MAX_MULTIPART_OVERHEAD_BYTES:
            return Response({"error": "Video is too large."}, status=413)

        upload = request.FILES.get("video")
        if upload is None:
            return Response({"error": "Provide a video file."}, status=400)
        if upload.size == 0 or upload.size > MAX_VIDEO_BYTES:
            return Response({"error": "Video size is invalid."}, status=413)
        if Path(upload.name).suffix.lower() != ".mp4":
            return Response({"error": "Only MP4 files are accepted."}, status=400)
        header = upload.read(12)
        upload.seek(0)
        if (
            len(header) < 12
            or header[4:8] != b"ftyp"
            or int.from_bytes(header[:4], "big") < 8
        ):
            return Response({"error": "File is not an MP4 container."}, status=400)

        with transaction.atomic():
            session = get_object_or_404(
                CaptureSession.objects.select_for_update(),
                pk=session_id,
                owner=request.user,
            )
            if session.video:
                return Response({"error": "This journey already has a video."}, status=409)
            try:
                session.video.save("video.mp4", upload, save=False)
                session.video_uploaded_at = timezone.now()
                session.save(update_fields=["video", "video_uploaded_at"])
            except Exception:
                if session.video.name:
                    session.video.storage.delete(session.video.name)
                raise

        return Response({"status": "stored"}, status=201)


class GPSBatchUploadView(APIView):
    def post(self, request, session_id):
        get_object_or_404(CaptureSession, pk=session_id, owner=request.user)
        batch = GPSBatchSerializer(data=request.data)
        batch.is_valid(raise_exception=True)

        with transaction.atomic():
            session = get_object_or_404(
                CaptureSession.objects.select_for_update(),
                pk=session_id,
                owner=request.user,
            )
            if session.gps_readings.exists():
                return Response({"error": "This journey already has GPS readings."}, status=409)
            GPSReading.objects.bulk_create(
                GPSReading(session=session, **reading)
                for reading in batch.validated_data["readings"]
            )

        return Response({"status": "stored", "count": len(batch.validated_data["readings"])}, status=201)
