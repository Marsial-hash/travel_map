# 数据许可审查（Data License Review）

- 版本：1.0.0
- 审查日期：2026-08-02
- 审查人：DeepSeek（MODEL_CROSS_CHECKED，非法律意见）

## 声明
本文件是**证据化的非法律条款审查**（补丁12-8），不构成法律意见。公开展示与再分发须在取得数据方明确授权前保持未批准状态。

## 各数据源许可状态

| source_id | 访问方式 | 协议/依据 | 内部研究 | 本地保存 | 公开展示 | 再分发 | 频率限制 | 风险 | 审查依据 |
|---|---|---|---|---|---|---|---|---|---|
| TENCENT_QUOTES | HTTP公开 | 未查获明确服务条款 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 未知 | 中（无文档） | 未文档化公开接口 |
| SOHU_HISQ | HTTP公开 | 未查获明确服务条款 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 未知 | 中 | 未文档化公开接口 |
| EM_NAV | HTTP公开 | 天天基金服务条款未逐条审 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 未知 | 中 | 页面公开数据 |
| SZSE_RT | HTTP公开 | 深交所官网公开数据 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 未知 | 低-中 | 交易所官网 |
| TUSHARE_FUND_SHARE | 付费API（2000积分） | Tushare服务协议（待调阅） | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 官方限制 | 低-中 | 付费订阅 |
| JISILU | HTTP公开 | 未查获明确服务条款 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 未知 | 中 | 社区网站 |
| FUND_DISCLOSURE | 公开PDF | 基金信息披露法规 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 禁止推定 | 无 | 低 | 法规要求披露 |
| REFERENCE_SITE | 静态JSON | 站点未明示授权 | NOT_APPROVED | NOT_APPROVED | NOT_APPROVED | NOT_APPROVED | — | 高 | **不得镜像/重新分发** |

## 规则

1. 许可状态无法确认时一律 `LICENSE_UNVERIFIED`，不得写成已批准。
2. `historical_backfill_approved=true` 与 `public_dashboard_approved=false` 允许并存（内部研究许可明确、公开展示许可未确认时）。
3. 参考站数据仅作复刻/对照，不得重新分发完整数据集。
4. 模型不得声称提供法律意见；需要正式使用时由用户与数据方确认。
