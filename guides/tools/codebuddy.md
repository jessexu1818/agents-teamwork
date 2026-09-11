# CodeBuddy

## Output paths

- Skill: `.codebuddy/skills/team-orchestrator/SKILL.md`
- Roles: `.codebuddy/agents/<role>.md` (`explorer`, `worker`, `tester`,
  `reviewer`, `researcher`, plus any `--extra` of `planner`, `oracle`,
  `designer`)
- Root: `AGENTS.md` at the target root (components `all` only)

## Model field mapping

Role Markdown keeps its frontmatter; the generator substitutes `model:` with
the preset or `--<role>-model` value. `temperature:`, `sandbox:`, and
`denied_tools:` pass through unchanged.

## Limits

- No CodeBuddy config file is generated; model defaults live in each role
  file and in the SKILL.md placeholders.
- Invocation flags (`--worker`, `--category`, …) override files per run.

## Verify

```sh
ls <target>/.codebuddy/skills/team-orchestrator/SKILL.md <target>/.codebuddy/agents <target>/AGENTS.md
grep '^model:' <target>/.codebuddy/agents/worker.md
```
