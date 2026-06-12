#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import tempfile
import time
import importlib.util
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_DIR.parents[1]
MANAGER = SKILL_DIR / "scripts" / "manage_harness.py"
CASES_PATH = Path(__file__).with_name("cases.json")
MANAGER_SPEC = importlib.util.spec_from_file_location("manage_harness_eval", MANAGER)
MANAGER_MODULE = importlib.util.module_from_spec(MANAGER_SPEC)
MANAGER_SPEC.loader.exec_module(MANAGER_MODULE)


def load_case_metadata():
    if not CASES_PATH.exists():
        return {}
    return {item["id"]: item for item in json.loads(CASES_PATH.read_text())}


def run_manager(*args, expect_success=True):
    result = subprocess.run(
        [sys.executable, str(MANAGER), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if expect_success and result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    if not expect_success and result.returncode == 0:
        raise AssertionError("Command succeeded unexpectedly")
    if result.stdout.strip():
        return json.loads(result.stdout)
    return {}


def write_answers(path, project_name="demo"):
    answers = {
        "project_name": project_name,
        "project_summary": "A developer tooling project used to install and maintain Codex harness docs.",
        "primary_users": "Codex users and maintainers",
        "deployment_targets": "npm package and local repositories",
        "product_domain": "developer tooling",
        "reliability_targets": "Repeatable local commands and safe init behavior",
        "security_constraints": "Do not write secrets or overwrite user-owned docs without consent",
        "frontend_stack_notes": "Frontend changes require browser validation when a UI is detected",
        "design_style_direction": "A restrained developer-tool interface with high-contrast text, calm neutral surfaces, compact spacing, and no decorative gradients.",
        "quality_focus": "installer behavior, generated docs, plan closure, and knowledge capture",
        "frontend_scope": "No frontend unless one is detected by analysis",
    }
    path.write_text(json.dumps(answers, indent=2) + "\n")


def assert_exists(repo, relative_path):
    path = repo / relative_path
    if not path.exists():
        raise AssertionError(f"Expected {relative_path} to exist")


def assert_contains(repo, relative_path, needle):
    text = (repo / relative_path).read_text()
    if needle not in text:
        raise AssertionError(f"Expected {relative_path} to contain {needle!r}")


def quality_note_args(
    product="Product behavior was validated by the eval case command.",
    ux="User/operator workflow evidence was reviewed in the generated plan.",
    architecture="Architecture and plan state were inspected in repository files.",
    reliability="Repeatable validation command evidence was produced by the eval case.",
    security="Security and data-handling assumptions were reviewed in generated metadata files.",
):
    return [
        "--product-note",
        product,
        "--ux-note",
        ux,
        "--architecture-note",
        architecture,
        "--reliability-note",
        reliability,
        "--security-note",
        security,
    ]


def acceptance_args(
    product="The requested behavior is verified against a concrete product assertion for this eval case.",
    ux="The user or operator workflow remains understandable for this eval case.",
    architecture="The implementation keeps lifecycle state and repository boundaries maintainable for this eval case.",
    reliability="The eval case records repeatable command evidence for the lifecycle behavior.",
    security="The eval case confirms no secrets or sensitive data are introduced into plan metadata.",
):
    return [
        "--product",
        product,
        "--ux",
        ux,
        "--architecture",
        architecture,
        "--reliability",
        reliability,
        "--security",
        security,
    ]


def set_acceptance(repo, relative_plan, **kwargs):
    return run_manager(
        "acceptance-set",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        *acceptance_args(**kwargs),
    )


def set_continuation_complete(repo, relative_plan):
    return run_manager(
        "continuation-set",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--decision",
        "complete",
        "--closure-reason",
        "The eval plan is complete and has no follow-up workstream.",
    )


def continuation_codes(repo, plan_path):
    return {
        issue["code"]
        for issue in MANAGER_MODULE.continuation_decision_issues(repo, plan_path, plan_path.read_text())
    }


def fill_plan_details(plan_path):
    path = Path(plan_path)
    text = path.read_text()
    replacements = {
        "- Define in-scope work.\n- Define out-of-scope work.": "- Implement the requested lifecycle behavior.\n- Keep unrelated repository behavior out of scope.",
        "- Add relevant product, architecture, reliability, security, or delivery constraints.": "- Preserve existing command semantics unless this eval explicitly changes them.\n- Keep all validation evidence in repository-local files.",
        "1. Add the first concrete step.\n2. Add the next concrete step.": "1. Prepare the target plan state.\n2. Run the lifecycle command under test.\n3. Verify the command result and persisted files.",
        "1. Add the first concrete step.\n2. Add the next step.": "1. Prepare the target plan state.\n2. Run the lifecycle command under test.\n3. Verify the command result and persisted files.",
        "- Describe how the work will be verified.": "- Run the relevant eval command and inspect generated Markdown and JSON state.",
    }
    for before, after in replacements.items():
        text = text.replace(before, after)
    path.write_text(text)


def test_empty_repo_init(tmp_root):
    repo = tmp_root / "empty-repo"
    repo.mkdir()
    answers = tmp_root / "answers.json"
    write_answers(answers)

    analysis = run_manager("analyze", "--repo", str(repo))
    if analysis["recommended_action"] != "init":
        raise AssertionError("Empty repo should recommend init")
    if not analysis["missing_exec_plan_state"]:
        raise AssertionError("Analysis should report missing exec-plan state")
    if not analysis["missing_sops"]:
        raise AssertionError("Analysis should report missing SOPs")
    nested_output = tmp_root / "nested" / "generated" / "analysis.json"
    run_manager("analyze", "--repo", str(repo), "--output", str(nested_output))
    if not nested_output.exists():
        raise AssertionError("analyze --output should create missing parent directories")

    run_manager("init", "--repo", str(repo), "--answers", str(answers))
    for relative_path in [
        "AGENTS.md",
        "ARCHITECTURE.md",
        "docs/PLANS.md",
        "docs/QUALITY_SCORE.md",
        "docs/exec-plans/workstreams.md",
        "docs/exec-plans/active/_template.md",
        "docs/exec-plans/completed/README.md",
        "docs/sops/encode-unseen-knowledge.md",
        "docs/sops/evidence-first-eval-loop.md",
    ]:
        assert_exists(repo, relative_path)
    assert_contains(repo, "AGENTS.md", "docs/exec-plans/active/")
    assert_contains(repo, "AGENTS.md", "docs/exec-plans/workstreams.md")
    assert_contains(repo, "AGENTS.md", "docs/sops/")
    assert_contains(repo, "AGENTS.md", "Codex runs the local harness check before handoff")
    assert_contains(repo, "AGENTS.md", "## Harness Task Intake")
    assert_contains(repo, "AGENTS.md", "Default rule: any request that changes repository files or behavior goes through the harness lifecycle")
    assert_contains(repo, "AGENTS.md", "No-plan exceptions are narrow")
    assert_contains(repo, "AGENTS.md", "plan-start")
    assert_contains(repo, "AGENTS.md", "acceptance-set")
    assert_contains(repo, "AGENTS.md", "quality-score")
    assert_contains(repo, "AGENTS.md", "plan-close")
    assert_contains(repo, "AGENTS.md", "## Issue Workflows")
    assert_contains(repo, "AGENTS.md", "Product contract or acceptance drift")
    assert_contains(repo, "AGENTS.md", "Backend, API, runtime behavior, background jobs, or integrations")
    assert_contains(repo, "AGENTS.md", "Architecture boundaries, layering, data flow, or dependency direction")
    assert_contains(repo, "AGENTS.md", "Data, state, migrations, cache, queues, or file formats")
    assert_contains(repo, "AGENTS.md", "Security, privacy, auth, authorization, secrets, or sensitive data")
    assert_contains(repo, "AGENTS.md", "Performance, capacity, timeout, resource use, or availability")
    assert_contains(repo, "AGENTS.md", "Convert requirements, risks, or reported failures into assertions, tests, smoke checks, or review evidence")
    assert_contains(repo, "AGENTS.md", "Log confirmed defects or missing evidence with `defect-log`")
    assert_contains(repo, "docs/PLANS.md", "Create or reuse an execution plan for every repository change")
    assert_contains(repo, "docs/PLANS.md", "For small changes, keep the plan lightweight")
    assert_contains(repo, "docs/PLANS.md", "Only skip an execution plan for pure question answering")
    assert_contains(repo, "docs/exec-plans/active/README.md", "Create one markdown file per in-flight repository change")
    assert_contains(repo, "docs/exec-plans/active/_template.md", "## Continuation Decision")
    assert_contains(repo, "docs/exec-plans/active/_template.md", "Decision: pending")
    assert_contains(repo, "docs/sops/evidence-first-eval-loop.md", "Read Harness Task Intake in `AGENTS.md`")
    assert_contains(repo, "docs/QUALITY_SCORE.md", "Evidence Requirements")
    assert_contains(repo, "docs/QUALITY_SCORE.md", "Treat LLM or human judgment as a summary over evidence")
    assert_contains(repo, "docs/QUALITY_SCORE.md", "Backend and runtime scores must cite")
    assert_contains(repo, "docs/QUALITY_SCORE.md", "Architecture scores must cite")
    assert_contains(repo, "docs/QUALITY_SCORE.md", "Security scores must cite")
    for relative_path in [
        "docs/FRONTEND.md",
        "docs/DESIGN.md",
        "docs/design-docs/style-options.md",
    ]:
        if (repo / relative_path).exists():
            raise AssertionError(f"Empty backend-shaped repo should not receive frontend design docs: {relative_path}")
    assert_contains(repo, "docs/sops/evidence-first-eval-loop.md", "Report per-case results")


def test_frontend_analysis(tmp_root):
    repo = tmp_root / "frontend-repo"
    repo.mkdir()
    (repo / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "react": "^19.0.0",
                    "vite": "^6.0.0",
                }
            },
            indent=2,
        )
        + "\n"
    )
    (repo / "src").mkdir()
    (repo / "src" / "App.tsx").write_text("export default function App() { return null; }\n")

    analysis = run_manager("analyze", "--repo", str(repo))
    question_ids = {item["id"] for item in analysis["human_confirmations"]}
    if not analysis["has_frontend"]:
        raise AssertionError("Frontend repo should be detected")
    if "frontend_stack_notes" not in question_ids:
        raise AssertionError("Frontend repo should ask frontend confirmation questions")
    if "design_style_direction" not in question_ids:
        raise AssertionError("Frontend repo should ask for the desired visual style direction")
    if "React" not in analysis["frameworks"]:
        raise AssertionError("React should be detected")
    if "src/App.tsx" not in analysis["frontend_style_files"]:
        raise AssertionError("Frontend analysis should expose existing frontend code signals")
    if "docs/sops/evidence-first-eval-loop.md" not in analysis["missing_sops"]:
        raise AssertionError("Analysis should include the evidence-first eval SOP")


def test_init_reconciles_existing_harness(tmp_root):
    repo = tmp_root / "reconcile-repo"
    repo.mkdir()
    answers = tmp_root / "reconcile-answers.json"
    write_answers(answers, project_name="reconcile-demo")
    init_result = run_manager("init", "--repo", str(repo), "--answers", str(answers))
    if init_result["mode"] != "init" or "AGENTS.md" not in init_result["created"]:
        raise AssertionError("init should report created managed files")

    existing_analysis = run_manager("analyze", "--repo", str(repo))
    if existing_analysis["recommended_action"] != "init" or existing_analysis["harness_state"] != "existing":
        raise AssertionError("existing harnesses should still route through init reconciliation")

    target = repo / "docs" / "sops" / "evidence-first-eval-loop.md"
    target.unlink()
    (repo / "AGENTS.md").write_text("<!-- harness-engine:managed -->\n# stale managed router\n")
    reconcile_result = run_manager("init", "--repo", str(repo), "--answers", str(answers))
    if reconcile_result["mode"] != "init" or reconcile_result["operation"] != "reconciled":
        raise AssertionError("init should reconcile an existing managed harness")
    if "docs/sops/evidence-first-eval-loop.md" not in reconcile_result["created"]:
        raise AssertionError("init reconcile should create missing managed files introduced by newer templates")
    if "AGENTS.md" not in reconcile_result["refreshed"]:
        raise AssertionError("init reconcile should refresh existing managed files")
    assert_contains(repo, "AGENTS.md", "## Issue Workflows")
    assert_exists(repo, "docs/sops/evidence-first-eval-loop.md")


def test_clean_removes_runtime_state_and_untracks_artifacts(tmp_root):
    repo = tmp_root / "clean-repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, text=True, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "harness-eval@example.com"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Harness Eval"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    tracked_files = [
        ".codex/skills/harness-engine/SKILL.md",
        "docs/generated/canvas-polish-desktop-final.png",
        "docs/generated/harness-analysis.json",
    ]
    durable_plan_files = [
        "docs/exec-plans/active/2026-06-11-old-task.md",
        "docs/exec-plans/active/2026-06-11-old-task.json",
        "docs/exec-plans/completed/2026-06-11-old-task.md",
        "docs/exec-plans/completed/2026-06-11-old-task.json",
        "docs/exec-plans/workstreams.md",
    ]
    all_files = tracked_files + durable_plan_files
    for relative_path in all_files:
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("tracked harness file\n")
    subprocess.run(["git", "add", *all_files], cwd=repo, text=True, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "track runtime artifacts"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )

    dry_run = run_manager("clean", "--repo", str(repo))
    if dry_run["mode"] != "dry-run" or dry_run["tracked_candidate_count"] != len(tracked_files):
        raise AssertionError("clean should dry-run tracked runtime artifact candidates")
    if set(dry_run["tracked_candidates"]) != set(tracked_files):
        raise AssertionError("clean tracked candidates should include only local skill installs and generated evidence")
    if set(dry_run["tracked_candidates"]) & set(durable_plan_files):
        raise AssertionError("clean dry-run should not list execution plans, sidecars, or workstreams as tracked candidates")
    if "docs/generated/canvas-polish-desktop-final.png" not in set(dry_run["local_candidates"]):
        raise AssertionError("clean should preview local generated evidence cleanup")
    if set(dry_run["local_candidates"]) & set(durable_plan_files):
        raise AssertionError("clean dry-run should not list execution plans, sidecars, or workstreams as local cleanup candidates")
    for relative_path in all_files:
        if not (repo / relative_path).exists():
            raise AssertionError("clean dry-run should not delete local files")

    applied = run_manager("clean", "--repo", str(repo), "--apply")
    if applied["mode"] != "apply" or set(applied["removed_from_index"]) != set(tracked_files):
        raise AssertionError("clean --apply should remove candidates from the git index")
    if set(applied["removed_from_index"]) & set(durable_plan_files):
        raise AssertionError("clean --apply should not untrack execution plans, sidecars, or workstreams")
    assert_contains(repo, ".gitignore", ".codex/skills/")
    assert_contains(repo, ".gitignore", "docs/generated/")
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    for relative_path in tracked_files:
        if f"D  {relative_path}" not in status:
            raise AssertionError(f"clean should stage index deletion for {relative_path}")
    for relative_path in durable_plan_files:
        if f"D  {relative_path}" in status:
            raise AssertionError(f"clean should not stage index deletion for durable plan state {relative_path}")
        if not (repo / relative_path).exists():
            raise AssertionError(f"clean should keep durable plan state file {relative_path}")
    for relative_path in tracked_files:
        if relative_path.startswith(".codex/skills/"):
            if not (repo / relative_path).exists():
                raise AssertionError(f"clean should keep local skill install file for {relative_path}")
        elif (repo / relative_path).exists():
            raise AssertionError(f"clean should delete local runtime file for {relative_path}")
    if "A  .gitignore" not in status:
        raise AssertionError("clean should stage the new .gitignore block")


def test_broad_task_intake_routes_repo_changes(tmp_root):
    repo = tmp_root / "task-intake-repo"
    repo.mkdir()
    answers = tmp_root / "task-intake-answers.json"
    write_answers(answers, project_name="task-intake-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))

    agents = (repo / "AGENTS.md").read_text()
    plans = (repo / "docs" / "PLANS.md").read_text()
    active_readme = (repo / "docs" / "exec-plans" / "active" / "README.md").read_text()
    sop = (repo / "docs" / "sops" / "evidence-first-eval-loop.md").read_text()

    for needle in [
        "## Harness Task Intake",
        "Default rule: any request that changes repository files or behavior goes through the harness lifecycle",
        "code, docs, configuration, tests, dependencies, generated templates, build/release scripts, runtime behavior, migrations, cleanup",
        "No-plan exceptions are narrow",
        "Codex creates or reuses an active plan with `plan-start`",
        "Codex defines a ready Acceptance Contract with `acceptance-set` before implementation",
        "have Codex score with `quality-score`",
        "Codex closes with `plan-close`",
        "Codex runs the local harness check before handoff",
    ]:
        if needle not in agents:
            raise AssertionError(f"AGENTS.md should include broad task intake rule: {needle}")

    scenario_needles = [
        "New feature or product behavior",
        "Bug, regression, or user-reported issue",
        "Refactor, cleanup, or code organization",
        "Frontend, UI, design, layout, terminal interface, visual state, or interaction",
        "Tests, evals, fixtures, or validation harnesses",
        "Documentation, policy, specs, or generated harness templates",
        "Dependencies, tooling, package manager, or build system",
        "Build, release, deployment, or packaging",
        "Configuration, environment, flags, secrets handling, or policy gates",
        "Data, migrations, storage, cache, queues, or file formats",
        "Performance, reliability, observability, or operational behavior",
        "Security, privacy, auth, authorization, or sensitive data",
        "Code review finding or user feedback that requires changes",
    ]
    for needle in scenario_needles:
        if needle not in agents:
            raise AssertionError(f"AGENTS.md should route scenario: {needle}")

    evidence_needles = [
        "Product assertions, workflow checks, tests or smoke evidence",
        "Reproduction, regression assertion, fix validation, defect log if confirmed",
        "Before/after behavior checks, boundary or dependency notes, compatibility evidence",
        "Browser or local-runtime evidence for workflows, states, and relevant viewports",
        "Failing-before or coverage rationale, passing test/eval output, artifact paths when produced",
        "Doc diff review, link/path validation, generated-output or eval evidence when templates change",
        "Install/build/test output, lockfile or package diff, compatibility and rollback notes",
        "Repeatable build/package output, smoke check, release-risk notes",
        "Config diff, secret-handling review, permission or failure-mode evidence",
        "Fixtures or migration checks, rollback/compatibility evidence, data-loss risk notes",
        "Baseline measurement, repeatable benchmark or smoke check, logs/traces, before/after evidence",
        "Threat check, sensitive-data path, permission test, and secret-handling evidence",
    ]
    for needle in evidence_needles:
        if needle not in agents:
            raise AssertionError(f"AGENTS.md should name minimum evidence: {needle}")

    if "Issue handling is one branch of Harness Task Intake" not in agents:
        raise AssertionError("Issue Workflows should be subordinate to Harness Task Intake")
    if "Create or reuse an execution plan for every repository change" not in plans:
        raise AssertionError("PLANS.md should require plans for every repository change")
    if "For small changes, keep the plan lightweight" not in plans:
        raise AssertionError("PLANS.md should keep small changes lightweight but planned")
    if "Only skip an execution plan for pure question answering" not in plans:
        raise AssertionError("PLANS.md should document no-plan exceptions")
    if "Create one markdown file per in-flight repository change" not in active_readme:
        raise AssertionError("active README should cover any in-flight repository change")
    if "Read Harness Task Intake in `AGENTS.md`" not in sop:
        raise AssertionError("SOP should start from Harness Task Intake")


def test_closed_loop_plan(tmp_root):
    repo = tmp_root / "loop-repo"
    repo.mkdir()
    (repo / "snake.sh").write_text("#!/usr/bin/env bash\nprintf 'snake\\n'\n")
    (repo / ".codex" / "skills" / "demo" / "scripts").mkdir(parents=True)
    (repo / ".codex" / "skills" / "demo" / "scripts" / "tool.py").write_text("print('ignore me')\n")
    answers = tmp_root / "loop-answers.json"
    write_answers(answers, project_name="loop-demo")
    analysis = run_manager("analyze", "--repo", str(repo))
    if "Shell" not in analysis["languages"]:
        raise AssertionError("Shell should be detected from target project files")
    if "Python" in analysis["languages"]:
        raise AssertionError(".codex skill files should not affect target project language detection")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))

    plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "knowledge-loop",
        "--goal",
        "Validate durable knowledge closure",
    )
    plan_path = Path(plan_result["plan"])
    fill_plan_details(plan_path)
    relative_plan = str(plan_path.resolve().relative_to(repo.resolve()))
    fact = "Install mode must distinguish local and global skill destinations"
    run_manager(
        "knowledge-log",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--fact",
        fact,
        "--destination",
        "docs/PRODUCT_SENSE.md",
    )
    open_knowledge_close = run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--summary",
        "done",
        expect_success=False,
    )
    if open_knowledge_close.get("reason") != "acceptance-contract-not-ready":
        raise AssertionError("plan-close should return structured acceptance-contract-not-ready JSON before acceptance")
    run_manager(
        "knowledge-mark-written",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--fact",
        fact,
        "--destination",
        "docs/PRODUCT_SENSE.md",
        expect_success=False,
    )
    run_manager(
        "knowledge-mark-written",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--fact",
        fact,
        "--destination",
        "docs/PRODUCT_SENSE.md",
        "--append",
    )
    assert_contains(repo, "docs/PRODUCT_SENSE.md", fact)
    set_acceptance(repo, relative_plan)
    no_score_close = run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--summary",
        "done",
        expect_success=False,
    )
    if no_score_close.get("reason") != "quality-result-not-passing":
        raise AssertionError("plan-close should return structured quality-result-not-passing JSON before scoring")
    failing_score = run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product-correctness",
        "9",
        "--ux-operator-clarity",
        "8",
        "--architecture-maintainability",
        "7",
        "--reliability-observability",
        "8",
        "--security-data-handling",
        "8",
        "--architecture-note",
        "Plan closure review found architecture evidence below the required threshold.",
        *quality_note_args(
            architecture="Plan closure review found architecture evidence below the required threshold.",
        ),
        expect_success=False,
    )
    if failing_score["status"] != "fail":
        raise AssertionError("Low dimension score should fail the quality gate")
    plan_text_after_fail = plan_path.read_text()
    if "## Rework Required" not in plan_text_after_fail:
        raise AssertionError("Failing quality score should keep a rework section")
    if "Improve Architecture and maintainability" not in plan_text_after_fail:
        raise AssertionError("Failing quality score should name the low dimension")
    set_continuation_complete(repo, relative_plan)
    check_after_fail = run_manager("check", "--repo", str(repo))
    if check_after_fail["status"] != "pass":
        raise AssertionError("Active plan check should require acceptance readiness, not a passing post-implementation score")
    passing_score = run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product-correctness",
        "9",
        "--ux-operator-clarity",
        "8",
        "--architecture-maintainability",
        "8",
        "--reliability-observability",
        "8",
        "--security-data-handling",
        "8",
        *quality_note_args(
            product="Requested behavior was validated by the closed-loop eval command.",
            architecture="Plan closure architecture was reviewed in plan sidecar files.",
        ),
    )
    if passing_score["status"] != "pass":
        raise AssertionError("Scores at or above the minimum should pass")
    close_result = run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--summary",
        "Closed after writing durable knowledge.",
    )
    if close_result["status"] != "closed":
        raise AssertionError("Plan should close after knowledge is marked written")
    if plan_path.exists():
        raise AssertionError("Active plan should be moved after close")
    assert_exists(repo, "docs/exec-plans/completed/" + plan_path.name)
    check_result = run_manager("check", "--repo", str(repo))
    if check_result["status"] != "pass":
        raise AssertionError("Harness check should pass after plan closure")

    formatted_plan = create_formatted_plan(repo)
    formatted_relative_plan = str(formatted_plan.resolve().relative_to(repo.resolve()))
    formatted_fact = "snake.sh is the single runtime entrypoint and owns terminal control directly with stty and tput"
    with (repo / "ARCHITECTURE.md").open("a") as handle:
        handle.write("\n`snake.sh` is the single runtime entrypoint and owns terminal control directly with `stty` and `tput`.\n")
    run_manager(
        "knowledge-mark-written",
        "--repo",
        str(repo),
        "--plan",
        formatted_relative_plan,
        "--fact",
        formatted_fact,
        "--destination",
        "ARCHITECTURE.md",
    )

    id_plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "id-knowledge-loop",
        "--goal",
        "Validate id-based durable knowledge closure",
    )
    id_plan_path = Path(id_plan_result["plan"])
    fill_plan_details(id_plan_path)
    id_relative_plan = str(id_plan_path.resolve().relative_to(repo.resolve()))
    id_fact = "Runtime input is owned by the terminal runner and core game logic remains independent of terminal packages"
    log_result = run_manager(
        "knowledge-log",
        "--repo",
        str(repo),
        "--plan",
        id_relative_plan,
        "--fact",
        id_fact,
        "--destination",
        "ARCHITECTURE.md",
    )
    with (repo / "ARCHITECTURE.md").open("a") as handle:
        handle.write(
            "\nThe `main` package owns keyboard input and rendering, while `game` contains pure state transitions.\n"
        )
    evidence_file = tmp_root / "evidence.txt"
    evidence_file.write_text("main package owns keyboard input and rendering\n")
    run_manager(
        "knowledge-mark-written",
        "--repo",
        str(repo),
        "--plan",
        id_relative_plan,
        "--id",
        log_result["id"],
        "--evidence-file",
        str(evidence_file),
    )
    set_acceptance(repo, id_relative_plan)
    run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        id_relative_plan,
        "--product-correctness",
        "8",
        "--ux-operator-clarity",
        "8",
        "--architecture-maintainability",
        "8",
        "--reliability-observability",
        "8",
        "--security-data-handling",
        "8",
        *quality_note_args(
            architecture="Id-based evidence closure was validated against ARCHITECTURE.md",
        ),
    )
    plan_text = id_plan_path.read_text()
    if id_fact in (repo / "ARCHITECTURE.md").read_text():
        raise AssertionError("Id/evidence closure should not require appending the exact fact to the destination")
    if "| evidence: main package owns keyboard input and rendering" not in plan_text:
        raise AssertionError("Closed knowledge item should record the verification evidence")
    set_continuation_complete(repo, id_relative_plan)
    run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        id_relative_plan,
        "--summary",
        "Closed with id-based evidence.",
    )


def create_formatted_plan(repo):
    plan_path = repo / "docs" / "exec-plans" / "active" / "formatted-plan.md"
    plan_path.write_text(
        """# Execution Plan: Formatted Plan

## Quality Gate

Status: pass
Minimum score: 8.0
Average score: 8.0
Last scored: 2026-06-11T00:00:00Z

| Dimension | Score | Notes |
| --- | ---: | --- |
| Product correctness | 8.0 | ok |
| UX and operator clarity | 8.0 | ok |
| Architecture and maintainability | 8.0 | ok |
| Reliability and observability | 8.0 | ok |
| Security and data handling | 8.0 | ok |

## Durable Knowledge To Capture

- [ ] `snake.sh` is the single runtime entrypoint and owns terminal control directly with `stty` and `tput`. -> `ARCHITECTURE.md`
"""
    )
    return plan_path


def test_preserve_unmanaged_docs(tmp_root):
    repo = tmp_root / "partial-repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("# Existing user router\n\nKeep this custom content.\n")
    answers = tmp_root / "partial-answers.json"
    write_answers(answers)

    result = run_manager("init", "--repo", str(repo), "--answers", str(answers))
    if "AGENTS.md" not in result["skipped"]:
        raise AssertionError("Unmanaged AGENTS.md should be skipped")
    assert_contains(repo, "AGENTS.md", "Keep this custom content.")
    assert_exists(repo, "docs/PLANS.md")


def test_continuation_decision_workstream(tmp_root):
    repo = tmp_root / "continuation-repo"
    repo.mkdir()
    answers = tmp_root / "phase-answers.json"
    write_answers(answers, project_name="phase-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))

    plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "local-workbench-phase-1",
        "--goal",
        "Complete Local Workbench Phase 1",
    )
    plan_path = Path(plan_result["plan"])
    fill_plan_details(plan_path)
    plan_relative_for_assert = str(plan_path.resolve().relative_to(repo.resolve()))
    assert_contains(repo, plan_relative_for_assert, "## Continuation Decision")
    assert_contains(repo, plan_relative_for_assert, "Decision: pending")
    relative_plan = str(plan_path.resolve().relative_to(repo.resolve()))
    set_acceptance(repo, relative_plan)
    run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product-correctness",
        "8",
        "--ux-operator-clarity",
        "8",
        "--architecture-maintainability",
        "8",
        "--reliability-observability",
        "8",
        "--security-data-handling",
        "8",
        *quality_note_args(
            product="Phase 1 plan state was validated by the eval command.",
            architecture="Workstream continuity was inspected in docs/exec-plans/workstreams.md.",
        ),
    )
    close_without_continuity = run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--summary",
        "Phase 1 done",
        expect_success=False,
    )
    if close_without_continuity.get("reason") != "continuation-decision-incomplete":
        raise AssertionError("plan-close should return structured continuation-decision-incomplete JSON")
    check_without_continuity = run_manager("check", "--repo", str(repo), expect_success=False)
    issue_codes = {issue["code"] for issue in check_without_continuity["issues"]}
    if "continuation-decision-pending" not in issue_codes:
        raise AssertionError("check should flag plans that do not declare a continuation decision")

    run_manager(
        "continuation-set",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--decision",
        "continue",
        "--workstream",
        "local-workbench",
        "--next-target",
        "docs/exec-plans/workstreams.md#local-workbench",
        "--next-action",
        "Create Phase 2 plan for command adapters",
        "--resume-notes",
        "Read completed Phase 1 plan and ARCHITECTURE.md before continuing",
    )
    assert_contains(repo, "docs/exec-plans/workstreams.md", "local-workbench")
    assert_contains(repo, "docs/exec-plans/workstreams.md", "Create Phase 2 plan for command adapters")
    assert_contains(repo, "docs/exec-plans/workstreams.md", "Goal: Complete Local Workbench Phase 1")
    if "Goal: none" in (repo / "docs/exec-plans/workstreams.md").read_text():
        raise AssertionError("continuation-set should derive a useful workstream goal instead of writing Goal: none")
    close_result = run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--summary",
        "Phase 1 done; Phase 2 recovery is recorded in workstreams.",
    )
    if close_result["status"] != "closed":
        raise AssertionError("Phased plan should close after continuity and workstream recovery are recorded")
    completed_relative_plan = "docs/exec-plans/completed/" + plan_path.name
    workstreams_text = (repo / "docs/exec-plans/workstreams.md").read_text()
    if completed_relative_plan not in workstreams_text:
        raise AssertionError("plan-close should update workstream ledger to the completed plan path")
    if relative_plan in workstreams_text:
        raise AssertionError("workstream ledger should not keep stale active plan references after plan-close")
    broken = workstreams_text.replace(completed_relative_plan, relative_plan)
    (repo / "docs/exec-plans/workstreams.md").write_text(broken)
    broken_check = run_manager("check", "--repo", str(repo), expect_success=False)
    broken_codes = {issue["code"] for issue in broken_check["issues"]}
    if "missing-workstream-plan-reference" not in broken_codes:
        raise AssertionError("check should fail when workstream ledger points to a missing plan")

    complete_plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "single-plan-complete",
        "--goal",
        "Validate complete continuation decision",
    )
    complete_plan = Path(complete_plan_result["plan"])
    fill_plan_details(complete_plan)
    complete_relative = str(complete_plan.resolve().relative_to(repo.resolve()))
    set_acceptance(repo, complete_relative)
    run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        complete_relative,
        "--product-correctness",
        "8",
        "--ux-operator-clarity",
        "8",
        "--architecture-maintainability",
        "8",
        "--reliability-observability",
        "8",
        "--security-data-handling",
        "8",
        *quality_note_args(product="Complete continuation decision was validated by eval closure."),
    )
    set_continuation_complete(repo, complete_relative)
    complete_close = run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        complete_relative,
        "--summary",
        "Closed as complete with no follow-up.",
    )
    if complete_close["status"] != "closed":
        raise AssertionError("complete continuation decision should allow single-plan closure")

    pause_plan = repo / "docs" / "exec-plans" / "active" / "pause-plan.md"
    pause_plan.write_text(
        "# Execution Plan: Pause Plan\n\n## Continuation Decision\n\nDecision: pause\nWorkstream: pause-demo\nNext target: docs/exec-plans/workstreams.md#pause-demo\nNext action: Resume after dependency lands\nClosure reason: none\nResume notes: none\n"
    )
    pause_issues = continuation_codes(repo, pause_plan)
    if "missing-resume-condition" not in pause_issues or "missing-resume-notes" not in pause_issues:
        raise AssertionError("pause decisions should require resume condition and notes")
    invalid_pause = run_manager(
        "continuation-set",
        "--repo",
        str(repo),
        "--plan",
        str(pause_plan.relative_to(repo)),
        "--decision",
        "pause",
        "--workstream",
        "pause-demo",
        "--next-target",
        "docs/exec-plans/workstreams.md#pause-demo",
        "--next-action",
        "Resume after dependency lands",
        expect_success=False,
    )
    invalid_pause_codes = {issue["code"] for issue in invalid_pause.get("issues", [])}
    if "missing-resume-condition" not in invalid_pause_codes or "missing-resume-notes" not in invalid_pause_codes:
        raise AssertionError("continuation-set should reject pause before writing when resume fields are missing")
    if "pause-demo" in (repo / "docs/exec-plans/workstreams.md").read_text():
        raise AssertionError("invalid pause continuation-set should not write a half-valid workstream")
    run_manager(
        "continuation-set",
        "--repo",
        str(repo),
        "--plan",
        str(pause_plan.relative_to(repo)),
        "--decision",
        "pause",
        "--workstream",
        "pause-demo",
        "--next-target",
        "docs/exec-plans/workstreams.md#pause-demo",
        "--next-action",
        "Resume after dependency lands",
        "--closure-reason",
        "Resume when the dependency is released",
        "--resume-notes",
        "Read dependency release notes before continuing",
    )
    if continuation_codes(repo, pause_plan):
        raise AssertionError("pause decision with resume condition and notes should validate")

    defer_plan = repo / "docs" / "exec-plans" / "active" / "defer-plan.md"
    defer_plan.write_text(
        "# Execution Plan: Defer Plan\n\n## Continuation Decision\n\nDecision: defer\nWorkstream: none\nNext target: none\nNext action: none\nClosure reason: Follow-up is outside this workstream\nResume notes: none\n"
    )
    if "missing-deferred-target" not in continuation_codes(repo, defer_plan):
        raise AssertionError("defer decisions should require a tech-debt or follow-up target")

    legacy_plan = repo / "docs" / "exec-plans" / "active" / "legacy-plan.md"
    legacy_plan.write_text(
        "# Execution Plan: Legacy Plan\n\n## Phase Continuity\n\nMode: single-phase\nWorkstream: none\nCurrent phase: none\nNext phase: none\nContinuation: none\nNext action: none\nClosure reason: Legacy single-phase plan is complete.\nResume notes: none\n"
    )
    if continuation_codes(repo, legacy_plan):
        raise AssertionError("legacy single-phase Phase Continuity should map to complete")
    alias_result = run_manager(
        "phase-set",
        "--repo",
        str(repo),
        "--plan",
        str(legacy_plan.relative_to(repo)),
        "--mode",
        "completed",
        "--closure-reason",
        "Legacy alias remains supported.",
    )
    if alias_result["decision"] != "complete" or "deprecated" not in alias_result.get("warning", ""):
        raise AssertionError("phase-set should remain as a deprecated compatibility alias")


def test_plan_path_canonicalization(tmp_root):
    repo = tmp_root / "canonical-repo"
    repo.mkdir()
    answers = tmp_root / "canonical-answers.json"
    write_answers(answers, project_name="canonical-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))

    plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "canonical-close",
        "--goal",
        "Close a plan when repo and plan paths use different filesystem spellings",
    )
    plan_path = Path(plan_result["plan"])
    fill_plan_details(plan_path)
    relative_plan = str(plan_path.resolve().relative_to(repo.resolve()))
    set_acceptance(repo, relative_plan)
    run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        str(plan_path),
        "--product-correctness",
        "8",
        "--ux-operator-clarity",
        "8",
        "--architecture-maintainability",
        "8",
        "--reliability-observability",
        "8",
        "--security-data-handling",
        "8",
        *quality_note_args(
            architecture="Canonical plan path normalization was validated by file path inspection.",
        ),
    )
    run_manager(
        "continuation-set",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--decision",
        "continue",
        "--workstream",
        "canonical-close",
        "--next-target",
        "docs/exec-plans/workstreams.md#canonical-close",
        "--next-action",
        "Close after canonical path validation",
        "--resume-notes",
        "No special resume notes",
    )

    repo_arg = os.path.realpath(repo)
    plan_arg = str(plan_path)
    if repo_arg == str(repo) and plan_arg == str(plan_path.resolve()):
        repo_arg = str(repo)
        plan_arg = str(plan_path.resolve())

    close_result = run_manager(
        "plan-close",
        "--repo",
        repo_arg,
        "--plan",
        plan_arg,
        "--summary",
        "Closed with canonicalized plan path.",
    )
    if close_result["status"] != "closed":
        raise AssertionError("plan-close should accept absolute plan paths inside the repo")
    completed_relative_plan = "docs/exec-plans/completed/" + plan_path.name
    workstreams_text = (repo / "docs/exec-plans/workstreams.md").read_text()
    if completed_relative_plan not in workstreams_text:
        raise AssertionError("canonicalized plan-close should update last completed plan")
    if relative_plan in workstreams_text:
        raise AssertionError("canonicalized plan-close should remove stale current plan references")
    check_result = run_manager("check", "--repo", str(repo))
    if check_result["status"] != "pass":
        raise AssertionError("canonicalized plan-close should leave harness check passing")


def test_defect_recovery_loop(tmp_root):
    repo = tmp_root / "defect-repo"
    repo.mkdir()
    answers = tmp_root / "defect-answers.json"
    write_answers(answers, project_name="defect-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))

    plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "snake-tail-collision",
        "--goal",
        "Validate defect recovery when Snake tail-cell collision behavior fails",
    )
    plan_path = Path(plan_result["plan"])
    fill_plan_details(plan_path)
    relative_plan = str(plan_path.resolve().relative_to(repo.resolve()))
    defect_summary = (
        "Snake marks game over when the head moves into the current tail cell during a non-eating tick"
    )
    defect_result = run_manager(
        "defect-log",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--severity",
        "P1",
        "--summary",
        defect_summary,
        "--evidence",
        "go test ./internal/game -run TestCanMoveIntoVacatedTailCell failed",
        expect_success=False,
    )
    defect_id = defect_result["id"]
    plan_text = plan_path.read_text()
    if "## Defects To Resolve" not in plan_text or defect_id not in plan_text:
        raise AssertionError("defect-log should record the open defect in the plan")
    if "Status: pending" not in plan_text:
        raise AssertionError("defect-log should invalidate any existing quality result")
    if "Resolve all open defects" not in plan_text:
        raise AssertionError("defect-log should turn the bug into rework input")

    set_acceptance(repo, relative_plan)
    score_with_open_defect = run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product-correctness",
        "10",
        "--ux-operator-clarity",
        "10",
        "--architecture-maintainability",
        "10",
        "--reliability-observability",
        "10",
        "--security-data-handling",
        "10",
        *quality_note_args(
            product="Open Snake defect remains unresolved in go test evidence.",
            reliability="Open defect blocking was validated by the eval command.",
        ),
        expect_success=False,
    )
    if score_with_open_defect["status"] != "fail" or defect_id not in score_with_open_defect["open_defects"]:
        raise AssertionError("quality-score should fail while any defect is open")
    check_with_open_defect = run_manager("check", "--repo", str(repo), expect_success=False)
    issue_codes = {issue["code"] for issue in check_with_open_defect["issues"]}
    if "open-defect" not in issue_codes:
        raise AssertionError("check should surface unresolved defects")
    close_with_open_defect = run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--summary",
        "Should not close with open defects",
        expect_success=False,
    )
    if close_with_open_defect.get("reason") != "open-defects":
        raise AssertionError("plan-close should return structured open-defects JSON")

    run_manager(
        "defect-resolve",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--id",
        defect_id,
        "--fix-evidence",
        "go test ./internal/game -run TestCanMoveIntoVacatedTailCell passed",
    )
    plan_text_after_resolve = plan_path.read_text()
    if f"- [x] [bug:{defect_id}]" not in plan_text_after_resolve:
        raise AssertionError("defect-resolve should close the defect checkbox")
    if "Defects resolved. Re-run validation and `quality-score` before closing." not in plan_text_after_resolve:
        raise AssertionError("defect-resolve should require a fresh quality score")

    passing_score = run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product-correctness",
        "9",
        "--ux-operator-clarity",
        "8",
        "--architecture-maintainability",
        "8",
        "--reliability-observability",
        "9",
        "--security-data-handling",
        "10",
        *quality_note_args(
            product="Snake tail-cell defect was resolved with passing test evidence.",
            reliability="Defect recovery was validated with fresh passing evidence.",
        ),
    )
    if passing_score["status"] != "pass":
        raise AssertionError("quality-score should pass after defects are resolved")
    set_continuation_complete(repo, relative_plan)
    close_result = run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--summary",
        "Closed after defect recovery and fresh quality score.",
    )
    if close_result["status"] != "closed":
        raise AssertionError("plan-close should close after defect recovery")
    completed_plan = repo / "docs" / "exec-plans" / "completed" / plan_path.name
    completed_text = completed_plan.read_text()
    if "- [x] Add durable facts here as they emerge" in completed_text:
        raise AssertionError("plan-close should not mark the default knowledge placeholder as completed")


def test_quality_score_requires_notes(tmp_root):
    repo = tmp_root / "quality-notes-repo"
    repo.mkdir()
    answers = tmp_root / "quality-notes-answers.json"
    write_answers(answers, project_name="quality-notes-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))

    plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "quality-notes",
        "--goal",
        "Validate quality-score evidence notes are required",
    )
    relative_plan = str(Path(plan_result["plan"]).resolve().relative_to(repo.resolve()))
    set_acceptance(repo, relative_plan)
    missing_notes = run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product-correctness",
        "9",
        "--ux-operator-clarity",
        "9",
        "--architecture-maintainability",
        "9",
        "--reliability-observability",
        "9",
        "--security-data-handling",
        "9",
        expect_success=False,
    )
    if missing_notes["reason"] != "missing-quality-notes":
        raise AssertionError("quality-score should fail with a missing-quality-notes reason")
    if len(missing_notes["missing_notes"]) != 5:
        raise AssertionError("quality-score should name every dimension missing an evidence note")
    arguments = {item["argument"] for item in missing_notes["missing_notes"]}
    if "--product-note" not in arguments or "--security-note" not in arguments:
        raise AssertionError("quality-score should name the missing note arguments")

    passing_score = run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product-correctness",
        "9",
        "--ux-operator-clarity",
        "9",
        "--architecture-maintainability",
        "9",
        "--reliability-observability",
        "9",
        "--security-data-handling",
        "9",
        *quality_note_args(
            product="Product assertions were checked by the eval command.",
            ux="User workflow evidence was reviewed in the generated plan.",
            architecture="Architecture evidence was inspected in plan files.",
            reliability="Validation command evidence was checked.",
            security="Security evidence was reviewed in generated metadata files.",
        ),
    )
    if passing_score["status"] != "pass":
        raise AssertionError("quality-score should pass when all evidence notes are present")
    plan_text = Path(plan_result["plan"]).read_text()
    if "No note provided" in plan_text:
        raise AssertionError("quality-score should not write placeholder notes when evidence is required")


def test_knowledge_evidence_verbatim(tmp_root):
    repo = tmp_root / "knowledge-evidence-repo"
    repo.mkdir()
    answers = tmp_root / "knowledge-evidence-answers.json"
    write_answers(answers, project_name="knowledge-evidence-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))

    plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "knowledge-evidence",
        "--goal",
        "Validate durable knowledge evidence must be exact destination text",
    )
    plan_path = Path(plan_result["plan"])
    fill_plan_details(plan_path)
    relative_plan = str(plan_path.resolve().relative_to(repo.resolve()))
    fact = "Snake non-growth movement may enter the current tail cell because the tail leaves during the same tick"
    log_result = run_manager(
        "knowledge-log",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--fact",
        fact,
        "--destination",
        "docs/product-specs/snake.md",
    )
    destination = repo / "docs" / "product-specs" / "snake.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    exact_evidence = "On a non-eating tick, moving into the current tail cell is legal because the tail leaves during the same tick."
    destination.write_text(f"# Snake Rules\n\n- {exact_evidence}\n")

    paraphrase_result = run_manager(
        "knowledge-mark-written",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--id",
        log_result["id"],
        "--evidence",
        "docs/product-specs/snake.md now states the tail-vacating rule.",
        expect_success=False,
    )
    if paraphrase_result:
        raise AssertionError("Paraphrased knowledge evidence should not succeed")
    plan_text_after_failure = plan_path.read_text()
    if f"- [x] [id:{log_result['id']}]" in plan_text_after_failure:
        raise AssertionError("Failed knowledge evidence should not close the knowledge item")

    evidence_file = tmp_root / "snake-evidence.txt"
    evidence_file.write_text(exact_evidence + "\n")
    run_manager(
        "knowledge-mark-written",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--id",
        log_result["id"],
        "--evidence-file",
        str(evidence_file),
    )
    plan_text = plan_path.read_text()
    if f"- [x] [id:{log_result['id']}]" not in plan_text:
        raise AssertionError("Exact destination evidence should close the knowledge item")
    if f"| evidence: {exact_evidence}" not in plan_text:
        raise AssertionError("Closed knowledge item should record the exact verification evidence")


def test_structured_plan_sidecar_and_acceptance(tmp_root):
    repo = tmp_root / "structured-plan-repo"
    repo.mkdir()
    answers = tmp_root / "structured-answers.json"
    write_answers(answers, project_name="structured-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))

    plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "structured-sidecar",
        "--goal",
        "Validate structured sidecar creation and acceptance readiness",
    )
    plan_path = Path(plan_result["plan"])
    sidecar_path = plan_path.with_suffix(".json")
    if not sidecar_path.exists():
        raise AssertionError("plan-start should create a JSON sidecar")
    state = json.loads(sidecar_path.read_text())
    if state["acceptance_contract"]["status"] != "draft":
        raise AssertionError("new plan sidecar should start with draft acceptance contract")
    if "## Acceptance Contract" not in plan_path.read_text() or "## Quality Result" not in plan_path.read_text():
        raise AssertionError("new plan markdown should render acceptance and quality sections")

    relative_plan = str(plan_path.resolve().relative_to(repo.resolve()))
    check_draft = run_manager("check", "--repo", str(repo), expect_success=False)
    if "acceptance-contract-not-ready" not in {issue["code"] for issue in check_draft["issues"]}:
        raise AssertionError("active check should require ready acceptance contract")

    generic = run_manager(
        "acceptance-set",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product",
        "Confirm requested behavior is complete.",
        "--ux",
        "Confirm requested behavior is complete.",
        "--architecture",
        "Confirm requested behavior is complete.",
        "--reliability",
        "Confirm requested behavior is complete.",
        "--security",
        "Confirm requested behavior is complete.",
        expect_success=False,
    )
    if generic["reason"] != "acceptance-criteria-not-specific":
        raise AssertionError("acceptance-set should reject generic template criteria")

    ready = set_acceptance(repo, relative_plan)
    if ready["status"] != "ready" or not ready["criteria_fingerprint"]:
        raise AssertionError("acceptance-set should mark the contract ready with a fingerprint")
    set_continuation_complete(repo, relative_plan)
    check_ready = run_manager("check", "--repo", str(repo))
    if check_ready["status"] != "pass":
        raise AssertionError("active check should pass with ready acceptance contract and no open defects")


def test_quality_score_requires_ready_acceptance(tmp_root):
    repo = tmp_root / "quality-contract-repo"
    repo.mkdir()
    answers = tmp_root / "quality-contract-answers.json"
    write_answers(answers, project_name="quality-contract-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))
    plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "quality-contract",
        "--goal",
        "Validate quality-score blocks before acceptance is ready",
    )
    relative_plan = str(Path(plan_result["plan"]).resolve().relative_to(repo.resolve()))
    blocked = run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product-correctness",
        "8",
        "--ux-operator-clarity",
        "8",
        "--architecture-maintainability",
        "8",
        "--reliability-observability",
        "8",
        "--security-data-handling",
        "8",
        *quality_note_args(),
        expect_success=False,
    )
    if blocked["reason"] != "acceptance-contract-not-ready":
        raise AssertionError("quality-score should require a ready acceptance contract before scoring")


def test_plan_close_rejects_template_placeholders(tmp_root):
    repo = tmp_root / "placeholder-close-repo"
    repo.mkdir()
    answers = tmp_root / "placeholder-close-answers.json"
    write_answers(answers, project_name="placeholder-close-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))
    plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "placeholder-close",
        "--goal",
        "Validate plan-close rejects unresolved starter placeholders",
    )
    plan_path = Path(plan_result["plan"])
    relative_plan = str(plan_path.resolve().relative_to(repo.resolve()))
    set_acceptance(repo, relative_plan)
    run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product-correctness",
        "8",
        "--ux-operator-clarity",
        "8",
        "--architecture-maintainability",
        "8",
        "--reliability-observability",
        "8",
        "--security-data-handling",
        "8",
        *quality_note_args(),
    )
    set_continuation_complete(repo, relative_plan)
    blocked = run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--summary",
        "Should reject placeholders",
        expect_success=False,
    )
    if blocked.get("reason") != "plan-placeholders-unresolved":
        raise AssertionError("plan-close should return structured plan-placeholders-unresolved JSON")
    if not plan_path.exists():
        raise AssertionError("plan-close should leave the active plan in place when placeholders remain")


def test_plan_close_returns_open_knowledge_json(tmp_root):
    repo = tmp_root / "open-knowledge-close-repo"
    repo.mkdir()
    answers = tmp_root / "open-knowledge-close-answers.json"
    write_answers(answers, project_name="open-knowledge-close-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))
    plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "open-knowledge-close",
        "--goal",
        "Validate structured close output for open durable knowledge",
    )
    plan_path = Path(plan_result["plan"])
    fill_plan_details(plan_path)
    relative_plan = str(plan_path.resolve().relative_to(repo.resolve()))
    set_acceptance(repo, relative_plan)
    fact = "Structured plan-close output should identify open durable knowledge items"
    run_manager(
        "knowledge-log",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--fact",
        fact,
        "--destination",
        "docs/QUALITY_SCORE.md",
    )
    run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product-correctness",
        "8",
        "--ux-operator-clarity",
        "8",
        "--architecture-maintainability",
        "8",
        "--reliability-observability",
        "8",
        "--security-data-handling",
        "8",
        *quality_note_args(),
    )
    set_continuation_complete(repo, relative_plan)
    blocked = run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--summary",
        "Should reject open knowledge",
        expect_success=False,
    )
    if blocked.get("reason") != "open-durable-knowledge":
        raise AssertionError("plan-close should return structured open-durable-knowledge JSON")
    if fact not in "\n".join(blocked.get("details", {}).get("open_items", [])):
        raise AssertionError("structured open knowledge JSON should include the blocked item")


def test_plan_close_moves_sidecar_and_rejects_stale_score(tmp_root):
    repo = tmp_root / "stale-score-repo"
    repo.mkdir()
    answers = tmp_root / "stale-score-answers.json"
    write_answers(answers, project_name="stale-score-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))
    plan_result = run_manager(
        "plan-start",
        "--repo",
        str(repo),
        "--slug",
        "stale-score",
        "--goal",
        "Validate plan-close rejects stale fingerprints and moves sidecars",
    )
    plan_path = Path(plan_result["plan"])
    fill_plan_details(plan_path)
    relative_plan = str(plan_path.resolve().relative_to(repo.resolve()))
    set_acceptance(repo, relative_plan)
    run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product-correctness",
        "8",
        "--ux-operator-clarity",
        "8",
        "--architecture-maintainability",
        "8",
        "--reliability-observability",
        "8",
        "--security-data-handling",
        "8",
        *quality_note_args(),
    )
    state_path = plan_path.with_suffix(".json")
    state = json.loads(state_path.read_text())
    state["acceptance_contract"]["criteria"]["product_correctness"] = "A changed product criterion makes the previous score stale."
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    stale_close = run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--summary",
        "Should reject stale score",
        expect_success=False,
    )
    if stale_close.get("reason") != "acceptance-fingerprint-stale":
        raise AssertionError("plan-close should return structured acceptance-fingerprint-stale JSON")

    set_acceptance(
        repo,
        relative_plan,
        product="The stale score plan closes only after rescoring the changed product criterion.",
    )
    run_manager(
        "quality-score",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--product-correctness",
        "8",
        "--ux-operator-clarity",
        "8",
        "--architecture-maintainability",
        "8",
        "--reliability-observability",
        "8",
        "--security-data-handling",
        "8",
        *quality_note_args(product="Changed acceptance criterion was rescored with eval command evidence."),
    )
    set_continuation_complete(repo, relative_plan)
    close_result = run_manager(
        "plan-close",
        "--repo",
        str(repo),
        "--plan",
        relative_plan,
        "--summary",
        "Closed after rescoring changed acceptance contract.",
    )
    if close_result["status"] != "closed":
        raise AssertionError("plan-close should close after fresh passing score")
    if plan_path.exists() or state_path.exists():
        raise AssertionError("plan-close should remove active markdown and sidecar")
    completed_plan = repo / "docs" / "exec-plans" / "completed" / plan_path.name
    completed_sidecar = completed_plan.with_suffix(".json")
    if not completed_plan.exists() or not completed_sidecar.exists():
        raise AssertionError("plan-close should move markdown and sidecar to completed")
    completed_check = run_manager("check", "--repo", str(repo))
    if completed_check["status"] != "pass":
        raise AssertionError("completed structured plan should satisfy check")


def test_evidence_prune_generated_artifacts(tmp_root):
    repo = tmp_root / "prune-repo"
    repo.mkdir()
    answers = tmp_root / "prune-answers.json"
    write_answers(answers, project_name="prune-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))

    generated = repo / "docs" / "generated"
    stale = generated / "old-layout.json"
    referenced = generated / "kept-layout.json"
    recent = generated / "recent-layout.json"
    managed = generated / "managed-starter.md"
    stale.write_text('{"old": true}\n')
    referenced.write_text('{"referenced": true}\n')
    recent.write_text('{"recent": true}\n')
    managed.write_text("<!-- harness-engine:managed -->\n# Starter\n")
    old_time = time.time() - (30 * 24 * 60 * 60)
    for path in [stale, referenced, managed]:
        os.utime(path, (old_time, old_time))
    (repo / "docs" / "PLANS.md").write_text(
        (repo / "docs" / "PLANS.md").read_text()
        + "\nKeep evidence at docs/generated/kept-layout.json for the closed mobile layout plan.\n"
    )

    dry_run = run_manager("evidence-prune", "--repo", str(repo), "--older-than-days", "14")
    candidate_paths = {item["path"] for item in dry_run["candidates"]}
    if dry_run["mode"] != "dry-run" or dry_run["removed"]:
        raise AssertionError("evidence-prune should dry-run by default")
    if "docs/generated/old-layout.json" not in candidate_paths:
        raise AssertionError("stale unreferenced generated evidence should be a prune candidate")
    if "docs/generated/kept-layout.json" in candidate_paths:
        raise AssertionError("referenced generated evidence should not be a prune candidate")
    if "docs/generated/recent-layout.json" in candidate_paths:
        raise AssertionError("recent generated evidence should not be a prune candidate")
    if "docs/generated/managed-starter.md" in candidate_paths:
        raise AssertionError("managed starter files should not be prune candidates")
    if not stale.exists():
        raise AssertionError("dry-run should not delete candidates")

    applied = run_manager(
        "evidence-prune",
        "--repo",
        str(repo),
        "--older-than-days",
        "14",
        "--apply",
    )
    if "docs/generated/old-layout.json" not in applied["removed"]:
        raise AssertionError("apply should remove stale unreferenced generated evidence")
    if stale.exists() or not referenced.exists() or not recent.exists() or not managed.exists():
        raise AssertionError("apply should delete only stale unreferenced evidence")


def test_eval_report_shape(tmp_root):
    case_metadata = load_case_metadata()
    report = build_report(
        [
            {
                "id": "empty-repo-init",
                "status": "pass",
                "description": case_metadata["empty-repo-init"]["description"],
                "score": 1.0,
                "duration_seconds": 0.01,
                "findings": [],
                "recommended_actions": [],
            },
            {
                "id": "frontend-analysis",
                "status": "fail",
                "description": case_metadata["frontend-analysis"]["description"],
                "score": 0.0,
                "duration_seconds": 0.02,
                "findings": ["Frontend repo should ask frontend confirmation questions"],
                "recommended_actions": ["Fix frontend-analysis before release."],
            },
        ]
    )
    if report["schema_version"] != "harness-eval-report.v1":
        raise AssertionError("Eval report should expose a stable schema version")
    if report["status"] != "fail" or report["score"] != 50:
        raise AssertionError("Eval report should expose aggregate status and score")
    if report["metrics"]["case_pass_rate"] != 0.5:
        raise AssertionError("Eval report should expose detailed aggregate metrics")
    if "case_results" not in report or len(report["case_results"]) != 2:
        raise AssertionError("Eval report should expose per-case results")
    failed_case = report["case_results"][1]
    if not failed_case["findings"] or not failed_case["recommended_actions"]:
        raise AssertionError("Failed eval cases should expose findings and recommended actions")
    if "Review `case_results`" not in report["user_message"]:
        raise AssertionError("Eval report should include a user-facing failure message")


def test_backend_init_skips_frontend_design_docs(tmp_root):
    repo = tmp_root / "backend-only-repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text('[project]\nname = "backend-only"\n')
    answers = tmp_root / "backend-only-answers.json"
    write_answers(answers, project_name="backend-only-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))
    for relative_path in [
        "docs/FRONTEND.md",
        "docs/DESIGN.md",
        "docs/design-docs/index.md",
        "docs/design-docs/style-options.md",
        "docs/design-docs/core-beliefs.md",
    ]:
        if (repo / relative_path).exists():
            raise AssertionError(f"Backend-only init should not create {relative_path}")
    assert_exists(repo, "AGENTS.md")
    assert_exists(repo, "ARCHITECTURE.md")
    assert_exists(repo, "docs/QUALITY_SCORE.md")


def test_frontend_design_control_plane(tmp_root):
    repo = tmp_root / "frontend-design-control-repo"
    repo.mkdir()
    (repo / "package.json").write_text(json.dumps({"dependencies": {"react": "^19.0.0", "vite": "^6.0.0"}}))
    (repo / "src" / "styles").mkdir(parents=True)
    (repo / "src" / "styles" / "theme.css").write_text(":root { --color-primary: #1A1C1E; }\n")
    answers = tmp_root / "frontend-design-control-answers.json"
    write_answers(answers, project_name="frontend-design-control-demo")
    run_manager("init", "--repo", str(repo), "--answers", str(answers))
    frontend_text = (repo / "docs" / "FRONTEND.md").read_text()
    design_text = (repo / "docs" / "DESIGN.md").read_text()
    options_text = (repo / "docs" / "design-docs" / "style-options.md").read_text()
    if not design_text.startswith("---\n"):
        raise AssertionError("DESIGN.md should start with YAML frontmatter, not the harness marker")
    for needle in [
        "## Project Positioning",
        "Requested style direction:",
        "Existing frontend code signals:",
        "src/styles/theme.css",
        "Read `docs/DESIGN.md` before implementing frontend",
        "project-owned unified visual specification",
        "Files controlled by `docs/DESIGN.md` include token notes",
        "Tailwind theme files",
        "global CSS variables",
        "component theme modules",
        "Storybook/theme previews",
        "Agents must read in this order for UI work",
        "map `docs/DESIGN.md` tokens into the project's shared style layer first",
        "Do not add new fonts, font sizes, semantic colors, shadows, radii, or spacing scales directly in component files",
        "Do not call external design-generation skills or package CLIs as part of harness init",
    ]:
        if needle not in frontend_text:
            raise AssertionError(f"FRONTEND.md should define design control plane: {needle}")
    for needle in [
        "version: alpha",
        "source: harness-engine-template",
        "colors:",
        "on-primary:",
        "surface-muted:",
        "focus:",
        "success:",
        "warning:",
        "danger:",
        "typography:",
        "display-xl:",
        "display-md:",
        "headline-lg:",
        "headline-md:",
        "title-lg:",
        "title-md:",
        "body-lg:",
        "body-md:",
        "body-sm:",
        "label-md:",
        "label-sm:",
        "rounded:",
        "full: 9999px",
        "spacing:",
        "gutter:",
        "page:",
        "components:",
        "button-primary-hover:",
        "button-secondary:",
        "badge:",
        "table-row:",
        "## Overview",
        "Requested style direction:",
        "Existing frontend code signals:",
        "src/styles/theme.css",
        "## Colors",
        "## Typography",
        "## Layout",
        "## Elevation & Depth",
        "## Shapes",
        "## Components",
        "## Do's and Don'ts",
        "Do not depend on external design-generation skills or packages during init",
        "A restrained developer-tool interface",
        "Use one primary UI font family across the product",
        "All shared UI components must consume tokens from this document through the project's existing style layer",
        "Don't add untracked font families, font sizes, shadows, radii, or semantic colors directly in component files",
    ]:
        if needle not in design_text:
            raise AssertionError(f"DESIGN.md should contain project-owned design spec structure: {needle}")
    if "/Users/murphy/code/github/design.md" not in options_text:
        raise AssertionError("style-options.md should document the local design.md reference path")


def test_no_external_design_dependency(tmp_root):
    readme_text = (REPO_ROOT / "README.md").read_text()
    skill_text = (SKILL_DIR / "SKILL.md").read_text()
    manager_text = (SKILL_DIR / "scripts" / "manage_harness.py").read_text()
    combined = "\n".join([readme_text, skill_text, manager_text])
    forbidden = [
        "@google/design.md",
        "prompt in Stitch",
        "brand URL/image import",
        "$google-design-style",
        "google-design-style",
        "third_party/google-design-md",
        "design-source-required",
    ]
    for needle in forbidden:
        if needle in combined:
            raise AssertionError(f"Harness Engine should not depend on external design integration text: {needle}")
    for needle in [
        "has no external design runtime dependency",
        "never calls an external design skill",
        "/Users/murphy/code/github/design.md",
    ]:
        if needle not in readme_text and needle not in skill_text:
            raise AssertionError(f"Docs should state the dependency-free design boundary: {needle}")


def test_pack_excludes_external_design_dependency(tmp_root):
    result = subprocess.run(
        ["npm", "pack", "--dry-run", "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    json_start = result.stdout.rfind("\n[")
    if json_start == -1:
        json_start = result.stdout.find("[")
    if json_start == -1:
        raise AssertionError(f"npm pack did not emit JSON file data: {result.stdout}")
    pack_data = json.loads(result.stdout[json_start:].strip())
    files = {item["path"] for item in pack_data[0]["files"]}
    for required_path in [
        ".codex-plugin/plugin.json",
        "skills/harness-engine/SKILL.md",
    ]:
        if required_path not in files:
            raise AssertionError(f"npm pack should include {required_path}")
    forbidden_prefixes = [
        "skills/google-design-style/",
        "third_party/",
    ]
    for file_path in files:
        if any(file_path.startswith(prefix) for prefix in forbidden_prefixes):
            raise AssertionError(f"npm pack should not include external design source or adapter: {file_path}")


EVALS = [
    ("empty-repo-init", test_empty_repo_init),
    ("frontend-analysis", test_frontend_analysis),
    ("init-reconciles-existing-harness", test_init_reconciles_existing_harness),
    ("clean-removes-runtime-state-and-untracks-artifacts", test_clean_removes_runtime_state_and_untracks_artifacts),
    ("broad-task-intake-routes-repo-changes", test_broad_task_intake_routes_repo_changes),
    ("closed-loop-plan", test_closed_loop_plan),
    ("continuation-decision-workstream", test_continuation_decision_workstream),
    ("plan-path-canonicalization", test_plan_path_canonicalization),
    ("defect-recovery-loop", test_defect_recovery_loop),
    ("quality-score-requires-notes", test_quality_score_requires_notes),
    ("knowledge-evidence-verbatim", test_knowledge_evidence_verbatim),
    ("structured-plan-sidecar-and-acceptance", test_structured_plan_sidecar_and_acceptance),
    ("quality-score-requires-ready-acceptance", test_quality_score_requires_ready_acceptance),
    ("plan-close-rejects-template-placeholders", test_plan_close_rejects_template_placeholders),
    ("plan-close-returns-open-knowledge-json", test_plan_close_returns_open_knowledge_json),
    ("plan-close-moves-sidecar-and-rejects-stale-score", test_plan_close_moves_sidecar_and_rejects_stale_score),
    ("evidence-prune-generated-artifacts", test_evidence_prune_generated_artifacts),
    ("eval-report-shape", test_eval_report_shape),
    ("preserve-unmanaged-docs", test_preserve_unmanaged_docs),
    ("backend-init-skips-frontend-design-docs", test_backend_init_skips_frontend_design_docs),
    ("frontend-design-control-plane", test_frontend_design_control_plane),
    ("no-external-design-dependency", test_no_external_design_dependency),
    ("pack-excludes-external-design-dependency", test_pack_excludes_external_design_dependency),
]


def build_report(results):
    passed = sum(1 for result in results if result["status"] == "pass")
    total = len(results)
    failed_results = [result for result in results if result["status"] == "fail"]
    return {
        "schema_version": "harness-eval-report.v1",
        "status": "pass" if passed == total else "fail",
        "score": round((passed / total) * 100) if total else 0,
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "message": (
                f"All {total} harness eval cases passed."
                if passed == total
                else f"{total - passed} of {total} harness eval cases failed."
            ),
        },
        "metrics": {
            "case_pass_rate": round(passed / total, 4) if total else 0,
            "case_fail_rate": round((total - passed) / total, 4) if total else 0,
            "failed_case_count": total - passed,
        },
        "case_results": results,
        "user_message": (
            "Harness evals passed. No release-blocking eval findings were detected."
            if passed == total
            else "Harness evals failed. Review `case_results` and fix the listed findings before handoff or release."
        ),
        "recommended_actions": [
            action
            for result in failed_results
            for action in result["recommended_actions"]
        ],
    }


def main():
    results = []
    case_metadata = load_case_metadata()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        for eval_id, test_func in EVALS:
            started = time.monotonic()
            metadata = case_metadata.get(eval_id, {})
            try:
                test_func(tmp_root)
                results.append(
                    {
                        "id": eval_id,
                        "status": "pass",
                        "description": metadata.get("description", ""),
                        "score": 1.0,
                        "duration_seconds": round(time.monotonic() - started, 3),
                        "findings": [],
                        "recommended_actions": [],
                    }
                )
            except Exception as error:
                message = str(error)
                results.append(
                    {
                        "id": eval_id,
                        "status": "fail",
                        "description": metadata.get("description", ""),
                        "score": 0.0,
                        "duration_seconds": round(time.monotonic() - started, 3),
                        "findings": [message],
                        "recommended_actions": [
                            f"Reproduce `{eval_id}` locally with python3 skills/harness-engine/evals/run_evals.py.",
                            "Treat the failing assertion as the next implementation input before release.",
                        ],
                    }
                )

    report = build_report(results)
    print(json.dumps(report, indent=2) + "\n")
    if report["status"] != "pass":
        sys.exit(1)


if __name__ == "__main__":
    main()
