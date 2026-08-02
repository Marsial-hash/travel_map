# 参考网站审计报告（Phase 0A 封版）

- 审计对象：https://forgpt-d0g49jg3794cda582-1456017603.tcloudbaseapp.com/
- 审计日期：2026-08-02
- 证据清单：见 `docs/reference_site_evidence_manifest.csv`（25条，EV001-EV025）
- 状态定义：CONFIRMED_SOURCE（公开源文件直接确认）/ CONFIRMED_BEHAVIOR（实际操作确认）/ REPRODUCED（独立代码复算一致）/ INFERRED / UNVERIFIED / UNKNOWN

## 一、页面与产品结构

| 结论 | 状态 | 证据 |
|---|---|---|
| 纯静态SPA，无后端API，数据全部来自静态JSON | CONFIRMED_SOURCE | EV001,EV002（app.js fetchJson("data/...")，refreshData明示"公开版为只读页面"） |
| 页面为单页，通过 ?dataset=huijin-csf\|insurance-state 切换两套数据集 | CONFIRMED_SOURCE | EV002（DATASET_CONFIGS/DATASET_ALIASES） |
| 主数据集 huijin-csf=汇金/证金及关联主体持仓追踪 | CONFIRMED_SOURCE | EV002（siteName: "桃子冰粉.汇金证金及其关联公司持仓追踪"） |
| 副数据集 insurance-state=险资/国资前十大持有人专题 | CONFIRMED_SOURCE | EV002（DATASET_CONFIGS["insurance-state"]） |
| 布局：topbar(品牌+操作) → toolbar(分组/ETF筛选) → dashboard-grid(ETF列表+主视图) → trend-board(趋势表) | CONFIRMED_SOURCE | EV001（body结构） |
| 概览卡6项：最新日期/前复权价/复权成交额/复权份额/最新披露持仓比例/金额 | CONFIRMED_SOURCE | EV001（summary-grid） |
| 五联图：price/turnover/shares/flow/flowImpact | CONFIRMED_SOURCE | EV001（chart-stack） |
| 趋势表9-13列（ETF/日期/价格变动/成交额/分位/净份额/分位/净申赎/净申赎比） | CONFIRMED_SOURCE | EV001,EV013（trend-table） |
| 累计摘要条（近一周5/近一月21/近三月63日） | CONFIRMED_SOURCE | EV001,EV002（addRollingStats） |
| 日期区间/时间滚动条/悬浮窗开关/日夜间主题 | CONFIRMED_SOURCE | EV001,EV002（date-range-panel/time-scroll/tooltip/theme） |
| 指标解释弹窗（help-trigger） | CONFIRMED_SOURCE | EV001,EV002（HELP_DEFINITIONS） |
| 投票/反馈/打赏/提问箱模块 | CONFIRMED_SOURCE | EV001（存在），不属核心功能，本项目不复制 |

## 二、数据接口与字段

| 接口 | 内容 | 状态 | 证据 |
|---|---|---|---|
| data/universe.json | 41只ETF主数据（code/name/display_group/manager/latest_ratio/value/dashboard_eligible） | CONFIRMED_SOURCE | EV004 |
| data/groups.json | 16个方向分组 | CONFIRMED_SOURCE | EV005 |
| data/etfs/{code}.json | 单ETF全序列625行（meta+series+disclosures） | CONFIRMED_SOURCE | EV006-EV011 |
| data/index-turnover/{key}.json | 9个趋势分组指数成交额 | CONFIRMED_SOURCE | EV012 |
| data/trends/{key}_recent_week.json | 趋势表近5日 | CONFIRMED_SOURCE | EV013 |
| data/margin/{key}.json | 指数+ETF融资余额 | CONFIRMED_SOURCE | EV014 |

**series[] 行结构**：date, etf_qfq_close, etf_qfq_avg_price_est, etf_qfq_turnover_est_yi, qfq_total_units_yi, qfq_delta_units_yi, benchmark_close
**disclosures[]**：report_date, combined_ratio_pct, combined_value_yi, total_shares_yi_qfq

## 三、指标口径与公式（全部从app.js源码提取）

| 指标 | 公式 | 状态 | 证据 |
|---|---|---|---|
| 前复权价 | etf_qfq_close（腾讯fqkline qfq） | CONFIRMED_SOURCE（meta.price_basis） | EV002 |
| 复权成交额 | typical_price=(H+L+C)/3 × volume × 100(手→份) / 1e8 | **REPRODUCED**（510300 70.1259亿精确复算） | EV025 |
| 复权份额 | 交易所总份额按调整事件换算到当前单位基准 | CONFIRMED_SOURCE（meta.shares_basis） | EV002,EV006 |
| 净份额变化 | qfq_total_t − qfq_total_{上一有份额日} | CONFIRMED_SOURCE | EV002（normalizeSeriesForTrend） |
| 估算净申赎 | delta × avg_price_est（兜底 close） | CONFIRMED_SOURCE | EV002（estimateFlowAmount/flowAmountPrice） |
| 净申赎/指数成交额 | flow_amount / vendor_index_turnover × 100 | CONFIRMED_SOURCE | EV002（parsePayload flowImpact） |
| 成交额/份额/申赎分位 | 排序位置%，样本 2024-01-01 起 | CONFIRMED_SOURCE | EV002（percentileFromSorted/TREND_PERCENTILE_START_DATE） |
| 分组合计价格 | 直接显示对应指数真实收盘点位 | CONFIRMED_SOURCE | EV002（aggregateTitles） |
| 分组合计涨跌 | 组内ETF日收益按成交额加权 | CONFIRMED_SOURCE | EV002（buildTrendGroupHistory） |
| 分组合计额/份额/申赎 | 当日全组覆盖才展示（覆盖门控） | CONFIRMED_SOURCE | EV002（allHaveShares等） |
| 持仓比例合计 | Σ(金额)/Σ(金额/(比例/100)) 加权 | CONFIRMED_SOURCE | EV002（aggregateHoldingStats） |
| 披露标记 | disclosures日期垂直线+标注画在shares图 | CONFIRMED_SOURCE | EV002（drawDisclosureMarkers） |

## 四、分组与持仓主体

| 结论 | 状态 | 证据 |
|---|---|---|
| 16方向分组（宽基9+金融/成长/消费/跨境/货币/周期7） | CONFIRMED_SOURCE | EV005 |
| 9个趋势映射（trendGroupMap: hs300/sse50/sse180/csi500/csi800/csi1000/chinext/star50/sz100） | CONFIRMED_SOURCE | EV002 |
| 持仓主体口径=汇金/证金及关联主体 | CONFIRMED_SOURCE | EV002（HELP_DEFINITIONS holderMetaNote） |
| 最新披露=2025-12-31定期报告（410300披露82.76%/3494亿） | CONFIRMED_SOURCE | EV006 |
| 510300 2026-01-28 份额跳变-60.28亿份（疑似份额折算，未证实） | CONFIRMED_SOURCE（数据） | EV006 |

## 五、数据更新与可用性

| 结论 | 状态 | 证据 |
|---|---|---|
| 数据由站点维护者定期重建JSON（data_refreshed_at时间戳） | CONFIRMED_SOURCE | EV006（meta.data_refreshed_at=2026-07-31T23:49:10+08:00） |
| 页面刷新按钮明示"公开版为只读页面" | CONFIRMED_SOURCE | EV002（refreshData） |
| 参考站份额序列2024-01起逐日覆盖99-100%（159919有2025-11五连缺） | CONFIRMED_SOURCE | EV006,EV008（本地统计） |
| 份额更新时间推测为T+1早晨（参考站与集思录08:06一致） | INFERRED | EV020 |
| 数据源语义：腾讯前复权价、搜狐指数成交额（万元→亿元） | REPRODUCED | EV015-EV018 |

## 六、数据源对账结论（Phase 0B输入）

| 数据项 | 首选源 | 备用源 | 状态 | 备注 |
|---|---|---|---|---|
| ETF行情/前复权 | 腾讯 qt.gtimg.cn / ifzq.gtimg.cn | 搜狐 hisHq | REPRODUCED（单位/量=手已验证） | 免费 |
| ETF真实成交额 | 搜狐 cn_{code} hisHq（万元） | 深交所 getTimeData（amount元） | REPRODUCED | 与估算偏差0.06% |
| NAV历史 | 天天基金 f10/lsjz | 基金公司官网 | CONFIRMED_BEHAVIOR（2014起） | 免费 |
| ETF逐日历史份额 | **Tushare fund_share（待实测）** | 交易所页面（失效） | UNVERIFIED | **Phase 0B核心验证** |
| 指数成交额 | 搜狐 zs_{code} hisHq（万元→亿） | Tushare index_daily | REPRODUCED（与参考站一致） | 语义待对账 |
| 基金持仓披露 | 天天基金/巨潮 PDF | 基金公告 | UNVERIFIED | Phase 0B解析≥2家 |

## 七、UNKNOWN / UNVERIFIED 清单

| 项目 | 状态 | 说明 |
|---|---|---|
| 参考站后台原始抓取脚本 | UNKNOWN | 公开资源无线索 |
| 数据修订机制（参考站是否留痕修订） | UNKNOWN | 公开资源无线索 |
| ETF费率字段 | UNKNOWN | universe.json无费率 |
| 退市ETF覆盖策略 | UNKNOWN | universe仅41只在市 |
| 份额调整事件完整清单 | UNVERIFIED | 需Phase 0B生命周期扫描 |
| fund_share实际语义（每日快照/变动日） | UNVERIFIED | **Phase 0B实测** |
| fund_share更新时间 | UNVERIFIED | 未观察前用保守政策 T+2 09:30 |
| 交易所免费历史份额接口 | UNVERIFIED | 已测多个失效，待商业/付费源确认 |
| 搜狐指数成交额语义（成分口径/是否跨市场） | UNVERIFIED | Phase 0B双源对账 |
| 基金报告PDF解析稳定性 | UNVERIFIED | Phase 0B实测 |

## 八、结论

参考网站**公开功能拆解完成度约95%**，核心指标公式全部可从公开JS提取，数据接口全部为静态JSON。参考站作为**产品与指标逻辑研究参照**完成使命；其数据**不得作为Canonical真值**。下一阶段（Phase 0B）聚焦：fund_share实测、份额语义判定、指数成交额语义对账、披露解析、生命周期事件扫描。
