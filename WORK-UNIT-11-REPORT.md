# Work Unit 11 Report — LEADS_EXPANSION_V1

## Scope

Controlled expansion from an explicit iterable of CNPJ seeds into the existing BrasilAPI acquisition/persistence path. This is not broad discovery or crawling.

## Decisions

- Seed-driven expansion only: `ENGINEERING_CHOICE`.
- Duplicate input CNPJs are removed before acquisition: `ENGINEERING_CHOICE`.
- Companies already persisted as `company:cnpj:<cnpj>` are counted as `already_present` and skipped before source acquisition: `ENGINEERING_CHOICE` supporting immutable evidence semantics.
- One seed failure does not abort the batch: `ENGINEERING_CHOICE`.
- Expansion does not create or qualify a Lead automatically: `EVIDENCE_BACKED` architectural constraint (`COMPANY != LEAD`).
- ICP remains undefined: `UNKNOWN`; B2B remains `HYPOTHESIS / PROVISIONAL`.

## Controlled real-seed smoke

The smoke fixture uses three institution CNPJs independently verified in public institutional material before this work unit:

- SERPRO — `33.683.111/0002-80`
- CAIXA ECONOMICA FEDERAL — `00.360.305/0001-04`
- EMPRESA BRASILEIRA DE CORREIOS E TELEGRAFOS — `34.028.316/0001-03`

The source payloads in tests are deterministic fixtures representing those seeds; this report does not claim live BrasilAPI HTTP execution from the local container.

First run:

- requested seeds: 3
- unique seeds: 3
- newly ingested companies: 3
- already present: 0
- failed: 0

Immediate repeated run against the same store:

- newly ingested companies: 0
- already present: 3
- failed: 0
- evidence rows remain 3 (no rewrite/re-fetch for already-present companies)

## Validation

Command:

```bash
python -m unittest discover -s tests -v
```

Result at completion:

- `TESTS_DISCOVERED = 120`
- `TESTS_EXECUTED = 120`
- `TESTS_PASSED = 120`

## Gates

- `CONTROLLED_EXPANSION = PASS`
- `SEED_DEDUPLICATION = PASS`
- `PER_ITEM_FAILURE_ISOLATION = PASS`
- `RERUN_ALREADY_PRESENT_HANDLING = PASS`
- `EXPANSION_NEW_COMPANIES = 3`
- `ICP_DEFINED = NO`
- `QUALIFYING_LEAD_GROWTH = NOT_EVALUABLE`
- `B2B_ASSUMPTION = PROVISIONAL`

## Limitation

This work unit proves controlled batch acquisition over explicit seeds. It does not establish discovery coverage, source diversification, production throughput, or growth of qualified leads. Those claims require an explicit ICP and broader real-source evaluation.
