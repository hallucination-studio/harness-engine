from .common import *
from .templates import DEFAULT_DEFECT_PLACEHOLDER, DEFAULT_KNOWLEDGE_PLACEHOLDER, PLAN_TEMPLATE, ensure_parent

def slugify(value):
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "task"


def utc_now_iso():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_section(lines, heading):
    target = heading.strip().lower()
    for index, line in enumerate(lines):
        if line.strip().lower() == target:
            return index
    return None


def sidecar_path_for_plan(plan_path):
    return plan_path.with_suffix(".json")


def plan_id_for_path(plan_path):
    digest = hashlib.sha1(str(plan_path.name).encode()).hexdigest()
    return f"plan-{digest[:10]}"


def empty_acceptance_criteria():
    return {key: "" for key, _ in QUALITY_DIMENSIONS}


def criteria_fingerprint(criteria):
    normalized = {
        key: re.sub(r"\s+", " ", (criteria.get(key) or "").strip())
        for key, _ in QUALITY_DIMENSIONS
    }
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def new_plan_state(plan_path, goal):
    now = utc_now_iso()
    return {
        "schema_version": SIDECAR_VERSION,
        "plan_id": plan_id_for_path(plan_path),
        "goal": goal,
        "created_at": now,
        "updated_at": now,
        "acceptance_contract": {
            "status": "draft",
            "criteria": empty_acceptance_criteria(),
            "fingerprint": None,
        },
        "quality_result": {
            "status": "pending",
            "minimum": 8.0,
            "average": None,
            "scored_at": None,
            "criteria_fingerprint": None,
            "dimensions": {},
        },
        "defects": [],
        "knowledge_items": [],
        "implementation_dirty_after_score": False,
        "dirty_reasons": [],
        "markdown_path": str(plan_path),
    }


def load_plan_state(plan_path):
    sidecar = sidecar_path_for_plan(plan_path)
    if not sidecar.exists():
        return None
    return json.loads(sidecar.read_text())


def save_plan_state(plan_path, state):
    state["updated_at"] = utc_now_iso()
    state["markdown_path"] = str(plan_path)
    sidecar = sidecar_path_for_plan(plan_path)
    ensure_parent(sidecar)
    sidecar.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def require_plan_state(plan_path):
    state = load_plan_state(plan_path)
    if state is None:
        raise RuntimeError(
            f"Plan is missing structured metadata sidecar: {sidecar_path_for_plan(plan_path)}. "
            "Run migration or recreate the plan with `plan-start`."
        )
    return state


def mark_state_dirty(plan_path, reason):
    state = load_plan_state(plan_path)
    if state is None:
        return
    if state.get("quality_result", {}).get("status") in {"pass", "fail"}:
        state["implementation_dirty_after_score"] = True
        reasons = state.setdefault("dirty_reasons", [])
        if reason not in reasons:
            reasons.append(reason)
        quality = state.setdefault("quality_result", {})
        quality["status"] = "pending"
    save_plan_state(plan_path, state)


def markdown_escape_cell(value):
    return (value or "").replace("\n", " ").replace("|", "\\|").strip()


def render_acceptance_contract(state):
    contract = state.get("acceptance_contract", {})
    criteria = contract.get("criteria", {})
    fingerprint = contract.get("fingerprint") or "pending"
    lines = [
        f"Status: {contract.get('status', 'draft')}",
        f"Fingerprint: {fingerprint}",
        "",
    ]
    if contract.get("status") != "ready":
        lines.append(
            "Run `acceptance-set` before implementation to define specific product, UX, architecture, reliability, and security acceptance criteria."
        )
        lines.append("")
    lines.extend(["| Dimension | Criteria |", "| --- | --- |"])
    for key, label in QUALITY_DIMENSIONS:
        criterion = criteria.get(key) or "pending"
        lines.append(f"| {label} | {markdown_escape_cell(criterion)} |")
    return "\n".join(lines)


def render_quality_result(state):
    quality = state.get("quality_result", {})
    status = quality.get("status", "pending")
    average = quality.get("average")
    average_text = f"{average:.1f}" if isinstance(average, (int, float)) else "pending"
    lines = [
        f"Status: {status}",
        f"Minimum score: {float(quality.get('minimum', 8.0)):.1f}",
        f"Average score: {average_text}",
        f"Last scored: {quality.get('scored_at') or 'pending'}",
        f"Criteria fingerprint: {quality.get('criteria_fingerprint') or 'pending'}",
        "",
    ]
    dimensions = quality.get("dimensions") or {}
    if dimensions:
        lines.extend(["| Dimension | Score | Evidence |", "| --- | ---: | --- |"])
        for key, label in QUALITY_DIMENSIONS:
            item = dimensions.get(key, {})
            score = item.get("score")
            score_text = f"{score:.1f}" if isinstance(score, (int, float)) else "pending"
            evidence = item.get("evidence") or "pending"
            lines.append(f"| {label} | {score_text} | {markdown_escape_cell(evidence)} |")
    else:
        lines.append("Run `quality-score` after implementation and validation. Scores must cite evidence for the ready acceptance contract.")
    if state.get("implementation_dirty_after_score"):
        lines.extend(["", "Result invalidated by later plan state changes. Re-run `quality-score`."])
    return "\n".join(lines)


def sync_plan_markdown_from_state(plan_path, state):
    text = plan_path.read_text()
    text = replace_section(text, "Acceptance Contract", render_acceptance_contract(state))
    text = replace_section(text, "Quality Result", render_quality_result(state))
    plan_path.write_text(text)


def sync_state_from_markdown(plan_path, state):
    from .knowledge import extract_defect_items, extract_knowledge_items, parse_defect_item, parse_knowledge_item
    text = plan_path.read_text()
    defects = []
    for item in extract_defect_items(text):
        parsed = parse_defect_item(item)
        if parsed:
            defects.append(parsed)
    knowledge_items = []
    for item in extract_knowledge_items(text):
        if item == DEFAULT_KNOWLEDGE_PLACEHOLDER:
            continue
        parsed = parse_knowledge_item(item)
        if parsed:
            knowledge_items.append(parsed)
    if state.get("defects") != defects or state.get("knowledge_items") != knowledge_items:
        state["defects"] = defects
        state["knowledge_items"] = knowledge_items
        save_plan_state(plan_path, state)
    return state


def specific_acceptance_issues(criteria):
    issues = []
    for key, label in QUALITY_DIMENSIONS:
        value = (criteria.get(key) or "").strip()
        words = re.findall(r"[A-Za-z0-9]+", value)
        lower = value.lower()
        if len(words) < 6:
            issues.append({"dimension": label, "argument": "--" + ACCEPTANCE_ARGS[key], "message": "Acceptance criterion is too short or empty."})
            continue
        if any(phrase in lower for phrase in GENERIC_ACCEPTANCE_PHRASES):
            issues.append({"dimension": label, "argument": "--" + ACCEPTANCE_ARGS[key], "message": "Acceptance criterion is a generic template phrase."})
            continue
        if lower in {"pending", "todo", "tbd", "n/a", "none"}:
            issues.append({"dimension": label, "argument": "--" + ACCEPTANCE_ARGS[key], "message": "Acceptance criterion is not specific."})
    return issues


def ensure_acceptance_ready(plan_path):
    state = require_plan_state(plan_path)
    contract = state.get("acceptance_contract", {})
    criteria = contract.get("criteria") or {}
    issues = specific_acceptance_issues(criteria)
    fingerprint = criteria_fingerprint(criteria)
    if contract.get("status") != "ready" or issues or contract.get("fingerprint") != fingerprint:
        raise RuntimeError(
            "Cannot score before the Acceptance Contract is ready and specific. "
            "Run `acceptance-set` with concrete criteria for all dimensions."
        )
    return state


def replace_completion_notes(text, summary):
    lines = text.splitlines()
    section_index = find_section(lines, "## Completion Notes")
    if section_index is None:
        return text.rstrip() + "\n\n## Completion Notes\n\n" + summary + "\n"
    end_index = len(lines)
    for index in range(section_index + 1, len(lines)):
        if lines[index].startswith("## "):
            end_index = index
            break
    new_lines = lines[: section_index + 1] + ["", summary] + lines[end_index:]
    return "\n".join(new_lines).rstrip() + "\n"


def replace_section(text, heading, body):
    lines = text.splitlines()
    section_index = find_section(lines, f"## {heading}")
    if section_index is None:
        return text.rstrip() + f"\n\n## {heading}\n\n{body.rstrip()}\n"
    end_index = len(lines)
    for index in range(section_index + 1, len(lines)):
        if lines[index].startswith("## "):
            end_index = index
            break
    new_lines = lines[: section_index + 1] + ["", body.rstrip()] + lines[end_index:]
    return "\n".join(new_lines).rstrip() + "\n"


def quality_result_for_plan(text):
    lines = text.splitlines()
    section_index = find_section(lines, "## Quality Result")
    if section_index is None:
        return {"status": "missing", "minimum": None, "average": None, "scores": {}, "criteria_fingerprint": None}
    section_lines = []
    for line in lines[section_index + 1 :]:
        if line.startswith("## "):
            break
        section_lines.append(line)
    section_text = "\n".join(section_lines)
    status_match = re.search(r"^Status:\s*(?P<status>\w+)", section_text, flags=re.MULTILINE)
    minimum_match = re.search(r"^Minimum score:\s*(?P<score>[0-9]+(?:\.[0-9]+)?)", section_text, flags=re.MULTILINE)
    average_match = re.search(r"^Average score:\s*(?P<score>[0-9]+(?:\.[0-9]+)?)", section_text, flags=re.MULTILINE)
    fingerprint_match = re.search(r"^Criteria fingerprint:\s*(?P<fingerprint>[A-Fa-f0-9]+|pending)", section_text, flags=re.MULTILINE)
    scores = {}
    for _, label in QUALITY_DIMENSIONS:
        row_match = re.search(
            rf"^\|\s*{re.escape(label)}\s*\|\s*(?P<score>[0-9]+(?:\.[0-9]+)?)\s*\|",
            section_text,
            flags=re.MULTILINE,
        )
        if row_match:
            scores[label] = float(row_match.group("score"))
    return {
        "status": status_match.group("status").lower() if status_match else "missing",
        "minimum": float(minimum_match.group("score")) if minimum_match else None,
        "average": float(average_match.group("score")) if average_match else None,
        "scores": scores,
        "criteria_fingerprint": (
            fingerprint_match.group("fingerprint")
            if fingerprint_match and fingerprint_match.group("fingerprint") != "pending"
            else None
        ),
    }


def quality_gate_for_plan(text):
    return quality_result_for_plan(text)


def section_key_values(text, heading):
    lines = text.splitlines()
    section_index = find_section(lines, f"## {heading}")
    if section_index is None:
        return None
    values = {}
    for line in lines[section_index + 1 :]:
        if line.startswith("## "):
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower().replace(" ", "_")
        values[normalized_key] = value.strip()
    return values


def phase_number_from_text(value):
    match = re.search(r"\bphase[-_\s]*(?P<number>\d+)\b", value, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group("number")


def plan_title(text):
    for line in text.splitlines():
        if line.startswith("# Execution Plan:"):
            return line.split(":", 1)[1].strip()
    return ""


def open_defects_for_plan(text):
    from .knowledge import extract_defect_items, parse_defect_item
    open_items = []
    for item in extract_defect_items(text):
        parsed = parse_defect_item(item)
        if parsed and parsed["status"] == "open":
            open_items.append(parsed)
    return open_items


def render_quality_gate(scores, notes, minimum, open_defects=None):
    open_defects = open_defects or []
    average = sum(scores.values()) / len(scores)
    low_dimensions = [
        label for key, label in QUALITY_DIMENSIONS if scores[key] < minimum
    ]
    passed = average >= minimum and not low_dimensions and not open_defects
    status = "pass" if passed else "fail"
    lines = [
        f"Status: {status}",
        f"Minimum score: {minimum:.1f}",
        f"Average score: {average:.1f}",
        f"Last scored: {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "| Dimension | Score | Notes |",
        "| --- | ---: | --- |",
    ]
    for key, label in QUALITY_DIMENSIONS:
        note = notes.get(key) or "No note provided."
        safe_note = note.replace("\n", " ").replace("|", "\\|").strip()
        lines.append(f"| {label} | {scores[key]:.1f} | {safe_note} |")
    return "\n".join(lines), passed, average, low_dimensions


def render_rework_section(passed, average, minimum, low_dimensions, notes, open_defects=None):
    open_defects = open_defects or []
    if passed:
        return "None. Quality Result passed."
    lines = [
        f"- Rework implementation until every quality dimension is at least {minimum:.1f}; current average is {average:.1f}.",
    ]
    for defect in open_defects:
        evidence = f" Evidence: {defect['evidence']}." if defect.get("evidence") else ""
        lines.append(
            f"- Resolve {defect['id']} ({defect['severity']}): {defect['summary']}.{evidence}"
        )
    for key, label in QUALITY_DIMENSIONS:
        if label in low_dimensions:
            note = notes.get(key) or "No note provided."
            lines.append(f"- Improve {label}: {note}")
    return "\n".join(lines)


def update_quality_gate(plan_path, scores, notes, minimum):
    state = ensure_acceptance_ready(plan_path)
    state = sync_state_from_markdown(plan_path, state)
    open_defects = [defect for defect in state.get("defects", []) if defect.get("status") == "open"]
    _, passed, average, low_dimensions = render_quality_gate(scores, notes, minimum, open_defects)
    fingerprint = state["acceptance_contract"]["fingerprint"]
    state["quality_result"] = {
        "status": "pass" if passed else "fail",
        "minimum": minimum,
        "average": round(average, 1),
        "scored_at": utc_now_iso(),
        "criteria_fingerprint": fingerprint,
        "dimensions": {
            key: {"score": scores[key], "evidence": notes.get(key) or ""}
            for key, _ in QUALITY_DIMENSIONS
        },
    }
    state["implementation_dirty_after_score"] = False
    state["dirty_reasons"] = []
    save_plan_state(plan_path, state)
    text = plan_path.read_text()
    updated = replace_section(text, "Quality Result", render_quality_result(state))
    updated = replace_section(
        updated,
        "Rework Required",
        render_rework_section(passed, average, minimum, low_dimensions, notes, open_defects),
    )
    plan_path.write_text(updated)
    return {
        "status": "pass" if passed else "fail",
        "minimum": minimum,
        "average": round(average, 1),
        "low_dimensions": low_dimensions,
        "open_defects": [defect["id"] for defect in open_defects],
        "criteria_fingerprint": fingerprint,
    }


def missing_quality_notes(notes):
    missing = []
    for key, label in QUALITY_DIMENSIONS:
        if not (notes.get(key) or "").strip():
            missing.append(
                {
                    "dimension": label,
                    "argument": "--" + QUALITY_NOTE_ARGS[key],
                    "message": f"Provide evidence for {label}.",
                }
            )
    return missing


def weak_quality_notes(notes):
    weak = []
    for key, label in QUALITY_DIMENSIONS:
        note = (notes.get(key) or "").strip()
        lower = note.lower()
        if not note:
            continue
        if len(re.findall(r"[A-Za-z0-9./:-]+", note)) < 4 or not any(hint in lower for hint in EVIDENCE_HINTS):
            weak.append(
                {
                    "dimension": label,
                    "argument": "--" + QUALITY_NOTE_ARGS[key],
                    "message": f"Provide concrete verification evidence for {label}, such as a command, browser check, log, code path, or review finding.",
                }
            )
    return weak


def assert_quality_gate_passed(plan_path, plan_text):
    state = require_plan_state(plan_path)
    state = sync_state_from_markdown(plan_path, state)
    contract = state.get("acceptance_contract", {})
    if contract.get("status") != "ready":
        raise PlanCloseError("acceptance-contract-not-ready", "Cannot close plan until the Acceptance Contract is ready.")
    current_fingerprint = criteria_fingerprint(contract.get("criteria") or {})
    if contract.get("fingerprint") != current_fingerprint:
        raise PlanCloseError(
            "acceptance-fingerprint-stale",
            "Cannot close plan because the Acceptance Contract fingerprint is stale. Re-run `acceptance-set`.",
            {"current_fingerprint": current_fingerprint, "recorded_fingerprint": contract.get("fingerprint")},
        )
    open_defects = [defect for defect in state.get("defects", []) if defect.get("status") == "open"]
    if open_defects:
        defects = "\n".join(
            f"- {defect['id']} ({defect['severity']}): {defect['summary']}" for defect in open_defects
        )
        raise PlanCloseError(
            "open-defects",
            "Cannot close plan with unresolved defects. Run `defect-resolve`, re-run validation, and score again.",
            {"open_defects": open_defects, "defects_text": defects},
        )
    quality = state.get("quality_result", {})
    if state.get("implementation_dirty_after_score"):
        raise PlanCloseError(
            "quality-result-stale",
            "Cannot close plan because plan state changed after the last quality score. Re-run `quality-score`.",
            {"dirty_reasons": state.get("dirty_reasons", [])},
        )
    if quality.get("status") != "pass":
        raise PlanCloseError(
            "quality-result-not-passing",
            "Cannot close plan until the quality result passes. "
            "Run `quality-score`, fix any `## Rework Required` items, then score again.",
            {"quality_status": quality.get("status")},
        )
    if quality.get("criteria_fingerprint") != current_fingerprint:
        raise PlanCloseError(
            "quality-fingerprint-stale",
            "Cannot close plan because the quality result was scored against a stale Acceptance Contract fingerprint.",
            {"quality_fingerprint": quality.get("criteria_fingerprint"), "current_fingerprint": current_fingerprint},
        )
    return quality


def plan_placeholder_issues(plan_text):
    issues = []
    for placeholder in PLAN_PLACEHOLDERS:
        if placeholder in plan_text:
            issues.append(placeholder)
    return issues


def assert_plan_placeholders_resolved(plan_text):
    placeholders = plan_placeholder_issues(plan_text)
    if placeholders:
        raise PlanCloseError(
            "plan-placeholders-unresolved",
            "Cannot close plan with unresolved starter placeholders:\n"
            + "\n".join(f"- {placeholder}" for placeholder in placeholders)
            + "\nReplace generic Scope, Constraints, Steps, and Validation text with task-specific content before closing.",
            {"placeholders": placeholders},
        )


def active_plan_dir(repo):
    return repo / "docs" / "exec-plans" / "active"


def completed_plan_dir(repo):
    return repo / "docs" / "exec-plans" / "completed"


def plan_path_from_arg(repo, plan_arg):
    raw_plan = Path(plan_arg)
    if raw_plan.is_absolute():
        plan_path = raw_plan.resolve()
    else:
        plan_path = (repo / raw_plan).resolve()

    try:
        relative_plan = str(plan_path.relative_to(repo.resolve()))
    except ValueError as error:
        raise ValueError(f"Plan must be inside repo: {plan_arg}") from error

    if not plan_path.exists():
        raise FileNotFoundError(f"Plan not found: {plan_path}")

    return plan_path, relative_plan


def create_plan(repo, slug, goal):
    plan_dir = active_plan_dir(repo)
    plan_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now(UTC).strftime('%Y-%m-%d')}-{slugify(slug)}.md"
    plan_path = plan_dir / filename
    if plan_path.exists():
        raise FileExistsError(f"Plan already exists: {plan_path}")
    title = slug.replace("-", " ").strip() or "task"
    content = PLAN_TEMPLATE.format(
        title=title.title(),
        goal=goal,
        defect_section=DEFAULT_DEFECT_PLACEHOLDER,
        knowledge_section="- [ ] Add durable facts here as they emerge -> <destination-doc>",
    )
    plan_path.write_text(content)
    state = new_plan_state(plan_path, goal)
    save_plan_state(plan_path, state)
    sync_plan_markdown_from_state(plan_path, state)
    return plan_path


def set_acceptance_contract(plan_path, criteria):
    from .knowledge import clean_fact_text
    state = require_plan_state(plan_path)
    normalized = {key: clean_fact_text(criteria.get(key) or "") for key, _ in QUALITY_DIMENSIONS}
    issues = specific_acceptance_issues(normalized)
    if issues:
        return {
            "status": "fail",
            "reason": "acceptance-criteria-not-specific",
            "message": "acceptance-set requires concrete, task-specific criteria for every dimension.",
            "issues": issues,
        }
    fingerprint = criteria_fingerprint(normalized)
    state["acceptance_contract"] = {
        "status": "ready",
        "criteria": normalized,
        "fingerprint": fingerprint,
    }
    if state.get("quality_result", {}).get("status") in {"pass", "fail"}:
        state["implementation_dirty_after_score"] = True
        reasons = state.setdefault("dirty_reasons", [])
        if "acceptance-contract-changed" not in reasons:
            reasons.append("acceptance-contract-changed")
        state["quality_result"]["status"] = "pending"
    save_plan_state(plan_path, state)
    sync_plan_markdown_from_state(plan_path, state)
    return {"status": "ready", "criteria_fingerprint": fingerprint}


def close_plan(repo, plan_relative_path, summary, force):
    from .continuation import assert_phase_continuity_closed, update_workstreams_after_plan_close
    from .knowledge import extract_knowledge_items, mark_knowledge_items_closed
    plan_path, active_relative_path = plan_path_from_arg(repo, plan_relative_path)
    text = plan_path.read_text()
    if not force:
        assert_plan_placeholders_resolved(text)
        assert_quality_gate_passed(plan_path, text)
        assert_phase_continuity_closed(repo, plan_path, text)
    open_items = [
        item
        for item in extract_knowledge_items(text)
        if item.startswith("- [ ]") and item != DEFAULT_KNOWLEDGE_PLACEHOLDER
    ]
    if open_items and not force:
        raise PlanCloseError(
            "open-durable-knowledge",
            "Cannot close plan with unresolved durable knowledge items.",
            {"open_items": open_items},
        )
    updated_text = replace_completion_notes(mark_knowledge_items_closed(text), summary)
    state = load_plan_state(plan_path)
    if state is not None:
        state = sync_state_from_markdown(plan_path, state)
    completed_dir = completed_plan_dir(repo)
    completed_dir.mkdir(parents=True, exist_ok=True)
    destination = completed_dir / plan_path.name
    destination.write_text(updated_text)
    sidecar = sidecar_path_for_plan(plan_path)
    destination_sidecar = sidecar_path_for_plan(destination)
    if sidecar.exists():
        if state is not None:
            state["markdown_path"] = str(destination)
            state["updated_at"] = utc_now_iso()
            sidecar.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        shutil.move(str(sidecar), str(destination_sidecar))
    plan_path.unlink()
    completed_relative_path = str(destination.relative_to(repo))
    update_workstreams_after_plan_close(repo, active_relative_path, completed_relative_path)
    return destination, open_items

