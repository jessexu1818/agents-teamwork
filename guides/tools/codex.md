# Codex

## Output paths

- Skill: `.agents/skills/team-orchestrator/SKILL.md`
- Roles: `.codex/agents/<role>.toml` (`explorer`, `worker`, `tester`,
  `reviewer`, `researcher`, plus any `--extra` of `planner`, `oracle`,
  `designer`)
- Root config: `.codex/config.toml` (`model` + `default_subagent_model`)
- Root: `AGENTS.md` at the target root (components `all` only)

## Model field mapping

Role Markdown frontmatter converts to TOML: `name`, `description`, `model`
(substituted from preset or `--<role>-model`), `sandbox` to `sandbox_mode`,
`temperature` emitted raw (unquoted number), body to
`developer_instructions`. The `effort:` frontmatter on reviewer maps to the
`{{REVIEWER_EFFORT}}` placeholder (default `low`).

## Limits

- Markdown-only tooling expecting `.codex/agents/*.md` will not see these
  roles; Codex reads the `.toml` form.
- The skill path (`.agents/skills/…`) is shared with the generic `agents`
  tool; installing both for the same target writes the same file.

## Verify

```sh
ls <target>/.agents/skills/team-orchestrator/SKILL.md <target>/.codex/agents <target>/.codex/config.toml
python3 -c "import tomllib; [tomllib.load(open(f,'rb')) for f in __import__('glob').glob('<target>/.codex/agents/*.toml')]; print('toml ok')"
```
