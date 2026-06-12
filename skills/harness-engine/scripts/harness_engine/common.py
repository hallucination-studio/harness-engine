import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

MANAGED_MARKER = "<!-- harness-engine:managed -->"
OBSOLETE_MANAGED_MARKERS = [
    "<!-- harness-repo-bootstrap:managed -->",
    "<!-- harness-init:managed -->",
]
DEFAULT_KNOWLEDGE_PLACEHOLDER = "- [ ] Add durable facts here as they emerge -> <destination-doc>"
DEFAULT_DEFECT_PLACEHOLDER = "None."
PLAN_PLACEHOLDERS = [
    "Define in-scope work.",
    "Define out-of-scope work.",
    "Add relevant product, architecture, reliability, security, or delivery constraints.",
    "Add the first concrete step.",
    "Add the next concrete step.",
    "Add the next step.",
    "Describe how the work will be verified.",
    "List product, architecture, reliability, security, or delivery constraints.",
    "Describe what is included and excluded.",
]
GITIGNORE_BLOCK_START = "# harness-engine transient files"
GITIGNORE_BLOCK_END = "# end harness-engine transient files"
GITIGNORE_ENTRIES = [
    ".codex/skills/",
    "docs/generated/",
]
CLEAN_INIT_DIRS = [
    "docs/generated",
]
GIT_CLEAN_PATHS = [
    ".codex/skills",
    "docs/generated",
]
PLAN_TEMPLATE = """# Execution Plan: {title}

## Goal

{goal}

## Scope

- Define in-scope work.
- Define out-of-scope work.

## Constraints

- Add relevant product, architecture, reliability, security, or delivery constraints.

## Steps

1. Add the first concrete step.
2. Add the next concrete step.

## Validation

- Describe how the work will be verified.

## Acceptance Contract

Status: draft
Fingerprint: pending

Run `acceptance-set` before implementation to define specific product, UX, architecture, reliability, and security acceptance criteria.

| Dimension | Criteria |
| --- | --- |
| Product correctness | pending |
| UX and operator clarity | pending |
| Architecture and maintainability | pending |
| Reliability and observability | pending |
| Security and data handling | pending |

## Quality Result

Status: pending
Minimum score: 8.0
Average score: pending
Last scored: pending
Criteria fingerprint: pending

Run `quality-score` after implementation and validation. Scores must cite evidence for the ready acceptance contract.

## Defects To Resolve

{defect_section}

## Rework Required

- Acceptance Contract is not ready.

## Continuation Decision

Decision: pending
Workstream: none
Next target: none
Next action: none
Closure reason: none
Resume notes: none

## Durable Knowledge To Capture

{knowledge_section}

## Completion Notes

Pending.
"""

ROOT_FILES = {
    "AGENTS.md": """{marker}
# AGENTS

Read this file first, then follow the linked docs.

## Routing

- Read `ARCHITECTURE.md` before changing boundaries, data flow, or integrations.
- Read `docs/PLANS.md` before any repository change. Every code, doc, config, test, dependency, build, release, or runtime-behavior change needs an execution plan.
- Read `docs/exec-plans/workstreams.md` before resuming interrupted feature, refactor, reliability, security, frontend, or cleanup work.
- Read `docs/exec-plans/active/` before changing files; use `plan-start` when no active plan covers the requested repository change.
- Read `docs/QUALITY_SCORE.md` before evaluating tradeoffs or readiness.
- Read `docs/RELIABILITY.md` for runtime validation and failure handling.
- Read `docs/SECURITY.md` before touching auth, secrets, permissions, or sensitive data.
- Read `docs/FRONTEND.md` and `docs/DESIGN.md` for UI, terminal interface, layout, visual-state, canvas, or interaction changes.
- Read the matching file in `docs/sops/` before architecture changes, UI validation, observability work, evidence-first evals, or knowledge capture.

## Harness Task Intake

Default rule: any request that changes repository files or behavior goes through the harness lifecycle. This includes code, docs, configuration, tests, dependencies, generated templates, build/release scripts, runtime behavior, migrations, cleanup, and fixes found during review. Codex starts or reuses an execution plan, sets acceptance before implementation, validates with evidence, runs `quality-score`, closes the plan, then runs `check`.

No-plan exceptions are narrow: pure question answering, read-only investigation, showing command output, or status reporting with no file changes. If the work moves from investigation to editing files, create or reuse an active plan before editing.

| Request Type | Read First | SOP | Minimum Evidence |
| --- | --- | --- | --- |
| New feature or product behavior | `docs/PRODUCT_SENSE.md`, `docs/product-specs/`, `docs/PLANS.md` | `docs/sops/evidence-first-eval-loop.md` | Product assertions, workflow checks, tests or smoke evidence |
| Bug, regression, or user-reported issue | `AGENTS.md` Issue Workflows, affected domain docs, `docs/PLANS.md` | Domain SOP from Issue Workflows | Reproduction, regression assertion, fix validation, defect log if confirmed |
| Refactor, cleanup, or code organization | `ARCHITECTURE.md`, `docs/PLANS.md`, `docs/exec-plans/workstreams.md` | `docs/sops/layered-domain-architecture-setup.md` when boundaries change | Before/after behavior checks, boundary or dependency notes, compatibility evidence |
| Frontend, UI, design, layout, terminal interface, visual state, or interaction | `docs/FRONTEND.md`, `docs/DESIGN.md`, `docs/QUALITY_SCORE.md` | `docs/sops/chrome-devtools-ui-validation-loop.md` and evidence-first eval loop | Browser or local-runtime evidence for workflows, states, and relevant viewports |
| Tests, evals, fixtures, or validation harnesses | `docs/QUALITY_SCORE.md`, `docs/sops/evidence-first-eval-loop.md`, relevant product or architecture docs | `docs/sops/evidence-first-eval-loop.md` | Failing-before or coverage rationale, passing test/eval output, artifact paths when produced |
| Documentation, policy, specs, or generated harness templates | `docs/PLANS.md`, affected docs, `docs/QUALITY_SCORE.md` | `docs/sops/encode-unseen-knowledge.md` when durable facts change | Doc diff review, link/path validation, generated-output or eval evidence when templates change |
| Dependencies, tooling, package manager, or build system | `ARCHITECTURE.md`, `docs/RELIABILITY.md`, `docs/SECURITY.md` | Local observability SOP when runtime behavior can change | Install/build/test output, lockfile or package diff, compatibility and rollback notes |
| Build, release, deployment, or packaging | `ARCHITECTURE.md`, `docs/RELIABILITY.md`, `docs/SECURITY.md` | `docs/sops/local-observability-feedback-loop.md` | Repeatable build/package output, smoke check, release-risk notes |
| Configuration, environment, flags, secrets handling, or policy gates | `docs/SECURITY.md`, `docs/RELIABILITY.md`, `ARCHITECTURE.md` | Local observability SOP; security review rules | Config diff, secret-handling review, permission or failure-mode evidence |
| Data, migrations, storage, cache, queues, or file formats | `ARCHITECTURE.md`, `docs/RELIABILITY.md`, `docs/SECURITY.md` | Evidence-first eval loop | Fixtures or migration checks, rollback/compatibility evidence, data-loss risk notes |
| Performance, reliability, observability, or operational behavior | `docs/RELIABILITY.md`, `ARCHITECTURE.md`, `docs/QUALITY_SCORE.md` | `docs/sops/local-observability-feedback-loop.md` | Baseline measurement, repeatable benchmark or smoke check, logs/traces, before/after evidence |
| Security, privacy, auth, authorization, or sensitive data | `docs/SECURITY.md`, `ARCHITECTURE.md`, `docs/QUALITY_SCORE.md` | Evidence-first eval loop plus security review rules | Threat check, sensitive-data path, permission test, and secret-handling evidence |
| Code review finding or user feedback that requires changes | Affected domain docs, `docs/PLANS.md`, `docs/QUALITY_SCORE.md` | Matching domain SOP | Finding reproduction or rationale, changed-file validation, defect log when it is a bug |

For every repository change:

- Inspect the relevant code path, runtime path, and user/operator workflow before editing.
- Codex creates or reuses an active plan with `plan-start`; keep plan scope lightweight for small changes, but do not skip the lifecycle.
- Codex defines a ready Acceptance Contract with `acceptance-set` before implementation.
- Convert requirements, risks, or reported failures into assertions, tests, smoke checks, or review evidence.
- Log confirmed defects or missing evidence with `defect-log`; unresolved defects must block `plan-close`, and scoring must be rerun after defects are resolved.
- Run task-appropriate validation, then have Codex score with `quality-score` using concrete evidence notes for every dimension.
- Codex closes with `plan-close` only after validation, passing quality, resolved defects, and durable knowledge updates are complete.
- Codex runs the local harness check before handoff.

## Issue Workflows

For any user-reported issue, classify the domain first, read the listed files, then reproduce,
fix, and validate with evidence before judging the result. Issue handling is one branch of Harness Task Intake; if a fix or repository change is needed, the full plan, acceptance, quality, close, and check lifecycle applies.

| Domain | Read First | Required Evidence |
| --- | --- | --- |
| Product contract or acceptance drift | `docs/PRODUCT_SENSE.md`, `docs/product-specs/`, `docs/sops/evidence-first-eval-loop.md` | Product assertions, acceptance checks, or documented limitation |
| Frontend, UI, layout, interaction, responsive, canvas, visual state, or design fidelity | `docs/FRONTEND.md`, `docs/DESIGN.md`, `docs/sops/evidence-first-eval-loop.md` | Browser or local-runtime evidence across relevant workflows and viewports |
| Backend, API, runtime behavior, background jobs, or integrations | `ARCHITECTURE.md`, `docs/RELIABILITY.md`, `docs/sops/local-observability-feedback-loop.md` | Narrow reproduction, tests or API smoke checks, logs, and failure-mode evidence |
| Architecture boundaries, layering, data flow, or dependency direction | `ARCHITECTURE.md`, `docs/PLANS.md`, `docs/sops/layered-domain-architecture-setup.md` | Boundary map, tradeoff notes, migration or compatibility plan, and validation path |
| Data, state, migrations, cache, queues, or file formats | `ARCHITECTURE.md`, `docs/RELIABILITY.md`, `docs/SECURITY.md` | Fixtures or migration checks, rollback/compatibility evidence, and data-loss risk notes |
| Security, privacy, auth, authorization, secrets, or sensitive data | `docs/SECURITY.md`, `ARCHITECTURE.md` | Threat check, sensitive-data path, permission test, and secret-handling evidence |
| Performance, capacity, timeout, resource use, or availability | `docs/RELIABILITY.md`, `ARCHITECTURE.md`, `docs/sops/local-observability-feedback-loop.md` | Baseline measurement, repeatable benchmark or smoke check, and before/after evidence |

## Repository Focus

- Project: {project_name}
- Domain: {product_domain}
- Primary outcome: {project_summary}
- Main users: {primary_users}

## Operating Rules

- Keep durable decisions in repo docs, not only in chat.
- Keep active plans in `docs/exec-plans/active/` and completed plans in `docs/exec-plans/completed/`; both the Markdown plans and JSON sidecars are version-controlled project state.
- Keep resumable feature, refactor, reliability, security, frontend, and cleanup work in `docs/exec-plans/workstreams.md`.
- Update plans during the work, not only at the end.
- Codex defines acceptance criteria with `acceptance-set` before implementation, then scores completed work with `quality-score` before closing an execution plan.
- If `quality-score` fails, treat `## Rework Required` as the next implementation input and do not close the plan.
- Encode durable facts learned during execution into permanent docs before closing the task.
- Before handoff, Codex runs the local harness check. Active plans must have ready Acceptance Contracts; completed plans must have passing Quality Results scored against the current contract.
- Keep generated evidence and transient artifacts in `docs/generated/`; it is ignored by default unless intentionally promoted into tracked docs.
- Keep local skill installs in `.codex/skills/`; they are ignored by default.
- Keep external references in `docs/references/`.
""",

    "ARCHITECTURE.md": """{marker}
# Architecture

## System Summary

{project_summary}

## Domain Boundaries

- Product domain: {product_domain}
- Primary users: {primary_users}
- Deployment targets: {deployment_targets}

## Repository Shape

- Detected languages: {languages}
- Detected package managers: {package_managers}
- Detected frameworks: {frameworks}

## Reliability Architecture

{reliability_targets}

## Security Architecture

{security_constraints}

## Open Questions

- Document major runtime boundaries, shared libraries, and integration seams here as the codebase grows.
""",
}

FRONTEND_DOC_FILES = {
    "docs/DESIGN.md": """---
version: alpha
name: {project_name} Design System
description: Project-owned unified visual specification for frontend and interface work.
frontend: true
source: harness-engine-template
colors:
  primary: "#1A1C1E"
  on-primary: "#FFFFFF"
  primary-container: "#F0F1F2"
  on-primary-container: "#1A1C1E"
  secondary: "#6C7278"
  on-secondary: "#FFFFFF"
  tertiary: "#B8422E"
  on-tertiary: "#FFFFFF"
  neutral: "#F7F5F2"
  surface: "#FFFFFF"
  surface-muted: "#F3F4F6"
  surface-elevated: "#FFFFFF"
  text: "#1A1C1E"
  muted: "#6C7278"
  border: "#D7D9DD"
  focus: "#2563EB"
  success: "#166534"
  warning: "#A16207"
  danger: "#B91C1C"
typography:
  display-xl:
    fontFamily: Inter
    fontSize: 56px
    fontWeight: "700"
    lineHeight: 1.1
    letterSpacing: 0px
  display-md:
    fontFamily: Inter
    fontSize: 44px
    fontWeight: "700"
    lineHeight: 1.12
    letterSpacing: 0px
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: "650"
    lineHeight: 1.2
    letterSpacing: 0px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: "650"
    lineHeight: 1.25
    letterSpacing: 0px
  title-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: "650"
    lineHeight: 28px
    letterSpacing: 0px
  title-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: "650"
    lineHeight: 26px
    letterSpacing: 0px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: "400"
    lineHeight: 30px
    letterSpacing: 0px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: "400"
    lineHeight: 24px
    letterSpacing: 0px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: "400"
    lineHeight: 20px
    letterSpacing: 0px
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: "600"
    lineHeight: 20px
    letterSpacing: 0px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: "600"
    lineHeight: 16px
    letterSpacing: 0px
rounded:
  xs: 2px
  sm: 4px
  md: 8px
  lg: 12px
  xl: 16px
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  xxl: 64px
  gutter: 24px
  page: 48px
components:
  button-primary:
    backgroundColor: "{{colors.tertiary}}"
    textColor: "{{colors.on-tertiary}}"
    typography: "{{typography.label-md}}"
    rounded: "{{rounded.md}}"
    padding: "{{spacing.md}}"
    height: 44px
  button-primary-hover:
    backgroundColor: "{{colors.primary}}"
    textColor: "{{colors.on-primary}}"
  button-secondary:
    backgroundColor: "{{colors.surface}}"
    textColor: "{{colors.primary}}"
    typography: "{{typography.label-md}}"
    rounded: "{{rounded.md}}"
    padding: "{{spacing.md}}"
    height: 44px
  button-secondary-hover:
    backgroundColor: "{{colors.primary-container}}"
    textColor: "{{colors.on-primary-container}}"
  card:
    backgroundColor: "{{colors.surface-elevated}}"
    textColor: "{{colors.text}}"
    rounded: "{{rounded.lg}}"
    padding: "{{spacing.lg}}"
  input:
    backgroundColor: "{{colors.surface}}"
    textColor: "{{colors.text}}"
    typography: "{{typography.body-md}}"
    rounded: "{{rounded.sm}}"
    padding: "{{spacing.md}}"
    height: 40px
  badge:
    backgroundColor: "{{colors.surface-muted}}"
    textColor: "{{colors.muted}}"
    typography: "{{typography.label-sm}}"
    rounded: "{{rounded.full}}"
    padding: "{{spacing.xs}}"
  table-row:
    backgroundColor: "{{colors.surface}}"
    textColor: "{{colors.text}}"
    typography: "{{typography.body-sm}}"
    height: 44px
---

# Design System: {project_name}

## Overview

{project_summary}

Project positioning: {product_domain}

Primary users: {primary_users}

Frontend context: {frontend_stack_notes}

Requested style direction: {design_style_direction}

Existing frontend code signals: {existing_frontend_style_notes}

This document is the repository-owned visual system. It follows the DESIGN.md pattern of YAML tokens plus markdown rationale, using `/Users/murphy/code/github/design.md` only as a local reference for structure. Do not depend on external design-generation skills or packages during init. Refine this file from the human-confirmed style direction and the existing code signals above before large UI work.

## Colors

Use the YAML tokens as the source of truth. Replace the starter palette with project-specific colors before major UI implementation. Derive replacements from the human-confirmed style direction and existing frontend code, not from an external generator. Every UI surface must map colors to semantic roles instead of introducing one-off hex values in components.

- **Primary / On Primary:** Durable brand presence, selected navigation, and high-emphasis surfaces.
- **Secondary:** Metadata, borders, captions, inactive states, and lower-emphasis UI.
- **Tertiary / On Tertiary:** Primary actions and critical interactive emphasis.
- **Neutral / Surface:** Page backgrounds, panels, cards, table rows, and form fields.
- **State colors:** Success, warning, danger, and focus must be used consistently for feedback and validation.
- **Borders:** Use the `border` token for rules, dividers, field strokes, table separators, and card outlines.

## Typography

Use one primary UI font family across the product until the project explicitly documents a second family. All headings, labels, body text, metadata, tables, and controls must map to the typography tokens in frontmatter. Do not create local font sizes or weights in component files unless `docs/DESIGN.md` is updated first.

- **Display XL / Display MD:** Rare product-level moments, onboarding, or empty states. Do not use inside dense panels.
- **Headline LG / Headline MD:** Page, section, and major panel titles.
- **Title LG / Title MD:** Card titles, modal titles, table group headings, and toolbar labels.
- **Body LG / Body MD / Body SM:** Main reading text, dense table copy, helper text, and secondary descriptions.
- **Label MD / Label SM:** Buttons, form labels, badges, tabs, compact metadata, and column headers.
- **Font rule:** Use the tokenized `fontFamily`, `fontSize`, `fontWeight`, `lineHeight`, and `letterSpacing` values in shared style files so type remains uniform across the product.

## Layout

Use the spacing tokens as the implementation scale. Keep workflow surfaces dense enough for repeated use but leave enough separation for scanning, comparison, and error recovery. Document fixed-format surfaces, responsive breakpoints, page gutters, panel padding, table density, and primary task areas here before implementing them. Do not add ad hoc margins that bypass the token scale.

## Elevation & Depth

Prefer hierarchy through spacing, contrast, borders, tonal layers, and restrained shadows. Record the allowed elevation levels for base page, raised surface, modal/popover, and active drag/focus states. If the product is flat, say so and use border/contrast tokens consistently instead of shadows.

## Shapes

Use the rounded token scale consistently. Buttons, inputs, cards, chips, modals, tables, and fixed-format controls should share a coherent corner-radius language. Do not mix pill, sharp, and soft-rounded styles without documenting the role of each shape.

## Components

Define component treatment before scaling UI work:

- **Buttons:** color role, icon placement, loading state, disabled state, and hover/focus behavior.
- **Forms:** field shape, validation state, helper text, density, and keyboard ergonomics.
- **Navigation:** selected state, hierarchy, collapsed behavior, and responsive fallback.
- **Cards and panels:** surface color, border/elevation, padding, and information density.
- **Tables and lists:** row height, selected state, sorting/filtering affordances, empty state, and overflow behavior.
- **Feedback states:** loading, empty, error, success, warning, and permission-denied patterns.

All shared UI components must consume tokens from this document through the project's existing style layer, such as CSS variables, Tailwind theme config, theme modules, component library theme objects, or generated token notes. Component-local styling is allowed only for layout-specific composition, not for redefining global color, type, spacing, or radius decisions.

## Do's and Don'ts

- Do update this file with project-specific visual decisions before large UI changes.
- Do reconcile the requested style direction with the current frontend code before changing shared styles.
- Do keep tokens and prose aligned: tokens provide exact values, prose explains when to use them.
- Do map tokens into the project's shared style file, theme config, or component theme module before broad UI implementation.
- Do cite this file in frontend plans and code-review notes when UI choices matter.
- Do validate meaningful UI work in a real browser before closing it out.
- Don't call external design skills or packages during harness init.
- Don't create one-off component styles that contradict this file without updating it.
- Don't leave generic palette or typography defaults in place for production-facing UI.
- Don't add untracked font families, font sizes, shadows, radii, or semantic colors directly in component files.
""",
    "docs/FRONTEND.md": """{marker}
# Frontend

## Project Positioning

Project: {project_name}

Domain: {product_domain}

Primary users: {primary_users}

Product purpose: {project_summary}

Requested style direction: {design_style_direction}

Existing frontend code signals: {existing_frontend_style_notes}

## Scope

{frontend_scope}

## Stack Notes

{frontend_stack_notes}

## Validation Loop

{frontend_validation_loop}

## Design Style Contract

- Read `docs/DESIGN.md` before implementing frontend, UI, layout, visual-state, canvas, or interaction work.
- Treat `docs/DESIGN.md` as the project-owned unified visual specification. It is written and maintained in this repository.
- Use the human-confirmed style direction and existing frontend code signals as the inputs for refining `docs/DESIGN.md`.
- Treat `docs/DESIGN.md` as the source of truth for UI tokens, colors, typography, spacing, radius, elevation, component treatment, and Do's and Don'ts.
- Files controlled by `docs/DESIGN.md` include token notes under `docs/design-docs/`, Tailwind theme files, global CSS variables, component theme modules, Storybook/theme previews, and any UI implementation that consumes those tokens or style rules.
- Agents must read in this order for UI work: `docs/FRONTEND.md`, `docs/DESIGN.md`, then the component, theme, or stylesheet being changed.
- When implementing UI, map `docs/DESIGN.md` tokens into the project's shared style layer first: CSS variables, Tailwind config, theme module, component-library theme, or equivalent existing style file.
- Do not add new fonts, font sizes, semantic colors, shadows, radii, or spacing scales directly in component files. Add or update tokens in `docs/DESIGN.md`, then update the shared style layer and consume it from components.
- Do not call external design-generation skills or package CLIs as part of harness init. If a project later adopts a generator, record that decision here first.

## Evidence For Meaningful UI Work

- Capture desktop and mobile evidence for significant UI changes.
- Assert primary text, controls, selected state, loading state, empty state, error state, and primary interactions from the DOM or accessibility tree.
- Define and verify layout invariants for the changed surface, including readable content, non-overlapping controls, usable primary work area, stable fixed-format elements, and reachable actions.
- For responsive UI, verify that navigation, side panels, inspectors, toolbars, and secondary panes preserve the primary task area at intended breakpoints.
- For canvas, WebGL, or game UIs, add pixel or scene-state checks so a blank render cannot pass.
- Record browser limitations and fallback checks instead of claiming full UX validation when browser evidence is unavailable.
""",
    "docs/design-docs/index.md": """{marker}
# Design Docs Index

- Add one document per durable design decision.
- Link active design decisions from plans and specs.
""",
    "docs/design-docs/style-options.md": """{marker}
# Design System Control

The project owns `docs/DESIGN.md`. Harness Engine initializes the document from a local template inspired by `/Users/murphy/code/github/design.md` structure, then the project refines it with its own product, brand, human-confirmed style direction, and existing frontend code.

## Controlled Files

- `docs/DESIGN.md`: source of truth for design tokens and design rationale.
- `docs/design-docs/`: durable design decisions, option notes, and validation evidence.
- `src/styles/`, `app/styles/`, or equivalent style directories: CSS variables, Tailwind themes, or framework-specific theme modules.
- Component theme files, Storybook theme previews, and UI implementation files that consume shared tokens or style rules.

## Operating Rules

- Read `docs/FRONTEND.md` before editing controlled files.
- Read `docs/DESIGN.md` before changing UI implementation.
- Keep token values and prose rationale in sync.
- Record major visual-system changes in this folder or in the active plan.
""",
    "docs/design-docs/core-beliefs.md": """{marker}
# Core Beliefs

- Keep the repository as the system of record.
- Prefer explicit policies over implied team memory.
- Prefer repeatable checks over remembered rules.
""",
}

DOC_FILES = {
    "docs/PLANS.md": """{marker}
# Plans

## Plan Lifecycle

- Create or reuse an execution plan for every repository change: code, docs, configuration, tests, dependencies, build/release scripts, generated templates, runtime behavior, migrations, cleanup, and fixes found during review.
- Put active execution plans in `docs/exec-plans/active/`.
- Move completed plans to `docs/exec-plans/completed/`.
- Commit active plans, completed plans, JSON sidecars, and `docs/exec-plans/workstreams.md` as durable project state.
- Track resumable multi-plan workstreams in `docs/exec-plans/workstreams.md`.
- Record cross-cutting follow-up work in `docs/exec-plans/tech-debt-tracker.md`.

## Authoring Rules

- Keep plans concrete, testable, and scoped.
- For small changes, keep the plan lightweight: narrow scope, short steps, and focused validation are fine, but the Acceptance Contract and Quality Result are still required.
- Update plans during the work, not after the fact.
- Link to specs, decisions, and validation artifacts when they exist.
- Include a section for durable knowledge that must be written back into permanent docs.
- Record a continuation decision before closing every plan. Use workstreams only for resumable continue or pause decisions.
- Do not treat plans as the final home for product, architecture, or policy knowledge.

## No-Plan Exceptions

Only skip an execution plan for pure question answering, read-only investigation, showing command output, or status reporting with no file changes. If the work moves from investigation to editing files, create or reuse an active plan before editing.
""",
    "docs/PRODUCT_SENSE.md": """{marker}
# Product Sense

## Product Summary

{project_summary}

## Users

{primary_users}

## Decision Rules

- Optimize for the main user outcome before edge polish.
- Make tradeoffs explicit when speed, quality, and scope conflict.
- Capture durable product decisions in `docs/product-specs/`.
""",
    "docs/QUALITY_SCORE.md": """{marker}
# Quality Score

## Priority Areas

{quality_focus}

## Scoring Dimensions

- Product correctness
- UX and operator clarity
- Architecture and maintainability
- Reliability and observability
- Security and data handling

## Evidence Requirements

- Product correctness scores must cite product contract checks, tests, browser assertions, or documented limitations.
- UX scores for frontend work must cite browser evidence such as screenshots, DOM/accessibility snapshots, or responsive viewport checks.
- Backend and runtime scores must cite narrow reproductions, tests, API smoke checks, logs, or integration evidence.
- Architecture scores must cite boundary, dependency, data-flow, migration, or compatibility evidence.
- Data and state scores must cite fixtures, migration checks, rollback checks, or data-loss risk analysis.
- Security scores must cite threat checks, permission tests, sensitive-data path review, or secret-handling evidence.
- Performance and reliability scores must cite baseline measurements, repeatable checks, failure-mode tests, or before/after evidence.
- Reliability scores must cite repeatable commands, smoke checks, logs, traces, or failure-mode tests.
- Every quality-score dimension requires a concrete evidence note tied to the ready Acceptance Contract; do not leave score notes empty.
- Open defects must be logged with `defect-log`; do not hide known failures inside a high numeric score.
- Treat LLM or human judgment as a summary over evidence, not as the only eval signal.

## Usage

- Score changes by affected domain and layer.
- Read `AGENTS.md` Harness Task Intake, Issue Workflows, and `docs/sops/evidence-first-eval-loop.md` before closing repository-mutating work.
- Document recurring weak spots and improvement themes here.
""",
    "docs/RELIABILITY.md": """{marker}
# Reliability

## Reliability Targets

{reliability_targets}

## Runtime Validation

- Define the smallest useful local validation loop.
- Document required health checks, logs, and dashboards.
- Capture recurring incidents or near misses in repo docs.
""",
    "docs/SECURITY.md": """{marker}
# Security

## Security Constraints

{security_constraints}

## Review Rules

- Review auth, authorization, secrets, and sensitive data changes explicitly.
- Prefer least privilege and traceable configuration.
- Record security-sensitive assumptions in durable docs.
""",
    "docs/exec-plans/tech-debt-tracker.md": """{marker}
# Tech Debt Tracker

Record follow-up work that should survive beyond a single execution plan.
""",
    "docs/exec-plans/workstreams.md": """{marker}
# Workstreams

Use this ledger only for resumable work that spans plans or is intentionally paused.

## Index

| ID | Status | Current Plan | Last Completed Plan | Next Action | Last Updated |
| --- | --- | --- | --- | --- | --- |

## Operating Rules

- Add a workstream when work spans multiple execution plans or may be resumed by another agent.
- Do not add one-off completed plans here unless their continuation decision is `continue` or `pause`.
- Keep `Current Plan` pointed at the active plan when one exists.
- Keep `Last Completed Plan` pointed at the latest completed plan after `plan-close`.
- Keep `Next Action` concrete enough that another agent can resume without chat history.
- If a workstream is paused, record the restart condition in `Next Action`.
""",
    "docs/exec-plans/active/README.md": """{marker}
# Active Execution Plans

Create one markdown file per in-flight repository change. A repository change includes code, docs, configuration, tests, dependencies, build/release scripts, generated templates, runtime behavior, migrations, cleanup, and fixes found during review.

Suggested filename:

`YYYY-MM-DD-short-task-name.md`

Minimum contents:

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

Use a lightweight plan for small changes, but still set a ready Acceptance Contract, record a Quality Result, close the plan, and run the local harness check.
""",
    "docs/exec-plans/active/_template.md": """{marker}
# Execution Plan: <title>

## Goal

Describe the intended outcome.

## Scope

Describe what is included and excluded.

## Constraints

List product, architecture, reliability, security, or delivery constraints.

## Steps

1. Add the first concrete step.
2. Add the next step.

## Validation

- Describe how the work will be verified.

## Acceptance Contract

Status: draft
Fingerprint: pending

Run `acceptance-set` before implementation to define specific product, UX, architecture, reliability, and security acceptance criteria.

| Dimension | Criteria |
| --- | --- |
| Product correctness | pending |
| UX and operator clarity | pending |
| Architecture and maintainability | pending |
| Reliability and observability | pending |
| Security and data handling | pending |

## Quality Result

Status: pending
Minimum score: 8.0
Average score: pending
Last scored: pending
Criteria fingerprint: pending

Run `quality-score` after implementation and validation. Scores must cite evidence for the ready acceptance contract.

## Rework Required

- Acceptance Contract is not ready.

## Continuation Decision

Decision: pending
Workstream: none
Next target: none
Next action: none
Closure reason: none
Resume notes: none

## Durable Knowledge To Capture

- List facts that must be written back into permanent docs before completion.

## Completion Notes

Summarize outcomes, follow-ups, and doc updates.
""",
    "docs/exec-plans/completed/README.md": """{marker}
# Completed Execution Plans

Move finished plans here after:

1. validation is complete
2. the Acceptance Contract is ready and the Quality Result has passed
3. a continuation decision has been recorded
4. permanent docs have been updated
5. any remaining follow-ups are recorded in workstreams, tech debt, or new plans
""",
    "docs/generated/db-schema.md": """{marker}
# Generated DB Schema

Place generated database or storage schema snapshots here when relevant.
""",
    "docs/product-specs/index.md": """{marker}
# Product Specs Index

- Add one durable product spec per important workflow or product area.
- Link the active plan that created or changed each spec when useful.
""",
    "docs/product-specs/new-user-onboarding.md": """{marker}
# New User Onboarding

## Outcome

Describe the desired first successful experience for a new user of {project_name}.

## Open Questions

- What must a new user understand before reaching value?
- Which steps are fragile or confusing today?
""",
    "docs/references/design-system-reference-llms.txt": "Add model-friendly design system notes or links here.\n",
    "docs/references/nixpacks-llms.txt": "Add model-friendly deployment or buildpack notes here.\n",
    "docs/references/uv-llms.txt": "Add model-friendly Python tooling notes here.\n",
    "docs/sops/layered-domain-architecture-setup.md": """{marker}
# SOP: Layered Domain Architecture Setup

1. Identify user-facing domains and bounded contexts.
2. Map code ownership and integration seams.
3. Record allowed dependency direction between layers.
4. Capture the result in `ARCHITECTURE.md` and the relevant design docs.
""",
    "docs/sops/encode-unseen-knowledge.md": """{marker}
# SOP: Encode Unseen Knowledge

1. Notice repeated chat-only facts or tribal knowledge.
2. Decide the right durable home inside `docs/`.
3. Write the fact in concise, retrievable language.
4. Link it from the nearest routing doc if it will be reused often.
""",
    "docs/sops/local-observability-feedback-loop.md": """{marker}
# SOP: Local Observability Feedback Loop

1. Run the narrowest local reproduction of the issue.
2. Capture logs, metrics, traces, or screenshots.
3. Tighten the validation loop until failures are easy to observe.
4. Record the durable validation path in `docs/RELIABILITY.md`.
""",
    "docs/sops/chrome-devtools-ui-validation-loop.md": """{marker}
# SOP: Chrome DevTools UI Validation Loop

1. Open the relevant route in a browser.
2. Check layout, interaction, loading, error, and empty states.
3. Verify responsive behavior for the intended breakpoints.
4. Write reusable findings back to `docs/FRONTEND.md` or `docs/design-docs/`.
""",
    "docs/sops/evidence-first-eval-loop.md": """{marker}
# SOP: Evidence-First Eval Loop

1. Read Harness Task Intake in `AGENTS.md`; every repository-mutating change needs an active plan unless it is a documented no-plan exception.
2. Convert product requirements into explicit product contract checks and write them with `acceptance-set` before implementation.
3. Run deterministic validation before scoring: tests, API smoke checks, CLI checks, browser actions, and state assertions.
4. Read the Issue Workflows in `AGENTS.md` and the domain docs named there before judging or fixing reported bugs.
5. For frontend work, capture browser evidence: screenshots, DOM/accessibility snapshots, responsive checks, and layout invariants.
6. For backend, architecture, data, security, and performance work, capture the domain evidence named in `AGENTS.md`.
7. Log every discovered bug or evidence gap with `defect-log` before running `quality-score`.
8. Resolve defects only after fixes have passing evidence, then rerun validation and `quality-score`.
9. Report per-case results, failed assertions, artifact paths, and recommended next actions to the user.
""",
}

QUESTION_CATALOG = [
    {
        "id": "project_summary",
        "prompt": "What is the main user or business outcome this repository exists to deliver?",
        "reason": "Needed for AGENTS, ARCHITECTURE, and product docs.",
    },
    {
        "id": "primary_users",
        "prompt": "Who are the primary users or operators of this repository?",
        "reason": "Needed to make product and quality tradeoffs concrete.",
    },
    {
        "id": "deployment_targets",
        "prompt": "Where does this system run or get deployed?",
        "reason": "Needed for architecture and reliability guidance.",
    },
    {
        "id": "product_domain",
        "prompt": "Which product domain best describes this repository?",
        "reason": "Needed for quality scoring and policy language.",
    },
    {
        "id": "reliability_targets",
        "prompt": "Which uptime, recovery, or runtime validation expectations matter most?",
        "reason": "Needed for reliability docs and validation loops.",
    },
    {
        "id": "security_constraints",
        "prompt": "Which security, compliance, auth, or sensitive-data constraints matter here?",
        "reason": "Needed for security review guidance.",
    },
    {
        "id": "frontend_stack_notes",
        "prompt": "If there is a frontend, what experience bar, platforms, or UX constraints should the docs enforce?",
        "reason": "Needed for design and frontend policies.",
    },
    {
        "id": "design_style_direction",
        "prompt": "If there is a frontend, what visual style should the project follow? Describe the concrete reference, mood, density, color/typography preferences, and hard don'ts.",
        "reason": "Needed to generate the project-owned DESIGN.md without external design-generation skills.",
    },
    {
        "id": "quality_focus",
        "prompt": "Which product areas or architectural layers deserve the strictest quality scoring?",
        "reason": "Needed for QUALITY_SCORE.md.",
    },
]

QUALITY_DIMENSIONS = [
    ("product_correctness", "Product correctness"),
    ("ux_operator_clarity", "UX and operator clarity"),
    ("architecture_maintainability", "Architecture and maintainability"),
    ("reliability_observability", "Reliability and observability"),
    ("security_data_handling", "Security and data handling"),
]
QUALITY_NOTE_ARGS = {
    "product_correctness": "product-note",
    "ux_operator_clarity": "ux-note",
    "architecture_maintainability": "architecture-note",
    "reliability_observability": "reliability-note",
    "security_data_handling": "security-note",
}
ACCEPTANCE_ARGS = {
    "product_correctness": "product",
    "ux_operator_clarity": "ux",
    "architecture_maintainability": "architecture",
    "reliability_observability": "reliability",
    "security_data_handling": "security",
}
GENERIC_ACCEPTANCE_PHRASES = [
    "confirm the requested behavior is complete",
    "confirm the user or operator experience is understandable",
    "confirm the implementation is clean and easy to change",
    "confirm the validation loop and failure handling are sufficient",
    "confirm secrets and sensitive data are handled safely",
    "requested behavior is complete",
]
EVIDENCE_HINTS = [
    "test",
    "pytest",
    "go test",
    "npm test",
    "smoke",
    "browser",
    "screenshot",
    "dom",
    "accessibility",
    "log",
    "trace",
    "review",
    "inspected",
    "verified",
    "validated",
    "command",
    "path",
    "file",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    "./",
]
SIDECAR_VERSION = 1


class PlanCloseError(RuntimeError):
    def __init__(self, reason, message, details=None):
        super().__init__(message)
        self.reason = reason
        self.details = details or {}


