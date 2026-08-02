# 数据集独立 Availability Policy

- 版本：1.0.0
- 日期：2026-08-02
- 时区：Asia/Shanghai
- 补丁：P3（各数据集独立水位线）

## 一、各数据集 Policy

| availability_policy_id | dataset_name | research_available_at_rule | basis | confidence | 历史研究 | 日批 | 实时 |
|---|---|---|---|---|---|---|---|
| TUSHARE_FUND_SHARE_V1_CONSERVATIVE | ETF份额(fund_share) | **T+2 09:30**（第2个后续开放日） | CONSERVATIVE_POLICY | LOW | ✅ | ✅ | ❌ |
| TUSHARE_FUND_DAILY_V1 | ETF行情(fund_daily) | T日 15:00 后 | LIVE_OBSERVATION | MEDIUM | ✅ | ✅ | ❌ |
| ETF_NAV_V1_CONSERVATIVE | ETF净值 | T+1 09:30（净值晚间发布惯例，待观察） | CONSERVATIVE_POLICY | LOW | ✅ | ✅ | ❌ |
| INDEX_DAILY_V1 | 指数日线 | T日 15:00 后 | LIVE_OBSERVATION | MEDIUM | ✅ | ✅ | ❌ |
| INDEX_TURNOVER_V1_CONSERVATIVE | 指数成交额 | T日 15:00 后 | LIVE_OBSERVATION | MEDIUM | ✅ | ✅ | ❌ |
| FUND_DISCLOSURE_V1 | 定期报告披露 | **披露公告日** 09:30 | OFFICIAL_DOCUMENTATION | MEDIUM | ✅(披露后) | ✅ | ❌ |
| LIFECYCLE_ANNOUNCEMENT_V1 | 生命周期公告 | 公告/正式生效日 | OFFICIAL_DOCUMENTATION | MEDIUM | ✅ | ✅ | ❌ |
| MASTER_DATA_CHANGE_V1 | 主数据变更 | 变更生效日 | OFFICIAL_DOCUMENTATION | MEDIUM | ✅ | ✅ | ❌ |

**硬规则**：
- fund_share V1 保守政策**不得修改**，后续只能新增 V2_OBSERVED。
- 不得把 NAV 业务日期当可用时间；流量计算必须检查 `nav_research_available_at <= evaluation_timestamp`。
- 定期报告只能从披露日生效，不得从报告期末开始进入知识集。

## 二、各数据集字段

每个 Policy 必须包含：
`availability_policy_id / dataset_name / event_time_definition / trade_date_definition / source_published_at_rule / source_observed_at_rule / research_available_at_rule / availability_basis / policy_confidence / timezone / effective_from / effective_to / policy_version / may_be_used_for_historical_research / may_be_used_for_daily_batch / may_be_used_for_live_signal`

## 三、数据集水位线（dataset_watermark）

字段：`dataset_name / source_id / latest_completed_trade_date / latest_observed_trade_date / latest_source_expected_trade_date / latest_research_available_trade_date / latest_published_canonical_trade_date / watermark_calculated_at / availability_policy_id / watermark_status`

watermark_status：`UP_TO_DATE / EXPECTED_SOURCE_LAG / UNEXPECTED_DATA_GAP / SOURCE_UNAVAILABLE / BLOCKED_BY_QUALITY / UNKNOWN`

规则：
1. EXPECTED_SOURCE_LAG（处于政策延迟窗口内）不得标记 DATA_MISSING，不进覆盖率分母。
2. 延迟窗口由运行前版本化Policy定义，执行后不得临时扩大。
3. 超过政策预期时间自动转 UNEXPECTED_DATA_GAP。
4. 报告单独列出预期延迟记录数。

## 四、流量发布截止日

```
flow_publication_cutoff =
min(
  share_research_available_cutoff,
  nav_or_close_research_available_cutoff,
  market_calendar_cutoff,
  master_data_cutoff,
  lifecycle_event_cutoff
)
```

不得因行情已到T日就提前生成尚未满足份额/NAV可用条件的T日流量。
