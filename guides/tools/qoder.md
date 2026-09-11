# Qoder

## Output paths

- Skill: `.qoder/skills/team-orchestrator/SKILL.md` (by-convention; verify in
  your Qoder version)
- Roles: `.qoder/agents/<role>.md` (official; `explorer`, `worker`,
  `tester`, `reviewer`, `researcher`, plus any `--extra` of `planner`,
  `oracle`, `designer`)
- Root: `AGENTS.md` at the target root (components `all` only, auto-read by
  Qoder)

## Model field mapping

Role Markdown keeps frontmatter `name:`, `description:`, `model:`
(substituted from preset or `--<role>-model`). The generator adds a `tools:`
line auto-mapped from `denied_tools:`: readonly roles (for example explorer)
get `Read, Grep, Glob, Bash`; write roles (for example worker) get `Read,
Grep, Glob, Bash, Edit, Write`.

## Limits

- Skill path is by-convention: if your Qoder version does not pick up
  `.qoder/skills/`, verify the skills directory in your build, or install
  via `npx skills add -a qoder` as an alternative.
- `AGENTS.md` at the repo root is auto-read; keep it alongside the generated
  roles for cross-tool consistency.
- User-level roles live under `~/.qoder/agents/` (see
  [global-setup](../global-setup.md)). Merge, do not overwrite.
- Invocation flags (`--worker`, `--category`, …) override files per run.

## Verify

```sh
ls <target>/.qoder/skills/team-orchestrator/SKILL.md <target>/.qoder/agents <target>/AGENTS.md
grep '^tools:' <target>/.qoder/agents/explorer.md <target>/.qoder/agents/worker.md
```
