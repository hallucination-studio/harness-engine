# Acceptance Plan

This repository ships an installable Codex skill. Acceptance must prove both the package mechanics
and the agent-facing harness workflow.

## Acceptance Goals

- The npm package installs the bundled `harness-repo-bootstrap` skill without extra build output.
- The deterministic manager commands protect the closed loop: analyze, scaffold, plan, knowledge capture, quality score, phase continuity, workstream recovery, plan close, and check.
- A fresh target repository can install the skill locally and have Codex use it to create a harness before implementing real work.
- The generated work is reviewed for requirement fit, code quality, maintainability, and whether the harness workflow actually shaped the implementation.

## Required Gates

Run these from the repository root before release or after changing skill behavior:

```bash
npm test
npm run smoke:install
npm run pack:check
```

Passing criteria:

- `npm test` reports every eval as `pass`.
- `npm test` emits `harness-eval-report.v1` JSON with aggregate metrics, per-case results,
  findings, a user-facing message, and recommended actions for failed cases.
- `smoke:install` installs the skill into a temporary skills directory.
- `pack:check` includes `SKILL.md`, `agents`, `assets`, `references`, `scripts`, and eval sources, but does not include `__pycache__`, `.pyc`, local `.codex`, or tarball artifacts.

## Codex E2E Scenario

Use a clean temporary repository to avoid leaking local state:

```bash
TARGET_DIR="$(mktemp -d /tmp/harness-engine-acceptance-XXXXXX)"
git -C "$TARGET_DIR" init
node /path/to/harness-engine/bin/install.js install --local --force
codex exec --cd "$TARGET_DIR" --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox - < acceptance-prompt.txt
```

The prompt must require Codex to:

- Use `$harness-repo-bootstrap`.
- Analyze the empty repository before creating docs.
- Create or update the harness with concrete project answers.
- Start an execution plan before implementation.
- Implement a frontend/backend separated Snake game with a Go backend and browser frontend.
- Avoid adding CI.
- Capture durable knowledge into permanent docs.
- Log any test, eval, browser, or code-review bug with `defect-log`.
- Resolve logged bugs with `defect-resolve` and explicit passing evidence before scoring again.
- Treat product requirements, frontend layout checks, and bug regressions as evidence-first eval cases, not only subjective score notes.
- Run `quality-score`; if it fails, rework before closing.
- Use `phase-set`, `workstream-upsert`, `plan-close`, and `check`.
- Report validation commands and artifact paths.

Passing criteria:

- `AGENTS.md`, `ARCHITECTURE.md`, `docs/PLANS.md`, `docs/QUALITY_SCORE.md`, `docs/RELIABILITY.md`, `docs/SECURITY.md`, `docs/FRONTEND.md`, `docs/exec-plans/workstreams.md`, and `docs/sops/` exist.
- `docs/exec-plans/active/` contains no task plan after completion.
- `docs/exec-plans/completed/` contains the completed plan.
- Completed plan has `Quality Gate` status `pass` with average score at least `8.0`.
- Any discovered defect is recorded under `Defects To Resolve`, blocks `quality-score`, and is resolved with evidence before `plan-close`.
- Eval or validation results shown to the user include concrete failed cases, evidence gaps, artifact paths when available, and recommended next actions.
- Completed plan has no open durable knowledge items.
- `docs/exec-plans/workstreams.md` points at the completed plan path, not the old active path.
- `python3 .codex/skills/harness-repo-bootstrap/scripts/manage_harness.py check --repo .` passes.
- The target app validates with its own commands, including backend tests and frontend syntax checks.
- If a browser is available, the UI is opened and key user-visible states are verified. If browser automation is blocked, the limitation is recorded and API/static smoke checks must still pass.

## Review Rubric

Score the result from `0` to `10` in each area:

| Area | What To Look For |
| --- | --- |
| Skill workflow adherence | Did Codex follow the harness lifecycle instead of only writing code? |
| Harness quality | Are router docs short, durable docs concrete, plans closed, workstreams recoverable, and checks mechanical? |
| Requirement completion | Does the generated app implement the requested behavior without adding forbidden infrastructure? |
| Code cleanliness | Are names, file boundaries, tests, and control flow understandable? |
| Architecture | Is frontend/backend separation real, and are integration seams explicit? |
| Reliability | Are validation commands meaningful and repeatable without target-project CI? |
| Gaps and risks | Are browser/tooling limitations, fragile commands, or remaining bugs stated honestly? |

Overall acceptance should fail if any required gate fails, if `check` fails in the target repo, or if Codex closes the plan without passing quality score and durable knowledge closure.
