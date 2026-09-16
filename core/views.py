"""Operational endpoints and the bounded Increment 1 topic shell."""

import logging

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ReadinessProofForm
from .topic_manifest import ManifestError, load_topic_manifest

logger = logging.getLogger(__name__)


@require_GET
def home(request):
    return render(request, "core/home.html")


@require_GET
def topics(request):
    return render(request, "core/topics.html")


@require_GET
def accessibility_help(request):
    return render(request, "core/accessibility_help.html")


def get_topic_entry_context() -> dict:
    """Return a truthful entry state without importing educational body content."""
    try:
        manifest = load_topic_manifest()
    except ManifestError as exc:
        logger.warning(
            "Topic metadata is unavailable",
            extra={"manifest_error": exc.code},
        )
        return {"entry_state": "unavailable", "topic": None}

    topic = manifest.get("topic")
    if topic is None:
        return {"entry_state": "empty", "topic": None}
    return {"entry_state": "ready", "topic": topic}


def get_reliable_resume_activity(request) -> dict | None:
    """Increment 2 will supply durable evidence; a page visit is never sufficient."""
    return None


@require_GET
def integer_topic_entry(request):
    context = get_topic_entry_context()
    context["resume_activity"] = get_reliable_resume_activity(request)
    return render(request, "core/integer_topic_entry.html", context)


@require_GET
@never_cache
def controlled_activity(request, activity: str):
    labels = {
        "check": "Check where to start",
        "lesson-1": "Lesson 1",
    }
    return render(
        request,
        "core/controlled_activity.html",
        {"activity_label": labels[activity]},
        status=503,
    )


@require_GET
@never_cache
def liveness(request):
    return JsonResponse({"status": "alive"})


@require_GET
@never_cache
def readiness(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError as exc:
        logger.warning(
            "Database readiness probe failed",
            extra={"exception_type": type(exc).__name__},
        )
        return JsonResponse({"status": "not_ready"}, status=503)
    return JsonResponse({"status": "ready"})


@never_cache
@require_http_methods(["GET", "POST"])
def readiness_proof(request):
    confirmed = bool(request.session.pop("readiness_proof_confirmed", False))
    if request.method == "POST":
        form = ReadinessProofForm(request.POST)
        if form.is_valid():
            request.session["readiness_proof_confirmed"] = True
            return redirect("readiness-proof")
    else:
        form = ReadinessProofForm()
    return render(
        request,
        "core/readiness_proof.html",
        {"form": form, "confirmed": confirmed},
    )
