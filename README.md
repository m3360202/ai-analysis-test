# 北京天通苑房价历史分析 Demo

围绕北京天通苑板块，采集公开房价参考序列与政策事件数据，经清洗、分析后生成一份可离线打开的静态 HTML 分析报告。项目覆盖 **爬虫 → 清洗 → 分析 → 报告** 完整链路，适用于 AI 数据报告 / 数据分析方向的 Demo 展示。

## 项目状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 安居客板块参考价爬虫 | ✅ 已跑通 | 36 条月度记录（2024–2026） |
| 链家成交明细爬虫 | ⏸ 暂停 | 验证码拦截，本次报告未纳入 |
| 政策事件清单 | ✅ 已整理 | `events.csv` 24 条 + 权威引用索引 |
| 舆情爬虫 | ⏸ 未纳入 | 本次时间关系跳过 |
| 数据分析脚本 | ✅ 已完成 | `analysis/prepare_report_data.py` |
| HTML 报告 | ✅ 已生成 | `report/天通苑房价分析报告.html` |

## 目录结构

```text
.
├── crawler/                    # Python 爬虫
│   ├── config.py               # 目标小区、时间范围、路径配置
│   ├── utils.py                # 请求、重试、落盘工具
│   ├── fetch_anjuke.py         # 安居客板块月度参考价
│   └── fetch_lianjia.py        # 链家成交/挂牌（验证码未通过）
├── data/
│   ├── raw/                    # 原始 HTML / JSON（gitignore）
│   └── clean/
│       ├── events.csv          # 政策与关键事件（24 条）
│       └── events2.text        # 官方/媒体/学术引用索引
├── analysis/
│   └── prepare_report_data.py  # 清洗安居客数据 + 生成分析指标
├── report/
│   ├── 天通苑房价分析报告.html   # ⭐ 最终交付物（单文件、可离线）
│   ├── dist/                   # Vite 构建输出
│   └── web/                    # React + Vite + ECharts 前端源码
├── doc/
│   ├── 天通苑房价报告-页面提纲与布局.md
│   └── 天通苑房价报告-执行方案与AI交互流程.md
├── requirements.txt
└── README.md
```

## 快速开始：查看报告

无需安装任何依赖，直接在浏览器中打开：

```text
report/天通苑房价分析报告.html
```

报告为单文件 HTML（CSS / JS / ECharts 已内联），双击即可离线浏览。

## 环境安装

### Python（爬虫 + 分析）

建议 Python 3.10+，使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如需运行链家浏览器爬虫，额外安装 Playwright：

```bash
playwright install chromium
```

### Node.js（报告前端构建）

报告前端需要 Node.js 18+：

```bash
cd report/web
npm install
```

## 使用流程

### 1. 采集安居客板块参考价

```bash
# 在项目根目录执行
python3 -m crawler.fetch_anjuke
```

输出示例：`data/raw/anjuke_records_YYYYMMDD_HHMMSS.json`

配置项见 `crawler/config.py`：

- `TARGET.ANJUKE_COMMUNITY_SLUG`：安居客小区 slug（默认 `tiantongyuan`）
- `ANJUKE_YEARS`：抓取年份列表（默认 `[2024, 2025, 2026]`）

### 2. （可选）采集链家成交明细

```bash
# 需配置登录态环境变量，且可能触发验证码
export LIANJIA_COOKIE="..."   # 可选
python3 -m crawler.fetch_lianjia
```

链家爬虫受反爬限制，当前 Demo 以安居客序列为主数据源。

### 3. 生成分析数据

```bash
python3 analysis/prepare_report_data.py
```

读取 `data/raw/anjuke_records_*.json` 与 `data/clean/events.csv`，输出：

```text
report/web/src/data/reportData.json
```

脚本会自动：

- 去重并清洗 2026 年重复月份
- 计算定基指数（2024-01 = 100）、环比、同比
- 划分四个分析阶段
- 生成事件归因矩阵与合规结论文案

### 4. 构建 HTML 报告

```bash
cd report/web
npm run build
cp ../dist/index.html ../天通苑房价分析报告.html
```

开发预览（热更新）：

```bash
cd report/web
npm run dev
```

## 报告内容概览

报告共 8 个章节，信息架构遵循 `doc/天通苑房价报告-页面提纲与布局.md`：

| 章节 | 内容 |
|------|------|
| 封面 | 核心 KPI + 走势预览 |
| 01 数据概览 | 三年板块价格全景摘要 |
| 02 价格走势 | 月度参考价曲线、定基指数、同比/环比 |
| 03 事件时间线 | 24 条政策/配套事件（全国 / 北京 / 天通苑） |
| 04 宏观归因 | 事件 × 价格叠加，阶段划分与归因矩阵 |
| 05 结构拆解 | 临铁/户型/保障房分流等结构性说明 + 权威引用 |
| 06 阶段涨跌 | 各阶段定基变化柱状图 |
| 07 结论展望 | 审慎中性结论，不构成投资建议 |
| 08 方法说明 | 数据来源、处理流程、局限声明 |

### 本次报告的数据边界

- **主数据源**：安居客天通苑板块月度参考序列（2024-01 ~ 2026-07，31 个月）
- **未纳入**：链家成交明细、社媒舆情
- **表述规范**：使用「板块月度参考价 / 定基指数」，避免以单一均价掩盖结构性分化；结论采用同比/定基口径

### 核心分析结论（摘要）

- 定基变化（较 2024-01）：约 **-20.1%**，呈现结构性调整与弱修复并存
- 2024 年：温和下行；2025 年：政策效果存在滞后性，四季度筑底
- 2026 上半年：随回天行动、奥北中学建设等配套预期，参考序列弱修复
- 17/18 号线贯通、城市更新对临铁板块形成中长期支撑

## 数据文件说明

| 文件 | 说明 |
|------|------|
| `data/raw/anjuke_records_*.json` | 安居客原始抓取结果 |
| `data/clean/events.csv` | 政策/利率/配套/法拍等事件，含来源链接 |
| `data/clean/events2.text` | 官方数据源与媒体引用索引 |
| `report/web/src/data/reportData.json` | 报告渲染用的结构化分析结果 |

## 架构原则

1. **配置与代码分离**：目标小区、时间范围集中在 `crawler/config.py`
2. **爬虫只做采集**：取页 → 解析 → 存 raw，不做业务分析
3. **清洗与分析独立**：`analysis/` 读取 raw + clean，输出 JSON
4. **报告与数据解耦**：React 前端只消费 `reportData.json`，可替换数据源重新构建

## 文档

- [页面提纲与布局](doc/天通苑房价报告-页面提纲与布局.md) — 报告 8 章节蓝图与视觉规范
- [执行方案与 AI 交互流程](doc/天通苑房价报告-执行方案与AI交互流程.md) — 端到端开发与 AI 协作流程

## 合规声明

本报告为数据分析 Demo，仅供学习与研究：

- 不构成任何投资建议
- 事件与价格窗口分析仅表明相关性，**相关不等于因果**
- 平台参考序列不等同于网签成交均价，存在滞后与口径差异
- 极端成交个案不代表整体市场

## License

Demo 项目，仅供学习与面试展示使用。
