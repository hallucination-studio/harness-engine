# Acceptance Runs

This file records concrete acceptance runs for the packaged `harness-engine` skill.
Keep reusable methodology in `docs/ACCEPTANCE_PLAN.md`; keep run-specific evidence here.

## 2026-06-12 No External Design Dependency Acceptance

### Scenario

- Source package: local checkout at `/Users/murphy/code/github/harness-engine`.
- Change under acceptance: Harness Engine does not depend on external design-generation skills,
  does not install or call design packages, and does not generate frontend/design docs for backend-only
  repositories. Frontend repositories receive local templates shaped by the DESIGN.md document
  pattern from `/Users/murphy/code/github/design.md`.

### Package Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| `npm test` | Pass | Evals passed, including `backend-init-skips-frontend-design-docs`, `frontend-design-control-plane`, `no-external-design-dependency`, and `pack-excludes-external-design-dependency`. |
| `npm run smoke:install` | Pass | Installed plugin root `harness-engine-plugin` plus compatibility `harness-engine` skill into a temporary skills directory. |
| `npm run pack:check` | Pass | Dry-run tarball included `.codex-plugin/plugin.json` and `skills/harness-engine/**`, and excluded external design source or adapter skills. |
| `git diff --check` | Pass | No whitespace errors. |

### Design Template Behavior

| Check | Result | Evidence |
| --- | --- | --- |
| Backend-only init skips UI docs | Pass | Backend-shaped repos do not receive `docs/FRONTEND.md`, `docs/DESIGN.md`, or `docs/design-docs/`. |
| Frontend init creates UI docs | Pass | Frontend-shaped repos receive `docs/FRONTEND.md`, `docs/DESIGN.md`, and `docs/design-docs/`. |
| `FRONTEND.md` controls readers | Pass | Generated `docs/FRONTEND.md` records project positioning, scope, stack notes, controlled files, and read order. |
| `DESIGN.md` is local template | Pass | Generated `docs/DESIGN.md` includes YAML tokens and markdown sections for Overview, Colors, Typography, Layout, Elevation & Depth, Shapes, Components, and Do's and Don'ts. |
| No external design dependency | Pass | README, SKILL.md, and generated templates do not instruct agents to call external design-generation skills or install design packages during init. |

### Findings

- Harness Engine now treats frontend/design docs as conditional outputs, not universal harness files.
- The design template is self-contained and project-owned. `/Users/murphy/code/github/design.md` is
  only a reference for document structure.
- Package checks still prevent external design source or local adapter skills from entering the
  install artifact.

### Acceptance Decision

Pass.

The updated acceptance gates prove that Harness Engine does not depend on external design-generation
tools during init, skips frontend/design docs for backend-only projects, and still creates a
structured frontend design control plane when a frontend is present.

## 2026-06-11 Clean-Repo Codex E2E

### Scenario

- Source package: local checkout at `/Users/murphy/code/github/harness-engine`.
- Target repository: `/tmp/harness-engine-acceptance-JzZCz7`.
- Install command: `node /Users/murphy/code/github/harness-engine/bin/install.js install --local --force`.
- Task: use `$harness-engine` to analyze an empty repo, initialize the harness, then implement a frontend/backend separated Snake game with a Go backend and static browser frontend.
- Constraint: do not add target-project CI.

### Package And Manager Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| `npm test` | Pass | All evals passed after adding path canonicalization coverage. |
| `npm run smoke:install` | Pass | Skill installed into a temporary local skills directory. |
| `npm run pack:check` | Pass | Dry-run tarball contains the package allowlist and excludes cache/build artifacts. |

### Target Harness Results

| Check | Result | Evidence |
| --- | --- | --- |
| Skill used before implementation | Pass | Codex invoked analyze, sample answers, init, plan-start, quality-score, phase-set, workstream-upsert, plan-close, and check. |
| Harness scaffold exists | Pass | `AGENTS.md`, `ARCHITECTURE.md`, policy docs, SOPs, references, workstreams, active/completed plan folders were created. |
| Active plan closure | Pass | `docs/exec-plans/active/` retained only `README.md` and `_template.md`; task plan moved to `docs/exec-plans/completed/2026-06-11-snake-game.md`. |
| Durable knowledge closure | Pass | Completed plan records three closed knowledge items with destinations/evidence. |
| Workstream recovery | Pass | `docs/exec-plans/workstreams.md` points at the completed Snake plan and records next action/resume notes. |
| Harness check | Pass | `manage_harness.py check --repo .` returned `status: pass`, `issue_count: 0`. |

### Target App Validation

| Check | Result | Evidence |
| --- | --- | --- |
| Backend tests | Pass | `go test ./...` passed for `cmd/snake-server`, `internal/game`, and `internal/server`. |
| Frontend syntax | Pass | `node --check web/static/app.js` passed. |
| HTTP API smoke | Pass | `/api/state`, `/api/direction`, `/api/tick`, and `/api/reset` returned valid JSON and expected state transitions. |
| Static serving | Pass | `/` returned the Snake Shell HTML; `/app.js` returned the browser client. |
| Browser rendering | Pass | In-app browser read title `Snake Shell`, score, direction, running state, board content, snake head, food, and reset control from the live DOM. |

### Review Scores

| Area | Score | Notes |
| --- | ---: | --- |
| Skill workflow adherence | 9.0 | The agent followed the intended analyze -> harness -> plan -> implement -> validate -> score -> capture knowledge -> close loop. |
| Harness quality | 8.5 | Router docs stayed short, durable docs became concrete, plan/workstream state closed correctly, and mechanical check passed. |
| Requirement completion | 8.0 | Go backend, static browser frontend, playable Snake behavior, run docs, and no CI were delivered. |
| Code cleanliness | 8.0 | Generated code has clear package boundaries and understandable tests, but game edge-case coverage missed one classic rule. |
| Architecture | 8.5 | `internal/game`, `internal/server`, `cmd/snake-server`, and `web/static` are separated with explicit API seams. |
| Reliability | 8.0 | Repeatable local tests and smoke checks exist; no target-project CI was introduced. |
| Overall | 8.3 | Accepted as a workflow validation with one generated-app bug and one harness usability issue discovered. |

### Findings

- P1 generated-app bug: `internal/game/game.go` checks self-collision before removing the tail on non-eating moves. Moving into the current tail cell should be legal in classic Snake, but an added review test failed against the generated app.
- P2 harness usability issue: `plan-close` initially failed when `--repo` resolved as `/private/tmp/...` while `--plan` was passed as `/tmp/...`. The manager now canonicalizes plan paths inside the repo before updating workstreams, and an eval covers this case.
- P3 validation limitation: the child Codex run reported browser automation unavailable, but the parent acceptance run successfully verified the served UI through the in-app browser afterward.

### Follow-Up Implemented

- Added `defect-log` and `defect-resolve` so bugs found by tests, evals, browser checks, or code review become active-plan state instead of chat-only observations.
- Updated `quality-score`, `check`, and `plan-close` so unresolved defects block handoff even when numeric scores are high.
- Added the `defect-recovery-loop` eval using the Snake tail-cell collision failure pattern as the motivating example.

### Acceptance Decision

Pass with follow-up.

The skill successfully induced the desired closed-loop harness workflow in a clean repository, including durable knowledge capture, quality scoring, workstream recovery, and plan closure. The generated Snake implementation is good enough to validate the workflow, but its tail-cell collision bug showed that bug discoveries must become mechanical plan state. The follow-up defect recovery loop now makes that failure mode block closure until fixed.

## 2026-06-11 Defect Recovery Skill Acceptance

### Scenario

- Source package: local checkout at `/Users/murphy/code/github/harness-engine`.
- Target repository: `/tmp/harness-skill-acceptance-PjIMg1`.
- Install command: `node /Users/murphy/code/github/harness-engine/bin/install.js install --local --force`, executed from the target repository.
- Task: verify the installed skill can initialize a harness, record a Snake tail-cell collision defect, block handoff, resolve the defect with evidence, rescore, close the plan, and pass `check`.

### Package Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| `npm test` | Pass | 7/7 evals passed, including `defect-recovery-loop`. |
| `npm run smoke:install` | Pass | Skill installed into a temporary local skills directory. |
| `npm run pack:check` | Pass | Dry-run package contains the expected 18 files and excludes repo-level acceptance docs. |

### Installed-Skill Results

| Check | Result | Evidence |
| --- | --- | --- |
| Local install into clean repo | Pass | `.codex/skills/harness-engine/` contained `SKILL.md`, `agents`, `evals`, `references`, and `scripts/manage_harness.py`. |
| Harness initialization | Pass | `analyze`, `sample-answers`, and `init` created the advanced harness scaffold. |
| Defect logging blocks quality | Pass | `defect-log` recorded `bug-f834b2fffd`; `quality-score` with all dimensions at `10` still returned `status: fail`. |
| Defect logging blocks handoff | Pass | `check` returned `quality-gate-not-passing` and `open-defect`; `plan-close` refused to close while the defect was open. |
| Defect resolution restores closure | Pass | `defect-resolve` recorded passing evidence, fresh `quality-score` returned `pass`, `plan-close` moved the plan to completed, and final `check` returned `issue_count: 0`. |
| Knowledge placeholder handling | Pass | Completed plan kept the default durable-knowledge placeholder open instead of marking it as completed. |

### Findings

- The first local install attempt ran from the source package directory and correctly installed into that directory's `.codex/skills`; local install semantics are cwd-based, so acceptance scripts must `cd` into the target repo before installing.
- The run exposed and fixed a closure bug where `plan-close` marked the default durable-knowledge placeholder as completed. The eval now guards against that regression.

### Acceptance Decision

Pass.

The installed skill now proves the intended bug recovery behavior mechanically: discovered defects become active plan state, unresolved defects fail scoring and handoff checks, and closure is only possible after resolution evidence and a fresh passing quality score.

## 2026-06-11 Evidence-First Eval Output Acceptance

### Scenario

- Source package: local checkout at `/Users/murphy/code/github/harness-engine`.
- Target repository: `/tmp/harness-engine-real-acceptance-scANUs`.
- Install command: `node /Users/murphy/code/github/harness-engine/bin/install.js install --local --force`, executed from the target repository.
- Task: verify the installed skill generates evidence-first eval guidance, emits structured eval reports, and blocks handoff when frontend evidence is incomplete.

### Package Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| `npm test` | Pass | 8/8 evals passed and emitted `harness-eval-report.v1` with aggregate metrics, per-case results, user message, and recommended actions. |
| `npm run smoke:install` | Pass | Skill installed into a temporary local skills directory. |
| `npm run pack:check` | Pass | Ran with `npm_config_cache=/tmp/harness-engine-npm-cache` because the default npm cache contained root-owned files; dry-run package included `references/evidence-first-evals.md`. |

### Codex CLI Limitation

Attempted a real `codex exec` child run from the clean target repo. It failed before agent execution with:

```text
Error: failed to initialize in-process app-server client: Operation not permitted (os error 1)
```

The installed skill was then validated directly through its packaged CLI in the target repository.

### Installed-Skill Results

| Check | Result | Evidence |
| --- | --- | --- |
| Local install into clean repo | Pass | `.codex/skills/harness-engine/` contained the updated skill, references, evals, and manager script. |
| Evidence-first SOP generation | Pass | `docs/sops/evidence-first-eval-loop.md` was generated by `init`. |
| Quality template upgrade | Pass | `docs/QUALITY_SCORE.md` contains `Evidence Requirements` and states that LLM/human judgment is a summary over evidence. |
| Frontend template upgrade | Pass | `docs/FRONTEND.md` contains `Evidence For Meaningful UI Work` with screenshot, DOM/accessibility, responsive, and layout-invariant requirements. |
| Product contract validation | Pass | `node validate-evidence.js` emitted `docs/generated/evidence-demo-validation.json` with 8/8 passing checks. |
| Evidence gap defect blocks handoff | Pass | Logged `bug-3853b54970`; `quality-score` failed despite average `9.6`, `check` returned `open-defect`, and `plan-close` refused closure. |
| Defect resolution restores closure | Pass | `defect-resolve` cited fallback browser evidence; fresh `quality-score` passed at `9.2`, `plan-close` moved the plan to completed, and final `check` returned `issue_count: 0`. |

### Findings

- The new eval output is user-presentable: it includes schema version, pass/fail status, score, aggregate metrics, per-case results, findings, user message, and recommended actions.
- Evidence gaps now behave like real defects. A missing frontend screenshot artifact blocked closure until it was resolved with explicit fallback evidence.
- The target validation script initially had a JavaScript regex syntax bug. This was fixed during acceptance and reinforced the value of treating validation failures as first-class evidence.
- Browser screenshot capture was not available through the attempted Codex child run, so the target repo recorded a limitation and fallback evidence in `docs/generated/evidence-demo-browser-fallback.md`.

### Acceptance Decision

Pass with environment limitation.

The package gates, installed-skill behavior, structured eval output, evidence-first generated docs, defect blocking, defect resolution, plan closure, and final harness check all passed. The only blocked part was spawning a real Codex child agent, which failed before task execution because of a local app-server permission error.

## 2026-06-11 Issue Workflows And Quality Notes Acceptance

### Scenario

- Source package: local checkout at `/Users/murphy/code/github/harness-engine`.
- Target repository: `/tmp/harness-snake-issue-workflows-ebeUCt`.
- Task: validate that the generated Issue Workflows route frontend/backend issue handling through
  the right docs, evidence, defect state, and quality gate in a frontend/backend separated Snake
  project with a Go backend.

### Package Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| `npm test` | Pass | 9/9 evals passed, including `quality-score-requires-notes`. |
| `npm run smoke:install` | Pass | Skill installed into a temporary local skills directory. |
| `npm run pack:check` | Pass | Ran with `npm_config_cache=/tmp/harness-engine-npm-cache`; package dry-run included the updated skill sources and references. |

### Target App And Harness Validation

| Check | Result | Evidence |
| --- | --- | --- |
| Frontend/backend project exists | Pass | Target repo contains a Go backend, static browser frontend, harness docs, and completed execution plans. |
| Backend tests | Pass | `go test ./...` passed. |
| Frontend static checks | Pass | `scripts/check_frontend.sh` passed. |
| API/browser smoke | Pass | `SNAKE_SMOKE_PORT=18081 scripts/smoke.sh` passed and wrote evidence under `docs/generated/evidence/`. |
| Browser DOM verification | Pass | In-app browser verified title, score, status, 144 board cells, snake cells, food cell, and controls at `http://127.0.0.1:18082`. |
| Harness check | Pass | `manage_harness.py check --repo .` returned `issue_count: 0`. |

### Issue Workflow Results

| Check | Result | Evidence |
| --- | --- | --- |
| Domain routing generated | Pass | `AGENTS.md` includes Issue Workflows for product, frontend, backend, architecture, data/state, security, and performance/reliability issues. |
| Frontend issue workflow | Pass | Frontend validation required browser or local-runtime evidence across relevant workflows and viewports rather than only subjective review. |
| Backend issue workflow | Pass | Backend validation required narrow reproduction, tests/API smoke checks, logs, and failure-mode evidence. |
| Defect state gates quality | Pass | Confirmed defects and evidence gaps are recorded through `defect-log`; unresolved defects block `quality-score`, `plan-close`, and `check`. |
| Evidence notes required | Pass | `quality-score` failed with `reason: missing-quality-notes` when notes were absent and named every missing dimension. |
| Evidence-backed quality passes | Pass | Re-running `quality-score` with product, UX, architecture, reliability, and security evidence notes passed at average `9.0`. |

### Findings

- The previous Issue Workflows were too frontend-focused for later backend and architecture issue
  prompts. The generated router now covers backend/API/runtime, architecture boundaries, data/state,
  security/privacy, and performance/reliability domains.
- Numeric quality scores were still possible without enough evidence. `quality-score` now requires
  evidence notes by default, with `--allow-empty-notes` only as an explicit escape hatch.
- Acceptance planning now includes a second pass that asks Codex concrete frontend and backend issue
  questions and verifies that fixes consult the right domain docs and pass the feature quality gate.

### Acceptance Decision

Pass.

The installed skill now validates both initial project creation and later issue handling: generated
Issue Workflows route frontend and backend problems through domain docs, reproduction evidence,
defect state, and an evidence-backed quality gate before handoff.
