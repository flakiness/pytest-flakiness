"""
flakiness_report.py

Python type definitions mirroring the FlakinessReport TypeScript schema.
"""

from typing import TypedDict, List, Dict, Literal, NewType, Union

# Note: For Python < 3.11, install typing_extensions: pip install typing_extensions
from typing import NotRequired

# -----------------------------------------------------------------------------
# Branded Types
# -----------------------------------------------------------------------------
# These behave like strings/ints at runtime but enforce type safety in static analysis.

CommitId = NewType("CommitId", str)
AttachmentId = NewType("AttachmentId", str)
UnixTimestampMS = NewType("UnixTimestampMS", int)
DurationMS = NewType("DurationMS", int)
Number1Based = NewType("Number1Based", int)
GitFilePath = NewType("GitFilePath", str)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

CATEGORY_PLAYWRIGHT = "playwright"
CATEGORY_JUNIT = "junit"
CATEGORY_PERF = "perf"


# -----------------------------------------------------------------------------
# Basic Structures
# -----------------------------------------------------------------------------


class Location(TypedDict):
    """Represents a location in the source code."""

    file: GitFilePath
    line: Number1Based
    column: Number1Based


TestStatus = Literal["passed", "failed", "timedOut", "skipped", "interrupted"]

# -----------------------------------------------------------------------------
# Environment
# -----------------------------------------------------------------------------


class SystemData(TypedDict):
    osName: NotRequired[str]
    osVersion: NotRequired[str]
    osArch: NotRequired[str]


class Environment(TypedDict):
    """
    Represents test environment that was used to execute test.
    """

    # In Playwright, this is the project name
    name: str

    # System data automatically collected by reporter
    systemData: NotRequired[SystemData]

    # User-supplied data (metadata, env vars)
    metadata: NotRequired[Dict[str, Union[str, bool, int, float]]]


# -----------------------------------------------------------------------------
# System Utilization
# -----------------------------------------------------------------------------


class SystemUtilizationSample(TypedDict):
    """Represents a single sample of system resource utilization."""

    dts: DurationMS
    cpuUtilization: float  # 0 to 100
    memoryUtilization: float  # 0 to 100


class SystemUtilization(TypedDict):
    """Represents system resource utilization monitoring data."""

    totalMemoryBytes: int
    startTimestamp: UnixTimestampMS
    samples: List[SystemUtilizationSample]


# -----------------------------------------------------------------------------
# Errors and Attachments
# -----------------------------------------------------------------------------


class ReportError(TypedDict):
    """Information about an error thrown during test execution."""

    location: NotRequired[Location]
    message: NotRequired[str]
    stack: NotRequired[str]
    snippet: NotRequired[str]
    value: NotRequired[str]


class Attachment(TypedDict):
    """Reference to an attachment (screenshot, video, log, etc.)."""

    name: str
    contentType: str
    id: AttachmentId


class Annotation(TypedDict):
    """Metadata annotation attached to a test run (e.g., 'skip', 'slow')."""

    type: str
    description: NotRequired[str]
    location: NotRequired[Location]


# -----------------------------------------------------------------------------
# Test Steps and Execution
# -----------------------------------------------------------------------------


# Helper for STDIOEntry Union
class TextEntry(TypedDict):
    text: str


class BufferEntry(TypedDict):
    buffer: str


STDIOEntry = Union[TextEntry, BufferEntry]


class TestStep(TypedDict):
    """
    Represents a step within a test execution.
    Steps can be nested.
    """

    title: str
    duration: DurationMS
    location: NotRequired[Location]
    snippet: NotRequired[str]
    error: NotRequired[ReportError]

    # Recursive reference needs quotes
    steps: NotRequired[List["TestStep"]]


class RunAttempt(TypedDict):
    """Represents a single execution attempt of a test in a specific environment."""

    environmentIdx: int
    expectedStatus: TestStatus
    status: TestStatus
    startTimestamp: UnixTimestampMS
    duration: DurationMS

    timeout: NotRequired[DurationMS]
    annotations: NotRequired[List[Annotation]]
    errors: NotRequired[List[ReportError]]
    parallelIndex: NotRequired[int]

    steps: NotRequired[List[TestStep]]
    stdout: NotRequired[List[STDIOEntry]]
    stderr: NotRequired[List[STDIOEntry]]
    attachments: NotRequired[List[Attachment]]


# -----------------------------------------------------------------------------
# Tests and Suites
# -----------------------------------------------------------------------------


class FKTest(TypedDict):
    """Represents a single test case."""

    title: str
    location: NotRequired[Location]
    tags: NotRequired[List[str]]
    attempts: List[RunAttempt]


SuiteType = Literal["file", "anonymous suite", "suite"]


class Suite(TypedDict):
    """
    Represents a test suite that can contain other suites and/or tests.
    """

    type: SuiteType
    title: str
    location: NotRequired[Location]

    # Recursive references
    suites: NotRequired[List["Suite"]]
    tests: NotRequired[List[FKTest]]


# -----------------------------------------------------------------------------
# Source Code
# -----------------------------------------------------------------------------


class Source(TypedDict):
    """Represents source code snippets embedded in the report."""

    filePath: GitFilePath
    text: str
    lineOffset: NotRequired[Number1Based]
    contentType: NotRequired[str]


# -----------------------------------------------------------------------------
# Root Report
# -----------------------------------------------------------------------------


class FlakinessReport(TypedDict):
    """The root report object containing all test execution data."""

    flakinessProject: NotRequired[str]

    category: str  # 'playwright' | 'junit' | 'perf' | string

    commitId: CommitId
    relatedCommitIds: NotRequired[List[CommitId]]

    configPath: NotRequired[GitFilePath]
    url: NotRequired[str]

    environments: List[Environment]
    suites: List[Suite]

    tests: NotRequired[List[FKTest]]
    unattributedErrors: NotRequired[List[ReportError]]

    startTimestamp: UnixTimestampMS
    duration: DurationMS

    # Source code snippets referenced by locations in the report
    sources: NotRequired[List[Source]]

    # CPU telemetry
    cpuCount: NotRequired[int]
    cpuAvg: NotRequired[List[tuple[DurationMS, float]]]  # UtilizationTelemetry
    cpuMax: NotRequired[List[tuple[DurationMS, float]]]  # UtilizationTelemetry

    # RAM telemetry
    ram: NotRequired[List[tuple[DurationMS, float]]]  # UtilizationTelemetry
    ramBytes: NotRequired[int]
