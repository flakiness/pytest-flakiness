import os
import json
import requests
import brotli
from typing import TypedDict, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .flakiness_report import FlakinessReport, AttachmentId
from pathlib import Path


class FileAttachment(TypedDict):
    """Reference to a file attachment"""

    contentType: str
    id: AttachmentId
    path: Path


def _get_session() -> requests.Session:
    """Creates a requests session with automatic retries."""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST", "PUT"]),
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def _upload_attachments(
    session: requests.Session,
    endpoint: str,
    attachments: List[FileAttachment],
    headers: dict,
):
    if not attachments:
        return

    attachments_resp = session.post(
        f"{endpoint}/api/upload/attachments",
        json={"attachmentIds": [att["id"] for att in attachments]},
        headers=headers,
        timeout=10,
    )
    attachments_resp.raise_for_status()
    attachment_urls_data = attachments_resp.json()
    # Create a mapping from attachment ID to presigned URL
    attachment_urls = {
        item["attachmentId"]: item["presignedUrl"] for item in attachment_urls_data
    }

    for att_info in attachments:
        attachment_id = att_info["id"]
        if attachment_id not in attachment_urls:
            print(f"[Flakiness] Warning: No upload URL for attachment {attachment_id}")
            continue

        file_path = att_info["path"]
        if not os.path.exists(file_path):
            print(f"[Flakiness] Warning: Attachment not found {file_path}")
            continue

        # Check if attachment is compressible
        mime_type = att_info["contentType"].lower().strip()
        is_compressible = (
            mime_type.startswith("text/")
            or mime_type.endswith("+json")
            or mime_type.endswith("+text")
            or mime_type.endswith("+xml")
        )

        # Read file content
        with open(file_path, "rb") as f:
            file_data = f.read()

        # Compress if compressible
        if is_compressible:
            file_data = brotli.compress(file_data)

        # Prepare headers
        upload_headers = {
            "Content-Type": att_info["contentType"],
            "Content-Length": str(len(file_data)),
        }
        if is_compressible:
            upload_headers["Content-Encoding"] = "br"

        # Upload attachment
        session.put(
            attachment_urls[attachment_id],
            data=file_data,
            headers=upload_headers,
            timeout=30,
        )


def upload_report(
    report: FlakinessReport,
    attachments: List[FileAttachment],
    endpoint: str,
    token: str,
) -> None:
    session = _get_session()

    try:
        # Step 1: Start upload
        start_resp = session.post(
            f"{endpoint}/api/upload/start",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        start_resp.raise_for_status()
        upload_session_data = start_resp.json()
        headers = {"Authorization": f"Bearer {upload_session_data['uploadToken']}"}

        # Step 2: Upload report
        report_json = json.dumps(report).encode("utf-8")
        compressed_report = brotli.compress(report_json)
        session.put(
            upload_session_data["presignedReportUrl"],
            data=compressed_report,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "br",
                "Content-Length": str(len(compressed_report)),
            },
            timeout=30,
        )

        # Step 3: Upload attachments
        _upload_attachments(session, endpoint, attachments, headers)

        # Step 4: Finish upload
        finish_resp = session.post(
            f"{endpoint}/api/upload/finish",
            headers=headers,
            timeout=10,
        )
        finish_resp.raise_for_status()

        full_url = f"{endpoint}{upload_session_data['webUrl']}"
        print(f"\n[Flakiness] Report uploaded: {full_url}")

    except Exception as e:
        print(f"\n[Flakiness] Upload failed: {e}")
