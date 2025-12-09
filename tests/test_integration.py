import json
from pathlib import Path
from pytest_flakiness.flakiness_report import FlakinessReport, FKTest


def generate_json(pytester, str) -> FlakinessReport:
    # 1. Create a dummy test file so pytest has something to run
    pytester.makepyfile(str)

    # 2. Define the output directory name
    output_dir_name = "my_flake_report"

    # 3. Run pytest
    pytester.runpytest_subprocess(
        f"--flakiness-output-dir={output_dir_name}",
        "--flakiness-commit-id=deadbeef",
        f"--flakiness-git-root={Path.cwd()}",
    )

    # 5. Construct the path to the expected report file
    # pytester.path points to the temporary root of this test run
    report_file = pytester.path / output_dir_name / "report.json"

    # 6. Assert the file exists
    assert report_file.exists(), f"Report file not found at {report_file}"
    with open(report_file, "r") as f:
        data = json.load(f)
    return data


def assert_first_test(json: FlakinessReport):
    test = json.get("tests", [])[0]
    assert test
    return test


def assert_last_attempt(test: FKTest):
    attempt = test["attempts"][-1]
    assert attempt
    return attempt


def test_sanity(pytester):
    """
    Test that the flakiness plugin writes report.json to the specified directory.
    """
    json = generate_json(
        pytester,
        """
        def test_dummy_pass():
            assert True
    """,
    )
    assert json["category"] == "pytest"
    assert len(json["environments"]) == 1
    assert len(json.get("tests", [])) == 1
    assert len(json.get("suites", [])) == 0

    test = assert_first_test(json)
    last_attempt = assert_last_attempt(test)
    assert len(test["attempts"]) == 1

    assert last_attempt["status"] == "passed"
    assert last_attempt["expectedStatus"] == "passed"
    assert last_attempt["environmentIdx"] == 0  # Should point to the first env

    # --- 2. Assert Timing Logic ---
    # Timestamps should be non-zero integers (Unix MS)
    assert isinstance(json["startTimestamp"], int)
    assert json["startTimestamp"] > 0
    assert isinstance(json["duration"], int)
    assert json["duration"] >= 0

    # The attempt duration should be recorded
    assert isinstance(last_attempt["duration"], int)
    assert last_attempt["duration"] >= 0

    # --- 3. Assert Location Details ---
    # You checked line/file, checking column ensures the parser is precise
    location = test.get("location")
    assert location is not None
    assert location["file"] == "test_sanity.py"
    assert location["line"] == 1
    assert isinstance(location["column"], int)
    assert location["column"] > 0

    # --- 4. Assert Environment Data ---
    # Verify the plugin captured basic OS info (if your plugin does that)
    env = json["environments"][0]
    assert env["name"]  # Ensure name is not empty string

    # systemData is 'NotRequired' in schema, but good to check if your plugin supports it
    if "systemData" in env:
        sys_data = env["systemData"]
        assert isinstance(sys_data.get("osName"), str)


def test_skip_with_reason(pytester):
    json = generate_json(
        pytester,
        """
        import pytest

        @pytest.mark.skip(reason="no way of currently testing this")
        def test_should_be_skipped():
            assert False
    """,
    )

    test = assert_first_test(json)
    last_attempt = assert_last_attempt(test)
    assert last_attempt["status"] == "skipped"

    annotations = last_attempt.get("annotations", [])
    assert len(annotations) == 1
    assert annotations[0]["type"] == "skip"
    assert (
        annotations[0].get("description", None)
        == "Skipped: no way of currently testing this"
    )


def test_skip_no_reason(pytester):
    json = generate_json(
        pytester,
        """
        import pytest

        @pytest.mark.skip
        def test_should_be_skipped():
            assert False
    """,
    )
    test = assert_first_test(json)
    last_attempt = assert_last_attempt(test)
    assert last_attempt["status"] == "skipped"

    annotations = last_attempt.get("annotations", [])
    assert len(annotations) == 1
    assert annotations[0]["type"] == "skip"
    assert annotations[0].get("description", None) == "Skipped: unconditional skip"


def test_skip_dynamic(pytester):
    json = generate_json(
        pytester,
        """
        import pytest

        def test_should_be_skipped():
            pytest.skip("This test is skipped dynamically")
    """,
    )
    test = assert_first_test(json)
    last_attempt = assert_last_attempt(test)
    assert last_attempt["status"] == "skipped"
    assert last_attempt["expectedStatus"] == "skipped"

    annotations = last_attempt.get("annotations", [])
    assert len(annotations) == 1
    assert annotations[0]["type"] == "skip"
    assert (
        annotations[0].get("description", None)
        == "Skipped: This test is skipped dynamically"
    )


def test_tags(pytester):
    json = generate_json(
        pytester,
        """
        import pytest

        @pytest.mark.smoke
        @pytest.mark.foo
        def test_should_work():
            assert False
    """,
    )
    test = assert_first_test(json)
    last_attempt = assert_last_attempt(test)
    assert last_attempt["status"] == "failed"
    assert last_attempt["expectedStatus"] == "passed"

    tags = test.get("tags", [])
    assert len(tags) == 2
    assert "smoke" in tags
    assert "foo" in tags


def test_xfail(pytester):
    json = generate_json(
        pytester,
        """
        import pytest
        
        @pytest.mark.xfail
        def test_fails():
            assert False
    """,
    )
    test = assert_first_test(json)
    attempt = assert_last_attempt(test)
    assert attempt["expectedStatus"] == "failed"
    assert attempt["status"] == "skipped"


def test_owner(pytester):
    json = generate_json(
        pytester,
        """
        import pytest

        @pytest.mark.owner("johndoe")
        def test_should_work():
            assert True
    """,
    )
    test = assert_first_test(json)
    last_attempt = assert_last_attempt(test)

    tags = test.get("tags", [])
    assert len(tags) == 0

    annotations = last_attempt.get("annotations", [])
    assert len(annotations) == 1
    assert annotations[0]["type"] == "owner"
    assert annotations[0].get("description", None) == "johndoe"


def test_record_property(pytester):
    json = generate_json(
        pytester,
        """
        import pytest

        def test_should_work(record_property):
            record_property("jira", "BUG-123")
    """,
    )
    test = assert_first_test(json)
    last_attempt = assert_last_attempt(test)

    annotations = last_attempt.get("annotations", [])
    assert len(annotations) == 1
    assert annotations[0]["type"] == "jira"
    assert annotations[0].get("description", None) == "BUG-123"


def test_parametrization_unnamed(pytester):
    json = generate_json(
        pytester,
        """
        import pytest
        
        @pytest.mark.parametrize("has_server", [True, False])
        def test_should_work(has_server):
            assert True
    """,
    )
    tests = json.get("tests", [])
    assert len(tests) == 2
    assert tests[0]["title"] == "test_should_work[True]"
    assert tests[1]["title"] == "test_should_work[False]"


def test_parametrization_named(pytester):
    json = generate_json(
        pytester,
        """
        import pytest
        
        @pytest.mark.parametrize("has_server", [True, False], ids=["Without Server", "With Server"])
        def test_should_work(has_server):
            assert True
    """,
    )
    tests = json.get("tests", [])
    assert len(tests) == 2
    assert tests[0]["title"] == "test_should_work[Without Server]"
    assert tests[1]["title"] == "test_should_work[With Server]"
