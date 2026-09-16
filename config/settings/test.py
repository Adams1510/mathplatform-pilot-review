"""Fast isolated tests. PostgreSQL contract tests use test_postgres.py."""

from .base import *  # noqa: F403

SECRET_KEY = "increment-zero-test-key"
DEBUG = False
ALLOWED_HOSTS = ["testserver"]
READINESS_PROOF_ENABLED = True
SYNTHETIC_ACTIVITY_ENABLED = True
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
