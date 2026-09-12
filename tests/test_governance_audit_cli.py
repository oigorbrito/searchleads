from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_governance_snapshot.py"


def _scope(path: Path, *, fresh: bool) -> None:
    path.write_text(
        json.dumps(
            {
                "campaign_id": "cmp-1",
                "policy_id": "policy-1",
                "policy_version": "v1",
                "jurisdiction": "BR-RS",
                "channel": "email",
                "brasilapi_fresh": fresh,
                "professional_verification_required": False,
            }
        ),
        encoding="utf-8",
    )


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_records_and_verifies_hash_chained_snapshots(tmp_path) -> None:
    db = tmp_path / "governance.sqlite"
    scope = tmp_path / "scope.json"
    _scope(scope, fresh=False)

    first = _run(
        "record",
        "--scope", str(scope),
        "--db", str(db),
        "--now", "2026-09-12T03:00:00+00:00",
        "--audit-id", "audit-1",
    )
    assert first.returncode == 0, first.stderr
    first_payload = json.loads(first.stdout)
    assert first_payload["sequence"] == 1
    assert first_payload["previous_entry_hash"] is None
    assert first_payload["send_authorized"] is False
    assert "EXT-BRASILAPI-001" in first_payload["blockers"]

    _scope(scope, fresh=True)
    second = _run(
        "record",
        "--scope", str(scope),
        "--db", str(db),
        "--now", "2026-09-12T03:05:00+00:00",
        "--audit-id", "audit-2",
    )
    assert second.returncode == 0, second.stderr
    second_payload = json.loads(second.stdout)
    assert second_payload["sequence"] == 2
    assert second_payload["previous_entry_hash"] == first_payload["entry_hash"]
    assert second_payload["send_authorized"] is False

    verified = _run("verify", "--db", str(db))
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout) == {
        "audit_entries": 2,
        "chain_valid": True,
        "send_authorized": False,
    }

    listed = _run("list", "--db", str(db))
    assert listed.returncode == 0, listed.stderr
    listed_payload = json.loads(listed.stdout)
    assert listed_payload["chain_valid"] is True
    assert listed_payload["send_authorized"] is False
    assert [item["audit_id"] for item in listed_payload["audit_entries"]] == ["audit-1", "audit-2"]


def test_cli_rejects_duplicate_audit_id(tmp_path) -> None:
    db = tmp_path / "governance.sqlite"
    scope = tmp_path / "scope.json"
    _scope(scope, fresh=False)
    args = (
        "record",
        "--scope", str(scope),
        "--db", str(db),
        "--now", "2026-09-12T03:00:00+00:00",
        "--audit-id", "audit-1",
    )
    assert _run(*args).returncode == 0
    duplicate = _run(*args)
    assert duplicate.returncode == 2
    assert "already exists" in duplicate.stderr
