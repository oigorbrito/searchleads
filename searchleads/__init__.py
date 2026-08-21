"""SearchLeads evidence-preserving lead data foundation."""

from .contact_discovery import ContactAcquisitionError, ContactDiscoveryError, ContactDiscoveryResult, DiscoveredContact, OfficialPageContactSource, discover_contacts_from_html
from .contact_validation import ContactValidationDisposition, ContactValidationMethod, ContactValidationResult, validate_contact_from_official_evidence
from .person_discovery import OfficialPeopleSource, PersonAcquisitionError, PersonDiscoveryError, PersonDiscoveryResult, PersonRoleObservation, discover_person_roles_from_html
from .person_professional_contacts import ContactPointStore, PersonChannelExtraction, PublishedPersonChannel, build_person_contact_points, discover_person_professional_channels, persist_person_contact_points
from .person_entity_resolution import LabeledPersonPair, PersonMatchFeatures, PersonRecord, PersonResolutionDecision, PersonResolutionDisposition, PersonResolutionMetrics, compare_person_features, evaluate_person_resolution, resolve_person_pair
from .role_persistence import ROLE_SCHEMA_VERSION, ensure_professional_role_schema, get_professional_role, save_professional_role
from .qualification import CriterionEvaluation, CriterionOperator, QualificationCriterion, QualificationPolicy, QualificationResult, criterion_matches, lead_from_qualification, qualify_company
from .qualification_signals import QualificationInputType, QualificationInput, SignalCriterionEvaluation, SignalQualificationResult, inputs_from_evidence, qualify_company_inputs
from .qualification_field_canonicalization import QualificationFieldCanonicalizationResult, canonicalize_selected_company_fields, persist_qualification_field_canonicalization
from .expansion import ExpansionItemResult, ExpansionRunResult, expand_cnpj_seeds
from .company_enrichment import CompanyEnrichmentAcquisitionError, CompanyEnrichmentError, CompanyEnrichmentResult, OfficialCompanyLocationSource, extract_official_location_facts
from .repeatable_discovery import DiscoveredCompanySeed, RECIPE_ID, RepeatableDiscoveryResult, SerproOfficeDirectorySource, discover_serpro_office_seeds
from .selective_review import ReviewItem, ReviewKind, ReviewPriority, build_review_queue, review_company_match, review_conflict, review_contact, review_person_match, review_person_resolution, review_qualification
from .lead_export import LeadExportBundle, export_csv, export_json, to_export_dict
from .gap_automation import ActionDisposition, ActionKind, AutomationAction, AutomationPlan, Gap, GapKind, GapRequirements, detect_gaps, plan_gap_actions
from .gap_execution import ActionExecutionRecord, ActionExecutionStatus, GapCycleResult, GapLifecycleHooks, GapRunResult, GapRuntimeState, execute_and_reassess_gap_cycle, execute_gap_plan, run_gap_automation_until_stable
from .acceptance import AcceptanceResult, run_acceptance_fixture
from .icp_decision_support import ICPDimension, ICPReadinessSnapshot, ReadinessLevel, DimensionAssessment, ICPDecisionSupportReport, acceptance_fixture_snapshot, qualification_bridge_snapshot, qualification_field_canonicalization_snapshot, registry_size_signal_snapshot, assess_icp_readiness
from .metrics import ContactMetrics, DiscoveryMetrics, EnrichmentMetrics, EntityResolutionMetrics, MetricAvailability, MetricValue, OperationalMetrics, QualificationMetrics, compute_contact_metrics, compute_discovery_metrics, compute_enrichment_metrics, compute_entity_resolution_metrics, compute_operational_metrics, compute_qualification_metrics
from .domain import CandidateFact, CanonicalFact, Company, Conflict, ConflictStatus, ContactKind, ContactPoint, ContactStatus, DecisionClass, EntityRef, EntityType, Evidence, Lead, LeadStatus, Person, ProfessionalRole, Provenance, Source, SourceType
from .brasilapi import BASE_URL as BRASILAPI_BASE_URL, BrasilAPIAcquisitionError, BrasilAPIError, BrasilAPIIngestionResult, BrasilAPIPayloadError, BrasilAPISource
from .entity_resolution import BlockingMetrics, CompanyRecord, EvaluationMetrics, LabeledPair, MatchDecision, MatchFeatures, ResolutionDisposition, Strategy, TriageDecision, blocking_keys, compare_features, evaluate, evaluate_blocking, evaluate_blocking_corpus, is_blocked_candidate, resolve_pair, triage_pair
from .field_fusion import FusionOutcome, FusionPolicy, FusionStatus, ValueSupport, fuse_candidate_facts, fuse_persisted_candidates, naive_majority_value, persist_fusion_outcome
from .normalization import NormalizationError, NormalizationResult, NormalizationStatus, normalize_candidate_fact, normalize_candidate_facts, normalize_persisted_candidate
from .persistence import IdentityCollisionError, MissingReferenceError, PersistenceError, SCHEMA_VERSION, SQLiteLeadStore

__all__ = [name for name in globals() if not name.startswith("_")]
