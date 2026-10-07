from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
import json
from pathlib import Path
from typing import Any, Callable, ClassVar, Mapping
from urllib.parse import urlsplit

from searchleads.domain import utc_now
from searchleads.persistence import SCHEMA_VERSION as SQLITE_SCHEMA_VERSION, SQLiteRepository


class ConfigurationClassification(StrEnum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    ENVIRONMENT_SPECIFIC = "ENVIRONMENT_SPECIFIC"
    SECRET = "SECRET"
    NON_SECRET = "NON_SECRET"


class OperationalFailureClass(StrEnum):
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    SOURCE_ERROR = "SOURCE_ERROR"
    TIMEOUT = "TIMEOUT"
    INTEGRITY_ERROR = "INTEGRITY_ERROR"
    SCHEMA_ERROR = "SCHEMA_ERROR"
    DOMAIN_ERROR = "DOMAIN_ERROR"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    COMPLIANCE_BLOCKED = "COMPLIANCE_BLOCKED"


class ProcessHealth(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    HEALTHY = "HEALTHY"
    BROKEN = "BROKEN"


class SystemReadiness(StrEnum):
    NOT_READY = "NOT_READY"
    READY = "READY"


class SendReadyState(StrEnum):
    DISCOVERED = "DISCOVERED"
    VALIDATED = "VALIDATED"
    QUALIFIED = "QUALIFIED"
    COMPLIANCE_PENDING = "COMPLIANCE_PENDING"
    LIVE_CERTIFICATION_PENDING = "LIVE_CERTIFICATION_PENDING"
    SEND_READY = "SEND_READY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    COMPLIANCE_BLOCKED = "COMPLIANCE_BLOCKED"


class ContactUseState(StrEnum):
    UNKNOWN = "UNKNOWN"
    ALLOWED_BY_POLICY = "ALLOWED_BY_POLICY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    SUPPRESSED = "SUPPRESSED"
    BLOCKED = "BLOCKED"


class CertificationResult(StrEnum):
    UNIT_PASS = "UNIT_PASS"
    INTEGRATION_PASS = "INTEGRATION_PASS"
    LIVE_PASS = "LIVE_PASS"
    LIVE_BLOCKED = "LIVE_BLOCKED"
    LIVE_FAIL = "LIVE_FAIL"


class PilotReadinessState(StrEnum):
    NOT_READY = "NOT_READY"
    READY_PENDING_MANUAL_AUTHORIZATION = "READY_PENDING_MANUAL_AUTHORIZATION"
    READY = "READY"


class SourceCertificationStatus(StrEnum):
    CERTIFIED = "CERTIFIED"
    CERTIFIED_WITH_LIMITATIONS = "CERTIFIED_WITH_LIMITATIONS"
    BLOCKED_CREDENTIAL = "BLOCKED_CREDENTIAL"
    BLOCKED_HUMAN_VERIFICATION = "BLOCKED_HUMAN_VERIFICATION"
    BLOCKED_NETWORK = "BLOCKED_NETWORK"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    CONTRACT_FAIL = "CONTRACT_FAIL"
    OPTIONAL_NOT_RUN = "OPTIONAL_NOT_RUN"


class SourceAuthorityScope(StrEnum):
    PRODUCT_CRITICAL = "PRODUCT_CRITICAL"
    CAMPAIGN_CRITICAL = "CAMPAIGN_CRITICAL"
    OPTIONAL_BREADTH = "OPTIONAL_BREADTH"
    EXPERIMENTAL_ONLY = "EXPERIMENTAL_ONLY"


class FreshnessPolicy(StrEnum):
    REVALIDATE_BEFORE_USE = "REVALIDATE_BEFORE_USE"
    REVALIDATE_ON_CHANGE = "REVALIDATE_ON_CHANGE"
    REVALIDATE_ON_EXPIRY = "REVALIDATE_ON_EXPIRY"
    STALE = "STALE"


class ContactClass(StrEnum):
    COMPANY_GENERIC = "COMPANY_GENERIC"
    BUSINESS_PERSONALIZED = "BUSINESS_PERSONALIZED"
    PERSONAL = "PERSONAL"
    UNKNOWN = "UNKNOWN"


class AuthorizationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class ConfigurationField:
    env_var: str
    classifications: tuple[ConfigurationClassification, ...]
    description: str


@dataclass(frozen=True, slots=True)
class OperationalFailure:
    failure_class: OperationalFailureClass
    message: str
    details: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("failure message must be non-blank")
        if any(not key.strip() or not value.strip() for key, value in self.details):
            raise ValueError("failure details must not contain blanks")
        if len({key for key, _ in self.details}) != len(self.details):
            raise ValueError("failure details must use unique keys")

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_class": self.failure_class.value,
            "message": self.message,
            "details": {key: value for key, value in self.details},
        }


class OperationalError(RuntimeError):
    def __init__(
        self,
        failure_class: OperationalFailureClass,
        message: str,
        *,
        details: Mapping[str, str] | None = None,
    ) -> None:
        self.failure_class = failure_class
        self.details = dict(details or {})
        super().__init__(message)

    def to_failure(self) -> OperationalFailure:
        return OperationalFailure(
            self.failure_class,
            str(self),
            tuple(sorted((str(key), str(value)) for key, value in self.details.items())),
        )


@dataclass(frozen=True, slots=True)
class OperationalEvent:
    event: str
    timestamp: datetime
    correlation_id: str
    capability: str
    outcome: str
    entity_id: str | None = None
    error_class: OperationalFailureClass | None = None
    details: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.event.strip():
            raise ValueError("event must be non-blank")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if not self.correlation_id.strip():
            raise ValueError("correlation_id must be non-blank")
        if not self.capability.strip():
            raise ValueError("capability must be non-blank")
        if not self.outcome.strip():
            raise ValueError("outcome must be non-blank")
        if any(not key.strip() or not value.strip() for key, value in self.details):
            raise ValueError("details must not contain blanks")
        if len({key for key, _ in self.details}) != len(self.details):
            raise ValueError("details must use unique keys")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "event": self.event,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "capability": self.capability,
            "outcome": self.outcome,
            "entity_id": self.entity_id,
            "error_class": self.error_class.value if self.error_class else None,
            "details": {key: value for key, value in self.details},
        }
        return payload


@dataclass(frozen=True, slots=True)
class OperationalTelemetrySnapshot:
    request_count: int = 0
    acquisition_success_count: int = 0
    acquisition_failure_count: int = 0
    retry_count: int = 0
    latency_ms_total: int = 0
    evidence_persisted_count: int = 0
    er_auto_match_count: int = 0
    er_review_count: int = 0
    er_insufficient_count: int = 0
    review_queue_count: int = 0
    qualification_outcome_count: int = 0
    startup_failure_count: int = 0
    integrity_failure_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class LiveCertificationRecord:
    source: str
    capability: str
    environment: str
    live_executed: bool
    contract_passed: bool
    evidence_id: str | None
    last_certified: datetime | None
    expiry_policy: str
    blocker: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.capability.strip() or not self.environment.strip():
            raise ValueError("live certification record requires source, capability, and environment")
        if self.last_certified is not None and self.last_certified.tzinfo is None:
            raise ValueError("last_certified must be timezone-aware")
        if self.evidence_id is not None and not self.evidence_id.strip():
            raise ValueError("evidence_id must not be blank when supplied")
        if not self.expiry_policy.strip():
            raise ValueError("expiry_policy must be non-blank")
        if self.blocker is not None and not self.blocker.strip():
            raise ValueError("blocker must not be blank when supplied")


@dataclass(frozen=True, slots=True)
class ComplianceBlocker:
    blocker_id: str
    topic: str
    description: str
    status: str = "OPEN"
    owner: str = "compliance"

    def __post_init__(self) -> None:
        if not self.blocker_id.strip() or not self.topic.strip() or not self.description.strip():
            raise ValueError("compliance blocker requires non-blank identity and description")
        if not self.status.strip() or not self.owner.strip():
            raise ValueError("compliance blocker status and owner must be non-blank")


@dataclass(frozen=True, slots=True)
class LiveSourceCertification:
    certification_id: str
    source: str
    source_type: str
    official_endpoint_or_surface: str
    timestamp: datetime
    tested_commit_sha: str
    request_class: str
    request_identifier: str
    http_status: int | None
    response_contract: str
    raw_evidence_id: str | None
    integrity_digest: str | None
    expected_semantics: str
    observed_semantics: str
    result: CertificationResult
    failure_classification: str | None
    revalidation_due: datetime | None

    def __post_init__(self) -> None:
        required_text = (
            self.certification_id,
            self.source,
            self.source_type,
            self.official_endpoint_or_surface,
            self.tested_commit_sha,
            self.request_class,
            self.request_identifier,
            self.response_contract,
            self.expected_semantics,
            self.observed_semantics,
        )
        if any(not item.strip() for item in required_text):
            raise ValueError("live source certification requires non-blank fields")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if self.revalidation_due is not None and self.revalidation_due.tzinfo is None:
            raise ValueError("revalidation_due must be timezone-aware")
        if self.http_status is not None and self.http_status <= 0:
            raise ValueError("http_status must be positive when supplied")
        if self.raw_evidence_id is not None and not self.raw_evidence_id.strip():
            raise ValueError("raw_evidence_id must not be blank when supplied")
        if self.integrity_digest is not None and not self.integrity_digest.strip():
            raise ValueError("integrity_digest must not be blank when supplied")
        if self.failure_classification is not None and not self.failure_classification.strip():
            raise ValueError("failure_classification must not be blank when supplied")


@dataclass(frozen=True, slots=True)
class SourceAuthorityFact:
    fact_name: str
    authority_scope: SourceAuthorityScope
    description: str

    def __post_init__(self) -> None:
        if any(not item.strip() for item in (self.fact_name, self.description)):
            raise ValueError("source authority fact requires non-blank fields")


@dataclass(frozen=True, slots=True)
class SourceAuthorityMapEntry:
    source_id: str
    source_name: str
    source_authority: str
    source_type: str
    criticality: SourceAuthorityScope
    facts: tuple[SourceAuthorityFact, ...]
    freshness_policy: FreshnessPolicy
    certification_status: SourceCertificationStatus
    next_gate: str

    def __post_init__(self) -> None:
        if any(not item.strip() for item in (self.source_id, self.source_name, self.source_authority, self.source_type, self.next_gate)):
            raise ValueError("source authority map entry requires non-blank fields")
        if not self.facts:
            raise ValueError("source authority map entry requires at least one fact")


@dataclass(frozen=True, slots=True)
class SourceContractDrift:
    source_id: str
    source_name: str
    status: SourceCertificationStatus
    missing_fields: tuple[str, ...] = ()
    unexpected_fields: tuple[str, ...] = ()
    semantic_changes: tuple[str, ...] = ()
    observed_at: datetime | None = None
    evidence_id: str | None = None

    def __post_init__(self) -> None:
        if any(not item.strip() for item in (self.source_id, self.source_name)):
            raise ValueError("source contract drift requires non-blank identity")
        if self.observed_at is not None and self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.evidence_id is not None and not self.evidence_id.strip():
            raise ValueError("evidence_id must not be blank when supplied")


@dataclass(frozen=True, slots=True)
class CampaignCompliancePolicy:
    policy_id: str
    version: str
    jurisdiction: str
    channel: str
    allowed_contact_classes: tuple[ContactClass, ...]
    target_rules: tuple[str, ...]
    contact_use_rules: tuple[str, ...]
    suppression_rules: tuple[str, ...]
    required_certifications: tuple[str, ...]
    authorization_authority: str
    legal_signoff_required: bool = True
    manual_review_required: bool = True

    def __post_init__(self) -> None:
        if any(not item.strip() for item in (self.policy_id, self.version, self.jurisdiction, self.channel, self.authorization_authority)):
            raise ValueError("campaign compliance policy requires non-blank identity")
        if not self.allowed_contact_classes:
            raise ValueError("campaign compliance policy requires at least one allowed contact class")
        if not self.target_rules or not self.contact_use_rules or not self.suppression_rules or not self.required_certifications:
            raise ValueError("campaign compliance policy requires rule sets")


@dataclass(frozen=True, slots=True)
class ManualAuthorizationRecord:
    authorization_id: str
    campaign_id: str
    policy_id: str
    version: str
    authorized_by: str
    timestamp: datetime
    scope: str
    expires_at: datetime | None
    reason: str
    status: AuthorizationStatus = AuthorizationStatus.ACTIVE
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if any(not item.strip() for item in (self.authorization_id, self.campaign_id, self.policy_id, self.version, self.authorized_by, self.scope, self.reason)):
            raise ValueError("manual authorization record requires non-blank fields")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if self.revoked_at is not None and self.revoked_at.tzinfo is None:
            raise ValueError("revoked_at must be timezone-aware")

    @property
    def active(self) -> bool:
        if self.status is not AuthorizationStatus.ACTIVE:
            return False
        if self.expires_at is not None and self.expires_at <= utc_now():
            return False
        return self.revoked_at is None


@dataclass(frozen=True, slots=True)
class SendReadyProof:
    proof_id: str
    evaluation_id: str
    qualification_decision_id: str | None
    contact_validation_id: str | None
    contact_use_decision_id: str | None
    suppression_decision_id: str | None
    certification_refs: tuple[str, ...]
    policy_version: str
    authorization_ref: str | None
    result: SendReadyAssessment
    timestamp: datetime

    def __post_init__(self) -> None:
        if any(not item.strip() for item in (self.proof_id, self.evaluation_id, self.policy_version)):
            raise ValueError("send ready proof requires non-blank fields")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if any(not item.strip() for item in self.certification_refs):
            raise ValueError("certification_refs must not contain blanks")


@dataclass(frozen=True, slots=True)
class ContactUseDecision:
    decision_id: str
    contact_id: str
    relationship_id: str
    campaign_policy_version: str
    decision: ContactUseState
    reason_code: str
    evidence_refs: tuple[str, ...] = ()
    reviewed_at: datetime | None = None
    authority: str = "automatic"

    def __post_init__(self) -> None:
        if any(not item.strip() for item in (self.decision_id, self.contact_id, self.relationship_id, self.campaign_policy_version, self.reason_code, self.authority)):
            raise ValueError("contact use decision requires non-blank fields")
        if self.reviewed_at is not None and self.reviewed_at.tzinfo is None:
            raise ValueError("reviewed_at must be timezone-aware")
        if any(not item.strip() for item in self.evidence_refs):
            raise ValueError("evidence_refs must not contain blanks")


@dataclass(frozen=True, slots=True)
class SuppressionRule:
    suppression_id: str
    scope: str
    subject_id: str
    reason: str
    active: bool = True
    reviewed_at: datetime | None = None

    def __post_init__(self) -> None:
        if any(not item.strip() for item in (self.suppression_id, self.scope, self.subject_id, self.reason)):
            raise ValueError("suppression rule requires non-blank fields")
        if self.reviewed_at is not None and self.reviewed_at.tzinfo is None:
            raise ValueError("reviewed_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ComplianceDecision:
    decision_id: str
    subject_id: str
    campaign_policy_version: str
    decision: ContactUseState
    reason_code: str
    evidence_refs: tuple[str, ...] = ()
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None
    authority: str = "automatic"

    def __post_init__(self) -> None:
        if any(not item.strip() for item in (self.decision_id, self.subject_id, self.campaign_policy_version, self.reason_code, self.authority)):
            raise ValueError("compliance decision requires non-blank fields")
        if self.reviewed_at is not None and self.reviewed_at.tzinfo is None:
            raise ValueError("reviewed_at must be timezone-aware")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if any(not item.strip() for item in self.evidence_refs):
            raise ValueError("evidence_refs must not contain blanks")


@dataclass(frozen=True, slots=True)
class CommercialPilotReadiness:
    state: PilotReadinessState
    ready: bool
    blockers: tuple[str, ...] = ()
    manual_authorization_required: bool = True
    certification_results: tuple[LiveSourceCertification, ...] = ()
    contact_use_decision: ContactUseDecision | None = None
    compliance_decision: ComplianceDecision | None = None
    suppression_rules: tuple[SuppressionRule, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationalConfiguration:
    repository_path: Path
    backup_path: Path | None = None
    runtime_source_id: str | None = None
    runtime_source_url: str | None = None
    secret_token: str | None = field(default=None, repr=False)
    schema_version: int = SQLITE_SCHEMA_VERSION
    deployment_mode: str = "local"
    log_level: str = "INFO"

    FIELD_CATALOG: ClassVar[tuple[ConfigurationField, ...]] = (
        ConfigurationField(
            "SEARCHLEADS_REPOSITORY_PATH",
            (ConfigurationClassification.REQUIRED, ConfigurationClassification.NON_SECRET),
            "Primary SQLite repository path for the operational runtime.",
        ),
        ConfigurationField(
            "SEARCHLEADS_SCHEMA_VERSION",
            (ConfigurationClassification.REQUIRED, ConfigurationClassification.NON_SECRET),
            "Explicit schema marker used to reject unsupported startup state.",
        ),
        ConfigurationField(
            "SEARCHLEADS_BACKUP_PATH",
            (
                ConfigurationClassification.OPTIONAL,
                ConfigurationClassification.ENVIRONMENT_SPECIFIC,
                ConfigurationClassification.NON_SECRET,
            ),
            "Optional backup destination for local recovery runs.",
        ),
        ConfigurationField(
            "SEARCHLEADS_RUNTIME_SOURCE_ID",
            (
                ConfigurationClassification.OPTIONAL,
                ConfigurationClassification.ENVIRONMENT_SPECIFIC,
                ConfigurationClassification.NON_SECRET,
            ),
            "Optional runtime source identity for the acquisition adapter.",
        ),
        ConfigurationField(
            "SEARCHLEADS_RUNTIME_SOURCE_URL",
            (
                ConfigurationClassification.OPTIONAL,
                ConfigurationClassification.ENVIRONMENT_SPECIFIC,
                ConfigurationClassification.NON_SECRET,
            ),
            "Optional runtime source locator for the acquisition adapter.",
        ),
        ConfigurationField(
            "SEARCHLEADS_SECRET_TOKEN",
            (ConfigurationClassification.OPTIONAL, ConfigurationClassification.SECRET),
            "Optional secret boundary used by the runtime wrapper.",
        ),
        ConfigurationField(
            "SEARCHLEADS_DEPLOYMENT_MODE",
            (
                ConfigurationClassification.OPTIONAL,
                ConfigurationClassification.ENVIRONMENT_SPECIFIC,
                ConfigurationClassification.NON_SECRET,
            ),
            "Operational environment label, such as local or ci.",
        ),
        ConfigurationField(
            "SEARCHLEADS_LOG_LEVEL",
            (
                ConfigurationClassification.OPTIONAL,
                ConfigurationClassification.ENVIRONMENT_SPECIFIC,
                ConfigurationClassification.NON_SECRET,
            ),
            "Logging level for structured operational events.",
        ),
    )

    def __post_init__(self) -> None:
        self._validate()

    @classmethod
    def field_catalog(cls) -> tuple[ConfigurationField, ...]:
        return cls.FIELD_CATALOG

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, str]) -> "OperationalConfiguration":
        repository_value = mapping.get("SEARCHLEADS_REPOSITORY_PATH")
        if repository_value is None or not repository_value.strip():
            raise OperationalError(
                OperationalFailureClass.CONFIGURATION_ERROR,
                "missing required configuration SEARCHLEADS_REPOSITORY_PATH",
            )
        schema_value = mapping.get("SEARCHLEADS_SCHEMA_VERSION")
        if schema_value is None or not str(schema_value).strip():
            raise OperationalError(
                OperationalFailureClass.CONFIGURATION_ERROR,
                "missing required configuration SEARCHLEADS_SCHEMA_VERSION",
            )
        try:
            schema_version = int(str(schema_value))
        except ValueError as exc:
            raise OperationalError(
                OperationalFailureClass.CONFIGURATION_ERROR,
                "SEARCHLEADS_SCHEMA_VERSION must be an integer",
            ) from exc
        repository_path = _parse_repository_path(repository_value, "SEARCHLEADS_REPOSITORY_PATH")
        backup_path = _parse_optional_path(mapping.get("SEARCHLEADS_BACKUP_PATH"), "SEARCHLEADS_BACKUP_PATH")
        runtime_source_url = _parse_optional_url(mapping.get("SEARCHLEADS_RUNTIME_SOURCE_URL"), "SEARCHLEADS_RUNTIME_SOURCE_URL")
        runtime_source_id = _parse_optional_text(mapping.get("SEARCHLEADS_RUNTIME_SOURCE_ID"), "SEARCHLEADS_RUNTIME_SOURCE_ID")
        secret_token = _parse_optional_text(mapping.get("SEARCHLEADS_SECRET_TOKEN"), "SEARCHLEADS_SECRET_TOKEN")
        deployment_mode = _parse_optional_text(mapping.get("SEARCHLEADS_DEPLOYMENT_MODE", "local"), "SEARCHLEADS_DEPLOYMENT_MODE") or "local"
        log_level = (_parse_optional_text(mapping.get("SEARCHLEADS_LOG_LEVEL", "INFO"), "SEARCHLEADS_LOG_LEVEL") or "INFO").upper()
        return cls(
            repository_path=repository_path,
            backup_path=backup_path,
            runtime_source_id=runtime_source_id,
            runtime_source_url=runtime_source_url,
            secret_token=secret_token,
            schema_version=schema_version,
            deployment_mode=deployment_mode,
            log_level=log_level,
        )

    def classification_map(self) -> dict[str, tuple[ConfigurationClassification, ...]]:
        return {field.env_var: field.classifications for field in self.FIELD_CATALOG}

    def _validate(self) -> None:
        if self.schema_version != SQLITE_SCHEMA_VERSION:
            raise OperationalError(
                OperationalFailureClass.SCHEMA_ERROR,
                f"unsupported schema version {self.schema_version!r}; supported={SQLITE_SCHEMA_VERSION}",
            )
        _parse_repository_path(str(self.repository_path), "repository_path")
        if self.backup_path is not None:
            _parse_optional_path(str(self.backup_path), "backup_path")
        if self.runtime_source_url is not None:
            _parse_optional_url(self.runtime_source_url, "runtime_source_url")
        if self.runtime_source_id is not None and not self.runtime_source_id.strip():
            raise OperationalError(
                OperationalFailureClass.CONFIGURATION_ERROR,
                "runtime_source_id must not be blank",
            )
        if self.secret_token is not None and not self.secret_token.strip():
            raise OperationalError(
                OperationalFailureClass.CONFIGURATION_ERROR,
                "secret_token must not be blank",
            )
        if not self.deployment_mode.strip():
            raise OperationalError(
                OperationalFailureClass.CONFIGURATION_ERROR,
                "deployment_mode must not be blank",
            )
        if not self.log_level.strip():
            raise OperationalError(
                OperationalFailureClass.CONFIGURATION_ERROR,
                "log_level must not be blank",
            )


@dataclass(frozen=True, slots=True)
class OperationalHealthReport:
    status: ProcessHealth
    started_at: datetime | None
    stopped_at: datetime | None
    failure: OperationalFailure | None = None

    @property
    def healthy(self) -> bool:
        return self.status is ProcessHealth.HEALTHY


@dataclass(frozen=True, slots=True)
class SystemReadinessReport:
    status: SystemReadiness
    blockers: tuple[str, ...] = ()
    details: tuple[tuple[str, str], ...] = ()

    @property
    def ready(self) -> bool:
        return self.status is SystemReadiness.READY


@dataclass(frozen=True, slots=True)
class SendReadyAssessment:
    state: SendReadyState
    ready: bool
    blockers: tuple[str, ...] = ()
    missing_inputs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SendReadyInputs:
    discovered: bool = False
    validated: bool = False
    qualified: bool = False
    compliance_cleared: bool = False
    live_certified: bool = False
    compliance_blockers: tuple[str, ...] = ()
    review_required: bool = False

    def __post_init__(self) -> None:
        if any(not item.strip() for item in self.compliance_blockers):
            raise ValueError("compliance_blockers must not contain blanks")


@dataclass(slots=True)
class OperationalRuntime:
    configuration: OperationalConfiguration
    repository: SQLiteRepository | None = None
    runtime_adapter: Any | None = None
    startup_checks: tuple[Callable[[], None], ...] = ()
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    startup_failure: OperationalFailure | None = None

    def startup(self) -> None:
        try:
            self.configuration._validate()
            if self.repository is None:
                raise OperationalError(
                    OperationalFailureClass.DEPENDENCY_ERROR,
                    "repository is not configured",
                )
            if self.runtime_adapter is None:
                raise OperationalError(
                    OperationalFailureClass.DEPENDENCY_ERROR,
                    "runtime adapter is not configured",
                )
            if self.repository.schema_version != self.configuration.schema_version:
                raise OperationalError(
                    OperationalFailureClass.SCHEMA_ERROR,
                    f"repository schema {self.repository.schema_version} does not match configured schema {self.configuration.schema_version}",
                )
            for check in self.startup_checks:
                check()
        except Exception as exc:
            self.startup_failure = exc.to_failure() if isinstance(exc, OperationalError) else OperationalFailure(
                OperationalFailureClass.DOMAIN_ERROR,
                str(exc),
            )
            raise
        self.started_at = utc_now()
        self.stopped_at = None
        self.startup_failure = None

    def shutdown(self) -> None:
        self.stopped_at = utc_now()

    def restart(self) -> None:
        self.shutdown()
        self.startup()

    def health_report(self) -> OperationalHealthReport:
        if self.startup_failure is not None:
            return OperationalHealthReport(ProcessHealth.BROKEN, self.started_at, self.stopped_at, self.startup_failure)
        if self.started_at is None:
            return OperationalHealthReport(ProcessHealth.NOT_STARTED, self.started_at, self.stopped_at, self.startup_failure)
        return OperationalHealthReport(ProcessHealth.HEALTHY, self.started_at, self.stopped_at)

    def readiness_report(self) -> SystemReadinessReport:
        blockers: list[str] = []
        if self.started_at is None or self.startup_failure is not None:
            blockers.append("process not healthy")
        if self.repository is None:
            blockers.append("repository unavailable")
        else:
            if self.repository.schema_version != self.configuration.schema_version:
                blockers.append("schema mismatch")
        if self.runtime_adapter is None:
            blockers.append("runtime adapter unavailable")
        if blockers:
            return SystemReadinessReport(SystemReadiness.NOT_READY, tuple(blockers), ())
        details = (
            ("repository", type(self.repository).__name__),
            ("runtime_adapter", type(self.runtime_adapter).__name__),
            ("schema_version", str(self.configuration.schema_version)),
        )
        return SystemReadinessReport(SystemReadiness.READY, (), details)


@dataclass(frozen=True, slots=True)
class CertificationScope:
    source: str
    capability: str
    environment: str
    expected_contract: str
    expiry_policy: str = "revalidate before live certification expiry"


def build_external_certification_inventory() -> tuple[CertificationScope, ...]:
    return (
        CertificationScope("BrasilAPI CNPJ v1", "company acquisition", "live-network", "CNPJ lookups and response parsing"),
        CertificationScope("SERPRO transparency page", "company enrichment", "live-network", "official source discovery and replayable capture"),
        CertificationScope("CRO/CFO registry", "professional registration", "live-network", "registration status and source identity"),
        CertificationScope("DNS/HTTP contact path", "contact publication", "live-network", "publication and reachability observations"),
    )


def build_source_authority_map() -> tuple[SourceAuthorityMapEntry, ...]:
    return (
        SourceAuthorityMapEntry(
            "source:brasilapi:cnpj-v1",
            "BrasilAPI CNPJ v1",
            "official BrasilAPI public endpoint",
            "public-api",
            SourceAuthorityScope.PRODUCT_CRITICAL,
            (
                SourceAuthorityFact("company registry facts", SourceAuthorityScope.PRODUCT_CRITICAL, "registry-derived company identity and status"),
                SourceAuthorityFact("source observation", SourceAuthorityScope.PRODUCT_CRITICAL, "raw response and parseable contract evidence"),
            ),
            FreshnessPolicy.REVALIDATE_BEFORE_USE,
            SourceCertificationStatus.CERTIFIED_WITH_LIMITATIONS,
            "revalidate before use and on response shape change",
        ),
        SourceAuthorityMapEntry(
            "source:serpro:transparency",
            "SERPRO transparency page",
            "official SERPRO transparency portal",
            "public-web",
            SourceAuthorityScope.PRODUCT_CRITICAL,
            (
                SourceAuthorityFact("source discovery", SourceAuthorityScope.PRODUCT_CRITICAL, "official page identity and published endpoints"),
                SourceAuthorityFact("replayable capture", SourceAuthorityScope.PRODUCT_CRITICAL, "captured HTML or response body for offline replay"),
            ),
            FreshnessPolicy.REVALIDATE_ON_CHANGE,
            SourceCertificationStatus.SOURCE_UNAVAILABLE,
            "revalidate on source change or when live capture succeeds",
        ),
        SourceAuthorityMapEntry(
            "source:cfo:registration",
            "CFO/CRO registration",
            "official CFO public consultation surface",
            "public-web",
            SourceAuthorityScope.CAMPAIGN_CRITICAL,
            (
                SourceAuthorityFact("professional registration status", SourceAuthorityScope.CAMPAIGN_CRITICAL, "current registration visibility for dental professional verification"),
            ),
            FreshnessPolicy.REVALIDATE_ON_EXPIRY,
            SourceCertificationStatus.BLOCKED_HUMAN_VERIFICATION,
            "manual verification required before current status certification",
        ),
        SourceAuthorityMapEntry(
            "source:dns-http:contact-path",
            "DNS/HTTP contact path",
            "DNS and HTTP transport surfaces",
            "technical-validation",
            SourceAuthorityScope.OPTIONAL_BREADTH,
            (
                SourceAuthorityFact("domain existence", SourceAuthorityScope.OPTIONAL_BREADTH, "DNS resolution and HTTP accessibility"),
                SourceAuthorityFact("publication observation", SourceAuthorityScope.OPTIONAL_BREADTH, "contact page or publication availability"),
            ),
            FreshnessPolicy.REVALIDATE_ON_CHANGE,
            SourceCertificationStatus.OPTIONAL_NOT_RUN,
            "revalidate when contact publication becomes pilot-critical",
        ),
    )


def build_live_certification_contract() -> tuple[str, ...]:
    return (
        "certification_id",
        "source",
        "source_type",
        "official_endpoint_or_surface",
        "timestamp",
        "tested_commit_sha",
        "request_class",
        "request_identifier",
        "http_status",
        "response_contract",
        "raw_evidence_id",
        "integrity_digest",
        "expected_semantics",
        "observed_semantics",
        "result",
        "failure_classification",
        "revalidation_due",
    )


def evaluate_source_freshness(*, certified_at: datetime | None, policy: FreshnessPolicy, expired: bool = False) -> str:
    if policy is FreshnessPolicy.STALE:
        return "STALE"
    if certified_at is None:
        return "UNKNOWN"
    if certified_at.tzinfo is None:
        raise ValueError("certified_at must be timezone-aware")
    if expired:
        return "EXPIRED"
    if policy is FreshnessPolicy.REVALIDATE_BEFORE_USE:
        return "REVALIDATE_BEFORE_USE"
    if policy is FreshnessPolicy.REVALIDATE_ON_CHANGE:
        return "REVALIDATE_ON_CHANGE"
    return "REVALIDATE_ON_EXPIRY"


def evaluate_source_contract_drift(
    *,
    source_id: str,
    source_name: str,
    expected_fields: tuple[str, ...],
    observed_fields: tuple[str, ...],
    observed_at: datetime,
    evidence_id: str | None = None,
) -> SourceContractDrift:
    missing = tuple(field for field in expected_fields if field not in observed_fields)
    unexpected = tuple(field for field in observed_fields if field not in expected_fields)
    semantic_changes = ()
    status = SourceCertificationStatus.CERTIFIED if not missing and not unexpected else SourceCertificationStatus.CONTRACT_FAIL
    return SourceContractDrift(source_id, source_name, status, missing, unexpected, semantic_changes, observed_at, evidence_id)


def build_compliance_gap_analysis() -> tuple[tuple[str, str, str, str, str, str, str], ...]:
    return (
        ("LEGAL-001", "Brazil", "email campaign", "published corporate contact", "current policy requires legal review input", "legal review and campaign policy version", "YES"),
        ("LEGAL-002", "Brazil", "pilot batch", "professional registration status", "current policy requires fresh external certification", "CFO/CRO current status lookup", "YES"),
        ("LEGAL-003", "Brazil", "any outbound contact", "suppressed contacts", "suppression controls are internal but external approval can override only manually", "campaign authorization", "YES"),
    )


def build_campaign_compliance_policy(
    *,
    policy_id: str = "policy:commercial-pilot:v1",
    version: str = "v1",
    jurisdiction: str = "BR",
    channel: str = "email",
) -> CampaignCompliancePolicy:
    return CampaignCompliancePolicy(
        policy_id,
        version,
        jurisdiction,
        channel,
        (ContactClass.COMPANY_GENERIC, ContactClass.BUSINESS_PERSONALIZED),
        target_rules=("single ICP", "bounded geography", "manual approval required"),
        contact_use_rules=("published != deliverable", "deliverable != authorized", "suppression wins"),
        suppression_rules=("contact suppression", "person suppression", "company/domain suppression"),
        required_certifications=("BrasilAPI CNPJ", "SERPRO", "CFO/CRO"),
        authorization_authority="campaign owner and compliance reviewer",
    )


def build_live_certification_matrix() -> tuple[LiveCertificationRecord, ...]:
    now = None
    blocker = "live network unavailable in this local environment"
    return (
        LiveCertificationRecord("BrasilAPI CNPJ v1", "acquisition", "live-network", False, False, None, now, "revalidate on live network access", blocker),
        LiveCertificationRecord("SERPRO transparency page", "company enrichment", "live-network", False, False, None, now, "revalidate on source change", blocker),
        LiveCertificationRecord("DNS/HTTP contact path", "contact validation", "live-network", False, False, None, now, "revalidate on source or contact-page change", blocker),
        LiveCertificationRecord("CRO/CFO registration", "professional registration", "live-network", False, False, None, now, "revalidate on registry update", blocker),
    )


def default_compliance_blockers() -> tuple[ComplianceBlocker, ...]:
    return (
        ComplianceBlocker("CB-001", "campaign legal review", "campaign legal review remains unresolved"),
        ComplianceBlocker("CB-002", "jurisdiction-specific rules", "jurisdiction-specific send rules are not yet certified"),
        ComplianceBlocker("CB-003", "contact-use authorization", "explicit contact-use authorization is not yet documented"),
        ComplianceBlocker("CB-004", "suppression and opt-out", "suppression and opt-out handling is not yet certified"),
        ComplianceBlocker("CB-005", "send authorization", "send authorization remains separate from qualification"),
        ComplianceBlocker("CB-006", "retention", "retention and deletion policy still needs explicit owner"),
    )


def evaluate_send_ready_proof(
    *,
    evaluation_id: str,
    qualification_decision_id: str | None,
    contact_validation_id: str | None,
    contact_use_decision: ContactUseDecision | None,
    suppression_rule: SuppressionRule | None,
    certification_refs: tuple[str, ...],
    policy: CampaignCompliancePolicy,
    authorization: ManualAuthorizationRecord | None,
    inputs: SendReadyInputs,
    timestamp: datetime,
) -> SendReadyProof:
    assessment = evaluate_send_ready(inputs)
    authorization_ref = authorization.authorization_id if authorization is not None else None
    if authorization is not None and not authorization.active:
        assessment = SendReadyAssessment(SendReadyState.COMPLIANCE_BLOCKED, False, ("authorization inactive",), ("authorization inactive",))
    suppression_decision_id = suppression_rule.suppression_id if suppression_rule is not None else None
    proof = SendReadyProof(
        proof_id=f"proof:{evaluation_id}",
        evaluation_id=evaluation_id,
        qualification_decision_id=qualification_decision_id,
        contact_validation_id=contact_validation_id,
        contact_use_decision_id=contact_use_decision.decision_id if contact_use_decision is not None else None,
        suppression_decision_id=suppression_decision_id,
        certification_refs=certification_refs,
        policy_version=policy.version,
        authorization_ref=authorization_ref,
        result=assessment,
        timestamp=timestamp,
    )
    return proof


def build_certification_matrix() -> tuple[tuple[str, str, str, str, str, str], ...]:
    return (
        ("BrasilAPI CNPJ v1", "company acquisition", "PRODUCT_CRITICAL", "CERTIFIED_WITH_LIMITATIONS", "", "live source certification and replay required"),
        ("SERPRO transparency page", "company enrichment", "PRODUCT_CRITICAL", "SOURCE_UNAVAILABLE", "", "official portal capture pending live access"),
        ("CRO/CFO registry", "professional registration", "CAMPAIGN_CRITICAL", "BLOCKED_HUMAN_VERIFICATION", "", "manual verification boundary required"),
        ("DNS/HTTP contact path", "contact publication", "OPTIONAL_BREADTH", "OPTIONAL_NOT_RUN", "", "promotion not required for current gate"),
    )


def assess_contact_use(
    *,
    contact_id: str,
    relationship_id: str,
    campaign_policy_version: str,
    publication_verified: bool = False,
    compliance_decision: ComplianceDecision | None = None,
    suppression_rules: tuple[SuppressionRule, ...] = (),
    evidence_refs: tuple[str, ...] = (),
    reviewed_at: datetime | None = None,
) -> ContactUseDecision:
    if any(not item.strip() for item in (contact_id, relationship_id, campaign_policy_version)):
        raise ValueError("contact_id, relationship_id, and campaign_policy_version must be non-blank")
    if reviewed_at is not None and reviewed_at.tzinfo is None:
        raise ValueError("reviewed_at must be timezone-aware")
    active_suppression = next((rule for rule in suppression_rules if rule.active and rule.subject_id == contact_id), None)
    if active_suppression is not None:
        return ContactUseDecision(
            f"contact-use:{contact_id}:{campaign_policy_version}",
            contact_id,
            relationship_id,
            campaign_policy_version,
            ContactUseState.SUPPRESSED,
            "SUPPRESSED",
            evidence_refs,
            reviewed_at,
            "automatic",
        )
    if compliance_decision is not None:
        if compliance_decision.decision is ContactUseState.BLOCKED:
            return ContactUseDecision(
                f"contact-use:{contact_id}:{campaign_policy_version}",
                contact_id,
                relationship_id,
                campaign_policy_version,
                ContactUseState.BLOCKED,
                compliance_decision.reason_code,
                evidence_refs + compliance_decision.evidence_refs,
                reviewed_at or compliance_decision.reviewed_at,
                compliance_decision.authority,
            )
        if compliance_decision.decision is ContactUseState.REVIEW_REQUIRED:
            return ContactUseDecision(
                f"contact-use:{contact_id}:{campaign_policy_version}",
                contact_id,
                relationship_id,
                campaign_policy_version,
                ContactUseState.REVIEW_REQUIRED,
                compliance_decision.reason_code,
                evidence_refs + compliance_decision.evidence_refs,
                reviewed_at or compliance_decision.reviewed_at,
                compliance_decision.authority,
            )
        if compliance_decision.decision is ContactUseState.ALLOWED_BY_POLICY and publication_verified:
            return ContactUseDecision(
                f"contact-use:{contact_id}:{campaign_policy_version}",
                contact_id,
                relationship_id,
                campaign_policy_version,
                ContactUseState.ALLOWED_BY_POLICY,
                "ALLOWED_BY_POLICY",
                evidence_refs + compliance_decision.evidence_refs,
                reviewed_at or compliance_decision.reviewed_at,
                compliance_decision.authority,
            )
    if publication_verified:
        return ContactUseDecision(
            f"contact-use:{contact_id}:{campaign_policy_version}",
            contact_id,
            relationship_id,
            campaign_policy_version,
            ContactUseState.REVIEW_REQUIRED,
            "REVIEW_REQUIRED",
            evidence_refs,
            reviewed_at,
            "automatic",
        )
    return ContactUseDecision(
        f"contact-use:{contact_id}:{campaign_policy_version}",
        contact_id,
        relationship_id,
        campaign_policy_version,
        ContactUseState.UNKNOWN,
        "CONTACT_USE_UNKNOWN",
        evidence_refs,
        reviewed_at,
        "automatic",
    )


def evaluate_compliance_decision(
    *,
    subject_id: str,
    campaign_policy_version: str,
    legal_review_required: bool = False,
    suppressed: bool = False,
    certification_blocked: bool = False,
    evidence_refs: tuple[str, ...] = (),
    reviewed_at: datetime | None = None,
) -> ComplianceDecision:
    if any(not item.strip() for item in (subject_id, campaign_policy_version)):
        raise ValueError("subject_id and campaign_policy_version must be non-blank")
    if reviewed_at is not None and reviewed_at.tzinfo is None:
        raise ValueError("reviewed_at must be timezone-aware")
    if suppressed:
        return ComplianceDecision("compliance:block", subject_id, campaign_policy_version, ContactUseState.BLOCKED, "SUPPRESSED", evidence_refs, reviewed_at, None, "automatic")
    if certification_blocked or legal_review_required:
        return ComplianceDecision("compliance:review", subject_id, campaign_policy_version, ContactUseState.REVIEW_REQUIRED, "LEGAL_REVIEW_REQUIRED", evidence_refs, reviewed_at, None, "automatic")
    return ComplianceDecision("compliance:allow", subject_id, campaign_policy_version, ContactUseState.ALLOWED_BY_POLICY, "ALLOWED_BY_POLICY", evidence_refs, reviewed_at, None, "automatic")


def evaluate_pilot_readiness(
    *,
    operational_ready: bool,
    live_sources_certified: bool,
    send_ready: bool,
    policy_version_fixed: bool,
    suppression_ready: bool,
    review_path_ready: bool,
    audit_export_ready: bool,
    measurement_ready: bool,
    manual_authorization_required: bool = True,
    manual_authorization_granted: bool = False,
    compliance_decision: ComplianceDecision | None = None,
    contact_use_decision: ContactUseDecision | None = None,
    suppression_rules: tuple[SuppressionRule, ...] = (),
) -> CommercialPilotReadiness:
    blockers: list[str] = []
    if not operational_ready:
        blockers.append("operational_ready")
    if not live_sources_certified:
        blockers.append("live_sources_certified")
    if not send_ready:
        blockers.append("send_ready")
    if not policy_version_fixed:
        blockers.append("policy_version_fixed")
    if not suppression_ready:
        blockers.append("suppression_ready")
    if not review_path_ready:
        blockers.append("review_path_ready")
    if not audit_export_ready:
        blockers.append("audit_export_ready")
    if not measurement_ready:
        blockers.append("measurement_ready")
    if compliance_decision is not None and compliance_decision.decision is not ContactUseState.ALLOWED_BY_POLICY:
        blockers.append(compliance_decision.reason_code)
    if contact_use_decision is not None and contact_use_decision.decision is not ContactUseState.ALLOWED_BY_POLICY:
        blockers.append(contact_use_decision.reason_code)
    if any(rule.active for rule in suppression_rules):
        blockers.append("active_suppression_present")
    if blockers:
        return CommercialPilotReadiness(
            PilotReadinessState.NOT_READY,
            False,
            tuple(dict.fromkeys(blockers)),
            manual_authorization_required,
            (),
            contact_use_decision,
            compliance_decision,
            suppression_rules,
        )
    state = PilotReadinessState.READY_PENDING_MANUAL_AUTHORIZATION if manual_authorization_required and not manual_authorization_granted else PilotReadinessState.READY
    return CommercialPilotReadiness(
        state,
        state is PilotReadinessState.READY,
        (),
        manual_authorization_required,
        (),
        contact_use_decision,
        compliance_decision,
        suppression_rules,
    )


def evaluate_send_ready(inputs: SendReadyInputs) -> SendReadyAssessment:
    blockers = tuple(item.strip() for item in inputs.compliance_blockers if item.strip())
    if blockers:
        return SendReadyAssessment(
            SendReadyState.COMPLIANCE_BLOCKED,
            False,
            blockers,
            ("compliance blockers present",),
        )
    if inputs.review_required:
        return SendReadyAssessment(
            SendReadyState.REVIEW_REQUIRED,
            False,
            (),
            ("review required",),
        )
    missing: list[str] = []
    if not inputs.discovered:
        missing.append("discovered")
        return SendReadyAssessment(SendReadyState.DISCOVERED, False, (), tuple(missing))
    if not inputs.validated:
        missing.append("validated")
        return SendReadyAssessment(SendReadyState.VALIDATED, False, (), tuple(missing))
    if not inputs.qualified:
        missing.append("qualified")
        return SendReadyAssessment(SendReadyState.QUALIFIED, False, (), tuple(missing))
    if not inputs.compliance_cleared:
        missing.append("compliance_cleared")
        return SendReadyAssessment(SendReadyState.COMPLIANCE_PENDING, False, (), tuple(missing))
    if not inputs.live_certified:
        missing.append("live_certified")
        return SendReadyAssessment(SendReadyState.LIVE_CERTIFICATION_PENDING, False, (), tuple(missing))
    return SendReadyAssessment(SendReadyState.SEND_READY, True, (), ())


def _parse_optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise OperationalError(
            OperationalFailureClass.CONFIGURATION_ERROR,
            f"{name} must not be blank",
        )
    return text


def _parse_repository_path(value: str, name: str) -> Path:
    text = str(value).strip()
    if not text:
        raise OperationalError(
            OperationalFailureClass.CONFIGURATION_ERROR,
            f"{name} must not be blank",
        )
    if text == ":memory:":
        return Path(text)
    path = Path(text)
    if not path.is_absolute():
        raise OperationalError(
            OperationalFailureClass.CONFIGURATION_ERROR,
            f"{name} must be an absolute path or :memory:",
        )
    return path


def _parse_optional_path(value: Any, name: str) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise OperationalError(
            OperationalFailureClass.CONFIGURATION_ERROR,
            f"{name} must not be blank",
        )
    path = Path(text)
    if not path.is_absolute():
        raise OperationalError(
            OperationalFailureClass.CONFIGURATION_ERROR,
            f"{name} must be an absolute path",
        )
    return path


def _parse_optional_url(value: Any, name: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise OperationalError(
            OperationalFailureClass.CONFIGURATION_ERROR,
            f"{name} must not be blank",
        )
    parsed = urlsplit(text)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise OperationalError(
            OperationalFailureClass.CONFIGURATION_ERROR,
            f"{name} must be an absolute HTTP(S) URL without credentials",
        )
    return text


__all__ = [
    "CertificationScope",
    "CertificationResult",
    "CampaignCompliancePolicy",
    "ComplianceBlocker",
    "ComplianceDecision",
    "ConfigurationClassification",
    "ConfigurationField",
    "ContactUseDecision",
    "ContactUseState",
    "CommercialPilotReadiness",
    "FreshnessPolicy",
    "ManualAuthorizationRecord",
    "LiveSourceCertification",
    "LiveCertificationRecord",
    "OperationalConfiguration",
    "OperationalError",
    "OperationalEvent",
    "OperationalFailure",
    "OperationalFailureClass",
    "OperationalHealthReport",
    "OperationalRuntime",
    "OperationalTelemetrySnapshot",
    "ProcessHealth",
    "PilotReadinessState",
    "SendReadyProof",
    "SendReadyAssessment",
    "SendReadyInputs",
    "SendReadyState",
    "SourceAuthorityFact",
    "SourceAuthorityMapEntry",
    "SourceAuthorityScope",
    "SourceCertificationStatus",
    "SourceContractDrift",
    "SystemReadiness",
    "SystemReadinessReport",
    "SuppressionRule",
    "assess_contact_use",
    "build_campaign_compliance_policy",
    "build_compliance_gap_analysis",
    "build_certification_matrix",
    "build_external_certification_inventory",
    "build_live_certification_contract",
    "build_live_certification_matrix",
    "build_source_authority_map",
    "default_compliance_blockers",
    "evaluate_compliance_decision",
    "evaluate_pilot_readiness",
    "evaluate_send_ready_proof",
    "evaluate_source_contract_drift",
    "evaluate_source_freshness",
    "evaluate_send_ready",
]
