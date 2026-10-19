"""Match an incoming path to the Python function that handles it."""

from django.urls import path

from captures.views import CaptureSessionListCreateView, CaptureVideoUploadView, GPSBatchUploadView

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("health/database/", views.database_health, name="database_health"),
    path("api/capture-sessions/", CaptureSessionListCreateView.as_view(), name="capture_sessions"),
    path(
        "api/capture-sessions/<uuid:session_id>/video/",
        CaptureVideoUploadView.as_view(),
        name="capture_video_upload",
    ),
    path(
        "api/capture-sessions/<uuid:session_id>/gps-readings/",
        GPSBatchUploadView.as_view(),
        name="gps_batch_upload",
    ),
]
