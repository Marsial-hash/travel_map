# 时间可用性模型（Availability Model）

- 版本：1.0.0
- 时区：Asia/Shanghai
- 关联：contracts/availability/、docs/execution_timing_model.md

## 一、八时间字段

| 字段 | 定义 | 用途 |
|---|---|---|
| event_time | 事件实际发生时间 | 溯源 |
| trade_date | 归属A股交易日 | 主键之一 |
| source_published_at | 数据源明确记录的发布时间 | 溯源 |
| source_observed_at | 实测首次观察到数据可用的时间 | 溯源 |
| research_available_at | Point-in-time保守最早可用时间 | **历史回测唯一依据** |
| first_seen_at | 本系统首次抓取到的时间 | 生产实时 |
| ingested_at | 当前版本入库时间 | 审计 |
| revised_at | 修订/重算时间 | 审计 |

附加：source_timezone / availability_policy_id / availability_basis(OFFICIAL_DOCUMENTATION|LIVE_OBSERVATION|CROSS_SOURCE_INFERENCE|CONSERVATIVE_POLICY|UNKNOWN) / availability_evidence_id / policy_confidence

## 二、Availability Policy（版本化，不得原地修改）

| policy_id | 数据集 | 规则 | basis | confidence | live_signal |
|---|---|---|---|---|---|
| TUSHARE_FUND_SHARE_V1_CONSERVATIVE | fund_share | research_available_at = T+2 09:30（保守） | CONSERVATIVE_POLICY | LOW | false |
| TUSHARE_FUND_SHARE_V2_OBSERVED | fund_share | 待连续观察后新增（不修改V1） | 未定 | 未定 | 未定 |
| TENCENT_QUOTES_V1 | 行情/前复权 | T日 15:00 后（当日收盘数据） | LIVE_OBSERVATION | MEDIUM | false |
| SOHU_INDEX_V1 | 指数成交额 | T日 15:00 后 | LIVE_OBSERVATION | MEDIUM | false |
| EM_NAV_V1 | NAV | T日 20:00 后（净值发布惯例，待观察） | CONSERVATIVE_POLICY | LOW | false |
| FUND_REPORT_V1 | 定期报告 | 披露公告日（巨潮/官网） | OFFICIAL_DOCUMENTATION | MEDIUM | false |

**禁止**：把集思录单次08:06、etf_share_size约08:30 套用到 fund_share。fund_share 未连续观察前一律 V1 保守。

**允许**：historical_backfill_approved=true 与 live_signal_approved=false 并存。

## 三、交易日历

- market_calendar：exchange/calendar_date/is_open/previous_open_date/next_open_date(派生, lead over open dates, 记 calculation_version)/source/calendar_version/system_valid_from/to
- market_session_calendar：时段（pre_open/morning/afternoon/closing）+ 午休 + 时区
- SSE 与 SZSE 分开拉取，对账后再建共享A股日历视图
- 禁止自然日+1；gap/open_session_distance/T+1/T+2/NEXT_DAY_OPEN 全部依赖日历

## 四、记录语义与重建

- fund_share_record_semantics ∈ {DAILY_SNAPSHOT, CHANGE_EVENT, MIXED_OR_UNKNOWN}
- 重建模式：
  - EX_POST_BIDIRECTIONAL_RECONSTRUCTION：可看前后记录，仅用于语义分析/对账/质量，**不得用于回测**
  - PIT_FORWARD_ONLY_RECONSTRUCTION：回测唯一合法，value_at_t = latest record where research_available_at <= t；**不得用未来记录反向确认**
- 字段：source_record_semantics / is_observed_record / is_forward_filled / effective_from / effective_to / reconstruction_method / reconstruction_confidence / reconstruction_mode / reconstruction_source_record_id / knowledge_cutoff_at / pit_reconstruction_eligible / future_confirmation_used
- 硬规则：future_confirmation_used=true → pit_reconstruction_eligible=false
