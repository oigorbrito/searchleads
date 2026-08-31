from searchleads.acceptance import run_dental_commercial_acceptance

def test_real_policy_contract_path_is_deterministic_and_separate_from_external_gates():
    result=run_dental_commercial_acceptance()
    assert result.policy_id=='dental-facial-surgery-education-br-v1'
    assert (result.qualification_status,result.fit,result.intent,result.priority)==('QUALIFIED','HIGH','UNKNOWN','P2')
    assert result.evidence_count==3 and result.deterministic is True
    assert result.technical_acceptance_gate=='SEPARATE_UNCHANGED'
    assert result.live_cfo_gate==result.campaign_legal_gate=='NOT_EVALUATED'

def test_acceptance_defensive_policy_status_and_determinism_guards(monkeypatch):
    import searchleads.acceptance.dental_qualification as mod
    original=mod._run_once
    decision,lead=original()
    import pytest

    def mutated_decision(**changes):
        clone=object.__new__(type(decision))
        for name in decision.__dataclass_fields__:
            object.__setattr__(clone,name,getattr(decision,name))
        for name,value in changes.items():
            object.__setattr__(clone,name,value)
        return clone

    monkeypatch.setattr(mod,'_run_once',lambda:(mutated_decision(policy_id='wrong'),lead))
    with pytest.raises(AssertionError,match='wrong policy'): mod.run_dental_commercial_acceptance()

    monkeypatch.setattr(mod,'_run_once',lambda:(mutated_decision(qualification_status=mod.QualificationStatus.UNKNOWN),lead))
    with pytest.raises(AssertionError,match='did not qualify'): mod.run_dental_commercial_acceptance()

    from dataclasses import replace
    calls=iter(((decision,lead),(decision,replace(lead,lead_id='different'))))
    monkeypatch.setattr(mod,'_run_once',lambda:next(calls))
    with pytest.raises(AssertionError,match='not deterministic'): mod.run_dental_commercial_acceptance()
