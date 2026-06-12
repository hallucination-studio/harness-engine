from .common import *

def make_default_answers(analysis):
    repo_name = analysis["project_name"]
    frameworks = ", ".join(analysis["frameworks"]) or "Unknown"
    style_files = analysis.get("frontend_style_files") or []
    style_file_summary = ", ".join(style_files) if style_files else "No shared style, theme, token, or component style files detected yet."
    has_frontend = analysis["has_frontend"]
    frontend_scope = (
        "User-facing or operator-facing frontend work is expected."
        if has_frontend
        else "No clear frontend surface was detected yet. Update this if a UI emerges."
    )
    frontend_validation_loop = (
        "- Run local UI changes in a browser.\n"
        "- Check desktop and mobile layouts when relevant.\n"
        "- Verify key flows, empty states, and failure states.\n"
        "- Record reusable UI findings in `docs/design-docs/`."
        if has_frontend
        else "- Validate interface changes in the relevant local runtime.\n"
        "- Verify key flows, empty states, failure states, and cleanup behavior where applicable.\n"
        "- Record reusable interface findings in `docs/design-docs/`."
    )
    defaults = {
        "project_name": repo_name,
        "project_summary": f"Summarize the main outcome that {repo_name} should deliver.",
        "primary_users": "Describe the primary users, operators, or internal teams.",
        "deployment_targets": "Describe the main runtime or deployment targets.",
        "product_domain": "Describe the product domain in one line.",
        "reliability_targets": "Describe uptime, failure tolerance, recovery expectations, and required validation loops.",
        "security_constraints": "Describe auth, secrets, compliance, sensitive data, and review constraints.",
        "frontend_stack_notes": (
            f"Detected frameworks: {frameworks}. Describe UX expectations, supported environments, and review rules."
            if has_frontend
            else "No frontend detected. Replace this if the repo includes UI work."
        ),
        "design_style_direction": (
            "Describe the concrete visual direction before major UI work: reference point, mood, density, palette, typography, component shape, and hard don'ts."
            if has_frontend
            else "No frontend detected."
        ),
        "existing_frontend_style_notes": style_file_summary,
        "quality_focus": "List the product areas and architectural layers that deserve the strictest quality bar.",
        "frontend_scope": frontend_scope,
        "frontend_validation_loop": frontend_validation_loop,
    }
    return defaults


def fill_template(template, answers, analysis):
    merged = {}
    merged.update(make_default_answers(analysis))
    merged.update(answers)
    merged.update(
        {
            "marker": MANAGED_MARKER,
            "languages": ", ".join(analysis["languages"]) or "Unknown",
            "package_managers": ", ".join(analysis["package_managers"]) or "Unknown",
            "frameworks": ", ".join(analysis["frameworks"]) or "Unknown",
        }
    )
    return template.format(**merged)


def ensure_parent(path):
    path.parent.mkdir(parents=True, exist_ok=True)


def is_managed_text(text):
    return text.startswith(MANAGED_MARKER) or (
        text.startswith("---") and "\nsource: harness-engine-template\n" in text[:500]
    )


def is_obsolete_managed_text(text):
    return any(text.startswith(marker) for marker in OBSOLETE_MANAGED_MARKERS)


def is_harness_owned_text(text):
    return is_managed_text(text) or is_obsolete_managed_text(text)


def should_write(path, refresh_managed, force):
    if not path.exists():
        return True
    if force:
        return True
    try:
        is_managed = is_harness_owned_text(path.read_text())
    except UnicodeDecodeError:
        return False
    if refresh_managed and is_managed:
        return True
    return False


def write_scaffold(repo, analysis, answers, refresh_managed=False, force=False):
    written = []
    created = []
    refreshed = []
    skipped = []
    all_templates = {}
    all_templates.update(ROOT_FILES)
    all_templates.update(DOC_FILES)
    if analysis["has_frontend"]:
        all_templates.update(FRONTEND_DOC_FILES)

    for relative_path, template in all_templates.items():
        target = repo / relative_path
        existed = target.exists()
        if should_write(target, refresh_managed, force):
            ensure_parent(target)
            content = fill_template(template, answers, analysis)
            target.write_text(content)
            written.append(relative_path)
            if existed:
                refreshed.append(relative_path)
            else:
                created.append(relative_path)
        else:
            skipped.append(relative_path)
    return written, skipped, created, refreshed


