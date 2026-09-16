"""Package-only loopback synthetic review profile. Never deploy."""
from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
SECRET_KEY = "review-only-placeholder-not-a-production-secret"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "review.sqlite3",
    }
}
READINESS_PROOF_ENABLED = True
SYNTHETIC_ACTIVITY_ENABLED = True
PRODUCTION_ENVIRONMENT = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
