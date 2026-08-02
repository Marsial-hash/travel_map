"""instrument_code_resolver（补丁12-7）：六位代码经 registry 解析为内部 instrument_id 及来源专属代码。

禁止猜测市场或把六位代码原样发给 Tushare。
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

REGISTRY_DIR = Path(__file__).resolve().parents[2] / "registry"


@dataclass(frozen=True)
class ResolvedInstrument:
    internal_instrument_id: str
    security_code: str
    exchange: str
    tushare_code: str
    valid_from: str
    valid_to: str | None


class InstrumentCodeResolver:
    """基于 registry/instruments.csv + identifier_history.csv 的代码解析器。"""

    def __init__(self, registry_dir: Path = REGISTRY_DIR) -> None:
        self._by_code: dict[str, ResolvedInstrument] = {}
        self._load(registry_dir)

    def _load(self, registry_dir: Path) -> None:
        instruments_path = registry_dir / "instruments.csv"
        identifiers_path = registry_dir / "identifier_history.csv"
        if not instruments_path.exists() or not identifiers_path.exists():
            raise FileNotFoundError(f"registry files missing: {instruments_path} / {identifiers_path}")

        code_to_inst: dict[str, dict[str, str]] = {}
        with instruments_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                code_to_inst[row["security_code"]] = row

        tushare_codes: dict[str, str] = {}
        with identifiers_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["identifier_type"] == "TUSHARE_CODE":
                    tushare_codes[row["identifier_value"].split(".")[0]] = row["identifier_value"]

        for code, inst in code_to_inst.items():
            self._by_code[code] = ResolvedInstrument(
                internal_instrument_id=inst["internal_instrument_id"],
                security_code=code,
                exchange=inst["exchange"],
                tushare_code=tushare_codes.get(code, f"{code}.UNKNOWN"),
                valid_from=inst["valid_from"],
                valid_to=inst["valid_to"] or None,
            )

    def resolve(self, security_code: str) -> ResolvedInstrument:
        inst = self._by_code.get(security_code)
        if inst is None:
            raise KeyError(f"unknown security_code {security_code}; not in registry/instruments.csv")
        return inst

    def exchange(self, security_code: str) -> str:
        return self.resolve(security_code).exchange
