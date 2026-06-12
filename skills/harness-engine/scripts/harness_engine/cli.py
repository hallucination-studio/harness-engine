import argparse
import json
from pathlib import Path

from .analysis import analyze_repo
from .templates import make_default_answers, ensure_parent, write_scaffold
from .plans import (PlanCloseError, sidecar_path_for_plan, create_plan, plan_path_from_arg, set_acceptance_contract, close_plan, ensure_acceptance_ready, missing_quality_notes, weak_quality_notes, update_quality_gate)
from .knowledge import append_knowledge_item, append_defect_item, mark_defect_resolved, mark_single_knowledge_item_written
from .continuation import map_legacy_phase_mode, default_workstream_id_from_plan, continuation_command_issues, update_phase_continuity, append_workstream_entry, plan_goal_for_workstream, update_continuation_decision
from .checks import check_harness, evidence_prune_candidates
from .git_ops import CLEAN_INIT_DIRS, ensure_gitignore, clean_init_state, git_tracked_harness_runtime_files, git_untrack_files, git_add_paths

def load_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, payload):
    output = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if path:
        target = Path(path)
        ensure_parent(target)
        target.write_text(output)
    else:
        print(output, end="")


def read_text_arg(value=None, file_path=None, label="value"):
    if value and file_path:
        raise ValueError(f"Use either --{label} or --{label}-file, not both")
    if file_path:
        return Path(file_path).read_text().strip()
    return value


def command_analyze(args):
    repo = Path(args.repo).resolve()
    analysis = analyze_repo(repo)
    write_json(args.output, analysis)


def command_sample_answers(args):
    analysis = load_json(args.analysis)
    payload = make_default_answers(analysis)
    write_json(args.output, payload)


def command_init(args):
    repo = Path(args.repo).resolve()
    analysis = analyze_repo(repo)
    answers = load_json(args.answers)
    has_harness = bool(analysis["existing_harness_files"] or analysis["existing_managed_files"])
    effective_refresh = has_harness or args.force
    written, skipped, created, refreshed = write_scaffold(
        repo,
        analysis,
        answers,
        refresh_managed=effective_refresh,
        force=args.force,
    )
    result = {
        "repo": str(repo),
        "written": written,
        "created": created,
        "refreshed": refreshed,
        "skipped": skipped,
        "mode": "init",
        "operation": "reconciled" if has_harness else "created",
        "refresh_managed": effective_refresh,
        "force": args.force,
    }
    write_json(args.output, result)


def command_plan_start(args):
    repo = Path(args.repo).resolve()
    plan_path = create_plan(repo, args.slug, args.goal)
    result = {
        "repo": str(repo),
        "plan": str(plan_path),
        "metadata": str(sidecar_path_for_plan(plan_path)),
        "acceptance_contract": "draft",
        "status": "created",
    }
    write_json(args.output, result)


def command_acceptance_set(args):
    repo = Path(args.repo).resolve()
    plan_path, _ = plan_path_from_arg(repo, args.plan)
    criteria = {
        "product_correctness": args.product,
        "ux_operator_clarity": args.ux,
        "architecture_maintainability": args.architecture,
        "reliability_observability": args.reliability,
        "security_data_handling": args.security,
    }
    result = set_acceptance_contract(plan_path, criteria)
    result.update({"repo": str(repo), "plan": str(plan_path), "metadata": str(sidecar_path_for_plan(plan_path))})
    write_json(args.output, result)
    if result["status"] != "ready":
        raise SystemExit(1)


def command_knowledge_log(args):
    repo = Path(args.repo).resolve()
    plan_path, _ = plan_path_from_arg(repo, args.plan)
    fact = read_text_arg(args.fact, args.fact_file, "fact")
    if not fact:
        raise ValueError("Provide --fact or --fact-file")
    item, item_id = append_knowledge_item(plan_path, fact, args.destination)
    result = {"repo": str(repo), "plan": str(plan_path), "id": item_id, "logged": item}
    write_json(args.output, result)


def command_defect_log(args):
    repo = Path(args.repo).resolve()
    plan_path, _ = plan_path_from_arg(repo, args.plan)
    summary = read_text_arg(args.summary, args.summary_file, "summary")
    evidence = read_text_arg(args.evidence, args.evidence_file, "evidence")
    if not summary:
        raise ValueError("Provide --summary or --summary-file")
    item, item_id = append_defect_item(plan_path, args.severity, summary, evidence=evidence)
    result = {"repo": str(repo), "plan": str(plan_path), "id": item_id, "logged": item, "status": "fail"}
    write_json(args.output, result)
    raise SystemExit(1)


def command_defect_resolve(args):
    repo = Path(args.repo).resolve()
    plan_path, _ = plan_path_from_arg(repo, args.plan)
    fix_evidence = read_text_arg(args.fix_evidence, args.fix_evidence_file, "fix-evidence")
    mark_defect_resolved(plan_path, args.id, fix_evidence)
    result = {
        "repo": str(repo),
        "plan": str(plan_path),
        "id": args.id,
        "status": "resolved",
        "fix_evidence": fix_evidence,
    }
    write_json(args.output, result)


def command_plan_close(args):
    repo = Path(args.repo).resolve()
    try:
        destination, unresolved = close_plan(repo, args.plan, args.summary, args.force)
    except PlanCloseError as error:
        plan = None
        try:
            plan_path, _ = plan_path_from_arg(repo, args.plan)
            plan = str(plan_path)
        except Exception:
            plan = args.plan
        result = {
            "repo": str(repo),
            "plan": plan,
            "status": "blocked",
            "reason": error.reason,
            "message": str(error),
            "details": error.details,
        }
        write_json(args.output, result)
        raise SystemExit(1)
    result = {
        "repo": str(repo),
        "closed_plan": str(destination),
        "unresolved_items_forced": unresolved,
        "status": "closed",
    }
    write_json(args.output, result)


def score_arg(args, name):
    value = getattr(args, name)
    if value < 0 or value > 10:
        raise ValueError(f"{name.replace('_', '-')} must be between 0 and 10")
    return float(value)


def command_quality_score(args):
    repo = Path(args.repo).resolve()
    plan_path, _ = plan_path_from_arg(repo, args.plan)
    try:
        ensure_acceptance_ready(plan_path)
    except RuntimeError as error:
        result = {
            "status": "fail",
            "repo": str(repo),
            "plan": str(plan_path),
            "reason": "acceptance-contract-not-ready",
            "message": str(error),
        }
        write_json(args.output, result)
        raise SystemExit(1)
    scores = {
        "product_correctness": score_arg(args, "product_correctness"),
        "ux_operator_clarity": score_arg(args, "ux_operator_clarity"),
        "architecture_maintainability": score_arg(args, "architecture_maintainability"),
        "reliability_observability": score_arg(args, "reliability_observability"),
        "security_data_handling": score_arg(args, "security_data_handling"),
    }
    notes = {
        "product_correctness": args.product_note,
        "ux_operator_clarity": args.ux_note,
        "architecture_maintainability": args.architecture_note,
        "reliability_observability": args.reliability_note,
        "security_data_handling": args.security_note,
    }
    missing_notes = missing_quality_notes(notes)
    if missing_notes and not args.allow_empty_notes:
        result = {
            "status": "fail",
            "repo": str(repo),
            "plan": str(plan_path),
            "reason": "missing-quality-notes",
            "message": "quality-score requires evidence notes for every dimension.",
            "missing_notes": missing_notes,
        }
        write_json(args.output, result)
        raise SystemExit(1)
    weak_notes = weak_quality_notes(notes)
    if weak_notes and not args.allow_empty_notes:
        result = {
            "status": "fail",
            "repo": str(repo),
            "plan": str(plan_path),
            "reason": "weak-quality-notes",
            "message": "quality-score requires concrete verification evidence notes.",
            "weak_notes": weak_notes,
        }
        write_json(args.output, result)
        raise SystemExit(1)
    result = update_quality_gate(plan_path, scores, notes, args.minimum)
    result.update({"repo": str(repo), "plan": str(plan_path)})
    write_json(args.output, result)
    if result["status"] != "pass":
        raise SystemExit(1)


def command_phase_set(args):
    repo = Path(args.repo).resolve()
    plan_path, relative_plan = plan_path_from_arg(repo, args.plan)
    decision = map_legacy_phase_mode(args.mode)
    resolved_workstream = args.workstream or (
        default_workstream_id_from_plan(plan_path, plan_path.read_text()) if decision in {"continue", "pause"} else "none"
    )
    issues = continuation_command_issues(
        repo,
        relative_plan,
        decision,
        resolved_workstream,
        args.continuation,
        args.next_action,
        args.closure_reason,
        args.resume_notes,
    )
    if issues:
        result = {
            "status": "blocked",
            "repo": str(repo),
            "plan": str(plan_path),
            "reason": "continuation-decision-incomplete",
            "message": "Cannot update continuation decision until required fields are provided.",
            "issues": issues,
            "warning": "phase-set is deprecated; use continuation-set.",
        }
        write_json(args.output, result)
        raise SystemExit(1)
    result = update_phase_continuity(
        plan_path,
        args.mode,
        resolved_workstream,
        args.current_phase,
        args.next_phase,
        args.continuation,
        args.next_action,
        args.closure_reason,
        args.resume_notes,
    )
    if result["decision"] in {"continue", "pause"}:
        append_workstream_entry(
            repo,
            result["workstream"],
            "active" if result["decision"] == "continue" else "paused",
            relative_plan,
            "none",
            args.next_action,
            plan_goal_for_workstream(plan_path, args.closure_reason),
            args.resume_notes,
        )
    result.update(
        {
            "repo": str(repo),
            "plan": str(plan_path),
            "warning": "phase-set is deprecated; use continuation-set.",
        }
    )
    write_json(args.output, result)


def command_continuation_set(args):
    repo = Path(args.repo).resolve()
    plan_path, relative_plan = plan_path_from_arg(repo, args.plan)
    decision = args.decision.lower()
    resolved_workstream = args.workstream or (
        default_workstream_id_from_plan(plan_path, plan_path.read_text()) if decision in {"continue", "pause"} else "none"
    )
    issues = continuation_command_issues(
        repo,
        relative_plan,
        decision,
        resolved_workstream,
        args.next_target,
        args.next_action,
        args.closure_reason,
        args.resume_notes,
    )
    if issues:
        result = {
            "status": "blocked",
            "repo": str(repo),
            "plan": str(plan_path),
            "reason": "continuation-decision-incomplete",
            "message": "Cannot update continuation decision until required fields are provided.",
            "issues": issues,
        }
        write_json(args.output, result)
        raise SystemExit(1)
    result = update_continuation_decision(
        plan_path,
        decision,
        resolved_workstream,
        args.next_target,
        args.next_action,
        args.closure_reason,
        args.resume_notes,
    )
    if result["decision"] in {"continue", "pause"}:
        append_workstream_entry(
            repo,
            result["workstream"],
            "active" if result["decision"] == "continue" else "paused",
            relative_plan,
            "none",
            result["next_action"],
            plan_goal_for_workstream(plan_path, args.goal),
            args.resume_notes,
        )
    result.update({"repo": str(repo), "plan": str(plan_path)})
    write_json(args.output, result)


def command_workstream_upsert(args):
    repo = Path(args.repo).resolve()
    target = append_workstream_entry(
        repo,
        args.id,
        args.status,
        args.current_plan,
        args.last_completed_plan,
        args.next_action,
        args.goal,
        args.resume_notes,
    )
    result = {"repo": str(repo), "workstreams": str(target), "id": args.id, "status": "updated"}
    write_json(args.output, result)


def command_knowledge_mark_written(args):
    repo = Path(args.repo).resolve()
    plan_path, _ = plan_path_from_arg(repo, args.plan)
    fact = read_text_arg(args.fact, args.fact_file, "fact")
    evidence = read_text_arg(args.evidence, args.evidence_file, "evidence")
    mark_single_knowledge_item_written(
        repo,
        plan_path,
        fact,
        args.destination,
        append=args.append,
        knowledge_id=args.id,
        evidence=evidence,
    )
    result = {
        "repo": str(repo),
        "plan": str(plan_path),
        "marked_written": args.id or fact,
        "destination": args.destination,
        "evidence": evidence,
    }
    write_json(args.output, result)


def command_check(args):
    repo = Path(args.repo).resolve()
    result = check_harness(repo)
    write_json(args.output, result)
    if result["status"] != "pass":
        raise SystemExit(1)


def command_evidence_prune(args):
    repo = Path(args.repo).resolve()
    candidates = evidence_prune_candidates(
        repo,
        root=args.root,
        older_than_days=args.older_than_days,
    )
    removed = []
    if args.apply:
        for candidate in candidates:
            path = repo / candidate["path"]
            if path.exists() and path.is_file():
                path.unlink()
                removed.append(candidate["path"])
    result = {
        "repo": str(repo),
        "root": args.root,
        "older_than_days": args.older_than_days,
        "mode": "apply" if args.apply else "dry-run",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "removed": removed,
    }
    write_json(args.output, result)


def command_clean(args):
    repo = Path(args.repo).resolve()
    candidates = git_tracked_harness_runtime_files(repo)
    local_clean_candidates = []
    for relative_dir in CLEAN_INIT_DIRS:
        root = repo / relative_dir
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() or path.is_symlink():
                local_clean_candidates.append(str(path.relative_to(repo)))
    gitignore = None
    removed_from_index = []
    cleaned = []
    if args.apply:
        gitignore = ensure_gitignore(repo)
        cleaned = clean_init_state(repo)
        removed_from_index = git_untrack_files(repo, candidates)
        if gitignore["updated"]:
            git_add_paths(repo, [gitignore["path"]])
    result = {
        "repo": str(repo),
        "mode": "apply" if args.apply else "dry-run",
        "tracked_candidate_count": len(candidates),
        "tracked_candidates": candidates,
        "local_candidate_count": len(local_clean_candidates),
        "local_candidates": local_clean_candidates,
        "gitignore": gitignore,
        "removed_from_index": removed_from_index,
        "cleaned": cleaned,
        "next_steps": (
            [
                "Review staged changes with `git status --short` and `git diff --cached --stat`.",
                "Commit and push to remove these files from the remote repository.",
            ]
            if args.apply
            else ["Re-run with `--apply` to clean local harness runtime files, update .gitignore, and stage git index removals."]
        ),
    }
    write_json(args.output, result)


def build_parser():
    parser = argparse.ArgumentParser(description="Manage the harness repo scaffold.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("--repo", required=True)
    analyze.add_argument("--output")
    analyze.set_defaults(func=command_analyze)

    sample_answers = subparsers.add_parser("sample-answers")
    sample_answers.add_argument("--analysis", required=True)
    sample_answers.add_argument("--output")
    sample_answers.set_defaults(func=command_sample_answers)

    init = subparsers.add_parser("init")
    init.add_argument("--repo", required=True)
    init.add_argument("--answers", required=True)
    init.add_argument("--output")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)

    plan_start = subparsers.add_parser("plan-start")
    plan_start.add_argument("--repo", required=True)
    plan_start.add_argument("--slug", required=True)
    plan_start.add_argument("--goal", required=True)
    plan_start.add_argument("--output")
    plan_start.set_defaults(func=command_plan_start)

    acceptance_set = subparsers.add_parser("acceptance-set")
    acceptance_set.add_argument("--repo", required=True)
    acceptance_set.add_argument("--plan", required=True)
    acceptance_set.add_argument("--product", required=True)
    acceptance_set.add_argument("--ux", required=True)
    acceptance_set.add_argument("--architecture", required=True)
    acceptance_set.add_argument("--reliability", required=True)
    acceptance_set.add_argument("--security", required=True)
    acceptance_set.add_argument("--output")
    acceptance_set.set_defaults(func=command_acceptance_set)

    knowledge_log = subparsers.add_parser("knowledge-log")
    knowledge_log.add_argument("--repo", required=True)
    knowledge_log.add_argument("--plan", required=True)
    knowledge_log.add_argument("--fact")
    knowledge_log.add_argument("--fact-file")
    knowledge_log.add_argument("--destination", required=True)
    knowledge_log.add_argument("--output")
    knowledge_log.set_defaults(func=command_knowledge_log)

    defect_log = subparsers.add_parser("defect-log")
    defect_log.add_argument("--repo", required=True)
    defect_log.add_argument("--plan", required=True)
    defect_log.add_argument("--severity", choices=["P0", "P1", "P2", "P3"], required=True)
    defect_log.add_argument("--summary")
    defect_log.add_argument("--summary-file")
    defect_log.add_argument("--evidence")
    defect_log.add_argument("--evidence-file")
    defect_log.add_argument("--output")
    defect_log.set_defaults(func=command_defect_log)

    defect_resolve = subparsers.add_parser("defect-resolve")
    defect_resolve.add_argument("--repo", required=True)
    defect_resolve.add_argument("--plan", required=True)
    defect_resolve.add_argument("--id", required=True)
    defect_resolve.add_argument("--fix-evidence")
    defect_resolve.add_argument("--fix-evidence-file")
    defect_resolve.add_argument("--output")
    defect_resolve.set_defaults(func=command_defect_resolve)

    knowledge_mark_written = subparsers.add_parser("knowledge-mark-written")
    knowledge_mark_written.add_argument("--repo", required=True)
    knowledge_mark_written.add_argument("--plan", required=True)
    knowledge_mark_written.add_argument("--id")
    knowledge_mark_written.add_argument("--fact")
    knowledge_mark_written.add_argument("--fact-file")
    knowledge_mark_written.add_argument("--destination")
    knowledge_mark_written.add_argument("--evidence")
    knowledge_mark_written.add_argument("--evidence-file")
    knowledge_mark_written.add_argument("--append", action="store_true")
    knowledge_mark_written.add_argument("--output")
    knowledge_mark_written.set_defaults(func=command_knowledge_mark_written)

    plan_close = subparsers.add_parser("plan-close")
    plan_close.add_argument("--repo", required=True)
    plan_close.add_argument("--plan", required=True)
    plan_close.add_argument("--summary", required=True)
    plan_close.add_argument("--force", action="store_true")
    plan_close.add_argument("--output")
    plan_close.set_defaults(func=command_plan_close)

    quality_score = subparsers.add_parser("quality-score")
    quality_score.add_argument("--repo", required=True)
    quality_score.add_argument("--plan", required=True)
    quality_score.add_argument("--minimum", type=float, default=8.0)
    quality_score.add_argument("--product-correctness", type=float, required=True)
    quality_score.add_argument("--ux-operator-clarity", type=float, required=True)
    quality_score.add_argument("--architecture-maintainability", type=float, required=True)
    quality_score.add_argument("--reliability-observability", type=float, required=True)
    quality_score.add_argument("--security-data-handling", type=float, required=True)
    quality_score.add_argument("--product-note", default="")
    quality_score.add_argument("--ux-note", default="")
    quality_score.add_argument("--architecture-note", default="")
    quality_score.add_argument("--reliability-note", default="")
    quality_score.add_argument("--security-note", default="")
    quality_score.add_argument("--allow-empty-notes", action="store_true")
    quality_score.add_argument("--output")
    quality_score.set_defaults(func=command_quality_score)

    continuation_set = subparsers.add_parser("continuation-set")
    continuation_set.add_argument("--repo", required=True)
    continuation_set.add_argument("--plan", required=True)
    continuation_set.add_argument(
        "--decision",
        choices=["complete", "continue", "pause", "stop", "defer"],
        required=True,
    )
    continuation_set.add_argument("--workstream")
    continuation_set.add_argument("--next-target", default="none")
    continuation_set.add_argument("--next-action", default="none")
    continuation_set.add_argument("--closure-reason", default="none")
    continuation_set.add_argument("--resume-notes", default="none")
    continuation_set.add_argument("--goal", default="")
    continuation_set.add_argument("--output")
    continuation_set.set_defaults(func=command_continuation_set)

    phase_set = subparsers.add_parser("phase-set")
    phase_set.add_argument("--repo", required=True)
    phase_set.add_argument("--plan", required=True)
    phase_set.add_argument(
        "--mode",
        choices=["single-phase", "multi-phase", "paused", "completed", "stopped"],
        required=True,
    )
    phase_set.add_argument("--workstream")
    phase_set.add_argument("--current-phase")
    phase_set.add_argument("--next-phase", default="none")
    phase_set.add_argument("--continuation", default="none")
    phase_set.add_argument("--next-action", default="none")
    phase_set.add_argument("--closure-reason", default="none")
    phase_set.add_argument("--resume-notes", default="none")
    phase_set.add_argument("--output")
    phase_set.set_defaults(func=command_phase_set)

    workstream_upsert = subparsers.add_parser("workstream-upsert")
    workstream_upsert.add_argument("--repo", required=True)
    workstream_upsert.add_argument("--id", required=True)
    workstream_upsert.add_argument(
        "--status",
        choices=["active", "paused", "completed", "stopped"],
        required=True,
    )
    workstream_upsert.add_argument("--current-plan", default="none")
    workstream_upsert.add_argument("--last-completed-plan", default="none")
    workstream_upsert.add_argument("--next-action", required=True)
    workstream_upsert.add_argument("--goal", default="")
    workstream_upsert.add_argument("--resume-notes", default="")
    workstream_upsert.add_argument("--output")
    workstream_upsert.set_defaults(func=command_workstream_upsert)

    check = subparsers.add_parser("check")
    check.add_argument("--repo", required=True)
    check.add_argument("--output")
    check.set_defaults(func=command_check)

    evidence_prune = subparsers.add_parser("evidence-prune")
    evidence_prune.add_argument("--repo", required=True)
    evidence_prune.add_argument("--root", default="docs/generated")
    evidence_prune.add_argument("--older-than-days", type=int, default=14)
    evidence_prune.add_argument("--apply", action="store_true")
    evidence_prune.add_argument("--output")
    evidence_prune.set_defaults(func=command_evidence_prune)

    clean = subparsers.add_parser("clean")
    clean.add_argument("--repo", required=True)
    clean.add_argument("--apply", action="store_true")
    clean.add_argument("--output")
    clean.set_defaults(func=command_clean)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
