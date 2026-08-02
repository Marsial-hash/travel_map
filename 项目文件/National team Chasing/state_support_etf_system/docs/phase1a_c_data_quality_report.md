# Phase 1A-C 数据质量报告

- 版本：1.0.0
- 日期：2026-08-02
- 运行：backfill_20260802_192254

## 一、数据质量问题统计

| 严重级 | 数量 | 说明 |
|---|---|---|
| CRITICAL | 0 | 无 |
| MAJOR | 1 | 510300 2026-01-28 份额跳变-60.28亿份（Canonical源异常，已阻断流量） |
| MINOR | 0 | 无 |
| INFO | 0 | 无 |

MAJOR 问题处置：510300 跳变已设置 `economic_flow_eligible=false` + `flow_block_reason=UNRESOLVED_SHARE_JUMP`，未生成任何 NAV/Close 流量。待取得基金管理人/交易所官方证据后升级为 CONFIRMED_SHARE_ADJUSTMENT_EVENT 并应用调整因子。

## 二、流量阻断归因

510300 全表 2825 行：
- economic_flow_eligible=True：2793（98.9%）
- 阻断 32 行：
  - NON_CONSECUTIVE_OPEN_SESSION：31（份额观测缺失日，可归因）
  - UNRESOLVED_SHARE_JUMP：1（2026-01-28 跳变，可归因）
- **UNKNOWN 阻断 = 0** ✅

## 三、覆盖率（按各自上市起点分母）

| ETF | 份额覆盖 | 经济流量覆盖 | 说明 |
|---|---|---|---|
| 510300 | 99.93% | 99.36% | ✅ |
| 510310 | 99.68% | 99.11% | ✅ |
| 159919 | 99.89% | 99.25% | ✅ |
| 510050 | 100.0% | 99.43% | ✅ |
| 510500 | 99.86% | 99.29% | ✅ |
| 159845 | 99.46% | 99.15% | ⚠️ 略低于99.5%（2021上市初期） |

合同阈值：market≥99.5% / share≥99.5% / economic≥99.0% / nav≥95.0% / close≥99.0%
- share 覆盖率：159845=99.46%（略低于99.5%），其余全部达标
- economic 流量覆盖率：全部≥99.0% ✅
- UNKNOWN 阻断比例：0 ✅

## 四、数据完整性

- 主数据：fund_master(7)/share_class(7)/instrument(7)/identifier_history(14)/index(16)/data_source(13)/availability_policy(8)/source_selection_policy(16)
- 日历：SSE+SZSE 各 4230 行（2015-2026），2813 开放日
- Canonical：26 张表（6ETF × market/share/nav/flow + flow_all）

## 五、Decimal 存储验证（C15）

- `canonical_economic_delta_shares`：Decimal(precision=38, scale=0) ✅
- `estimated_flow_nav`：Decimal(precision=38, scale=4) ✅
- 核心计算未用不受控 float
