# Contact Discovery v1

## Work unit

`CONTACT_DISCOVERY_V1`

This unit discovers evidence-linked **company** contact observations from one explicitly supplied public/official company page. It does not crawl broadly, discover people, validate contacts, or qualify leads.

## Pipeline

```text
known persisted Company
→ explicit HTTP(S) company page
→ raw HTTP page Evidence
→ bounded HTML extraction
→ ContactPoint(status=DISCOVERED)
→ SQLite persistence
```

If an HTTP response is received, its textual body is persisted before status handling or extraction. Network errors without a response remain acquisition failures and do not fabricate Evidence.

## Supported V1 channels

- `EMAIL`: `mailto:` and visible e-mail text;
- `PHONE`: `tel:` and phone-labeled visible text;
- `WHATSAPP`: explicit `https://wa.me/<7-15 digits>` only;
- `CONTACT_FORM`: the page URL when at least one visible form exists;
- `LINKEDIN`: direct `/company/<slug>` profile URLs only;
- `INSTAGRAM`: one-segment profile URLs only.

Personal LinkedIn profiles, social post/content routes, arbitrary digit strings, hidden template/script/style/noscript content, and form submission handlers are intentionally excluded.

## Discovery vs validation

Every extracted `ContactPoint` has:

```text
owner_id = known Company
status = DISCOVERED
discovery_evidence_ids = page Evidence
validation_evidence_ids = ()
validated_at = null
```

No deliverability, reachability, mailbox ownership, phone ownership, account control, freshness, or responsiveness claim is made.

## Snapshot identity

Evidence identity includes request URL + HTTP status + exact body. This distinguishes, for example, an anti-abuse `429` body from a later `200` response even if their text happens to be identical.

Contact IDs include company + channel kind + dedupe key + Evidence ID. Therefore:

- repeated ingestion of the same response snapshot is idempotent;
- a changed page creates new immutable contact observations;
- previous discovery evidence is never rewritten.

## Curated extraction benchmark

A deterministic 12-scenario fixture includes:

- valid e-mail/phone/WhatsApp/form/company-social contacts;
- duplicate representations;
- CNPJ/CEP/date/unlabeled-number distractors;
- script/style/template/noscript distractors;
- malformed e-mail/phone/WhatsApp values;
- LinkedIn personal profiles;
- Instagram post/reel/story routes;
- third-party form submission endpoints.

Current result:

```text
SCENARIOS = 12
EXPECTED_CONTACTS = 17
TRUE_POSITIVE = 17
FALSE_POSITIVE = 0
FALSE_NEGATIVE = 0
PRECISION = 100.0%
RECALL = 100.0%
F1 = 100.0%
```

These are **local curated-contract metrics**, not a production estimate across arbitrary websites.

## Current public SERPRO calibration — checked 2026-08-25

Current official SERPRO pages continue to expose:

- support e-mail `css.serpro@serpro.gov.br`;
- support phone `0800 728 2323`;
- a contact form on `https://www.serpro.gov.br/contact-info`.

Official references checked:

- `https://www.serpro.gov.br/menu/contato/cliente/perguntas-frequentes/suporte/suporte-perguntas-frequentes`
- `https://www.serpro.gov.br/contact-info`

The test uses only a minimal calibration HTML containing those values. It is **not** represented as a byte-for-byte live SERPRO capture, and the local runtime did not perform a live page fetch.

## Verification

```text
WU7_FOCUSED_TESTS = 63/63 PASS
WU7_MODULE_LINE_COVERAGE = 100%
WU7_MEASURED_STATEMENTS = 266
WU6_PLUS_WU7_RECONSTRUCTED = 86/86 PASS
CONTACT_BENCHMARK = PASS
PYTHON_MODULE_COMPILE = PASS
```

The clean base PR #47 remains separately validated according to its published verification. This reconstructed runtime run does not relabel prior whole-stack counts as newly executed.

## Gate

```text
KNOWN_COMPANY_REQUIRED = YES
RAW_PAGE_EVIDENCE = PASS
HTTP_ERROR_BODY_EVIDENCE = PASS
DISCOVERY_ONLY = YES
ALL_CONTACT_STATUS = DISCOVERED
CONTACT_EVIDENCE_LINK = PASS
PHONE_FALSE_POSITIVE_GUARDS = PASS
PERSON_DISCOVERY = NO
CONTACT_VALIDATION = NO
CURATED_PRECISION = 100.0%
CURATED_RECALL = 100.0%
FOCUSED_TESTS = PASS
LINE_COVERAGE_NEW_MODULE = 100%
ICP_DEFINED = NO
B2B_ASSUMPTION = PROVISIONAL
```

## Next work unit

Per the supplied roadmap, Person/role discovery precedes contact validation: `PERSON_AND_ROLE_DISCOVERY_V1`.
