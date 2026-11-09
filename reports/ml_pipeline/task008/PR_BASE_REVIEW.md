# PR #4 review and TASK008 base selection — 2026-11-08

Live GitHub connector and `gh pr view 4 --repo acchasujal/aqi --json number,state,headRefName,headRefOid,baseRefName,baseRefOid,url` confirm [PR #4](https://github.com/acchasujal/aqi/pull/4) is OPEN, unmerged, head `d7bfbdbaa0b112d8dc2c9341cd731287d4b57d92`. GitHub reports mergeable=false. PR metadata still reports the old base SHA `9d3fad0afb25b3247bb564464a5e6a090e107444`; the live compare endpoint and refreshed origin/main identify current main as `d9bead48951b3f584ce4a8e0ba79f97950fa1edb`, with two commits ahead and ten behind. Distinguish the stale PR base field from the actual main tip.

Starting checkout was clean at the exact PR head. Local main is stale at `c5e6a3f`; origin/main was refreshed with `git fetch origin`. TASK008 branch `feature/task008-final-gap-execution` is based on the reviewed PR head. This keeps the repaired exact-source loader and shared baseline available without merging either branch or discarding main's work. Main's newer EXP-008–015 code/reports were inspected with `git show`; their experimental code is not silently combined with this branch. Integration into main requires a separate conflict review.

## Code findings

- Production P_FIX_SERIES matches the requested exact IDs and excludes Mindspace. Provenance fields survive loading; source identity is a predictive policy, not a physical equivalence claim.
- Shared median72 has the same 72 elapsed-hour boundary and all-history median fallback in inference and validation. The diur7 control is the historical capped/filtered profile, with an explicit support gate. It can be missing and cannot silently define evaluation eligibility for all models.
- The old TASK007 seasonal script contains P_FIX_SPEC with Mindspace, although its selected P_fix output uses a different development-selected map. This ambiguity makes it unsuitable as the new common evaluator. TASK008 uses the production P_FIX_SERIES directly.
- Archive timestamp semantics remain a hypothesis. Calendar mapping uses month/day in leap-year 2024; it is not proof of interval semantics.
- Validation previously discards nonfinite candidate rows and reports candidate-specific metrics. TASK008 must retain all eligible labelled rows and report missing prediction coverage; unsupported candidates cannot win by scoring a subset.
- A potential unavailable-source lookup in per-source sum metadata is repaired and regression tested in TASK008 before use.

## Generated artifacts and evidence

PR #4 changes 159 files, including many repeated seasonal/supervised OOF runs. Reviewed Python separately with local Git diffs. None of those generated CSVs is imported as a new candidate's validation prediction. Candidate files and manifests, including superseded files, are frozen in candidate_provenance.json and input_hashes.txt. Main's EXP-013/014/015 conclusions retain W50 and explicitly acknowledge reused folds, tail dominance and no reliable challenger; these inform conservative promotion, not a score transfer to P_fix.

## Executed checks on selected base

`.venv\Scripts\python.exe -m pytest -q --basetemp .task008-test-tmp`: **44 passed**, one cache permission warning. Initial default-temp run: 42 passed, two fixture permission errors; no model test failed. Scoped Ruff over ML code/scripts and ML tests is executed again in the final audit. A broader check including creative tests found the pre-existing import ordering in tests/test_forecast_artifact.py; no creative change is included.

Disposition: **keep PR #4 isolated and revise within TASK008**, no automatic merge. Confidence high in the identity-preserving implementation intent, limited in source semantics and model superiority. The common evaluator and future perturbation/parity tests gate new experiments.
