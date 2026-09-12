import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "show_governance_snapshot.py"
INTAKE = ROOT / "scripts" / "process_governance_intake.py"
NOW = "2026-09-12T02:45:00+00:00"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _scope() -> dict[str, object]:
    return {
        "campaign_id": "camp-1",
        "policy_id": "policy-1",
        "policy_version": "v1",
        "jurisdiction": "BR-RS",
        "channel": "email",
        "brasilapi_fresh": True,
        "professional_verification_required": False,
    }


def test_snapshot_cli_reports_missing_decisions_and_never_authorizes_send(tmp_path: Path) -> None:
    scope = tmp_path / "scope.json"
    db = tmp_path / "governance.sqlite"
    _write_json(scope, _scope())

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--scope",
            str(scope),
            "--db",
            str(db),
            "--now",
            NOW,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["send_authorized"] is False
    assert payload["blockers"] == ["LEGAL-001", "AUTH-CAMPAIGN-001"]
    professional = next(g for g in payload["gates"] if g["gate_id"] == "EXT-CFO-001")
    assert professional["status"] == "NOT_REQUIRED"


def test_snapshot_cli_reads_decisions_persisted_by_intake_cli(tmp_path: Path) -> None:
    scope = tmp_path / "scope.json"
    db = tmp_path / "governance.sqlite"
    legal = tmp_path / "legal.json"
    authorization = tmp_path / "authorization.json"
    _write_json(scope, _scope())
    _write_json(
        legal,
        {
            "signoff_id": "legal-1",
            "reviewer_reference": "legal-reviewer",
            "policy_id": "policy-1",
            "policy_version": "v1",
            "jurisdiction": "BR-RS",
            "channel": "email",
            "campaign_id": "camp-1",
            "decision": "APPROVED",
            "decided_at": "2026-09-12T01:00:00+00:00",
            "authority_evidence_refs": ["legal-memo:1"],
        },
    )
    _write_json(
        authorization,
        {
            "authorization_id": "auth-1",
            "campaign_id": "camp-1",
            "policy_id": "policy-1",
            "policy_version": "v1",
            "authorizer_reference": "campaign-owner",
            "authorized_at": "2026-09-12T02:00:00+00:00",
        },
    )

    for kind, decision in (("compliance-signoff", legal), ("campaign-authorization", authorization)):
        result = subprocess.run(
            [
                sys.executable,
                str(INTAKE),
                kind,
                str(decision),
                "--scope",
                str(scope),
                "--db",
                str(db),
                "--now",
                NOW,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--scope", str(scope), "--db", str(db), "--now", NOW],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["preflight_state"] == "READY_FOR_AUTHORIZED_EXECUTION"
    assert payload["pilot_release_state"] == "READY_FOR_AUTHORIZED_EXECUTION"
    assert payload["blockers"] == []
    assert payload["send_authorized"] is False
    legal_gate = next(g for g in payload["gates"] if g["gate_id"] == "LEGAL-001")
    assert legal_gate["decision_id"] == "legal-1"
    assert legal_gate["evidence_refs"] == ["legal-memo:1"]


def test_snapshot_cli_rejects_naive_timestamp(tmp_path: Path) -> None:
    scope = tmp_path / "scope.json"
    db = tmp_path / "governance.sqlite"
    _write_json(scope, _scope())

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--scope", str(scope), "--db", str(db), "--now", "2026-09-12T02:45:00"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "timezone-aware" in result.stderr
