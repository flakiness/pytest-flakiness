from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import patch

from pytest_flakiness.reporter import Reporter


def test_normalize_path_uses_forward_slashes(tmp_path):
    """GitFilePath should always use forward slashes, even on Windows."""
    # Create a nested directory structure to get a path with separators
    nested = tmp_path / "subdir" / "pkg"
    nested.mkdir(parents=True)
    test_file = nested / "test_example.py"
    test_file.write_text("# test")

    reporter = Reporter(
        commit_id="deadbeef",
        git_root=tmp_path,
        pytest_root=tmp_path,
    )

    result = reporter.normalize_path(str(test_file))
    assert result is not None
    assert "\\" not in result, f"Expected forward slashes only, got: {result}"
    assert result == "subdir/pkg/test_example.py"



def test_as_location_uses_forward_slashes(tmp_path):
    """as_location should produce GitFilePath with forward slashes."""
    nested = tmp_path / "mypackage"
    nested.mkdir()
    test_file = nested / "test_bar.py"
    test_file.write_text("# test")

    reporter = Reporter(
        commit_id="deadbeef",
        git_root=tmp_path,
        pytest_root=tmp_path,
    )

    location = reporter.as_location(str(test_file), 10)
    assert location is not None
    assert "\\" not in location["file"], (
        f"Expected forward slashes only, got: {location['file']}"
    )
    assert location["file"] == "mypackage/test_bar.py"
