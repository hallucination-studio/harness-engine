# Execution Plan: Python Runtime Split

## Goal

Split harness-engine Python runtime and eval monoliths into behavior-preserving packages while keeping public wrapper paths stable.

## Scope

- Split the source harness runtime and eval runner into Python packages under `skills/harness-engine/`.
- Keep `scripts/manage_harness.py` and `evals/run_evals.py` as executable compatibility wrappers.
- Update package/include and install-smoke validation so nested Python modules are shipped and installed.
- Leave generated `.codex/skills/**` copies untouched.

## Constraints

- Preserve command names, arguments, JSON output shape, and exit-code behavior.
- Use only Python standard library modules and existing npm scripts.
- Keep domain modules independent from CLI wrapper code.
- Treat existing evals as the primary regression signal.

## Steps

1. Move manager logic into cohesive `harness_engine` modules and leave the public script as a thin wrapper.
2. Move eval helpers, cases, registry, report builder, and runner into `harness_engine_evals` modules.
3. Update package file globs and smoke-install assertions for nested Python package files.
4. Run wrapper smoke checks, full evals, npm test, smoke install, and pack check.

## Validation

- `python3 skills/harness-engine/scripts/manage_harness.py --help`
- Representative `analyze`, `sample-answers`, and `quality-score` failure-path CLI checks.
- `python3 skills/harness-engine/evals/run_evals.py`
- `npm test`
- `npm run smoke:install`
- `npm run pack:check`

## Acceptance Contract

Status: ready
Fingerprint: 27e2877eda920a22

| Dimension | Criteria |
| --- | --- |
| Product correctness | The existing manage_harness.py and evals/run_evals.py public entrypoint paths remain executable with the same commands, arguments, JSON schemas, and exit-code behavior. |
| UX and operator clarity | Developers can continue using python3 skills/harness-engine/scripts/manage_harness.py, python3 skills/harness-engine/evals/run_evals.py, npm test, smoke:install, and pack:check without learning new commands. |
| Architecture and maintainability | Runtime logic is moved into cohesive standard-library-only Python packages under scripts/harness_engine and evals/harness_engine_evals with one-way imports and thin wrappers. |
| Reliability and observability | All 23 harness eval cases pass after the split, representative CLI smoke commands pass, and package/install checks include nested Python modules. |
| Security and data handling | The refactor does not introduce new dependencies, network calls, credential handling, or broader filesystem side effects beyond the existing CLI behavior. |
## Quality Result

Status: pass
Minimum score: 8.0
Average score: 9.0
Last scored: 2026-06-12T03:46:55Z
Criteria fingerprint: 27e2877eda920a22

| Dimension | Score | Evidence |
| --- | ---: | --- |
| Product correctness | 9.0 | python3 skills/harness-engine/scripts/manage_harness.py --help, analyze, sample-answers, and quality-score failure-path CLI checks produced expected JSON/CLI outputs. |
| UX and operator clarity | 9.0 | npm test, npm run smoke:install, and npm run pack:check remained the same developer commands and passed. |
| Architecture and maintainability | 9.0 | Reviewed code paths skills/harness-engine/scripts/harness_engine/cli.py, skills/harness-engine/scripts/manage_harness.py, skills/harness-engine/evals/harness_engine_evals/registry.py, and skills/harness-engine/evals/run_evals.py after py_compile passed. |
| Reliability and observability | 9.0 | python3 skills/harness-engine/evals/run_evals.py and npm test both passed all 23 harness eval cases. |
| Security and data handling | 9.0 | Review of changed files shows no new dependencies, network calls, credential paths, or expanded sensitive-data handling. |
## Defects To Resolve

None.

## Rework Required

None. Quality Result passed.
## Continuation Decision

Decision: complete
Workstream: none
Next target: none
Next action: none
Closure reason: The runtime split is complete and has no follow-up workstream.
Resume notes: none
## Durable Knowledge To Capture

- [ ] Add durable facts here as they emerge -> <destination-doc>

## Completion Notes

Split the harness-engine manager and eval runner into packaged Python modules while preserving public wrapper paths, package install shape, and eval behavior.
