#!/usr/bin/env python3
"""统一对账入口（M-04）：按固定顺序运行5个对账任务。

- 记录每个任务开始/结束时间
- 单项失败后继续（收集所有结果），返回非零退出码
- 生成统一 manifest
"""
from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from research.reconciliation import (  # noqa: E402
    flow_method_reconciliation,
    index_turnover_reconciliation,
    lifecycle_event_reconciliation,
    share_reconciliation,
    turnover_reconciliation,
)

ETFS = [("510300", "SH"), ("510310", "SH"), ("159919", "SZ"), ("510050", "SH"), ("510500", "SH"), ("159845", "SZ")]
START = "2026-05-05"
END = "2026-07-31"


def main() -> int:
    tasks: list[tuple[str, Callable[[], Any]]] = [
        ("turnover_reconciliation", lambda: turnover_reconciliation.run(ETFS, START, END)),
        ("index_turnover_reconciliation", lambda: index_turnover_reconciliation.run(START, END)),
        ("share_reconciliation", lambda: share_reconciliation.run(ETFS)),
        ("flow_method_reconciliation", lambda: flow_method_reconciliation.run()),
        ("lifecycle_event_reconciliation", lambda: lifecycle_event_reconciliation.run()),
    ]
    manifest: dict[str, Any] = {"run_at": datetime.now().isoformat(timespec="seconds"), "tasks": []}
    exit_code = 0
    for name, fn in tasks:
        started = time.time()
        try:
            result = fn()
            status = "SUCCESS"
            detail = result
        except Exception as e:  # noqa: BLE001
            status = "FAILED"
            detail = str(e)[:500]
            exit_code = 1
        elapsed = round(time.time() - started, 2)
        task_record = {"name": name, "status": status, "elapsed_seconds": elapsed, "detail": detail}
        manifest["tasks"].append(task_record)
        print(f"[{status}] {name} ({elapsed}s)")
    manifest_path = PROJECT_ROOT / "warehouse" / "metadata" / "reconciliation_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"manifest: {manifest_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
