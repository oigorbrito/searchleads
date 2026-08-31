# ENGINEERING_GOVERNANCE

Status: CANONICAL
Authority: governs how SearchLeads distinguishes baseline decisions from experimental evidence.

## Incident Record

- PR `#113` (`Chassis bake-off v1`) was merged on GitHub.
- The merge diverged from the previously stated laboratory-only expectation for that experiment.
- The merge does not by itself promote the experiment to canonical baseline.
- Experimental evidence and canonical implementation remain distinct concepts even when experimental commits become part of repository ancestry.

## Governance Rules

- Experimental PRs may produce evidence.
- Any promotion from experiment to baseline must be explicit.
- Merge of a PR does not automatically imply architectural acceptance.
- Canonical decisions continue to be governed by the baseline documents and ADRs.
- Future experimental merges must not be treated as implicit baseline adoption.

## Interpretation Rule

- If an experiment lands in ancestry, treat it as historical evidence until a canonical document or ADR explicitly adopts it.
- If canonical baseline and implementation diverge, the divergence must be recorded and reconciled rather than assumed away.

