import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .helpers import *

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
    runtime_text = "\n".join(
        path.read_text()
        for path in sorted((SKILL_DIR / "scripts").rglob("*.py"))
    )
    combined = "\n".join([readme_text, skill_text, runtime_text])
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
        "skills/harness-engine/SKILL.md",
    ]:
        if required_path not in files:
            raise AssertionError(f"npm pack should include {required_path}")
    forbidden_prefixes = [
        ".codex-plugin/",
        "skills/google-design-style/",
        "third_party/",
    ]
    for file_path in files:
        if any(file_path.startswith(prefix) for prefix in forbidden_prefixes):
            raise AssertionError(f"npm pack should not include external design source or adapter: {file_path}")
