# Antigravity

## Output paths

- Skill: `.agents/skills/team-orchestrator/SKILL.md` (official Antigravity
  default)
- Roles: `.agent/agents/<role>.md` (`explorer`, `worker`, `tester`,
  `reviewer`, `researcher`, plus any `--extra` of `planner`, `oracle`,
  `designer`)
- Root: `AGENTS.md` at the target root (components `all` only)

## Model field mapping

Role Markdown keeps its frontmatter; the generator substitutes `model:` with
the preset or `--<role>-model` value. `temperature:`, `sandbox:`, and
`denied_tools:` pass through unchanged.

## Limits

- The skill path (`.agents/skills/…`) is shared with the generic `agents`
  output and with Codex; installing those tools for the same target writes
  the same file.
- Backward-compat note: older docs reference `.agent/skills/`; the generator
  uses `.agents/skills/` as the canonical Antigravity default.
- Global install: copy `SKILL.md` to `~/.gemini/antigravity/skills/`
  (see [global-setup](../global-setup.md)). Role files stay per-repo under
  `.agent/agents/`.
- Invocation flags (`--worker`, `--category`, …) override files per run.

See https://antigravity.google/docs/skills for the official Skills format.

## Verify

```sh
ls <target>/.agents/skills/team-orchestrator/SKILL.md <target>/.agent/agents <target>/AGENTS.md
grep '^model:' <target>/.agent/agents/worker.md
```
