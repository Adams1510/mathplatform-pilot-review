"""Transactional state protocol for the constrained synthetic Increment 2 fixture."""

from dataclasses import dataclass
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from .models import ActivityAttempt, SavedOperation, SyntheticResponse


@dataclass(frozen=True)
class SaveAcknowledgement:
    revision: int
    saved_at: object
    value: str
    replayed: bool = False


class StateProtocolError(Exception):
    code = "state_error"


class RevisionConflictError(StateProtocolError):
    code = "revision_conflict"

    def __init__(self, *, revision: int, value: str):
        self.revision = revision
        self.value = value
        super().__init__(self.code)


class AttemptLockedError(StateProtocolError):
    code = "attempt_locked"


class ContentVersionConflictError(StateProtocolError):
    code = "content_version_conflict"


@transaction.atomic
def save_synthetic_response(
    *,
    attempt_id: UUID,
    operation_id: UUID,
    base_revision: int,
    content_version: str,
    value: str,
) -> SaveAcknowledgement:
    attempt = ActivityAttempt.objects.select_for_update().get(id=attempt_id)
    previous = SavedOperation.objects.filter(
        attempt=attempt,
        operation_id=operation_id,
    ).first()
    if previous:
        return SaveAcknowledgement(
            revision=previous.acknowledged_revision,
            saved_at=previous.acknowledged_at,
            value=previous.value,
            replayed=True,
        )
    if attempt.status != ActivityAttempt.Status.ACTIVE:
        raise AttemptLockedError
    if attempt.content_version != content_version:
        raise ContentVersionConflictError

    response = SyntheticResponse.objects.select_for_update().get(attempt=attempt)
    if response.revision != base_revision:
        raise RevisionConflictError(revision=response.revision, value=response.value)

    response.value = value
    response.revision += 1
    response.saved_at = timezone.now()
    response.save(update_fields=("value", "revision", "saved_at"))
    SavedOperation.objects.create(
        attempt=attempt,
        operation_id=operation_id,
        base_revision=base_revision,
        acknowledged_revision=response.revision,
        acknowledged_at=response.saved_at,
        value=value,
    )
    return SaveAcknowledgement(
        revision=response.revision,
        saved_at=response.saved_at,
        value=response.value,
    )
