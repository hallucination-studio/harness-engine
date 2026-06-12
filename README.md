# Harness Engine

Harness Engine packages a Codex skill that bootstraps an agent-first repository harness.
It turns the repository-shaping ideas from OpenAI's
["Harness engineering: leveraging Codex in an agent-first world"](https://openai.com/index/harness-engineering/)
into an installable `npx` workflow.

The package does not install a harness into this repository. This repository builds and publishes
the installer. Users install the bundled `harness-engine` skill into their own project or
global Codex skill directory, then ask Codex to use that skill to analyze the target repository,
ask for missing high-impact facts, create the harness files, and keep future work closed-loop.

## What This Project Does

- Installs the `harness-engine` Codex skill locally, globally, or into a custom skills directory.
- Provides a repository analyzer that detects language, package manager, frontend signals, existing harness files, missing execution-plan state, and missing SOPs.
- Generates a short routing-style `AGENTS.md` plus durable system-of-record docs such as `ARCHITECTURE.md`, `docs/RELIABILITY.md`, `docs/SECURITY.md`, and `docs/QUALITY_SCORE.md`.
- Generates `docs/FRONTEND.md`, `docs/DESIGN.md`, and `docs/design-docs/` only when a frontend surface is detected.
- Creates version-controlled execution-plan folders for active and completed plans.
- Adds SOPs for architecture setup, knowledge capture, local observability, and UI validation.
- Reconciles managed harnesses through the same `init` flow, refreshing managed files and backfilling newly introduced managed files while preserving unmanaged docs.
- Provides `clean` to remove local skill installs and generated evidence, add `.gitignore` entries, and untrack already committed runtime artifacts so a follow-up commit deletes them from the remote.
- Enforces a local harness check without assuming the user's project has CI.
- Previews and optionally removes stale unreferenced generated evidence under `docs/generated/`.
- Supports durable knowledge closure with stable knowledge IDs and evidence text, so permanent docs can use natural wording instead of duplicated checklist strings.
- Enforces structured execution-plan state: `acceptance-set` creates a pre-implementation Acceptance Contract, `quality-score` records post-implementation evidence against that contract, and stale or failed scores block `plan-close`.
- Tracks resumable workstreams so interrupted features, refactors, reliability work, and cleanup efforts can be recovered from repo state instead of chat history.
- For frontend projects, asks for the desired visual style and initializes a repository-owned visual specification based on the local DESIGN.md format pattern: YAML design tokens plus markdown rationale.

## Why It Exists

The OpenAI harness engineering article argues that agent-first repositories work better when the
repo itself becomes the system of record: a short `AGENTS.md` routes agents into deeper docs,
execution plans live beside the code, and validation loops are mechanical rather than remembered.
This project packages that shape as a reusable Codex skill.

The goal is not to blindly copy a template. The skill first analyzes the target repo, then asks the
human to confirm product, reliability, security, frontend, and quality facts that cannot be safely
inferred from code alone.

## Install

The npm package is scoped as `@hallucination-studio/harness-engine`. The installed command name is
still `harness-engine`.

Install the latest stable release into the current repository:

```bash
npx @hallucination-studio/harness-engine install --local
```

Install the latest beta build from `main`:

```bash
npx @hallucination-studio/harness-engine@beta install --local
```

Install globally into `${CODEX_HOME:-~/.codex}/skills`:

```bash
npx @hallucination-studio/harness-engine install --global
```

Install into a custom skills directory:

```bash
npx @hallucination-studio/harness-engine install --path /path/to/skills
```

Replace an existing installed plugin bundle:

```bash
npx @hallucination-studio/harness-engine install --local --force
```

Show where the plugin bundle would be installed:

```bash
npx @hallucination-studio/harness-engine where --local
```

## Frontend Design Docs

Harness Engine has no external design runtime dependency and never calls an external design skill
during `init`. When a target repository has no frontend, it does not generate `docs/FRONTEND.md`,
`docs/DESIGN.md`, or `docs/design-docs/`.

When a frontend is detected, Harness Engine creates:

- `docs/FRONTEND.md`: project positioning, requested style direction, existing frontend code signals, frontend scope, stack notes, validation loop, and the read order for UI work.
- `docs/DESIGN.md`: a project-owned unified visual specification using YAML design tokens plus markdown rationale, seeded from the human-confirmed style direction and existing frontend code signals. It defines semantic colors, a unified typography scale, spacing/radius tokens, component states, and rules for mapping those tokens into the project's shared style layer.
- `docs/design-docs/`: durable design decisions and style-system notes.

The templates are informed by the local reference checkout at `/Users/murphy/code/github/design.md`
for document shape only. The target project owns the content and should replace starter tokens and
prose with its concrete product style before substantial UI work.

## Update An Installed Skill Package

The `npx` installer installs or replaces the Codex plugin bundle and compatibility skill entries.
To update an already installed bundle, rerun `install` with `--force` in the same install location.

Replace the local skill install:

```bash
npx @hallucination-studio/harness-engine install --local --force
```

Replace the global skill install:

```bash
npx @hallucination-studio/harness-engine install --global --force
```

Replace a custom skill install:

```bash
npx @hallucination-studio/harness-engine install --path /path/to/skills --force
```

After the skill package is installed, the target repository workflow happens inside Codex. In the
target workspace, invoke the skill:

```text
$harness-engine
```

The skill should analyze the workspace and run the single workspace entrypoint:

- If the harness is not installed in that repository, `manage_harness.py init` creates it.
- If a managed harness already exists, `manage_harness.py init` reconciles it by refreshing managed files and backfilling newly introduced managed files.
- Unmanaged user files are preserved unless `--force` is explicitly used.

The underlying command for both cases is:

```bash
python3 .codex/skills/harness-engine/scripts/manage_harness.py init --repo . --answers answers.json
```

## Use The Skill In A Target Repo

After installing, open Codex in the target repository and invoke:

```text
$harness-engine
```

The intended workflow is:

1. Analyze the target repository.
2. Ask the human only for unresolved, high-impact facts.
3. Initialize or reconcile the harness files.
4. Create or reuse execution plans for repository-mutating work, including code, docs, configuration, tests, dependencies, build/release scripts, generated templates, runtime behavior, migrations, cleanup, and review fixes.
5. Define the Acceptance Contract before implementation with product, UX, architecture, reliability, and security criteria.
6. Log durable knowledge into active plans.
7. Write the durable facts into permanent docs.
8. Mark knowledge as written using ID plus evidence text.
9. Score the finished work against the Acceptance Contract across product, UX/operator clarity, architecture, reliability, and security.
10. If the Quality Result fails, implement the generated `## Rework Required` items and score again.
11. For phased or resumable work, update `Phase Continuity` and `docs/exec-plans/workstreams.md`.
12. Close the execution plan only after the Quality Result passes against the current contract fingerprint, phase continuity is recorded, and durable docs are updated.
13. Run the local harness check before handoff.
14. Periodically run `evidence-prune` to preview stale unreferenced generated evidence, and apply it only after reviewing the candidate list.

The installed skill exposes the underlying script at:

```bash
python3 .codex/skills/harness-engine/scripts/manage_harness.py --help
```

For frontend or visual-design work, the generated harness uses `docs/FRONTEND.md` to route agents through `docs/DESIGN.md`. `docs/FRONTEND.md` defines which files are controlled by `docs/DESIGN.md`: design notes under `docs/design-docs/`, Tailwind theme files, global CSS variables, component theme modules, Storybook/theme previews, and UI implementation files that consume shared tokens or style rules. Agents should read `docs/FRONTEND.md`, then `docs/DESIGN.md`, then the relevant component, theme, or stylesheet.

Common commands:

```bash
python3 .codex/skills/harness-engine/scripts/manage_harness.py analyze --repo . --output analysis.json
python3 .codex/skills/harness-engine/scripts/manage_harness.py sample-answers --analysis analysis.json --output answers.json
python3 .codex/skills/harness-engine/scripts/manage_harness.py init --repo . --answers answers.json
python3 .codex/skills/harness-engine/scripts/manage_harness.py plan-start --repo . --slug feature-name --goal "Implement the feature"
python3 .codex/skills/harness-engine/scripts/manage_harness.py acceptance-set --repo . --plan docs/exec-plans/active/2026-06-11-feature-name.md --product "The feature satisfies the named user workflow and expected output." --ux "The user or operator can complete the workflow without ambiguous states." --architecture "The change fits the existing module boundaries and keeps plan state recoverable." --reliability "The validation commands and failure evidence are repeatable from a clean checkout." --security "The change introduces no secrets and preserves sensitive-data handling rules."
python3 .codex/skills/harness-engine/scripts/manage_harness.py quality-score --repo . --plan docs/exec-plans/active/2026-06-11-feature-name.md --product-correctness 8 --product-note "Product assertions passed" --ux-operator-clarity 8 --ux-note "User workflow evidence passed" --architecture-maintainability 8 --architecture-note "Boundary and maintainability review passed" --reliability-observability 8 --reliability-note "Tests and smoke checks passed" --security-data-handling 8 --security-note "No new sensitive-data paths or secrets"
python3 .codex/skills/harness-engine/scripts/manage_harness.py phase-set --repo . --plan docs/exec-plans/active/2026-06-11-feature-name.md --mode multi-phase --workstream feature-name --current-phase 1 --next-phase 2 --continuation docs/exec-plans/workstreams.md#feature-name --next-action "Create Phase 2 plan"
python3 .codex/skills/harness-engine/scripts/manage_harness.py workstream-upsert --repo . --id feature-name --status active --current-plan docs/exec-plans/active/2026-06-11-feature-name.md --next-action "Create Phase 2 plan"
python3 .codex/skills/harness-engine/scripts/manage_harness.py check --repo .
python3 .codex/skills/harness-engine/scripts/manage_harness.py evidence-prune --repo . --older-than-days 14
python3 .codex/skills/harness-engine/scripts/manage_harness.py evidence-prune --repo . --older-than-days 14 --apply
python3 .codex/skills/harness-engine/scripts/manage_harness.py clean --repo .
python3 .codex/skills/harness-engine/scripts/manage_harness.py clean --repo . --apply
```

The quality workflow is intentionally local and repository-owned. It does not require the user's
project to have CI. Active plans must have a ready Acceptance Contract sidecar so work is
recoverable before implementation finishes. Completed plans must have a passing Quality Result
scored against the current Acceptance Contract fingerprint; `plan-close` rejects stale scores,
open defects, unresolved placeholders, and unresolved durable knowledge. Blocked `plan-close`
commands return structured JSON with `status: "blocked"`, a stable `reason`, a user-readable
`message`, and machine-readable `details`.

## Version Control Policy

Commit harness docs that carry durable repository knowledge: `AGENTS.md`, `ARCHITECTURE.md`,
`docs/PLANS.md`, `docs/QUALITY_SCORE.md`, `docs/RELIABILITY.md`, `docs/SECURITY.md`,
`docs/FRONTEND.md`, `docs/sops/`, `docs/product-specs/`, `docs/design-docs/`,
`docs/references/`, and execution-plan state.

Execution plans are project state. Commit active plans, completed plans, JSON sidecars, and `docs/exec-plans/workstreams.md` so another agent can recover the work from the repository.

Do not commit local skill installs or generated evidence by default. `clean --apply` adds these directory-level ignores:

```gitignore
# harness-engine transient files
.codex/skills/
docs/generated/
# end harness-engine transient files
```

If those files were already committed or pushed, run:

```bash
python3 .codex/skills/harness-engine/scripts/manage_harness.py clean --repo .
python3 .codex/skills/harness-engine/scripts/manage_harness.py clean --repo . --apply
git status --short
git diff --cached --stat
git commit -m "Remove harness runtime artifacts from git"
git push
```

`clean --apply` removes local generated evidence, then uses `git rm --cached` to stage removal of tracked local skill installs and generated evidence from git and the remote. It does not remove, ignore, or untrack execution plans, JSON sidecars, or workstreams.

For multi-phase work, `Phase Continuity` and `docs/exec-plans/workstreams.md` form the recovery
ledger. A plan like `Local Workbench Phase 1` can close only after it records whether the workstream
continues, pauses, completes, or stops, and where the next agent should resume.

## Generated Harness Shape

A typical initialized target repository receives:

```text
AGENTS.md
ARCHITECTURE.md
docs/
├── DESIGN.md
├── FRONTEND.md
├── PLANS.md
├── PRODUCT_SENSE.md
├── QUALITY_SCORE.md
├── RELIABILITY.md
├── SECURITY.md
├── design-docs/
├── exec-plans/
│   ├── active/
│   ├── completed/
│   ├── workstreams.md
│   └── tech-debt-tracker.md
├── generated/
├── product-specs/
├── references/
└── sops/
```

`AGENTS.md` is intentionally short. It is a router, not an encyclopedia.

## Version Channels

- `latest`: Stable releases created from GitHub Release tags. The workflow derives the package version from the release tag and publishes to npm with the `latest` dist-tag.
- `beta`: Every push to `main` publishes a unique prerelease version like `1.0.0-beta.<run-number>.<short-sha>` with the `beta` dist-tag. npm cannot overwrite an existing version, so the `beta` tag moves forward to the newest main build.
- `nightly`: A scheduled daily build publishes versions like `1.0.0-nightly.<yyyymmdd>.<run-number>` with the `nightly` dist-tag.
- Manual test builds: The release workflow can be run manually. By default it performs `npm publish --dry-run` with a generated `-test.<run-number>` version. Set `dry_run=false` to publish a test package to a non-`latest` dist-tag such as `next`.

Examples:

```bash
npx @hallucination-studio/harness-engine install --local
npx @hallucination-studio/harness-engine@beta install --local
npx @hallucination-studio/harness-engine@nightly install --local
```

## Local Development

Run the skill evaluations:

```bash
npm test
```

Smoke-test installation:

```bash
npm run smoke:install
```

Check npm package contents:

```bash
npm run pack:check
```

Before release, run:

```bash
npm test
npm run smoke:install
npm run pack:check
git diff --check
```

The publish workflows expect an npm token when trusted publishing is not yet configured:

```text
GitHub Actions secret: NPM_TOKEN
```

## Implementation Quality Score

These scores describe the current implementation, not an external guarantee.

| Layer | Score | Notes |
| --- | ---: | --- |
| Product fit | 9 / 10 | Clear purpose: install a Codex skill that creates and maintains an agent-first repository harness. Real acceptance against a fresh Go backend plus browser frontend project validated generation and later issue workflows. Broader usage across more project types would still improve confidence. |
| Skill workflow design | 9.2 / 10 | Strong progressive workflow: analyze, confirm, init/reconcile, plan, capture knowledge, validate, score with evidence notes, rework, record continuity, close. The workflow now explicitly routes repository-mutating feature, bug, refactor, docs, dependency, UI, test, security, performance, and reliability work through the same lifecycle. |
| Knowledge, quality, and workstream closure loop | 9.3 / 10 | Stable knowledge IDs plus exact destination evidence reduce noisy doc duplication. Execution plans now have JSON sidecars for Acceptance Contracts, Quality Results, defects, and knowledge state; `quality-score` rejects missing evidence notes or missing contracts, defects invalidate stale scores, and workstreams make phased work recoverable. |
| CLI installer | 8 / 10 | Simple local/global/custom install modes, force replacement, and path discovery. It is intentionally minimal and does not manage Codex runtime configuration. |
| Generated harness docs | 8.4 / 10 | Covers architecture, plans, reliability, security, frontend policy, broad task intake, issue workflows, references, generated artifacts, and SOPs. The docs now front-load exact knowledge evidence, per-dimension quality notes, default plan lifecycle, and plan placeholder cleanup, but templates still require Codex to tighten project-specific language after generation. |
| Evaluation coverage | 9.2 / 10 | `npm test` runs 23 structured eval cases covering empty-repo init, frontend analysis, init reconciliation, clean command behavior, broad task intake, closed-loop plan behavior, phase continuity, path canonicalization, defect recovery, required quality-score notes, exact knowledge evidence, structured sidecars, acceptance readiness, stale score rejection, generated-evidence cleanup, eval report shape, user-owned doc preservation, and frontend design control. A fully automated Codex child-agent E2E would raise this further. |
| Release automation | 8 / 10 | Supports stable release, beta on every main commit, nightly, manual dry-run, artifacts, provenance, and token fallback. npm first-publish/trusted-publishing setup still requires external configuration. |
| User-project safety | 8.8 / 10 | The skill avoids adding CI to target projects by default, preserves unmanaged files unless forced, and requires evidence-backed closure for defects and durable knowledge. More destructive-change simulation in evals would improve this score. |
| Overall | 9.1 / 10 | The skill is now strong enough for regular use: self evals pass across the structured suite, real acceptance covered initial scaffold plus frontend and backend issue workflows, and plan lifecycle state is enforced through JSON sidecars. Remaining leverage is automated child-agent E2E coverage. |

## Reference

- OpenAI: [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)
