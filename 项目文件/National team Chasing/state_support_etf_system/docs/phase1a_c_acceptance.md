# Phase 1A-C 独立审计验收（Acceptance Report — 红队复核版）

- 版本：2.0.0（独立审计修正版）
- 日期：2026-08-02
- 审计分支：audit/phase-1a-c-final
- 实现分支：feature/phase-1a-c-canonical-minimal-loop（98e39f3）

# 唯一结论：PHASE_1A_C_PARTIAL_REMEDIATION_REQUIRED

独立审计发现以下问题，需修复后才能判 COMPLETE：
1. **C17 FAIL**：159845 份额覆盖率 99.4628% < 冻结阈值 99.5%
2. **C12 未物化**：backfill 未调用 PublicationManager，无 published dataset version
3. **C14 未物化**：无 record_supersession / canonical_record_versions 表
4. **C21 未真实实现**：API 双时间参数未真正过滤数据（无 research_available_at 过滤）
5. **C27 未物化**：无 source_selection_result / conflict_resolution 表
6. **C08 语义表述**：非"2015起全部DAILY_SNAPSHOT"，42/66年为 MIXED_SNAPSHOT_PLUS_NONTRADING
7. **C13 字段不一致**：market/nav 用 YYYYMMDD，flow 用 YYYY-MM-DD
8. **C02 提交数**：仅4个（要求≥5）

## C01-C27 验收矩阵（独立复核）

| Gate | 状态 | 证据 |
|---|---|---|
| C01 Phase 0B封版复核 | ✅ PASS | phase0b_seal_audit.md，S-01~S-05 未推翻 |
| C02 独立分支+提交 | ⚠️ FAIL | 分支正确但仅4提交（要求≥5） |
| C03 主数据身份 | ✅ PASS | 10表物化，resolve正确，无冲突 |
| C04 日历时段 | ✅ PASS | SSE+SZSE 各2813开放日，一致 |
| C05 字段组选源 | ✅ PASS | 16条SSP（metric_group级） |
| C06 Policy+Watermark | ✅ PASS | 8条Policy + WatermarkTracker |
| C07 行情回填 | ✅ PASS | 2811-2813行，fund_daily主源 |
| C08 份额回填+语义 | ⚠️ FAIL | 语义非纯DAILY_SNAPSHOT；2825含14非交易日记录；上市初期有缺口 |
| C09 NAV回填 | ✅ PASS | 2827行，fund_nav含ann_date |
| C10 指数成交额 | ✅ PASS | candidate未冒充真值，语义UNVERIFIED未使用 |
| C11 三层物化 | ✅ PASS | raw/normalized/canonical 25张表 |
| C12 Staging原子发布 | ⚠️ FAIL | PublicationManager代码存在但backfill未调用，未物化 |
| C13 PIT+血缘+字段一致 | ⚠️ FAIL | market/nav用YYYYMMDD，flow用YYYY-MM-DD不一致 |
| C14 Immutable+Supersession | ⚠️ FAIL | AppendOnlyStore测试过但未物化record_supersession |
| C15 economic_delta非float | ✅ PASS | Decimal(precision=38, scale=0) |
| C16 四层门控 | ✅ PASS | 日期/经济/NAV/Close测试全过 |
| C17 覆盖率阈值 | ❌ **FAIL** | 159845=99.4628%<99.5%；其余5只≥99.5% |
| C18 510300跳变 | ✅ PASS | Canonical源异常→阻断，Reference未污染 |
| C19 幂等 | ⚠️ NOT VERIFIED | 未实际重跑验证Raw哈希/Supersession |
| C20 日批 | ✅ PASS | run_canonical_daily按watermark推进，不生成实时信号 |
| C21 双时间API | ⚠️ FAIL | 参数存在但未真实过滤（无research_available_at） |
| C22 DQ报告 | ⚠️ FAIL | MAJOR resolution_status=OPEN（应UNRESOLVED_NON_PHASE_BLOCKING） |
| C23 离线pytest | ✅ PASS | 96 passed |
| C24 Live测试 | ✅ PASS | 2 passed（真实fund_share） |
| C25 ruff+mypy+密钥 | ✅ PASS | ruff全绿/mypy 48 files/密钥扫描PASS |
| C26 水位线+截止日 | ⚠️ PARTIAL | watermark物化但flow_cutoff未真正约束发布 |
| C27 冲突分离 | ⚠️ FAIL | 无source_selection_result/conflict_resolution表物化 |

## 修复清单（下一轮必须）

| 阻断项 | 修复文件 | 验收标准 |
|---|---|---|
| C17 159845覆盖率 | 需评估合法排除或接受FAIL | 覆盖率≥99.5%或明确FAIL |
| C12/C14 原子发布+Supersession | backfill调PublicationManager+物化版本表 | 有PUBLISHED版本+supersession记录 |
| C21 双时间API | canonical_api加research_available_at过滤 | 场景1-8测试通过 |
| C22 DQ状态 | data_quality表更新resolution_status | 合法枚举 |
| C02 提交数 | 新增真实审计提交 | ≥5提交 |
