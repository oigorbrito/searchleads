from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = ROOT / "scripts" / "audit_governance_snapshot.py"
EXPORT_SCRIPT = ROOT / "scripts" / "export_governance_evidence.py"


def _write_scope(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "campaign_id": "cmp-1",
                "policy_id": "policy-1",
                "policy_version": "v1",
                "jurisdiction": "BR-RS",
                "channel": "email",
                "brasilapi_fresh": False,
                "professional_verification_required": False,
            }
        ),
        encoding="utf-8",
    )


def test_export_then_offline_verify_bundle(tmp_path) -> None:
    db = tmp_path / "governance.sqlite"
    scope = tmp_path / "scope.json"
    bundle = tmp_path / "evidence.json"
    _write_scope(scope)

    recorded = subprocess.run(
        [
            sys.executable,
            str(AUDIT_SCRIPT),
            "record",
            "--scope",
            str(scope),
            "--db",
            str(db),
            "--now",
            "2026-09-12T04:00:00+00:00",
            "--audit-id",
            "audit-1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert recorded.returncode == 0, recorded.stderr

    exported = subprocess.run(
        [
            sys.executable,
            str(EXPORT_SCRIPT),
            "export",
            "--audit-db",
            str(db),
            "--audit-id",
            "audit-1",
            "--output",
            str(bundle),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert exported.returncode == 0, exported.stderr
    export_result = json.loads(exported.stdout)
    assert export_result["status"] == "EXPORTED"
    assert export_result["send_authorized"] is False

    payload = json.loads(bundle.read_text(encoding="utf-8"))
    assert payload["audit_id"] == "audit-1"
    assert payload["send_authorized"] is False
    assert payload["authority_semantics"]["bundle_is_authorization"] is False

    verified = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "verify", "--bundle", str(bundle)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert verified.returncode == 0, verified.stderr
    verify_result = json.loads(verified.stdout)
    assert verify_result["status"] == "VERIFIED"
    assert verify_result["bundle_sha256"] == payload["bundle_sha256"]
    assert verify_result["send_authorized"] is False


def test_verify_rejects_tampered_bundle(tmp_path) -> None:
    db = tmp_path / "governance.sqlite"
    scope = tmp_path / "scope.json"
    bundle = tmp_path / "evidence.json"
    _write_scope(scope)

    recorded = subprocess.run(
        [
            sys.executable,
            str(AUDIT_SCRIPT),
            "record",
            "--scope",
            str(scope),
            "--db",
            str(db),
            "--now",
            "2026-09-12T04:00:00+00:00",
            "--audit-id",
            "audit-1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert recorded.returncode == 0, recorded.stderr

    exported = subprocess.run(
        [
            sys.executable,
            str(EXPORT_SCRIPT),
            "export",
            "--audit-db",
            str(db),
            "--audit-id",
            "audit-1",
            "--output",
            str(bundle),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert exported.returncode == 0, exported.stderr

    payload = json.loads(bundle.read_text(encoding="utf-8"))
    payload["snapshot"]["blockers"] = []
    bundle.write_text(json.dumps(payload), encoding="utf-8")

    verified = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "verify", "--bundle", str(bundle)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert verified.returncode == 2
    assert "INVALID:" in verified.stderr
