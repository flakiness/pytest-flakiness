from typing import List

import pytest

# Import your types from the sibling file
from .reporter import Reporter
from .flakiness_report import Annotation
from .options import add_options, resolve_config


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    """Called when the test session begins."""
    # Resolve the full configuration once, up front, so it stays stable for the
    # whole session (in particular, before any test can mutate FLAKINESS_* env
    # variables). The Reporter reads from this snapshot at session finish.
    config = resolve_config(session.config)

    if config.git_root and config.commit_id:
        reporter = Reporter(config, session.config.rootpath)
        session.config.pluginmanager.register(reporter, name="flakiness_reporter")


def pytest_addoption(parser):
    add_options(parser)


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
