const state = {
  universe: [],
  groups: [],
  activeGroup: "全部",
  activeCode: "510310",
  payload: null,
  rows: [],
  disclosures: [],
  full: null,
  view: null,
  zoomDrag: null,
  axisPan: null,
  trendRequestId: 0,
};

const DAY_MS = 24 * 60 * 60 * 1000;
const MIN_VIEW_MS = 7 * DAY_MS;
const fmt = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 });
const priceFmt = new Intl.NumberFormat("zh-CN", { minimumFractionDigits: 3, maximumFractionDigits: 3 });

const els = {
  pageTitle: document.getElementById("pageTitle"),
  metaLine: document.getElementById("metaLine"),
  groupSelect: document.getElementById("groupSelect"),
  etfSelect: document.getElementById("etfSelect"),
  refreshBtn: document.getElementById("refreshBtn"),
  resetZoomBtn: document.getElementById("resetZoomBtn"),
  etfList: document.getElementById("etfList"),
  chartStack: document.querySelector(".chart-stack"),
  charts: Array.from(document.querySelectorAll(".chart")),
  tooltip: document.getElementById("tooltip"),
  statusLine: document.getElementById("statusLine"),
  mDate: document.getElementById("mDate"),
  mPrice: document.getElementById("mPrice"),
  mTurnover: document.getElementById("mTurnover"),
  mShares: document.getElementById("mShares"),
  mHoldingRatio: document.getElementById("mHoldingRatio"),
  mHoldingValue: document.getElementById("mHoldingValue"),
  trendPanel: document.getElementById("trendPanel"),
  trendTitle: document.getElementById("trendTitle"),
  trendMeta: document.getElementById("trendMeta"),
  trendTableBody: document.getElementById("trendTableBody"),
  trendPopoutBtn: document.getElementById("trendPopoutBtn"),
  trendBackdrop: document.getElementById("trendBackdrop"),
};

const trendGroupMap = {
  "宽基/沪深300": "hs300",
  "宽基/上证50": "sse50",
  "宽基/上证180": "sse180",
  "宽基/中证500": "csi500",
  "宽基/中证800": "csi800",
  "宽基/中证1000": "csi1000",
  "宽基/创业板": "chinext",
  "宽基/科创50": "star50",
  "宽基/深证100": "sz100",
};

const chartConfig = {
  price: {
    title: "日线价格走势",
    key: "price",
    benchmarkKey: "benchmark",
    kind: "line",
    format: (value) => priceFmt.format(value),
  },
  turnover: {
    title: "日度 ETF 成交额",
    key: "turnover",
    kind: "bar",
    floorZero: true,
    format: (value) => `${fmt.format(value)} 亿`,
  },
  shares: {
    title: "日线 ETF 份额走势",
    key: "shares",
    kind: "line",
    format: (value) => `${fmt.format(value)} 亿份`,
  },
  flow: {
    title: "日度 ETF 申购赎回份额",
    key: "flow",
    kind: "signedBar",
    symmetric: true,
    format: (value) => `${fmt.format(value)} 亿份`,
  },
};

function defined(value) {
  return value !== null && value !== undefined && Number.isFinite(Number(value));
}

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  return node;
}

function setStatus(text) {
  els.statusLine.textContent = text || "";
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function latestRowWith(key) {
  for (let i = state.rows.length - 1; i >= 0; i -= 1) {
    if (defined(state.rows[i][key])) return state.rows[i];
  }
  return null;
}

function latestDisclosure() {
  if (!state.disclosures.length) return null;
  return state.disclosures.slice().sort((a, b) => a.t - b.t).at(-1);
}

function updateMetrics() {
  const meta = { ...(state.payload?.meta || {}), ...(activeEtfMeta() || {}) };
  const latestPrice = latestRowWith("price");
  const latestTurnover = latestRowWith("turnover");
  const latestShares = latestRowWith("shares");
  const disclosure = latestDisclosure();
  const latestDate = latestPrice?.date || latestShares?.date || meta.latest_series_date || "-";
  els.mDate.textContent = latestDate;
  els.mPrice.textContent = latestPrice ? priceFmt.format(latestPrice.price) : "-";
  els.mTurnover.textContent = latestTurnover ? `${fmt.format(latestTurnover.turnover)} 亿元` : "-";
  els.mShares.textContent = latestShares ? `${fmt.format(latestShares.shares)} 亿份` : "-";
  els.mHoldingRatio.textContent = defined(meta.latest_combined_ratio_pct) ? `${fmt.format(meta.latest_combined_ratio_pct)}%` : "-";
  els.mHoldingValue.textContent = defined(meta.latest_combined_value_yi) ? `${fmt.format(meta.latest_combined_value_yi)} 亿元` : "-";
  if (disclosure?.ratioText) {
    els.mHoldingRatio.textContent = disclosure.ratioText;
  }
  if (defined(disclosure?.combinedValue)) {
    els.mHoldingValue.textContent = `${fmt.format(disclosure.combinedValue)} 亿元`;
  }
}

function formatSignedPct(value, digits = 2) {
  if (!defined(value)) return "-";
  const number = Number(value);
  return `${number > 0 ? "+" : ""}${number.toFixed(digits)}%`;
}

function formatSignedNumber(value, suffix = "", digits = 2) {
  if (!defined(value)) return "-";
  const number = Number(value);
  return `${number > 0 ? "+" : ""}${number.toFixed(digits)}${suffix}`;
}

function signedClass(value) {
  if (!defined(value)) return "";
  const number = Number(value);
  if (number > 0) return "cell-positive";
  if (number < 0) return "cell-negative";
  return "";
}

function percentileChip(value) {
  if (!defined(value)) return "-";
  const number = Number(value);
  const extra = number >= 80 ? " is-high" : number <= 20 ? " is-low" : "";
  return `<span class="percentile-chip${extra}">${number.toFixed(1)}%</span>`;
}

function renderTrendBoard(payload) {
  const meta = payload.meta || {};
  const title = `${meta.index_name || "当前分组"}最近一周趋势`;
  els.trendTitle.textContent = title;
  els.trendPanel.setAttribute("aria-label", `${title}看板`);
  const percentileStart = meta.percentile_start_date ? `分位基准：${meta.percentile_start_date}之后` : "";
  els.trendMeta.textContent = `${meta.date_start || "-"} 至 ${meta.date_end || "-"} · ${percentileStart} · ${meta.denominator_note || ""}`;
  const rows = payload.rows || [];
  if (!rows.length) {
    els.trendTableBody.innerHTML = '<tr><td colspan="9">暂无数据</td></tr>';
    return;
  }
  let lastGroupKey = "";
  els.trendTableBody.innerHTML = rows
    .map((row) => {
      const isAggregate = row.row_type === "aggregate";
      const name = isAggregate
        ? row.name
        : `<button type="button" class="trend-row-button" data-trend-code="${row.code}">${row.code} ${row.name}</button>`;
      const deltaText = isAggregate ? "金额口径" : formatSignedNumber(row.delta_units_yi, " 亿份", 2);
      const groupKey = isAggregate ? "aggregate" : row.code;
      const isGroupStart = groupKey !== lastGroupKey;
      lastGroupKey = groupKey;
      const rowClass = `${isAggregate ? "aggregate-row" : ""}${isGroupStart ? " trend-group-start" : ""}`.trim();
      return `
        <tr class="${rowClass}">
          <td>${name}</td>
          <td>${row.date}</td>
          <td class="${signedClass(row.price_change_pct)}">${formatSignedPct(row.price_change_pct, 2)}</td>
          <td>${defined(row.turnover_yi) ? `${fmt.format(row.turnover_yi)} 亿` : "-"}</td>
          <td>${percentileChip(row.turnover_percentile)}</td>
          <td class="${signedClass(row.delta_units_yi)}">${deltaText}</td>
          <td>${percentileChip(row.delta_units_percentile)}</td>
          <td class="${signedClass(row.flow_amount_yi)}">${formatSignedNumber(row.flow_amount_yi, " 亿", 2)}</td>
          <td class="${signedClass(row.flow_amount_to_index_turnover_pct)}">${formatSignedPct(row.flow_amount_to_index_turnover_pct, 2)}</td>
        </tr>
      `;
    })
    .join("");
}

function handleTrendTableClick(event) {
  const button = event.target.closest("[data-trend-code]");
  if (!button) return;
  const code = button.dataset.trendCode;
  const item = state.universe.find((row) => row.code === code);
  if (item?.display_group && state.activeGroup !== item.display_group) {
    state.activeGroup = item.display_group;
    renderSelectors();
    loadTrendBoard();
  }
  selectEtf(code);
}

function setTrendPopout(open) {
  els.trendPanel.classList.toggle("is-expanded", open);
  document.body.classList.toggle("trend-popout-open", open);
  els.trendBackdrop.hidden = !open;
  els.trendPopoutBtn.textContent = open ? "收起" : "展开";
  els.trendPopoutBtn.setAttribute("aria-expanded", String(open));
  if (open) {
    els.trendPanel.setAttribute("role", "dialog");
    els.trendPanel.setAttribute("aria-modal", "true");
  } else {
    els.trendPanel.removeAttribute("role");
    els.trendPanel.removeAttribute("aria-modal");
  }
}

function toggleTrendPopout() {
  setTrendPopout(!els.trendPanel.classList.contains("is-expanded"));
}

function activeTrendGroup() {
  if (state.activeGroup !== "全部") return state.activeGroup;
  return activeEtfMeta()?.display_group || state.universe.find((item) => item.dashboard_eligible)?.display_group || "";
}

function trendLabelForGroup(group) {
  if (!group) return "当前分组";
  return group.includes("/") ? group.split("/").at(-1) : group;
}

function renderUnsupportedTrendBoard(group) {
  const label = trendLabelForGroup(group);
  const title = `${label}最近一周趋势`;
  els.trendTitle.textContent = title;
  els.trendPanel.setAttribute("aria-label", `${title}看板`);
  els.trendMeta.textContent = "这个分组暂未配置指数趋势表；切到已配置的宽基指数分组后会自动显示。";
  els.trendTableBody.innerHTML = '<tr><td colspan="9">暂无趋势表</td></tr>';
}

async function loadTrendBoard() {
  const requestId = state.trendRequestId + 1;
  state.trendRequestId = requestId;
  const group = activeTrendGroup();
  const indexKey = trendGroupMap[group];
  const label = trendLabelForGroup(group);
  els.trendTitle.textContent = `${label}最近一周趋势`;
  els.trendPanel.setAttribute("aria-label", `${label}最近一周趋势看板`);
  if (!indexKey) {
    renderUnsupportedTrendBoard(group);
    return;
  }
  els.trendMeta.textContent = "读取趋势表中";
  els.trendTableBody.innerHTML = '<tr><td colspan="9">读取中</td></tr>';
  try {
    const payload = await fetchJson(`data/trends/${indexKey}_recent_week.json`);
    if (requestId !== state.trendRequestId) return;
    renderTrendBoard(payload);
  } catch (error) {
    if (requestId !== state.trendRequestId) return;
    els.trendMeta.textContent = `趋势表读取失败：${error.message}`;
    els.trendTableBody.innerHTML = '<tr><td colspan="9">读取失败</td></tr>';
  }
}

function filteredUniverse() {
  if (state.activeGroup === "全部") return state.universe;
  return state.universe.filter((item) => item.display_group === state.activeGroup);
}

function renderSelectors() {
  const groups = ["全部", ...state.groups.map((item) => item.group)];
  els.groupSelect.innerHTML = groups.map((group) => `<option value="${group}">${group}</option>`).join("");
  els.groupSelect.value = state.activeGroup;
  renderEtfOptions();
}

function renderEtfOptions() {
  const items = filteredUniverse();
  els.etfSelect.innerHTML = items
    .map((item) => {
      const suffix = item.dashboard_eligible ? "" : " · 缺份额";
      return `<option value="${item.code}">${item.code} ${item.name}${suffix}</option>`;
    })
    .join("");
  if (!items.some((item) => item.code === state.activeCode)) {
    const fallback = items.find((item) => item.dashboard_eligible) || items[0];
    if (fallback) state.activeCode = fallback.code;
  }
  els.etfSelect.value = state.activeCode;
  renderEtfList();
}

function renderEtfList() {
  const items = filteredUniverse();
  els.etfList.innerHTML = "";
  for (const item of items) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `etf-row${item.code === state.activeCode ? " is-active" : ""}`;
    button.dataset.code = item.code;
    button.innerHTML = `
      <span class="etf-name">${item.name}</span>
      <span class="etf-code">${item.code}</span>
      <span class="etf-note">${fmt.format(item.latest_combined_ratio_pct || 0)}% · ${fmt.format(item.latest_combined_value_yi || 0)} 亿</span>
      <span class="etf-note">${item.dashboard_eligible ? item.display_group : "待补份额"}</span>
    `;
    button.addEventListener("click", () => selectEtf(item.code));
    els.etfList.appendChild(button);
  }
}

function activeEtfMeta() {
  return state.universe.find((item) => item.code === state.activeCode) || null;
}

function parsePayload(payload) {
  state.payload = payload;
  state.rows = (payload.series || [])
    .map((row) => {
      const t = new Date(`${row.date}T00:00:00`).getTime();
      return {
        date: row.date,
        t,
        price: defined(row.etf_qfq_close) ? Number(row.etf_qfq_close) : null,
        turnover: defined(row.etf_qfq_turnover_est_yi) ? Number(row.etf_qfq_turnover_est_yi) : null,
        shares: defined(row.qfq_total_units_yi) ? Number(row.qfq_total_units_yi) : null,
        flow: defined(row.qfq_delta_units_yi) ? Number(row.qfq_delta_units_yi) : null,
        benchmark: defined(row.benchmark_close) ? Number(row.benchmark_close) : null,
      };
    })
    .filter((row) => Number.isFinite(row.t))
    .sort((a, b) => a.t - b.t);

  state.disclosures = (payload.disclosures || [])
    .map((row) => {
      const day = row.report_date || row.date;
      const ratio = row.combined_ratio_pct ?? row.ratio;
      const value = row.combined_value_yi ?? row.value_yi;
      return {
        date: day,
        t: new Date(`${day}T00:00:00`).getTime(),
        ratio,
        ratioText: defined(ratio) ? `${fmt.format(Number(ratio))}%` : null,
        combinedValue: defined(value) ? Number(value) : null,
        totalShares: defined(row.total_shares_yi_qfq) ? Number(row.total_shares_yi_qfq) : null,
      };
    })
    .filter((row) => Number.isFinite(row.t))
    .sort((a, b) => a.t - b.t);

  if (state.rows.length) {
    const minT = Math.min(...state.rows.map((row) => row.t));
    const maxT = Math.max(...state.rows.map((row) => row.t));
    state.full = { minT, maxT };
    state.view = { minT, maxT };
  } else {
    state.full = null;
    state.view = null;
  }
  updateZoomButton();
  updateHeader();
  updateMetrics();
}

function updateHeader() {
  const meta = { ...(state.payload?.meta || {}), ...(activeEtfMeta() || {}) };
  els.pageTitle.textContent = `${meta.code || state.activeCode} ${meta.name || ""}`.trim();
  const bits = [
    meta.display_group,
    meta.latest_report_date ? `披露日 ${meta.latest_report_date}` : null,
    meta.data_refreshed_at ? `刷新 ${meta.data_refreshed_at}` : null,
  ].filter(Boolean);
  els.metaLine.textContent = bits.join(" · ") || "证金汇金 ETF 持仓 Dashboard";
}

async function selectEtf(code) {
  state.activeCode = code;
  els.etfSelect.value = code;
  renderEtfList();
  if (state.activeGroup === "全部") loadTrendBoard();
  setStatus("读取 ETF 数据中");
  try {
    const payload = await fetchJson(`data/etfs/${code}.json`);
    parsePayload(payload);
    draw();
    const meta = payload.meta || {};
    if (!meta.dashboard_eligible || !state.rows.some((row) => defined(row.shares))) {
      setStatus("这只 ETF 已在持仓名单中，但日度份额数据还在 backfill 队列里。");
    } else {
      setStatus("");
    }
  } catch (error) {
    clearCharts();
    setStatus(`读取失败：${error.message}`);
  }
}

function clearCharts() {
  for (const chart of els.charts) {
    chart.querySelector("svg").innerHTML = "";
  }
}

function minMax(items, key, options = {}) {
  const values = items.map((item) => item[key]).filter(defined).map(Number);
  if (!values.length) return [0, 1];
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (options.floorZero) min = Math.min(0, min);
  if (options.symmetric) {
    const abs = Math.max(Math.abs(min), Math.abs(max));
    min = -abs;
    max = abs;
  }
  if (min === max) {
    min -= Math.abs(min || 1) * 0.1;
    max += Math.abs(max || 1) * 0.1;
  }
  const pad = (max - min) * 0.08;
  return [min - pad, max + pad];
}

function niceTicks(min, max, count = 4) {
  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) return [min || 0];
  const raw = (max - min) / Math.max(1, count - 1);
  const pow = Math.pow(10, Math.floor(Math.log10(Math.abs(raw))));
  const mult = raw / pow;
  const step = (mult <= 1 ? 1 : mult <= 2 ? 2 : mult <= 5 ? 5 : 10) * pow;
  const start = Math.ceil(min / step) * step;
  const ticks = [];
  for (let value = start; value <= max + step * 0.5; value += step) {
    ticks.push(value);
  }
  return ticks.slice(0, 6);
}

function addMonths(dateValue, count) {
  const date = new Date(dateValue);
  date.setMonth(date.getMonth() + count);
  return date;
}

function tickLabel(tick, unit) {
  const date = new Date(tick);
  const yy = String(date.getFullYear()).slice(2);
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  if (unit === "quarter") return `${yy}Q${Math.floor(date.getMonth() / 3) + 1}`;
  if (unit === "month") return `${yy}-${mm}`;
  return `${mm}-${dd}`;
}

function xTicks(minT, maxT, innerW) {
  const rangeDays = Math.max(1, (maxT - minT) / DAY_MS);
  const maxLabels = Math.max(2, Math.floor(innerW / 54));
  let unit = "quarter";
  let cursor;
  let advance;
  const start = new Date(minT);
  if (rangeDays > 400) {
    const quarterMonth = Math.floor(start.getMonth() / 3) * 3;
    cursor = new Date(start.getFullYear(), quarterMonth, 1);
    advance = (date) => addMonths(date, 3);
  } else if (rangeDays > 120) {
    unit = "month";
    cursor = new Date(start.getFullYear(), start.getMonth(), 1);
    advance = (date) => addMonths(date, 1);
  } else if (rangeDays > 28) {
    unit = "week";
    const weekday = (start.getDay() + 6) % 7;
    cursor = new Date(start.getFullYear(), start.getMonth(), start.getDate() - weekday);
    advance = (date) => new Date(date.getTime() + 7 * DAY_MS);
  } else {
    unit = "day";
    cursor = new Date(start.getFullYear(), start.getMonth(), start.getDate());
    advance = (date) => new Date(date.getTime() + DAY_MS);
  }
  while (cursor.getTime() < minT) cursor = advance(cursor);
  const ticks = [];
  while (cursor.getTime() <= maxT) {
    ticks.push({ t: cursor.getTime(), label: tickLabel(cursor.getTime(), unit) });
    cursor = advance(cursor);
  }
  if (!ticks.length) ticks.push({ t: minT + (maxT - minT) / 2, label: tickLabel(minT + (maxT - minT) / 2, unit) });
  const step = Math.max(1, Math.ceil(ticks.length / maxLabels));
  return ticks.filter((_, idx) => idx % step === 0);
}

function linePath(items, x, y, key) {
  let path = "";
  let open = false;
  for (const item of items) {
    if (!defined(item[key])) {
      open = false;
      continue;
    }
    path += `${open ? "L" : "M"}${x(item.t).toFixed(2)},${y(Number(item[key])).toFixed(2)}`;
    open = true;
  }
  return path;
}

function nearestRow(targetT) {
  const pool = state.rows.filter((row) => row.t >= state.view.minT && row.t <= state.view.maxT);
  const rows = pool.length ? pool : state.rows;
  let best = rows[0];
  let dist = Math.abs(targetT - best.t);
  for (const row of rows) {
    const next = Math.abs(targetT - row.t);
    if (next < dist) {
      best = row;
      dist = next;
    }
  }
  return best;
}

function nearestShare(rowT) {
  let best = null;
  let dist = Infinity;
  for (const row of state.rows) {
    if (!defined(row.shares)) continue;
    const next = Math.abs(row.t - rowT);
    if (next < dist) {
      best = row;
      dist = next;
    }
  }
  return best;
}

function clampView(minT, maxT) {
  if (!state.full) return { minT, maxT };
  let lo = Math.min(minT, maxT);
  let hi = Math.max(minT, maxT);
  const fullRange = state.full.maxT - state.full.minT;
  let range = Math.max(hi - lo, MIN_VIEW_MS);
  if (range >= fullRange) return { minT: state.full.minT, maxT: state.full.maxT };
  if (lo < state.full.minT) {
    lo = state.full.minT;
    hi = lo + range;
  }
  if (hi > state.full.maxT) {
    hi = state.full.maxT;
    lo = hi - range;
  }
  return { minT: lo, maxT: hi };
}

function isFullView() {
  if (!state.full || !state.view) return true;
  return Math.abs(state.full.minT - state.view.minT) < 1000 && Math.abs(state.full.maxT - state.view.maxT) < 1000;
}

function updateZoomButton() {
  els.resetZoomBtn.disabled = isFullView();
}

function setView(minT, maxT) {
  state.view = clampView(minT, maxT);
  updateZoomButton();
  draw();
}

function resetZoom() {
  if (!state.full) return;
  state.view = { ...state.full };
  updateZoomButton();
  draw();
}

function drawAxis(svg, cs, y, minY, maxY, showX) {
  const ticks = niceTicks(minY, maxY, 4);
  for (const tick of ticks) {
    const yy = y(tick);
    svg.appendChild(svgEl("line", { x1: cs.left, x2: cs.left + cs.innerW, y1: yy, y2: yy, class: "grid-line" }));
    const label = svgEl("text", { x: cs.left - 8, y: yy + 4, "text-anchor": "end", class: "chart-label" });
    label.textContent = fmt.format(tick);
    svg.appendChild(label);
  }
  svg.appendChild(svgEl("line", { x1: cs.left, x2: cs.left, y1: cs.top, y2: cs.top + cs.innerH, class: "axis-line" }));
  svg.appendChild(svgEl("line", { x1: cs.left, x2: cs.left + cs.innerW, y1: cs.top + cs.innerH, y2: cs.top + cs.innerH, class: "axis-line" }));
  if (!showX) return;
  for (const tick of xTicks(state.view.minT, state.view.maxT, cs.innerW)) {
    const xx = cs.x(tick.t);
    svg.appendChild(svgEl("line", { x1: xx, x2: xx, y1: cs.top + cs.innerH, y2: cs.top + cs.innerH + 5, class: "axis-line" }));
    const label = svgEl("text", { x: xx, y: cs.top + cs.innerH + 21, "text-anchor": "middle", class: "chart-label" });
    label.textContent = tick.label;
    svg.appendChild(label);
  }
}

function drawBars(svg, visible, cs, y, key, signed = false) {
  const values = visible.filter((row) => defined(row[key]));
  if (!values.length) return;
  const barW = Math.max(1, Math.min(18, (cs.innerW / Math.max(1, visible.length)) * 0.72));
  const zeroY = signed ? y(0) : cs.top + cs.innerH;
  for (const row of values) {
    const value = Number(row[key]);
    const xx = cs.x(row.t) - barW / 2;
    const yy = signed ? Math.min(y(value), zeroY) : y(value);
    const height = Math.max(1, Math.abs(zeroY - y(value)));
    svg.appendChild(
      svgEl("rect", {
        x: xx,
        y: yy,
        width: barW,
        height,
        class: signed ? (value >= 0 ? "bar-positive" : "bar-negative") : "bar-turnover",
      }),
    );
  }
  if (signed) {
    svg.appendChild(svgEl("line", { x1: cs.left, x2: cs.left + cs.innerW, y1: zeroY, y2: zeroY, class: "zero-line" }));
  }
}

function drawDisclosureMarkers(svg, cs, y) {
  const markers = state.disclosures.filter((item) => item.t >= state.view.minT && item.t <= state.view.maxT);
  for (const item of markers) {
    const shareRow = nearestShare(item.t);
    if (!shareRow || !defined(shareRow.shares)) continue;
    const xx = cs.x(item.t);
    const yy = y(shareRow.shares);
    svg.appendChild(svgEl("line", { x1: xx, x2: xx, y1: cs.top, y2: cs.top + cs.innerH, class: "marker-line" }));
    svg.appendChild(svgEl("circle", { cx: xx, cy: yy, r: 4, class: "marker-dot" }));
    const label = svgEl("text", { x: Math.min(xx + 6, cs.left + cs.innerW - 42), y: Math.max(cs.top + 12, yy - 8), class: "marker-label" });
    label.textContent = item.ratioText || item.date;
    svg.appendChild(label);
  }
}

function drawChart(chart) {
  const type = chart.dataset.chart;
  const config = chartConfig[type];
  const svg = chart.querySelector("svg");
  svg.innerHTML = "";
  const width = Math.max(320, chart.clientWidth);
  const height = chart.clientHeight;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  if (!state.view || !state.rows.length) return;

  const showX = type === "flow";
  const margin = { top: 24, right: 44, bottom: showX ? 34 : 10, left: 58 };
  const innerW = Math.max(40, width - margin.left - margin.right);
  const innerH = Math.max(40, height - margin.top - margin.bottom);
  const visible = state.rows.filter((row) => row.t >= state.view.minT && row.t <= state.view.maxT);
  const activeRows = visible.length ? visible : state.rows;
  const [minY, maxY] = minMax(activeRows, config.key, config);
  const x = (t) => margin.left + ((t - state.view.minT) / Math.max(1, state.view.maxT - state.view.minT)) * innerW;
  const y = (value) => margin.top + (1 - (value - minY) / Math.max(1e-9, maxY - minY)) * innerH;
  const cs = { left: margin.left, top: margin.top, innerW, innerH, x };

  const title = svgEl("text", { x: margin.left, y: 14, class: "chart-title" });
  title.textContent = config.title;
  svg.appendChild(title);
  drawAxis(svg, cs, y, minY, maxY, showX);

  if (config.kind === "line") {
    const path = linePath(activeRows, x, y, config.key);
    if (path) svg.appendChild(svgEl("path", { d: path, class: "series-line" }));
    if (type === "price" && activeRows.some((row) => defined(row.benchmark))) {
      const [benchMin, benchMax] = minMax(activeRows, "benchmark");
      const yBench = (value) => margin.top + (1 - (value - benchMin) / Math.max(1e-9, benchMax - benchMin)) * innerH;
      const benchPath = linePath(activeRows, x, yBench, "benchmark");
      if (benchPath) svg.appendChild(svgEl("path", { d: benchPath, class: "benchmark-line" }));
    }
    if (type === "shares") drawDisclosureMarkers(svg, cs, y);
  } else if (config.kind === "bar") {
    drawBars(svg, activeRows, cs, y, config.key, false);
  } else {
    drawBars(svg, activeRows, cs, y, config.key, true);
  }

  const overlay = svgEl("rect", {
    x: margin.left,
    y: margin.top,
    width: innerW,
    height: innerH,
    class: "hover-layer",
  });
  overlay.addEventListener("pointerdown", (event) => beginZoomDrag(event, svg, cs));
  overlay.addEventListener("pointermove", (event) => showTooltip(event, cs, config));
  overlay.addEventListener("pointerleave", () => {
    if (!state.zoomDrag) hideTooltip();
  });
  overlay.addEventListener("dblclick", resetZoom);
  overlay.addEventListener("wheel", (event) => wheelZoom(event, cs), { passive: false });
  svg.appendChild(overlay);

  if (showX) {
    const panLayer = svgEl("rect", {
      x: margin.left,
      y: margin.top + innerH,
      width: innerW,
      height: margin.bottom,
      class: "axis-pan-layer",
    });
    panLayer.addEventListener("pointerdown", (event) => beginAxisPan(event, cs, panLayer));
    svg.appendChild(panLayer);
  }
}

function draw() {
  if (!state.rows.length) {
    clearCharts();
    return;
  }
  for (const chart of els.charts) drawChart(chart);
}

function beginZoomDrag(event, svg, cs) {
  if (event.button !== 0 || !state.view) return;
  const rect = event.currentTarget.getBoundingClientRect();
  const startX = event.clientX - rect.left + cs.left;
  const selection = svgEl("rect", { x: startX, y: cs.top, width: 0, height: cs.innerH, class: "zoom-selection" });
  svg.appendChild(selection);
  state.zoomDrag = { startX, currentX: startX, cs, selection };
  event.currentTarget.setPointerCapture(event.pointerId);
}

function updateZoomDrag(event) {
  if (!state.zoomDrag) return;
  const chartRect = event.target.closest?.(".chart")?.getBoundingClientRect() || els.chartStack.getBoundingClientRect();
  const x = Math.max(
    state.zoomDrag.cs.left,
    Math.min(state.zoomDrag.cs.left + state.zoomDrag.cs.innerW, event.clientX - chartRect.left),
  );
  state.zoomDrag.currentX = x;
  const left = Math.min(state.zoomDrag.startX, x);
  const width = Math.abs(x - state.zoomDrag.startX);
  state.zoomDrag.selection.setAttribute("x", left);
  state.zoomDrag.selection.setAttribute("width", width);
}

function finishZoomDrag() {
  if (!state.zoomDrag) return;
  const drag = state.zoomDrag;
  drag.selection.remove();
  state.zoomDrag = null;
  const width = Math.abs(drag.currentX - drag.startX);
  if (width > 10) {
    const inv = (x) => state.view.minT + ((x - drag.cs.left) / drag.cs.innerW) * (state.view.maxT - state.view.minT);
    setView(inv(Math.min(drag.startX, drag.currentX)), inv(Math.max(drag.startX, drag.currentX)));
  }
}

function wheelZoom(event, cs) {
  if (!state.view) return;
  event.preventDefault();
  const rect = event.currentTarget.getBoundingClientRect();
  const localX = event.clientX - rect.left + cs.left;
  const ratio = Math.max(0, Math.min(1, (localX - cs.left) / cs.innerW));
  const center = state.view.minT + ratio * (state.view.maxT - state.view.minT);
  const factor = event.deltaY > 0 ? 1.22 : 0.82;
  const range = (state.view.maxT - state.view.minT) * factor;
  setView(center - range * ratio, center + range * (1 - ratio));
}

function beginAxisPan(event, cs, layer) {
  if (event.button !== 0 || !state.view) return;
  state.axisPan = {
    startX: event.clientX,
    startMinT: state.view.minT,
    startMaxT: state.view.maxT,
    range: state.view.maxT - state.view.minT,
    innerW: cs.innerW,
    layer,
  };
  layer.classList.add("is-panning");
  layer.setPointerCapture(event.pointerId);
  hideTooltip();
  event.preventDefault();
}

function updateAxisPan(event) {
  if (!state.axisPan) return;
  const dx = event.clientX - state.axisPan.startX;
  const deltaT = (-dx / state.axisPan.innerW) * state.axisPan.range;
  state.view = clampView(state.axisPan.startMinT + deltaT, state.axisPan.startMaxT + deltaT);
  updateZoomButton();
  draw();
}

function finishAxisPan() {
  if (!state.axisPan) return;
  state.axisPan.layer.classList.remove("is-panning");
  state.axisPan = null;
}

function showTooltip(event, cs, config) {
  if (state.zoomDrag || state.axisPan || !state.view || !state.rows.length) return;
  const rect = event.currentTarget.getBoundingClientRect();
  const localX = event.clientX - rect.left + cs.left;
  const t = state.view.minT + ((localX - cs.left) / cs.innerW) * (state.view.maxT - state.view.minT);
  const row = nearestRow(t);
  if (!row) return;
  const rows = [
    ["前复权价", defined(row.price) ? priceFmt.format(row.price) : "-"],
    ["成交额", defined(row.turnover) ? `${fmt.format(row.turnover)} 亿` : "-"],
    ["ETF 份额", defined(row.shares) ? `${fmt.format(row.shares)} 亿份` : "-"],
    ["申购赎回", defined(row.flow) ? `${fmt.format(row.flow)} 亿份` : "-"],
  ];
  if (config.key === "price" && defined(row.benchmark)) rows.push(["对照线", fmt.format(row.benchmark)]);
  els.tooltip.innerHTML = `
    <div class="tooltip-title">${row.date}</div>
    ${rows.map(([label, value]) => `<div class="tooltip-row"><span>${label}</span><strong>${value}</strong></div>`).join("")}
  `;
  const stackRect = els.chartStack.getBoundingClientRect();
  const left = Math.min(event.clientX - stackRect.left + 12, stackRect.width - 250);
  const top = Math.max(10, event.clientY - stackRect.top - 20);
  els.tooltip.style.left = `${Math.max(8, left)}px`;
  els.tooltip.style.top = `${top}px`;
  els.tooltip.style.visibility = "visible";
}

function hideTooltip() {
  els.tooltip.style.visibility = "hidden";
}

async function refreshData() {
  setStatus("公开版为只读页面；数据由站点维护者定期更新。");
}

async function init() {
  setStatus("读取 universe");
  state.universe = await fetchJson("data/universe.json");
  state.groups = await fetchJson("data/groups.json");
  if (!state.universe.some((item) => item.code === state.activeCode)) {
    const first = state.universe.find((item) => item.dashboard_eligible) || state.universe[0];
    state.activeCode = first?.code || "";
  }
  renderSelectors();
  await loadTrendBoard();
  await selectEtf(state.activeCode);
}

els.groupSelect.addEventListener("change", () => {
  state.activeGroup = els.groupSelect.value;
  renderEtfOptions();
  loadTrendBoard();
  selectEtf(state.activeCode);
});

els.etfSelect.addEventListener("change", () => selectEtf(els.etfSelect.value));
els.trendTableBody.addEventListener("click", handleTrendTableClick);
els.trendPopoutBtn.addEventListener("click", toggleTrendPopout);
els.trendBackdrop.addEventListener("click", () => setTrendPopout(false));
els.refreshBtn.addEventListener("click", refreshData);
els.resetZoomBtn.addEventListener("click", resetZoom);
window.addEventListener("resize", draw);
window.addEventListener("pointermove", (event) => {
  updateZoomDrag(event);
  updateAxisPan(event);
});
window.addEventListener("pointerup", () => {
  finishZoomDrag();
  finishAxisPan();
});
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && els.trendPanel.classList.contains("is-expanded")) {
    setTrendPopout(false);
  }
});

init().catch((error) => {
  clearCharts();
  setStatus(`初始化失败：${error.message}`);
});
