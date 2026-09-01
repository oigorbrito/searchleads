from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


EVIDENCE_STATES = {
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "NOT_SUPPORTED",
    "NOT_EVALUATED",
    "INSUFFICIENT_EVIDENCE",
    "REPLICATION_REQUIRED",
}

DECISION_STATES = {
    "ADOPT",
    "COMPOSE",
    "RETAIN",
    "DEFER",
    "REJECT",
    "HISTORICAL_DECISION",
}

EVIDENCE_CLASSES = {
    "STATIC_INSPECTION",
    "FUNCTIONAL_PROBE",
    "CONTROLLED_BENCHMARK",
    "INTERNAL_REPRODUCTION",
    "EXTERNAL_REPRODUCTION",
    "LIVE_OPERATIONAL_EVIDENCE",
    "HUMAN_OR_EXTERNAL_AUTHORITY",
}


@dataclass(frozen=True)
class ArtifactRecord:
    path: str
    sha256: str
    payload: Any | None = None


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_raw_artifact(path: Path) -> ArtifactRecord:
    raw = path.read_bytes()
    return ArtifactRecord(path=path.as_posix(), sha256=_sha256_bytes(raw))


def load_json_artifact(path: Path) -> ArtifactRecord:
    raw = path.read_bytes()
    return ArtifactRecord(
        path=path.as_posix(),
        sha256=_sha256_bytes(raw),
        payload=json.loads(raw.decode("utf-8")),
    )


def _validate_claim(claim: dict[str, Any]) -> dict[str, Any]:
    required = {
        "claim_id",
        "research_question",
        "method",
        "evidence_class",
        "input_artifacts",
        "observations",
        "analysis",
        "validity_limits",
        "supported_conclusion",
        "unsupported_conclusions",
        "evidence_state",
        "decision_state",
    }
    missing = sorted(required.difference(claim))
    if missing:
        raise ValueError(f"claim missing required fields: {', '.join(missing)}")
    if claim["evidence_class"] not in EVIDENCE_CLASSES:
        raise ValueError(f"unsupported evidence_class: {claim['evidence_class']}")
    if claim["evidence_state"] not in EVIDENCE_STATES:
        raise ValueError(f"unsupported evidence_state: {claim['evidence_state']}")
    if claim["decision_state"] not in DECISION_STATES:
        raise ValueError(f"unsupported decision_state: {claim['decision_state']}")
    if not isinstance(claim["input_artifacts"], list):
        raise ValueError("input_artifacts must be a list")
    return claim


def load_claims(paths: Iterable[Path]) -> list[ArtifactRecord]:
    records: list[ArtifactRecord] = []
    seen: set[str] = set()
    for path in paths:
        record = load_json_artifact(path)
        payload = record.payload
        claims = payload if isinstance(payload, list) else [payload]
        validated: list[dict[str, Any]] = []
        for raw_claim in claims:
            if not isinstance(raw_claim, dict):
                raise ValueError(f"claim file {path} must contain an object or list of objects")
            claim = _validate_claim(dict(raw_claim))
            claim_id = str(claim["claim_id"])
            if claim_id in seen:
                raise ValueError(f"duplicate claim_id: {claim_id}")
            seen.add(claim_id)
            validated.append(claim)
        records.append(ArtifactRecord(record.path, record.sha256, validated))
    return records


def _junit_summary(record: ArtifactRecord) -> dict[str, Any]:
    root = ET.parse(record.path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    tests = failures = errors = skipped = 0
    for suite in suites:
        tests += int(suite.attrib.get("tests", "0"))
        failures += int(suite.attrib.get("failures", "0"))
        errors += int(suite.attrib.get("errors", "0"))
        skipped += int(suite.attrib.get("skipped", "0"))
    return {
        "path": record.path,
        "sha256": record.sha256,
        "tests": tests,
        "passed": tests - failures - errors - skipped,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
    }


def _materialize_claim(claim: dict[str, Any], available_paths: set[str]) -> dict[str, Any]:
    materialized = dict(claim)
    referenced = [str(value) for value in claim["input_artifacts"]]
    missing = sorted(path for path in referenced if path not in available_paths)
    declared_state = str(claim["evidence_state"])
    effective_state = "INSUFFICIENT_EVIDENCE" if missing else declared_state
    materialized["declared_evidence_state"] = declared_state
    materialized["evidence_state"] = effective_state
    materialized["traceability"] = {
        "all_inputs_present": not missing,
        "missing_input_artifacts": missing,
    }
    decision_state = str(claim["decision_state"])
    materialized["decision_support"] = {
        "eligible_from_current_evidence": (
            effective_state == "SUPPORTED" and decision_state not in {"DEFER", "HISTORICAL_DECISION"}
        ),
        "reason": (
            "SUPPORTED_EVIDENCE_AND_COMPLETE_INPUTS"
            if effective_state == "SUPPORTED" and not missing
            else "DECISION_NOT_AUTHORIZED_BY_CURRENT_EVIDENCE"
        ),
    }
    return materialized


def build_report(
    *,
    study_id: str,
    manifest: ArtifactRecord,
    junit: list[ArtifactRecord],
    observations: list[ArtifactRecord],
    claims: list[ArtifactRecord],
) -> dict[str, Any]:
    claim_payloads = [claim for record in claims for claim in record.payload]
    source_artifacts = [manifest, *junit, *observations, *claims]
    artifact_index = [
        {"path": artifact.path, "sha256": artifact.sha256}
        for artifact in sorted(source_artifacts, key=lambda item: item.path)
    ]
    available_paths = {item["path"] for item in artifact_index}
    materialized_claims = [
        _materialize_claim(claim, available_paths) for claim in claim_payloads
    ]
    report = {
        "schema_version": "searchleads_empirical_study_report_v1",
        "study_id": study_id,
        "environment_manifest": manifest.payload,
        "artifacts": artifact_index,
        "junit_summaries": [
            _junit_summary(record) for record in sorted(junit, key=lambda item: item.path)
        ],
        "observations": [
            {
                "path": record.path,
                "sha256": record.sha256,
                "payload": record.payload,
            }
            for record in sorted(observations, key=lambda item: item.path)
        ],
        "claims": sorted(materialized_claims, key=lambda item: str(item["claim_id"])),
    }
    report["report_sha256"] = _sha256_bytes(canonical_json(report).encode("utf-8"))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a deterministic canonical report from preserved chassis bake-off artifacts."
    )
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--junit", nargs="*", default=[], type=Path)
    parser.add_argument("--observation", nargs="*", default=[], type=Path)
    parser.add_argument("--claim", nargs="*", default=[], type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_json_artifact(args.manifest)
    report = build_report(
        study_id=args.study_id,
        manifest=manifest,
        junit=[load_raw_artifact(path) for path in args.junit],
        observations=[load_json_artifact(path) for path in args.observation],
        claims=load_claims(args.claim),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(report) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
