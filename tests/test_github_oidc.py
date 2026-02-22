import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from pathlib import Path

from pytest_flakiness.flakiness_report import FlakinessReport
from pytest_flakiness.github_oidc import GithubOIDC


def generate_json(pytester, code: str, extra_args: list[str] | None = None) -> FlakinessReport:
    pytester.makepyfile(code)
    output_dir_name = "my_flake_report"
    args = [
        f"--flakiness-output-dir={output_dir_name}",
        "--flakiness-commit-id=deadbeef",
        f"--flakiness-git-root={Path.cwd()}",
    ]
    if extra_args:
        args.extend(extra_args)
    pytester.runpytest_subprocess(*args)
    report_file = pytester.path / output_dir_name / "report.json"
    assert report_file.exists(), f"Report file not found at {report_file}"
    with open(report_file, "r") as f:
        data = json.load(f)
    return data


def test_flakiness_project_in_report(pytester):
    """Test that flakinessProject is included in the report when configured."""
    report = generate_json(
        pytester,
        """
        def test_dummy():
            assert True
        """,
        extra_args=["--flakiness-project=myorg/myproject"],
    )
    assert report.get("flakinessProject") == "myorg/myproject"


def test_flakiness_project_absent_when_not_set(pytester):
    """Test that flakinessProject is not in the report when not configured."""
    report = generate_json(
        pytester,
        """
        def test_dummy():
            assert True
        """,
    )
    assert "flakinessProject" not in report


def test_github_oidc_init_from_env_missing(monkeypatch):
    """Test that init_from_env returns None when env vars are missing."""
    monkeypatch.delenv("ACTIONS_ID_TOKEN_REQUEST_URL", raising=False)
    monkeypatch.delenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", raising=False)
    assert GithubOIDC.init_from_env() is None


def test_github_oidc_init_from_env_present(monkeypatch):
    """Test that init_from_env returns an instance when env vars are set."""
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", "https://token.actions.githubusercontent.com/foo")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "test-token-123")
    oidc = GithubOIDC.init_from_env()
    assert oidc is not None
    assert isinstance(oidc, GithubOIDC)


def test_github_oidc_init_from_env_partial(monkeypatch):
    """Test that init_from_env returns None when only one env var is set."""
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", "https://token.actions.githubusercontent.com/foo")
    monkeypatch.delenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", raising=False)
    assert GithubOIDC.init_from_env() is None

    monkeypatch.delenv("ACTIONS_ID_TOKEN_REQUEST_URL", raising=False)
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "test-token-123")
    assert GithubOIDC.init_from_env() is None


class _OIDCHandler(BaseHTTPRequestHandler):
    """Mock HTTP handler that simulates GitHub's OIDC token endpoint."""

    def do_GET(self):
        # Check authorization header
        auth = self.headers.get("Authorization")
        if auth != "bearer test-request-token":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        # Parse audience from query string
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        audience = params.get("audience", [None])[0]

        if audience == "myorg/myproject":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"value": "oidc-jwt-token-for-myorg"}).encode())
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad audience")

    def log_message(self, format, *args):
        pass  # Suppress request logging during tests


def test_github_oidc_fetch_token_success():
    """Test that fetch_token correctly fetches an OIDC token from a mock server."""
    server = HTTPServer(("127.0.0.1", 0), _OIDCHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    try:
        oidc = GithubOIDC(
            request_url=f"http://127.0.0.1:{port}/token",
            request_token="test-request-token",
        )
        token = oidc.fetch_token("myorg/myproject")
        assert token == "oidc-jwt-token-for-myorg"
    finally:
        thread.join(timeout=5)
        server.server_close()


def test_github_oidc_fetch_token_failure():
    """Test that fetch_token raises on HTTP error."""
    server = HTTPServer(("127.0.0.1", 0), _OIDCHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    try:
        oidc = GithubOIDC(
            request_url=f"http://127.0.0.1:{port}/token",
            request_token="wrong-token",
        )
        try:
            oidc.fetch_token("myorg/myproject")
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "401" in str(e)
    finally:
        thread.join(timeout=5)
        server.server_close()


def test_github_oidc_audience_passed_correctly():
    """Test that the audience parameter is correctly passed in the request URL."""
    received_audiences = []

    class AudienceCapture(BaseHTTPRequestHandler):
        def do_GET(self):
            from urllib.parse import urlparse, parse_qs

            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            received_audiences.append(params.get("audience", [None])[0])
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"value": "token"}).encode())

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), AudienceCapture)
    port = server.server_address[1]
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    try:
        oidc = GithubOIDC(
            request_url=f"http://127.0.0.1:{port}/token",
            request_token="test-request-token",
        )
        oidc.fetch_token("myorg/my-special-project")
        assert received_audiences == ["myorg/my-special-project"]
    finally:
        thread.join(timeout=5)
        server.server_close()
