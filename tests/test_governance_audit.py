from __future__ import annotations

from datetime import datetime, timezone

import pytest

from searchleads.governance_audit import (
    GovernanceAuditConflictError,
    GovernanceAuditIntegrityError,
    GovernanceAuditRepository,
)
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope
from searchleads.governance_snapshot import build_governance_operational_snapshot


NOW = datetime(2026, 9, 12, 3, 0, tzinfo=timezone.utc)


def _scope(*, fresh: bool = False) -> CampaignPreflightScope:
    return CampaignPreflightScope(
        campaign_id="cmp-1",
        policy_id="policy-1",
        policy_version="v1",
        jurisdiction="BR-RS",
        channel="email",
        brasilapi_fresh=fresh,
    )


def _snapshot(tmp_path, *, fresh: bool = False):
    governance_db = tmp_path / "governance.sqlite"
    with GovernanceDecisionRepository(governance_db) as repository:
        return build_governance_operational_snapshot(
            repository=repository,
            scope=_scope(fresh=fresh),
            now=NOW,
        )


def test_append_snapshot_creates_hash_chained_entries(tmp_path) -> None:
    audit_db = tmp_path / "audit.sqlite"
    first_snapshot = _snapshot(tmp_path, fresh=False)
    second_snapshot = _snapshot(tmp_path, fresh=True)

    with GovernanceAuditRepository(audit_db) as repository:
        first = repository.append_snapshot(audit_id="audit-1", snapshot=first_snapshot)
        second = repository.append_snapshot(audit_id="audit-2", snapshot=second_snapshot)
        entries = repository.list_entries()

        assert first.sequence == 1
        assert first.previous_entry_hash is None
        assert second.sequence == 2
        assert second.previous_entry_hash == first.entry_hash
        assert entries == (first, second)
        assert repository.verify_chain() == 2
        assert first.send_authorized is False
        assert second.send_authorized is False


def test_reusing_audit_id_is_rejected(tmp_path) -> None:
    snapshot = _snapshot(tmp_path)
    with GovernanceAuditRepository(tmp_path / "audit.sqlite") as repository:
        repository.append_snapshot(audit_id="audit-1", snapshot=snapshot)
        with pytest.raises(GovernanceAuditConflictError):
            repository.append_snapshot(audit_id="audit-1", snapshot=snapshot)


def test_snapshot_payload_tampering_is_detected(tmp_path) -> None:
    snapshot = _snapshot(tmp_path)
    with GovernanceAuditRepository(tmp_path / "audit.sqlite") as repository:
        repository.append_snapshot(audit_id="audit-1", snapshot=snapshot)
        repository._connection.execute(
            "UPDATE governance_snapshot_audit SET snapshot_json = ? WHERE audit_id = ?",
            ('{"tampered":true}', "audit-1"),
        )
        repository._connection.commit()
        with pytest.raises(GovernanceAuditIntegrityError, match="snapshot payload digest mismatch"):
            repository.verify_chain()


def test_predecessor_tampering_is_detected(tmp_path) -> None:
    snapshot = _snapshot(tmp_path)
    with GovernanceAuditRepository(tmp_path / "audit.sqlite") as repository:
        repository.append_snapshot(audit_id="audit-1", snapshot=snapshot)
        repository.append_snapshot(audit_id="audit-2", snapshot=snapshot)
        repository._connection.execute(
            "UPDATE governance_snapshot_audit SET previous_entry_hash = ? WHERE audit_id = ?",
            ("0" * 64, "audit-2"),
        )
        repository._connection.commit()
        with pytest.raises(GovernanceAuditIntegrityError, match="predecessor mismatch"):
            repository.verify_chain()
