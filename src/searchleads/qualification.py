from __future__ import annotations

from dataclasses import dataclass

ICP_UNDEFINED = "ICP_UNDEFINED"
NOT_EVALUATED = "NOT_EVALUATED"
WU11_BLOCKED = "BLOCKED_ICP_UNDEFINED"


@dataclass(frozen=True, slots=True)
class QualificationAssessment:
    company_id: str
    state: str
    reason: str


def qualification_without_icp(company_id: str) -> QualificationAssessment:
    if not isinstance(company_id, str) or not company_id.strip():
        raise ValueError("company_id must be non-empty text")
    return QualificationAssessment(
        company_id=company_id,
        state=NOT_EVALUATED,
        reason=ICP_UNDEFINED,
    )


def wu11_status() -> str:
    return WU11_BLOCKED
