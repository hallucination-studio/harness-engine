# Harness Engine

Harness Engine packages a Codex skill that bootstraps an agent-first repository harness.
It turns the repository-shaping ideas from OpenAI's
["Harness engineering: leveraging Codex in an agent-first world"](https://openai.com/index/harness-engineering/)
into an installable `npx` workflow.

The package does not install a harness into this repository. This repository builds and publishes
the installer. Users install the bundled `harness-repo-bootstrap` skill into their own project or
global Codex skill directory, then ask Codex to use that skill to analyze the target repository,
ask for missing high-impact facts, create the harness files, and keep future work closed-loop.

## What This Project Does

- Installs the `harness-repo-bootstrap` Codex skill locally, globally, or into a custom skills directory.
- Provides a repository analyzer that detects language, package manager, frontend signals, existing harness files, missing execution-plan state, and missing SOPs.
- Generates a short routing-style `AGENTS.md` plus durable system-of-record docs such as `ARCHITECTURE.md`, `docs/RELIABILITY.md`, `docs/SECURITY.md`, `docs/QUALITY_SCORE.md`, and `docs/FRONTEND.md`.
- Creates execution-plan folders for active and completed plans.
- Adds SOPs for architecture setup, knowledge capture, local observability, and UI validation.
- Enforces a local harness check without assuming the user's project has CI.
- Supports durable knowledge closure with stable knowledge IDs and evidence text, so permanent docs can use natural wording instead of duplicated checklist strings.

## Why It Exists

The OpenAI harness engineering article argues that agent-first repositories work better when the
repo itself becomes the system of record: a short `AGENTS.md` routes agents into deeper docs,
execution plans live beside the code, and validation loops are mechanical rather than remembered.
This project packages that shape as a reusable Codex skill.

The goal is not to blindly copy a template. The skill first analyzes the target repo, then asks the
human to confirm product, reliability, security, frontend, and quality facts that cannot be safely
inferred from code alone.

## Install

Install the latest stable release into the current repository:

```bash
npx harness-engine install --local
```

Install the latest beta build from `main`:

```bash
npx harness-engine@beta install --local
```

Install globally into `${CODEX_HOME:-~/.codex}/skills`:

```bash
npx harness-engine install --global
```

Install into a custom skills directory:

```bash
npx harness-engine install --path /path/to/skills
```

Replace an existing installed skill:

```bash
npx harness-engine install --local --force
```

Show where the skill would be installed:

```bash
npx harness-engine where --local
```

## Use The Skill In A Target Repo

After installing, open Codex in the target repository and invoke:

```text
$harness-repo-bootstrap
```

The intended workflow is:

1. Analyze the target repository.
2. Ask the human only for unresolved, high-impact facts.
3. Initialize or update the harness files.
4. Create execution plans for multi-step work.
5. Log durable knowledge into active plans.
6. Write the durable facts into permanent docs.
7. Mark knowledge as written using ID plus evidence text.
8. Run the local harness check before handoff.
9. Close the execution plan only after the durable docs are updated.

The installed skill exposes the underlying script at:

```bash
python3 .codex/skills/harness-repo-bootstrap/scripts/manage_harness.py --help
```

Common commands:

```bash
python3 .codex/skills/harness-repo-bootstrap/scripts/manage_harness.py analyze --repo . --output analysis.json
python3 .codex/skills/harness-repo-bootstrap/scripts/manage_harness.py sample-answers --analysis analysis.json --output answers.json
python3 .codex/skills/harness-repo-bootstrap/scripts/manage_harness.py init --repo . --answers answers.json
python3 .codex/skills/harness-repo-bootstrap/scripts/manage_harness.py plan-start --repo . --slug feature-name --goal "Implement the feature"
python3 .codex/skills/harness-repo-bootstrap/scripts/manage_harness.py check --repo .
```

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
npx harness-engine install --local
npx harness-engine@beta install --local
npx harness-engine@nightly install --local
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

The publish workflows expect an npm token when trusted publishing is not yet configured:

```text
GitHub Actions secret: NPM_TOKEN
```

## Implementation Quality Score

These scores describe the current implementation, not an external guarantee.

| Layer | Score | Notes |
| --- | ---: | --- |
| Product fit | 8.5 / 10 | Clear purpose: install a Codex skill that creates and maintains an agent-first repository harness. The main missing piece is broader real-world usage data across more project types. |
| Skill workflow design | 8.5 / 10 | Strong progressive workflow: analyze, confirm, initialize/update, plan, capture knowledge, validate, close. The current skill is opinionated but still adapts to target repositories. |
| Knowledge-closure loop | 8 / 10 | Stable knowledge IDs plus evidence text reduce noisy doc duplication. Future work could move plan state into structured sidecar metadata instead of Markdown parsing. |
| CLI installer | 8 / 10 | Simple local/global/custom install modes, force replacement, and path discovery. It is intentionally minimal and does not manage Codex runtime configuration. |
| Generated harness docs | 7.5 / 10 | Covers architecture, plans, reliability, security, frontend policy, references, generated artifacts, and SOPs. Templates still require Codex to tighten project-specific language after generation. |
| Evaluation coverage | 7.5 / 10 | Includes empty-repo init, frontend analysis, closed-loop plan behavior, user-owned doc preservation, and installer smoke tests. More end-to-end Codex acceptance tests would raise confidence. |
| Release automation | 8 / 10 | Supports stable release, beta on every main commit, nightly, manual dry-run, artifacts, provenance, and token fallback. npm first-publish/trusted-publishing setup still requires external configuration. |
| User-project safety | 8.5 / 10 | The skill avoids adding CI to target projects by default and uses local harness checks instead. It preserves unmanaged files unless forced. |
| Overall | 8.1 / 10 | Usable and coherent, with the highest leverage still in richer evals and more structured plan/knowledge state. |

## Reference

- OpenAI: [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)
