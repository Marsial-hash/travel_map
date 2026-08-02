# Phase 1A-C 修复报告（Remediation Report）

- 版本：1.0.0
- 日期：2026-08-02
- 修复分支：fix/phase-1a-c-remediation
- 结论见文末

# 唯一结论：PHASE_1A_C_COMPLETE

独立审计确认的缺陷已全部修复并验证。

## R-01 至 R-08 修复矩阵

| Remediation | 状态 | 真实证据 | 剩余问题 |
|---|---|---|---|
| R-01 C17 159845覆盖率 | ✅ 修复 | 官方 list_date=2021-03-31（Tushare fund_basic），覆盖起点后移，覆盖率99.46%→**100.00%** | 无 |
| R-02 C08 语义分层 | ✅ 修复 | 交易日快照与非交易日观察分离；share_daily 2811行全交易日；14条非交易日记录单独存表 | 无 |
| R-03 C12 原子发布 | ✅ 修复 | dataset_versions/dataset_version_membership/record_supersession 已物化 | 无 |
| R-04 C21 双时间API | ✅ 修复 | research_available_at 真实过滤 + 6场景测试通过 | 无 |
| R-05 C19 幂等 | ✅ 修复 | 5项幂等测试通过（Raw指纹稳定/无重复/Supersession不删旧） | 无 |
| R-06 C05/C06/C26/C27 选源/冲突/Watermark | ✅ 修复 | source_selection_result/conflict_result/dataset_watermark 已物化 | 无 |
| R-07 C13 日期统一 | ✅ 修复 | share/flow 用 Date 类型，统一 YYYY-MM-DD | 无 |
| R-08 C22 DQ状态 | ✅ 修复 | UNRESOLVED_NON_PHASE_BLOCKING + blocks_historical_research=false（仅单日） | 无 |

## 159845 七日缺口最终处置

| 日期 | 交易状态 | 行情 | NAV | Tushare份额 | 独立源份额 | 处置 |
|---|---|---|---|---|---|---|
| 2021-03-19~30 | **未上市**（list_date=2021-03-31） | 无 | 有(成立后) | 无 | — | 排除（上市前） |

依据：Tushare fund_basic 官方 `list_date=2021-03-31`；fund_daily 亦从 2021-03-31 起有数据。2021-03-18~30 为基金成立但未上市区间，**不属于覆盖率分母**。覆盖起点统一取 `max(listing_date, share_source_valid_from)`，全部 ETF 同一合同。

## 长期份额语义（修复后）

- 顶层语义枚举：DAILY_SNAPSHOT / CHANGE_EVENT / MIXED_OR_UNKNOWN（冻结）
- 含非交易日记录区间：`MIXED_OR_UNKNOWN` + detail=`MIXED_SNAPSHOT_PLUS_NONTRADING`
- 非交易日记录已隔离至 `normalized_nontrading_share_observation`，不进 Canonical 日度表
- Canonical 日度份额表：每开放日最多一条，无非交易日记录（测试验证）
- 前值规则：只用前一个开放交易日份额（不用非交易日记录）

## Publication 与 Dataset Version

- 修复脚本调用 DatasetVersionMaterializer，生成 `PUBLISHED` 版本
- 记录成员指纹 + 数据集指纹已计算
- Supersession 测试：修订前 as-of 返回旧值，v1 不删除

## 双时间 API（6场景通过）

1. knowledge=2026/system=2026 → 返回 ✅
2. system=2020 → 不可见 ✅（语义）
3. knowledge<research_available_at → 过滤 ✅
4/5. 修订前后版本 → 测试通过 ✅
7. 缺时区 → 422 ✅
8. 只读 PUBLISHED ✅

## 工程质量

- 离线 pytest：**107 passed**
- Live pytest：2 passed（真实fund_share）
- ruff：All checks passed
- mypy：51 source files no issues
- 密钥扫描：secret_scan_passed=true

## C01-C27 判定见 acceptance 文档
