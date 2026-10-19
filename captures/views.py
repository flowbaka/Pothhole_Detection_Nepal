from rest_framework.generics import ListCreateAPIView

from .models import CaptureSession
from .serializers import CaptureSessionSerializer


class CaptureSessionListCreateView(ListCreateAPIView):
    serializer_class = CaptureSessionSerializer

    def get_queryset(self):
        return CaptureSession.objects.filter(owner=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
