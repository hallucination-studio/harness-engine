# Execution Plan: Harness Default Intake

## Goal

Make harness lifecycle the default for repository-mutating work and keep execution plans under version control.

## Scope

- Update the skill workflow, generated harness docs, references, clean behavior, and eval coverage for default repository-change intake.
- Keep installer mechanics and unrelated frontend-design behavior out of scope.

## Constraints

- Preserve managed-file reconciliation semantics.
- Do not let `clean` remove, untrack, or ignore execution-plan state.
- Keep local skill installs and generated evidence as the only default transient directories.

## Steps

1. Update generated templates and references to make the lifecycle default for repository-mutating work.
2. Restrict clean and version-control policy to directory-level runtime state.
3. Add eval coverage for broad task intake and plan-state preservation.
4. Run evals and package smoke checks.

## Validation

- Run `python3 skills/harness-engine/evals/run_evals.py`.
- Run `npm run smoke:install`.
- Run `npm run pack:check`.

## Acceptance Contract

Status: ready
Fingerprint: 3b6f29e4322d74bd

| Dimension | Criteria |
| --- | --- |
| Product correctness | Generated harness docs route every repository-mutating request through plan-start, acceptance-set, validation, quality-score, plan-close, and check, with only explicit read-only/no-file-change exceptions. |
| UX and operator clarity | AGENTS.md and references make the broad task intake easy for a future agent to follow without relying on issue or bug keywords. |
| Architecture and maintainability | The manager keeps execution plans, JSON sidecars, and workstreams as durable project state while restricting clean and .gitignore behavior to local runtime directories. |
| Reliability and observability | Eval coverage proves clean ignores plan state and generated docs include broad task intake for feature, bug, refactor, docs, dependency, UI, test, security, and performance work. |
| Security and data handling | The lifecycle and clean changes do not introduce secret handling changes and continue to keep local skill installs and generated evidence out of version control by default. |
## Quality Result

Status: pass
Minimum score: 8.0
Average score: 8.8
Last scored: 2026-06-12T02:46:35Z
Criteria fingerprint: 3b6f29e4322d74bd

| Dimension | Score | Evidence |
| --- | ---: | --- |
| Product correctness | 9.0 | Generated AGENTS.md, PLANS.md, active plan README, and evidence-first SOP now route repository-mutating work through plan-start, acceptance-set, validation, quality-score, plan-close, and check; eval broad-task-intake-routes-repo-changes passed. |
| UX and operator clarity | 9.0 | Harness Task Intake is a top-level AGENTS.md section with scenario routing, no-plan exceptions, and evidence requirements; empty-repo-init and broad-task-intake evals passed. |
| Architecture and maintainability | 9.0 | CLEAN_INIT_DIRS and GIT_CLEAN_PATHS now include only docs/generated and .codex/skills respectively; clean eval preserves active/completed plans, JSON sidecars, and workstreams. |
| Reliability and observability | 9.0 | python3 skills/harness-engine/evals/run_evals.py passed 23/23 cases, npm run smoke:install passed, and npm run pack:check passed. |
| Security and data handling | 8.0 | No secret-handling paths changed; version-control policy still ignores local skill installs and generated evidence while keeping durable plan state tracked. |
## Defects To Resolve

None.

## Rework Required

None. Quality Result passed.
## Phase Continuity

Mode: single-phase
Workstream: none
Current phase: none
Next phase: none
Continuation: none
Next action: none
Closure reason: This plan is not part of a longer workstream.
Resume notes: none

## Durable Knowledge To Capture

- [ ] Add durable facts here as they emerge -> <destination-doc>

## Completion Notes

Updated harness default intake, clean/version-control policy, references, README, and eval coverage; validation passed.
