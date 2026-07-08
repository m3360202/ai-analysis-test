"""Fetch Anjuke monthly average prices for cross-validation with Lianjia data."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

try:
    from crawler import config
    from crawler.utils import log, request_with_retry, save_json, save_raw
except ImportError:  # Allows running this file directly with python crawler/fetch_anjuke.py.
    import config  # type: ignore[no-redef]
    from utils import log, request_with_retry, save_json, save_raw  # type: ignore[no-redef]


BASE_URL = "https://www.anjuke.com"
CITY_SLUG = "beijing"


def build_fangjia_url(year: int) -> str:
    """Build an Anjuke yearly fangjia page URL for the configured community."""
    slug = config.TARGET["ANJUKE_COMMUNITY_SLUG"]
    return f"{BASE_URL}/fangjia/{CITY_SLUG}{year}/{slug}/"


def fetch_page(url: str, raw_name: str) -> str:
    """Fetch one page and store its HTML in data/raw for later inspection."""
    response = request_with_retry(
        url,
        headers={
            "Referer": f"{BASE_URL}/",
            "Cache-Control": "no-cache",
        },
        follow_redirects=True,
    )
    save_raw(raw_name, response.text)
    return response.text


def parse_monthly_prices(html: str, year: int, url: str) -> list[dict[str, Any]]:
    """Parse monthly average prices embedded in Anjuke NUXT payload."""
    monthly_rows = _extract_nuxt_monthly_rows(html)
    records: list[dict[str, Any]] = []

    for row in monthly_rows:
        month_num = _month_label_to_number(row["month_label"])
        if month_num is None:
            continue

        month_key = f"{year}-{month_num:02d}"
        record = {
            "source": "anjuke",
            "record_type": "monthly_avg_price",
            "city": config.TARGET["CITY"],
            "community": config.TARGET["COMMUNITY_NAME"],
            "community_slug": config.TARGET["ANJUKE_COMMUNITY_SLUG"],
            "year": year,
            "month": month_key,
            "month_label": row["month_label"],
            "avg_price": row["avg_price"],
            "avg_price_unit": "元/㎡",
            "month_change": row["month_change"],
            "year_change": row["year_change"],
            "source_url": url,
        }
        records.append(record)

    return records


def fetch_anjuke_trial(years: list[int] | None = None) -> dict[str, Any]:
    """Fetch yearly Anjuke fangjia pages and save parsed monthly records."""
    target_years = years or config.ANJUKE_YEARS
    payload: dict[str, Any] = {
        "source": "anjuke",
        "target": config.TARGET,
        "time_range": config.TIME_RANGE,
        "years": target_years,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "records": [],
        "errors": [],
    }

    for year in target_years:
        url = build_fangjia_url(year)
        try:
            html = fetch_page(url, f"anjuke_fangjia_{year}.html")
            payload["records"].extend(parse_monthly_prices(html, year, url))
        except Exception as exc:
            log(str(exc), "ERROR")
            payload["errors"].append({"year": year, "url": url, "error": str(exc)})

    output_path = save_json("anjuke_records.json", payload)
    log(f"Saved {len(payload['records'])} parsed Anjuke records to {output_path}")
    return payload


def _extract_nuxt_monthly_rows(html: str) -> list[dict[str, Any]]:
    """Decode Anjuke window.__NUXT__ payload and extract monthly price rows."""
    start = html.find("window.__NUXT__=")
    if start < 0:
        raise ValueError("Anjuke NUXT payload not found")

    end = html.find("</script>", start)
    chunk = html[start:end]
    arg_start = chunk.find("(function(") + len("(function(")
    arg_end = chunk.find("){return")
    if arg_start < 0 or arg_end < 0:
        raise ValueError("Anjuke NUXT function header not found")

    argnames = chunk[arg_start:arg_end].split(",")
    call_idx = chunk.rfind("}(")
    if call_idx < 0:
        raise ValueError("Anjuke NUXT argument list not found")

    args_part = chunk[call_idx + 2 : -2]
    values = _parse_nuxt_args(args_part)
    if len(argnames) != len(values):
        raise ValueError(
            f"Anjuke NUXT arg mismatch: names={len(argnames)} values={len(values)}"
        )

    varmap = dict(zip(argnames, values))
    pattern = (
        r'\{title:"(\d+月)",actionUrl:[^,]*,avgPrice:([^,]+),'
        r"monthChange:([^,]+),yearChange:([^}]+)\}"
    )
    rows: list[dict[str, Any]] = []
    for month_label, avg_price, month_change, year_change in re.findall(pattern, chunk):
        rows.append(
            {
                "month_label": month_label,
                "avg_price": _resolve_nuxt_value(avg_price, varmap),
                "month_change": _resolve_nuxt_value(month_change, varmap),
                "year_change": _resolve_nuxt_value(year_change, varmap),
            }
        )

    if not rows:
        raise ValueError("No monthly price rows found in Anjuke NUXT payload")

    return rows


def _parse_nuxt_args(args_part: str) -> list[Any]:
    """Parse the comma-separated literal argument list of an Anjuke NUXT IIFE."""
    values: list[Any] = []
    index = 0
    while index < len(args_part):
        char = args_part[index]
        if char == '"':
            index += 1
            chars: list[str] = []
            while index < len(args_part):
                current = args_part[index]
                if current == "\\":
                    chars.append(args_part[index + 1])
                    index += 2
                    continue
                if current == '"':
                    break
                chars.append(current)
                index += 1
            values.append("".join(chars))
            index += 1
            if index < len(args_part) and args_part[index] == ",":
                index += 1
            continue

        match = re.match(r"(void 0|-?\d+\.?\d*)", args_part[index:])
        if match:
            token = match.group(1)
            values.append(None if token == "void 0" else token)
            index += len(token)
            if index < len(args_part) and args_part[index] == ",":
                index += 1
            continue

        identifier = re.match(r"([A-Za-z_$][\w$]*)", args_part[index:])
        if identifier:
            values.append(identifier.group(1))
            index += len(identifier.group(1))
            if index < len(args_part) and args_part[index] == ",":
                index += 1
            continue

        index += 1

    return values


def _resolve_nuxt_value(token: Any, varmap: dict[str, Any]) -> Any:
    """Follow NUXT variable aliases until a concrete literal is reached."""
    seen: set[str] = set()
    current = token
    while isinstance(current, str) and current in varmap and current not in seen:
        seen.add(current)
        current = varmap[current]

    if current is None:
        return None
    try:
        return float(current)
    except (TypeError, ValueError):
        return current


def _month_label_to_number(month_label: str) -> int | None:
    match = re.match(r"(\d+)月", month_label)
    if not match:
        return None
    return int(match.group(1))


if __name__ == "__main__":
    log("Starting Anjuke trial fetch")
    result = fetch_anjuke_trial()
    preview = result["records"][:8]
    log(f"Previewing {len(preview)} parsed records")
    for record in preview:
        print(record)
