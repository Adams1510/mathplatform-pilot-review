"""Strict loader for the metadata-only Increment 1 content manifest spine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings


@dataclass(frozen=True)
class ManifestError(Exception):
    code: str

    def __str__(self) -> str:
        return self.code


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"invalid_{field}")
    return value


def validate_topic_manifest(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ManifestError("invalid_document")
    if data.get("schema_version") != "1.0":
        raise ManifestError("unsupported_schema")
    _require_string(data.get("release_id"), "release_id")
    if data.get("educational_bodies_included") is not False:
        raise ManifestError("educational_body_boundary")

    topic = data.get("topic")
    if topic is None:
        return data
    if not isinstance(topic, dict):
        raise ManifestError("invalid_topic")

    for field in ("slug", "grade_label", "title", "orientation"):
        _require_string(topic.get(field), field)

    outcomes = topic.get("outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != 4:
        raise ManifestError("invalid_outcomes")
    for outcome in outcomes:
        _require_string(outcome, "outcome")

    activities = topic.get("activities")
    if not isinstance(activities, list) or not activities:
        raise ManifestError("invalid_activities")
    positions: list[int] = []
    resource_ids: set[str] = set()
    for activity in activities:
        if not isinstance(activity, dict):
            raise ManifestError("invalid_activity")
        resource_id = _require_string(activity.get("resource_id"), "resource_id")
        if resource_id in resource_ids:
            raise ManifestError("duplicate_resource")
        resource_ids.add(resource_id)
        if activity.get("rendering_authorized") is not False:
            raise ManifestError("rendering_boundary")
        if activity.get("published_version") != "v1.0":
            raise ManifestError("unapproved_version")
        position = activity.get("sequence_position")
        if not isinstance(position, int) or position < 1:
            raise ManifestError("invalid_sequence")
        positions.append(position)
    if positions != list(range(1, len(positions) + 1)):
        raise ManifestError("invalid_sequence")
    return data


def load_topic_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = Path(path or settings.TOPIC_MANIFEST_PATH)
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError("not_found") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError("unreadable") from exc
    return validate_topic_manifest(data)
