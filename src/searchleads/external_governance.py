from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GateAuthority(StrEnum):
    ENGINEERING = "ENGINEERING"
    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    LEGAL_REVIEW = "LEGAL_REVIEW"
    CAMPAIGN_OWNER = "CAMPAIGN_OWNER"


class GateDecision(StrEnum):
    SATISFIED = "SATISFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    NOT_REQUIRED = "NOT_REQUIRED"


@dataclass(frozen=True, slots=True)
class AuthorityReference:
    reference_id: str
    publisher: str
    title: str
    locator: str
    jurisdiction: str
    supports: tuple[str, ...]
    observed_date: str

    def __post_init__(self) -> None:
        values = (
            self.reference_id,
            self.publisher,
            self.title,
            self.locator,
            self.jurisdiction,
            self.observed_date,
        )
        if any(not value.strip() for value in values):
            raise ValueError("authority reference fields must not be blank")
        if not self.supports or any(not item.strip() for item in self.supports):
            raise ValueError("supports must contain non-blank facts")


@dataclass(frozen=True, slots=True)
class ExternalGateRequirement:
    gate_id: str
    subject: str
    authority: GateAuthority
    decision: GateDecision
    reason_code: str
    required_evidence: tuple[str, ...]
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if any(not value.strip() for value in (self.gate_id, self.subject, self.reason_code)):
            raise ValueError("gate fields must not be blank")
        if any(not item.strip() for item in self.required_evidence):
            raise ValueError("required_evidence must not contain blanks")
        if any(not item.strip() for item in self.authority_refs):
            raise ValueError("authority_refs must not contain blanks")


@dataclass(frozen=True, slots=True)
class LegalReviewPacket:
    packet_id: str
    jurisdiction: str
    processing_purpose: str
    contact_class: str
    channel: str
    decision: GateDecision
    reason_code: str
    questions_for_reviewer: tuple[str, ...]
    authority_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.decision is GateDecision.SATISFIED:
            raise ValueError("engineering cannot self-approve the legal review packet")
        if not self.questions_for_reviewer:
            raise ValueError("legal review packet must contain reviewer questions")


def build_authority_references(*, observed_date: str = "2026-09-01") -> tuple[AuthorityReference, ...]:
    return (
        AuthorityReference(
            "AUTH-LGPD-001",
            "Presidencia da Republica / Planalto",
            "Lei 13.709/2018 - LGPD, texto compilado",
            "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm",
            "BR",
            (
                "Art. 6 requires purpose, adequacy and necessity among the processing principles",
                "Art. 7 lists legal bases and includes legitimate interest in item IX",
                "Art. 18 establishes data-subject rights against the controller",
            ),
            observed_date,
        ),
        AuthorityReference(
            "AUTH-ANPD-001",
            "Autoridade Nacional de Protecao de Dados",
            "Guia Orientativo - Hipoteses Legais de Tratamento de Dados Pessoais - Legitimo Interesse",
            "https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_hipoteses_legais_tratamento_de_dados_pessoais_legitimo_interesse",
            "BR",
            (
                "legitimate-interest analysis is contextual and must consider purpose, necessity, safeguards and data-subject expectations",
                "engineering evidence does not substitute a controller legal decision",
            ),
            observed_date,
        ),
        AuthorityReference(
            "AUTH-CFO-001",
            "Conselho Federal de Odontologia",
            "Consulta de Profissionais",
            "https://website.cfo.org.br/busca-profissionais/",
            "BR",
            (
                "CFO publishes an official consultation surface for dental professionals",
                "current individual registration status still requires a person-specific lookup",
            ),
            observed_date,
        ),
        AuthorityReference(
            "AUTH-SERPRO-001",
            "Servico Federal de Processamento de Dados - SERPRO",
            "Consulta CNPJ - Servico Serpro API",
            "https://www.serpro.gov.br/menu/suporte/css",
            "BR",
            (
                "SERPRO offers an official Consulta CNPJ API service",
                "the service is a distinct authenticated/contracted source and is not the SearchLeads transparency-page enrichment path",
            ),
            observed_date,
        ),
    )


def build_external_gate_requirements() -> tuple[ExternalGateRequirement, ...]:
    return (
        ExternalGateRequirement(
            "EXT-BRASILAPI-001",
            "BrasilAPI CNPJ product source",
            GateAuthority.EXTERNAL_SOURCE,
            GateDecision.REVIEW_REQUIRED,
            "SOURCE_CERTIFIED_WITH_LIMITATIONS_REVALIDATE_BEFORE_USE",
            ("fresh response evidence", "response-shape validation", "integrity digest"),
        ),
        ExternalGateRequirement(
            "EXT-SERPRO-001",
            "SERPRO transparency enrichment path",
            GateAuthority.ENGINEERING,
            GateDecision.NOT_REQUIRED,
            "NOT_ON_MINIMUM_COMMERCIAL_CRITICAL_PATH",
            (),
            ("AUTH-SERPRO-001",),
        ),
        ExternalGateRequirement(
            "EXT-CFO-001",
            "CFO/CRO professional registration status",
            GateAuthority.HUMAN_REVIEW,
            GateDecision.REVIEW_REQUIRED,
            "PERSON_SPECIFIC_CURRENT_STATUS_REQUIRED",
            ("professional identifier", "current consultation result", "capture timestamp", "evidence digest"),
            ("AUTH-CFO-001",),
        ),
        ExternalGateRequirement(
            "LEGAL-001",
            "outbound dental commercial contact policy",
            GateAuthority.LEGAL_REVIEW,
            GateDecision.REVIEW_REQUIRED,
            "CONTROLLER_LEGAL_BASIS_AND_BALANCING_DECISION_REQUIRED",
            ("campaign purpose", "contact class", "channel", "minimization rationale", "suppression/opt-out controls", "retention policy"),
            ("AUTH-LGPD-001", "AUTH-ANPD-001"),
        ),
        ExternalGateRequirement(
            "AUTH-CAMPAIGN-001",
            "campaign-specific send authorization",
            GateAuthority.CAMPAIGN_OWNER,
            GateDecision.BLOCKED,
            "MANUAL_AUTHORIZATION_NOT_GRANTED",
            ("approved policy version", "approved bounded audience", "authorization timestamp", "authorizer identity"),
        ),
    )


def build_legal_review_packet() -> LegalReviewPacket:
    return LegalReviewPacket(
        "legal-review:commercial-pilot:v1",
        "BR",
        "bounded B2B dental lead outreach",
        "published corporate or business-personalized contact",
        "email",
        GateDecision.REVIEW_REQUIRED,
        "LEGAL_REVIEW_REQUIRED",
        (
            "Which LGPD legal basis is approved for this exact campaign purpose and contact class?",
            "If legitimate interest is relied upon, is the documented purpose/necessity/balancing analysis sufficient for the controller?",
            "What notice, opposition, suppression and opt-out controls are required before first contact?",
            "What retention/deletion period is approved for contact data and raw evidence?",
            "Are any contact classes, source classes or professional-registration uses prohibited or review-only?",
        ),
        ("AUTH-LGPD-001", "AUTH-ANPD-001"),
    )


def critical_path_gate_ids() -> tuple[str, ...]:
    return tuple(
        gate.gate_id
        for gate in build_external_gate_requirements()
        if gate.decision is not GateDecision.NOT_REQUIRED
    )


__all__ = [
    "AuthorityReference",
    "ExternalGateRequirement",
    "GateAuthority",
    "GateDecision",
    "LegalReviewPacket",
    "build_authority_references",
    "build_external_gate_requirements",
    "build_legal_review_packet",
    "critical_path_gate_ids",
]
