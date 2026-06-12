# Workflow

Use this skill in two passes.

## Pass 1: Analyze and Confirm

Run `analyze` before editing repository docs.

Ask the human only about facts that cannot be derived safely from the repo, especially:

- product domain and top-level outcomes
- intended users or operators
- production reliability expectations
- security or compliance constraints
- frontend experience bar
- canonical external references worth pinning inside `docs/references/`

Do not ask for facts that can be inferred from source layout, dependency manifests, or existing docs.

Also inspect the analysis for:

- missing durable knowledge that should be written during the task
- missing execution-plan state
- which SOPs should be referenced in the generated router docs

## Pass 2: Init

Run `sample-answers`, fill the answers, then run `init`.

Use `init` for both first-time adoption and managed-harness reconciliation. It creates a new harness when none exists, and refreshes managed harness files plus backfills newly introduced managed files when an existing managed harness is detected. Unmanaged user files are preserved unless `--force` is explicitly used.

After the script runs, read the generated docs once and tighten weak generic phrases before handing off.

## Ongoing Use

After the scaffold exists:

- treat harness commands as Codex's execution interface, not as steps the user must manually run
- translate user intent like "complete this", "continue this later", "pause until X", "stop this", or "defer this" into the matching continuation decision yourself
- read `docs/exec-plans/workstreams.md` before resuming interrupted or long-running work
- create or reuse an execution plan before any repository-mutating work, including code, docs, configuration, tests, dependencies, build/release scripts, generated templates, runtime behavior, migrations, cleanup, or review fixes
- use `plan-start` instead of creating plan files manually when possible
- use `acceptance-set` before implementation so the active plan has a ready, task-specific Acceptance Contract
- log durable facts during execution instead of waiting until the end
- follow the matching SOP for architecture, UI, observability, or knowledge capture work
- route repository-mutating requests through Harness Task Intake in `AGENTS.md`; route product, frontend, backend, architecture, data/state, security, performance, and reliability issues through the Issue Workflows branch when the request is a bug or regression
- encode durable knowledge back into the repository before closing the task
- mark logged knowledge items as written after updating the permanent docs; the `knowledge-mark-written` evidence must be exact text already present in the destination doc, not a paraphrase
- log every defect found by tests, evals, browser validation, or code review with `defect-log`
- resolve logged defects only after fixing the implementation and citing passing validation with `defect-resolve`
- run `quality-score` after implementation and validation, with evidence notes for every dimension tied to the ready Acceptance Contract
- if `quality-score` fails, implement the `## Rework Required` items and score again
- use `continuation-set` before every `plan-close`; `continue` and `pause` update the workstream ledger automatically after required fields validate
- do not ask the user to invoke `continuation-set`, `plan-close`, or `check`; run them and summarize blocked reasons or successful state changes
- use `clean` when local skill installs or generated evidence need cleanup or were already committed; review dry-run output first, then apply, commit, and push the staged removals
- use `plan-close` to verify no durable knowledge is left stranded in the active plan
- before `plan-close`, replace generic plan placeholders with task-specific scope, constraints, steps, validation, and completion notes; delete unused ad hoc durable-knowledge TODOs
- run the installed manager `check` command before handoff; active plans require ready Acceptance Contracts, while completed plans require passing Quality Results
- preview stale generated evidence with `evidence-prune` when `docs/generated/` contains old screenshots, DOM dumps, layout summaries, or smoke outputs; review the dry-run output before using `--apply`
- do not add CI to the target repository unless the human explicitly asks for it

No-plan exceptions are limited to pure question answering, read-only investigation, showing command output, or status reporting with no file changes. If files will change, enter the plan lifecycle first.
