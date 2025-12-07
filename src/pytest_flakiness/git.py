import subprocess
from pathlib import Path


def _run_git_cmd(args: list[str]) -> str | None:
    """Helper to run a git command and return clean string output."""
    try:
        return (
            subprocess.check_output(["git"] + args, stderr=subprocess.DEVNULL)
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
