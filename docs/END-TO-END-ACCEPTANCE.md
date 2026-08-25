# End-to-End Acceptance v1

## Work unit

`END_TO_END_ACCEPTANCE_V1`

This is the final original-handoff work unit for the clean SearchLeads stack. It exercises the published boundaries together and reports what the implementation can actually prove. It deliberately does not turn deterministic fixtures into claims about live network availability, production web coverage, or commercial qualification.

## Acceptance boundary

The deterministic run composes:

```text
SERPRO known-source directory recipe
→ evidence-linked CNPJ seed
→ BrasilAPI structured acquisition snapshots
→ persistence / Evidence replay
→ normalization
→ company ER
→ conservative field fusion + explicit conflict
→ company contact discovery on two pages
→ contact publication corroboration
→ Person + role discovery
→ selective review
→ explicit gap detection / bounded action planning
→ integrity-checked deterministic export
```

All acquisition boundaries use the real clean-stack adapters with deterministic in-process transports. No alternative acceptance-only extraction logic replaces WU3, WU7, or WU8.

## Fixed acceptance company

The fixture uses the SERPRO Brasília observation with CNPJ:

```text
33.683.111/0002-80
```

The directory snapshot produces one seed. That seed is then passed through WU10's `acquire_discovered_seeds()` boundary into the real WU3 `BrasilAPISource`.

Two deterministic BrasilAPI snapshots are captured for the same CNPJ. They agree on legal name after WU4 normalization but disagree on trade name. Therefore the acceptance run simultaneously proves:

- normalized legal-name unanimity may create one WU6 CanonicalFact;
- disagreeing trade names remain one explicit WU6 Conflict;
- same namespaced `br:cnpj` observations produce WU5 `AUTO_MATCH`.

The second snapshot is not presented as a second independent company-enrichment source. It is a second observation of the same structured source.

## Contact path

Two distinct company-page Evidence observations publish the same e-mail association:

```text
css.serpro@serpro.gov.br
```

WU7 discovers the contact independently on both pages. WU9 corroborates publication from those independent persisted Evidence records and creates a separate immutable `VALIDATED` ContactPoint snapshot.

This still does **not** claim mailbox deliverability, responsiveness, current human ownership, or reachability.

## Person / role path

The people-page fixture contains one leadership observation:

```text
Wilton Itaiguara Gonçalves Mota
Diretor-Presidente - DP
```

WU8 creates an observation-scoped Person linked to the Company by page Evidence, plus separate `person_name` and `professional_role_title` CandidateFacts and local discovered contacts.

No Person entity-resolution merge is performed by acceptance.

## Qualification and review

No ICP or clean qualification engine exists. Acceptance therefore creates a Lead with:

```text
qualification_status = UNKNOWN
qualification_reasons = ("ICP/policy is not defined",)
```

WU11 routes the existing high-value qualification ambiguity to review without changing that status. The open trade-name conflict is also routed to review as high impact.

The acceptance harness never creates a synthetic ICP merely to turn the commercial gate green.

## Gap planning

Acceptance requests:

- `legal_name`;
- `state`;
- `employee_count`;
- one validated company contact;
- one Person role;
- qualification.

Observed result:

- `legal_name`: closed by the canonical fact;
- validated contact: closed;
- Person role: closed;
- `state`: gap remains and maps to one READY WU3 BrasilAPI prerequisite action because a CNPJ is explicitly available;
- `employee_count`: BLOCKED because no implemented clean-stack source owns this field;
- qualification: BLOCKED because no qualification engine/ICP exists.

This demonstrates the WU13 distinction between **detecting a gap** and **having a safe implemented action**.

## Persistence / provenance acceptance

Every Evidence record used in the exported bundle is loaded back through `SQLiteRepository.iter_evidence()`. For every Evidence ID, `raw_evidence_bytes()` must reproduce the original UTF-8 bytes exactly.

The acceptance run fails if any replay differs.

## Export reproducibility

The entire scenario runs twice against fresh in-memory SQLite repositories using the same fixed timestamps and deterministic transport observations.

Measured result:

```text
DISCOVERED_SEEDS = 1
STRUCTURED_SNAPSHOTS = 2
EVIDENCE_RECORDS = 6
CANDIDATE_FACTS = 18
CANONICAL_FACTS = 1
CONFLICTS = 1
COMPANY_CONTACTS = 6
VALIDATED_COMPANY_CONTACTS = 1
PEOPLE = 1
ROLE_FACTS = 1
REVIEW_ITEMS = 2
GAPS = 3
READY_ACTIONS = 1
BLOCKED_ACTIONS = 2
ER_DISPOSITION = AUTO_MATCH
PERSISTENCE_REPLAY = PASS
```

The two fresh runs produce byte-identical JSON export and the same SHA-256:

```text
ec1120c4a75058fe933353558ff8b88e605d0bf369c7008171e4c2e1d56671f8
```

Reproducibility here means deterministic output for the fixed Evidence snapshots. It is not a claim that live upstream sources never change.

## Verification

Focused acceptance verification:

```text
WU14_FOCUSED_TESTS = 18/18 PASS
WU14_MODULE_LINE_COVERAGE = 100%
WU14_MEASURED_STATEMENTS = 159
WU14_MEASURED_BRANCHES = 28
END_TO_END_SCRIPT = PASS
PYTHON_MODULE_COMPILE = PASS
```

The tests cover the successful path and defensive failures including zero/multiple seeds, failed or empty structured acquisition, both legal-name normalization failures, unexpected fusion outcomes, non-AUTO ER, non-independent contact evidence, missing Person role, persistence replay mismatch, and forced export non-reproducibility.

## Gate report

```text
TECHNICAL_DATA_PATH = PASS
REPRODUCIBLE_EXPORT = PASS
PERSISTENCE_EVIDENCE_REPLAY = PASS
DISCOVERY_TO_STRUCTURED_ACQUISITION = PASS
NORMALIZATION = PASS
COMPANY_ER = PASS
FIELD_FUSION = PASS
EXPLICIT_CONFLICT = PASS
CONTACT_DISCOVERY = PASS
CONTACT_PUBLICATION_VALIDATION = PASS
PERSON_ROLE_DISCOVERY = PASS
SELECTIVE_REVIEW = PASS
GAP_PLANNING = PASS
EXPORT = PASS

LIVE_BRASILAPI_HTTP = NOT_CERTIFIED_IN_EXECUTION_CONTAINER
MULTI_SOURCE_COMPANY_ENRICHMENT = NOT_IMPLEMENTED_IN_CLEAN_STACK
ICP_DEFINED = NO
COMMERCIAL_QUALIFICATION = BLOCKED_BY_UNDEFINED_ICP
B2B_ASSUMPTION = PROVISIONAL
```

## Why live network is separate

The execution environment used for the clean-stack work could not complete direct outbound DNS/network access for the live BrasilAPI smoke. WU14 therefore does not relabel deterministic transport execution as a live HTTP success.

The adapter itself is exercised through its real transport boundary and persistence logic. A future environment with outbound access can run the separate live smoke without changing the acceptance semantics.

## Final original-handoff status

`END_TO_END_ACCEPTANCE_V1` completes the original technical work-unit sequence for the clean stack.

It does **not** close product/research blockers that require external evidence or business decisions: live-network certification, a defined ICP/qualification policy, broader multi-source enrichment, Person ER, or market-coverage measurement.
