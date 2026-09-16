import gzip
import json
import threading
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import DatabaseError, IntegrityError, close_old_connections, connection, transaction
from django.test import Client, override_settings
from django.utils import timezone

from core.checks import operational_security_checks
from core.models import ActivityAttempt, SavedOperation, SyntheticResponse, SyntheticSession
from core.state_service import (
    AttemptLockedError,
    ContentVersionConflictError,
    RevisionConflictError,
    save_synthetic_response,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def synthetic_attempt():
    synthetic_session = SyntheticSession.objects.create(
        expires_at=timezone.now() + timedelta(hours=1)
    )
    attempt = ActivityAttempt.objects.create(
        synthetic_session=synthetic_session,
        activity_key="synthetic-state-proof",
        content_version="synthetic-v1",
    )
    SyntheticResponse.objects.create(attempt=attempt)
    return attempt


def save(attempt, *, operation_id=None, base_revision=0, value="alpha"):
    return save_synthetic_response(
        attempt_id=attempt.id,
        operation_id=operation_id or uuid.uuid4(),
        base_revision=base_revision,
        content_version="synthetic-v1",
        value=value,
    )


def test_transactional_revision_and_idempotent_replay(synthetic_attempt):
    operation_id = uuid.uuid4()
    first = save(synthetic_attempt, operation_id=operation_id)
    replay = save(
        synthetic_attempt,
        operation_id=operation_id,
        base_revision=99,
        value="gamma",
    )

    response = SyntheticResponse.objects.get(attempt=synthetic_attempt)
    assert first.revision == 1
    assert replay.replayed is True
    assert replay.revision == 1
    assert replay.value == "alpha"
    assert response.revision == 1
    assert response.value == "alpha"
    assert SavedOperation.objects.count() == 1


def test_revision_conflict_preserves_both_values(synthetic_attempt):
    save(synthetic_attempt, value="beta")

    with pytest.raises(RevisionConflictError) as error:
        save(synthetic_attempt, base_revision=0, value="gamma")

    assert error.value.revision == 1
    assert error.value.value == "beta"
    response = SyntheticResponse.objects.get(attempt=synthetic_attempt)
    assert response.value == "beta"
    assert response.revision == 1


def test_stale_content_and_locked_attempt_fail_closed(synthetic_attempt):
    with pytest.raises(ContentVersionConflictError):
        save_synthetic_response(
            attempt_id=synthetic_attempt.id,
            operation_id=uuid.uuid4(),
            base_revision=0,
            content_version="synthetic-stale",
            value="alpha",
        )

    synthetic_attempt.status = ActivityAttempt.Status.LOCKED
    synthetic_attempt.save(update_fields=("status",))
    with pytest.raises(AttemptLockedError):
        save(synthetic_attempt)


def test_database_failure_rolls_back_response_and_operation(synthetic_attempt):
    with patch.object(SavedOperation.objects, "create", side_effect=DatabaseError("fault")):
        with pytest.raises(DatabaseError, match="fault"):
            save(synthetic_attempt)

    response = SyntheticResponse.objects.get(attempt=synthetic_attempt)
    assert response.revision == 0
    assert response.value == ""
    assert not SavedOperation.objects.exists()


def test_database_constraints_enforce_synthetic_boundary():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SyntheticSession.objects.create(
                is_synthetic=False,
                expires_at=timezone.now() + timedelta(hours=1),
            )


def test_fixture_route_has_no_free_text_or_identifier_surface(client):
    response = client.get("/_synthetic/state/")

    assert response.status_code == 200
    assert b"Development fixture only" in response.content
    assert b'type="text"' not in response.content
    assert b'name="name"' not in response.content
    assert b'name="email"' not in response.content
    assert b'name="participant"' not in response.content
    assert b"synthetic_state_session_id" not in response.content
    assert b"serviceWorker" not in response.content


def test_synthetic_route_stays_within_asset_budget(client):
    response = client.get("/_synthetic/state/")
    static_root = settings.BASE_DIR / "core" / "static" / "core"
    assets = (
        response.content,
        (static_root / "app.css").read_bytes(),
        (static_root / "app.js").read_bytes(),
        (static_root / "synthetic-state.js").read_bytes(),
    )

    assert sum(len(gzip.compress(asset)) for asset in assets) <= 200 * 1024
    assert len(gzip.compress(assets[-1])) <= 75 * 1024


def test_native_form_save_is_csrf_protected_and_confirmed(client):
    page = client.get("/_synthetic/state/")
    form = page.context["form"]

    rejected = Client(enforce_csrf_checks=True).post(
        "/_synthetic/state/save/",
        {
            "value": "alpha",
            "operation_id": uuid.uuid4(),
            "base_revision": 0,
            "content_version": "synthetic-v1",
        },
    )
    assert rejected.status_code == 403

    accepted = client.post(
        "/_synthetic/state/save/",
        {
            "value": "alpha",
            "operation_id": form.initial["operation_id"],
            "base_revision": form.initial["base_revision"],
            "content_version": form.initial["content_version"],
        },
        follow=True,
    )
    assert accepted.status_code == 200
    assert b"Saved online after database confirmation" in accepted.content
    assert SyntheticResponse.objects.get().revision == 1


def test_json_save_conflict_and_invalid_payload_are_generic(client):
    page = client.get("/_synthetic/state/")
    form = page.context["form"]
    payload = {
        "value": "beta",
        "operation_id": str(form.initial["operation_id"]),
        "base_revision": 0,
        "content_version": "synthetic-v1",
    }
    first = client.post(
        "/_synthetic/state/save/",
        json.dumps(payload),
        content_type="application/json",
        HTTP_ACCEPT="application/json",
    )
    payload["operation_id"] = str(uuid.uuid4())
    payload["value"] = "gamma"
    conflict = client.post(
        "/_synthetic/state/save/",
        json.dumps(payload),
        content_type="application/json",
        HTTP_ACCEPT="application/json",
    )
    invalid = client.post(
        "/_synthetic/state/save/",
        b"not-json",
        content_type="application/json",
        HTTP_ACCEPT="application/json",
    )

    assert first.json()["status"] == "saved"
    assert conflict.status_code == 409
    assert conflict.json() == {
        "status": "revision_conflict",
        "current_revision": 1,
        "current_value": "beta",
    }
    assert invalid.status_code == 400
    assert invalid.json() == {"status": "invalid_request"}


def test_two_browser_sessions_are_isolated():
    first = Client()
    second = Client()
    first_form = first.get("/_synthetic/state/").context["form"]
    second.get("/_synthetic/state/")

    first.post(
        "/_synthetic/state/save/",
        {
            "value": "alpha",
            "operation_id": first_form.initial["operation_id"],
            "base_revision": 0,
            "content_version": "synthetic-v1",
        },
    )

    responses = list(SyntheticResponse.objects.order_by("attempt__synthetic_session_id"))
    assert len(responses) == 2
    assert sorted(response.value for response in responses) == ["", "alpha"]


def test_expired_synthetic_state_can_be_purged(capsys):
    SyntheticSession.objects.create(expires_at=timezone.now() - timedelta(seconds=1))
    SyntheticSession.objects.create(expires_at=timezone.now() + timedelta(hours=1))

    call_command("purge_synthetic_state")

    assert SyntheticSession.objects.count() == 1
    assert "Deleted 1 expired synthetic state records" in capsys.readouterr().out


def test_production_check_rejects_enabled_fixture():
    with override_settings(
        PRODUCTION_ENVIRONMENT=True,
        SYNTHETIC_ACTIVITY_ENABLED=True,
        READINESS_PROOF_ENABLED=False,
    ):
        errors = operational_security_checks(None)

    assert "core.E003" in {error.id for error in errors}


@pytest.mark.django_db(transaction=True)
def test_postgresql_concurrent_tabs_cannot_silently_overwrite(synthetic_attempt):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL-only concurrency proof")

    barrier = threading.Barrier(2)
    outcomes = []

    def worker(value):
        close_old_connections()
        barrier.wait()
        try:
            result = save(synthetic_attempt, value=value)
            outcomes.append(("saved", result.revision))
        except RevisionConflictError as exc:
            outcomes.append(("conflict", exc.revision))
        finally:
            close_old_connections()

    threads = [threading.Thread(target=worker, args=(value,)) for value in ("alpha", "beta")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcome[0] for outcome in outcomes) == ["conflict", "saved"]
    response = SyntheticResponse.objects.get(attempt=synthetic_attempt)
    assert response.revision == 1
    assert response.value in {"alpha", "beta"}
