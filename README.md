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
export FLAKINESS_API_KEY="fk_live_..."
```

## Usage

Once installed, simply run pytest. If the `FLAKINESS_API_KEY` is present, the reporter will automatically activate, aggregate test results, and upload them at the end of the session.

```bash
uv run pytest
```

You should see a confirmation in your terminal summary:

```text
...
PASSED [100%]
============================== 
✅ Flakiness.io report uploaded successfully:
https://app.flakiness.io/report/12345
==============================
```

## CI/CD Example (GitHub Actions)

To ensure reports are uploaded during your CI runs, map the secret in your workflow:

```yaml
- name: Run Tests
  env:
    FLAKINESS_API_KEY: ${{ secrets.FLAKINESS_API_KEY }}
  run: uv run pytest
```

## License

MIT
