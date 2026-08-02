# Phase 1A-C 数据质量报告（红队审计版）

- 版本：2.0.0
- 日期：2026-08-02

## 一、数据质量问题

| 严重级 | 数量 | 说明 |
|---|---|---|
| CRITICAL | 0 | 无 |
| MAJOR | 1 | 510300 2026-01-28 跳变（UNRESOLVED_NON_PHASE_BLOCKING） |
| MINOR | 0 | 无 |
| INFO | 0 | 无 |

MAJOR 完整记录：
- issue_id: DQ-be12d96432cd
- severity: MAJOR / issue_type: UNRESOLVED_SHARE_JUMP / date: 2026-01-28
- resolution_status: **UNRESOLVED_NON_PHASE_BLOCKING**（已阻断流量，但异常未解释）
- blocks_daily_flow: true / blocks_historical_research: true
- 处置：未生成任何 NAV/Close 流量；待官方证据升级 CONFIRMED

## 二、流量阻断归因

510300 全表 2825 行：
- economic_flow_eligible=True：2793（98.9%）
- 阻断 32 行：NON_CONSECUTIVE_OPEN_SESSION=31（含14条非交易日记录+交易日缺口）、UNRESOLVED_SHARE_JUMP=1
- **UNKNOWN = 0** ✅

## 三、覆盖率（红队复算，按各自上市起点）

| ETF | 份额覆盖 | 阈值99.5% | 经济流量覆盖 | 阈值99.0% |
|---|---|---|---|---|
| 510300 | 99.929% | ✅ | 99.36% | ✅ |
| 510310 | 99.680% | ✅ | 99.11% | ✅ |
| 159919 | 99.893% | ✅ | 99.25% | ✅ |
| 510050 | 100.000% | ✅ | 99.43% | ✅ |
| 510500 | 99.858% | ✅ | 99.29% | ✅ |
| **159845** | **99.463%** | ❌ | 99.15% | ✅ |

159845 缺失7个交易日（2021-03-19~30 上市初期），行情亦无记录 → 真实数据缺口，不可排除。

## 四、字段一致性（C13）

- market/nav 表：trade_date/nav_date 用 `YYYYMMDD`
- flow/share 表：trade_date 用 `YYYY-MM-DD`
- **格式不一致** → C13 FAIL（需统一）

## 五、Decimal 存储（C15）
- canonical_economic_delta_shares: Decimal(38,0) ✅
- estimated_flow_nav: Decimal(38,4) ✅
