from dataclasses import replace
import pytest
from searchleads.dental_discovery import *
from searchleads.qualification_policy import APPROVED_DENTAL_ICP_POLICY_V1


def obs(i, title, snippet="", url=None, evidence=None):
    return PublicSearchObservation(f"o{i}", url or f"https://example.com/p/{i}", title, snippet, evidence or f"e{i}")


def test_default_query_plan_is_bounded_deterministic_and_policy_ordered():
    first=build_dental_discovery_queries(max_queries=20); second=build_dental_discovery_queries(max_queries=20)
    assert first == second and len(first)==4
    assert [q.professional_group for q in first] == list(APPROVED_DENTAL_ICP_POLICY_V1.eligible_professional_groups)
    assert all(q.state is None and q.recipe_id==RECIPE_ID for q in first)


def test_explicit_states_are_normalized_sorted_and_bounded():
    q=build_dental_discovery_queries(states=["sp","PR","SP"], professional_groups=["HOF_OR_FACIAL_ACTIVITY"], max_queries=1)
    assert len(q)==1 and q[0].state=="PR" and q[0].professional_group=="HOF_OR_FACIAL_ACTIVITY"


def test_invalid_query_inputs_rejected():
    with pytest.raises(ValueError): build_dental_discovery_queries(max_queries=0)
    with pytest.raises(ValueError): build_dental_discovery_queries(states=["XX"])
    with pytest.raises(ValueError): build_dental_discovery_queries(professional_groups=["MEDICINE"])
    with pytest.raises(ValueError): build_dental_discovery_queries(replace(APPROVED_DENTAL_ICP_POLICY_V1, country="US"))


def test_query_contract_rejects_wrong_group_state_recipe_and_blank():
    with pytest.raises(ValueError): DentalDiscoveryQuery("", "x", "GENERAL_DENTIST", None)
    with pytest.raises(ValueError): DentalDiscoveryQuery("q", "x", "MEDICINE", None)
    with pytest.raises(ValueError): DentalDiscoveryQuery("q", "x", "GENERAL_DENTIST", "XX")
    with pytest.raises(ValueError): DentalDiscoveryQuery("q", "x", "GENERAL_DENTIST", None, "other")


def test_public_observation_validates_identity_url_and_optional_query():
    with pytest.raises(ValueError): obs(1,"")
    with pytest.raises(ValueError): PublicSearchObservation("o","ftp://x.test/a","Dentista","", "e")
    with pytest.raises(ValueError): PublicSearchObservation("o","https://u:p@x.test/a","Dentista","", "e")
    with pytest.raises(ValueError): PublicSearchObservation("o","https://x.test/a","Dentista","", "e"," ")


@pytest.mark.parametrize(("text","state","number"), [
    ("CRO-SP 92703","SP","92703"), ("CRO 9029/PE","PE","9029"),
    ("PR-CD-25373","PR","25373"), ("25342 CRO RS","RS","25342")
])
def test_supported_cro_forms(text,state,number):
    c=candidate_from_public_observation(obs(text, f"Dentista {text}"))
    assert (c.cro_state,c.cro_number,c.cfo_verification_status)==(state,number,CFOVerificationStatus.PENDING)


def test_unknown_cro_state_is_not_promoted_but_dental_signal_can_candidate():
    c=candidate_from_public_observation(obs(2,"Dentista CRO-XX 12345"))
    assert c.cro_state is None and c.cro_number is None


@pytest.mark.parametrize(("title","group"), [
    ("Cirurgião bucomaxilofacial CRO-SP 1234","BUCOMAXILLOFACIAL"),
    ("Especialista em Harmonização Orofacial CRO-PR 1234","HOF_OR_FACIAL_ACTIVITY"),
    ("Cirurgião-dentista CRO-RS 1234","GENERAL_DENTIST"),
    ("Ortodontia CRO-MG 1234","DENTAL_SPECIALIST"),
])
def test_professional_group_classification(title,group):
    assert candidate_from_public_observation(obs(group,title)).observed_professional_group==group


def test_facial_term_alone_can_create_candidate_but_not_cfo_verification():
    c=candidate_from_public_observation(obs(3,"Clínica X","Blefaroplastia e frontoplastia"))
    assert c.observed_professional_group is None and c.facial_relevance_terms==("blefaroplastia","frontoplastia")
    assert c.cfo_verification_status is CFOVerificationStatus.PENDING


def test_irrelevant_observation_produces_no_candidate():
    assert candidate_from_public_observation(obs(4,"Empresa de software","ERP e cloud")) is None


def test_url_is_canonicalized_without_query_fragment_or_default_port():
    c=candidate_from_public_observation(PublicSearchObservation("o","HTTPS://Example.COM:443/a/?x=1#f","Dentista","", "e"))
    assert c.source_url=="https://example.com/a"


def test_exact_cro_dedupes_and_unions_evidence_not_names():
    a=candidate_from_public_observation(obs(5,"Alice Dentista CRO-SP 12345", evidence="e2"))
    b=candidate_from_public_observation(obs(6,"Nome diferente CRO-SP 12345", url="https://other.test/x", evidence="e1"))
    out=deduplicate_dental_candidates((a,b))
    assert len(out)==1 and out[0].evidence_ids==("e1","e2") and out[0].display_name_hint==a.display_name_hint


def test_exact_url_dedupes_without_cro_and_unions_signals():
    a=candidate_from_public_observation(obs(7,"Dentista","",url="https://x.test/p?one=1",evidence="e2"))
    b=candidate_from_public_observation(obs(8,"Harmonização Orofacial","lip lift",url="https://x.test/p?two=2",evidence="e1"))
    out=deduplicate_dental_candidates((a,b))
    assert len(out)==1 and out[0].evidence_ids==("e1","e2")
    assert out[0].observed_professional_group=="GENERAL_DENTIST"
    assert "lip lift" in out[0].facial_relevance_terms


def test_same_name_different_urls_remains_distinct():
    out=discover_dental_candidates((obs(9,"Mesma Pessoa Dentista",url="https://a.test/p"),obs(10,"Mesma Pessoa Dentista",url="https://b.test/p")))
    assert len(out)==2


def test_candidate_invariants_block_forged_states():
    c=candidate_from_public_observation(obs(11,"Dentista"))
    with pytest.raises(ValueError): replace(c,evidence_ids=())
    with pytest.raises(ValueError): replace(c,cro_state="SP",cro_number=None)
    with pytest.raises(ValueError): replace(c,cro_state="XX",cro_number="123")
    with pytest.raises(ValueError): replace(c,observed_professional_group="MEDICINE")
    with pytest.raises(ValueError): replace(c,recipe_id="other")


def test_dental_discovery_filters_irrelevant_and_deduplicates():
    observations=(obs(12,"Dentista CRO-PR 22606",evidence="e1"),obs(13,"Dentista CRO-PR 22606",url="https://b.test",evidence="e2"),obs(14,"Software"))
    out=discover_dental_candidates(observations)
    assert len(out)==1 and out[0].evidence_ids==("e1","e2")


def test_candidate_rejects_blank_identity_duplicate_evidence_and_forged_cfo_state():
    c=candidate_from_public_observation(obs(15,"Dentista"))
    with pytest.raises(ValueError): replace(c,candidate_id="")
    with pytest.raises(ValueError): replace(c,evidence_ids=("e1","e1"))
    object.__setattr__(c,"cfo_verification_status","VERIFIED")
    with pytest.raises(ValueError, match="cannot promote"):
        c.__post_init__()


def test_invalid_port_url_is_rejected():
    with pytest.raises(ValueError, match="valid absolute"):
        PublicSearchObservation("o","https://example.com:99999/a","Dentista","", "e")
