# State Support ETF System

《A股国家队ETF资金追踪、介入预测与低位择时系统》— Phase 0A/0B 数据可行性验证工程。

## 项目边界
- **只研究ETF**，不研究个股/个股因子/951个普通选股因子/行业扩散。
- 长期路线：参考网站复刻 → Canonical数据底座 → 介入证据分 → 校准概率 → 方向识别 → 低位/止跌 → ETF比较 → 决策状态机。
- 本轮仅执行 Phase 0A（参考网站审计封版）与 Phase 0B（6只ETF×60日数据可行性Spike）。

## Track A / Track B
- **Track A Reference Replica**：高度还原参考网站公开产品结构，使用有限抽样Fixture/Mock，页面标注"参考兼容演示数据"。
- **Track B Canonical Research**：独立、可追溯、Point-in-time 的正式ETF研究数据。历史份额源未通过 Phase 0B 前，历史资金流及相关研究阻断。

## 环境
- Python `>=3.12,<3.13`（uv 管理）
- 依赖：DuckDB / Parquet / Polars / Pydantic / FastAPI / pytest / ruff / mypy
- Tushare Token：`export TUSHARE_TOKEN="..."` 或 `.env`（被 .gitignore 排除，严禁提交）

## 常用命令
```bash
uv sync --frozen
uv run pytest -m "not live and not network"   # 离线单元/集成测试
uv run pytest -m "live and requires_tushare_token"  # 真实Tushare测试（需Token）
uv run ruff check .
uv run mypy .
python scripts/phase0b_spike.py --etfs 510300,510310,159919,510050,510500,159845 --start 2026-05-05 --end 2026-07-31
python scripts/run_phase0b_reconciliations.py
```

## 文档
见 `docs/`：参考网站审计、指标合同、可用性/执行时间模型、Universe政策、Track分离、数据源状态矩阵、数据许可、数据可行性报告、Go/No-Go结论。
