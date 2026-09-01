from __future__ import annotations

import argparse
import hashlib
import json
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
    payload: Any


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _load_json(path: Path) -> ArtifactRecord:
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
    return claim


def _load_claims(paths: Iterable[Path]) -> list[ArtifactRecord]:
    records: list[ArtifactRecord] = []
    seen: set[str] = set()
    for path in paths:
        record = _load_json(path)
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
    report = {
        "schema_version": "searchleads_empirical_study_report_v1",
        "study_id": study_id,
        "environment_manifest": manifest.payload,
        "artifacts": artifact_index,
        "junit_artifacts": [record.path for record in sorted(junit, key=lambda item: item.path)],
        "observation_artifacts": [
            record.path for record in sorted(observations, key=lambda item: item.path)
        ],
        "claims": sorted(claim_payloads, key=lambda item: str(item["claim_id"])),
    }
    report["report_sha256"] = _sha256_bytes(_canonical_json(report).encode("utf-8"))
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
    manifest = _load_json(args.manifest)
    report = build_report(
        study_id=args.study_id,
        manifest=manifest,
        junit=[_load_json(path) for path in args.junit],
        observations=[_load_json(path) for path in args.observation],
        claims=_load_claims(args.claim),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(_canonical_json(report) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
