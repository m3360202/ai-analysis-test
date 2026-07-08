import ReactECharts from "echarts-for-react";
import reportData from "./data/reportData.json";
import "./App.css";

const { summary, price_series, significant_mom, events, phases, event_impact, references, structural_notes, conclusion } =
  reportData;

const COLORS = {
  green: "#1A3C34",
  up: "#2E7D57",
  down: "#C0392B",
  flat: "#8B8378",
  accent: "#D4A574",
};

function fmtPrice(n: number) {
  return n.toLocaleString("zh-CN", { maximumFractionDigits: 0 });
}

function trendTag(pct: number) {
  if (pct > 0.3) return "pos";
  if (pct < -0.3) return "neg";
  return "neu";
}

function PriceLineChart({ showEvents = false }: { showEvents?: boolean }) {
  const months = price_series.map((d) => d.month);
  const prices = price_series.map((d) => d.ref_price);
  const indexLine = price_series.map((d) => d.index_base100);

  const eventMarks = showEvents
    ? events
        .filter((e) => {
          const m = e.date.slice(0, 7);
          return months.includes(m);
        })
        .slice(0, 8)
        .map((e) => ({
          name: e.event.slice(0, 8),
          coord: [e.date.slice(0, 7), prices[months.indexOf(e.date.slice(0, 7))]],
        }))
    : [];

  const option = {
    color: [COLORS.green, COLORS.accent],
    tooltip: {
      trigger: "axis",
      formatter: (params: { seriesName: string; data: number; axisValue: string }[]) => {
        const p = params[0];
        const idx = params[1];
        return `${p.axisValue}<br/>参考价：${fmtPrice(p.data)} 元/㎡<br/>定基指数：${idx?.data ?? "-"}`;
      },
    },
    legend: { data: ["板块月度参考价", "定基指数(2024-01=100)"], bottom: 0 },
    grid: { left: 56, right: 56, top: 40, bottom: 56 },
    xAxis: { type: "category", data: months, axisLabel: { rotate: 45, fontSize: 11 } },
    yAxis: [
      { type: "value", name: "元/㎡", scale: true },
      { type: "value", name: "定基指数", scale: true, min: 70, max: 105 },
    ],
    series: [
      {
        name: "板块月度参考价",
        type: "line",
        smooth: true,
        areaStyle: { color: "rgba(26,60,52,0.08)" },
        data: prices,
        markPoint: showEvents
          ? {
              data: eventMarks,
              symbol: "pin",
              symbolSize: 42,
              label: { fontSize: 10 },
            }
          : undefined,
      },
      {
        name: "定基指数(2024-01=100)",
        type: "line",
        yAxisIndex: 1,
        smooth: true,
        lineStyle: { type: "dashed" },
        data: indexLine,
      },
    ],
  };

  return <ReactECharts option={option} className="chart-box" />;
}

function MomBarChart() {
  const data = significant_mom;
  const option = {
    tooltip: { trigger: "axis" },
    grid: { left: 48, right: 24, top: 24, bottom: 48 },
    xAxis: { type: "category", data: data.map((d) => d.month), axisLabel: { rotate: 35 } },
    yAxis: { type: "value", name: "环比%" },
    series: [
      {
        type: "bar",
        data: data.map((d) => ({
          value: d.mom_pct,
          itemStyle: { color: (d.mom_pct ?? 0) >= 0 ? COLORS.up : COLORS.down },
        })),
        label: { show: true, position: "top", formatter: "{c}%" },
      },
    ],
  };
  return <ReactECharts option={option} className="chart-box sm" />;
}

function YoyLineChart() {
  const option = {
    tooltip: { trigger: "axis", formatter: "{b}<br/>同比：{c}%" },
    grid: { left: 48, right: 24, top: 24, bottom: 48 },
    xAxis: { type: "category", data: price_series.map((d) => d.month), axisLabel: { rotate: 45, fontSize: 11 } },
    yAxis: { type: "value", name: "同比%" },
    series: [
      {
        type: "line",
        smooth: true,
        data: price_series.map((d) => d.year_change),
        areaStyle: { color: "rgba(192,57,43,0.08)" },
        lineStyle: { color: COLORS.down },
        itemStyle: { color: COLORS.down },
      },
    ],
  };
  return <ReactECharts option={option} className="chart-box sm" />;
}

function EventTimeline() {
  const sorted = [...events].sort((a, b) => a.date.localeCompare(b.date));
  const start = summary.period_start;
  const end = summary.period_end;

  const scatterData = sorted.map((e) => {
    const levelMap: Record<string, number> = { 全国: 2, 北京: 1, 天通苑: 0 };
    const colorMap: Record<string, string> = { 利好: COLORS.up, 利空: COLORS.down, 中性: COLORS.flat };
    return {
      value: [e.date.slice(0, 7), levelMap[e.level] ?? 1],
      name: e.event,
      itemStyle: { color: colorMap[e.direction] ?? COLORS.flat },
      label: { show: false },
    };
  });

  const option = {
    tooltip: {
      trigger: "item",
      formatter: (p: { data: { name: string; value: string[] } }) => {
        const ev = sorted.find((e) => e.event === p.data.name);
        return ev ? `${ev.date}<br/>${ev.event}<br/>${ev.note}` : p.data.name;
      },
    },
    grid: { left: 80, right: 24, top: 24, bottom: 48 },
    xAxis: { type: "time", min: `${start}-01`, max: `${end}-28` },
    yAxis: {
      type: "category",
      data: ["天通苑本地", "北京楼市", "全国政策"],
      inverse: true,
    },
    series: [
      {
        type: "scatter",
        symbolSize: 14,
        data: scatterData,
      },
    ],
  };
  return <ReactECharts option={option} className="chart-box" />;
}

function PhaseBarChart() {
  const option = {
    tooltip: { trigger: "axis" },
    grid: { left: 48, right: 24, top: 24, bottom: 72 },
    xAxis: {
      type: "category",
      data: phases.map((p) => p.name.replace("：", "\n")),
      axisLabel: { interval: 0, fontSize: 11 },
    },
    yAxis: { type: "value", name: "阶段定基变化%" },
    series: [
      {
        type: "bar",
        data: phases.map((p) => ({
          value: p.change_pct,
          itemStyle: { color: p.change_pct >= 0 ? COLORS.up : COLORS.down },
        })),
        label: { show: true, position: "top", formatter: "{c}%" },
      },
    ],
  };
  return <ReactECharts option={option} className="chart-box sm" />;
}

function CoverSparkline() {
  const prices = price_series.map((d) => d.ref_price);
  const option = {
    grid: { left: 8, right: 8, top: 8, bottom: 8 },
    xAxis: { type: "category", show: false, data: price_series.map((d) => d.month) },
    yAxis: { type: "value", show: false, scale: true },
    series: [
      {
        type: "line",
        smooth: true,
        data: prices,
        lineStyle: { color: "#fff", width: 2 },
        areaStyle: { color: "rgba(255,255,255,0.15)" },
        symbol: "none",
      },
    ],
  };
  return <ReactECharts option={option} style={{ height: 120, width: "100%" }} />;
}

export default function App() {
  return (
    <div className="wrap">
      <header className="cover">
        <div>
          <div className="eyebrow">小区房价专项分析</div>
          <h1>北京天通苑 · 三年房价历史分析</h1>
          <p className="subtitle">
            {summary.period_start} — {summary.period_end} · 安居客板块参考序列与政策事件复盘（不含成交明细与舆情）
          </p>
          <div className="stat-row">
            <div className="stat-cell">
              <div className="k">最新参考价</div>
              <div className="v">{fmtPrice(summary.latest_ref_price)}</div>
              <div className="u">元/㎡（安居客板块序列）</div>
            </div>
            <div className="stat-cell">
              <div className="k">定基变化</div>
              <div className="v">
                {summary.fixed_base_change_pct}%
                <span className={`trend-tag ${trendTag(summary.fixed_base_change_pct)}`} style={{ marginLeft: 8 }}>
                  较{summary.base_month}
                </span>
              </div>
              <div className="u">基准 {summary.base_month}</div>
            </div>
            <div className="stat-cell">
              <div className="k">最新同比</div>
              <div className="v">{summary.latest_yoy_pct}%</div>
              <div className="u">{summary.period_end} 同比口径</div>
            </div>
            <div className="stat-cell">
              <div className="k">观测月份</div>
              <div className="v">{summary.month_count}</div>
              <div className="u">月度参考序列</div>
            </div>
          </div>
        </div>
        <div>
          <div style={{ fontSize: 13, opacity: 0.85, marginBottom: 8 }}>走势预览</div>
          <CoverSparkline />
        </div>
      </header>

      {/* Section 01 */}
      <section className="section">
        <div className="section-num">01</div>
        <div className="section-head">
          <div className="label">数据概览</div>
          <h2>天通苑板块价格全景摘要</h2>
          <p className="lead">
            基于安居客天通苑板块月度参考序列（2024-01 至 2026-07，共 {summary.month_count}{" "}
            个观测点），板块价格呈现「温和调整 → 加速筑底 → 弱修复」三阶段特征。定基口径（{summary.base_month}
            =100）累计变化 {summary.fixed_base_change_pct}%，反映市场回归理性与区域供需再平衡，临铁/非临铁、户型面积段存在显著结构性分化。
          </p>
        </div>
        <div className="stat-row" style={{ marginBottom: 24 }}>
          <div className="stat-cell light">
            <div className="k">分析周期</div>
            <div className="v">{summary.month_count} 个月</div>
          </div>
          <div className="stat-cell light">
            <div className="k">数据来源</div>
            <div className="v" style={{ fontSize: 16 }}>
              安居客
            </div>
          </div>
          <div className="stat-cell light">
            <div className="k">参考价区间</div>
            <div className="v" style={{ fontSize: 16 }}>
              {fmtPrice(summary.price_range_low)}~{fmtPrice(summary.price_range_high)}
            </div>
          </div>
          <div className="stat-cell light">
            <div className="k">最大单月环比跌幅</div>
            <div className="v">
              {summary.max_mom_drop.mom_pct}%{" "}
              <span className="trend-tag neg">{summary.max_mom_drop.month}</span>
            </div>
          </div>
        </div>
        <div className="prose">
          <p>
            2024 年，在「房住不炒」总基调下，板块参考序列延续温和下行，全年定基跌幅约 10.5%，体现结构性调整而非单边恐慌。
            2025 年政策密集出台（利率下调、五环外限购松绑、公积金优化），但政策效果存在滞后性，序列于四季度筑底。
            2026 年上半年，随着存量公积金降息兑现、第三轮回天行动计划发布及奥北中学建设推进，参考序列较年初低点小幅回升，呈现弱修复态势。
          </p>
        </div>
        <div className="pull">
          <h3>三年主线：政策预期与配套落地交织，板块呈现结构性调整</h3>
          <p>
            认房不认贷与 2024 年四季度政策组合拳一度稳定市场预期，但区域供需失衡与大型社区挂牌存量使得调整周期延长；17/18
            号线贯通与城市更新则为天通苑作为北京最大居住社区提供中长期支撑。
          </p>
        </div>
      </section>

      {/* Section 02 */}
      <section className="section">
        <div className="section-num">02</div>
        <div className="section-head">
          <div className="label">价格走势</div>
          <h2>月度参考价曲线与定基指数</h2>
          <p className="lead">
            展示安居客天通苑板块月度参考价及定基指数（{summary.base_month}=100）。分析采用同比/定基口径，避免以历史极值直接对比误导读者。
          </p>
        </div>
        <div className="panel">
          <PriceLineChart />
          <div className="panel-caption">
            数据来源：安居客板块月度参考序列，抓取时间 {summary.fetch_time}。该序列由平台算法汇总，不等同于网签成交均价，存在滞后与口径差异。
          </div>
        </div>
        <h3 className="sub">2.1 同比变化趋势</h3>
        <div className="panel">
          <YoyLineChart />
          <div className="panel-caption">同比降幅自 2024 年逐步收窄，2026 年上半年同比约 -8% 至 -11% 区间，显示筑底特征。</div>
        </div>
        <h3 className="sub">2.2 显著环比波动月份（|环比|≥1.5%）</h3>
        <div className="panel">
          <MomBarChart />
        </div>
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>月份</th>
                <th>参考价（元/㎡）</th>
                <th>环比</th>
                <th>同比</th>
                <th>定基指数</th>
              </tr>
            </thead>
            <tbody>
              {price_series.map((row) => (
                <tr key={row.month}>
                  <td>{row.month}</td>
                  <td>{fmtPrice(row.ref_price)}</td>
                  <td>
                    {row.mom_pct == null ? "—" : (
                      <span className={`trend-tag ${trendTag(row.mom_pct)}`}>{row.mom_pct}%</span>
                    )}
                  </td>
                  <td>
                    <span className={`trend-tag ${trendTag(row.year_change)}`}>{row.year_change}%</span>
                  </td>
                  <td>{row.index_base100}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 03 */}
      <section className="section">
        <div className="section-num">03</div>
        <div className="section-head">
          <div className="label">事件时间线</div>
          <h2>三年影响预期的关键事件与文件</h2>
          <p className="lead">梳理全国、北京市、天通苑本地三个层级中对市场预期与板块走势产生显著影响的事件（共 {events.length} 条）。</p>
        </div>
        <div className="panel">
          <EventTimeline />
        </div>
        <h3 className="sub">3.1 事件清单</h3>
        <div className="panel" style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>事件</th>
                <th>层级</th>
                <th>类型</th>
                <th>方向</th>
                <th>摘要</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.date + e.event}>
                  <td>{e.date}</td>
                  <td>{e.event}</td>
                  <td>{e.level}</td>
                  <td>{e.type}</td>
                  <td>
                    <span className={`dir-badge ${e.direction}`}>{e.direction}</span>
                  </td>
                  <td>{e.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h3 className="sub">3.2 事件分级说明</h3>
        <ul className="bullet-list">
          <li>
            <strong>预期型</strong>：认房不认贷、限购松绑、LPR 下调等，主要影响购房意愿与市场预期，传导至成交存在时滞。
          </li>
          <li>
            <strong>落地型</strong>：17/18 号线开通、老旧小区改造、加装电梯等，改善居住体验，体现为结构性分化而非整体跳涨。
          </li>
          <li>
            <strong>分流型</strong>：保障房、共有产权房体系对刚需客群形成分流，需与商品房市场分开评估。
          </li>
          <li>
            <strong>个案型</strong>：法拍折价成交等极端案例，对议价心理有下拉参照，但不代表普遍成交水平。
          </li>
        </ul>
      </section>

      {/* Section 04 */}
      <section className="section">
        <div className="section-num">04</div>
        <div className="section-head">
          <div className="label">宏观归因</div>
          <h2>政策事件与价格拐点的对应关系</h2>
          <p className="lead">
            将月度参考序列与关键事件对齐，观察事件窗口前后的价格反应。<strong>声明：相关不等于因果。</strong>
          </p>
        </div>
        <div className="panel">
          <PriceLineChart showEvents />
        </div>
        <h3 className="sub">4.1 阶段划分</h3>
        <div className="phase-grid">
          {phases.map((p) => (
            <div className="phase-card" key={p.name}>
              <h4>{p.name}</h4>
              <div className="meta">{p.range}</div>
              <div className={`chg trend-tag ${trendTag(p.change_pct)}`}>{p.change_pct}%</div>
              <div className="meta">关联事件：{p.related_events.join("；")}</div>
              <p style={{ margin: 0, fontSize: 14 }}>{p.summary}</p>
            </div>
          ))}
        </div>
        <div className="pull">
          <h3>归因观察</h3>
          <p>
            2023 下半年至 2024 年初：认房不认贷释放置换需求，板块参考序列短暂企稳；2024 全年：预期走弱叠加挂牌增加，序列承压下行；2025
            年：政策效果存在滞后性，五环外松绑后成交量预期改善，但价格仍处筑底；2026 年上半年：配套预期升温，弱修复迹象显现。
          </p>
        </div>
        <h3 className="sub">4.2 归因矩阵（事件窗口观测）</h3>
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>事件</th>
                <th>事件后 1 月</th>
                <th>事件后 3 月</th>
                <th>价格反应</th>
                <th>置信度</th>
              </tr>
            </thead>
            <tbody>
              {event_impact.map((row) => (
                <tr key={row.event}>
                  <td>{row.event}</td>
                  <td>{row.after_1m_pct}%</td>
                  <td>{row.after_3m_pct}%</td>
                  <td>{row.reaction}</td>
                  <td>{row.confidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 05 - replaced with structural analysis */}
      <section className="section">
        <div className="section-num">05</div>
        <div className="section-head">
          <div className="label">结构拆解</div>
          <h2>结构性分化与数据边界说明</h2>
          <p className="lead">
            本次报告不使用成交明细与舆情爬取。以下从户型、临铁、保障房分流等维度说明板块内部结构，避免以单一参考序列掩盖分化。
          </p>
        </div>
        <div className="stat-row" style={{ marginBottom: 24 }}>
          <div className="stat-cell light">
            <div className="k">数据口径</div>
            <div className="v" style={{ fontSize: 15 }}>
              板块月度参考序列
            </div>
          </div>
          <div className="stat-cell light">
            <div className="k">成交明细</div>
            <div className="v" style={{ fontSize: 15 }}>
              本次未纳入
            </div>
          </div>
          <div className="stat-cell light">
            <div className="k">舆情数据</div>
            <div className="v" style={{ fontSize: 15 }}>
              本次未纳入
            </div>
          </div>
          <div className="stat-cell light">
            <div className="k">网签滞后</div>
            <div className="v" style={{ fontSize: 15 }}>
              已注明
            </div>
          </div>
        </div>
        <div className="phase-grid">
          {structural_notes.map((n) => (
            <div className="phase-card" key={n.dimension}>
              <h4>{n.dimension}</h4>
              <p style={{ margin: 0, fontSize: 14 }}>{n.description}</p>
            </div>
          ))}
        </div>
        <div className="pull">
          <h3>数据边界声明</h3>
          <p>{summary.disclaimer}</p>
        </div>
        <h3 className="sub">5.1 权威引用索引</h3>
        <ul className="ref-list">
          {references.map((r) => (
            <li key={r.url}>
              <span className={`dir-badge ${r.type === "官方" ? "利好" : "中性"}`}>{r.type}</span>{" "}
              <a href={r.url} target="_blank" rel="noreferrer">
                {r.title}
              </a>
            </li>
          ))}
        </ul>
      </section>

      {/* Section 06 */}
      <section className="section">
        <div className="section-num">06</div>
        <div className="section-head">
          <div className="label">阶段涨跌</div>
          <h2>阶段性定基变化拆解</h2>
          <p className="lead">以定基口径划分阶段涨跌幅，解释各时段价格调整节奏与主要因素，不使用极值成交对比。</p>
        </div>
        <div className="panel">
          <PhaseBarChart />
        </div>
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>阶段</th>
                <th>起止</th>
                <th>参考价起</th>
                <th>参考价止</th>
                <th>涨跌%</th>
                <th>主要解释</th>
              </tr>
            </thead>
            <tbody>
              {phases.map((p) => (
                <tr key={p.name}>
                  <td>{p.name}</td>
                  <td>{p.range}</td>
                  <td>{fmtPrice(p.start_price)}</td>
                  <td>{fmtPrice(p.end_price)}</td>
                  <td>
                    <span className={`trend-tag ${trendTag(p.change_pct)}`}>{p.change_pct}%</span>
                  </td>
                  <td>{p.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 07 */}
      <section className="section">
        <div className="section-num">07</div>
        <div className="section-head">
          <div className="label">结论展望</div>
          <h2>综合判断与后续关注</h2>
          <p className="lead">审慎、可辩护的中性结论，不构成投资建议，不预测政策走向。</p>
        </div>
        <div className="pull accent">
          <h3>{conclusion.headline}</h3>
          <p>{conclusion.template}</p>
        </div>
        <h3 className="sub">7.1 核心发现</h3>
        <ol className="bullet-list">
          {conclusion.findings.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ol>
        <h3 className="sub">7.2 后续 6~12 个月关注项（基于已出台政策与规划）</h3>
        <ul className="bullet-list">
          {conclusion.watchlist.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
        <h3 className="sub">7.3 风险提示</h3>
        <ul className="bullet-list">
          {conclusion.risks.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </section>

      {/* Section 08 */}
      <section className="section">
        <div className="section-num">08</div>
        <div className="section-head">
          <div className="label">方法说明</div>
          <h2>数据来源、处理流程与局限</h2>
          <p className="lead">保证报告可追溯、可复现，体现工程与合规意识。</p>
        </div>
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>数据</th>
                <th>来源</th>
                <th>抓取时间</th>
                <th>用途</th>
                <th>备注</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>板块月度参考价</td>
                <td>安居客</td>
                <td>2026-07-08</td>
                <td>主价格序列</td>
                <td>平台算法汇总，非网签成交均价</td>
              </tr>
              <tr>
                <td>成交明细</td>
                <td>链家</td>
                <td>2026-07-08</td>
                <td>原计划交叉验证</td>
                <td>因验证码拦截未纳入本次报告</td>
              </tr>
              <tr>
                <td>政策/事件</td>
                <td>官方发布 + 权威媒体</td>
                <td>人工整理</td>
                <td>事件时间轴与归因</td>
                <td>共 24 条，含来源链接</td>
              </tr>
              <tr>
                <td>舆情</td>
                <td>微博/小红书</td>
                <td>—</td>
                <td>联动分析</td>
                <td>本次时间关系未纳入</td>
              </tr>
            </tbody>
          </table>
        </div>
        <h3 className="sub">处理流程</h3>
        <pre style={{ background: "#faf9f7", padding: 16, borderRadius: 8, fontSize: 13, overflow: "auto" }}>
          {`爬虫 raw（安居客）→ analysis/prepare_report_data.py → reportData.json → React+Vite 构建 → 静态 HTML`}
        </pre>
        <h3 className="sub">方法与局限</h3>
        <ul className="bullet-list">
          <li>价格序列按月聚合，采用定基（2024-01=100）与同比口径，避免极值误导。</li>
          <li>安居客参考序列与真实成交存在口径差异，网签存在 1~3 个月滞后，个别阴阳合同可能影响样本。</li>
          <li>事件窗口分析仅表明相关性，相关不等于因果。</li>
          <li>法拍等极端成交不代表普遍市场，结论强调结构性分化。</li>
          <li>本报告仅使用公开数据，不构成任何投资建议。</li>
        </ul>
      </section>

      <div className="footer-note">
        报告生成日期：{summary.report_date} · 数据抓取：{summary.fetch_time} · 北京天通苑房价历史分析 Demo
      </div>
    </div>
  );
}
