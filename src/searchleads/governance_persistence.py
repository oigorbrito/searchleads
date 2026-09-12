from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Callable, TypeVar

from .campaign_preflight import (
    CampaignAuthorizationRecord,
    ComplianceSignoffRecord,
    ProfessionalVerificationRecord,
)
from .governance_decision_io import (
    campaign_authorization_from_mapping,
    campaign_authorization_to_mapping,
    compliance_signoff_from_mapping,
    compliance_signoff_to_mapping,
)
from .professional_verification_io import (
    professional_verification_from_mapping,
    professional_verification_to_mapping,
)


class GovernancePersistenceError(RuntimeError):
    """Base class for governance-decision persistence failures."""


class GovernanceDecisionConflictError(GovernancePersistenceError):
    """Raised when an immutable decision ID is reused with different content."""


class GovernanceDecisionIntegrityError(GovernancePersistenceError):
    """Raised when a stored governance payload no longer matches its digest."""


TDecision = TypeVar(
    "TDecision",
    ComplianceSignoffRecord,
    ProfessionalVerificationRecord,
    CampaignAuthorizationRecord,
)

_KIND_COMPLIANCE = "compliance-signoff"
_KIND_PROFESSIONAL = "professional-verification"
_KIND_AUTHORIZATION = "campaign-authorization"


def _canonical_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


class GovernanceDecisionRepository:
    """Append-only SQLite store for externally supplied governance decisions.

    This repository deliberately lives outside the canonical domain-record codec.
    Human/legal decisions are authority inputs to campaign preflight, not lead-domain
    facts. Records are immutable by ID, integrity-protected, and scoped so callers
    can recover the most recent candidate decision for exact preflight inputs.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def __enter__(self) -> "GovernanceDecisionRepository":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def _initialize_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS governance_decisions (
                kind TEXT NOT NULL,
                decision_id TEXT NOT NULL,
                campaign_id TEXT,
                person_id TEXT,
                policy_id TEXT,
                policy_version TEXT,
                jurisdiction TEXT,
                channel TEXT,
                council TEXT,
                effective_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (kind, decision_id)
            );

            CREATE INDEX IF NOT EXISTS idx_governance_campaign_scope
                ON governance_decisions (
                    kind, campaign_id, policy_id, policy_version,
                    jurisdiction, channel, effective_at
                );

            CREATE INDEX IF NOT EXISTS idx_governance_person_scope
                ON governance_decisions (kind, person_id, council, effective_at);
            """
        )
        self._connection.commit()

    def _save(
        self,
        *,
        kind: str,
        decision_id: str,
        payload: dict[str, object],
        effective_at: str,
        campaign_id: str | None = None,
        person_id: str | None = None,
        policy_id: str | None = None,
        policy_version: str | None = None,
        jurisdiction: str | None = None,
        channel: str | None = None,
        council: str | None = None,
    ) -> bool:
        payload_json = _canonical_json(payload)
        digest = _sha256(payload_json)
        row = self._connection.execute(
            """SELECT payload_json, payload_sha256
               FROM governance_decisions
               WHERE kind = ? AND decision_id = ?""",
            (kind, decision_id),
        ).fetchone()
        if row is not None:
            self._verify_payload(row["payload_json"], row["payload_sha256"])
            if row["payload_json"] == payload_json:
                return False
            raise GovernanceDecisionConflictError(
                f"{kind} id {decision_id!r} already exists with different content"
            )

        self._connection.execute(
            """INSERT INTO governance_decisions(
                   kind, decision_id, campaign_id, person_id, policy_id,
                   policy_version, jurisdiction, channel, council,
                   effective_at, payload_json, payload_sha256
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                kind,
                decision_id,
                campaign_id,
                person_id,
                policy_id,
                policy_version,
                jurisdiction,
                channel,
                council,
                effective_at,
                payload_json,
                digest,
            ),
        )
        self._connection.commit()
        return True

    @staticmethod
    def _verify_payload(payload_json: str, digest: str) -> None:
        if _sha256(payload_json) != digest:
            raise GovernanceDecisionIntegrityError("governance decision storage digest mismatch")

    def _load(
        self,
        *,
        kind: str,
        decision_id: str,
        decoder: Callable[[dict[str, object]], TDecision],
    ) -> TDecision | None:
        row = self._connection.execute(
            """SELECT payload_json, payload_sha256
               FROM governance_decisions
               WHERE kind = ? AND decision_id = ?""",
            (kind, decision_id),
        ).fetchone()
        if row is None:
            return None
        self._verify_payload(row["payload_json"], row["payload_sha256"])
        return decoder(json.loads(row["payload_json"]))

    def _load_latest(
        self,
        *,
        where_sql: str,
        params: tuple[object, ...],
        decoder: Callable[[dict[str, object]], TDecision],
    ) -> TDecision | None:
        row = self._connection.execute(
            f"""SELECT payload_json, payload_sha256
                FROM governance_decisions
                WHERE {where_sql}
                ORDER BY effective_at DESC, decision_id DESC
                LIMIT 1""",
            params,
        ).fetchone()
        if row is None:
            return None
        self._verify_payload(row["payload_json"], row["payload_sha256"])
        return decoder(json.loads(row["payload_json"]))

    def save_compliance_signoff(self, record: ComplianceSignoffRecord) -> bool:
        return self._save(
            kind=_KIND_COMPLIANCE,
            decision_id=record.signoff_id,
            campaign_id=record.campaign_id,
            policy_id=record.policy_id,
            policy_version=record.policy_version,
            jurisdiction=record.jurisdiction,
            channel=record.channel,
            effective_at=record.decided_at.isoformat(),
            payload=compliance_signoff_to_mapping(record),
        )

    def load_compliance_signoff(self, signoff_id: str) -> ComplianceSignoffRecord | None:
        return self._load(
            kind=_KIND_COMPLIANCE,
            decision_id=signoff_id,
            decoder=compliance_signoff_from_mapping,
        )

    def latest_compliance_signoff(
        self,
        *,
        campaign_id: str,
        policy_id: str,
        policy_version: str,
        jurisdiction: str,
        channel: str,
    ) -> ComplianceSignoffRecord | None:
        return self._load_latest(
            where_sql=(
                "kind = ? AND campaign_id = ? AND policy_id = ? AND policy_version = ? "
                "AND jurisdiction = ? AND channel = ?"
            ),
            params=(
                _KIND_COMPLIANCE,
                campaign_id,
                policy_id,
                policy_version,
                jurisdiction,
                channel,
            ),
            decoder=compliance_signoff_from_mapping,
        )

    def save_professional_verification(self, record: ProfessionalVerificationRecord) -> bool:
        return self._save(
            kind=_KIND_PROFESSIONAL,
            decision_id=record.verification_id,
            person_id=record.person_id,
            council=record.council,
            effective_at=record.verified_at.isoformat(),
            payload=professional_verification_to_mapping(record),
        )

    def load_professional_verification(
        self, verification_id: str
    ) -> ProfessionalVerificationRecord | None:
        return self._load(
            kind=_KIND_PROFESSIONAL,
            decision_id=verification_id,
            decoder=professional_verification_from_mapping,
        )

    def latest_professional_verification(
        self, *, person_id: str, council: str | None = None
    ) -> ProfessionalVerificationRecord | None:
        if council is None:
            where_sql = "kind = ? AND person_id = ?"
            params: tuple[object, ...] = (_KIND_PROFESSIONAL, person_id)
        else:
            where_sql = "kind = ? AND person_id = ? AND council = ?"
            params = (_KIND_PROFESSIONAL, person_id, council)
        return self._load_latest(
            where_sql=where_sql,
            params=params,
            decoder=professional_verification_from_mapping,
        )

    def save_campaign_authorization(self, record: CampaignAuthorizationRecord) -> bool:
        return self._save(
            kind=_KIND_AUTHORIZATION,
            decision_id=record.authorization_id,
            campaign_id=record.campaign_id,
            policy_id=record.policy_id,
            policy_version=record.policy_version,
            effective_at=record.authorized_at.isoformat(),
            payload=campaign_authorization_to_mapping(record),
        )

    def load_campaign_authorization(
        self, authorization_id: str
    ) -> CampaignAuthorizationRecord | None:
        return self._load(
            kind=_KIND_AUTHORIZATION,
            decision_id=authorization_id,
            decoder=campaign_authorization_from_mapping,
        )

    def latest_campaign_authorization(
        self, *, campaign_id: str, policy_id: str, policy_version: str
    ) -> CampaignAuthorizationRecord | None:
        return self._load_latest(
            where_sql=(
                "kind = ? AND campaign_id = ? AND policy_id = ? AND policy_version = ?"
            ),
            params=(_KIND_AUTHORIZATION, campaign_id, policy_id, policy_version),
            decoder=campaign_authorization_from_mapping,
        )


__all__ = [
    "GovernanceDecisionConflictError",
    "GovernanceDecisionIntegrityError",
    "GovernanceDecisionRepository",
    "GovernancePersistenceError",
]
