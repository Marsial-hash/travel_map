# Phase 1A-C 最终独立审计报告（红队复核）

- 版本：1.0.0
- 日期：2026-08-02
- 审计分支：audit/phase-1a-c-final
- 审计范围：真实 Git、Parquet、DuckDB、Manifest、API、测试、数据

# 唯一结论：PHASE_1A_C_PARTIAL_REMEDIATION_REQUIRED

独立审计确认上一版报告存在**非法状态表述**（`PHASE_1A_C_COMPLETE（有条件）`）和**多项未物化/未实现**，不能判 COMPLETE。

## A01-A14 审计结果

| Audit | 状态 | 关键证据 | 修复情况 |
|---|---|---|---|
| A01 状态合法性 | ❌ FAIL | 原报告用 `PARTIAL`/`COMPLETE（有条件）`非法状态 | ✅ 已改合法状态 |
| A02 159845覆盖率 | ❌ FAIL | 99.4628% < 99.5% 阈值 | 待修复（合法排除或接受FAIL） |
| A03 2813vs2825 | ✅ 解释完成 | 2825=raw含14非交易日(季末/年末)记录；2811=交易日记录；2813=预期开放日 | ✅ 已解释 |
| A04 长期语义 | ❌ 表述错误 | 42/66年为MIXED_SNAPSHOT_PLUS_NONTRADING，非全DAILY_SNAPSHOT | ✅ 已按年工件化 |
| A05 C10指数 | ✅ PASS | candidate未冒充真值，语义UNVERIFIED未使用 | 无需修复 |
| A06 DQ MAJOR | ⚠️ 状态错误 | resolution_status=OPEN | ✅ 已改UNRESOLVED_NON_PHASE_BLOCKING |
| A07 510300异常 | ✅ 正确 | Canonical源跳变-60.28亿→阻断；Reference未污染 | 无需修复 |
| A08 表清单 | ❌ 数字错误 | 实为25张（非26），market/nav用YYYYMMDD | ✅ 已生成逐表清单 |
| A09 版本快照 | ⚠️ 未物化 | PublicationManager存在但backfill未调用 | 待修复 |
| A10 双时间API | ❌ 未真实过滤 | 参数存在但无research_available_at过滤 | 待修复 |
| A11 幂等 | ⚠️ 未验证 | 未实际重跑Raw哈希对比 | 待验证 |
| A12 选源Watermark | ⚠️ 未物化 | 无source_selection_result | 待修复 |
| A13 流量覆盖率 | ⚠️ 部分FAIL | 经济流量99.1-99.4%达标；share 159845 FAIL | 待修复 |
| A14 提交结构 | ❌ 仅4个 | 要求≥5 | 本审计提交补足 |

## 核心数据事实（真实复算）

### 份额覆盖率（按各自上市起点分母）
| ETF | 起点 | 分母 | 覆盖 | 缺失 | 非交易日记录 | 覆盖率 | ≥99.5%? |
|---|---|---|---|---|---|---|---|
| 510300 | 2015-01-05 | 2813 | 2811 | 2 | 14 | 99.929% | ✅ |
| 510310 | 2015-01-05 | 2813 | 2804 | 9 | 14 | 99.680% | ✅ |
| 159919 | 2015-01-06 | 2812 | 2809 | 3 | 16 | 99.893% | ✅ |
| 510050 | 2015-01-05 | 2813 | 2813 | 0 | 14 | 100.000% | ✅ |
| 510500 | 2015-01-05 | 2813 | 2809 | 4 | 14 | 99.858% | ✅ |
| **159845** | 2021-03-18 | 1303 | 1296 | 7 | 7 | **99.463%** | ❌ |

159845 缺失7日：2021-03-19/23/24/25/26/29/30（上市初期），行情表亦无记录 → 真实数据缺口，**不能排除**。

### 2813 vs 2825 差异解释
- **2813** = SSE 日历 2015-01-05~2026-07-31 开放交易日数
- **2825** = 510300 raw fund_share 记录数（含 14 条非交易日季末/年末记录如 2016-12-31, 2017-09-30 等）
- **2811** = 实际交易日记录数（= 2813 - 2 缺失交易日）
- 差异 = 14 条非交易日记录（份额与相邻交易日不同，为真实变动事件）
- 验证：flow 表中这14条均被 `NON_CONSECUTIVE_OPEN_SESSION` 阻断，未污染日度流量 ✅

### 长期份额语义（逐ETF/年）
- 42/66 年度 = `MIXED_SNAPSHOT_PLUS_NONTRADING`（季末/年末有非交易日份额记录）
- 20/66 年度 = 纯 `DAILY_SNAPSHOT`（如 2020/2021/2025/2026）
- 4/66 年度 = `DAILY_SNAPSHOT_WITH_GAPS`（2015年上市初期缺口）
- **不得表述为"2015起全部DAILY_SNAPSHOT"**

### 510300 2026-01-28 异常（独立复核）
- 前日(01-27) 575.33亿份 → 当日(01-28) 515.05亿份（delta=-60.28亿份）→ 后日(01-29) 492.60亿份
- `event_evidence_scope=CANONICAL_SOURCE_EVENT_CANDIDATE`（选定源自身异常）
- 门控：economic/nav/close 全 false + `UNRESOLVED_SHARE_JUMP` ✅
- Reference 异常未污染 Canonical ✅

## 未物化/未实现（阻断项）

| 声称 | 实际 | 影响 |
|---|---|---|
| Staging原子发布 | backfill未调PublicationManager，无published版本 | C12 FAIL |
| record_supersession | 无表物化 | C14 FAIL |
| 双时间API过滤 | 仅参数校验，未过滤research_available_at | C21 FAIL |
| source_selection_result | 无表 | C27 FAIL |
| conflict_resolution_status | 无表 | C27 FAIL |

## 测试与安全
- 离线 pytest：96 passed
- Live pytest：2 passed（真实fund_share）
- ruff：All checks passed
- mypy：48 source files no issues
- 密钥扫描：secret_scan_passed=true（真实密钥0，变量引用10允许）
- `.env` 未被跟踪 ✅

## 修复命令（下一轮）
```bash
# 1. 修复C17: 评估159845缺失日是否合法排除（预计仍FAIL）
# 2. 修复C12/C14: backfill调用PublicationManager并物化supersession
# 3. 修复C21: canonical_api加research_available_at过滤
# 4. 修复C27: 物化source_selection_result
# 5. 补足提交数≥5
```

## 未确认事项
- `UNVERIFIED`：fund_share实时更新时间 / 指数成交额语义 / 披露解析 / 燃烧测试跨日
- `UNKNOWN`：159845上市初期7日缺口的根因（数据源缺失，非本地错误）
- `LICENSE_UNVERIFIED`：非选定源许可
- 510300跳变定性：UNRESOLVED_SHARE_JUMP（待官方证据）

## 唯一下一步
修复指定阻断项（C17/C12/C14/C21/C27/C02），不接受"有条件完成"。
