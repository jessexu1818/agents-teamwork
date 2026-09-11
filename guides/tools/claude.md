# Claude

## Output paths

- Skill: `.claude/skills/team-orchestrator/SKILL.md`
- Roles: `.claude/agents/<role>.md` (`explorer`, `worker`, `tester`,
  `reviewer`, `researcher`, plus any `--extra` of `planner`, `oracle`,
  `designer`)
- Root: `AGENTS.md` at the target root (components `all` only)

## Model field mapping

Role Markdown keeps its frontmatter; the generator substitutes `model:` with
the preset or `--<role>-model` value. `temperature:`, `sandbox:`, and
`denied_tools:` pass through unchanged.

## Limits

- No config file is generated for Claude; model defaults live in each role
  file and in the SKILL.md placeholders.
- Invocation flags (`--worker`, `--category`, …) override files per run.

## Verify

```sh
ls <target>/.claude/skills/team-orchestrator/SKILL.md <target>/.claude/agents <target>/AGENTS.md
grep '^model:' <target>/.claude/agents/worker.md
```
