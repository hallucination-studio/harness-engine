# Template Policy

Every generated file starts with a managed marker:

`<!-- harness-engine:managed -->`

Init behavior:

- `init`: create missing files for new repositories; when an existing managed harness is detected, refresh managed files and create missing files while preserving unmanaged files
- `init` also cleans transient runtime state under `docs/generated/`, `docs/exec-plans/active/`, and `docs/exec-plans/completed/`, then recreates managed starter files
- `init` maintains `.gitignore` entries for `.codex/skills/` and `docs/generated/`
- `git-clean` previews or stages removal of already tracked harness runtime files from the git index; it requires `--apply` before running `git rm --cached`

Use `init` as the normal workspace command so creation and reconciliation share one path. Use `--force` only when the human explicitly accepts overwriting.

If a file exists without the managed marker, treat it as user-owned unless the human explicitly asks to replace it.
