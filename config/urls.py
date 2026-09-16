"""Operational and bounded Increment 1 routes."""

from django.conf import settings
from django.urls import include, path

from core import views

urlpatterns = [
    path("", include("core.urls")),
    path("health/live/", views.liveness, name="health-live"),
    path("health/ready/", views.readiness, name="health-ready"),
]

if settings.READINESS_PROOF_ENABLED:
    urlpatterns.append(path("_readiness/", views.readiness_proof, name="readiness-proof"))

if settings.SYNTHETIC_ACTIVITY_ENABLED:
    urlpatterns.append(path("_synthetic/", include("core.synthetic_urls")))
