from scripts.evaluate_dental_qualification import CASES, evaluate_case

def test_benchmark_exact_contract_routing():
    outcomes=[evaluate_case(case) for case in CASES]
    assert len(outcomes)==18
    assert all(actual==expected for actual,expected in outcomes)
    assert sum(actual[0]=='QUALIFIED' and expected[0]!='QUALIFIED' for actual,expected in outcomes)==0
    assert sum(actual[0]=='NOT_QUALIFIED' and expected[0]!='NOT_QUALIFIED' for actual,expected in outcomes)==0
    assert sum(actual[0]=='UNKNOWN' and expected[0]=='UNKNOWN' for actual,expected in outcomes)==3
