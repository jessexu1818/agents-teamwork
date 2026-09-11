# Categories

Pick one per run with `--category <name>`. The default is `deep` behavior when
no category fits better.

## quick

Tight single-area fixes with a known location. Favors fast worker and tester
passes; skip explorer and oracle unless the fix spreads.

Example: `$team-orchestrator --category quick Fix the off-by-one in
src/orders/totals.ts; keep the public API unchanged.`

## deep

Standard multi-file path: explore, implement, test, review. Use when the code
path must be mapped before editing or edits likely cross modules.

Example: `$team-orchestrator --category deep Refactor coupon validation under
src/orders into a tested module.`

## ultrabrain

Toughest reasoning: risky architecture or tangled debugging. Adds oracle
counsel before the change and a high-effort reviewer audit after it.

Example: `$team-orchestrator --category ultrabrain Decide between migrating
off the legacy session store vs. sharding it; then implement the safer path.`

## visual

Interface or image/PDF-led work. Adds designer with visual context kept local
to its turn; other roles stay text-only.

Example: `$team-orchestrator --category visual Rebuild the checkout form to
match design/mockup.png; keep validation messages identical.`
