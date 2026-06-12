# Template Policy

Every generated file starts with a managed marker:

`<!-- harness-engine:managed -->`

Init behavior:

- `init`: create missing files for new repositories; when an existing managed harness is detected, refresh managed files and create missing files while preserving unmanaged files
- `clean` removes transient runtime state under `docs/generated/`
- `clean` maintains `.gitignore` entries for `.codex/skills/` and `docs/generated/`
- `clean` previews or stages removal of already tracked local skill installs and generated evidence from the git index; it requires `--apply` before running `git rm --cached`
- execution plans, JSON sidecars, and `docs/exec-plans/workstreams.md` are durable project state and must not be cleaned, ignored, or untracked by default

Use `init` as the normal workspace command so creation and reconciliation share one path. Use `--force` only when the human explicitly accepts overwriting.

If a file exists without the managed marker, treat it as user-owned unless the human explicitly asks to replace it.
