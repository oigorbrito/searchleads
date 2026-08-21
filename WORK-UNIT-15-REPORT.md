# Work Unit 15 Report — END_TO_END_ACCEPTANCE_V1

## Acceptance run

A deterministic real-company acceptance fixture composes the implemented SearchLeads capabilities for SERPRO Regional Brasília (`33.683.111/0002-80`). Source facts used in deterministic fixtures were verified against the relevant official/current sources during their work units; the acceptance run itself is intentionally network-independent and reproducible.

Pipeline exercised:

```text
known-source discovery
→ structured CNPJ acquisition
→ second-source official enrichment
→ company entity resolution / dedupe
→ field fusion + explicit conflict
→ professional contact discovery
→ official-publication contact corroboration
→ person/company role discovery
→ qualification
→ selective review
→ independent export
```

## Measured run

- discovered companies in acceptance page: `1`
- exported company: `company:cnpj:33683111000280`
- evidence records in export bundle: `6`
- validated/corroborated contacts: `2`
- people: `1`
- professional roles: `1`
- explicit conflicts: `1`
- selective-review items: `2`
- export bytes: `15457`
- export SHA-256: `81af24599d7b0bc6ca012a397c243b4049d2e70f0e31a50e0c5eb1d747d0139d`

A second fresh run produces the same export bytes and SHA-256.

## Handoff gates

```text
REAL_COMPANIES = YES
MULTI_SOURCE = YES
DEDUPLICATION = PASS
COMPANY_ER = PASS
PROVENANCE = PASS
CONTACT_DISCOVERY = PASS
CONTACT_VALIDATION = PASS
PERSON_ROLE = PASS
QUALIFICATION_ENGINE = PASS
EXPORT = PASS
REPRODUCIBLE = PASS
```

## Qualification gate — critical distinction

The supplied handoff explicitly says qualification should only execute after ICP definition. The repository still has:

```text
ICP_DEFINED = NO
B2B_ASSUMPTION = PROVISIONAL
```

Therefore the acceptance harness uses two separate checks:

1. **Technical qualification engine check:** a policy explicitly named `acceptance-policy-only` requires canonical `state = DF`. It yields `QUALIFIED`, proving the mechanism composes correctly. This policy is synthetic test input and is **not** the product ICP.
2. **Real business qualification check:** `policy=None` yields `UNKNOWN`, exactly as required by the no-invented-ICP rule.

So:

```text
QUALIFICATION_ENGINE = PASS
REAL_QUALIFICATION = NOT_EVALUABLE
```

It would be false to report the original business `QUALIFICATION = PASS` while the ICP remains undefined.

## Overall acceptance status

```text
TECHNICAL_END_TO_END_ACCEPTANCE = PASS
COMMERCIAL_END_TO_END_ACCEPTANCE = BLOCKED_BY_UNDEFINED_ICP
```

This is the terminal engineering state supported by the current handoff without inventing a business requirement.

## Validation

Commands:

```bash
python -m unittest discover -s tests -v
python scripts/run_end_to_end_acceptance.py
```

Results:

- `TESTS_DISCOVERED = 162`
- `TESTS_EXECUTED = 162`
- `TESTS_PASSED = 162`

## Remaining known limitations

- production BrasilAPI HTTP smoke is still constrained by the original local execution environment's outbound-DNS limitation; deterministic source fixtures are used in acceptance;
- contact `VALIDATED` means corroborated official publication, not mailbox deliverability or phone reachability;
- ER/fusion benchmark metrics are local curated calibration results, not population accuracy;
- discovery coverage of the wider B2B universe remains unknown;
- real qualification precision/recall cannot be measured before ICP and labeled business ground truth exist.
