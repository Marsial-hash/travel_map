# 数据许可审查（Data License Review）

- 版本：2.0.0（S-01 封版复核统一版）
- 审查日期：2026-08-02
- 审查人：DeepSeek（MODEL_CROSS_CHECKED，非法律意见）

## 声明
本文件是**证据化的非法律条款审查**（S-01），不构成法律意见。公开展示与再分发须在取得数据方明确授权前保持未批准状态。

## 各数据源许可状态（含 Tushare 协议捕获）

| source_id | 访问方式 | 协议/依据 | 内部研究 | 本地保存 | 公开展示 | 再分发 | 频率限制 | 风险 | 审查依据 |
|---|---|---|---|---|---|---|---|---|---|
| TENCENT_QUOTES | HTTP公开 | 未查获明确服务条款 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 未知 | 中（无文档） | 未文档化公开接口 |
| SOHU_HISQ | HTTP公开 | 未查获明确服务条款 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 未知 | 中 | 未文档化公开接口 |
| EM_NAV | HTTP公开 | 天天基金服务条款未逐条审 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 未知 | 中 | 页面公开数据 |
| SZSE_RT | HTTP公开 | 深交所官网公开数据 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 未知 | 低-中 | 交易所官网 |
| **TUSHARE_FUND_SHARE** | 付费API（2000积分） | tushare.pro/document/1（2026-08-02捕获） | **CONDITIONALLY_APPROVED** | **CONDITIONALLY_APPROVED** | NOT_APPROVED | NOT_APPROVED | 官方限制 | 低-中 | 付费订阅实测通过 |
| JISILU | HTTP公开 | 未查获明确服务条款 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 未知 | 中 | 社区网站 |
| FUND_DISCLOSURE | 公开PDF | 基金信息披露法规 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 无 | 低 | 法规要求披露 |
| REFERENCE_SITE | 静态JSON | 站点未明示授权 | NOT_APPROVED | NOT_APPROVED | NOT_APPROVED | NOT_APPROVED | — | 高 | **不得镜像/重新分发** |

## 选定源（Tushare）许可审查结论（S-01）

| 字段 | 值 |
|---|---|
| terms_captured | true |
| terms_source_url | https://tushare.pro/document/1 |
| terms_retrieved_at | 2026-08-02T18:27:25+08:00 |
| terms_sha256 | 待用户确认后补（本地未保存协议全文） |
| nonlegal_review_completed | true |
| legal_opinion_provided | **false**（不提供法律意见） |
| license_internal_research_status | **CONDITIONALLY_APPROVED**（本地个人非商业研究） |
| license_local_storage_status | **CONDITIONALLY_APPROVED** |
| license_public_display_status | **NOT_APPROVED** |
| redistribution_status | **NOT_APPROVED** |
| user_confirmation_required | true |
| written_permission_required | true（公开使用/再分发前） |
| review_notes | 付费订阅，Tushare服务条款未全文保存到本地；内部研究用途经实测权限确认；公开展示与再分发须用户与Tushare确认 |

## 规则

1. 许可状态无法确认时一律 `LICENSE_UNVERIFIED`，不得写成已批准。
2. `historical_backfill_approved=true` 与 `public_dashboard_approved=false` 允许并存。
3. 参考站数据仅作复刻/对照，不得重新分发完整数据集。
4. 模型不得声称提供法律意见；公开展示须用户与数据方确认。
5. **内部研究 CONDITIONALLY_APPROVED 不等于 LICENSE_UNVERIFIED**（S-01 已统一）。
