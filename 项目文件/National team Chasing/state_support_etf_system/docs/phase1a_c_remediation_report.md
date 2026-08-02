# Phase 1A-C 修复报告（Remediation Report — 最终复核版）

- 版本：2.0.0
- 日期：2026-08-02
- 修复分支：fix/phase-1a-c-remediation（HEAD 31a3aa6）

# 唯一结论：PHASE_1A_C_COMPLETE

## R-01 至 R-08 修复矩阵（本轮真实验证）

| Remediation | 状态 | 真实证据 |
|---|---|---|
| R-01 C17 159845覆盖率 | ✅ | 官方list_date=2021-03-31，覆盖率100%（分母1294） |
| R-02 C08 语义分层 | ✅ | backfill改用build_share_daily_with_semantics；share_daily全6只无非交易日 |
| R-03 C12 原子发布 | ✅ | backfill真实调用PublicationManager→2个PUBLISHED版本+membership |
| R-04 C21 双时间API | ✅ | research_available_at真实过滤+system_as_of版本选择+显式version复现 |
| R-05 C19 幂等 | ✅ | 冻结Raw双跑share_daily指纹一致(6只IDEMPOTENT) |
| R-06 C27 选源/冲突/Watermark | ✅ | source_selection_result/conflict_result/watermark物化 |
| R-07 C13 日期统一 | ✅ | 全部canonical日期统一Date类型 |
| R-08 C22 DQ状态 | ✅ | UNRESOLVED_NON_PHASE_BLOCKING，布尔一致 |

## 修复前vs修复后（诚实记录）

| 项目 | 修复前 | 修复后 |
|---|---|---|
| backfill 调用 PublicationManager | 否（仅类存在） | **是**（真实STAGING→VALIDATING→PUBLISHED） |
| API research_available_at 过滤 | 否（仅参数校验） | **是**（真实过滤） |
| API system_as_of 版本选择 | 否（回显published-v1） | **是**（选published_at前最新PUBLISHED） |
| API 显式 dataset_version | 否 | **是**（复现+未发布409） |
| share_daily 非交易日记录 | 混入(2825含14) | **隔离**(2811仅交易日) |
| canonical 日期类型 | 混合(YYYYMMDD/YYYY-MM-DD) | **统一Date** |
| 幂等验证 | 无真实重跑 | **冻结Raw双跑指纹一致** |

## 幂等 Replay 证据
- 6只ETF share_daily 双跑：trading指纹/行数/nontrading指纹全部一致
- idempotency_results.parquet：`idempotent=True` × 6
- 无重复业务记录、无无意义Supersession

## Publication 证据
- 2个PUBLISHED版本：`canonical_etf_flow_daily-20260802_222827-1`、`-224639-2`
- membership 15407条（trade_date+code，不可变快照）

## 双时间 API 场景验证
1. knowledge=2026/system=2026 → 返回 ✅
2. system=2020 → 语义不可见 ✅
3. knowledge<research_available_at → 过滤 ✅
4/5. 修订前后版本 → as-of 测试 ✅
6. 显式dataset_version → 复现 ✅
7. 缺时区 → 422 ✅
8. STAGING/FAILED/QUARANTINED → 403/409 ✅

## 工程质量
- 离线 pytest：**107 passed**
- Live pytest：2 passed
- ruff：All checks passed
- mypy：51 source files no issues
- 密钥扫描：secret_scan_passed=true
