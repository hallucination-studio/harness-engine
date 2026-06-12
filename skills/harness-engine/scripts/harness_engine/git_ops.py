from .common import *
from .templates import ensure_parent

def ensure_gitignore(repo):
    path = repo / ".gitignore"
    existing = path.read_text() if path.exists() else ""
    block_lines = [GITIGNORE_BLOCK_START, *GITIGNORE_ENTRIES, GITIGNORE_BLOCK_END]
    block = "\n".join(block_lines)
    pattern = re.compile(
        rf"(^|\n){re.escape(GITIGNORE_BLOCK_START)}\n.*?\n{re.escape(GITIGNORE_BLOCK_END)}(?=\n|$)",
        flags=re.DOTALL,
    )
    if pattern.search(existing):
        updated = pattern.sub(lambda match: match.group(1) + block, existing)
    else:
        prefix = existing.rstrip()
        updated = f"{prefix}\n\n{block}" if prefix else block
    updated = updated.rstrip() + "\n"
    changed = updated != existing
    if changed:
        path.write_text(updated)
    return {
        "path": ".gitignore",
        "updated": changed,
        "entries": GITIGNORE_ENTRIES,
    }


def clean_init_state(repo):
    cleaned = []
    for relative_dir in CLEAN_INIT_DIRS:
        root = repo / relative_dir
        if not root.exists():
            continue
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                cleaned.append(str(path.relative_to(repo)))
                path.unlink()
            elif path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
    return cleaned


def git_tracked_harness_runtime_files(repo, roots=None):
    if not (repo / ".git").exists():
        return []
    roots = roots or GIT_CLEAN_PATHS
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-files", *roots],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git ls-files failed")
    return [line for line in result.stdout.splitlines() if line.strip()]


def git_untrack_files(repo, paths):
    if not paths:
        return []
    result = subprocess.run(
        ["git", "-C", str(repo), "rm", "-r", "--cached", "--", *paths],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git rm --cached failed")
    return paths


def git_add_paths(repo, paths):
    if not paths:
        return []
    result = subprocess.run(
        ["git", "-C", str(repo), "add", "--", *paths],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git add failed")
    return paths

