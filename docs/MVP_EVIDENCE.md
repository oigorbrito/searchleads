# SearchLeads MVP Evidence

Run `python scripts/run_mvp_evaluation.py` from the repository root. The command writes:

- `evaluation/runs/<run-id>/environment.json`
- `evaluation/runs/<run-id>/config.json`
- `evaluation/runs/<run-id>/raw_results.json`
- `evaluation/runs/<run-id>/metrics.json`
- `evaluation/runs/<run-id>/decision.json`
- `evaluation/baseline.json`

`raw_results.json` preserves the complete deterministic acceptance result. `decision.json` is `PASS` only when the technical path is reproducible, persistence replay is byte-preserving, and company ER produces `AUTO_MATCH`. Live network, commercial qualification, and multi-source enrichment remain explicit non-PASS states from the underlying acceptance contract.

Compare a candidate metrics file with `python scripts/compare_candidate.py evaluation/baseline.json <candidate-metrics.json>`.
