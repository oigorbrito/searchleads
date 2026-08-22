# MVP Regulatory Checkpoint — 2026-08-21

Purpose: keep the dental MVP campaign gate grounded in current official sources without turning a moving legal/regulatory dispute into an automatic product conclusion.

## Official framework currently published

The Conselho Federal de Odontologia continues to publish the 2026 Cirurgia Estética Orofacial (CEOF) framework and related technical guidance:

- CFO-SEC-286/2026 recognizes Cirurgia Estética Orofacial as a dental specialty, defines scope, procedures and formation requirements.
- CFO-SEC-285/2026 amends the earlier facial-surgery prohibition framework.
- CFO Technical Note 001/2026 addresses specialty-specific competence boundaries under the amended framework.
- CFO Technical Note 002/2026 continues to reference HOF, CTBMF and CEOF competence for Otomodelação according to training/scope.

Official CFO references:

- https://website.cfo.org.br/cirurgia-estetica-orofacial-e-oficialmente-regulamentada/
- https://website.cfo.org.br/notas-tecnicas/

## PDL 177/2026

The official Senado/Congresso record confirms that PDL 177/2026, authored by Sen. Dr. Hiran, proposes to sustain/suspend CFO Resolutions 283, 284, 285 and 286/2026.

As checked on 2026-08-21, the official Senado record reports:

```text
PDL = 177/2026
PRESENTED = 2026-04-01
STATUS = AGUARDANDO DESPACHO
LAST_RECORDED_ACTION = 2026-04-01
HOUSE = SENADO FEDERAL
```

Official references:

- https://www25.senado.leg.br/web/atividade/materias/-/materia/173445
- https://www.congressonacional.leg.br/materias/materias-bicamerais/-/ver/pdl-177-2026

A pending PDL is not itself encoded by SearchLeads as if the CFO resolutions were already suspended.

## Separate HOF litigation

The August 2026 TRF1 judgment discussed elsewhere in this branch concerns CFO Resolution 198/2019 (Harmonização Orofacial). SearchLeads keeps that litigation separate from the 2026 CEOF framework instead of treating the HOF case as an automatic direct suspension of CFO-SEC-285/286.

## MVP operational rule

The system does not make a categorical legal determination. It keeps campaign execution separate from lead preparation:

```text
PREPARATION_READY
= current official professional verification
+ eligible ICP / offer track
+ public professional contact

SEND_READY
= PREPARATION_READY
+ explicit current campaign legal/compliance confirmation
```

Current default remains:

```text
CampaignLegalStatus = PENDING_REVIEW
```

This lets discovery, qualification and official professional verification continue while the campaign sender remains conservative.
