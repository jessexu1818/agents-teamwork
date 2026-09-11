# Generic agents

Covers any tool that reads `.agents/` directly (no vendor-specific format).

## Output paths

- Skill: `.agents/skills/team-orchestrator/SKILL.md`
- Roles: `.agents/agents/<role>.md` (`explorer`, `worker`, `tester`,
  `reviewer`, `researcher`, plus any `--extra` of `planner`, `oracle`,
  `designer`)
- Root: `AGENTS.md` at the target root (components `all` only)

## Model field mapping

Role Markdown keeps its frontmatter; the generator substitutes `model:` with
the preset or `--<role>-model` value. `temperature:`, `sandbox:`, and
`denied_tools:` pass through unchanged.

## Limits

- The skill path (`.agents/skills/…`) is shared with Codex; installing both
  for the same target writes the same file.
- Invocation flags (`--worker`, `--category`, …) override files per run.

## Verify

```sh
ls <target>/.agents/skills/team-orchestrator/SKILL.md <target>/.agents/agents <target>/AGENTS.md
grep '^model:' <target>/.agents/agents/worker.md
```
