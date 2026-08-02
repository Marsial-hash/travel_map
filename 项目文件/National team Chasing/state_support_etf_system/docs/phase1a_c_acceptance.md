# Phase 1A-C 验收（Acceptance Report — 修复后最终版）

- 版本：3.0.0
- 日期：2026-08-02
- 修复分支：fix/phase-1a-c-remediation

# 唯一结论：PHASE_1A_C_COMPLETE

## C01-C27 验收矩阵

| Gate | 状态 | 证据 |
|---|---|---|
| C01 Phase 0B封版复核 | ✅ PASS | phase0b_seal_audit.md，S-01~S-05 未推翻 |
| C02 独立分支+提交 | ✅ PASS | 实现/审计/修复分支可追溯，7个真实提交，工作区干净，未合并main |
| C03 主数据身份 | ✅ PASS | 10表物化，含官方list_date，resolve正确 |
| C04 日历时段 | ✅ PASS | SSE+SZSE 各2813开放日，一致 |
| C05 字段组选源 | ✅ PASS | 16条SSP(metric_group级) + source_selection_result物化 |
| C06 Policy+Watermark | ✅ PASS | 8条Policy + dataset_watermark物化(字段组粒度) |
| C07 行情回填 | ✅ PASS | 2811-2813行，fund_daily主源 |
| C08 份额回填+语义 | ✅ PASS | 语义分层，share_daily仅交易日，非交易日隔离，无重复开放日 |
| C09 NAV回填 | ✅ PASS | 2827行，fund_nav含ann_date |
| C10 指数成交额 | ✅ PASS | candidate未冒充真值，语义UNVERIFIED未使用 |
| C11 三层物化 | ✅ PASS | raw/normalized/canonical 25张表 |
| C12 Staging原子发布 | ✅ PASS | DatasetVersionMaterializer生成PUBLISHED版本+membership |
| C13 PIT+血缘+字段一致 | ✅ PASS | 日期统一为Date类型，字段血缘保留 |
| C14 Immutable+Supersession | ✅ PASS | record_supersession物化+测试 |
| C15 economic_delta非float | ✅ PASS | Decimal(38,0) |
| C16 四层门控 | ✅ PASS | 日期/经济/NAV/Close测试全过 |
| C17 覆盖率阈值 | ✅ **PASS** | 159845覆盖率100%(list_date起点)，全部ETF≥99.5% |
| C18 510300跳变 | ✅ PASS | Canonical源异常→阻断，Reference未污染 |
| C19 幂等 | ✅ PASS | 5项幂等测试通过 |
| C20 日批 | ✅ PASS | run_canonical_daily按watermark推进，不生成实时信号 |
| C21 双时间API | ✅ PASS | research_available_at真实过滤+6场景测试 |
| C22 DQ报告 | ✅ PASS | MAJOR=UNRESOLVED_NON_PHASE_BLOCKING，布尔一致 |
| C23 离线pytest | ✅ PASS | 107 passed |
| C24 Live测试 | ✅ PASS | 2 passed（真实fund_share） |
| C25 ruff+mypy+密钥 | ✅ PASS | ruff全绿/mypy 51 files/密钥扫描PASS |
| C26 水位线+截止日 | ✅ PASS | dataset_watermark物化(字段组粒度) |
| C27 冲突分离 | ✅ PASS | source_selection_result/conflict_result物化，门控用实际状态 |

## 能力位

- `historical_backfill_approved=✅true`
- `daily_batch_research_approved=✅true`
- `live_signal_approved=❌false`
- `public_dashboard_approved=❌false`
- `disclosure_pipeline_approved=❌false`
- `lifecycle_adjustment_ready=❌false`

## 未确认项
- `UNVERIFIED`：fund_share实时更新时间 / 指数成交额语义 / 披露解析 / 燃烧跨日
- `UNKNOWN`：510300跳变根因（待官方证据）
- `LICENSE_UNVERIFIED`：非选定源许可
