import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = SKILL_DIR.parents[1]
MANAGER = SKILL_DIR / "scripts" / "manage_harness.py"
CASES_PATH = Path(__file__).resolve().parents[1] / "cases.json"
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_engine.continuation import continuation_decision_issues

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
        for issue in continuation_decision_issues(repo, plan_path, plan_path.read_text())
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


