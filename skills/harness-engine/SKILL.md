---
name: harness-engine
description: Initialize, refresh, and operate an advanced harness-engineering repository lifecycle for Codex-driven projects. Use when Codex needs to create or reconcile harness docs, or when work inside a harness-managed repository will change code, docs, configuration, tests, dependencies, build/release scripts, generated templates, runtime behavior, migrations, cleanup policy, or other durable repository state.
---

# Harness Engine

Run the packaged script to inspect the target repository before editing files. Use the generated analysis to decide what to ask the human, what durable knowledge is missing from the repo, and which execution-plan and SOP files must be created or reconciled.

In a harness-managed repository, default every repository-mutating request into the harness lifecycle. Repository-mutating work includes code, docs, configuration, tests, dependencies, build/release scripts, generated templates, runtime behavior, migrations, cleanup, and fixes from review or user feedback. The only no-plan exceptions are pure question answering, read-only investigation, showing command output, and status reporting with no file changes. If an investigation turns into editing files, enter the lifecycle before editing.

## Workflow

1. Run `python3 scripts/manage_harness.py analyze --repo <target-repo> --output <analysis.json>`.
2. Read `analysis.json`.
3. Ask the human only the unresolved, high-impact questions from `human_confirmations`.
4. During initialization, create frontend design docs only when the analysis detects a frontend surface. Frontend repos get `docs/FRONTEND.md`, `docs/DESIGN.md`, and `docs/design-docs/`; backend-only repos do not. Ask the human for the desired visual style direction and use existing frontend style files as evidence. The generated `docs/DESIGN.md` is a project-owned visual specification shaped like DESIGN.md: YAML tokens plus markdown rationale. Do not call external design-generation skills or packages during init.
5. Run `python3 scripts/manage_harness.py sample-answers --analysis <analysis.json> --output <answers.json>`.
6. Fill the placeholders in `answers.json` from the repository and the human's confirmed answers.
7. Run `python3 scripts/manage_harness.py init --repo <target-repo> --answers <answers.json>`. This is the single workspace entrypoint: it creates a new harness when none exists, and reconciles a managed or partial harness when managed harness files are already present. Reconcile refreshes managed files, backfills newly introduced managed files, and preserves unmanaged user files. Pass `--force` only with explicit user approval.
8. For any repository-mutating task, run `python3 scripts/manage_harness.py plan-start --repo <target-repo> --slug <task-name> --goal "<goal>"` unless an active plan already covers the exact work. Small changes may use a lightweight plan, but they still require acceptance, validation, quality scoring, plan close, and check.
9. Before implementation, run `python3 scripts/manage_harness.py acceptance-set --repo <target-repo> --plan <plan-file> --product "<product criterion>" --ux "<UX criterion>" --architecture "<architecture criterion>" --reliability "<reliability criterion>" --security "<security criterion>"`. Criteria must be concrete to the task; generic templates are rejected.
10. If you learn durable facts during the work, run `python3 scripts/manage_harness.py knowledge-log --repo <target-repo> --plan <plan-file> --fact "<fact>" --destination <durable-doc>` and keep the returned `id`. Use `--fact-file <file>` when the fact contains shell-sensitive characters.
11. Before closing the task, write those facts into their durable docs.
12. Run `python3 scripts/manage_harness.py knowledge-mark-written --repo <target-repo> --plan <plan-file> --id <knowledge-id> --evidence "<verbatim text already in durable doc>"`; prefer `--evidence-file <file>` when evidence contains backticks, globs, quotes, pipes, or other shell-sensitive characters. Evidence must be copied from the destination doc, not summarized. Use `--append` only when the exact fact should be appended mechanically.
13. If validation, evals, browser checks, or code review reveal a bug, immediately run `python3 scripts/manage_harness.py defect-log --repo <target-repo> --plan <plan-file> --severity <P0|P1|P2|P3> --summary "<bug>" --evidence "<failing check>"`. This invalidates any existing quality result and makes the defect the next rework input.
14. Fix logged defects, then run `python3 scripts/manage_harness.py defect-resolve --repo <target-repo> --plan <plan-file> --id <bug-id> --fix-evidence "<passing check or code evidence>"`.
15. Score the finished work with `python3 scripts/manage_harness.py quality-score --repo <target-repo> --plan <plan-file> --product-correctness <0-10> --product-note "<evidence>" --ux-operator-clarity <0-10> --ux-note "<evidence>" --architecture-maintainability <0-10> --architecture-note "<evidence>" --reliability-observability <0-10> --reliability-note "<evidence>" --security-data-handling <0-10> --security-note "<evidence>"`. Every dimension needs an evidence note tied to the ready Acceptance Contract.
16. If `quality-score` fails, treat `## Rework Required` in the plan as the next implementation input, fix the work, then run `quality-score` again.
17. For phased or resumable work, run `python3 scripts/manage_harness.py phase-set --repo <target-repo> --plan <plan-file> --mode <multi-phase|paused|completed|stopped> --workstream <id> --current-phase <n> --continuation <target> --next-action "<next action>"`, then update `workstreams.md` with `workstream-upsert`.
18. Before closing, replace generic plan placeholders with task-specific scope, constraints, steps, validation, and completion notes; leave no open durable-knowledge placeholder except the default unused line.
19. Close the plan with `python3 scripts/manage_harness.py plan-close --repo <target-repo> --plan <plan-file> --summary "<summary>"`.
20. Before handoff, run `python3 .codex/skills/harness-engine/scripts/manage_harness.py check --repo <target-repo>` from an installed target repository.
21. To review stale generated evidence, run `python3 scripts/manage_harness.py evidence-prune --repo <target-repo>` first; it is dry-run by default. Add `--apply` only after checking the candidate list.
22. To clean transient harness runtime files or remove already committed runtime files from the remote, run `python3 scripts/manage_harness.py clean --repo <target-repo>` first; it is dry-run by default. Add `--apply` to clean local runtime state, update `.gitignore`, and stage `git rm --cached` removals, then commit and push. Clean is limited to local skill installs and generated evidence; execution plans, sidecars, and workstreams are durable project state.
23. After changing this skill, run `python3 evals/run_evals.py` and iterate until it passes.

## Reading Order

- Read [references/workflow.md](references/workflow.md) first for the operating model and question policy.
- Read [references/file-map.md](references/file-map.md) when deciding which generated file to edit.
- Read [references/question-catalog.md](references/question-catalog.md) when the analysis surfaces ambiguous product, security, reliability, or frontend facts.
- Read [references/knowledge-capture.md](references/knowledge-capture.md) when you discover facts that should survive chat history.
- Read [references/exec-plans.md](references/exec-plans.md) before planning or updating any repository-mutating work.
- Read [references/sop-index.md](references/sop-index.md) to choose the right SOP for architecture, UI validation, observability, or knowledge capture work.
- Read [references/template-policy.md](references/template-policy.md) before overwriting existing files.
- Read [references/evaluation-loop.md](references/evaluation-loop.md) before changing the skill, templates, scripts, or policy references.
- Read [references/evidence-first-evals.md](references/evidence-first-evals.md) before designing evals for product correctness, frontend validation, or bug-discovery coverage.
- Read `docs/FRONTEND.md` and `docs/DESIGN.md` when they exist for frontend, UI, product design, visual design, canvas, or interface polish work.

## Command Rules

- Prefer `analyze` before `init`.
- Prefer the draft, test, evaluate, iterate loop for changes to this skill.
- Use `init` as the workspace entrypoint for both creation and reconciliation. It refreshes managed harness files when an existing managed harness is detected and preserves unmanaged user files. Use `--force` only when the human accepts overwriting.
- Do not overwrite existing files unless the human asked for it or you pass `--force`.
- Treat the generated files as starting points. After generation, tighten them with repository-specific details instead of leaving placeholders behind.
- Before plan close, replace or remove task placeholders such as "Define in-scope work", "Add the first concrete step", "Describe how the work will be verified", and any ad hoc durable-knowledge TODOs.
- Treat `docs/exec-plans/` as required durable state for repository-mutating work, not optional notes.
- Read `docs/exec-plans/workstreams.md` before resuming interrupted feature, refactor, reliability, security, frontend, or cleanup work.
- Treat `docs/sops/` as mechanical operating procedures, not background reading.
- When you answer a question using facts that are not yet in the repo but should be reusable, write them into a durable doc before finishing.
- Prefer `knowledge-mark-written --id ... --evidence-file ...` so durable docs can use natural wording without shell quoting failures or duplicated exact fact strings.
- The knowledge evidence text must exist verbatim in the destination doc; if it is only a paraphrase, write the durable doc first or use a file containing exact destination text.
- Use `defect-log` for every bug found by tests, evals, browser validation, or code review; unresolved defects must block handoff.
- Use `defect-resolve` only after the implementation is fixed and you can cite passing validation or code evidence.
- Use `acceptance-set` before implementation and `quality-score` before `plan-close`; include `--product-note`, `--ux-note`, `--architecture-note`, `--reliability-note`, and `--security-note`; failed or stale scores must drive rework, not handoff.
- Use `phase-set` and `workstream-upsert` before `plan-close` for Phase 1/2/3 or any other resumable multi-plan work.
- Use `plan-close` as the final guardrail so plan state, quality score, and durable docs stay synchronized. When blocked, it returns JSON with `status`, `reason`, `message`, and `details`; use that output as the next repair input.
- Use `check` as the local handoff guardrail for user repositories. Active plans require ready Acceptance Contracts; completed plans require passing Quality Results scored against the current contract fingerprint.
- Use `evidence-prune` as a cleanup preview for old unreferenced files under `docs/generated/`; it never deletes unless `--apply` is present.
- Use `clean` when `.codex/skills/` or `docs/generated/` files need cleanup or were already committed. It never changes files or the git index unless `--apply` is present, and it must not remove execution plans, sidecars, or workstreams.
- Run `python3 evals/run_evals.py` after skill changes, read the structured report, and treat per-case failures as iteration input.
- Do not add CI to user repositories unless the human explicitly asks for it.

## Frontend Design Docs

Harness-engine has no external design runtime dependency and must not call an external design skill during init. It uses the local `/Users/murphy/code/github/design.md` checkout only as a reference for document shape.

For frontend repositories, `docs/FRONTEND.md` records product positioning, requested style direction, existing frontend code signals, scope, stack notes, validation expectations, controlled files, and read order. `docs/DESIGN.md` records the unified visual specification with YAML tokens and markdown rationale. For backend-only repositories, these files are not generated.

## Output Rules

- Keep `AGENTS.md` short and routing-oriented.
- Keep durable knowledge in repo docs, not in chat-only explanations.
- Keep plans under `docs/exec-plans/active/` and move finished plans to `docs/exec-plans/completed/`; plan Markdown and JSON sidecars are version-controlled project state.
- Keep resumable workstreams in `docs/exec-plans/workstreams.md`; this is version-controlled project state.
- Keep generated evidence under `docs/generated/`; it is local runtime output and is ignored by git unless the human intentionally promotes a specific artifact into tracked docs.
- Keep external, model-friendly references under `docs/references/`.
- Keep SOPs explicit and task-triggered so the next agent can follow the same path mechanically.

## Assets

- Scaffold templates live under [assets/repo-template](assets/repo-template).
- SOP starter docs live under [assets/sops](assets/sops).
