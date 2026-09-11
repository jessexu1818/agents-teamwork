# Planning flow

The planner is optional (install with `--extra planner`). It interviews fuzzy
goals into an agreed document, then stops. Execution starts only on explicit
approval.

## Interview

```text
$team-orchestrator Use the planner to scope multi-currency checkout. Interview me first.
```

The planner asks about scope, defaults, constraints, and acceptance signals,
one round at a time, and never edits product code.

## Freeze

The agreed plan lands at `.plans/<topic>.md` (e.g. `.plans/checkout.md`).
Review it in full before approving; the freeze is the contract later workers
build against.

## Execute

```text
$team-orchestrator --category deep Execute .plans/checkout.md. Keep file ownership per the plan.
```

Execution follows the default coding chain: explorers map, the root freezes
direction and ownership, workers build, tester validates, reviewer audits,
then repair and re-verify.
