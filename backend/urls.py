"""Match an incoming path to the Python function that handles it."""

from django.urls import path

from captures.views import CaptureSessionListCreateView

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("health/database/", views.database_health, name="database_health"),
    path("api/capture-sessions/", CaptureSessionListCreateView.as_view(), name="capture_sessions"),
]
