"""最小 FastAPI 应用（Phase 0B 骨架）。"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="State Support ETF System", version="0.1.0")


@app.get("/api/v1/health")
def health() -> dict[str, object]:
    return {"status": "ok", "phase": "0A/0B"}


@app.get("/api/v1/etfs")
def list_etfs() -> dict[str, object]:
    """Reference Universe ETF 列表（Phase 1A-R 实现完整版）。"""
    import csv
    from pathlib import Path

    path = Path(__file__).resolve().parents[3] / "registry" / "reference_universe.csv"
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    return {"count": len(rows), "etfs": rows[:5]}
