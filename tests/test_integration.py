from pathlib import Path


def test_json_report_is_generated(pytester):
    """
    Test that the flakiness plugin writes report.json to the specified directory.
    """
    # 1. Create a dummy test file so pytest has something to run
    pytester.makepyfile("""
        def test_dummy_pass():
            assert True
    """)

    # 2. Define the output directory name
    output_dir_name = "my_flake_report"

    # 3. Run pytest
    result = pytester.runpytest(
        f"--flakiness-output-dir={output_dir_name}",
        "--flakiness-commit-id=deadbeef",
        f"--flakiness-git-root={Path.cwd()}",
    )
    assert result.ret == 0, "Test run failed"

    # 5. Construct the path to the expected report file
    # pytester.path points to the temporary root of this test run
    report_file = pytester.path / output_dir_name / "report.json"

    # 6. Assert the file exists
    assert report_file.exists(), f"Report file not found at {report_file}"
