import time
import json
import pytest
from _pytest._code.code import ReprFileLocation, ReprTraceback
import platform
import sys

from pathlib import Path
from typing import NewType, cast, Any

# Import your types from the sibling file
from .flakiness_report import (
    CommitId,
    DurationMS,
    UnixTimestampMS,
    ReportError,
    FlakinessReport,
    GitFilePath,
    Number1Based,
    TestStatus,
    RunAttempt,
    Environment,
    Location,
)

# This behaves like a string at runtime, but type checkers treat it as distinct
NormalizedPath = NewType("NormalizedPath", str)


class Reporter:
    def __init__(self, commit_id: str, git_root: Path, pytest_root: Path):
        self.git_root = git_root.resolve()
        self.pytest_root = pytest_root
        self.commit_id = CommitId(commit_id)
        self.start_time = int(time.time() * 1000)
        self.tests = {}

    def parse_test_title(self, nodeid: str):
        """
        Removes the filename from the nodeid.
        Input:  "tests/api/test_users.py::TestLogin::test_success"
        Output: "TestLogin::test_success"

        Input:  "test_simple.py::test_add"
        Output: "test_add"
        """
        parts = nodeid.split("::", 1)
        if len(parts) > 1:
            return parts[1]
        return nodeid  # Fallback (shouldn't happen for valid tests)

    def parse_pytest_error(self, report: pytest.TestReport) -> ReportError | None:
        """
        Extracts rich error data from the pytest report.
        """
        longrepr = report.longrepr

        # 1. No error info (shouldn't happen if report.failed, but safety first)
        if longrepr is None:
            return None

        # 2. String fallback (happens in some collection errors or legacy plugins)
        if isinstance(longrepr, str):
            return {
                "message": longrepr,
            }

        fk_error: ReportError = {
            "message": str(longrepr),
            "stack": str(longrepr),
        }
        longrepr = cast(Any, longrepr)
        if hasattr(longrepr, "reprcrash") and longrepr.reprcrash:
            crash: ReprFileLocation = longrepr.reprcrash
            if hasattr(crash, "message"):
                fk_error["message"] = str(crash.message)
            if hasattr(crash, "path") and crash.path:
                fk_error["location"] = {
                    "file": GitFilePath(str(self.normalize_path(crash.path))),
                    # Safety: lineno might be None in some rare crash objects
                    "line": Number1Based((crash.lineno or 0) + 1),
                    "column": Number1Based(0),
                }

        if hasattr(longrepr, "reprtraceback") and longrepr.reprtraceback:
            traceback: ReprTraceback = longrepr.reprtraceback
            # Get the last entry in the traceback (the actual crash)
            if traceback.reprentries:
                last_entry = traceback.reprentries[-1]
                # 'lines' is a list of strings showing the source code
                if hasattr(last_entry, "lines") and last_entry.lines:
                    fk_error["snippet"] = "\n".join(last_entry.lines)

        return fk_error

    def normalize_path(self, fspath: str) -> NormalizedPath | None:
        """
        Converts a pytest-relative path to a git-root-relative path.
        """
        # 1. Convert string input to Path
        path_obj = Path(fspath)

        # 2. If it's not absolute, anchor it to the pytest root
        if not path_obj.is_absolute():
            path_obj = self.pytest_root / path_obj

        # 3. Try to calculate relative path from Git Root
        try:
            # .resolve() handles symlinks and ".." to ensure accurate math
            full_path = path_obj.resolve()
            relative = full_path.relative_to(self.git_root)
            return NormalizedPath(str(relative))
        except ValueError:
            # Fallback: File is outside the git repo (e.g. site-packages)
            return None

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """
        Called for setup, call, and teardown.
        """
        # Filter out setup/teardown unless they failed
        if report.when != "call" and not (report.when == "setup" and report.failed):
            return

        # 1. Prepare Data
        duration_ms: DurationMS = DurationMS(int(report.duration * 1000))
        start_ts: UnixTimestampMS = UnixTimestampMS(
            int(time.time() * 1000) - duration_ms
        )

        current_status: TestStatus = report.outcome

        # Determine expectation (xfail handling)
        expected_status: TestStatus = "passed"
        if hasattr(report, "wasxfail"):
            expected_status = "failed"
        if report.outcome == "skipped":
            expected_status = "skipped"

        # Location parsing
        # report.location is Tuple[str, int, str] -> (file, line-0, domain)
        fspath, lineno, _ = report.location
        fspath = self.normalize_path(fspath)
        location: Location | None = None

        if fspath is not None and lineno is not None:
            location = {
                "file": GitFilePath(str(fspath)),
                "line": Number1Based(lineno + 1),
                "column": Number1Based(1),
            }

        # 2. Build Attempt
        attempt: RunAttempt = {
            "environmentIdx": 0,
            "expectedStatus": expected_status,
            "status": current_status,
            "startTimestamp": start_ts,
            "duration": duration_ms,
            "errors": [],
        }

        error = self.parse_pytest_error(report)
        if report.failed and error is not None:
            attempt["errors"] = [error]

        nodeid = report.nodeid
        if nodeid not in self.tests:
            self.tests[nodeid] = {
                "title": self.parse_test_title(nodeid),
                "location": location,
                "attempts": [],
                "tags": [],
            }
        self.tests[nodeid]["attempts"].append(attempt)

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        """
        Finalize report and upload.
        """

        # 1. Build Environment
        environment: Environment = {
            "name": "pytest-host",
            "systemData": {
                "osName": platform.system(),
                "osVersion": platform.release(),
                "osArch": platform.machine(),
            },
            "userSuppliedData": {"python_version": sys.version},
        }

        # 2. Build Final Report
        end_time = int(time.time() * 1000)

        # Cast strictly to the FlakinessReport TypedDict
        report_payload: FlakinessReport = {
            "category": "pytest",
            "commitId": self.commit_id,
            "startTimestamp": UnixTimestampMS(self.start_time),
            "duration": DurationMS(end_time - self.start_time),
            "environments": [environment],
            "tests": list(self.tests.values()),
            "suites": [],
        }

        output_dir = Path.cwd() / "flakiness-report"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "report.json"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    report_payload,
                    f,
                    indent=2,
                    default=str,  # Safe fallback: convert any non-serializable objects (like Path) to strings
                )
        except Exception as e:
            print(f"❌ Failed to write report: {e}")
