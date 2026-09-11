# Global setup (manual, v1)

`setup.sh --global` and `setup.ps1 -Global` are refused in v1: per-tool
global paths vary too much across OS and user dirs for a safe automated
install. Copy files by hand instead.

## Per-tool user/global paths

| Tool | Skills dir | Agents dir |
| --- | --- | --- |
| Claude | `~/.claude/skills/team-orchestrator/` | `~/.claude/agents/` |
| Codex | `~/.agents/skills/team-orchestrator/` | `~/.codex/agents/` |
| Cursor | `~/.cursor/skills/team-orchestrator/` | `~/.cursor/agents/` |
| opencode | `~/.config/opencode/skills/team-orchestrator/` | `~/.config/opencode/agents/` |
| Kiro | `~/.kiro/skills/team-orchestrator/` | `~/.kiro/agents/` |
| CodeBuddy | `~/.codebuddy/skills/team-orchestrator/` | `~/.codebuddy/agents/` |
| Generic agents | `~/.agents/skills/team-orchestrator/` | `~/.agents/agents/` |

Copy `templates/skills/team-orchestrator/SKILL.md` to the skills dir first;
then, if you want generated defaults globally, generate into a temp dir and
copy the `agents/` files over.

## Merge, don't overwrite

Global dirs often hold your other skills and agents. Merge file by file:
create only `team-orchestrator/SKILL.md` and the role files you want, and never
bulk-copy a whole directory over `~/.*`. Back up anything you replace.
