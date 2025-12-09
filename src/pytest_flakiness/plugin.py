from typing import List

import pytest

from pathlib import Path
from .git import get_git_commit, get_git_root

# Import your types from the sibling file
from .reporter import Reporter
from .flakiness_report import Annotation
import os


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    """Called when the test session begins."""
    commit_id = (
        session.config.getoption("flakiness_commit_id")
        or os.environ.get("FLAKINESS_COMMIT_ID")
        or get_git_commit()
    )
    git_root = (
        session.config.getoption("flakiness_git_root")
        or os.environ.get("FLAKINESS_GIT_ROOT")
        or get_git_root()
    )

    if git_root and commit_id:
        reporter = Reporter(commit_id, Path(git_root), session.config.rootpath)
        session.config.pluginmanager.register(reporter, name="flakiness_reporter")


def pytest_addoption(parser):
    group = parser.getgroup("flakiness")
    group.addoption(
        "--flakiness-output-dir",
        action="store",
        dest="flakiness_output_dir",
        default=None,
        help="Directory to dump the raw JSON report instead of uploading to Flakiness.io",
    )
    group.addoption(
        "--flakiness-commit-id",
        action="store",
        dest="flakiness_commit_id",
        default=None,
        help="Commit Id of the repository under test",
    )
    group.addoption(
        "--flakiness-git-root",
        action="store",
        dest="flakiness_git_root",
        default=None,
        help="The root directory to normalize all paths",
    )
    group.addoption(
        "--flakiness-access-token",
        action="store",
        dest="flakiness_access_token",
        default=None,
        help="The Flakiness Access Token to upload report",
    )
    group.addoption(
        "--flakiness-endpoint",
        action="store",
        dest="flakiness_endpoint",
        default=None,
        help="Flakiness.io service endpoint. Defaults to https://flakiness.io",
    )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    This hook intercepts the report creation.
    We use it to propagate markers from the Item to the Report.
    """
    # 1. Execute the standard logic to create the report
    outcome = yield
    report = outcome.get_result()
    # 2. Extract tags - markers without arguments, and annotations - markers with arguments
    # item.iter_markers() gives us all decorators like @pytest.mark.smoke
    IGNORED_MARKERS = {
        "parametrize",
        "usefixtures",
        "filterwarnings",
        "skip",
        "xfail",
    }
    tags: List[str] = []
    annotations: List[Annotation] = []
    tags: List[str] = []
    markers: List[str] = []
    for marker in item.iter_markers():
        markers.append(marker.name)
        if marker.name in IGNORED_MARKERS:
            continue

        if marker.args:
            annotations.append(
                {"type": marker.name, "description": str(marker.args[0])}
            )
        else:
            tags.append(marker.name)

    # 3. This attribute doesn't exist on TestReport, so we monkey-patch it on.
    report.flakiness_injected_tags = tags
    report.flakiness_injected_annotations = annotations
    report.flakiness_injected_markers = markers
