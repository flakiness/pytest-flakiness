# pytest-flakiness

[](https://www.google.com/search?q=https://badge.fury.io/py/pytest-flakiness)
[](https://www.google.com/search?q=https://pypi.org/project/pytest-flakiness/)
[](https://opensource.org/licenses/MIT)

The official [Flakiness.io](https://flakiness.io) reporter for **pytest**.

Automatically detect, track, and resolve flaky tests in your Python test suite. This plugin hooks into your pytest execution and uploads test results directly to your Flakiness.io dashboard.

## Installation

Install using **uv** (recommended):

```bash
uv add --dev pytest-flakiness
```

Or via standard pip:

```bash
pip install pytest-flakiness
```

## Configuration

To upload reports, you need your project's **API Key**. You can find this in your project settings on [flakiness.io](https://flakiness.io).

Set the API key in your environment. This is best for CI/CD systems.

```bash
export FLAKINESS_ACCESS_TOKEN="flakiness-io-..."
```

## Usage

Once installed, simply run pytest. If the `FLAKINESS_ACCESS_TOKEN` is present, the reporter will automatically activate, aggregate test results, and upload them at the end of the session.

```bash
uv run pytest
```

You should see a confirmation in your terminal summary:

```text
...
PASSED [100%]
============================== 
✅ [Flakiness] Report uploaded: https://flakiness.io/your_org/your_proj/run/1
==============================
```

## CI/CD Example (GitHub Actions)

To ensure reports are uploaded during your CI runs, map the secret in your workflow:

```yaml
- name: Run Tests
  env:
    FLAKINESS_ACCESS_TOKEN: ${{ secrets.FLAKINESS_ACCESS_TOKEN }}
  run: uv run pytest
```

## 🛠️ Development Setup

This project uses `uv` for dependency management and `pre-commit` for code quality checks.

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

## License

MIT
