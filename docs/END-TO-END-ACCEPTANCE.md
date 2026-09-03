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

## Live-network certification update

The original WU14 acceptance remained deterministic by design. Separately, a bounded live smoke was executed on 2026-09-03 from commit `9df9f6f9d15936796234fa969001e6175fd84780` in a network-capable Codex runtime using the production adapters and no fixture substitution.

For known CNPJ `33.683.111/0002-80`, BrasilAPI returned HTTP **200** and persisted raw Evidence `evidence:brasilapi:9d499ad5b5acc5d0aad9ea653705b09a420c5e243e6e16362abd2cb0c133de61` before interpretation. The fixed SERPRO official-location page also returned HTTP **200** and persisted raw Evidence `evidence:official-company-location:aa714197fa9d6acce7e1edc55131bb02b70c876ed369c3d2f8c235b8630248b3` before extraction.

This is a point-in-time certification of those exact acquisition boundaries. It does not alter deterministic WU14 semantics, imply continuous upstream availability, certify broader market coverage, or certify GitHub Actions runner health.

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

LIVE_BRASILAPI_HTTP_POINT_SMOKE = PASS_AT_9df9f6f_ON_2026-09-03
LIVE_SERPRO_HTTP_POINT_SMOKE = PASS_AT_9df9f6f_ON_2026-09-03
GITHUB_ACTIONS_EXECUTION = BLOCKED_BY_RUNNER_INFRASTRUCTURE
MULTI_SOURCE_COMPANY_ENRICHMENT = IMPLEMENTED_POST_WU14
ICP_DEFINED = NO
COMMERCIAL_QUALIFICATION = BLOCKED_BY_UNDEFINED_ICP
B2B_ASSUMPTION = PROVISIONAL
```

## Why live network remains separate

The deterministic acceptance harness remains fixture-based and reproducible. Live HTTP is maintained as a separate operational gate because upstream content and network availability can change independently of the deterministic contract.

The 2026-09-03 bounded smoke certifies successful point acquisition for the documented BrasilAPI CNPJ and fixed SERPRO page at the recorded commit. It does not relabel deterministic fixture behavior as live behavior, nor does it make a source-wide availability claim.

## Final original-handoff status

`END_TO_END_ACCEPTANCE_V1` completes the original technical work-unit sequence for the clean stack.

It does **not** close product/research blockers that require external evidence or business decisions: a defined ICP/qualification policy, broader Person ER, or market-coverage measurement. The bounded live-network point-smoke blocker was subsequently satisfied on 2026-09-03, while GitHub Actions execution remains separately blocked by runner infrastructure.
