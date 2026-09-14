# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Category routing (`quick|deep|ultrabrain|visual`): invocation-time model
  selection with documented precedence over presets and per-role pins.
- `scripts/verify.py`: static check for generated skill/role outputs
  (paths, model fields, Codex TOML conversion).
- CI verify step: test gate plus verify gate on generated outputs.
- Docs: 5 new tool guides (`antigravity/copilot/windsurf/qoder/trae`) with
  skill/role paths, model-field mapping, limits, and verify commands; global
  paths table and EN/ZH tool matrices updated to 12 tools.
- `--tools` selection candidate set expanded 7->12 (selection flag already
  existed; `--tools all` now covers all 12 targets).

## [0.1.0] - 2026-09-11

### Added

- `team-orchestrator` skill: delegation gate, root responsibilities, spawn
  policy with per-role model override and `--category`
  (`quick|deep|ultrabrain|visual`), delegation contract, completion gate.
- 8 role templates: 5 core (`explorer/worker/tester/reviewer/researcher`,
  `worker` with `quick|deep` modes) + 3 optional
  (`planner/oracle/designer` via `--extra`).
- `scripts/generate.py`: renders 7 tool targets
  (`.claude/.codex/.codebuddy/.kiro/.opencode/.cursor/.agents`),
  Codex TOML conversion + `config.toml`, `--preset pro|plus|custom`,
  `--components all|skills-only`.
- `setup.sh` / `setup.ps1`: parameterized thin wrappers with overwrite
  confirmation and type-conflict guards.
- Skills-only install as the recommended 30-second path (zero scripts).
- Docs: `README.md` (EN) + `README.zh-CN.md`, `guides/` (quickstart,
  model-matrix, categories, planning, global-setup, 7 tool guides).
- Tests: 11 passing (`tests/test_generate.py`, `tests/test_setup_sh.py`).
