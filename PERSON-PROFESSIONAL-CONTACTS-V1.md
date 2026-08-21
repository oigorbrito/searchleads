# Person Professional Contacts V1

This extension closes the remaining Work Unit 8 detail from the supplied handoff: after a company/person/role relationship is known, preserve professional contact observations published alongside the person.

## Source behavior

Current Serpro `Quem é quem` evidence (checked 2026-08-21) publishes, for each of the seven Diretoria Executiva entries, a name, role, telephone, e-mail, and a `Currículo` link.

The seven-current-director fixture therefore exercises:

```text
PEOPLE = 7
PUBLISHED_EMAIL_CHANNELS = 7
PUBLISHED_PHONE_CHANNELS = 7
TOTAL_PERSON_ASSOCIATED_CHANNELS = 14
```

All resulting contact points remain:

```text
STATUS = DISCOVERED
```

No mailbox deliverability, telephone reachability, or current human control is claimed.

## Profile-link safety

The current `Currículo` links for multiple directors resolve to the same shared curriculum page.

A shared URL is therefore retained only as contextual evidence and is **not** promoted to `ContactKind.PROFESSIONAL_PROFILE` for Person Entity Resolution.

A profile URL is emitted only when the page snapshot provides a URL unique to one known person.

This protects the non-negotiable rule:

```text
NAME MATCH != ENTITY MATCH
```

and avoids turning a shared directory page into a false strong person identifier.

## Association behavior

- extraction is limited to the local HTML block between one known person and the next known person;
- e-mail and phone observations are deduplicated per person;
- incomplete phone fragments are rejected;
- constructed `ContactPoint` records are person-owned evidence-bearing observations;
- provenance references the exact Evidence snapshot;
- a small persistence boundary writes those contact points through the existing store API.

## Validation

```text
TESTS_DISCOVERED = 9
TESTS_EXECUTED = 9
TESTS_PASSED = 9
```

## Classification

### EVIDENCE_BACKED

- contacts are created only from explicit values published alongside a known person;
- every contact carries Evidence-linked provenance;
- shared profile pages are not treated as person identity.

### LOCALLY_VERIFIED

- current Serpro page publishes seven director e-mails and seven director phone channels alongside the current executive entries.

### ENGINEERING_CHOICE

- bounded 16-chunk local person block;
- minimum 8 digits for emitted phone observations;
- profile URL must be unique across the known people in one snapshot before promotion to `PROFESSIONAL_PROFILE`.

### UNKNOWN

- deliverability / reachability;
- whether a functional role mailbox is directly controlled by the named individual;
- production extraction precision/recall across arbitrary people pages.
