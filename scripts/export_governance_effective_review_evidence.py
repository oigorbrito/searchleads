from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from searchleads.governance_effective_review_audit import EffectiveReviewAuditRepository  # noqa: E402
from searchleads.governance_effective_review_evidence_bundle import (  # noqa: E402
    build_effective_review_evidence_bundle,
    effective_review_evidence_bundle_to_mapping,
    verify_effective_review_evidence_bundle,
)


def _json_object(path: Path, label: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return payload


def _export(args: argparse.Namespace) -> dict:
    with EffectiveReviewAuditRepository(args.audit_db) as audit:
        bundle = build_effective_review_evidence_bundle(
            audit_repository=audit,
            audit_entry_id=args.audit_entry_id,
        )
    result = effective_review_evidence_bundle_to_mapping(bundle)
    if args.output is not None:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _verify(args: argparse.Namespace) -> dict:
    payload = _json_object(args.bundle, "bundle")
    verify_effective_review_evidence_bundle(payload)
    return {
        "valid": True,
        "schema_version": payload["schema_version"],
        "audit_entry_id": payload["audit_entry_id"],
        "audit_id": payload["audit_id"],
        "bundle_sha256": payload["bundle_sha256"],
        "evidence_sha256": payload["evidence_sha256"],
        "send_authorized": False,
        "evidence_is_campaign_authorization": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export or offline-verify deterministic evidence for one historical effective human-review audit entry. "
            "This command never authorizes campaign dispatch or send."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export")
    export.add_argument("--audit-db", required=True, type=Path)
    export.add_argument("--audit-entry-id", required=True)
    export.add_argument("--output", type=Path)

    verify = sub.add_parser("verify")
    verify.add_argument("--bundle", required=True, type=Path)

    args = parser.parse_args(argv)
    try:
        result = _export(args) if args.command == "export" else _verify(args)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError, KeyError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
