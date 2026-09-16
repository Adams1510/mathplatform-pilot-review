from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.db import DatabaseError
from django.test import Client, override_settings

from core.checks import operational_security_checks

pytestmark = pytest.mark.django_db


def test_liveness_is_minimal_and_never_cached(client):
    response = client.get("/health/live/")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert "no-cache" in response.headers["Cache-Control"]


def test_database_readiness_succeeds(client):
    response = client.get("/health/ready/")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_database_readiness_fails_without_leaking_exception(client):
    with patch("core.views.connection.cursor", side_effect=DatabaseError("secret-dsn")):
        response = client.get("/health/ready/")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert b"secret-dsn" not in response.content


def test_readiness_form_sets_csrf_cookie(client):
    response = client.get("/_readiness/")

    assert response.status_code == 200
    assert b"csrfmiddlewaretoken" in response.content
    assert "csrftoken" in response.cookies


def test_readiness_form_rejects_missing_csrf_token():
    client = Client(enforce_csrf_checks=True)

    response = client.post("/_readiness/", {"acknowledgement": "on"})

    assert response.status_code == 403


def test_readiness_form_reports_invalid_submission(client):
    response = client.post("/_readiness/", {})

    assert response.status_code == 200
    assert b'role="alert"' in response.content
    assert b"Confirm the acknowledgement" in response.content


def test_readiness_form_uses_database_session_and_post_redirect_get():
    client = Client(enforce_csrf_checks=True)
    client.get("/_readiness/")
    token = client.cookies["csrftoken"].value

    response = client.post(
        "/_readiness/",
        {"acknowledgement": "on", "csrfmiddlewaretoken": token},
        follow=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/_readiness/"
    session = SessionStore(session_key=client.cookies["sessionid"].value)
    assert session.load()["readiness_proof_confirmed"] is True

    confirmation = client.get("/_readiness/")
    assert b"synthetic session write was confirmed" in confirmation.content


def test_security_headers_are_applied(client):
    response = client.get("/health/live/")

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_unapproved_content_routes_remain_out_of_scope(client):
    for path in ("/api/", "/admin/", "/learn/m1/integers/questions/1/"):
        assert client.get(path).status_code == 404


def test_deployment_checks_reject_non_postgres_database():
    database = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
    with override_settings(DEBUG=False, READINESS_PROOF_ENABLED=False):
        with patch.object(settings, "DATABASES", database):
            errors = operational_security_checks(None)

    assert "core.E001" in {error.id for error in errors}


def test_deployment_checks_reject_readiness_proof():
    database = {"default": {"ENGINE": "django.db.backends.postgresql"}}
    with override_settings(DEBUG=False, READINESS_PROOF_ENABLED=True):
        with patch.object(settings, "DATABASES", database):
            errors = operational_security_checks(None)

    assert "core.E002" in {error.id for error in errors}
