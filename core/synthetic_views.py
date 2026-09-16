"""Production-disabled synthetic state fixture for Increment 2 verification."""

import json
import uuid
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .forms import SyntheticStateForm
from .models import ActivityAttempt, SyntheticResponse, SyntheticSession
from .state_service import (
    AttemptLockedError,
    ContentVersionConflictError,
    RevisionConflictError,
    save_synthetic_response,
)

ACTIVITY_KEY = "synthetic-state-proof"
CONTENT_VERSION = "synthetic-v1"
SESSION_KEY = "synthetic_state_session_id"
DRAFT_SCOPE_KEY = "synthetic_state_draft_scope"


@require_GET
@never_cache
def synthetic_math_accessibility(request):
    """Render unrelated synthetic mathematics; never a diagnostic educational object."""
    return render(request, "core/synthetic_math_probe.html")


def _get_or_create_attempt(request) -> ActivityAttempt:
    synthetic_session = None
    raw_session_id = request.session.get(SESSION_KEY)
    if raw_session_id:
        synthetic_session = SyntheticSession.objects.filter(
            id=raw_session_id,
            is_synthetic=True,
            expires_at__gt=timezone.now(),
        ).first()
    if synthetic_session is None:
        request.session.cycle_key()
        synthetic_session = SyntheticSession.objects.create(
            expires_at=timezone.now()
            + timedelta(hours=settings.SYNTHETIC_STATE_MAX_AGE_HOURS)
        )
        request.session[SESSION_KEY] = str(synthetic_session.id)
        request.session[DRAFT_SCOPE_KEY] = str(uuid.uuid4())
    else:
        synthetic_session.save(update_fields=("last_seen_at",))
        request.session.setdefault(DRAFT_SCOPE_KEY, str(uuid.uuid4()))

    attempt, _ = ActivityAttempt.objects.get_or_create(
        synthetic_session=synthetic_session,
        activity_key=ACTIVITY_KEY,
        defaults={"content_version": CONTENT_VERSION},
    )
    SyntheticResponse.objects.get_or_create(attempt=attempt)
    return attempt


def _page_context(request, *, form=None, conflict=None) -> dict:
    attempt = _get_or_create_attempt(request)
    response = attempt.response
    if form is None:
        form = SyntheticStateForm(
            initial={
                "value": response.value,
                "operation_id": uuid.uuid4(),
                "base_revision": response.revision,
                "content_version": attempt.content_version,
            }
        )
    return {
        "form": form,
        "revision": response.revision,
        "saved_at": response.saved_at,
        "save_notice": request.session.pop("synthetic_save_notice", ""),
        "conflict": conflict,
        "draft_scope": request.session[DRAFT_SCOPE_KEY],
    }


@require_GET
@never_cache
def synthetic_state(request):
    return render(request, "core/synthetic_state.html", _page_context(request))


def _request_data(request):
    if request.content_type == "application/json":
        try:
            return json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
    return request.POST


@require_POST
@never_cache
def save_state(request):
    wants_json = "application/json" in request.headers.get("Accept", "")
    data = _request_data(request)
    form = SyntheticStateForm(data) if data is not None else SyntheticStateForm()
    if not form.is_valid():
        if wants_json:
            return JsonResponse({"status": "invalid_request"}, status=400)
        return render(
            request,
            "core/synthetic_state.html",
            _page_context(request, form=form),
            status=400,
        )

    attempt = _get_or_create_attempt(request)
    try:
        result = save_synthetic_response(
            attempt_id=attempt.id,
            operation_id=form.cleaned_data["operation_id"],
            base_revision=form.cleaned_data["base_revision"],
            content_version=form.cleaned_data["content_version"],
            value=form.cleaned_data["value"],
        )
    except RevisionConflictError as exc:
        payload = {
            "status": exc.code,
            "current_revision": exc.revision,
            "current_value": exc.value,
        }
        if wants_json:
            return JsonResponse(payload, status=409)
        return render(
            request,
            "core/synthetic_state.html",
            _page_context(request, form=form, conflict=payload),
            status=409,
        )
    except (AttemptLockedError, ContentVersionConflictError) as exc:
        if wants_json:
            return JsonResponse({"status": exc.code}, status=409)
        form.add_error(None, "This synthetic state cannot be saved. Reload before retrying.")
        return render(
            request,
            "core/synthetic_state.html",
            _page_context(request, form=form),
            status=409,
        )

    if wants_json:
        return JsonResponse(
            {
                "status": "saved",
                "revision": result.revision,
                "saved_at": result.saved_at.isoformat(),
                "replayed": result.replayed,
            }
        )
    request.session["synthetic_save_notice"] = "Saved online after database confirmation."
    return redirect("synthetic:state")
