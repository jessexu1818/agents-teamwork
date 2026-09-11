# opencode

## Output paths

- Skill: `.opencode/skills/team-orchestrator/SKILL.md`
- Roles: `.opencode/agents/<role>.md` (`explorer`, `worker`, `tester`,
  `reviewer`, `researcher`, plus any `--extra` of `planner`, `oracle`,
  `designer`)
- Root: `AGENTS.md` at the target root (components `all` only)

## Model field mapping

Role Markdown keeps its frontmatter; the generator substitutes `model:` with
the preset or `--<role>-model` value. `temperature:`, `sandbox:`, and
`denied_tools:` pass through unchanged.

## Limits

- No opencode JSON config is generated; model defaults live in each role file
  and in the SKILL.md placeholders.
- Invocation flags (`--worker`, `--category`, …) override files per run.

## Verify

```sh
ls <target>/.opencode/skills/team-orchestrator/SKILL.md <target>/.opencode/agents <target>/AGENTS.md
grep '^model:' <target>/.opencode/agents/worker.md
```
