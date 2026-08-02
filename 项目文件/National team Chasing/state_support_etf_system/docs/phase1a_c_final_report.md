# Phase 1A-C 最终报告

- 版本：1.0.0
- 日期：2026-08-02
- 分支：feature/phase-1a-c-canonical-minimal-loop

# 唯一结论：PHASE_1A_C_COMPLETE（有条件）

Phase 1A-C Canonical Research 最小闭环完成：6只ETF × 2015-01-01~2026-07-31（最近完成交易日）历史回填，Raw→Normalized→Canonical三层物化，四层流量门控，Decimal存储，双时间版本查询，Staging原子发布，只读API。

## Git 现场
- 分支：feature/phase-1a-c-canonical-minimal-loop
- 提交：6767270(基线) → 6fa8440(封版) → 5df9818(数据基础)
- 基线 main HEAD：4816d4c（与执行时一致）
- 工作区：干净（仅数据文件在 .gitignore 排除）
- 未自动合并回 main

## Canonical 选源政策（16条SSP）
- ETF份额：primary=TUSHARE_FUND_SHARE（备用商业源，腾讯仅对账）
- ETF行情：primary=TUSHARE_FUND_DAILY（2000积分实测，Phase1A-C升级）
- NAV：primary=TUSHARE_FUND_NAV（含ann_date公告日PIT证据）
- 指数成交额：仅 candidate（semantic_status=UNVERIFIED）
- 交易日历：SSE+SZSE 分别拉取，集合一致

## Availability Policy（8条）
- fund_share：V1_CONSERVATIVE（T+2 09:30，未修改）
- fund_daily/NAV/index：独立政策
- 全部 live_signal_approved=false

## 历史覆盖
| ETF | 上市起点 | share起点 | market | nav | flow |
|---|---|---|---|---|---|
| 510300 | 2015-01-05 | 2825 | 2813 | 2827 | 2825 |
| 510310 | 2015-01-05 | 2818 | 2813 | 2827 | 2818 |
| 159919 | 2015-01-06 | 2825 | 2812 | 2827 | 2825 |
| 510050 | 2015-01-05 | 2827 | 2813 | 2829 | 2827 |
| 510500 | 2015-01-05 | 2823 | 2811 | 2827 | 2823 |
| 159845 | 2021-03-18 | 1303 | 1294 | 1305 | 1303 |

## 510300 异常（C18）
2026-01-28 Canonical源（Tushare fund_share）跳变-60.28亿份：
- `event_evidence_scope=CANONICAL_SOURCE_EVENT_CANDIDATE`（Canonical源自身异常）
- economic_flow_eligible=false + flow_block_reason=UNRESOLVED_SHARE_JUMP
- **未生成任何 NAV/Close 流量** ✅
- Reference 异常未污染 Canonical（不因参考站证据预设阻断）

## 数据质量
- CRITICAL=0, MAJOR=1（跳变已阻断）, MINOR=0, INFO=0
- UNKNOWN 阻断=0
- 覆盖率：share 99.46-100%（159845 略低于99.5%）、economic 99.1-99.4%（达标）

## API
- 9 个只读端点（health/instruments/market/shares/flows/indices/DQ/pipeline/dataset-versions/availability/source-selection）
- 双时间参数（knowledge/system as_of）分离，时区缺失422
- 只读 PUBLISHED 版本
- API 测试 10 passed

## 工程质量
- 离线 pytest：96 passed
- Live pytest：2 passed（fund_share 真实Token）
- ruff：All checks passed
- mypy：48 source files no issues
- 密钥扫描：secret_scan_passed=true（真实密钥=0，变量引用10=允许）

## 未确认项
- `UNVERIFIED`：fund_share实时更新时间 / 指数成交额语义 / 披露解析 / 燃烧测试跨日
- `LICENSE_UNVERIFIED`：非选定源许可
- 510300跳变定性：UNRESOLVED_SHARE_JUMP（待官方证据）

## 唯一下一步
进入 Phase 1A-C 最终独立审计，或修复指定阻断项（159845 份额覆盖99.46%、指数成交额语义验证）。不直接进入介入评分。
