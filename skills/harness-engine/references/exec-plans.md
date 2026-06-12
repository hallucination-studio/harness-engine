# Execution Plans

Execution plans are required for every repository-mutating change. This includes code, docs, configuration, tests, dependencies, build/release scripts, generated templates, runtime behavior, migrations, cleanup, and fixes found during review.

## When To Create One

- any file will be edited or created
- repository behavior, policy, generated templates, dependency state, build output, runtime behavior, or validation coverage will change
- a review finding, user feedback item, bug, or regression requires a repository change
- work will span enough time that another agent may resume it later

Only skip a plan for pure question answering, read-only investigation, showing command output, or status reporting with no file changes. If the work moves from investigation to editing files, create or reuse an active plan before editing.

## Location

- Workstream recovery ledger: `docs/exec-plans/workstreams.md`
- Active: `docs/exec-plans/active/`
- Completed: `docs/exec-plans/completed/`

Active plans, completed plans, JSON sidecars, and `workstreams.md` are durable project state and should be version-controlled.

## Minimum Sections

- goal
- scope
- constraints
- steps
- validation
- acceptance contract
- quality result
- defects to resolve
- rework required
- continuation decision
- durable knowledge to capture
- completion notes

## Operating Rule

Update the active plan during the work. Define the Acceptance Contract before implementation, score the completed work against that contract, complete any required rework, record the continuation decision, move it to `completed`, and leave behind any durable facts in the right permanent docs.

For small changes, keep the plan lightweight: narrow scope, short steps, and focused validation are acceptable. Do not skip `acceptance-set`, evidence-backed validation, `quality-score`, `plan-close`, or the final `check`.

Before scoring or closing, replace generic starter text with task-specific content. Do not leave placeholders such as "Define in-scope work", "Add the first concrete step", or "Describe how the work will be verified". The default unused durable-knowledge line may remain open, but any real knowledge TODO must be logged, written, and marked complete.

## Closed Loop

Codex should use the script, not ad hoc manual edits, for the lifecycle. Users express intent in natural language; Codex translates that intent into these commands:

- `plan-start`: create a new active execution plan
- `acceptance-set`: write concrete product, UX, architecture, reliability, and security acceptance criteria before implementation; this updates the structured sidecar fingerprint
- `knowledge-log`: append a durable fact that still needs to be written into permanent docs and return its stable id; use `--fact-file` for shell-sensitive facts
- `knowledge-mark-written`: verify and mark a logged fact as written into its permanent doc; evidence must be exact text already present in the destination doc; prefer `--id <knowledge-id> --evidence-file <file>` for shell-sensitive evidence, and use `--append` only to append the exact fact first
- `defect-log`: record a bug found by validation, evals, browser testing, or code review; this invalidates any existing quality result and makes the defect the next rework input
- `defect-resolve`: mark a logged defect fixed with validation or code evidence; re-run validation and `quality-score` before closing
- `quality-score`: write a scored Quality Result into the plan based on the ready Acceptance Contract; every dimension must include an evidence note; if it fails, the generated `## Rework Required` section becomes the next implementation input
- `continuation-set`: declare whether the work is complete, continues, pauses, stops, or is deferred; `continue` and `pause` update `docs/exec-plans/workstreams.md` automatically after required fields validate, and `--goal` can set the resumable workstream goal
- `workstream-upsert`: manually update `docs/exec-plans/workstreams.md` when repairing or migrating resumable workstream state
- `plan-close`: refuse to close cleanly until the Acceptance Contract is ready, the Quality Result passes against the current contract fingerprint, the continuation decision is recorded, and the listed knowledge items are marked as written to durable docs; blocked closes return structured JSON with `status: "blocked"`, `reason`, `message`, and `details`
- `check`: run a local handoff check without requiring target-repo CI
