import os
import subprocess
from pathlib import Path

# Workaround for git's "dubious ownership" error (CVE-2022-24765).
# In CI containers (e.g. GitHub Actions with `container:`), the repo
# is bind-mounted from the host with a different UID. We bypass the
# safe.directory check for our read-only git calls via env vars so we
# never touch the user's global git config.
_GIT_SAFE_ENV = {
    **os.environ,
    "GIT_CONFIG_COUNT": "1",
    "GIT_CONFIG_KEY_0": "safe.directory",
    "GIT_CONFIG_VALUE_0": "*",
}


def _run_git_cmd(args: list[str]) -> str | None:
    """Helper to run a git command and return clean string output."""
    try:
        return (
            subprocess.check_output(
                ["git"] + args, stderr=subprocess.DEVNULL, env=_GIT_SAFE_ENV
            )
            .decode("utf-8")
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_git_commit() -> str | None:
    """Attempts to get the current git commit hash."""
    return _run_git_cmd(["rev-parse", "HEAD"])


def get_git_root() -> Path | None:
    """Attempts to get the absolute path to the git root directory."""
    result = _run_git_cmd(["rev-parse", "--show-toplevel"])
    return None if result is None else Path(result)
