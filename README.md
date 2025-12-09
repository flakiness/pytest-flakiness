# pytest-flakiness

[](https://www.google.com/search?q=https://badge.fury.io/py/pytest-flakiness)
[](https://www.google.com/search?q=https://pypi.org/project/pytest-flakiness/)
[](https://opensource.org/licenses/MIT)

The official [Flakiness.io](https://flakiness.io) reporter for **pytest**.
This reporter is used to upload its own tests, see https://flakiness.io/flakiness/pytest-flakiness

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

### Authentication

Set the API key using either an environment variable or command-line flag:

**Environment variable (recommended for CI/CD):**
```bash
export FLAKINESS_ACCESS_TOKEN="flakiness-io-..."
```

**Command-line flag:**
```bash
pytest --flakiness-access-token="flakiness-io-..."
```

### All Configuration Options

All options can be set via environment variables or command-line flags:

| Flag | Environment Variable | Default | Description |
|------|---------------------|---------|-------------|
| `--flakiness-output-dir` | `FLAKINESS_OUTPUT_DIR` | - | Local directory to save JSON report |
| `--flakiness-access-token` | `FLAKINESS_ACCESS_TOKEN` | - | Your Flakiness.io API key (required for upload) |
| `--flakiness-endpoint` | `FLAKINESS_ENDPOINT` | `https://flakiness.io` | Flakiness.io service endpoint |

### Custom Environment Data

You can add custom metadata to your test runs using `FK_ENV_*` environment variables. These might be handy
to capture properties that affect system-under-test.

```bash
export FK_ENV_GPU="H100"
export FK_ENV_DEPLOYMENT="staging"
```

The `FK_ENV_` prefix is removed and keys are lowercased (e.g., `FK_ENV_DEPLOYMENT` becomes `deployment`).

## Usage

Once installed, simply run pytest. If the `FLAKINESS_ACCESS_TOKEN` is present, the reporter will automatically activate, aggregate test results, and upload them at the end of the session.

```bash
pytest
```

You should see a confirmation in your terminal summary:

```text
...
PASSED [100%]
==============================
✅ [Flakiness] Report uploaded: https://flakiness.io/your_org/your_proj/run/1
==============================
```

### Local Development

To save reports locally, pass `--flakiness-output-dir`:

```bash
pytest --flakiness-output-dir=./flakiness-reports
```

This will create a `report.json` file and an `attachments/` directory in the specified folder.

## CI/CD Example (GitHub Actions)

To ensure reports are uploaded during your CI runs, map the secret in your workflow:

```yaml
- name: Run Tests
  env:
    FLAKINESS_ACCESS_TOKEN: ${{ secrets.FLAKINESS_ACCESS_TOKEN }}
  run: pytest
```

Or use the command-line flag:

```yaml
- name: Run Tests
  run: pytest --flakiness-access-token="${{ secrets.FLAKINESS_ACCESS_TOKEN }}"
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
