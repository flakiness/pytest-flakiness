import base64
import binascii
import json
import os
from typing import Any


class GitlabOIDC:
    """Handles GitLab CI/CD OIDC authentication with flakiness.io.

    Unlike GitHub Actions — where the token is minted at runtime and we pick the
    `aud` claim ourselves — GitLab mints ID tokens when the job starts and exposes
    them as environment variables. The audience is therefore declared in
    `.gitlab-ci.yml` and must match the flakiness project the report is uploaded to:

        test:
          id_tokens:
            FLAKINESS_ID_TOKEN:
              aud: my-org/my-project
          script:
            - pytest
    """

    name = "GitLab CI/CD"

    def __init__(self, id_token: str):
        self._id_token = id_token

    @staticmethod
    def init_from_env() -> "GitlabOIDC | None":
        """Creates a GitlabOIDC instance from GitLab CI/CD environment variables.

        Reads `FLAKINESS_ID_TOKEN`, which GitLab CI/CD sets for jobs that declare an
        `id_tokens: FLAKINESS_ID_TOKEN:` entry in `.gitlab-ci.yml`. Returns None if
        not running in GitLab CI/CD with an ID token configured.
        """
        id_token = os.environ.get("FLAKINESS_ID_TOKEN")
        if id_token:
            return GitlabOIDC(id_token)
        return None

    def fetch_token(self, audience: str) -> str:
        """Returns the flakiness.io access token — the GitLab ID token itself.

        Succeeds as long as the ID token names `audience` in its `aud` claim. The
        returned token only uploads successfully if the flakiness.io project is bound
        to the GitLab project running the pipeline; otherwise flakiness.io rejects it.

        Args:
            audience: The expected audience claim (flakinessProject value).

        Returns:
            The GitLab ID token string.

        Raises:
            RuntimeError: If the ID token is not a JWT, carries no `aud` claim, or its
                `aud` claim does not include `audience`. GitLab mints the token when
                the job starts, so all three can only be fixed in `.gitlab-ci.yml`.
        """
        # Every check below is a `.gitlab-ci.yml` misconfiguration that cannot be fixed
        # at runtime and that the server would reject anyway, so failing here with a
        # precise message beats letting the upload come back as a bare 401.
        payload = _jwt_payload(self._id_token)
        if payload is None:
            raise RuntimeError(
                "GitLab ID token is not a JWT. Check that FLAKINESS_ID_TOKEN comes from "
                f"an id_tokens entry with `aud: {audience}` in .gitlab-ci.yml."
            )

        claim = _audience_claim(payload)
        if not claim:
            raise RuntimeError(
                f'GitLab ID token has no audience, so it cannot upload to "{audience}". '
                f"Declare the FLAKINESS_ID_TOKEN id_token with `aud: {audience}` in .gitlab-ci.yml."
            )
        if audience not in claim:
            found = ", ".join(json.dumps(entry) for entry in claim)
            raise RuntimeError(
                f'GitLab ID token audience is {found}, but the report uploads to "{audience}". '
                f'Set the audience of the FLAKINESS_ID_TOKEN id_token in .gitlab-ci.yml to "{audience}".'
            )

        return self._id_token


def _jwt_payload(jwt: str) -> dict[str, Any] | None:
    """Reads a JWT payload without verifying the signature; flakiness.io is the one
    that verifies the token. Returns None if the token is not a JWT."""
    parts = jwt.split(".")
    if len(parts) < 2 or not parts[1]:
        return None
    segment = parts[1]
    # base64url segments are unpadded in JWTs; b64decode insists on padding.
    segment += "=" * (-len(segment) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(segment).decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _audience_claim(payload: dict[str, Any]) -> list[str]:
    """Normalizes the `aud` claim, which a JWT may carry as either a string or a list
    of strings, into a list. Returns an empty list when absent or unusable."""
    aud = payload.get("aud")
    if isinstance(aud, str):
        return [aud]
    if isinstance(aud, list):
        return [entry for entry in aud if isinstance(entry, str)]
    return []
