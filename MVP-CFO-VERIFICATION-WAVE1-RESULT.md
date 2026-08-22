# MVP CFO Verification Wave 1 — Result

**Date:** 2026-08-21

Purpose: reduce the first current CFO review from 50 candidates to five high-confidence identity candidates, while keeping current registration status conservative.

## Wave

`DENTAL-CFO-VERIFICATION-WAVE1-5.csv` contains the first five manual checks:

1. Claudia Salete Judachesci — CRO-PR 22606
2. Gabriela Alves Pinto — CRO-PE 9029
3. Katleenn Martins Ferreira — CRO-MG 67976
4. Tainara Rieger Milnikel — CRO-RS 25342
5. Jessika Nascimento da Silva — CRO-PR 25373

## Official indexed evidence obtained

```text
WAVE_SIZE = 5
OFFICIAL_HISTORICAL_IDENTITY_MATCH = 5/5
OFFICIAL_CURRENT_SPECIALTY_LIST = 1/5
EXPLICIT_CURRENT_ACTIVE_STATUS = 0/5
PREPARATION_READY = 0/5
```

### Claudia Salete Judachesci — CRO-PR 22606

Current CRO-PR page `Especialistas em Harmonização Orofacial` lists:

```text
22606 | CLAUDIA SALETE JUDACHESCI
```

Source:

https://www.cropr.org.br/index.php/conteudo/especialistas-em-harmonizacao-orofacial/116

This is treated as **current official specialty evidence** for Harmonização Orofacial.

It is **not** converted to `VERIFIED_ACTIVE`, because the page does not explicitly state current registration status.

Historical CRO-PR records also associate PR-CD-22606 with the same current name through an apostilamento and with Harmonização Orofacial in a 2019 plenary record.

### Gabriela Alves Pinto — CRO-PE 9029

Official CRO-PE publication matches the name and CRO number historically:

https://www.cro-pe.org.br/site/adm_syscomm/publicacao/foto/132.pdf

No indexed current active-status source was found.

### Katleenn Martins Ferreira — CRO-MG 67976

Official CRO-MG minutes match the name and CRO number historically:

https://transparencia.cromg.org.br/baixar_documento/21425

No indexed current active-status or current specialty source was found.

### Tainara Rieger Milnikel — CRO-RS 25342

Official CRO-RS registration/cadastro documents match the name and CRO number historically:

https://transparencia.crors.org.br/wp-content/uploads/2019/12/Decis%C3%A3o-CRORS-52-2019-Setor-de-Cadastro-Delibera-Inscri%C3%A7%C3%B5es.pdf

No indexed current active-status or current specialty source was found.

### Jessika Nascimento da Silva — CRO-PR 25373

Official CRO-PR historical list matches the name and CRO number. A 2019 plenary record lists Endodontia for PR-CD-25373.

Sources:

https://www.cropr.org.br/uploads/arquivo/a05f651a729ed1808b709ce71d7f5ab4.pdf
https://www.cropr.org.br/uploads/transparencia/ata_plenaria_807.pdf

This does not disprove a later HOF/CEOF qualification; it means current specialty must be checked explicitly.

## Boundary confirmed

The CFO professional search page exposes CRO/UF, category, registration number, specialty, habilitation and name fields and reports update date 2026-08-21, but indexed web access does not expose individual result pages or a reusable documented result endpoint.

Therefore the MVP boundary remains:

```text
indexed official evidence
→ identity/specialty evidence when available
→ CURRENT ACTIVE STATUS still manual in CFO portal
```

No public profile or historical council document is promoted to `VERIFIED_ACTIVE` without current status evidence.
