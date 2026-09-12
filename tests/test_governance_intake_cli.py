from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "process_governance_intake.py"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _scope() -> dict[str, object]:
    return {
        "campaign_id": "campaign-1",
        "policy_id": "policy-1",
        "policy_version": "v1",
        "jurisdiction": "BR-RS",
        "channel": "email",
        "brasilapi_fresh": True,
        "professional_verification_required": False,
    }


def _authorization() -> dict[str, object]:
    return {
        "authorization_id": "authorization-1",
        "campaign_id": "campaign-1",
        "policy_id": "policy-1",
        "policy_version": "v1",
        "authorizer_reference": "campaign-owner-1",
        "authorized_at": "2026-09-12T02:20:00+00:00",
        "valid_until": "2026-09-13T02:20:00+00:00",
        "revoked_at": None,
    }


def test_cli_persists_decision_and_emits_non_send_receipt(tmp_path: Path) -> None:
    decision = tmp_path / "decision.json"
    scope = tmp_path / "scope.json"
    database = tmp_path / "governance.sqlite"
    _write_json(decision, _authorization())
    _write_json(scope, _scope())

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "campaign-authorization",
            str(decision),
            "--scope",
            str(scope),
            "--db",
            str(database),
            "--now",
            "2026-09-12T03:00:00+00:00",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )

    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout)
    assert receipt["decision_id"] == "authorization-1"
    assert receipt["storage_action"] == "INSERTED"
    assert receipt["send_authorized"] is False
    assert receipt["preflight_state"] == "BLOCKED"
    assert receipt["blockers"] == ["LEGAL-001"]
    assert database.exists()


def test_cli_rejects_scope_mismatch(tmp_path: Path) -> None:
    decision = tmp_path / "decision.json"
    scope = tmp_path / "scope.json"
    database = tmp_path / "governance.sqlite"
    payload = _authorization()
    payload["campaign_id"] = "other-campaign"
    _write_json(decision, payload)
    _write_json(scope, _scope())

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "campaign-authorization",
            str(decision),
            "--scope",
            str(scope),
            "--db",
            str(database),
            "--now",
            "2026-09-12T03:00:00+00:00",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )

    assert completed.returncode == 2
    assert "campaign_id does not match preflight scope" in completed.stderr
