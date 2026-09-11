# Windsurf

## Output paths

- Skill: `.windsurf/skills/team-orchestrator/SKILL.md` (official)
- Roles: `.windsurf/rules/<role>.md` (`explorer`, `worker`, `tester`,
  `reviewer`, `researcher`, plus any `--extra` of `planner`, `oracle`,
  `designer`)
- Root: `AGENTS.md` at the target root (components `all` only)

## Model field mapping

Role files become rules with frontmatter `trigger: model_decision` plus
`description:` carried over from the role template. The generator does not
emit a `model:` field for Windsurf rules; model selection stays in the
invocation flags and SKILL.md placeholders.

## Limits

- Mapping choice: `trigger: model_decision` means rules are evaluated per
  description at run time rather than pinned as agents. Keep each role
  description specific so the model routes to the right rule.
- Windsurf also auto-discovers `.agents/skills/`; the generated
  `.windsurf/skills/` copy is the explicit official path, the
  `.agents/skills/` overlap is a fallback, not a replacement.
- Global rules are managed via the Windsurf Settings UI; see
  [global-setup](../global-setup.md). Global skills live under
  `~/.windsurf/skills/`.
- Invocation flags (`--worker`, `--category`, …) override files per run.

## Verify

```sh
ls <target>/.windsurf/skills/team-orchestrator/SKILL.md <target>/.windsurf/rules <target>/AGENTS.md
grep '^trigger: model_decision' <target>/.windsurf/rules/explorer.md
```
