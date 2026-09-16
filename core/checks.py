"""Fail-closed operational checks for deployment configuration."""

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def operational_security_checks(app_configs, **kwargs):  # noqa: ARG001
    errors = []
    engine = settings.DATABASES["default"]["ENGINE"]
    if not settings.DEBUG and engine != "django.db.backends.postgresql":
        errors.append(Error("Non-debug environments must use PostgreSQL.", id="core.E001"))
    if not settings.DEBUG and settings.READINESS_PROOF_ENABLED:
        errors.append(
            Error(
                "The synthetic readiness proof must be disabled outside debug environments.",
                id="core.E002",
            )
        )
    if settings.PRODUCTION_ENVIRONMENT and settings.SYNTHETIC_ACTIVITY_ENABLED:
        errors.append(
            Error(
                "The synthetic activity fixture must be disabled in production.",
                id="core.E003",
            )
        )
    return errors
