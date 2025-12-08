from typing import List

import pytest

from pathlib import Path
from .git import get_git_commit, get_git_root

# Import your types from the sibling file
from .reporter import Reporter
from .flakiness_report import Annotation


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    """Called when the test session begins."""
    commit_id = get_git_commit()
    git_root = get_git_root()

    if git_root is not None and commit_id is not None:
        reporter = Reporter(commit_id, Path(git_root), session.config.rootpath)
        session.config.pluginmanager.register(reporter, name="flakiness_reporter")


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
    report.flakiness_injected_markers = annotations
