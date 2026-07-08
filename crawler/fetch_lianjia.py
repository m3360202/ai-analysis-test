"""Fetch small-sample Lianjia house price records for the target community."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any
from urllib.parse import quote

from parsel import Selector

try:
    from crawler import config
    from crawler.utils import log, request_with_retry, save_json, save_raw
except ImportError:  # Allows running this file directly with python crawler/fetch_lianjia.py.
    import config  # type: ignore[no-redef]
    from utils import log, request_with_retry, save_json, save_raw  # type: ignore[no-redef]


BASE_URL = "https://bj.lianjia.com"
TRIAL_PAGES = int(os.getenv("LIANJIA_PAGES", "1"))


class LianjiaBlockedError(RuntimeError):
    """Raised when Lianjia redirects the request to anti-bot verification."""


def build_deal_url(page: int) -> str:
    """Build a sold-record search URL for the configured community."""
    bizcircle_id = config.TARGET["LIANJIA_BIZCIRCLE_ID"]
    if bizcircle_id:
        page_part = "" if page == 1 else f"pg{page}"
        return f"{BASE_URL}/chengjiao/{page_part}{bizcircle_id}/"

    keyword = quote(config.TARGET["COMMUNITY_NAME"])
    page_part = "" if page == 1 else f"pg{page}"
    return f"{BASE_URL}/chengjiao/{page_part}rs{keyword}/"


def build_listing_url(page: int) -> str:
    """Build an on-sale listing search URL for the configured community."""
    bizcircle_id = config.TARGET["LIANJIA_BIZCIRCLE_ID"]
    if bizcircle_id:
        page_part = "" if page == 1 else f"pg{page}"
        return f"{BASE_URL}/ershoufang/{page_part}{bizcircle_id}/"

    keyword = quote(config.TARGET["COMMUNITY_NAME"])
    page_part = "" if page == 1 else f"pg{page}"
    return f"{BASE_URL}/ershoufang/{page_part}rs{keyword}/"


def fetch_page(url: str, raw_name: str) -> str:
    """Fetch one page and store its HTML in data/raw for later inspection."""
    headers = {
        "Referer": f"{BASE_URL}/",
        "Cache-Control": "no-cache",
    }
    headers.update(_get_lianjia_auth_headers())

    response = request_with_retry(
        url,
        headers=headers,
        follow_redirects=True,
    )
    save_raw(raw_name, response.text)
    if _is_blocked_response(str(response.url), response.text):
        raise LianjiaBlockedError(
            f"Lianjia anti-bot verification triggered for {url}; "
            f"final_url={response.url}"
        )
    return response.text


def parse_deal_records(html: str, page: int, url: str) -> list[dict[str, Any]]:
    """Parse sold records visible on a Lianjia chengjiao result page."""
    selector = Selector(text=html)
    records: list[dict[str, Any]] = []

    for item in selector.css("ul.listContent li"):
        title = _first_text(item.css(".title a::text").get())
        if not title:
            continue

        record = {
            "source": "lianjia",
            "record_type": "deal",
            "city": config.TARGET["CITY"],
            "target_community": config.TARGET["COMMUNITY_NAME"],
            "title": title,
            "community": _parse_title_part(title, 0),
            "layout": _parse_title_part(title, 1),
            "area": _parse_title_part(title, 2),
            "deal_date": _first_text(item.css(".dealDate::text").get()),
            "total_price": _join_text(item.css(".totalPrice ::text").getall()),
            "unit_price": _join_text(item.css(".unitPrice ::text").getall()),
            "house_info": _join_text(item.css(".houseInfo ::text").getall()),
            "position_info": _join_text(item.css(".positionInfo ::text").getall()),
            "source_url": url,
            "page": page,
        }
        if _is_in_time_range(record["deal_date"]):
            records.append(record)

    return records


def parse_listing_records(html: str, page: int, url: str) -> list[dict[str, Any]]:
    """Parse current on-sale records visible on a Lianjia listing result page."""
    selector = Selector(text=html)
    records: list[dict[str, Any]] = []

    for item in selector.css("ul.sellListContent li.clear"):
        title = _first_text(item.css(".title a::text").get())
        if not title:
            continue

        house_info = _split_pipe_text(_join_text(item.css(".houseInfo ::text").getall()))
        record = {
            "source": "lianjia",
            "record_type": "listing",
            "city": config.TARGET["CITY"],
            "target_community": config.TARGET["COMMUNITY_NAME"],
            "title": title,
            "community": _first_text(item.css(".positionInfo a::text").get()),
            "layout": _get_by_index(house_info, 0),
            "area": _get_by_index(house_info, 1),
            "deal_date": None,
            "listing_info": _join_text(item.css(".followInfo ::text").getall()),
            "total_price": _join_text(item.css(".totalPrice ::text").getall()),
            "unit_price": _join_text(item.css(".unitPrice ::text").getall()),
            "house_info": " | ".join(house_info),
            "position_info": _join_text(item.css(".positionInfo ::text").getall()),
            "source_url": url,
            "page": page,
        }
        records.append(record)

    return records


def fetch_lianjia_trial(pages: int = TRIAL_PAGES) -> dict[str, Any]:
    """Fetch a small sample of deal and listing pages, then save parsed records."""
    include_listings = os.getenv("LIANJIA_INCLUDE_LISTINGS", "1") != "0"
    start_page = int(os.getenv("LIANJIA_START_PAGE", "1"))
    payload: dict[str, Any] = {
        "source": "lianjia",
        "target": config.TARGET,
        "time_range": config.TIME_RANGE,
        "start_page": start_page,
        "trial_pages": pages,
        "include_listings": include_listings,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "records": [],
        "errors": [],
    }

    for page in range(start_page, start_page + pages):
        deal_url = build_deal_url(page)
        try:
            deal_html = fetch_page(deal_url, f"lianjia_deal_page_{page}.html")
            payload["records"].extend(parse_deal_records(deal_html, page, deal_url))
        except (LianjiaBlockedError, RuntimeError) as exc:
            log(str(exc), "ERROR")
            payload["errors"].append(
                {
                    "record_type": "deal",
                    "page": page,
                    "url": deal_url,
                    "error": str(exc),
                }
            )

        if include_listings:
            listing_url = build_listing_url(page)
            try:
                listing_html = fetch_page(
                    listing_url,
                    f"lianjia_listing_page_{page}.html",
                )
                payload["records"].extend(
                    parse_listing_records(listing_html, page, listing_url)
                )
            except (LianjiaBlockedError, RuntimeError) as exc:
                log(str(exc), "ERROR")
                payload["errors"].append(
                    {
                        "record_type": "listing",
                        "page": page,
                        "url": listing_url,
                        "error": str(exc),
                    }
                )

    output_path = save_json("lianjia_records.json", payload)
    log(f"Saved {len(payload['records'])} parsed Lianjia records to {output_path}")
    return payload


def _is_in_time_range(date_text: str | None) -> bool:
    """Check YYYY.MM.DD deal dates against configured YYYY-MM range."""
    if not date_text:
        return False

    normalized_month = date_text.strip().replace(".", "-")[:7]
    return config.TIME_RANGE["START"] <= normalized_month <= config.TIME_RANGE["END"]


def _is_blocked_response(final_url: str, html: str) -> bool:
    return "hip.lianjia.com/captcha" in final_url or 'content="Captcha"' in html[:1000]


def _get_lianjia_auth_headers() -> dict[str, str]:
    """Read temporary Lianjia auth headers from environment variables."""
    headers: dict[str, str] = {}

    cookie = os.getenv("LIANJIA_COOKIE", "").strip()
    if cookie:
        headers["Cookie"] = cookie
        log("Using Lianjia Cookie from LIANJIA_COOKIE")

    env_header_map = {
        "LIANJIA_USER_AGENT": "User-Agent",
        "LIANJIA_ACCESS_TOKEN": "Lianjia-Access-Token",
        "LIANJIA_APP_ID": "Lianjia-App-Id",
        "LIANJIA_DEVICE_ID": "Lianjia-Device-Id",
        "LIANJIA_IM_PROTOCAL_VERSION": "Lianjia-Im-Protocal-Version",
        "LIANJIA_IM_SIGNATURE": "Lianjia-Im-Signature",
        "LIANJIA_IM_TIMESTAMP": "Lianjia-Im-Timestamp",
        "LIANJIA_ORIGIN": "Origin",
        "LIANJIA_SEC_CH_UA": "sec-ch-ua",
        "LIANJIA_SEC_CH_UA_MOBILE": "sec-ch-ua-mobile",
        "LIANJIA_SEC_CH_UA_PLATFORM": "sec-ch-ua-platform",
    }
    for env_name, header_name in env_header_map.items():
        value = os.getenv(env_name, "").strip()
        if value:
            headers[header_name] = value

    return headers


def _first_text(value: str | None) -> str:
    return value.strip() if value else ""


def _join_text(values: list[str]) -> str:
    return " ".join(value.strip() for value in values if value.strip())


def _split_pipe_text(value: str) -> list[str]:
    return [part.strip() for part in value.split("|") if part.strip()]


def _parse_title_part(title: str, index: int) -> str:
    return _get_by_index(title.split(), index)


def _get_by_index(values: list[str], index: int) -> str:
    return values[index] if index < len(values) else ""


if __name__ == "__main__":
    log("Starting Lianjia trial fetch")
    result = fetch_lianjia_trial(pages=TRIAL_PAGES)
    preview = result["records"][:5]
    log(f"Previewing {len(preview)} parsed records")
    for record in preview:
        print(record)
