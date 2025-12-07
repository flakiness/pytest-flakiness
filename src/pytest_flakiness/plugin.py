import pytest

from pathlib import Path
from .git import get_git_commit, get_git_root
# Import your types from the sibling file
from .reporter import (
    Reporter
)

@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    """Called when the test session begins."""
    commit_id = get_git_commit()
    git_root = get_git_root()

    if git_root != None and commit_id != None:
        reporter = Reporter(commit_id, Path(git_root), session.config.rootpath)
        session.config.pluginmanager.register(reporter, name="flakiness_reporter")
