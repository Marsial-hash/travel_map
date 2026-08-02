# 数据源状态矩阵（Data Source Status Matrix）

- 版本：1.0.0
- 状态维度独立：access / schema / semantic / reference_compatibility / reliability / license_internal / license_public / production
- 状态值：CONFIRMED / UNVERIFIED / FAILED / NOT_APPLICABLE / NOT_APPROVED / APPROVED

| source_id | 数据源 | 数据集 | access | schema | semantic | ref_compat | reliability | license_internal | license_public | production | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TENCENT_QUOTES | 腾讯行情 qt.gtimg.cn / ifzq | ETF实时/前复权K线 | CONFIRMED | CONFIRMED | UNVERIFIED | CONFIRMED | UNVERIFIED | UNVERIFIED | UNVERIFIED | NOT_APPROVED | 量=手已验证；无官方字段文档 |
| SOHU_HISQ | 搜狐 hisHq | 指数/ETF历史行情 | CONFIRMED | CONFIRMED | UNVERIFIED | CONFIRMED | UNVERIFIED | UNVERIFIED | UNVERIFIED | NOT_APPROVED | 万元→亿元已验证；指数额语义待对账 |
| EM_NAV | 天天基金 f10/lsjz | NAV历史 | CONFIRMED | CONFIRMED | UNVERIFIED | NOT_APPLICABLE | UNVERIFIED | UNVERIFIED | UNVERIFIED | NOT_APPROVED | 2014起覆盖 |
| SZSE_RT | 深交所 getTimeData | 深市ETF实时 | CONFIRMED | CONFIRMED | UNVERIFIED | NOT_APPLICABLE | UNVERIFIED | UNVERIFIED | UNVERIFIED | NOT_APPROVED | 含真实成交额+netValue |
| SSE_QUERY | 上交所 query.sse | 历史份额 | FAILED | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | UNVERIFIED | UNVERIFIED | NOT_APPROVED | 6 sqlId全空 |
| SZSE_REPORT | 深交所 ShowReport | 历史份额 | FAILED | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | UNVERIFIED | UNVERIFIED | NOT_APPROVED | 空/404 |
| TUSHARE_FUND_SHARE | Tushare fund_share | ETF历史份额 | **UNVERIFIED（待实测）** | UNVERIFIED | UNVERIFIED | NOT_APPLICABLE | UNVERIFIED | UNVERIFIED | UNVERIFIED | NOT_APPROVED | 2000积分；fd_share万份；待实测 |
| TUSHARE_TRADE_CAL | Tushare trade_cal | 交易日历 | UNVERIFIED | UNVERIFIED | UNVERIFIED | NOT_APPLICABLE | UNVERIFIED | UNVERIFIED | UNVERIFIED | NOT_APPROVED | 待实测 |
| JISILU | 集思录 etf_list | 当日份额快照 | CONFIRMED | CONFIRMED | UNVERIFIED | NOT_APPLICABLE | UNVERIFIED | UNVERIFIED | UNVERIFIED | NOT_APPROVED | amount_dt=T+1 08:06 |
| FUND_DISCLOSURE | 基金定期报告PDF | 持仓披露 | UNVERIFIED | UNVERIFIED | UNVERIFIED | NOT_APPLICABLE | UNVERIFIED | UNVERIFIED | UNVERIFIED | NOT_APPROVED | 待解析≥2家 |
| REFERENCE_SITE | 参考站静态JSON | 复刻对照 | CONFIRMED | CONFIRMED | NOT_APPLICABLE | CONFIRMED | NOT_APPLICABLE | NOT_APPROVED | NOT_APPROVED | NOT_APPROVED | 仅作复刻/对照，不作Canonical真值 |

## 能力批准状态（Phase 0B 动态更新）

| 数据源 | historical_backfill | daily_batch | live_signal | public_dashboard |
|---|---|---|---|---|
| 腾讯行情 | 待定 | 待定 | false | false |
| 搜狐 | 待定 | 待定 | false | false |
| 天天基金NAV | 待定 | 待定 | false | false |
| Tushare fund_share | **待实测** | 待实测 | false | false |

## 规则

- 一次访问成功 **不得** 自动升级 reliability/license/production
- Reference 一致 ≠ Canonical 语义正确
- 未文档化来源（腾讯/搜狐）仅称"独立供应商对账源"，不称官方源
