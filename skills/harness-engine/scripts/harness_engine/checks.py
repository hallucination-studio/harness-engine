from .common import *
from .templates import DEFAULT_KNOWLEDGE_PLACEHOLDER, is_managed_text
from .plans import active_plan_dir, completed_plan_dir, load_plan_state, sync_state_from_markdown, specific_acceptance_issues, criteria_fingerprint, find_section
from .knowledge import extract_knowledge_items, parse_knowledge_item, destination_contains_fact
from .plans import open_defects_for_plan
from .continuation import phase_continuity_issues, continuation_decision_issues, workstreams_path

def check_harness(repo):
    required_files = [
        "AGENTS.md",
        "ARCHITECTURE.md",
        "docs/PLANS.md",
        "docs/QUALITY_SCORE.md",
        "docs/RELIABILITY.md",
        "docs/SECURITY.md",
        "docs/exec-plans/workstreams.md",
        "docs/exec-plans/active/README.md",
        "docs/exec-plans/active/_template.md",
        "docs/exec-plans/completed/README.md",
        "docs/sops/encode-unseen-knowledge.md",
    ]
    issues = []
    for relative_path in required_files:
        if not (repo / relative_path).exists():
            issues.append(
                {
                    "severity": "error",
                    "code": "missing-required-file",
                    "path": relative_path,
                    "message": f"Required harness file is missing: {relative_path}",
                }
            )

    active_dir = active_plan_dir(repo)
    if active_dir.exists():
        for plan_path in sorted(active_dir.glob("*.md")):
            if plan_path.name in {"README.md", "_template.md"}:
                continue
            relative_plan = str(plan_path.relative_to(repo))
            plan_text = plan_path.read_text()
            state = load_plan_state(plan_path)
            if state is None:
                issues.append(
                    {
                        "severity": "error",
                        "code": "missing-plan-sidecar",
                        "path": relative_plan,
                        "message": "Active plan is missing structured JSON sidecar metadata. Run migration or recreate it with plan-start.",
                    }
                )
            else:
                state = sync_state_from_markdown(plan_path, state)
                contract = state.get("acceptance_contract", {})
                criteria = contract.get("criteria") or {}
                acceptance_issues = specific_acceptance_issues(criteria)
                current_fingerprint = criteria_fingerprint(criteria)
                if contract.get("status") != "ready" or acceptance_issues:
                    issues.append(
                        {
                            "severity": "error",
                            "code": "acceptance-contract-not-ready",
                            "path": relative_plan,
                            "message": "Active plan must have a ready, task-specific Acceptance Contract before implementation.",
                            "acceptance_issues": acceptance_issues,
                        }
                    )
                elif contract.get("fingerprint") != current_fingerprint:
                    issues.append(
                        {
                            "severity": "error",
                            "code": "acceptance-fingerprint-stale",
                            "path": relative_plan,
                            "message": "Active plan Acceptance Contract fingerprint does not match current criteria.",
                        }
                    )
            if find_section(plan_text.splitlines(), "## Acceptance Contract") is None:
                issues.append(
                    {
                        "severity": "error",
                        "code": "missing-acceptance-contract",
                        "path": relative_plan,
                        "message": "Active plan is missing an Acceptance Contract section.",
                    }
                )
            if find_section(plan_text.splitlines(), "## Quality Result") is None:
                issues.append(
                    {
                        "severity": "error",
                        "code": "missing-quality-result",
                        "path": relative_plan,
                        "message": "Active plan is missing a Quality Result section.",
                    }
                )
            for defect in open_defects_for_plan(plan_text):
                issues.append(
                    {
                        "severity": "error",
                        "code": "open-defect",
                        "path": relative_plan,
                        "id": defect["id"],
                        "defect_severity": defect["severity"],
                        "message": f"Active plan has an unresolved defect: {defect['summary']}",
                    }
                )
            issues.extend(phase_continuity_issues(repo, plan_path, plan_text))
            for item in extract_knowledge_items(plan_text):
                if item == DEFAULT_KNOWLEDGE_PLACEHOLDER:
                    continue
                parsed = parse_knowledge_item(item)
                if not parsed:
                    issues.append(
                        {
                            "severity": "error",
                            "code": "unparseable-knowledge-item",
                            "path": relative_plan,
                            "message": f"Knowledge item is not parseable: {item}",
                        }
                    )
                    continue
                if parsed["status"] == "open":
                    issues.append(
                        {
                            "severity": "error",
                            "code": "open-durable-knowledge",
                            "path": relative_plan,
                            "destination": parsed["destination"],
                            "message": f"Durable knowledge is still open: {parsed['fact']}",
                        }
                    )
                else:
                    verification_text = parsed["evidence"] or parsed["fact"]
                    if destination_contains_fact(repo, parsed["destination"], verification_text):
                        continue
                    issues.append(
                        {
                            "severity": "error",
                            "code": "missing-written-knowledge",
                            "path": relative_plan,
                            "destination": parsed["destination"],
                            "message": f"Marked knowledge evidence is missing from destination: {verification_text}",
                        }
                    )

    completed_dir = completed_plan_dir(repo)
    if completed_dir.exists():
        for plan_path in sorted(completed_dir.glob("*.md")):
            if plan_path.name == "README.md":
                continue
            relative_plan = str(plan_path.relative_to(repo))
            state = load_plan_state(plan_path)
            if state is None:
                issues.append(
                    {
                        "severity": "error",
                        "code": "missing-plan-sidecar",
                        "path": relative_plan,
                        "message": "Completed plan is missing structured JSON sidecar metadata. Run migration or recreate structured plan history.",
                    }
                )
                continue
            state = sync_state_from_markdown(plan_path, state)
            contract = state.get("acceptance_contract", {})
            criteria = contract.get("criteria") or {}
            current_fingerprint = criteria_fingerprint(criteria)
            quality = state.get("quality_result", {})
            if contract.get("status") != "ready":
                issues.append(
                    {
                        "severity": "error",
                        "code": "completed-acceptance-contract-not-ready",
                        "path": relative_plan,
                        "message": "Completed plan must have a ready Acceptance Contract.",
                    }
                )
            if quality.get("status") != "pass":
                issues.append(
                    {
                        "severity": "error",
                        "code": "completed-quality-result-not-passing",
                        "path": relative_plan,
                        "message": "Completed plan must have a passing Quality Result.",
                    }
                )
            if quality.get("criteria_fingerprint") != current_fingerprint:
                issues.append(
                    {
                        "severity": "error",
                        "code": "completed-quality-fingerprint-stale",
                        "path": relative_plan,
                        "message": "Completed plan Quality Result was not scored against the current Acceptance Contract.",
                    }
                )
            issues.extend(continuation_decision_issues(repo, plan_path, plan_path.read_text()))

    ledger = workstreams_path(repo)
    if ledger.exists():
        for index, line in enumerate(ledger.read_text().splitlines(), start=1):
            stripped = line.strip()
            if not stripped.startswith("|") or stripped.startswith("| ---") or stripped.startswith("| ID |"):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) != 6:
                continue
            workstream_id, _, current_plan, last_completed_plan, _, _ = cells
            for label, plan_value in [
                ("current plan", current_plan),
                ("last completed plan", last_completed_plan),
            ]:
                if plan_value in {"", "none", "n/a", "-"}:
                    continue
                if not (repo / plan_value).exists():
                    issues.append(
                        {
                            "severity": "error",
                            "code": "missing-workstream-plan-reference",
                            "path": str(ledger.relative_to(repo)),
                            "line": index,
                            "workstream": workstream_id,
                            "message": f"Workstream {workstream_id} references missing {label}: {plan_value}",
                        }
                    )

    return {
        "repo": str(repo),
        "status": "pass" if not issues else "fail",
        "issue_count": len(issues),
        "issues": issues,
    }


def docs_text_for_reference_scan(repo):
    docs_root = repo / "docs"
    chunks = []
    roots = [repo / "AGENTS.md", repo / "ARCHITECTURE.md"]
    if docs_root.exists():
        roots.extend(path for path in docs_root.rglob("*") if path.is_file())
    for path in roots:
        if not path.exists() or not path.is_file():
            continue
        try:
            chunks.append(path.read_text())
        except UnicodeDecodeError:
            continue
    return "\n".join(chunks)


def evidence_prune_candidates(repo, root="docs/generated", older_than_days=14):
    evidence_root = (repo / root).resolve()
    if not evidence_root.exists():
        return []
    try:
        evidence_root.relative_to(repo.resolve())
    except ValueError as error:
        raise ValueError(f"Evidence root must be inside repo: {root}") from error

    now = time.time()
    max_age_seconds = older_than_days * 24 * 60 * 60
    docs_text = docs_text_for_reference_scan(repo)
    candidates = []
    for path in sorted(evidence_root.rglob("*")):
        if not path.is_file():
            continue
        relative_path = str(path.relative_to(repo))
        try:
            content = path.read_text()
        except UnicodeDecodeError:
            content = ""
        if is_managed_text(content):
            continue
        age_seconds = now - path.stat().st_mtime
        if age_seconds < max_age_seconds:
            continue
        if relative_path in docs_text or path.name in docs_text:
            continue
        candidates.append(
            {
                "path": relative_path,
                "age_days": round(age_seconds / (24 * 60 * 60), 1),
                "reason": (
                    f"unreferenced file under {root} older than {older_than_days} days "
                    "and not a managed starter"
                ),
            }
        )
    return candidates


