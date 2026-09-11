# AGENTS.md — Team Orchestration
Use the `team-orchestrator` skill when a task spans multiple files, needs parallel exploration, independent verification, external docs, or the user asks for delegation.
The root owns architecture, decomposition, integration, verification, and the final answer; subagents supply bounded evidence and execution only.
Prefer one bounded subagent per workstream with explicit scope, file ownership, and acceptance criteria; run independent work in parallel.
Do not delegate trivial single-file edits, simple questions, or purely conversational replies.
Available roles: explorer, worker (quick|deep), tester, reviewer, researcher (core) + planner, oracle, designer (optional).
Route by category when given: quick for fast bounded work, deep for default thorough work, ultrabrain for hardest reasoning, visual for UI/vision/PDF tasks.
Invocation overrides (`--orchestrator/--worker/--reviewer/--category/--extra`) win over generated defaults; the skill also works skills-only without generated configs.
Never claim delegation without spawning a real subagent; report spawn failures explicitly instead of silently doing the work inline.
The user's explicit instructions always take precedence over this file and the skill.
