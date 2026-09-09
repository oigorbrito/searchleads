# SearchLeads MVP Scope

The internal MVP covers the smallest evidence-backed path:

`input -> discovery -> company entity resolution -> enrichment -> contact discovery -> validation -> qualification -> export/review`

Campaign sending, CRM automation, production-scale infrastructure, and live commercial certification are outside this MVP gate.

The canonical deterministic workload is `tests/fixtures/end_to_end_acceptance_v1.json`. Its acceptance runner is `python scripts/run_mvp_evaluation.py`.
