"""Optional standard-library connectors for configured upstream APIs."""

from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen


def fetch_configured_wearable_payload() -> tuple[object, str]:
    """Fetch one JSON payload from the administrator-configured wearable URL.

    The URL is never supplied by an API caller. This keeps the pull connector
    bounded to a deployment-controlled provider and avoids arbitrary outbound
    requests from the application.
    """
    url = os.getenv("PRANATWIN_WEARABLE_API_URL")
    if not url:
        raise RuntimeError("PRANATWIN_WEARABLE_API_URL is not configured")
    request = Request(url, headers={"Accept": "application/json"})
    api_key = os.getenv("PRANATWIN_WEARABLE_API_KEY")
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urlopen(request, timeout=10) as response:
            content = response.read(2_000_001)
    except Exception as exc:
        raise RuntimeError("Configured wearable API request failed") from exc
    if len(content) > 2_000_000:
        raise RuntimeError("Configured wearable API response exceeds 2 MB")
    try:
        return json.loads(content), url
    except json.JSONDecodeError as exc:
        raise RuntimeError("Configured wearable API did not return JSON") from exc
