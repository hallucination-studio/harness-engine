from .common import *
from .plans import find_section, mark_state_dirty, open_defects_for_plan, replace_section, utc_now_iso
from .templates import ensure_parent

def extract_knowledge_items(text):
    lines = text.splitlines()
    section_index = find_section(lines, "## Durable Knowledge To Capture")
    if section_index is None:
        return []
    items = []
    for line in lines[section_index + 1 :]:
        if line.startswith("## "):
            break
        stripped = line.strip()
        if stripped.startswith("- ["):
            items.append(stripped)
    return items


def extract_defect_items(text):
    lines = text.splitlines()
    section_index = find_section(lines, "## Defects To Resolve")
    if section_index is None:
        return []
    items = []
    for line in lines[section_index + 1 :]:
        if line.startswith("## "):
            break
        stripped = line.strip()
        if stripped.startswith("- ["):
            items.append(stripped)
    return items


def knowledge_id_for(fact, destination):
    digest = hashlib.sha1(f"{clean_destination_text(destination)}\0{clean_fact_text(fact)}".encode()).hexdigest()
    return f"hk-{digest[:10]}"


def defect_id_for(summary):
    digest = hashlib.sha1(clean_fact_text(summary).encode()).hexdigest()
    return f"bug-{digest[:10]}"


def parse_knowledge_item(item):
    match = re.match(
        r"- \[(?P<status>[ xX])\]\s+"
        r"(?:\[(?:id|kid):(?P<id>[A-Za-z0-9_.:-]+)\]\s+)?"
        r"(?P<fact>.*?)\s+->\s+"
        r"(?P<destination>[^|]+?)"
        r"(?:\s+\|\s+evidence:\s+(?P<evidence>.+))?$",
        item.strip(),
    )
    if not match:
        return None
    return {
        "status": "closed" if match.group("status").lower() == "x" else "open",
        "id": match.group("id"),
        "fact": clean_fact_text(match.group("fact")),
        "destination": clean_destination_text(match.group("destination")),
        "evidence": clean_fact_text(match.group("evidence")) if match.group("evidence") else None,
        "raw": item,
    }


def parse_defect_item(item):
    match = re.match(
        r"- \[(?P<status>[ xX])\]\s+"
        r"(?:\[(?:id|bug):(?P<id>[A-Za-z0-9_.:-]+)\]\s+)?"
        r"\[(?P<severity>P[0-3])\]\s+"
        r"(?P<summary>.*?)"
        r"(?:\s+\|\s+evidence:\s+(?P<evidence>.*?))?"
        r"(?:\s+\|\s+fix:\s+(?P<fix>.+))?$",
        item.strip(),
    )
    if not match:
        return None
    return {
        "status": "closed" if match.group("status").lower() == "x" else "open",
        "id": match.group("id") or defect_id_for(match.group("summary")),
        "severity": match.group("severity"),
        "summary": clean_fact_text(match.group("summary")),
        "evidence": clean_fact_text(match.group("evidence")) if match.group("evidence") else None,
        "fix": clean_fact_text(match.group("fix")) if match.group("fix") else None,
        "raw": item,
    }


def clean_fact_text(value):
    cleaned = value.strip()
    cleaned = cleaned.replace("`", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def clean_destination_text(value):
    return value.strip().strip("`")


def append_knowledge_item(plan_path, fact, destination):
    text = plan_path.read_text()
    lines = text.splitlines()
    section_index = find_section(lines, "## Durable Knowledge To Capture")
    if section_index is None:
        raise ValueError("Plan is missing '## Durable Knowledge To Capture'")
    filtered_lines = [line for line in lines if line.strip() != DEFAULT_KNOWLEDGE_PLACEHOLDER]
    insert_index = section_index + 1
    while insert_index < len(filtered_lines) and not filtered_lines[insert_index].startswith("## "):
        insert_index += 1
    item_id = knowledge_id_for(fact, destination)
    item = f"- [ ] [id:{item_id}] {fact} -> {destination}"
    updated_lines = filtered_lines[:insert_index] + [item] + filtered_lines[insert_index:]
    plan_path.write_text("\n".join(updated_lines).rstrip() + "\n")
    mark_state_dirty(plan_path, "knowledge-item-logged")
    return item, item_id


def render_open_defect_rework(open_defects):
    lines = ["- Resolve all open defects, then re-run validation and `quality-score`."]
    for defect in open_defects:
        evidence = f" Evidence: {defect['evidence']}." if defect.get("evidence") else ""
        lines.append(f"- Resolve {defect['id']} ({defect['severity']}): {defect['summary']}.{evidence}")
    return "\n".join(lines)


def mark_quality_gate_blocked_by_defects(text):
    open_defects = open_defects_for_plan(text)
    if not open_defects:
        return text
    lines = text.splitlines()
    section_index = find_section(lines, "## Quality Result")
    if section_index is None:
        gate_text = "\n".join(
            [
                "Status: fail",
                "Minimum score: 8.0",
                "Average score: pending",
                f"Last scored: {utc_now_iso()}",
                "Criteria fingerprint: pending",
                "",
                "Blocked by unresolved defects. Run `defect-resolve`, re-run validation, then run `quality-score`.",
            ]
        )
        text = replace_section(text, "Quality Result", gate_text)
    else:
        end_index = len(lines)
        for index in range(section_index + 1, len(lines)):
            if lines[index].startswith("## "):
                end_index = index
                break
        section_lines = lines[section_index + 1 : end_index]
        has_status = False
        updated_section = []
        for line in section_lines:
            if line.startswith("Status:"):
                updated_section.append("Status: pending")
                has_status = True
            elif line.startswith("Last scored:"):
                updated_section.append(f"Last scored: {utc_now_iso()}")
            else:
                updated_section.append(line)
        if not has_status:
            updated_section.insert(0, "Status: pending")
        lines = lines[: section_index + 1] + updated_section + lines[end_index:]
        text = "\n".join(lines).rstrip() + "\n"
    return replace_section(text, "Rework Required", render_open_defect_rework(open_defects))


def append_defect_item(plan_path, severity, summary, evidence=None):
    text = plan_path.read_text()
    if find_section(text.splitlines(), "## Defects To Resolve") is None:
        text = replace_section(text, "Defects To Resolve", DEFAULT_DEFECT_PLACEHOLDER)
    lines = text.splitlines()
    section_index = find_section(lines, "## Defects To Resolve")
    if section_index is None:
        raise ValueError("Plan is missing '## Defects To Resolve'")
    filtered_lines = [line for line in lines if line.strip() != DEFAULT_DEFECT_PLACEHOLDER]
    insert_index = section_index + 1
    while insert_index < len(filtered_lines) and not filtered_lines[insert_index].startswith("## "):
        insert_index += 1
    item_id = defect_id_for(summary)
    safe_summary = clean_fact_text(summary)
    safe_evidence = clean_fact_text(evidence) if evidence else None
    item = f"- [ ] [bug:{item_id}] [{severity}] {safe_summary}"
    if safe_evidence:
        item = f"{item} | evidence: {safe_evidence}"
    updated_lines = filtered_lines[:insert_index] + [item] + filtered_lines[insert_index:]
    plan_path.write_text(mark_quality_gate_blocked_by_defects("\n".join(updated_lines).rstrip() + "\n"))
    mark_state_dirty(plan_path, "defect-logged")
    return item, item_id


def close_defect_line(line, fix_evidence):
    updated = line.replace("- [ ]", "- [x]", 1)
    if "| fix:" not in updated:
        updated = f"{updated} | fix: {fix_evidence}"
    return updated


def mark_defect_resolved(plan_path, defect_id, fix_evidence):
    if not defect_id:
        raise ValueError("Provide --id to resolve a defect")
    if not fix_evidence:
        raise ValueError("Provide --fix-evidence or --fix-evidence-file to resolve a defect")
    lines = plan_path.read_text().splitlines()
    safe_fix = clean_fact_text(fix_evidence)
    replaced = False
    updated = []
    for line in lines:
        stripped = line.strip()
        parsed = parse_defect_item(stripped)
        if parsed and parsed["status"] == "open" and parsed["id"] == defect_id and not replaced:
            updated.append(close_defect_line(line, safe_fix))
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        raise ValueError(f"Open defect not found for id: {defect_id}")
    text = "\n".join(updated).rstrip() + "\n"
    open_defects = open_defects_for_plan(text)
    if open_defects:
        text = replace_section(text, "Rework Required", render_open_defect_rework(open_defects))
    else:
        text = replace_section(
            text,
            "Rework Required",
            "Defects resolved. Re-run validation and `quality-score` before closing.",
        )
    plan_path.write_text(text)
    mark_state_dirty(plan_path, "defect-resolved")


def mark_knowledge_items_closed(text):
    lines = text.splitlines()
    updated = []
    in_knowledge_section = False
    for line in lines:
        if line.startswith("## "):
            in_knowledge_section = line.strip().lower() == "## durable knowledge to capture"
        if in_knowledge_section and line.strip().startswith("- [ ]") and line.strip() != DEFAULT_KNOWLEDGE_PLACEHOLDER:
            updated.append(line.replace("- [ ]", "- [x]", 1))
        else:
            updated.append(line)
    return "\n".join(updated).rstrip() + "\n"


def destination_contains_fact(repo, destination, fact):
    target = repo / destination
    if not target.exists() or not target.is_file():
        return False
    try:
        return normalize_fact_for_match(fact) in normalize_fact_for_match(target.read_text())
    except UnicodeDecodeError:
        return False


def normalize_fact_for_match(value):
    normalized = value.replace("`", "")
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip()
    normalized = re.sub(r"[.。]+$", "", normalized)
    return normalized


def append_fact_to_destination(repo, destination, fact):
    target = repo / destination
    ensure_parent(target)
    existing = ""
    if target.exists():
        existing = target.read_text()
    separator = "\n" if existing.endswith("\n") or not existing else "\n\n"
    target.write_text(existing + separator + fact + "\n")


def close_knowledge_line(line, evidence=None):
    updated = line.replace("- [ ]", "- [x]", 1)
    if evidence and "| evidence:" not in updated:
        updated = f"{updated} | evidence: {evidence}"
    return updated


def mark_single_knowledge_item_written(
    repo,
    plan_path,
    fact_text=None,
    destination=None,
    append=False,
    knowledge_id=None,
    evidence=None,
):
    if not fact_text and not knowledge_id:
        raise ValueError("Provide either --id or --fact to mark knowledge as written")
    lines = plan_path.read_text().splitlines()
    target = clean_fact_text(fact_text) if fact_text else None
    target_destination = clean_destination_text(destination) if destination else None
    target_evidence = clean_fact_text(evidence) if evidence else None
    replaced = False
    updated = []
    for line in lines:
        stripped = line.strip()
        parsed = parse_knowledge_item(stripped)
        if not parsed:
            updated.append(line)
            continue
        destination_matches = target_destination is None or parsed["destination"] == target_destination
        fact_matches = target is not None and normalize_fact_for_match(target) == normalize_fact_for_match(parsed["fact"])
        id_matches = knowledge_id is not None and parsed["id"] == knowledge_id
        if stripped.startswith("- [ ]") and (id_matches or fact_matches) and destination_matches and not replaced:
            parsed_destination = parsed["destination"]
            if not parsed_destination:
                raise ValueError("Destination is required to verify durable knowledge")
            verification_text = target_evidence or target or parsed["fact"]
            if not destination_contains_fact(repo, parsed_destination, verification_text):
                if append:
                    append_fact_to_destination(repo, parsed_destination, verification_text)
                else:
                    raise ValueError(
                        f"Destination {parsed_destination} does not contain verification text: {verification_text}. "
                        "Write it there first, pass --evidence with text present in the doc, or re-run with --append."
                    )
            updated.append(close_knowledge_line(line, evidence=target_evidence))
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        target_description = f"id: {knowledge_id}" if knowledge_id else f"fact: {fact_text}"
        raise ValueError(f"Open knowledge item not found for {target_description}")
    plan_path.write_text("\n".join(updated).rstrip() + "\n")
    mark_state_dirty(plan_path, "knowledge-item-written")
