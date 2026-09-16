import gzip
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.test import override_settings

from core.topic_manifest import ManifestError, load_topic_manifest, validate_topic_manifest

pytestmark = pytest.mark.django_db


def test_manifest_reconciles_metadata_only_release():
    manifest = load_topic_manifest()

    assert manifest["educational_bodies_included"] is False
    assert manifest["topic"]["slug"] == "m1-integers"
    assert [item["sequence_position"] for item in manifest["topic"]["activities"]] == list(
        range(1, 9)
    )
    assert all(item["published_version"] == "v1.0" for item in manifest["topic"]["activities"])
    assert not any(item["rendering_authorized"] for item in manifest["topic"]["activities"])


def test_manifest_rejects_rendering_authority_and_duplicate_resources():
    manifest = load_topic_manifest()
    manifest["topic"]["activities"][0]["rendering_authorized"] = True
    with pytest.raises(ManifestError, match="rendering_boundary"):
        validate_topic_manifest(manifest)

    manifest = load_topic_manifest()
    manifest["topic"]["activities"][1]["resource_id"] = manifest["topic"]["activities"][0][
        "resource_id"
    ]
    with pytest.raises(ManifestError, match="duplicate_resource"):
        validate_topic_manifest(manifest)


def test_manifest_rejects_educational_body_flag():
    manifest = load_topic_manifest()
    manifest["educational_bodies_included"] = True

    with pytest.raises(ManifestError, match="educational_body_boundary"):
        validate_topic_manifest(manifest)


def test_topic_discovery_and_entry_use_approved_copy(client):
    topics = client.get("/topics/")
    assert topics.status_code == 200
    assert b"Integers" in topics.content

    response = client.get("/learn/m1/integers/")
    assert response.status_code == 200
    assert response.context["entry_state"] == "ready"
    assert b"Learn how positive and negative whole numbers" in response.content
    assert b"Check where to start" in response.content
    assert b"Start with lesson 1" in response.content
    assert b"It is not presented as a grade" in response.content
    assert b"MLP-G07" not in response.content


def test_topic_entry_does_not_simulate_returning_progress(client):
    client.get("/")
    first = client.get("/learn/m1/integers/")
    second = client.get("/learn/m1/integers/")

    assert b"Continue " not in first.content
    assert b"Continue " not in second.content
    assert b"Not started" in second.content


def test_returning_action_requires_injected_reliable_activity(client):
    reliable_activity = {
        "label": "lesson 1",
        "route_name": "core:integer-lesson-1",
    }
    with patch("core.views.get_reliable_resume_activity", return_value=reliable_activity):
        response = client.get("/learn/m1/integers/")

    assert b"Continue lesson 1" in response.content
    assert b"last activity confirmed by the platform" in response.content
    assert b"Start with lesson 1" not in response.content


def test_controlled_targets_expose_no_activity_body(client):
    for path in ("/learn/m1/integers/check/", "/learn/m1/integers/lessons/1/"):
        response = client.get(path)
        assert response.status_code == 503
        assert b"not available in this increment" in response.content
        assert b"questions, lesson material, answers, results, or progress" in response.content


def test_loading_state_preserves_orientation_and_disabled_action(client):
    with patch(
        "core.views.get_topic_entry_context",
        return_value={"entry_state": "loading", "topic": None},
    ):
        response = client.get("/learn/m1/integers/")

    assert response.status_code == 200
    assert b'role="status"' in response.content
    assert b'aria-disabled="true"' in response.content
    assert b"Back to Topics" in response.content


def test_empty_manifest_has_no_false_start(tmp_path, client):
    manifest_path = tmp_path / "empty.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "release_id": "empty-release",
                "educational_bodies_included": False,
                "topic": None,
            }
        ),
        encoding="utf-8",
    )
    with override_settings(TOPIC_MANIFEST_PATH=manifest_path):
        response = client.get("/learn/m1/integers/")

    assert response.context["entry_state"] == "empty"
    assert b"Topic information is not available yet" in response.content
    assert b'href="/learn/m1/integers/check/"' not in response.content


def test_missing_or_invalid_manifest_fails_closed(tmp_path, client, caplog):
    with override_settings(TOPIC_MANIFEST_PATH=tmp_path / "missing.json"):
        missing = client.get("/learn/m1/integers/")

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("not-json", encoding="utf-8")
    with override_settings(TOPIC_MANIFEST_PATH=invalid_path):
        invalid = client.get("/learn/m1/integers/")

    for response in (missing, invalid):
        assert response.status_code == 200
        assert response.context["entry_state"] == "unavailable"
        assert b"cannot load this topic" in response.content
        assert b'href="/learn/m1/integers/check/"' not in response.content
    assert "missing.json" not in caplog.text
    assert "not-json" not in caplog.text


def test_first_route_asset_budget(client):
    response = client.get("/learn/m1/integers/")
    css = (settings.BASE_DIR / "core" / "static" / "core" / "app.css").read_bytes()
    javascript = (settings.BASE_DIR / "core" / "static" / "core" / "app.js").read_bytes()

    compressed_total = sum(
        len(gzip.compress(asset)) for asset in (response.content, css, javascript)
    )
    assert compressed_total <= 200 * 1024
    assert len(gzip.compress(javascript)) <= 75 * 1024


def test_schema_document_is_valid_json_and_matches_release_boundary():
    schema_path = Path(settings.BASE_DIR) / "content_manifest" / "schema-v1.0.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["properties"]["educational_bodies_included"]["const"] is False
    assert schema["properties"]["topic"]["properties"]["activities"]["items"][
        "properties"
    ]["rendering_authorized"]["const"] is False
