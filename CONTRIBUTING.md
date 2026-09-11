# Contributing

Thanks for your interest in contributing to agents-teamwork.

## Code of Conduct

By participating, you agree to abide by our `CODE_OF_CONDUCT.md`.

## Development setup

Requirements:

- `python3` (>= 3.11)
- `shellcheck` (for shell installer scripts)
- `git`

No build step is required. The project is templates + Markdown skills +
a small Python generator and shell installers.

## How to contribute

1. Fork the repository and create a feature branch.
2. Make your change with tests where applicable.
3. Run checks locally:
   - `python3 -m pytest tests/ -q`
   - `shellcheck setup.sh` (when shell scripts are touched)
4. Open a pull request using the PR template.

## PR process

- Keep PRs focused and small.
- Update docs (`guides/`, `README.md`, `CHANGELOG.md`) when behavior changes.
- A maintainer will review. Address feedback with new commits.

## TDD requirement for `scripts/generate.py`

Changes to `scripts/generate.py` must follow test-driven development:

1. Add or update tests under `tests/` first.
2. Show failing test output, then implement.
3. All tests must pass before requesting review.

## Originality rule

Do not copy prompts verbatim from other projects with incompatible
licenses (in particular oh-my style prompts, which carry SUL-like terms).
Take inspiration from ideas only and write original wording.
Reference inspirations in PR descriptions instead of pasting their text.
