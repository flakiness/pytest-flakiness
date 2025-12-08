import os
import json
import requests
import brotli  # <--- The mandate
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


def upload_report(
    report: FlakinessReport,
    attachments: List[FileAttachment],
    endpoint: str,
    token: str,
) -> None:
    session = _get_session()
    headers = {"Authorization": f"Bearer {token}"}

    try:
        start_resp = session.post(
            f"{endpoint}/api/run/startUpload",
            json={"attachmentIds": attachments},
            headers=headers,
            timeout=10,
        )
        start_resp.raise_for_status()
        upload_data = start_resp.json()

        report_json = json.dumps(report).encode("utf-8")
        compressed_report = brotli.compress(report_json)
        session.put(
            upload_data["report_upload_url"],
            data=compressed_report,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "br",
                "Content-Length": str(len(compressed_report)),
            },
            timeout=30,
        )

        upload_urls = upload_data.get("attachment_upload_urls", {})

        for att_info in attachments:
            if att_info["id"] not in upload_urls:
                continue

            file_path = att_info["path"]
            if not os.path.exists(file_path):
                print(f"[Flakiness] Warning: Attachment not found {file_path}")
                continue

            file_size = os.path.getsize(file_path)

            # Streaming upload
            with open(file_path, "rb") as f:
                session.put(
                    upload_urls[att_info["id"]],
                    data=f,
                    headers={
                        "Content-Type": att_info["contentType"],
                        "Content-Length": str(file_size),
                    },
                    timeout=30,
                )

        finish_resp = session.post(
            f"{endpoint}/api/run/completeUpload",
            json={"upload_token": upload_data["upload_token"]},
            headers=headers,
            timeout=10,
        )
        finish_resp.raise_for_status()

        result = finish_resp.json()
        report_url = result.get("report_url")

        if report_url:
            # Handle relative URLs from API
            full_url = (
                report_url
                if report_url.startswith("http")
                else f"{endpoint}{report_url}"
            )
            print(f"✅ [Flakiness] Report uploaded: {full_url}")
        else:
            print("✅ [Flakiness] Report uploaded successfully.")

    except Exception as e:
        print(f"❌ [Flakiness] Upload failed: {e}")
