from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from searchleads.governance_effective_review_verification_audit import EffectiveReviewVerificationAuditRepository  # noqa: E402
from searchleads.governance_effective_review_verification_audit_evidence_bundle import (  # noqa: E402
    build_effective_review_verification_audit_evidence_bundle,
    verification_audit_evidence_bundle_to_mapping,
    verify_effective_review_verification_audit_evidence_bundle,
)


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read bundle: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("bundle must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("bundle must contain a JSON object")
    return payload


def _export(args: argparse.Namespace) -> dict:
    with EffectiveReviewVerificationAuditRepository(args.audit_db) as repository:
        bundle = build_effective_review_verification_audit_evidence_bundle(
            audit_repository=repository,
            audit_entry_id=args.audit_entry_id,
        )
    payload = verification_audit_evidence_bundle_to_mapping(bundle)
    if args.output is not None:
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _verify(args: argparse.Namespace) -> dict:
    payload = _read_json(args.bundle)
    verify_effective_review_verification_audit_evidence_bundle(payload)
    return {
        "valid": True,
        "schema_version": payload["schema_version"],
        "audit_entry_id": payload["audit_entry_id"],
        "receipt_id": payload["receipt_id"],
        "evidence_sha256": payload["evidence_sha256"],
        "export_sha256": payload["export_sha256"],
        "send_authorized": False,
        "evidence_is_campaign_authorization": False,
        "evidence_is_human_approval": False,
        "evidence_is_observational_only": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export or verify offline evidence for the tamper-evident audit of technical verification receipts. This command never authorizes campaign dispatch or send.")
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
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
