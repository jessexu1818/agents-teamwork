# Model matrix

## Presets

| Preset | orchestrator | reviewer | explorer / worker / tester / researcher / planner / oracle / designer | reviewer effort |
| --- | --- | --- | --- | --- |
| pro (default) | gpt-5 | gpt-5 | gpt-5-mini | low |
| plus | gpt-5-mini | gpt-5 | gpt-5-mini | low |
| custom | gpt-5-mini | gpt-5-mini | gpt-5-mini | low |

Set with `--preset pro|plus|custom` on `setup.sh` or `scripts/generate.py`.

## Per-role flags

Any role model can be pinned, plus reviewer effort:

```sh
./setup.sh --target ../my-project --worker-model gpt-5-mini --reviewer-model gpt-5 --reviewer-effort high --yes
python3 scripts/generate.py --target /tmp/demo --tools claude --preset plus --oracle-model gpt-5
```

Available: `--orchestrator-model`, `--explorer-model`, `--worker-model`,
`--tester-model`, `--reviewer-model`, `--researcher-model`,
`--planner-model`, `--oracle-model`, `--designer-model`, `--reviewer-effort`.

## Category routing

Chosen per invocation with `--category quick|deep|ultrabrain|visual`:

- `quick` — fast worker and tester passes for tight fixes.
- `deep` — full explore, implement, test, review chain.
- `ultrabrain` — adds oracle counsel and a high-effort review.
- `visual` — adds designer with isolated image/PDF context.

Definitions and examples: [categories.md](categories.md).

## Precedence

Highest wins:

```text
invocation flags (--orchestrator/--worker/--reviewer/--category/--extra)
  > per-role pins (--<role>-model, --reviewer-effort)
    > category routing (quick/deep/ultrabrain/visual)
      > preset defaults (pro/plus/custom)
```

Per-run invocation flags never edit generated files; generated pins never edit
the skill. The root model stays stable within a session.
