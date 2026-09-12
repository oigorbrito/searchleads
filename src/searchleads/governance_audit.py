from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .governance_snapshot import (
    GovernanceOperationalSnapshot,
    governance_operational_snapshot_to_mapping,
)


class GovernanceAuditError(RuntimeError):
    """Base class for governance audit failures."""


class GovernanceAuditConflictError(GovernanceAuditError):
    """Raised when an immutable audit ID is reused."""


class GovernanceAuditIntegrityError(GovernanceAuditError):
    """Raised when an audit payload/hash chain does not verify."""


@dataclass(frozen=True, slots=True)
class GovernanceAuditEntry:
    sequence: int
    audit_id: str
    campaign_id: str
    policy_id: str
    policy_version: str
    jurisdiction: str
    channel: str
    evaluated_at: datetime
    preflight_state: str
    pilot_release_state: str
    blockers: tuple[str, ...]
    decision_ids: tuple[str, ...]
    snapshot_sha256: str
    previous_entry_hash: str | None
    entry_hash: str
    send_authorized: bool = False

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError("sequence must be positive")
        if not self.audit_id.strip():
            raise ValueError("audit_id must not be blank")
        if self.evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at must be timezone-aware")
        for digest in (self.snapshot_sha256, self.entry_hash):
            if len(digest) != 64:
                raise ValueError("audit digests must be SHA-256 hex digests")
        if self.previous_entry_hash is not None and len(self.previous_entry_hash) != 64:
            raise ValueError("previous_entry_hash must be a SHA-256 hex digest")
        if self.send_authorized:
            raise ValueError("governance audit cannot authorize send")


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _decision_ids(snapshot_payload: dict[str, Any]) -> tuple[str, ...]:
    result: list[str] = []
    for gate in snapshot_payload.get("gates", []):
        decision_id = gate.get("decision_id")
        if isinstance(decision_id, str) and decision_id:
            result.append(decision_id)
    return tuple(result)


class GovernanceAuditRepository:
    """Append-only, hash-chained audit trail for governance snapshots."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def __enter__(self) -> "GovernanceAuditRepository":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def _initialize_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS governance_snapshot_audit (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id TEXT NOT NULL UNIQUE,
                campaign_id TEXT NOT NULL,
                policy_id TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                channel TEXT NOT NULL,
                evaluated_at TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                snapshot_sha256 TEXT NOT NULL,
                previous_entry_hash TEXT,
                entry_hash TEXT NOT NULL UNIQUE,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_governance_snapshot_audit_scope
                ON governance_snapshot_audit(
                    campaign_id, policy_id, policy_version, jurisdiction, channel, sequence
                );
            """
        )
        self._connection.commit()

    @staticmethod
    def _entry_hash(
        *,
        audit_id: str,
        snapshot_sha256: str,
        previous_entry_hash: str | None,
    ) -> str:
        material = _canonical_json(
            {
                "audit_id": audit_id,
                "snapshot_sha256": snapshot_sha256,
                "previous_entry_hash": previous_entry_hash,
            }
        )
        return _sha256(material)

    def append_snapshot(
        self,
        *,
        audit_id: str,
        snapshot: GovernanceOperationalSnapshot,
    ) -> GovernanceAuditEntry:
        if not audit_id.strip():
            raise ValueError("audit_id must not be blank")
        existing = self._connection.execute(
            "SELECT 1 FROM governance_snapshot_audit WHERE audit_id = ?",
            (audit_id,),
        ).fetchone()
        if existing is not None:
            raise GovernanceAuditConflictError(f"audit_id {audit_id!r} already exists")

        payload = governance_operational_snapshot_to_mapping(snapshot)
        snapshot_json = _canonical_json(payload)
        snapshot_sha256 = _sha256(snapshot_json)
        previous = self._connection.execute(
            "SELECT entry_hash FROM governance_snapshot_audit ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_entry_hash = previous["entry_hash"] if previous is not None else None
        entry_hash = self._entry_hash(
            audit_id=audit_id,
            snapshot_sha256=snapshot_sha256,
            previous_entry_hash=previous_entry_hash,
        )

        cursor = self._connection.execute(
            """INSERT INTO governance_snapshot_audit(
                   audit_id, campaign_id, policy_id, policy_version, jurisdiction,
                   channel, evaluated_at, snapshot_json, snapshot_sha256,
                   previous_entry_hash, entry_hash
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                audit_id,
                snapshot.campaign_id,
                snapshot.policy_id,
                snapshot.policy_version,
                snapshot.jurisdiction,
                snapshot.channel,
                snapshot.generated_at.isoformat(),
                snapshot_json,
                snapshot_sha256,
                previous_entry_hash,
                entry_hash,
            ),
        )
        self._connection.commit()
        return self._entry_from_values(
            sequence=int(cursor.lastrowid),
            audit_id=audit_id,
            payload=payload,
            snapshot_sha256=snapshot_sha256,
            previous_entry_hash=previous_entry_hash,
            entry_hash=entry_hash,
        )

    @staticmethod
    def _entry_from_values(
        *,
        sequence: int,
        audit_id: str,
        payload: dict[str, Any],
        snapshot_sha256: str,
        previous_entry_hash: str | None,
        entry_hash: str,
    ) -> GovernanceAuditEntry:
        return GovernanceAuditEntry(
            sequence=sequence,
            audit_id=audit_id,
            campaign_id=str(payload["campaign_id"]),
            policy_id=str(payload["policy_id"]),
            policy_version=str(payload["policy_version"]),
            jurisdiction=str(payload["jurisdiction"]),
            channel=str(payload["channel"]),
            evaluated_at=datetime.fromisoformat(str(payload["generated_at"])),
            preflight_state=str(payload["preflight_state"]),
            pilot_release_state=str(payload["pilot_release_state"]),
            blockers=tuple(str(item) for item in payload["blockers"]),
            decision_ids=_decision_ids(payload),
            snapshot_sha256=snapshot_sha256,
            previous_entry_hash=previous_entry_hash,
            entry_hash=entry_hash,
            send_authorized=False,
        )

    def list_entries(self) -> tuple[GovernanceAuditEntry, ...]:
        rows = self._connection.execute(
            """SELECT sequence, audit_id, snapshot_json, snapshot_sha256,
                      previous_entry_hash, entry_hash
               FROM governance_snapshot_audit ORDER BY sequence ASC"""
        ).fetchall()
        entries: list[GovernanceAuditEntry] = []
        expected_previous: str | None = None
        for row in rows:
            snapshot_json = row["snapshot_json"]
            snapshot_sha256 = _sha256(snapshot_json)
            if snapshot_sha256 != row["snapshot_sha256"]:
                raise GovernanceAuditIntegrityError("snapshot payload digest mismatch")
            if row["previous_entry_hash"] != expected_previous:
                raise GovernanceAuditIntegrityError("governance audit chain predecessor mismatch")
            expected_entry_hash = self._entry_hash(
                audit_id=row["audit_id"],
                snapshot_sha256=snapshot_sha256,
                previous_entry_hash=expected_previous,
            )
            if expected_entry_hash != row["entry_hash"]:
                raise GovernanceAuditIntegrityError("governance audit entry hash mismatch")
            payload = json.loads(snapshot_json)
            entries.append(
                self._entry_from_values(
                    sequence=row["sequence"],
                    audit_id=row["audit_id"],
                    payload=payload,
                    snapshot_sha256=snapshot_sha256,
                    previous_entry_hash=expected_previous,
                    entry_hash=row["entry_hash"],
                )
            )
            expected_previous = row["entry_hash"]
        return tuple(entries)

    def verify_chain(self) -> int:
        """Verify the full append-only chain and return the number of valid entries."""
        return len(self.list_entries())

    def load_snapshot_mapping(self, audit_id: str) -> dict[str, Any]:
        """Return the historical snapshot payload after verifying the full audit chain."""
        if not audit_id.strip():
            raise ValueError("audit_id must not be blank")
        self.verify_chain()
        row = self._connection.execute(
            "SELECT snapshot_json FROM governance_snapshot_audit WHERE audit_id = ?",
            (audit_id,),
        ).fetchone()
        if row is None:
            raise KeyError(audit_id)
        payload = json.loads(row["snapshot_json"])
        if not isinstance(payload, dict):
            raise GovernanceAuditIntegrityError("snapshot payload must be a JSON object")
        return payload


def governance_audit_entry_to_mapping(entry: GovernanceAuditEntry) -> dict[str, Any]:
    return {
        "sequence": entry.sequence,
        "audit_id": entry.audit_id,
        "campaign_id": entry.campaign_id,
        "policy_id": entry.policy_id,
        "policy_version": entry.policy_version,
        "jurisdiction": entry.jurisdiction,
        "channel": entry.channel,
        "evaluated_at": entry.evaluated_at.isoformat(),
        "preflight_state": entry.preflight_state,
        "pilot_release_state": entry.pilot_release_state,
        "blockers": list(entry.blockers),
        "decision_ids": list(entry.decision_ids),
        "snapshot_sha256": entry.snapshot_sha256,
        "previous_entry_hash": entry.previous_entry_hash,
        "entry_hash": entry.entry_hash,
        "send_authorized": False,
    }


__all__ = [
    "GovernanceAuditConflictError",
    "GovernanceAuditEntry",
    "GovernanceAuditError",
    "GovernanceAuditIntegrityError",
    "GovernanceAuditRepository",
    "governance_audit_entry_to_mapping",
]
