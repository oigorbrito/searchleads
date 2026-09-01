from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from scripts.chassis_bakeoff_report import EVIDENCE_CLASSES, canonical_json


SCHEMA_VERSION = "searchleads_empirical_observation_v1"
ENV_OUTPUT_DIR = "SEARCHLEADS_EMPIRICAL_OBSERVATION_DIR"


def build_observation(
    *,
    observation_id: str,
    research_question: str,
    method: str,
    evidence_class: str,
    payload: dict[str, Any],
    validity_limits: list[str],
) -> dict[str, Any]:
    if not observation_id or any(character in observation_id for character in "/\\"):
        raise ValueError("observation_id must be a non-empty filename-safe identifier")
    if evidence_class not in EVIDENCE_CLASSES:
        raise ValueError(f"unsupported evidence_class: {evidence_class}")
    if not research_question.strip():
        raise ValueError("research_question must be non-empty")
    if not method.strip():
        raise ValueError("method must be non-empty")
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if not isinstance(validity_limits, list):
        raise ValueError("validity_limits must be a list")
    return {
        "schema_version": SCHEMA_VERSION,
        "observation_id": observation_id,
        "research_question": research_question,
        "method": method,
        "evidence_class": evidence_class,
        "payload": payload,
        "validity_limits": validity_limits,
    }


def write_observation(
    *,
    observation_id: str,
    research_question: str,
    method: str,
    evidence_class: str,
    payload: dict[str, Any],
    validity_limits: list[str],
) -> Path | None:
    output_dir = os.environ.get(ENV_OUTPUT_DIR)
    if not output_dir:
        return None

    observation = build_observation(
        observation_id=observation_id,
        research_question=research_question,
        method=method,
        evidence_class=evidence_class,
        payload=payload,
        validity_limits=validity_limits,
    )
    path = Path(output_dir) / f"{observation_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = canonical_json(observation) + "\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != rendered:
            raise ValueError(f"observation_id collision with different content: {observation_id}")
        return path
    path.write_text(rendered, encoding="utf-8")
    return path
