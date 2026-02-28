# Contributing to pytest-flakiness

This project uses `uv` for dependency management and `pre-commit` for code quality checks.

## Development Setup

### 1. Install Dependencies
Ensure you have [uv](https://github.com/astral-sh/uv) installed, then run:

```bash
uv sync
```

### 2\. Enable Git Hooks

This project uses `ruff` (formatting/linting) and `pyright` (type checking) as pre-commit hooks. You must install the git hooks to ensure checks run automatically before you commit:

```bash
uv run pre-commit install
```

### 3\. (Optional) Run Checks Manually

You can trigger the full suite of checks on all files at any time:

```bash
uv run pre-commit run --all-files
```

### Tests Dashboard

The tests dashboard is available at https://flakiness.io/flakiness/pytest-flakiness

## Publishing a New Version

1. Run `./release patch` (or `minor` / `major`) to bump the version, commit, and tag.
2. Push with tags: `git push --follow-tags`.
3. In GitHub, create a new release for the tag — use "Generate release notes" for the description.
4. The CI job reacts to the published release and publishes the package to PyPI automatically.
