# Full Regression Report — 2026-08-22

This report records the first complete current-branch regression executed by GitHub Actions after the dental ICP MVP and post-baseline extensions were stacked together.

## Execution

GitHub Actions workflow: `dental-mvp`

Run ID: `32544027242`

Tested executable commit: `6759dfd6701bc58c92296bc26177a002b4d7fb69`

Pull request: `#36 — feat: define dental facial-surgery education ICP MVP`

Environment:

```text
ubuntu-24.04
Python 3.11.16
```

## Result

```text
FULL_UNITTEST_DISCOVER = PASS
TESTS_DISCOVERED = 234
TESTS_EXECUTED = 234
TESTS_PASSED = 234
TESTS_FAILED = 0
TESTS_ERRORS = 0
```

Command:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions result:

```text
Ran 234 tests in 7.616s
OK
```

## Deterministic end-to-end acceptance

Command:

```bash
PYTHONPATH=. python scripts/run_end_to_end_acceptance.py
```

Result:

```text
REAL_COMPANIES=YES
MULTI_SOURCE=YES
DEDUPLICATION=PASS
COMPANY_ER=PASS
PROVENANCE=PASS
CONTACT_DISCOVERY=PASS
CONTACT_VALIDATION=PASS
PERSON_ROLE=PASS
QUALIFICATION_ENGINE=PASS
EXPORT=PASS
REPRODUCIBLE=PASS
DISCOVERED_COMPANIES=1
EVIDENCE_COUNT=6
VALIDATED_CONTACTS=2
PEOPLE_COUNT=1
ROLES_COUNT=1
CONFLICTS=1
REVIEW_ITEMS=2
TECHNICAL_QUALIFICATION=QUALIFIED
BUSINESS_QUALIFICATION=UNKNOWN
EXPORT_SHA256=81af24599d7b0bc6ca012a397c243b4049d2e70f0e31a50e0c5eb1d747d0139d
```

The acceptance script still prints the historical generic-business state `ICP_DEFINED=NO` because that script intentionally exercises the earlier generic company-level acceptance contract. This does not override the separately implemented dental Person ICP (`dental-facial-surgery-education-br-v1`).

## Dental 50-row operational batch

Command:

```bash
PYTHONPATH=. python scripts/evaluate_dental_verification_batch.py \
  DENTAL-CFO-VERIFICATION-BATCH-50.csv \
  --output /tmp/dental-batch-evaluated.csv
```

Result:

```text
ROWS=50
PREP_READY=0
SEND_READY=0
REVIEW=50
EXCLUDE=0
```

This is an expected safety result while current individual CFO registration verification and campaign send-compliance confirmation remain pending.

## WU3 live HTTP closure

Command:

```bash
PYTHONPATH=. python scripts/run_live_brasilapi_smoke.py
```

Result:

```text
WU3_LIVE_HTTP=PASS
COMPANY_ID=company:cnpj:33683111000280
EVIDENCE_ID=evidence:brasilapi:33683111000280:0fd37b41051557340f5d
CANDIDATE_FACTS=10
```

This closes the earlier execution-environment blocker for the literal live BrasilAPI ingestion smoke. A real company was ingested over live HTTP in GitHub Actions.

## Final regression status

```text
FULL_CURRENT_PRIVATE_BRANCH_DISCOVER = PASS
FULL_CURRENT_TEST_COUNT = 234/234 PASS
DETERMINISTIC_E2E = PASS
E2E_EXPORT_SHA_REPRODUCED = YES
DENTAL_BATCH_50_SMOKE = PASS
WU3_LIVE_HTTP = PASS
```

No failure required a code retry in this full-regression run. The workflow completed successfully on its first full-suite execution.

## Remaining non-test blockers

These are not test failures:

```text
CFO_VERIFIED_ACTIVE = 0/50
PREPARATION_READY = 0/50
CAMPAIGN_LEGAL_STATUS = PENDING_REVIEW
SEND_READY = 0/50
MAIN_INTEGRATION = NOT_DONE
```

They remain operational/compliance/integration states, not regression defects.
