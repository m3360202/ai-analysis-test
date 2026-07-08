"""Centralized crawler configuration."""

from pathlib import Path


# Project paths are derived from this file so scripts work from any cwd.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Crawl time range.
TIME_RANGE = {
    "START": "2025-09",
    "END": "2025-12",
}

# Target community metadata.
TARGET = {
    "CITY": "北京",
    "COMMUNITY_NAME": "天通苑",
    "LIANJIA_COMMUNITY_ID": "",
    "LIANJIA_BIZCIRCLE_ID": "tiantongyuan1",
    "ANJUKE_COMMUNITY_SLUG": "tiantongyuan",
}

# Anjuke fangjia pages are organized by calendar year.
ANJUKE_YEARS = [2024, 2025, 2026]

# Public-opinion and market-event keywords.
KEYWORDS = [
    "天通苑",
    "北京楼市",
    "认房不认贷",
    "房贷利率",
]

# User-Agent pool for crawler requests.
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]

# Request rate limit and retry settings.
RATE_LIMIT = {
    "MIN_INTERVAL_SECONDS": 2.0,
    "MAX_INTERVAL_SECONDS": 5.0,
    "MAX_RETRIES": 3,
    "TIMEOUT_SECONDS": 20.0,
}

# Data and report output paths.
PATHS = {
    "RAW": PROJECT_ROOT / "data" / "raw",
    "CLEAN": PROJECT_ROOT / "data" / "clean",
    "REPORT": PROJECT_ROOT / "report",
}
