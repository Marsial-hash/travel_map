"""instrument_code_resolver 测试（补丁12-7）。"""
from __future__ import annotations

import pytest

from data_pipeline.calendar.instrument_code_resolver import InstrumentCodeResolver


class TestInstrumentCodeResolver:
    def test_resolve_sh(self) -> None:
        r = InstrumentCodeResolver()
        inst = r.resolve("510300")
        assert inst.internal_instrument_id == "INST-510300"
        assert inst.exchange == "SH"
        assert inst.tushare_code == "510300.SH"

    def test_resolve_sz(self) -> None:
        r = InstrumentCodeResolver()
        inst = r.resolve("159919")
        assert inst.exchange == "SZ"
        assert inst.tushare_code == "159919.SZ"

    def test_unknown_code_raises(self) -> None:
        r = InstrumentCodeResolver()
        with pytest.raises(KeyError):
            r.resolve("999999")

    def test_no_guess_market(self) -> None:
        """禁止猜测市场：六位代码必须经registry解析。"""
        r = InstrumentCodeResolver()
        assert r.resolve("510050").tushare_code == "510050.SH"  # 不是 510050.SZ
