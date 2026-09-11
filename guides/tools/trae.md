# Trae

## Output paths

- Skill: `.trae/skills/team-orchestrator/SKILL.md` (official)
- Roles: `.trae/rules/<role>.md` (`explorer`, `worker`, `tester`,
  `reviewer`, `researcher`, plus any `--extra` of `planner`, `oracle`,
  `designer`)
- Root: `AGENTS.md` at the target root (components `all` only)

## Model field mapping

Role Markdown keeps its frontmatter; the generator substitutes `model:` with
the preset or `--<role>-model` value. `temperature:`, `sandbox:`, and
`denied_tools:` pass through unchanged.

## Limits

- Roles under `.trae/rules/` are an optional reference; skills-first is
  recommended (skills-only install is sufficient for the root to play every
  role contract inline).
- Global install: `~/.trae/skills/` for skills,
  `~/.trae/user_rules/` for shared rules (see
  [global-setup](../global-setup.md)). Merge, do not overwrite.
- `AGENTS.md` is shared across tools; the same root file written for Trae
  applies to the other supported tools in the same target.
- Invocation flags (`--worker`, `--category`, …) override files per run.

## Verify

```sh
ls <target>/.trae/skills/team-orchestrator/SKILL.md <target>/.trae/rules <target>/AGENTS.md
grep '^model:' <target>/.trae/rules/worker.md
```
