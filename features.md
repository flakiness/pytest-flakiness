# Reporter Features — pytest

Status of [Flakiness Report Features](https://github.com/flakiness/flakiness-report/blob/main/features.md) as implemented by this
`pytest-flakiness` plugin.

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 1 | Report metadata | ✅ | `url` auto-detected from GitHub Actions / Azure DevOps / GitLab CI (`CI_JOB_URL`) / Jenkins (`BUILD_URL`). `configPath` N/A (pytest has no single config file concept). `relatedCommitIds` not populated. |
| 2 | Environment metadata | ✅ | `name`, `osName`, `osVersion`, `osArch`, `python_version` |
| 3 | Multiple environments | N/A | pytest has no native concept of multi-project execution akin to Playwright/Vitest. A single `environments[]` entry is emitted |
| 4 | Custom environments (`FK_ENV_*`) | ✅ | Supports `FK_ENV_*` envs. |
| 5 | Test hierarchy / suites | ✅ | Pytest's hierarchy is shallow. |
| 6 | Per-attempt reporting (retries) | N/A | pytest has no native reruns. |
| 7 | Per-attempt timeout | N/A | pytest has no native per-test timeout. |
| 8 | Test steps | N/A | pytest has no native step concept. |
| 9 | Expected status (`expectedStatus`) | ✅ | `@pytest.mark.xfail`, skipped tests |
| 10 | Attachments | ✅ | While pytest has no native attachments, this reporter parses `record_property` values under keys ending `_path`/`_file`/`_img`/`_screenshot`/`_video` or starting with `attachment_` (community standard) |
| 11 | Step-level attachments | N/A | pytest has no native step concept. |
| 12 | Timed StdIO | N/A | pytest exposes stdout and stderr as two separate captured blobs with no per-write timings and no cross-stream ordering. |
| 13 | Annotations | ✅ | The plugin emits `skip` (with reason + location), turns any marker-with-args into a typed annotation (e.g. `@pytest.mark.owner("johndoe")`), and maps `record_property(key, value)` entries to annotations. |
| 14 | Tags | ✅ | Arg-less markers (e.g. `@pytest.mark.smoke`) become tags. |
| 15 | `parallelIndex` | N/A | pytest has no native parallelism. |
| 16 | `FLAKINESS_TITLE` | ✅ | Honored via `--flakiness-title` / `FLAKINESS_TITLE`. |
| 17 | `FLAKINESS_OUTPUT_DIR` | ✅ | Honored via `--flakiness-output-dir` / `FLAKINESS_OUTPUT_DIR`, defaults to `flakiness-report`. |
| 18 | Sources | ❌ | Top-level `sources[]` is never populated. Since there are no steps, this might not be needed at the moment. |
| 19 | Error snippets | ✅ | pytest emits only plain-text excerpts (no ANSI highlighting) |
| 20 | Errors support | ✅ | pytest has no native soft-assertion / multi-error capture. Single errors are captured in full. |
| 21 | Unattributed errors | ❌ | `unattributedErrors` is never populated. Collection / setup errors that aren't tied to a specific test are not surfaced at report level. |
| 22 | Source locations | ✅ | Populated on tests, errors, and skip annotations. pytest's `Mark` objects don't carry source locations, so marker annotations don't have one. |
| 23 | Auto-upload | ✅ | Supports GitHub OIDC, `FLAKINESS_ACCESS_TOKEN`, and `FLAKINESS_DISABLE_UPLOAD` / `--flakiness-disable-upload` to opt-out. |
| 24 | CPU / RAM telemetry | ❌ | System telemetry is not collected. |
