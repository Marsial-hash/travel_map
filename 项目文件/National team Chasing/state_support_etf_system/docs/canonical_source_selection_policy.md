# Canonical 选源政策（Source Selection Policy）

- 版本：1.0.0
- 日期：2026-08-02
- 主键：`dataset_name + metric_group`（字段组级，P2 补丁）
- 冲突动作：ACCEPT_PRIMARY / ACCEPT_WITH_WARNING / QUARANTINE / BLOCK_CANONICAL / MANUAL_REVIEW_REQUIRED
- 冲突结果状态（实际）：NO_CONFLICT / WITHIN_TOLERANCE / RESOLVED_PRIMARY_ACCEPTED / RESOLVED_SECONDARY_ACCEPTED / WARNING_ACCEPTED / MANUAL_REVIEW_PENDING / QUARANTINED / BLOCKED / UNKNOWN

## 一、ETF 总份额

| metric_group | 主源 | 备用源 | 对账源 | 冲突容差 | 冲突动作 | 历史研究 | 日批 | 实时 | 公开展示 |
|---|---|---|---|---|---|---|---|---|---|
| OUTSTANDING_TOTAL_SHARES | TUSHARE_FUND_SHARE | COMMERCIAL_VENDOR(未订阅) | TENCENT_REALTIME(仅单日) | ≤1份或声明舍入单位 | ACCEPT_PRIMARY | ✅ | ✅ | ❌ | ❌ |
| SHARE_OBSERVATION_TIME | TUSHARE_FUND_SHARE | — | — | — | ACCEPT_PRIMARY | ✅ | ✅ | ❌ | ❌ |
| SHARE_UNIT_DEFINITION | REGISTRY | — | — | 精确 | BLOCK_CANONICAL(不一致时) | ✅ | ✅ | ❌ | ❌ |

## 二、ETF 日行情

| metric_group | 主源 | 备用源 | 对账源 | 冲突容差 | 冲突动作 | 历史 | 日批 | 实时 | 公开 |
|---|---|---|---|---|---|---|---|---|---|
| PRICE_OHLC | TENCENT_QUOTES | SOHU_HISQ | SOHU_HISQ | 相对≤0.5% | ACCEPT_WITH_WARNING | ✅ | ✅ | ❌ | ❌ |
| VOLUME | TENCENT_QUOTES | SOHU_HISQ | — | 相对≤1% | ACCEPT_WITH_WARNING | ✅ | ✅ | ❌ | ❌ |
| TURNOVER_AMOUNT | SOHU_HISQ | SZSE_RT(深市) | — | 相对≤1% | ACCEPT_WITH_WARNING | ✅ | ✅ | ❌ | ❌ |
| ADJUSTMENT_FACTOR | TENCENT_QUOTES(fqkline) | — | — | 精确 | ACCEPT_PRIMARY | ✅ | ✅ | ❌ | ❌ |
| TRADING_STATUS | REGISTRY+日历 | — | — | 精确 | ACCEPT_PRIMARY | ✅ | ✅ | ❌ | ❌ |

## 三、ETF NAV

| metric_group | 主源 | 备用源 | 对账源 | 冲突容差 | 冲突动作 | 历史 | 日批 | 实时 | 公开 |
|---|---|---|---|---|---|---|---|---|---|
| UNIT_NAV | EM_NAV | FUND_MANAGER_WEBSITE | — | 相对≤0.1% | ACCEPT_WITH_WARNING | ✅ | ✅ | ❌ | ❌ |
| ACCUMULATED_NAV | EM_NAV | — | — | 相对≤0.1% | ACCEPT_WITH_WARNING | ✅ | ✅ | ❌ | ❌ |
| NAV_PUBLICATION_TIME | EM_NAV(观察) | — | — | — | ACCEPT_PRIMARY | ✅(保守) | ✅ | ❌ | ❌ |

NAV 主源 EM_NAV 语义/发布时间未完全验证 → CONDITIONALLY_SELECTED + 保守PIT政策。

## 四、指数行情与成交额

| metric_group | 主源 | 备用源 | 对账源 | 冲突容差 | 冲突动作 | 历史 | 日批 | 实时 | 公开 |
|---|---|---|---|---|---|---|---|---|---|
| INDEX_PRICE | SOHU_HISQ(zs_) | TUSHARE_INDEX | — | 相对≤0.1% | ACCEPT_WITH_WARNING | ✅ | ✅ | ❌ | ❌ |
| INDEX_TURNOVER_CANDIDATE | SOHU_HISQ(zs_) | — | 参考站(有限) | 相对≤1% | ACCEPT_WITH_WARNING | ✅(candidate) | ✅ | ❌ | ❌ |
| INDEX_COMPONENT_SCOPE | UNVERIFIED | — | — | — | MANUAL_REVIEW_REQUIRED | ❌ | ❌ | ❌ | ❌ |

**指数成交额语义未验证 → 仅物化 `canonical_index_turnover_candidate` + semantic_status=UNVERIFIED，不冒充正式真值。**

## 五、交易日历

| metric_group | 主源 | 备用源 | 冲突容差 | 冲突动作 |
|---|---|---|---|---|
| CALENDAR_SSE | TUSHARE_TRADE_CAL | PUBLIC_CALENDAR | 精确 | ACCEPT_PRIMARY |
| CALENDAR_SZSE | TUSHARE_TRADE_CAL | PUBLIC_CALENDAR | 精确 | ACCEPT_PRIMARY |

SSE/SZSE 分别拉取；一致时生成共享A股日历视图，底层来源与差异保留。

## 六、组合血缘

同一 Canonical 行混合多源时保存：
- `row_source_composition`：行级源组合
- `field_source_map`：字段→源映射
- `source_selection_policy_versions`：各字段组政策版本

不得只用一个模糊 `source_id` 代表整行。
