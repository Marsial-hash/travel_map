# Track A / Track B 分离政策（Track Separation Policy）

- 版本：1.0.0

## 一、双轨定义

| 轨道 | 目标 | 依赖 | 阻断条件 |
|---|---|---|---|
| Track A：Reference Replica | 高度还原参考网站公开产品结构与交互 | 参考站有限抽样Fixture / Mock / Reference指标 | 无（不依赖Canonical历史份额） |
| Track B：Canonical Research | 独立、可追溯、PIT的正式ETF研究数据 | Canonical历史份额源通过Phase 0B | 份额源未通过 → 历史资金流及相关研究阻断 |

## 二、模块归属矩阵

| 模块 | 轨道 | 受历史份额阻断？ |
|---|---|---|
| 项目脚手架 / 前端接口契约 | 共享 | 否 |
| 分组/ETF筛选 / 六概览卡 / 五联图 / 趋势表 / 日期缩放 / 披露标记 / 日夜间 / CSV / 口径切换框架 | Track A | 否 |
| 数据质量页面 | 共享 | 否 |
| 交易日历 / 时间模型 / 版本模型 / ETF身份模型 / 单位体系 | 共享 | 否 |
| 行情 / 真实成交额 / NAV 管线 | Track B（非资金流） | **否** |
| 历史份额差分 / 一级市场流量估算 / 介入证据分 / 方向识别 / 低位 / 止跌 / 回测 / 校准概率 / 决策状态机 | Track B（资金流） | **是** |

## 三、Track A 约束

1. 不得自动镜像或重新分发参考网站完整数据集
2. Reference Fixture 仅用于开发、兼容性测试、有限对照
3. 不得作为 Canonical 金融数据真值
4. 不得输入未来预测模型
5. 页面必须标注"参考兼容演示数据"或 Mock 性质

## 四、Canonical 物化保护

份额源未批准时：
```python
if not canonical_share_source_approved:
    prohibit_canonical_flow_materialization()
```
只允许生成 `warehouse/canonical/phase0b/BLOCKED.json` / `run_manifest.parquet` / `data_quality_issues.parquet`，或 Schema 文件并标 `contains_real_canonical_data=false`。Mock/Reference 数据不得进入 canonical 目录伪装真实。

## 五、能力位（分开批准）

historical_backfill_approved / daily_batch_research_approved / live_signal_approved / public_dashboard_approved / disclosure_pipeline_approved / lifecycle_adjustment_ready

允许：历史可查=true、实时信号=false、公开展示=false 并存。
