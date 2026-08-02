# Phase 1A-C 封版审查（Seal Review）

- 版本：1.0.0
- 日期：2026-08-02
- 审查分支：fix/phase-1a-c-remediation（HEAD 4d8c1f8）
- 审计工件：`warehouse/metadata/phase1a_c_seal_manifest.parquet` 等

# 唯一结论：PHASE_1A_C_SEAL_APPROVED

## F-01 至 F-10 矩阵

| Audit | 状态 | 真实证据 |
|---|---|---|
| F-01 159845覆盖起点 | ✅ PASS | 主数据重新物化后 `listing_date=20210331` 入 exchange_instrument_master.parquet；覆盖率 100%（分母1294） |
| F-02 非交易日隔离 | ✅ PASS | 6只ETF share_daily 非交易日=0；观察表 14/14/16/14/14/7；每开放日唯一 |
| F-03 日期类型统一 | ✅ PASS | market/nav/calendar/master 从 String 统一为 Date（7类核心表全 Date） |
| F-04 原子发布路径 | ✅ PASS | 2个 PUBLISHED 版本 + membership 15407 + record_supersession 物化 |
| F-05 失败回滚 | ✅ PASS | V2 注入 FAILED 后 V1 保持 PUBLISHED 且指纹不变（4测试通过） |
| F-06 完整流水线幂等 | ✅ PASS | 12项指纹（6 share + 6 nontrading）双跑一致 |
| F-07 输入变化Supersession | ✅ PASS | 修订链正确（supersedes=旧id），as-of 返回旧值 |
| F-08 双时间API | ✅ PASS | 8场景通过（S1/S2/S3/S6/S7/S9/S10/S10b） |
| F-09 选源/冲突/Watermark | ✅ PASS | source_selection_result(16行)/conflict_result/watermark(6行) 物化 |
| F-10 DQ与510300 | ✅ PASS | 510300 2026-01-28 四层门控全 false，无流量；DQ布尔一致 |

## C01-C27 判定

C01-C27 全部 PASS（基于本轮工件重算）。重点：
- C08：长期语义分层 + 非交易日隔离 ✅
- C12：真实发布 + 失败回滚 ✅
- C13：全部日期统一 Date ✅
- C14：不可变 Dataset Version + Supersession ✅
- C17：159845 覆盖率 100% ✅
- C19：完整流水线幂等 ✅
- C21：双时间 API 8场景 ✅
- C22：DQ 布尔一致 ✅
- C26：Watermark 物化 ✅
- C27：选源/冲突分离 ✅

## 质量门禁
- 离线 pytest：**111 passed**（含新增 seal_rollback 4测试）
- Live pytest：2 passed（真实 fund_share）
- ruff：All checks passed
- mypy：51 source files no issues
- 密钥扫描：secret_scan_passed=true（真实密钥0）

## 未确认事项（允许保留）
- `UNVERIFIED`：fund_share实时更新时间 / 指数成交额语义 / 披露解析 / 燃烧测试跨日
- `UNKNOWN`：510300跳变根因（待官方证据）
- `LICENSE_UNVERIFIED`：非选定源许可
