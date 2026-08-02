# 指标合同（Metric Contracts）

- 版本：1.0.0
- 更新日期：2026-08-02
- 双命名空间：`reference_*`（仅用于复刻参考网站）/ `canonical_*`（正式研究）
- 规则：任何预测/介入评分/回测不得默认使用 `reference_*`；净申赎一律为估算并带方法标记。

## 一、Reference 命名空间（复刻参考网站）

| 指标 | 公式 | 数据源 | 单位 | 是否估算 | 时间可用性 | 可用于模型 |
|---|---|---|---|---|---|---|
| reference_qfq_close | 腾讯前复权收盘 | 腾讯 fqkline | 元 | 否 | T日15:00后 | 否（仅对照） |
| reference_turnover_est | (H+L+C)/3 × volume × 100 / 1e8 | 腾讯K线(量)+OHLC | 亿元 | **是** | T日15:00后 | 否 |
| reference_adjusted_shares | 交易所总份额按调整事件换算 | 份额源(待定) | 亿份 | 否（需调整） | T+1保守 | 否 |
| reference_delta_adjusted_shares | 复权份额差分 | 同上 | 亿份 | 否（计算） | T+1 | 否 |
| reference_estimated_primary_market_flow_avg_price | delta_adjusted × avg_price_est | 份额源+均价 | 亿元 | **是** | T+1 | 否 |
| reference_flow_impact | flow / vendor_index_turnover × 100 | 上述+搜狐 | % | **是** | T+1 | 否 |
| reference_aggregate_holding_ratio | Σ(金额)/Σ(金额/(比例/100)) | 定期报告 | % | 否（披露） | 披露日 | 否 |
| reference_index_close | 指数收盘点位 | 搜狐/中证 | 点 | 否 | T日 | 否 |
| reference_vendor_index_turnover | 供应商指数成交额 | 搜狐 zs_ | 亿元 | 否（供应商） | T日 | 否（语义未验证） |

## 二、Canonical 命名空间（正式研究）

| 指标 | 公式 | 数据源 | 单位 | 是否估算 | 时间可用性 | 可用于模型 |
|---|---|---|---|---|---|---|
| canonical_raw_close | 行情源收盘价 | 腾讯/交易所 | 元 | 否 | T日15:00后 | 是 |
| canonical_adjusted_close | 复权收盘 | 行情源+复权因子 | 元 | 否 | T日 | 是 |
| canonical_volume | 原始成交量 | 行情源 | 手 | 否 | T日 | 是 |
| canonical_turnover_amount | **数据源真实货币成交额** | 搜狐/深交所 | 元 | 否 | T日 | 是 |
| canonical_raw_total_shares | 原始总份额（不含PCF） | 份额源(待定) | 份 | 否 | T+1保守 | 是 |
| canonical_adjusted_share_units | 调整后份额单位 | 份额源+调整事件 | 份 | 否 | T+1 | 是 |
| canonical_delta_raw_shares | 原始份额差分 | 份额源 | 份 | 否（计算） | T+1 | 是（须门控） |
| canonical_delta_adjusted_shares | 调整后份额差分 | 上述 | 份 | 否（计算） | T+1 | 是（须门控） |
| canonical_economic_delta_shares | **经济有效份额变化**（调整因子验证后） | 调整事件+份额 | 份 | 否 | T+1 | **是（唯一流量输入）** |
| canonical_estimated_primary_market_flow_nav | economic_delta × nav | 份额+NAV | 元 | **是** | T+1 | 是 |
| canonical_estimated_primary_market_flow_close | economic_delta × close | 份额+收盘 | 元 | **是** | T+1 | 是 |
| canonical_index_close | 指数收盘 | 中证/独立源 | 点 | 否 | T日 | 是 |
| canonical_index_turnover | 正式指数成交额（语义验证后） | 待对账 | 元 | 否 | T日 | 是 |
| canonical_aggregate_holding_ratio | Σheld_shares/Σtotal_shares | 定期报告 | % | 否 | 披露日 | 是（PIT） |

## 三、净申赎估算记录字段（每条必带）

is_cash_flow_observed(默认false) / is_share_based_estimate(默认true) / flow_estimation_method(NAV|CLOSE_PRICE|REFERENCE_AVG_PRICE|UNAVAILABLE) / flow_estimation_quality / price_used / nav_used / share_units_used / share_adjustment_version / calculation_version / metric_contract_version / input_dataset_versions / input_record_ids / input_fingerprint / availability_policy_version

## 四、份额差分门控字段

previous_observation_date / open_session_distance / missing_open_session_count / flow_interval_start / flow_interval_end / is_consecutive_trading_day / daily_flow_eligible(=distance==1 AND missing==0) / interval_flow_only / missing_share_observation_count

## 五、经济流量门控字段（补丁12-1/2/9）

canonical_economic_delta_shares / share_unit_basis_id / adjustment_factor_verified / share_unit_basis_matched / valuation_unit_basis_matched / unit_consistency_passed / identity_continuity_passed / event_contamination_status(CLEAN|CONFIRMED_ADJUSTMENT_APPLIED|UNRESOLVED_SHARE_JUMP|POSSIBLE_UNIT_CHANGE|POSSIBLE_SOURCE_REVISION|IDENTITY_DISCONTINUITY) / unresolved_event_candidate_id / source_revision_status / economic_flow_eligible / nav_flow_eligible / close_flow_eligible / flow_block_reason

**硬规则**：
- `daily_flow_eligible=true AND economic_flow_eligible=true` 双满足才生成 canonical 流量字段。
- `event_contamination_status==CONFIRMED_ADJUSTMENT_APPLIED` 时，须 `adjustment_factor_verified AND share_unit_basis_matched AND valuation_unit_basis_matched` 全 true 才允许。
- `nav_flow_eligible` 与 `close_flow_eligible` 分别验证 NAV/价格的日期、单位及 PIT 可用性。
- 未解决跳变（如510300 2026-01-28）即使日期连续也阻断流量，记 flow_block_reason。

## 六、版本存储模型（补丁12-5，二选一）

**已选定：严格 append-only（业务载荷不可变 + supersession 关系追加）**。业务载荷（source_payload_hash 对应的原始内容）一旦写入不可变更；修订通过追加新版本记录 + `supersedes_record_id` 链实现。`system_valid_to` 仅在新版本生效时更新。历史 as-of 查询返回当时有效版本。
