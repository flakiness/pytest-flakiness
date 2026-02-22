import os
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class GithubOIDC:
    """Handles GitHub Actions OIDC token fetching for authentication with flakiness.io."""

    def __init__(self, request_url: str, request_token: str):
        self._request_url = request_url
        self._request_token = request_token

    @staticmethod
    def init_from_env() -> "GithubOIDC | None":
        """Creates a GithubOIDC instance from GitHub Actions environment variables.

        Returns None if not running in GitHub Actions or if required env vars are missing.
        """
        request_url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
        request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
        if request_url and request_token:
            return GithubOIDC(request_url, request_token)
        return None

    def fetch_token(self, audience: str) -> str:
        """Fetches a GitHub OIDC token with the given audience.

        Args:
            audience: The audience claim for the OIDC token (flakinessProject value).

        Returns:
            The OIDC token string.

        Raises:
            RuntimeError: If the token request fails or returns an empty token.
        """
        parsed = urlparse(self._request_url)
        qs = parse_qs(parsed.query)
        qs["audience"] = [audience]
        new_query = urlencode(qs, doseq=True)
        url = urlunparse(parsed._replace(query=new_query))

        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=frozenset(["GET"]),
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))

        response = session.get(
            url,
            headers={
                "Authorization": f"bearer {self._request_token}",
                "Accept": "application/json; api-version=2.0",
            },
            timeout=10,
        )

        if not response.ok:
            raise RuntimeError(
                f"Failed to request GitHub OIDC token: {response.status_code} {response.text}"
            )

        data = response.json()
        token = data.get("value")
        if not token:
            raise RuntimeError(
                "GitHub OIDC token response did not contain a token value."
            )

        return token
