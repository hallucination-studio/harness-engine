from .common import *
from .templates import is_harness_owned_text

def detect_languages(files):
    ext_map = {}
    for file_path in files:
        suffix = Path(file_path).suffix.lower()
        if suffix:
            ext_map[suffix] = ext_map.get(suffix, 0) + 1
    mapping = {
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".sh": "Shell",
        ".bash": "Shell",
        ".zsh": "Shell",
        ".py": "Python",
        ".rb": "Ruby",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".kt": "Kotlin",
        ".swift": "Swift",
    }
    languages = []
    for ext, language in mapping.items():
        if ext in ext_map and language not in languages:
            languages.append(language)
    return languages


def read_json_if_exists(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def detect_frameworks(repo):
    frameworks = []
    package_json = read_json_if_exists(repo / "package.json")
    if package_json:
        deps = {}
        deps.update(package_json.get("dependencies", {}))
        deps.update(package_json.get("devDependencies", {}))
        dep_names = set(deps.keys())
        known = {
            "next": "Next.js",
            "react": "React",
            "vue": "Vue",
            "svelte": "Svelte",
            "vite": "Vite",
            "express": "Express",
            "nestjs": "NestJS",
        }
        for key, label in known.items():
            if key in dep_names and label not in frameworks:
                frameworks.append(label)
    if (repo / "pyproject.toml").exists():
        text = (repo / "pyproject.toml").read_text()
        if "fastapi" in text.lower():
            frameworks.append("FastAPI")
        if "django" in text.lower():
            frameworks.append("Django")
        if "flask" in text.lower():
            frameworks.append("Flask")
    return frameworks


def detect_package_managers(repo):
    package_managers = []
    markers = {
        "package-lock.json": "npm",
        "pnpm-lock.yaml": "pnpm",
        "yarn.lock": "yarn",
        "bun.lockb": "bun",
        "pyproject.toml": "uv/pip",
        "requirements.txt": "pip",
        "go.mod": "go",
        "Cargo.toml": "cargo",
    }
    for marker, label in markers.items():
        if (repo / marker).exists():
            package_managers.append(label)
    return package_managers


def detect_frontend_style_files(files):
    style_files = []
    style_markers = (
        ".css",
        ".scss",
        ".sass",
        ".less",
        "tailwind.config.js",
        "tailwind.config.ts",
        "postcss.config.js",
        "postcss.config.ts",
        "theme.js",
        "theme.ts",
        "tokens.js",
        "tokens.ts",
        "tokens.json",
    )
    path_keywords = (
        "/styles/",
        "/style/",
        "/theme/",
        "/themes/",
        "/tokens/",
        "/components/",
        "/ui/",
        "/app/",
        "/src/",
    )
    for file_path in files:
        lower = file_path.lower()
        if lower.endswith(style_markers) or any(keyword in f"/{lower}" for keyword in path_keywords):
            if lower.endswith((".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".sass", ".less", ".json")):
                style_files.append(file_path)
    return sorted(dict.fromkeys(style_files))[:20]


def list_repo_files(repo):
    ignored = {".git", ".codex", "node_modules", ".next", "dist", "build", "__pycache__"}
    results = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in ignored]
        for filename in files:
            path = Path(root, filename)
            results.append(str(path.relative_to(repo)))
    return sorted(results)


def detect_existing_managed_files(repo):
    managed = []
    for relative_path in list(ROOT_FILES.keys()) + list(DOC_FILES.keys()) + list(FRONTEND_DOC_FILES.keys()):
        path = repo / relative_path
        if path.exists():
            try:
                if is_harness_owned_text(path.read_text()):
                    managed.append(relative_path)
            except UnicodeDecodeError:
                continue
    return managed


def analyze_repo(repo):
    files = list_repo_files(repo)
    languages = detect_languages(files)
    frameworks = detect_frameworks(repo)
    package_managers = detect_package_managers(repo)
    has_frontend = any(name in frameworks for name in ["Next.js", "React", "Vue", "Svelte", "Vite"]) or any(
        file.endswith((".tsx", ".jsx", ".css", ".scss")) for file in files
    )
    frontend_style_files = detect_frontend_style_files(files) if has_frontend else []
    existing_managed = detect_existing_managed_files(repo)
    existing_harness = [
        file for file in ["AGENTS.md", "ARCHITECTURE.md", "docs/PLANS.md", "docs/SECURITY.md"] if (repo / file).exists()
    ]
    missing_exec_plan_state = [
        path
        for path in [
            "docs/exec-plans/active/README.md",
            "docs/exec-plans/active/_template.md",
            "docs/exec-plans/completed/README.md",
        ]
        if not (repo / path).exists()
    ]
    missing_sops = [
        path
        for path in [
            "docs/sops/layered-domain-architecture-setup.md",
            "docs/sops/encode-unseen-knowledge.md",
            "docs/sops/local-observability-feedback-loop.md",
            "docs/sops/chrome-devtools-ui-validation-loop.md",
            "docs/sops/evidence-first-eval-loop.md",
        ]
        if not (repo / path).exists()
    ]
    durable_knowledge_targets = [
        "ARCHITECTURE.md",
        "docs/product-specs/",
        "docs/RELIABILITY.md",
        "docs/SECURITY.md",
        "docs/references/",
    ]
    if has_frontend:
        durable_knowledge_targets.insert(2, "docs/design-docs/")

    inferred_answers = {
        "project_name": repo.name,
        "languages": languages,
        "frameworks": frameworks,
        "package_managers": package_managers,
        "frontend_scope": (
            "A frontend surface likely exists."
            if has_frontend
            else "No obvious frontend surface detected from the repository."
        ),
        "frontend_style_files": frontend_style_files,
    }

    human_confirmations = []
    for question in QUESTION_CATALOG:
        if question["id"] in {"frontend_stack_notes", "design_style_direction"} and not has_frontend:
            continue
        human_confirmations.append(question)

    analysis = {
        "project_name": repo.name,
        "repo_path": str(repo.resolve()),
        "languages": languages,
        "frameworks": frameworks,
        "package_managers": package_managers,
        "has_frontend": has_frontend,
        "frontend_style_files": frontend_style_files,
        "inferred_answers": inferred_answers,
        "existing_harness_files": existing_harness,
        "existing_managed_files": existing_managed,
        "missing_exec_plan_state": missing_exec_plan_state,
        "missing_sops": missing_sops,
        "durable_knowledge_targets": durable_knowledge_targets,
        "human_confirmations": human_confirmations,
        "harness_state": "existing" if existing_harness or existing_managed else "new",
        "recommended_action": "init",
        "notes": [
            "Ask the human only the confirmations that the repository cannot answer safely.",
            "If unmanaged harness files already exist, preserve them unless the human explicitly requests replacement.",
            "Create execution-plan state before expecting agents to keep repository-mutating work synchronized.",
            "Use SOPs to turn recurring architecture, UI, observability, and knowledge-capture work into mechanical loops.",
            "Write durable facts into permanent docs instead of leaving them trapped inside plans or chat history.",
        ],
    }
    return analysis


