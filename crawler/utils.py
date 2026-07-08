"""Shared crawler utilities."""

from __future__ import annotations

import json
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

try:
    from crawler import config
except ImportError:  # Allows running this file directly with python crawler/utils.py.
    import config  # type: ignore[no-redef]


def log(message: str, level: str = "INFO") -> None:
    """Print a simple timestamped log line."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level.upper()}] {message}")


def get_headers() -> dict[str, str]:
    """Return request headers with a random User-Agent."""
    user_agent = random.choice(config.USER_AGENTS)
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def polite_sleep() -> None:
    """Sleep for a random interval from RATE_LIMIT."""
    min_interval = config.RATE_LIMIT["MIN_INTERVAL_SECONDS"]
    max_interval = config.RATE_LIMIT["MAX_INTERVAL_SECONDS"]
    time.sleep(random.uniform(min_interval, max_interval))


def request_with_retry(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """Send an HTTP request with random UA, polite delay, and exponential retry."""
    max_retries = config.RATE_LIMIT["MAX_RETRIES"]
    timeout = kwargs.pop("timeout", config.RATE_LIMIT["TIMEOUT_SECONDS"])
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        request_headers = get_headers()
        if headers:
            request_headers.update(headers)

        polite_sleep()
        try:
            log(f"Requesting {method.upper()} {url}, attempt {attempt}/{max_retries}")
            response = httpx.request(
                method=method,
                url=url,
                headers=request_headers,
                timeout=timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_error = exc
            log(f"Request failed: {url} ({exc})", "WARNING")
            if attempt < max_retries:
                time.sleep(2 ** (attempt - 1))

    raise RuntimeError(
        f"Request failed after {max_retries} attempts: {method.upper()} {url}; "
        f"last error: {last_error}"
    ) from last_error


def save_raw(name: str, content: str | bytes) -> Path:
    """Save raw response content under data/raw with a timestamped filename."""
    output_path = _timestamped_raw_path(name)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(content, bytes):
        output_path.write_bytes(content)
    else:
        output_path.write_text(content, encoding="utf-8")

    log(f"Saved raw content: {output_path}")
    return output_path


def save_json(name: str, obj: Any) -> Path:
    """Save JSON serializable content under data/raw with a timestamped filename."""
    output_path = _timestamped_raw_path(name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"Saved JSON content: {output_path}")
    return output_path


def _timestamped_raw_path(name: str) -> Path:
    """Build a safe timestamped file path inside data/raw."""
    safe_name = _safe_filename(name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(safe_name)
    suffix = path.suffix
    stem = path.stem if suffix else path.name
    filename = f"{stem}_{timestamp}{suffix}"
    return config.PATHS["RAW"] / filename


def _safe_filename(name: str) -> str:
    """Keep generated filenames portable and inside the raw data directory."""
    basename = Path(name).name.strip()
    if not basename:
        basename = "raw"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", basename)


if __name__ == "__main__":
    log("Starting crawler utils self-test")
    test_url = "https://httpbin.org/get"
    result = request_with_retry(test_url)
    raw_path = save_raw("httpbin_get.html", result.text)
    json_path = save_json("httpbin_get.json", result.json())
    log(f"Self-test completed, raw={raw_path.name}, json={json_path.name}")
