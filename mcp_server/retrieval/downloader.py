"""
HTTP Downloader for Document Retrieval.
Fetches remote files safely with timeouts, realistic headers, and accurate error classification.
"""

from typing import Optional, Tuple
import requests

DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 Jaldhaara-CSR-Retriever/1.0"
)


def download_document_bytes(
    url: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    session: Optional[requests.Session] = None,
) -> Tuple[str, Optional[bytes], Optional[str], Optional[str]]:
    """
    Downloads remote document content with error classification.

    Returns:
        (status, content, content_type, error_message)
        status in ['FOUND', 'NOT_FOUND', 'ERROR']
    """
    if not url or not url.strip():
        return "ERROR", None, None, "Document URL is empty or missing"

    clean_url = url.strip()
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/pdf,application/octet-stream,text/html;q=0.8,*/*;q=0.5",
        "Accept-Language": "en-US,en;q=0.9",
    }

    req_fn = session.get if session else requests.get

    try:
        response = req_fn(
            clean_url,
            headers=headers,
            timeout=timeout_seconds,
            allow_redirects=True,
            stream=False,
        )

        # 404 means the document is not found at that location
        if response.status_code == 404:
            return "NOT_FOUND", None, None, f"HTTP 404: Document not found at {clean_url}"

        # 403 / 429 / 5xx are retrieval errors
        if response.status_code in (401, 403):
            return "ERROR", None, None, f"HTTP {response.status_code}: Access forbidden / unauthorized at source"

        if response.status_code == 429:
            return "ERROR", None, None, "HTTP 429: Rate limit encountered at source"

        if response.status_code >= 400:
            return "ERROR", None, None, f"HTTP {response.status_code}: Request failed for {clean_url}"

        content_type = response.headers.get("Content-Type")
        return "FOUND", response.content, content_type, None

    except requests.exceptions.Timeout:
        return "ERROR", None, None, f"Connection timed out after {timeout_seconds}s fetching {clean_url}"

    except requests.exceptions.SSLError as e:
        return "ERROR", None, None, f"SSL verification failure connecting to {clean_url}: {str(e)}"

    except requests.exceptions.ConnectionError as e:
        return "ERROR", None, None, f"Network connection failed for {clean_url}: {str(e)}"

    except Exception as e:
        return "ERROR", None, None, f"Unexpected retrieval error: {str(e)}"
