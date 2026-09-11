# Copilot

## Output paths

- Skill: `.github/skills/team-orchestrator/SKILL.md` (official)
- Roles: `.github/agents/<role>.agent.md` (`explorer`, `worker`, `tester`,
  `reviewer`, `researcher`, plus any `--extra` of `planner`, `oracle`,
  `designer`)
- Root: `AGENTS.md` at the target root (components `all` only)

## Model field mapping

Role files use frontmatter `name:`, `description:`, and `model:` (substituted
from preset or `--<role>-model`). `sandbox:` is dropped; Copilot agents do
not take a sandbox field. `temperature:` and `denied_tools:` pass through in
the body where present.

## Limits

- Add `tools:` / `target:` to a role file manually if your Copilot version or
  policy requires an explicit tool allowlist or targeting header; the
  generator leaves them out by default.
- User-level install: `~/.copilot/skills/` for the skill directory and
  `~/.copilot/agents/` for role files (see
  [global-setup](../global-setup.md)). Merge, do not overwrite.
- Invocation flags (`--worker`, `--category`, …) override files per run.

## Verify

```sh
ls <target>/.github/skills/team-orchestrator/SKILL.md <target>/.github/agents <target>/AGENTS.md
grep '^model:' <target>/.github/agents/worker.agent.md
```
