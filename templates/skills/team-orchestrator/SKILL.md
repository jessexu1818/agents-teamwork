---
name: team-orchestrator
description: Use when a task spans multiple files, needs parallel exploration, independent testing or review, version-specific external verification, or the user asks for delegation, subagents, or parallel work across IDEs. Does not apply to trivial single-file edits or simple questions.
---

# Team Orchestrator

The user's explicit instructions take precedence over this skill.

## Goal

Keep the root as the architect and integrator. Hand bounded slices to specialist
subagents, then merge, check, and report the combined outcome.

| Role | Focus | Required |
| --- | --- | --- |
| explorer | code mapping, flows, constraints | core |
| worker | scoped implementation (quick / deep) | core |
| tester | reproduction and targeted validation | core |
| reviewer | post-change independent audit | core |
| researcher | external and version-specific facts | core |
| planner | interview-style plan into `.plans/` (optional) | optional |
| oracle | pre-change architecture and debug counsel (optional) | optional |
| designer | UI structure plus image / PDF reading (optional) | optional |

## Delegation gate

Label each substantive request before touching the tree:

- **root-only** — small, local, and gains nothing from separate exploration,
  implementation, testing, research, or review.
- **delegated** — anything that benefits from an independent context.

Delegate when any holds:

- edits likely cross files, modules, or services
- two or more separable workstreams exist
- the code path must be mapped before editing
- building and checking deserve separate eyes
- a failure trail crosses component edges
- several areas need inspection at once
- outside docs or version behavior decide correctness
- a fresh post-change audit adds real safety
- the user requests delegation, parallelism, or subagents

A delegated task MUST produce at least one genuine subagent call before the root
does the delegated portion itself. Describing, simulating, or reasoning about
delegation does not count. When spawning is unavailable or errors, say so openly
and never quietly absorb the work while claiming it was delegated.

## Root responsibilities

The root keeps:

1. clarifying the real user goal
2. settling architecture and direction
3. slicing work into bounded pieces
4. marking what may run concurrently
5. launching the right subagents
6. issuing each one a tight contract
7. reconciling clashing reports
8. merging the returned pieces
9. inspecting the final diff
10. arranging closing verification
11. delivering the summary to the user

Subagents return evidence and finished slices. Direction stays with the root.

## Spawn policy

Defaults come from generated configs; per-run flags win over those files.

| Role | Model placeholder | Default posture |
| --- | --- | --- |
| explorer | `{{EXPLORER_MODEL}}` | cheap, read-only mapping |
| worker | `{{WORKER_MODEL}}` | quick for tight fixes, deep for broad edits |
| tester | `{{TESTER_MODEL}}` | minimal proving command |
| reviewer | `{{REVIEWER_MODEL}}` at `{{REVIEWER_EFFORT}}` | independent audit |
| researcher | `{{RESEARCHER_MODEL}}` | primary sources first |
| planner | `{{PLANNER_MODEL}}` | interview, then `.plans/<topic>.md` |
| oracle | `{{ORACLE_MODEL}}` | pre-change counsel, read-only |
| designer | `{{DESIGNER_MODEL}}` | UI plus isolated visual context |

Category routing (via `--category`):

- **quick** — tight single-area fixes; favor fast worker and tester passes.
- **deep** — standard multi-file path; full explore, implement, test, review chain.
- **ultrabrain** — toughest reasoning; add oracle counsel and a high-effort review.
- **visual** — interface or image / PDF led; add designer with isolated context.

Invocation overrides:

- `--orchestrator <model>` — root model for this run only.
- `--worker <model>` — worker model for this run only.
- `--reviewer <model>` — reviewer model for this run only.
- `--category <quick|deep|ultrabrain|visual>` — force the routing above.
- `--extra <text>` — free-form constraint appended to every delegation contract.

For each delegation: name the task clearly, pin the intended model, attach the
contract below, keep the returned handle, and wait where synthesis depends on it.
Keep the root model stable within a session; escalation choices belong to the root.

## Delegation contract

Give every subagent:

- **Objective** — the single concrete outcome.
- **Scope** — files, subsystem, or question; state file ownership for edits.
- **Context** — only the background needed to succeed.
- **Constraints** — what must stay untouched.
- **Deliverable** — what to return or change.
- **Acceptance** — how the parent will judge success.

Narrow beats broad. Bad: `Fix checkout.` Good: `Trace coupon validation on POST
/orders; return files, validation order, and covering tests; change nothing.`
Tell explorers and reviewers to report, not edit. Tell workers exactly which
files they own.

## Role selection

- **explorer** — map unfamiliar code, follow a path end to end, find owners, tests,
  config, and safe edit points.
- **worker** — apply a scoped fix, feature slice, or refactor inside owned files;
  pick quick for tight fixes, deep for sprawling ones.
- **tester** — reproduce a symptom, run the smallest proving suite, add tests only
  when asked or plainly required.
- **reviewer** — audit a finished diff for defects, regressions, security gaps,
  data hazards, concurrency faults, contract breaks, and missing high-value tests.
- **researcher** — confirm outside behavior: API shape, framework semantics,
  version deltas, and compatibility notes from authoritative sources.
- **planner (optional)** — interview fuzzy goals into an agreed `.plans/<topic>.md`;
  no product edits.
- **oracle (optional)** — second opinion before risky architecture or tangled
  debugging decisions; advisory and read-only.
- **designer (optional)** — UI breakdowns plus screenshot, mockup, or PDF reading
  with visual context kept local to its turn.

Engage only roles that move the task forward, but never zero once delegation
applies.

## Category routing

Static routing selects the member set before any spawn. An explicit
`--category` flag always wins; otherwise the root matches trigger phrases.

| Category | Trigger phrases | Default members | Fallback chain |
| --- | --- | --- | --- |
| quick | tight fix, single area, clear check | worker plus tester on light settings | deep chain, then preset default |
| deep | multi-file edit, fuzzy scope, standard path | explorer, worker, tester, reviewer | preset default, then session default |
| ultrabrain | hardest reasoning, high risk, tangled cause | deep chain plus oracle counsel and raised review effort | deep chain, then preset default |
| visual | interface change, screenshot, mockup, PDF brief | deep chain plus designer with local visual context | deep chain, then preset default |

When a listed member cannot run, step down its fallback chain instead of
quietly absorbing the slice at root. Keep visual context inside the designer
turn and return only compact findings.

## Resolution priority

When model or effort settings disagree, earlier entries win over later ones:

1. skill-invocation param passed for this run
2. role file pin recorded in the generated config
3. category default implied by the routing table above
4. preset default baked at generation time
5. session default from the surrounding tool session

Reasoning convention: every role file carries a `reasoning` frontmatter key.
Empty means use the model default. Reviewer and oracle pin `low`; all other
roles leave it empty. Generation copies a non-empty value into
`model_reasoning_effort` where the target format supports it.

## Tool restrictions

Read-only roles report findings and never alter files. Scoped writers edit
only files the root explicitly assigned to them.

| Role | May write | May edit | Scope note |
| --- | --- | --- | --- |
| explorer | no | no | mapping only, no file changes |
| reviewer | no | no | audit only, no fixes applied |
| researcher | no | no | outside facts only, no code changes |
| oracle | no | no | advisory only, no file changes |
| designer | no | no | spec and visual notes only, no implementation |
| worker | yes | yes | owned files only, as delegated |
| tester | yes | yes | test files only when asked or required |
| planner | yes | yes | plan artifact under `.plans/` only |

Deny matrix summary: explorer, reviewer, researcher, oracle, and designer
MUST NOT write or edit. Worker, tester, and planner may write and edit strictly
within their assigned scope and must stop and escalate on overlap.

## Parallelism

Launch separable work together; sequence only genuine dependencies.

Together: backend mapping, frontend mapping, and outside-doc lookup. In order:
map, decide, build, validate, audit, repair, re-verify.

One writer per file or subsystem. Do not assign overlapping edits without the
root mediating ownership.

## Workflows

### Default coding (11 steps)

1. run planner interviews when the goal is fuzzy (optional; skip if scope is clear)
2. launch explorers where repository knowledge is thin
3. collect and reconcile their maps
4. consult oracle on risky architecture or tangled causes (optional)
5. root freezes direction and file ownership
6. launch workers with quick or deep mode per category
7. collect implementations
8. launch tester for focused validation
9. launch reviewer, raising effort for ultrabrain or high-risk diffs
10. repair material findings and re-verify
11. present what changed, evidence, and residual risks

### Debugging

Map each suspect area in parallel, reproduce first, gather traces before naming a
cause, let the root pick the culprit, fix through one bounded worker, re-prove
with tester, and audit high-risk repairs. Avoid parallel competing fixes unless
the root deliberately wants alternatives.

### Research

Hand the researcher one crisp question, demand authoritative references with
version bounds, and let the root translate findings into build choices. Keep
unverified outside claims out of implementation.

### Planning

Use planner interviews to pin scope, defaults, and acceptance signals, freeze the
document under `.plans/`, then exit planning without building. Execution starts
only on explicit approval.

## Cost discipline

Reserve heavy reasoning for direction, audits, and ultrabrain calls. Routine
mapping, building, and checking stay on lighter models. Keep root context to
decisions, digests, diffs, test outcomes, audit notes, and open risks. Subagents
return conclusions with paths, symbols, commands, outcomes, and blockers — not
raw dumps.

## Escalation

Send the decision back to the root when a subagent meets an architecture call, a
contract or schema break, a fresh dependency, a security-sensitive shape, vague
requirements with divergent outcomes, drift outside its slice, overlap with
another owner, or a blocker needing wider judgment. Model upgrades are a root
call; subagents do not promote themselves.

## Failure handling

On a subagent failure: read the cause, then retry narrowed, reassign, or absorb
the slice at root — and record which path was taken. Never ignore the miss or
report the slice as done. On repeated worker failure the root may proceed
directly while noting the fallback.

## Completion gate

Before the final message, confirm each launched agent finished or openly failed,
their material notes were merged, conflicts were settled, owed checks ran, and
nothing required is still in flight. Never claim delegation that never spawned.

## Final verification

Inspect the closing diff, confirm the requested behavior exists, weigh audit
notes, run or cite the highest-value tests, and name anything left unvalidated.
For code tasks favor syntax or type passes, focused unit runs, relevant
integration or build signals, the original repro path, and a scan for stray edits.

## User-facing behavior

Lead with what changed, the proof, notable discoveries, and remaining risks.
Mention contributing agents briefly. Expand into per-agent names, models, tasks,
and status only when asked. Never credit a model that did not actually run.

## Skills-only note

This file alone is enough. Without generated role configs or installer output,
the root can still play each role's contract inline: issue the same objective,
scope, context, constraints, deliverable, and acceptance text to a generic
subagent, apply the same category routing and `--extra` constraints, and enforce
identical completion and verification gates. Generated files only prefill model
and sandbox defaults.
