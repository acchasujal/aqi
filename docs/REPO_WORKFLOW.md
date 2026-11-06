# Repository Workflow, Branching and Merge-Conflict Policy

## Branch model

- `main`: always runnable, reviewed, documented.
- `feature/<task-id>-<short-name>`: one coherent change per branch.
- `experiment/<experiment-id>`: isolated experiment implementation/results.
- Do not commit directly to `main` except by explicit project-owner instruction.

## Avoid concurrent file ownership

Before parallel agents start, assign each a task and a file ownership list. Two agents must not edit the same core module, config or log simultaneously. Prefer separate modules/config files and integrate through a reviewed PR.

## Pull request size

A PR should contain one logical change. Avoid combining model experiments, data pipeline rewrites, formatting-only changes and documentation restructuring in one PR.

## Merge-conflict strategy

1. Fetch latest `main`; do not force-push.
2. Inspect conflict markers and both semantic changes.
3. For `DECISIONS.md` and `PROGRESS.md`, preserve all unique entries. Never discard a valid agent log entry to resolve a conflict.
4. For experiment logs, preserve unique experiment IDs; reject duplicated IDs and reconcile timestamps/status.
5. For configs, compare actual parameter changes; do not choose a whole-file side without review.
6. For generated reports, regenerate from source artifacts where possible instead of hand-merging large outputs.
7. For source code, merge intent, add/update tests, then run the full relevant test set.
8. Search for leftover `<<<<<<<`, `=======`, `>>>>>>>` markers.
9. Record the conflict resolution in `PROGRESS.md`; add a decision only if a lasting policy changed.

## Log merge hygiene

- Append-only logs are still mergeable text files; conflicts are resolved by retaining both new entries and ordering by date then ID.
- Use stable IDs generated from date plus a local sequence. If two branches generated the same ID, assign a new ID during merge and reference the old provisional ID.
- Do not reformat/reflow historic entries.
- If parallel agents create frequent log conflicts, each agent writes a separate `reports/agent_logs/<task-id>.md`, and a designated integrator appends a consolidated entry to `PROGRESS.md`.

## Commit messages

Use concise conventional prefixes: `docs:`, `data:`, `feat:`, `fix:`, `test:`, `exp:`, `chore:`. Include task/experiment ID where possible.
