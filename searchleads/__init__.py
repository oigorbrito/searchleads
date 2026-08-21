"""SearchLeads evidence-preserving lead data foundation."""

from .contact_discovery import ContactAcquisitionError, ContactDiscoveryError, ContactDiscoveryResult, DiscoveredContact, OfficialPageContactSource, discover_contacts_from_html
from .contact_validation import ContactValidationDisposition, ContactValidationMethod, ContactValidationResult, validate_contact_from_official_evidence
from .person_discovery import OfficialPeopleSource, PersonAcquisitionError, PersonDiscoveryError, PersonDiscoveryResult, PersonRoleObservation, discover_person_roles_from_html
from .role_persistence import ROLE_SCHEMA_VERSION, ensure_professional_role_schema, get_professional_role, save_professional_role
from .qualification import CriterionEvaluation, CriterionOperator, QualificationCriterion, QualificationPolicy, QualificationResult, lead_from_qualification, qualify_company
from .expansion import ExpansionItemResult, ExpansionRunResult, expand_cnpj_seeds
from .company_enrichment import CompanyEnrichmentAcquisitionError, CompanyEnrichmentError, CompanyEnrichmentResult, OfficialCompanyLocationSource, extract_official_location_facts
from .repeatable_discovery import DiscoveredCompanySeed, RECIPE_ID, RepeatableDiscoveryResult, SerproOfficeDirectorySource, discover_serpro_office_seeds
from .domain import CandidateFact, CanonicalFact, Company, Conflict, ConflictStatus, ContactKind, ContactPoint, ContactStatus, DecisionClass, EntityRef, EntityType, Evidence, Lead, LeadStatus, Person, ProfessionalRole, Provenance, Source, SourceType
from .brasilapi import BASE_URL as BRASILAPI_BASE_URL, BrasilAPIAcquisitionError, BrasilAPIError, BrasilAPIIngestionResult, BrasilAPIPayloadError, BrasilAPISource
from .entity_resolution import BlockingMetrics, CompanyRecord, EvaluationMetrics, LabeledPair, MatchDecision, MatchFeatures, ResolutionDisposition, Strategy, TriageDecision, blocking_keys, compare_features, evaluate, evaluate_blocking, evaluate_blocking_corpus, is_blocked_candidate, resolve_pair, triage_pair
from .field_fusion import FusionOutcome, FusionPolicy, FusionStatus, ValueSupport, fuse_candidate_facts, fuse_persisted_candidates, naive_majority_value, persist_fusion_outcome
from .normalization import NormalizationError, NormalizationResult, NormalizationStatus, normalize_candidate_fact, normalize_candidate_facts, normalize_persisted_candidate
from .persistence import IdentityCollisionError, MissingReferenceError, PersistenceError, SCHEMA_VERSION, SQLiteLeadStore

__all__ = [name for name in globals() if not name.startswith("_")]
