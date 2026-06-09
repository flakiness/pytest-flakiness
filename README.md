[![Tests](https://img.shields.io/endpoint?url=https%3A%2F%2Fflakiness.io%2Fapi%2Fbadge%3Finput%3D%257B%2522badgeToken%2522%253A%2522badge-3dbfoCNJLqtm5d4AH1i8XX%2522%257D)](https://flakiness.io/flakiness/pytest-flakiness)

# pytest-flakiness

[](https://www.google.com/search?q=https://badge.fury.io/py/pytest-flakiness)
[](https://www.google.com/search?q=https://pypi.org/project/pytest-flakiness/)
[](https://opensource.org/licenses/MIT)

The official [Flakiness.io](https://flakiness.io) reporter for **pytest**.

> [!TIP]
> * Report demo is available at https://flakiness.io/flakiness/pytest-flakiness
> * Supported features: [features.md](./features.md)

## Installation

Install using **uv** (recommended):

```bash
uv add --dev pytest-flakiness
```

Or via standard pip:

```bash
pip install pytest-flakiness
```

## Usage

Once installed, simply run pytest. The reporter will automatically activate, aggregate test results,
and create Flakiness Report in the `flakiness-report` directory.

```bash
pytest
```

The generated report can be viewed interactively via the [Flakiness CLI Tool](https://flakiness.io/docs/cli):

```bash
flakiness show
```

> [!TIP]
> Make sure to add `flakiness-report` directory to your `.gitignore`
> ```gitignore
> flakiness-report/
> ```


If Flakiness Access Token is passed, then the reporter will upload the report to Flakiness.io.
You will see a confirmation in your terminal summary:

```text
...
PASSED [100%]
==============================
✅ [Flakiness] Report uploaded: https://flakiness.io/your_org/your_proj/run/1
==============================
```

## Uploading Reports to Flakiness.io

### Github Actions

When running in GitHub Actions, the reporter can authenticate using GitHub's OIDC token — no access token needed.

For this to work:
1. The GitHub Actions workflow must have `id-token: write` permission.
2. The `--flakiness-project` option (or `FLAKINESS_PROJECT` env variable) must be set to your Flakiness.io project identifier (`org/project`).
3. The Flakiness.io project must be bound to the GitHub repository that runs the GitHub Actions workflow.

```yaml
permissions:
  id-token: write

steps:
  - name: Run Tests
    run: pytest --flakiness-project="my-org/my-project"
```

You can also use the `FLAKINESS_PROJECT` environment variable instead of the CLI flag:

```yaml
permissions:
  id-token: write

steps:
  - name: Run Tests
    env:
      FLAKINESS_PROJECT: my-org/my-project
    run: pytest
```

### Access Token

Alternatively, you can authenticate using your project's **Access Token**. You can find this in your project settings on [flakiness.io](https://flakiness.io).

Set the Access Token using either an environment variable or command-line flag:

```bash
export FLAKINESS_ACCESS_TOKEN="flakiness-io-..."
pytest --flakiness-access-token="flakiness-io-..."
```

### All Configuration Options

Each option can be set via a command-line flag, an environment variable, or an ini option (see [Ini File Configuration](#ini-file-configuration) below). When the same option is set in more than one place, the highest-priority source wins:

> **CLI flag** > **environment variable** > **ini file** > **built-in default**

| Flag | Environment Variable | Ini Option | Description |
|------|---------------------|-----------|-------------|
| `--flakiness-name` | `FLAKINESS_NAME` | `flakiness_name` | Name for this environment. Defaults to `pytest` |
| `--flakiness-title` | `FLAKINESS_TITLE` | `flakiness_title` | Optional human-readable report title. Typically used to name a CI run, matrix shard, or other execution group |
| `--flakiness-output-dir` | `FLAKINESS_OUTPUT_DIR` | `flakiness_output_dir` | Local directory to save JSON report. Defaults to `flakiness-report` |
| `--flakiness-project` | `FLAKINESS_PROJECT` | `flakiness_project` | Flakiness.io project identifier (e.g. `org/project`). Required for GitHub OIDC authentication |
| `--flakiness-access-token` | `FLAKINESS_ACCESS_TOKEN` | — | Your Flakiness.io access token for upload. Not available as an ini option, since ini files are usually committed to version control |
| `--flakiness-endpoint` | `FLAKINESS_ENDPOINT` | `flakiness_endpoint` | Flakiness.io service endpoint. Defaults to `https://flakiness.io` |
| `--flakiness-disable-upload` | `FLAKINESS_DISABLE_UPLOAD` | `flakiness_disable_upload` | Disable uploading the report to Flakiness.io. The JSON report is still written to the output directory |
| `--flakiness-commit-id` | `FLAKINESS_COMMIT_ID` | `flakiness_commit_id` | Commit ID of the repository under test. Defaults to the current git commit |
| `--flakiness-git-root` | `FLAKINESS_GIT_ROOT` | `flakiness_git_root` | Root directory used to normalize all paths. Defaults to the git repository root |

### Ini File Configuration

Options can also be set in your pytest configuration file, which is handy for values that are stable across a project (such as `flakiness_project`). All of the ini option names above are recognized in any file pytest reads — `pytest.ini`, `tox.ini`, `setup.cfg`, or `pyproject.toml`.

`pytest.ini` (or `tox.ini` / `setup.cfg` under `[pytest]`):

```ini
[pytest]
flakiness_project = my-org/my-project
flakiness_name = pytest
flakiness_disable_upload = false
```

`pyproject.toml` — pytest 9 reads native TOML types from the `[tool.pytest]` table (recommended):

```toml
[tool.pytest]
flakiness_project = "my-org/my-project"
flakiness_name = "pytest"
flakiness_disable_upload = false
```

If you target older pytest, or prefer the string-based ini format, use `[tool.pytest.ini_options]` instead (don't combine both tables — pytest errors if it sees them together):

```toml
[tool.pytest.ini_options]
flakiness_project = "my-org/my-project"
flakiness_name = "pytest"
flakiness_disable_upload = "false"
```

> **Note:** The access token is intentionally **not** available as an ini option — keep secrets out of version-controlled config files and pass `--flakiness-access-token` or `FLAKINESS_ACCESS_TOKEN` instead.

### Custom Environment Data

You can add custom metadata to your test runs using `FK_ENV_*` environment variables. These might be handy
to capture properties that affect system-under-test.

```bash
export FK_ENV_GPU_TYPE="H100"
export FK_ENV_DEPLOYMENT="staging"
```

The `FK_ENV_` prefix is removed and keys are lowercased, e.g. `FK_ENV_DEPLOYMENT` becomes `deployment`, and `FK_ENV_GPU_TYPE` becomses `gpu_type`.

### Local Development

To save reports locally, pass `--flakiness-output-dir`:

```bash
pytest --flakiness-output-dir=./flakiness-reports
```

This will create a `report.json` file and an `attachments/` directory in the specified folder.

## CI/CD Example (GitHub Actions)

Using GitHub OIDC (recommended — no secrets needed):

```yaml
permissions:
  id-token: write

steps:
  - name: Run Tests
    run: pytest --flakiness-project="my-org/my-project"
```

Alternatively, using an access token:

```yaml
- name: Run Tests
  env:
    FLAKINESS_ACCESS_TOKEN: ${{ secrets.FLAKINESS_ACCESS_TOKEN }}
  run: pytest
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, running checks, and publishing new versions.

## License

MIT
