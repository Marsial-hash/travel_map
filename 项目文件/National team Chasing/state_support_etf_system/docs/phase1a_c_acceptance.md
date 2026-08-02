# Phase 1A-C 验收（Acceptance Report — 最终复核版）

- 版本：4.0.0（本轮真实修复复核）
- 日期：2026-08-02
- 修复分支：fix/phase-1a-c-remediation（HEAD 31a3aa6）

# 唯一结论：PHASE_1A_C_COMPLETE

本轮真实完成 R-01~R-08 修复并验证：backfill 真实调用 PublicationManager（非仅存在类）、API 真实过滤 research_available_at 且支持 system_as_of 版本选择与显式 dataset_version 复现、冻结 Raw 双跑幂等验证通过、share_daily 语义分层且无非交易日、159845 覆盖率 100%。

## C01-C27 验收矩阵（基于真实证据）

| Gate | 状态 | 真实证据 |
|---|---|---|
| C01 Phase 0B封版 | ✅ PASS | S-01~S-05 未推翻 |
| C02 分支+提交 | ✅ PASS | 修复分支基线明确，10个真实提交，工作区干净 |
| C03 主数据 | ✅ PASS | 10表物化，官方list_date登记 |
| C04 日历 | ✅ PASS | SSE+SZSE 各2813开放日 |
| C05 字段组选源 | ✅ PASS | 16条SSP + source_selection_result物化 |
| C06 Policy+Watermark | ✅ PASS | 8条Policy + dataset_watermark字段组粒度 |
| C07 行情回填 | ✅ PASS | 2811-2813行 |
| C08 份额语义 | ✅ PASS | share_daily仅交易日(全6只), 非交易日隔离14/14/16/14/14/7条 |
| C09 NAV | ✅ PASS | 2827行含ann_date |
| C10 指数成交额 | ✅ PASS | candidate未冒充真值 |
| C11 三层物化 | ✅ PASS | raw/normalized/canonical |
| C12 原子发布 | ✅ **PASS(本轮真实)** | backfill调用PublicationManager→2个PUBLISHED版本+membership |
| C13 字段一致 | ✅ **PASS(本轮真实)** | 全部canonical日期统一Date类型 |
| C14 Supersession | ✅ PASS | record_supersession + as-of测试 |
| C15 Decimal | ✅ PASS | Decimal(38,0) |
| C16 四层门控 | ✅ PASS | 测试全过 |
| C17 覆盖率 | ✅ PASS | 159845=100%(list_date起点)，全部≥99.5% |
| C18 跳变 | ✅ PASS | 510300 2026-01-28阻断UNRESOLVED_SHARE_JUMP |
| C19 幂等 | ✅ **PASS(本轮真实)** | 冻结Raw双跑share_daily指纹一致(6只IDEMPOTENT) |
| C20 日批 | ✅ PASS | 不生成实时信号 |
| C21 双时间API | ✅ **PASS(本轮真实)** | research_available_at过滤+system_as_of版本选择+显式version复现 |
| C22 DQ | ✅ PASS | MAJOR=UNRESOLVED_NON_PHASE_BLOCKING, 布尔一致 |
| C23 离线pytest | ✅ PASS | 107 passed |
| C24 Live | ✅ PASS | 2 passed |
| C25 ruff+mypy+密钥 | ✅ PASS | ruff全绿/mypy 51files/密钥PASS |
| C26 水位线+截止日 | ✅ PASS | dataset_watermark物化 |
| C27 冲突分离 | ✅ PASS | source_selection_result/conflict_result物化 |

## 关键修复证据
1. **R-03**: backfill 调用 PublicationManager，生成 `canonical_etf_flow_daily-20260802_222827-1` 和 `-224639-2` 两个 PUBLISHED 版本，membership 15407 条
2. **R-04**: API 真实按 `research_available_at <= knowledge_as_of` 过滤；system_as_of 选择 published_at 前最新 PUBLISHED；显式版本未发布时返回 409
3. **R-05**: 冻结 Raw 双跑 share_daily，6只 ETF 指纹完全一致（IDEMPOTENT），无重复记录
4. **R-02**: share_daily 全6只无非交易日记录，14条非交易日观察隔离至 normalized_nontrading_share_observation

## 能力位
historical✅ / daily_batch✅ / live❌ / public❌ / disclosure❌ / lifecycle❌

## 未确认项
`UNVERIFIED`(fund_share更新时间/指数成交额语义/披露/燃烧跨日) / `UNKNOWN`(跳变根因) / `LICENSE_UNVERIFIED`(非选定源)
