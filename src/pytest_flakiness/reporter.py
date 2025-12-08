import time
import json
import pytest
from _pytest._code.code import ReprFileLocation, ReprTraceback
import platform
import sys
import shutil
import mimetypes
import hashlib

from pathlib import Path
from typing import NewType, cast, Any, TypedDict, List

# Import your types from the sibling file
from .flakiness_report import (
    Annotation,
    CommitId,
    AttachmentId,
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


class FileAttachment(TypedDict):
    """Reference to a file attachment"""

    contentType: str
    id: AttachmentId
    path: Path


# This behaves like a string at runtime, but type checkers treat it as distinct
NormalizedPath = NewType("NormalizedPath", str)


def _calculate_file_hash(path: Path) -> str:
    """
    Calculates the MD5 hash of a file efficiently.
    """
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        # Read in 64kb chunks to be memory efficient
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class Reporter:
    def __init__(self, commit_id: str, git_root: Path, pytest_root: Path):
        self.git_root = git_root.resolve()
        self.pytest_root = pytest_root
        self.commit_id = CommitId(commit_id)
        self.start_time = int(time.time() * 1000)
        self.file_attachments: dict[str, FileAttachment] = {}
        self.tests = {}

    def parse_user_properties(
        self, report: pytest.TestReport
    ) -> tuple[list[Annotation], list[FileAttachment]]:
        """
        Splits generic pytest properties into (Annotations, Attachments).
        """
        annotations: list[Annotation] = []
        attachments: list[FileAttachment] = []

        for key, value in report.user_properties:
            # We only care about strings for paths.
            # (record_property can technically take numbers/objects)
            if not isinstance(value, str):
                continue

            is_likely_attachment = key.endswith(
                ("_path", "_file", "_img", "_screenshot", "_video")
            ) or key.startswith("attachment_")

            # We use try/except because 'value' might be "invalid\path" chars
            try:
                path_obj = Path(value)
                # Heuristic: It must exist, be a file, and be absolute
                # (or relative to cwd, which Path handles)
                if path_obj.is_file() and is_likely_attachment:
                    # mimetypes.guess_type returns (type, encoding)
                    mime_type, _ = mimetypes.guess_type(path_obj)
                    # Fallback if unknown
                    if mime_type is None:
                        mime_type = "application/octet-stream"

                    file_hash = _calculate_file_hash(path_obj)
                    attachments.append(
                        {
                            "contentType": mime_type,
                            "id": AttachmentId(file_hash),
                            "path": path_obj,
                        }
                    )
                    continue
            except (OSError, ValueError):
                pass  # Not a path, treat as normal string

            # Fallback: It's just an annotation
            annotations.append(
                {
                    "type": key,
                    "description": value,
                }
            )

        return annotations, attachments

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

    def as_location(self, raw_path: str, lineno: int | None) -> Location | None:
        fspath = self.normalize_path(raw_path)

        if fspath is not None and lineno is not None:
            return {
                "file": GitFilePath(str(fspath)),
                "line": Number1Based(lineno + 1),
                "column": Number1Based(1),
            }
        return None

    def extract_test_tags(self, report: pytest.TestReport) -> List[str] | None:
        markers = getattr(report, "flakiness_injected_markers", [])

        IGNORED_MARKERS = {
            "parametrize",
            "usefixtures",
            "filterwarnings",
            "skip",
            "xfail",
        }
        tags: List[str] = []
        for marker in markers:
            if marker not in IGNORED_MARKERS:
                tags.append(marker)
        return tags or None

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

        # 1. Always capture the actual test execution ('call')
        is_call = report.when == "call"

        # 2. Capture Setup ONLY if it failed or if the test was skipped there
        is_relevant_setup = report.when == "setup" and (report.failed or report.skipped)

        # 3. Drop everything else (successful setups, teardowns)

        if not is_call and not is_relevant_setup:
            return

        # 1. Prepare Data
        duration_ms: DurationMS = DurationMS(int(report.duration * 1000))
        start_ts: UnixTimestampMS = UnixTimestampMS(
            int(time.time() * 1000) - duration_ms
        )

        markers = getattr(report, "flakiness_injected_markers", [])
        current_status: TestStatus = report.outcome
        expected_status: TestStatus = "passed"
        if "xfail" in markers:
            expected_status = "failed"
        elif "skip" in markers:
            expected_status = "skipped"

        # Parse user properties
        annotations, file_attachments = self.parse_user_properties(report)
        for file_attachment in file_attachments:
            self.file_attachments[file_attachment["id"]] = file_attachment

        # Add "Skip" reason as an annotation
        if report.outcome == "skipped":
            # Pytest stores the skip reason in longrepr usually as a tuple or string
            annotation: Annotation = {
                "type": "skip",
            }
            if isinstance(report.longrepr, tuple):
                # (file, line, reason)
                annotation["description"] = report.longrepr[2]
                location = self.as_location(report.longrepr[0], report.longrepr[1])
                if location is not None:
                    annotation["location"] = location
            elif isinstance(report.longrepr, str):
                annotation["description"] = report.longrepr
            annotations.append(annotation)

        # 2. Build Attempt
        attempt: RunAttempt = {
            "environmentIdx": 0,
            "expectedStatus": expected_status,
            "status": current_status,
            "startTimestamp": start_ts,
            "duration": duration_ms,
            "errors": [],
            "annotations": annotations,
            "attachments": [
                {
                    # Extract filename from the Path object (e.g., "test_fail.png")
                    "name": fa["path"].name,
                    "contentType": fa["contentType"],
                    "id": fa["id"],
                }
                for fa in file_attachments
            ],
        }

        error = self.parse_pytest_error(report)
        if report.failed and error is not None:
            attempt["errors"] = [error]

        nodeid = report.nodeid
        if nodeid not in self.tests:
            self.tests[nodeid] = {
                "title": self.parse_test_title(nodeid),
                "location": self.as_location(report.location[0], report.location[1]),
                "tags": self.extract_test_tags(report),
                "attempts": [],
            }
        self.tests[nodeid]["attempts"].append(attempt)

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        """
        Finalize report and upload.
        """

        # 1. Build Environment
        environment: Environment = {
            "name": "pytest",
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
        if output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)
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

        attachments_dir = output_dir / "attachments"
        attachments_dir.mkdir(exist_ok=True)
        for attachment_id, attachment_data in self.file_attachments.items():
            source_path = attachment_data["path"]
            # The filename is exactly the ID (as requested)
            destination_path = attachments_dir / attachment_id
            try:
                if source_path.exists():
                    # copy2 preserves timestamps and metadata
                    shutil.copy2(source_path, destination_path)
                else:
                    print(
                        f"⚠️ Warning: Source file for attachment {source_path.name} is missing at {source_path}"
                    )
            except OSError as e:
                print(f"❌ Failed to copy attachment {attachment_id}: {e}")
