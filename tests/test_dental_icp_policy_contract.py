from dataclasses import replace
import json
import pytest

from searchleads.qualification_policy import APPROVED_DENTAL_ICP_POLICY_V1, DentalICPPolicyContractV1


def test_contract_is_exact_documented_vertical_scope():
    p = APPROVED_DENTAL_ICP_POLICY_V1
    assert p.policy_id == "dental-facial-surgery-education-br-v1"
    assert p.decision_basis == "BUSINESS_REQUIREMENT_USER_DEFINED_2026_08_21"
    assert p.primary_commercial_entity == "PERSON"
    assert p.country == "BR"
    assert p.default_offer_track == "CEOF_SPECIALIZATION"
    assert p.target_profession == "DENTISTRY"
    assert p.company_size_applicable is False


def test_documented_professional_groups_and_topics_are_preserved():
    p = APPROVED_DENTAL_ICP_POLICY_V1
    assert p.eligible_professional_groups == (
        "GENERAL_DENTIST", "DENTAL_SPECIALIST", "BUCOMAXILLOFACIAL", "HOF_OR_FACIAL_ACTIVITY"
    )
    assert p.core_topics == ("BLEFAROPLASTIA", "LIP_LIFT", "LIFTING_FACIAL", "FRONTOPLASTIA")


def test_geography_and_contact_semantics_are_conservative():
    p = APPROVED_DENTAL_ICP_POLICY_V1
    assert p.geography_default == "BRAZIL_WIDE"
    assert p.geography_filters == ("MACRO_REGION", "STATE")
    assert p.contact_required_by_default is False
    assert p.validated_contact_may_be_required_by_campaign is True
    assert p.missing_required_filter_result == "UNKNOWN_REVIEW"


def test_missing_intent_and_conflicts_never_become_positive_or_negative_by_default():
    p = APPROVED_DENTAL_ICP_POLICY_V1
    assert p.missing_intent_result == "UNKNOWN"
    assert p.unresolved_required_conflict_result == "UNKNOWN_REVIEW"


def test_offer_track_regulatory_split_matches_documented_policy():
    p = APPROVED_DENTAL_ICP_POLICY_V1
    assert p.ceof_specialization_missing_ceof_result == "NOT_REQUIRED_FOR_DEFAULT_TRACK"
    assert p.complementary_exclusive_ceof_missing_ceof_result == "UNKNOWN_REVIEW"
    assert p.complementary_exclusive_ceof_known_non_ceof_result == "NOT_QUALIFIED_EXCLUDE"


def test_fit_intent_priority_vocabularies_are_versioned():
    p = APPROVED_DENTAL_ICP_POLICY_V1
    assert p.fit_levels == ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
    assert p.intent_levels == ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
    assert p.priority_levels == ("P1", "P2", "P3", "REVIEW", "EXCLUDE")


def test_serialization_is_deterministic_and_round_trips():
    p = APPROVED_DENTAL_ICP_POLICY_V1
    first = p.to_json()
    second = p.to_json()
    assert first == second
    assert json.loads(first) == json.loads(json.dumps(p.to_dict()))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"policy_id": "other"},
        {"version": "2"},
        {"primary_commercial_entity": "COMPANY"},
        {"country": "US"},
        {"company_size_applicable": True},
        {"contact_required_by_default": True},
        {"missing_intent_result": "LOW"},
        {"unresolved_required_conflict_result": "QUALIFIED"},
    ],
)
def test_contract_rejects_mutations_that_contradict_documented_v1(kwargs):
    with pytest.raises(ValueError):
        replace(APPROVED_DENTAL_ICP_POLICY_V1, **kwargs)
