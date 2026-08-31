from __future__ import annotations

from dataclasses import asdict, dataclass
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
class OperationalConfiguration:
    repository_path: Path
    backup_path: Path | None = None
    runtime_source_id: str | None = None
    runtime_source_url: str | None = None
    secret_token: str | None = None
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
    "ComplianceBlocker",
    "ConfigurationClassification",
    "ConfigurationField",
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
    "SendReadyAssessment",
    "SendReadyInputs",
    "SendReadyState",
    "SystemReadiness",
    "SystemReadinessReport",
    "build_live_certification_matrix",
    "default_compliance_blockers",
    "evaluate_send_ready",
]
