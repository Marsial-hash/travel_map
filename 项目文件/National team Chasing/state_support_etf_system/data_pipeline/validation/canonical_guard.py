"""Canonical 物化保护（补丁/规格第33节）。

份额源未批准时，禁止生成真实 Canonical 份额/流量表。
只允许生成 BLOCKED.json / run_manifest.parquet / data_quality_issues.parquet，
或 Schema 文件并标 contains_real_canonical_data=false。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class CanonicalMaterializationGuard:
    canonical_dir: Path
    share_source_approved: bool

    def prohibit_canonical_flow_materialization(self) -> None:
        if not self.share_source_approved:
            raise RuntimeError(
                "canonical_share_source not approved: prohibit_canonical_flow_materialization() "
                "blocks etf_daily_share/etf_daily_flow materialization"
            )

    def write_blocked_marker(self, reason: str, run_metadata: dict[str, object] | None = None) -> Path:
        """份额源未批准时调用：写 BLOCKED.json。"""
        self.canonical_dir.mkdir(parents=True, exist_ok=True)
        marker = {
            "contains_real_canonical_data": False,
            "blocked": True,
            "reason": reason,
            "written_at": datetime.now().isoformat(timespec="seconds"),
            "run_metadata": run_metadata or {},
        }
        path = self.canonical_dir / "phase0b" / "BLOCKED.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_schema_only(self, schema: dict[str, object]) -> Path:
        """仅写Schema文件，标记无真实数据。"""
        self.canonical_dir.mkdir(parents=True, exist_ok=True)
        payload = {"contains_real_canonical_data": False, "schema": schema}
        path = self.canonical_dir / "phase0b" / "schema_only.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
