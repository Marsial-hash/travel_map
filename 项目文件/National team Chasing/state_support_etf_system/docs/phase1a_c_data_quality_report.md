# Phase 1A-C 数据质量报告（修复后）

- 版本：3.0.0
- 日期：2026-08-02

## 一、数据质量问题

| 严重级 | 数量 | 说明 |
|---|---|---|
| CRITICAL | 0 | 无 |
| MAJOR | 1 | 510300 2026-01-28 跳变 |
| MINOR | 0 | 无 |
| INFO | 0 | 无 |

MAJOR 完整记录：
- issue_id: DQ-be12d96432cd
- severity: MAJOR / type: UNRESOLVED_SHARE_JUMP / date: 2026-01-28
- resolution_status: **UNRESOLVED_NON_PHASE_BLOCKING**
- blocks_daily_flow: true / **blocks_historical_research: false** / blocks_affected_date_research: true / blocks_dataset_publication: false
- 处置：仅阻断 2026-01-28 单日流量，不阻断整体历史研究或数据集发布

## 二、流量阻断归因

510300 全表 2825 行：
- economic_flow_eligible=True：2793
- 阻断：NON_CONSECUTIVE_OPEN_SESSION=31（含非交易日记录+交易日缺口）、UNRESOLVED_SHARE_JUMP=1
- **UNKNOWN = 0** ✅

## 三、覆盖率（修复后）

| ETF | 覆盖起点 | 份额覆盖 | 阈值99.5% |
|---|---|---|---|
| 510300 | 2015-01-05 | 99.93% | ✅ |
| 510310 | 2015-01-05 | 99.68% | ✅ |
| 159919 | 2015-01-06 | 99.89% | ✅ |
| 510050 | 2015-01-05 | 100.00% | ✅ |
| 510500 | 2015-01-05 | 99.86% | ✅ |
| 159845 | 2021-03-31 | **100.00%** | ✅ |

159845 覆盖起点修正依据：Tushare fund_basic 官方 list_date=2021-03-31（非2012/2013），2021-03-18~30 为成立未上市区间，不属分母。

## 四、字段一致性（修复后）
- share_daily / flow：trade_date 用 **Date** 类型（YYYY-MM-DD）
- 非交易日观察：单独 normalized_nontrading_share_observation 表

## 五、Decimal 存储
- canonical_economic_delta_shares: Decimal(38,0) ✅
- estimated_flow_nav: Decimal(38,4) ✅
