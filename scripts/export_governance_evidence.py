from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from searchleads.governance_audit import (  # noqa: E402
    GovernanceAuditError,
    GovernanceAuditRepository,
)
from searchleads.governance_evidence_bundle import (  # noqa: E402
    GovernanceEvidenceBundleError,
    build_governance_evidence_bundle,
    governance_evidence_bundle_to_mapping,
    verify_governance_evidence_bundle,
)


def _read_bundle(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read bundle: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("bundle must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("bundle must contain a JSON object")
    return payload


def _write_bundle(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export or verify deterministic governance evidence bundles. "
            "This command never authorizes, sends, or dispatches a campaign."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--audit-db", required=True, type=Path)
    export_parser.add_argument("--audit-id", required=True)
    export_parser.add_argument("--output", required=True, type=Path)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--bundle", required=True, type=Path)

    args = parser.parse_args(argv)

    try:
        if args.command == "export":
            with GovernanceAuditRepository(args.audit_db) as repository:
                bundle = build_governance_evidence_bundle(
                    audit_repository=repository,
                    audit_id=args.audit_id,
                )
            payload = governance_evidence_bundle_to_mapping(bundle)
            _write_bundle(args.output, payload)
            print(
                json.dumps(
                    {
                        "status": "EXPORTED",
                        "audit_id": payload["audit_id"],
                        "bundle_sha256": payload["bundle_sha256"],
                        "output": str(args.output),
                        "send_authorized": False,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0

        payload = _read_bundle(args.bundle)
        verify_governance_evidence_bundle(payload)
        print(
            json.dumps(
                {
                    "status": "VERIFIED",
                    "audit_id": payload["audit_id"],
                    "bundle_sha256": payload["bundle_sha256"],
                    "send_authorized": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (
        GovernanceAuditError,
        GovernanceEvidenceBundleError,
        KeyError,
        OSError,
        ValueError,
    ) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
