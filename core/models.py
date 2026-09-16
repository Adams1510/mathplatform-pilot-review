"""Synthetic-only durable state models for the Increment 2 technical fixture."""

import uuid

from django.db import models
from django.db.models import Q


class SyntheticSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_synthetic = models.BooleanField(default=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(is_synthetic=True),
                name="core_synthetic_session_only",
            )
        ]


class ActivityAttempt(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        LOCKED = "locked", "Locked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    synthetic_session = models.ForeignKey(
        SyntheticSession,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    activity_key = models.CharField(max_length=64)
    content_version = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("synthetic_session", "activity_key"),
                name="core_one_synthetic_attempt_per_activity",
            ),
            models.CheckConstraint(
                condition=Q(activity_key__startswith="synthetic-"),
                name="core_synthetic_activity_key",
            ),
            models.CheckConstraint(
                condition=Q(content_version__startswith="synthetic-"),
                name="core_synthetic_content_version",
            ),
        ]


class SyntheticResponse(models.Model):
    class Value(models.TextChoices):
        ALPHA = "alpha", "Token A"
        BETA = "beta", "Token B"
        GAMMA = "gamma", "Token C"

    attempt = models.OneToOneField(
        ActivityAttempt,
        on_delete=models.CASCADE,
        related_name="response",
    )
    item_key = models.CharField(max_length=64, default="synthetic-item-1")
    value = models.CharField(max_length=16, choices=Value.choices, blank=True)
    revision = models.PositiveIntegerField(default=0)
    saved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(item_key__startswith="synthetic-"),
                name="core_synthetic_item_key",
            ),
            models.CheckConstraint(
                condition=Q(value__in=("", "alpha", "beta", "gamma")),
                name="core_synthetic_response_value",
            ),
        ]


class SavedOperation(models.Model):
    attempt = models.ForeignKey(
        ActivityAttempt,
        on_delete=models.CASCADE,
        related_name="operations",
    )
    operation_id = models.UUIDField()
    base_revision = models.PositiveIntegerField()
    acknowledged_revision = models.PositiveIntegerField()
    acknowledged_at = models.DateTimeField()
    value = models.CharField(max_length=16, choices=SyntheticResponse.Value.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("attempt", "operation_id"),
                name="core_unique_synthetic_operation",
            )
        ]
