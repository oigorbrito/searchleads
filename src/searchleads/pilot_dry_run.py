from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from typing import Any

from searchleads.operational import (
    CampaignCompliancePolicy,
    ComplianceSignoffRecord,
    ContactClass,
    ContactUseState,
    HumanVerificationRecord,
    HumanVerificationStatus,
    LegalSignoffDecision,
    ManualAuthorizationRecord,
    SendReadyInputs,
    SendReadyProof,
    SendReadyState,
    SuppressionRule,
    build_campaign_compliance_policy,
    evaluate_send_ready_proof,
)


@dataclass(frozen=True, slots=True)
class PilotDryRunCandidate:
    candidate_id: str
    company_name: str
    cnpj: str | None
    person_name: str | None
    cro_number: str | None
    contact_email: str | None
    contact_class: ContactClass
    er_company_status: str  # AUTO_MATCH, REVIEW
    er_person_status: str   # AUTO_MATCH, REVIEW, N/A
    qualified: bool
    contact_validated: bool
    professional_verification: HumanVerificationRecord | None
    is_suppressed: bool


@dataclass(frozen=True, slots=True)
class PilotDryRunMetrics:
    total_candidates: int
    auto_match_company: int
    company_review: int
    person_review: int
    qualified: int
    contact_validated: int
    compliance_approved: int
    suppressed: int
    send_ready: int
    blocked: int
    manual_review_required: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AuditExportRecord:
    candidate_id: str
    company_name: str
    cnpj: str | None
    contact_email: str | None
    contact_class: str
    er_status: str
    qualification_status: str
    professional_verification_status: str
    compliance_status: str
    proof_id: str | None
    proof_digest: str | None
    final_gate_state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_synthetic_pilot_dataset(now: datetime) -> tuple[PilotDryRunCandidate, ...]:
    return (
        # 1. Clean SEND_READY candidate
        PilotDryRunCandidate(
            candidate_id="cand-001",
            company_name="Odonto Smile Ltda",
            cnpj="33683111000280",
            person_name="Dr. Carlos Silva",
            cro_number="CRO-SP-12345",
            contact_email="contato@odontosmile.com.br",
            contact_class=ContactClass.COMPANY_GENERIC,
            er_company_status="AUTO_MATCH",
            er_person_status="AUTO_MATCH",
            qualified=True,
            contact_validated=True,
            professional_verification=HumanVerificationRecord(
                verification_id="hvr-001",
                registration_number="CRO-SP-12345",
                council="CRO-SP",
                subject_identity_ref="person:carlos",
                observed_status=HumanVerificationStatus.VERIFIED,
                verified_at=now,
                source_reference="https://crosp.org.br/consulta",
                evidence_refs=("ev-cro-1",),
                reviewer_authority="operator:jules",
            ),
            is_suppressed=False,
        ),
        # 2. Ambiguous ER company candidate
        PilotDryRunCandidate(
            candidate_id="cand-002",
            company_name="Clinica Odontologica Implante",
            cnpj=None,
            person_name=None,
            cro_number=None,
            contact_email="contato@implante.com.br",
            contact_class=ContactClass.COMPANY_GENERIC,
            er_company_status="REVIEW",
            er_person_status="N/A",
            qualified=True,
            contact_validated=True,
            professional_verification=None,
            is_suppressed=False,
        ),
        # 3. Suppressed contact candidate
        PilotDryRunCandidate(
            candidate_id="cand-003",
            company_name="Dentistas Associados",
            cnpj="00000000000191",
            person_name="Dra. Ana Santos",
            cro_number="CRO-SP-67890",
            contact_email="optout@dentistas.com.br",
            contact_class=ContactClass.BUSINESS_PERSONALIZED,
            er_company_status="AUTO_MATCH",
            er_person_status="AUTO_MATCH",
            qualified=True,
            contact_validated=True,
            professional_verification=HumanVerificationRecord(
                verification_id="hvr-003",
                registration_number="CRO-SP-67890",
                council="CRO-SP",
                subject_identity_ref="person:ana",
                observed_status=HumanVerificationStatus.VERIFIED,
                verified_at=now,
                source_reference="https://crosp.org.br/consulta",
                evidence_refs=("ev-cro-3",),
                reviewer_authority="operator:jules",
            ),
            is_suppressed=True,
        ),
        # 4. Pending professional verification candidate
        PilotDryRunCandidate(
            candidate_id="cand-004",
            company_name="Sorriso Perfeito",
            cnpj="12ABC34501DE67",
            person_name="Dr. Roberto Lima",
            cro_number="CRO-RJ-99999",
            contact_email="roberto@sorrisoperfeito.com.br",
            contact_class=ContactClass.BUSINESS_PERSONALIZED,
            er_company_status="AUTO_MATCH",
            er_person_status="AUTO_MATCH",
            qualified=True,
            contact_validated=True,
            professional_verification=HumanVerificationRecord(
                verification_id="hvr-004",
                registration_number="CRO-RJ-99999",
                council="CRO-RJ",
                subject_identity_ref="person:roberto",
                observed_status=HumanVerificationStatus.IN_PROGRESS,
                verified_at=now,
                source_reference="https://crorj.org.br/consulta",
                evidence_refs=("ev-cro-4",),
                reviewer_authority="operator:jules",
            ),
            is_suppressed=False,
        ),
        # 5. Unqualified candidate
        PilotDryRunCandidate(
            candidate_id="cand-005",
            company_name="Laboratorio Dental Pro",
            cnpj="99999999000188",
            person_name=None,
            cro_number=None,
            contact_email="vendas@labpro.com.br",
            contact_class=ContactClass.COMPANY_GENERIC,
            er_company_status="AUTO_MATCH",
            er_person_status="N/A",
            qualified=False,
            contact_validated=True,
            professional_verification=None,
            is_suppressed=False,
        ),
    )


def run_pilot_dry_run(
    dataset: tuple[PilotDryRunCandidate, ...],
    policy: CampaignCompliancePolicy,
    signoff: ComplianceSignoffRecord | None,
    authorization: ManualAuthorizationRecord | None,
    now: datetime,
) -> tuple[PilotDryRunMetrics, tuple[AuditExportRecord, ...]]:
    total = len(dataset)
    auto_match_co = 0
    co_review = 0
    pe_review = 0
    qualified_cnt = 0
    contact_val_cnt = 0
    compliance_app_cnt = 0
    suppressed_cnt = 0
    send_ready_cnt = 0
    blocked_cnt = 0
    manual_review_cnt = 0

    audit_records: list[AuditExportRecord] = []

    for cand in dataset:
        if cand.er_company_status == "AUTO_MATCH":
            auto_match_co += 1
        elif cand.er_company_status == "REVIEW":
            co_review += 1
            manual_review_cnt += 1

        if cand.er_person_status == "REVIEW":
            pe_review += 1
            manual_review_cnt += 1

        if cand.qualified:
            qualified_cnt += 1
        if cand.contact_validated:
            contact_val_cnt += 1

        if cand.is_suppressed:
            suppressed_cnt += 1

        # Check professional verification requirements
        prof_ok = True
        if cand.contact_class == ContactClass.BUSINESS_PERSONALIZED:
            if (
                cand.professional_verification is None
                or not cand.professional_verification.is_valid_active
            ):
                prof_ok = False
                manual_review_cnt += 1

        # Evaluate send ready inputs
        blockers: list[str] = []
        if cand.er_company_status != "AUTO_MATCH":
            blockers.append("Company ER review required")
        if cand.er_person_status == "REVIEW":
            blockers.append("Person ER review required")
        if cand.is_suppressed:
            blockers.append("Contact is suppressed")
        if not prof_ok:
            blockers.append("Professional verification missing or pending")

        compliance_cleared = (len(blockers) == 0)
        if compliance_cleared:
            compliance_app_cnt += 1

        inputs = SendReadyInputs(
            discovered=True,
            validated=cand.contact_validated,
            qualified=cand.qualified,
            compliance_cleared=compliance_cleared,
            live_certified=True,
            compliance_blockers=tuple(blockers),
        )

        suppression_rule = (
            SuppressionRule(
                suppression_id=f"sup:{cand.candidate_id}",
                scope="contact",
                subject_id=cand.candidate_id,
                reason="Opt-out requested",
            )
            if cand.is_suppressed
            else None
        )

        proof = evaluate_send_ready_proof(
            evaluation_id=f"eval:{cand.candidate_id}",
            qualification_decision_id=f"qual:{cand.candidate_id}" if cand.qualified else None,
            contact_validation_id=f"val:{cand.candidate_id}" if cand.contact_validated else None,
            contact_use_decision=None,
            suppression_rule=suppression_rule,
            certification_refs=("cert-brasilapi-1",),
            policy=policy,
            authorization=authorization,
            inputs=inputs,
            timestamp=now,
            compliance_signoff=signoff,
        )

        if proof.result.ready:
            send_ready_cnt += 1
        else:
            blocked_cnt += 1

        audit_records.append(
            AuditExportRecord(
                candidate_id=cand.candidate_id,
                company_name=cand.company_name,
                cnpj=cand.cnpj,
                contact_email=cand.contact_email,
                contact_class=cand.contact_class.value,
                er_status=f"co:{cand.er_company_status}|pe:{cand.er_person_status}",
                qualification_status="QUALIFIED" if cand.qualified else "UNQUALIFIED",
                professional_verification_status=(
                    cand.professional_verification.observed_status.value
                    if cand.professional_verification
                    else "N/A"
                ),
                compliance_status="CLEARED" if compliance_cleared else "BLOCKED",
                proof_id=proof.proof_id,
                proof_digest=proof.integrity_digest,
                final_gate_state=proof.result.state.value,
            )
        )

    metrics = PilotDryRunMetrics(
        total_candidates=total,
        auto_match_company=auto_match_co,
        company_review=co_review,
        person_review=pe_review,
        qualified=qualified_cnt,
        contact_validated=contact_val_cnt,
        compliance_approved=compliance_app_cnt,
        suppressed=suppressed_cnt,
        send_ready=send_ready_cnt,
        blocked=blocked_cnt,
        manual_review_required=manual_review_cnt,
    )

    return metrics, tuple(audit_records)
