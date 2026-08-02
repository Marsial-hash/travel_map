"""单位体系测试（元/万元/亿元、份/万份/亿份、手/份）。"""
from __future__ import annotations

from data_pipeline.normalization.units import (
    MoneyUnit,
    ShareUnit,
    convert_money,
    estimate_turnover_yi,
    to_share,
    to_share_from_lot,
    to_yuan,
    yuan_to_yi,
)


class TestMoney:
    def test_yuan_conversions(self) -> None:
        assert to_yuan(1.0, MoneyUnit.WAN) == 10_000.0
        assert to_yuan(1.0, MoneyUnit.YI) == 1e8
        assert to_yuan(1000.0, MoneyUnit.YUAN) == 1000.0

    def test_convert_money(self) -> None:
        c = convert_money(83290912.0, MoneyUnit.WAN, MoneyUnit.YI)
        assert c.value == 8329.0912
        assert c.conversion == "万元->亿元"

    def test_yuan_to_yi(self) -> None:
        assert yuan_to_yi(70.1655e8) == 70.1655


class TestShares:
    def test_share_conversions(self) -> None:
        assert to_share(1.0, ShareUnit.WAN_SHARE) == 10_000.0
        assert to_share(1.0, ShareUnit.YI_SHARE) == 1e8

    def test_lot_to_share(self) -> None:
        assert to_share_from_lot(100, 100) == 10_000.0


class TestTurnoverEstimate:
    def test_reference_formula(self) -> None:
        """参考站公式：typical_price × 量(手) × 100 / 1e8 = 亿元。

        注意：公式复算=70.0759亿，参考站=70.1259亿，偏差0.07%。
        差异来源：参考站avg_price_est可能是四舍五入到2位的均价(4.67)而非原始typical_price。
        本测试断言公式本身正确 + 偏差在0.5%内（诚实，不宣称精确一致）。
        """
        typical = (4.703 + 4.644 + 4.653) / 3
        est = estimate_turnover_yi(typical, 15016263.0)
        assert round(est, 4) == 70.0759
        # 与参考站70.1259的偏差 < 0.5%
        assert abs(est - 70.1259) / 70.1259 < 0.005
