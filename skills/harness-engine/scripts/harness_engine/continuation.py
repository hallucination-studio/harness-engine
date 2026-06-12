from .common import *
from .plans import find_section, phase_number_from_text, plan_title, replace_section, section_key_values, slugify, mark_state_dirty, sync_state_from_markdown, load_plan_state, save_plan_state
from .templates import DOC_FILES, ensure_parent

def default_workstream_id_from_plan(plan_path, text):
    source = plan_path.stem
    source = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", source)
    source = re.sub(r"phase[-_\s]*\d+", "", source, flags=re.IGNORECASE)
    source = source.strip("-_ ")
    if not source:
        source = plan_title(text)
        source = re.sub(r"phase[-_\s]*\d+", "", source, flags=re.IGNORECASE)
    return slugify(source or "workstream")


def map_legacy_phase_mode(mode):
    legacy = (mode or "").strip().lower()
    if legacy in {"single-phase", "single", "none", "completed"}:
        return "complete"
    if legacy in {"multi-phase", "phased"}:
        return "continue"
    if legacy == "paused":
        return "pause"
    if legacy == "stopped":
        return "stop"
    return legacy


def continuation_decision_for_plan(plan_path, text):
    values = section_key_values(text, "Continuation Decision")
    source = "continuation"
    if values is None:
        values = section_key_values(text, "Phase Continuity")
        source = "phase"
    detected_phase = phase_number_from_text(plan_path.stem) or phase_number_from_text(plan_title(text))
    if values is None:
        return {
            "status": "missing",
            "source": None,
            "detected_phase": detected_phase,
            "decision": None,
            "workstream": None,
            "next_target": None,
            "next_action": None,
            "closure_reason": None,
            "resume_notes": None,
        }
    if source == "phase":
        decision = map_legacy_phase_mode(values.get("mode", ""))
        next_target = values.get("continuation")
    else:
        decision = values.get("decision", "").lower()
        next_target = values.get("next_target") or values.get("continuation")
    workstream = values.get("workstream")
    next_action = values.get("next_action")
    closure_reason = values.get("closure_reason")
    resume_notes = values.get("resume_notes")
    return {
        "status": "present",
        "source": source,
        "detected_phase": detected_phase,
        "decision": decision,
        "workstream": workstream,
        "next_target": next_target,
        "next_action": next_action,
        "closure_reason": closure_reason,
        "resume_notes": resume_notes,
    }


def phase_continuity_for_plan(plan_path, text):
    return continuation_decision_for_plan(plan_path, text)


def is_empty_continuity_value(value):
    if value is None:
        return True
    return value.strip().lower() in {"", "none", "pending", "unknown", "n/a", "-"}


def target_exists_for_continuation(repo, next_target, workstream):
    target = next_target.split("#", 1)[0].strip()
    if target in {"", "none"}:
        return False
    if "workstreams.md" in target:
        ledger = workstreams_path(repo)
        return ledger.exists() and not is_empty_continuity_value(workstream) and workstream in ledger.read_text()
    return (repo / target).exists()


def deferred_target_exists(repo, next_target):
    target = next_target.split("#", 1)[0].strip()
    if target in {"", "none"}:
        return False
    if "tech-debt-tracker.md" in target:
        return (repo / "docs" / "exec-plans" / "tech-debt-tracker.md").exists()
    return (repo / target).exists()


def continuation_decision_issues(repo, plan_path, plan_text):
    continuity = continuation_decision_for_plan(plan_path, plan_text)
    if continuity["status"] == "missing":
        return [
            {
                "severity": "error",
                "code": "missing-continuation-decision",
                "path": str(plan_path.relative_to(repo)),
                "message": "Plan is missing a Continuation Decision section.",
            }
        ]
    issues = []
    relative_plan = str(plan_path.relative_to(repo))
    decision = continuity["decision"]
    if is_empty_continuity_value(decision):
        issues.append(
            {
                "severity": "error",
                "code": "continuation-decision-pending",
                "path": relative_plan,
                "message": "Continuation Decision must be set before plan closure.",
            }
        )
        return issues
    if decision not in {"complete", "continue", "pause", "stop", "defer"}:
        issues.append(
            {
                "severity": "error",
                "code": "invalid-continuation-decision",
                "path": relative_plan,
                "message": "Continuation Decision must be one of complete, continue, pause, stop, or defer.",
            }
        )
        return issues
    workstream = continuity["workstream"]
    next_target = continuity["next_target"]
    next_action = continuity["next_action"]
    closure_reason = continuity["closure_reason"]
    resume_notes = continuity["resume_notes"]
    if decision == "complete":
        return issues
    if decision in {"continue", "pause"} and is_empty_continuity_value(workstream):
        issues.append(
            {
                "severity": "error",
                "code": "missing-workstream",
                "path": relative_plan,
                "message": "Continue or pause decisions must name a resumable workstream.",
            }
        )
    if decision in {"continue", "pause"} and is_empty_continuity_value(next_action):
        issues.append(
            {
                "severity": "error",
                "code": "missing-next-action",
                "path": relative_plan,
                "message": "Continue or pause decisions must record a concrete next action for recovery.",
            }
        )
    if decision == "continue":
        if is_empty_continuity_value(next_target):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing-next-target",
                    "path": relative_plan,
                    "message": "Continue decisions must point to a next plan or workstream target.",
                }
            )
        elif not target_exists_for_continuation(repo, next_target, workstream):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing-continuation-target",
                    "path": relative_plan,
                    "message": "Continue decision points to a missing plan or missing workstream entry.",
                }
            )
    if decision == "pause":
        if is_empty_continuity_value(closure_reason):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing-resume-condition",
                    "path": relative_plan,
                    "message": "Pause decisions must record the condition for resuming.",
                }
            )
        if is_empty_continuity_value(resume_notes):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing-resume-notes",
                    "path": relative_plan,
                    "message": "Pause decisions must include resume notes.",
                }
            )
    if decision == "stop" and is_empty_continuity_value(closure_reason):
        issues.append(
            {
                "severity": "error",
                "code": "missing-closure-reason",
                "path": relative_plan,
                "message": "Stop decisions must explain why the work is ending.",
            }
        )
    if decision == "defer":
        if is_empty_continuity_value(next_target):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing-deferred-target",
                    "path": relative_plan,
                    "message": "Defer decisions must record a tech-debt or follow-up target.",
                }
            )
        elif not deferred_target_exists(repo, next_target):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing-deferred-target",
                    "path": relative_plan,
                    "message": "Defer decision points to a missing tech-debt or follow-up target.",
                }
            )
    if decision in {"continue", "pause"} and not is_empty_continuity_value(workstream):
        ledger = workstreams_path(repo)
        if not ledger.exists() or workstream not in ledger.read_text():
            issues.append(
                {
                    "severity": "error",
                    "code": "missing-workstream-ledger-entry",
                    "path": relative_plan,
                    "message": "Continue or pause decision names a workstream that is not recorded in workstreams.md.",
                }
            )
    return issues


def phase_continuity_issues(repo, plan_path, plan_text):
    return continuation_decision_issues(repo, plan_path, plan_text)


def render_continuation_decision(decision, workstream, next_target, next_action, closure_reason, resume_notes):
    return "\n".join(
        [
            f"Decision: {decision}",
            f"Workstream: {workstream}",
            f"Next target: {next_target}",
            f"Next action: {next_action}",
            f"Closure reason: {closure_reason}",
            f"Resume notes: {resume_notes}",
        ]
    )


def plan_goal_for_workstream(plan_path, explicit_goal=None):
    if explicit_goal and not is_empty_continuity_value(explicit_goal):
        return explicit_goal
    text = plan_path.read_text()
    lines = text.splitlines()
    section_index = find_section(lines, "## Goal")
    if section_index is not None:
        goal_lines = []
        for line in lines[section_index + 1 :]:
            if line.startswith("## "):
                break
            stripped = line.strip()
            if stripped:
                goal_lines.append(stripped)
        if goal_lines:
            return " ".join(goal_lines)
    title = plan_title(text)
    return title or plan_path.stem


def continuation_command_issues(repo, relative_plan, decision, workstream, next_target, next_action, closure_reason, resume_notes):
    issues = []
    decision = (decision or "").lower()
    if decision not in {"complete", "continue", "pause", "stop", "defer"}:
        issues.append(
            {
                "severity": "error",
                "code": "invalid-continuation-decision",
                "path": relative_plan,
                "message": "Continuation Decision must be one of complete, continue, pause, stop, or defer.",
            }
        )
        return issues
    if decision in {"continue", "pause"} and is_empty_continuity_value(workstream):
        issues.append(
            {
                "severity": "error",
                "code": "missing-workstream",
                "path": relative_plan,
                "message": "Continue or pause decisions must name a resumable workstream.",
            }
        )
    if decision in {"continue", "pause"} and is_empty_continuity_value(next_action):
        issues.append(
            {
                "severity": "error",
                "code": "missing-next-action",
                "path": relative_plan,
                "message": "Continue or pause decisions must record a concrete next action for recovery.",
            }
        )
    if decision == "continue" and is_empty_continuity_value(next_target):
        issues.append(
            {
                "severity": "error",
                "code": "missing-next-target",
                "path": relative_plan,
                "message": "Continue decisions must point to a next plan or workstream target.",
            }
        )
    if decision == "pause":
        if is_empty_continuity_value(closure_reason):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing-resume-condition",
                    "path": relative_plan,
                    "message": "Pause decisions must record the condition for resuming.",
                }
            )
        if is_empty_continuity_value(resume_notes):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing-resume-notes",
                    "path": relative_plan,
                    "message": "Pause decisions must include resume notes.",
                }
            )
    if decision == "stop" and is_empty_continuity_value(closure_reason):
        issues.append(
            {
                "severity": "error",
                "code": "missing-closure-reason",
                "path": relative_plan,
                "message": "Stop decisions must explain why the work is ending.",
            }
        )
    if decision == "defer":
        if is_empty_continuity_value(next_target):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing-deferred-target",
                    "path": relative_plan,
                    "message": "Defer decisions must record a tech-debt or follow-up target.",
                }
            )
        elif not deferred_target_exists(repo, next_target):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing-deferred-target",
                    "path": relative_plan,
                    "message": "Defer decision points to a missing tech-debt or follow-up target.",
                }
            )
    return issues


def update_continuation_decision(plan_path, decision, workstream, next_target, next_action, closure_reason, resume_notes):
    text = plan_path.read_text()
    decision = decision.lower()
    resolved_workstream = workstream or (
        default_workstream_id_from_plan(plan_path, text) if decision in {"continue", "pause"} else "none"
    )
    body = render_continuation_decision(
        decision,
        resolved_workstream,
        next_target,
        next_action,
        closure_reason,
        resume_notes,
    )
    if find_section(text.splitlines(), "## Continuation Decision") is None and find_section(text.splitlines(), "## Phase Continuity") is not None:
        updated = replace_section(text, "Phase Continuity", body)
        updated = updated.replace("## Phase Continuity", "## Continuation Decision", 1)
    else:
        updated = replace_section(text, "Continuation Decision", body)
    plan_path.write_text(updated)
    return {
        "status": "updated",
        "decision": decision,
        "workstream": resolved_workstream,
        "next_target": next_target,
        "next_action": next_action,
    }


def update_phase_continuity(plan_path, mode, workstream, current_phase, next_phase, continuation, next_action, closure_reason, resume_notes):
    return update_continuation_decision(
        plan_path,
        map_legacy_phase_mode(mode),
        workstream,
        continuation,
        next_action,
        closure_reason,
        resume_notes,
    )


def workstreams_path(repo):
    return repo / "docs" / "exec-plans" / "workstreams.md"


def workstream_table_insert_index(lines):
    index_heading = find_section(lines, "## Index")
    if index_heading is None:
        return len(lines)
    index = index_heading + 1
    while index < len(lines) and lines[index].strip() == "":
        index += 1
    while index < len(lines) and not lines[index].startswith("| ID |"):
        if lines[index].startswith("## "):
            return index
        index += 1
    if index >= len(lines):
        return index_heading + 1
    index += 1
    if index < len(lines) and lines[index].startswith("| ---"):
        index += 1
    while index < len(lines) and lines[index].startswith("|"):
        index += 1
    return index


def append_workstream_entry(repo, workstream_id, status, current_plan, last_completed_plan, next_action, goal, resume_notes):
    target = workstreams_path(repo)
    ensure_parent(target)
    if not target.exists():
        target.write_text(DOC_FILES["docs/exec-plans/workstreams.md"].format(marker=MANAGED_MARKER))
    text = target.read_text()
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    row = (
        f"| {workstream_id} | {status} | {current_plan or 'none'} | "
        f"{last_completed_plan or 'none'} | {next_action or 'none'} | {today} |"
    )
    lines = text.splitlines()
    replaced = False
    updated_lines = []
    for line in lines:
        if line.startswith(f"| {workstream_id} |"):
            updated_lines.append(row)
            replaced = True
        else:
            updated_lines.append(line)
    if not replaced:
        insert_index = workstream_table_insert_index(updated_lines)
        updated_lines.insert(insert_index, row)
    detail = (
        f"Status: {status}\n"
        f"Goal: {goal or 'Record the durable goal for this workstream.'}\n"
        f"Current plan: {current_plan or 'none'}\n"
        f"Last completed plan: {last_completed_plan or 'none'}\n"
        f"Next action: {next_action or 'none'}\n"
        f"Resume notes: {resume_notes or 'Read the current or last completed plan before continuing.'}\n"
        f"Last updated: {today}"
    )
    updated_text = "\n".join(updated_lines).rstrip() + "\n"
    updated_text = replace_section(updated_text, workstream_id, detail)
    target.write_text(updated_text)
    return target


def update_workstreams_after_plan_close(repo, active_relative_plan, completed_relative_plan):
    target = workstreams_path(repo)
    if not target.exists():
        return
    lines = target.read_text().splitlines()
    updated = []
    current_plan_was_closed = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and not stripped.startswith("| ---") and not stripped.startswith("| ID |"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) == 6:
                if cells[2] == active_relative_plan:
                    cells[2] = "none"
                    if cells[3] == "none":
                        cells[3] = completed_relative_plan
                if cells[3] == active_relative_plan:
                    cells[3] = completed_relative_plan
                updated.append("| " + " | ".join(cells) + " |")
                continue
        if line == f"Current plan: {active_relative_plan}":
            updated.append("Current plan: none")
            current_plan_was_closed = True
            continue
        if line == f"Last completed plan: {active_relative_plan}":
            updated.append(f"Last completed plan: {completed_relative_plan}")
            current_plan_was_closed = False
            continue
        if current_plan_was_closed and line == "Last completed plan: none":
            updated.append(f"Last completed plan: {completed_relative_plan}")
            current_plan_was_closed = False
            continue
        updated.append(line)
        if line.startswith("## "):
            current_plan_was_closed = False
    target.write_text("\n".join(updated).rstrip() + "\n")


def assert_phase_continuity_closed(repo, plan_path, plan_text):
    issues = continuation_decision_issues(repo, plan_path, plan_text)
    if issues:
        messages = "\n".join(f"- {issue['code']}: {issue['message']}" for issue in issues)
        raise PlanCloseError(
            "continuation-decision-incomplete",
            "Cannot close plan until the continuation decision is recorded:\n"
            + messages
            + "\nRecord a continuation decision before closing.",
            {"issues": issues},
        )


