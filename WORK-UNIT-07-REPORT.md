# WORK UNIT 07 REPORT — CONTACT_DISCOVERY_V1

## Scope

This work unit discovers professional contact observations from a known company page and persists them as evidence-bearing `ContactPoint` records. It does not validate contacts, discover people, infer employment, qualify leads, or crawl the web broadly.

## Pipeline

```text
known persisted Company
→ known official/public company page
→ raw HTML Evidence
→ extract contact observations
→ ContactPoint(status=DISCOVERED)
→ SQLite persistence
```

Supported observations:

- e-mail (`mailto:` and visible e-mail text);
- phone (`tel:` and labeled phone text);
- contact form (`<form>` target/page);
- LinkedIn company/profile URL;
- Instagram URL.

## Real-contact verification

Current official Serpro pages were checked on 2026-08-21. The official customer-help page exposes the professional support e-mail `css.serpro@serpro.gov.br` and phone `0800 728 2323`. The official contact page exposes a contact form at `/contact-info`.

The local test fixture contains only the minimal contact-bearing HTML needed to exercise these currently verified values; it is not represented as a byte-for-byte live page capture. The production adapter can preserve the full fetched HTML when network access is available.

```text
REAL_COMPANY = SERPRO / CNPJ 33.683.111/0002-80
REAL_CONTACT_VALUES_VERIFIED = 3
EMAIL = css.serpro@serpro.gov.br
PHONE = 0800 728 2323
CONTACT_FORM = https://www.serpro.gov.br/contact-info
REAL_CONTACTS_ASSOCIATED_WITH_COMPANY = PASS
LIVE_HTTP_IN_TEST_CONTAINER = NO
```

## Safety / precision behavior

- contacts remain `DISCOVERED`, never `VALIDATED`;
- a company must exist before page evidence is persisted;
- CNPJ, CEP, and dates are not interpreted as phones merely because they contain digits;
- phone extraction is limited to `tel:` links and phone-labeled text;
- repeated extraction of the same page snapshot is idempotent;
- changed page snapshots can create new evidence-bearing observations without rewriting older evidence.

## Validation

```text
TESTS_DISCOVERED = 82
TESTS_EXECUTED = 82
TESTS_PASSED = 82
```

## Gate

```text
REAL_CONTACTS_DISCOVERED > 0 = PASS (3 current official Serpro contact values verified and exercised)
CONTACTS_ASSOCIATED_WITH_REAL_COMPANY = PASS
FOUND_NOT_VALIDATED = PASS
RAW_PAGE_EVIDENCE_SUPPORTED = PASS
CONTACT_PROVENANCE = PASS
TESTS = PASS
```

## Decision classification

### EVIDENCE_BACKED

- contact is a separate evidence-bearing entity;
- discovered does not imply validated.

### LOCALLY_VERIFIED

- current official Serpro pages expose the three contact channels used by the real-company smoke fixture;
- extraction/persistence behavior passes the local suite.

### ENGINEERING_CHOICE

- stdlib HTML parser and HTTP client;
- phone-label restriction;
- deterministic contact IDs tied to the evidence snapshot;
- official/public page supplied explicitly rather than broad crawling.

### UNKNOWN

- deliverability / reachability;
- contact ownership freshness;
- production extraction precision/recall across arbitrary websites;
- best source ordering across official sites, directories, and associations.

## Next work unit

Per roadmap: `CONTACT_VALIDATION_V1`.
