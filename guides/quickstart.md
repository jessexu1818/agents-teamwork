# Quickstart (5 minutes)

Start skills-only. Add generated roles only when you want model defaults.

## 1. Skills-only (30 seconds, no scripts)

```sh
cp templates/skills/team-orchestrator/SKILL.md <repo>/.agents/skills/team-orchestrator/SKILL.md
```

For other tools, copy the same file to the matching folder: `.claude/skills/...`,
`.cursor/skills/...`, `.opencode/skills/...`, `.kiro/skills/...`,
`.codebuddy/skills/...` (Codex and generic agents both use `.agents/skills/...`).

## 2. Full install (2 minutes)

```sh
./setup.sh --target ../my-project --tools all --components all --yes
```

Add optional roles with `--extra planner,oracle,designer` (any subset).
Windows: `setup.ps1` mirrors these flags.

## 3. Verify

```sh
ls ../my-project/.agents/skills/team-orchestrator/SKILL.md
ls ../my-project/.claude/agents ../my-project/.codex/agents
ls ../my-project/AGENTS.md
```

Skills-only installs: expect only `SKILL.md` files, no `agents/` dirs, no
`AGENTS.md`, no `.codex/config.toml`.

## 4. First prompt

```text
$team-orchestrator --category deep Trace how login sessions expire under src/auth; report files, flow, and safe edit points. Change nothing.
```

If the task is a tight single-area fix, use `--category quick`. For UI or
image/PDF work, use `--category visual`. For the hardest reasoning, use
`--category ultrabrain`.
