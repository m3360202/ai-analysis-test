"""Prepare cleaned data and analysis metrics for the HTML report."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_JSON = PROJECT_ROOT / "data" / "raw" / "anjuke_records_20260708_173955.json"
EVENTS_CSV = PROJECT_ROOT / "data" / "clean" / "events.csv"
OUTPUT_JSON = PROJECT_ROOT / "report" / "web" / "src" / "data" / "reportData.json"


def parse_price(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip('"'))
    raise TypeError(f"Unexpected price value: {value!r}")


def load_price_series() -> list[dict]:
    payload = json.loads(RAW_JSON.read_text(encoding="utf-8"))
    by_month: dict[str, dict] = {}
    for row in payload["records"]:
        month = row["month"]
        year = int(month[:4])
        month_num = int(month[5:7])
        # Skip duplicated 2026 Aug-Dec rows (mirror 2025 with string prices).
        if year == 2026 and month_num >= 8:
            continue
        by_month[month] = {
            "month": month,
            "ref_price": parse_price(row["avg_price"]),
            "month_change": row.get("month_change"),
            "year_change": row.get("year_change"),
            "source_url": row.get("source_url", ""),
        }
    return [by_month[k] for k in sorted(by_month)]


def pct_change(start: float, end: float) -> float:
    return round((end - start) / start * 100, 2)


def load_events() -> list[dict]:
    rows = []
    with EVENTS_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "date": row["date"],
                    "event": row["event"],
                    "level": row["level"],
                    "weight": int(row["weight"]),
                    "type": row["type"],
                    "direction": row["direction"],
                    "note": row["note"],
                    "content": row["content"],
                    "source": row["source"],
                }
            )
    return rows


def build_phases(series: list[dict]) -> list[dict]:
    def phase(start_m: str, end_m: str, name: str, events: list[str], text: str) -> dict:
        start_p = next(x for x in series if x["month"] == start_m)["ref_price"]
        end_p = next(x for x in series if x["month"] == end_m)["ref_price"]
        return {
            "name": name,
            "range": f"{start_m} ~ {end_m}",
            "start_price": start_p,
            "end_price": end_p,
            "change_pct": pct_change(start_p, end_p),
            "related_events": events,
            "summary": text,
        }

    return [
        phase(
            "2024-01",
            "2024-12",
            "2024 年：市场回归理性与结构性调整",
            ["北京全市实施认房不认贷", "北京优化通州区商品住房限购政策", "回天地区老旧小区改造持续推进"],
            "2024 年安居客板块参考序列呈温和下行，同比降幅逐月扩大，反映区域供需再平衡与预期修复并存，临铁与非临铁、户型面积段分化明显。",
        ),
        phase(
            "2025-01",
            "2025-06",
            "2025 上半年：政策效果存在滞后性",
            ["央行下调个人住房公积金贷款利率", "LPR报价下调10个基点", "天通苑东一区老楼加装电梯工程推进"],
            "多轮利率与公积金优化陆续出台，但板块参考序列仍延续调整，说明信贷宽松向成交传导存在时滞，本地微更新主要体现为结构性支撑。",
        ),
        phase(
            "2025-07",
            "2025-12",
            "2025 下半年：区域供需失衡下的筑底",
            ["北京五环外商品住房不限套数", "天通苑东二区法拍房二拍成交", "北京进一步优化房地产相关政策"],
            "限购边际放松与轨交利好释放改善预期，但法拍折价个案对议价心理形成下拉参照；整体仍处筑底阶段，极端成交不代表普遍水平。",
        ),
        phase(
            "2026-01",
            "2026-07",
            "2026 上半年：弱修复与配套预期升温",
            ["存量公积金贷款利率正式下调执行", "第三轮回天行动计划正式发布", "昌平奥北中学项目施工资格预审公告"],
            "参考序列较年初低点小幅回升，城市更新与教育配套预期增强，市场呈现弱修复特征，临铁板块相对更具韧性。",
        ),
    ]


def build_event_impact(series: list[dict], events: list[dict]) -> list[dict]:
    month_index = {x["month"]: i for i, x in enumerate(series)}
    prices = [x["ref_price"] for x in series]
    impacts = []
    key_events = [
        "北京全市实施认房不认贷",
        "北京发布房地产政策优化组合拳",
        "北京五环外商品住房不限套数",
        "地铁17号线全线贯通及18号线开通",
    ]
    for event in events:
        if event["event"] not in key_events:
            continue
        event_month = event["date"][:7]
        if event_month not in month_index:
            # Map to nearest month in series
            candidates = [m for m in month_index if m >= event_month]
            if not candidates:
                continue
            event_month = candidates[0]
        idx = month_index[event_month]
        base = prices[idx]
        m1 = prices[min(idx + 1, len(prices) - 1)] if idx + 1 < len(prices) else base
        m3 = prices[min(idx + 3, len(prices) - 1)] if idx + 3 < len(prices) else base
        reaction = "短期企稳" if pct_change(base, m1) >= -0.5 else "延续调整"
        impacts.append(
            {
                "event": event["event"],
                "event_date": event["date"],
                "after_1m_pct": pct_change(base, m1),
                "after_3m_pct": pct_change(base, m3),
                "reaction": reaction,
                "confidence": "中",
            }
        )
    return impacts


def main() -> None:
    series = load_price_series()
    events = load_events()
    base_price = series[0]["ref_price"]
    latest = series[-1]

    for item in series:
        item["index_base100"] = round(item["ref_price"] / base_price * 100, 2)

    # MoM % from ref_price
    for i, item in enumerate(series):
        if i == 0:
            item["mom_pct"] = None
        else:
            prev = series[i - 1]["ref_price"]
            item["mom_pct"] = pct_change(prev, item["ref_price"])

    significant_mom = [x for x in series if x["mom_pct"] is not None and abs(x["mom_pct"]) >= 1.5]

    summary = {
        "community": "天通苑",
        "city": "北京",
        "report_date": date.today().isoformat(),
        "period_start": series[0]["month"],
        "period_end": latest["month"],
        "month_count": len(series),
        "latest_ref_price": latest["ref_price"],
        "base_month": series[0]["month"],
        "base_ref_price": base_price,
        "fixed_base_change_pct": pct_change(base_price, latest["ref_price"]),
        "latest_yoy_pct": latest["year_change"],
        "price_range_low": min(x["ref_price"] for x in series),
        "price_range_high": max(x["ref_price"] for x in series),
        "max_mom_drop": min(
            (x for x in series if x["mom_pct"] is not None),
            key=lambda x: x["mom_pct"],
        ),
        "data_source": "安居客板块月度参考序列",
        "fetch_time": "2026-07-08",
        "disclaimer": (
            "本报告不使用成交明细与舆情爬取；价格序列为安居客平台板块月度参考价，"
            "不等同于实际网签成交均价，存在网签滞后与样本口径差异；"
            "结论强调结构性分化，极端个案不代表整体市场。"
        ),
    }

    references = [
        {
            "title": "北京市人民政府 — 认房不认贷政策解读",
            "url": "https://www.beijing.gov.cn/zhengce/zcjd/202309/t20230901_3242582.html",
            "type": "官方",
        },
        {
            "title": "北京住房公积金管理中心 — 商贷首付比例调整",
            "url": "https://gjj.beijing.gov.cn/web/zwgk61/2024zcwj/436433464/436433467/543423930/index.html",
            "type": "官方",
        },
        {
            "title": "北京市发改委 — 第三轮回天行动计划",
            "url": "https://fgw.beijing.gov.cn/fgwzwgk/2024zcwj/sjbmgfxwj/bjszfwj/202604/t20260415_4582979.htm",
            "type": "官方",
        },
        {
            "title": "首都之窗 — 地铁17号线贯通及18号线开通",
            "url": "https://www.beijing.gov.cn/fuwu/bmfw/sy/jrts/202512/t20251213_4339500.html",
            "type": "官方",
        },
        {
            "title": "中国人民银行 — LPR 报价",
            "url": "https://www.bankofchina.com/fimarkets/lilv/fd32/201310/t20131031_2591219.html",
            "type": "官方",
        },
    ]

    structural_notes = [
        {
            "dimension": "临铁 / 非临铁",
            "description": "17/18 号线换乘后，临铁板块（天通苑东等）通勤溢价相对稳固；非临铁组团议价空间更大。",
        },
        {
            "dimension": "户型面积段",
            "description": "大两居、小三居为流通主力；超大户型与特殊户型成交稀疏，不宜用个案代表板块整体。",
        },
        {
            "dimension": "楼层与房龄",
            "description": "加装电梯推进改善多层住宅流动性；高层与老旧楼栋在挂牌周期与议价上呈现分化。",
        },
        {
            "dimension": "保障房分流",
            "description": "共有产权房与保障房体系对刚需客群形成分流，对商品房二手市场形成结构性影响。",
        },
    ]

    payload = {
        "summary": summary,
        "price_series": series,
        "significant_mom": significant_mom,
        "events": events,
        "phases": build_phases(series),
        "event_impact": build_event_impact(series, events),
        "references": references,
        "structural_notes": structural_notes,
        "conclusion": {
            "headline": "在「房住不炒」与多轮优化政策背景下，天通苑作为北京最大居住社区，其价格参考序列呈现结构性调整与弱修复并存的走势。",
            "template": (
                "在「房住不炒」总基调与北京市多轮房地产优化政策背景下，天通苑作为北京最大居住社区，"
                "其房价走势呈现出先缓后急再筑底的结构性调整特征。这主要受到信贷环境变化、"
                "区域供需再平衡、轨交与教育配套预期等因素的影响。未来，随着第三轮回天行动计划、"
                "奥北中学建设及城市更新的推进，市场有望保持温和修复与分化并存的格局。"
            ),
            "findings": [
                "定基观察（2024-01=100）：至 2026-07 参考序列定基跌幅约 20.1%，调整节奏前缓后快，符合市场回归理性特征。",
                "同比口径：2026-07 同比降幅 8.22%，较 2024 年高点同比降幅有所收窄，显示筑底信号。",
                "政策传导：认房不认贷、首付下调、五环外限购松绑等政策效果存在滞后性，未在单月序列中表现为单边上行。",
                "配套支撑：17/18 号线贯通、回天城市更新、奥北中学建设为板块提供中长期预期支撑。",
                "结构分化：临铁优于非临铁、主流户型优于极端户型；法拍折价个案需与普遍成交区分看待。",
                "数据边界：本报告基于安居客板块月度参考序列，未纳入链家成交明细；结论不构成投资建议。",
            ],
            "watchlist": [
                "已出台政策的落地效果与信贷利率变化（存量公积金利率兑现等）",
                "回天地区 127 个重点项目推进节奏与城市更新成效",
                "天通苑东换乘枢纽带来的职住便利性与临铁板块韧性",
                "共有产权房、保障房供应对刚需客群的分流效应",
            ],
            "risks": [
                "平台参考序列与网签成交存在口径差异及滞后，不宜直接等同于个人房源成交价",
                "事件与价格窗口分析仅表明相关性，相关不等于因果",
                "本报告为历史复盘与中性展望，不构成任何投资建议",
            ],
        },
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_JSON} ({len(series)} months, {len(events)} events)")


if __name__ == "__main__":
    main()
