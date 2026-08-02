"""单位体系（unit system）：元/万元/亿元、份/万份/亿份、手/份转换。

所有转换显式记录单位与来源。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MoneyUnit(StrEnum):
    YUAN = "元"
    THOUSAND = "千元"
    WAN = "万元"
    YI = "亿元"


class ShareUnit(StrEnum):
    SHARE = "份"
    WAN_SHARE = "万份"
    YI_SHARE = "亿份"


class VolumeUnit(StrEnum):
    SHARE = "份"
    LOT = "手"


@dataclass(frozen=True)
class Converted:
    value: float
    unit: str
    source_unit: str
    conversion: str


def to_yuan(value: float, unit: MoneyUnit) -> float:
    factors = {MoneyUnit.YUAN: 1.0, MoneyUnit.THOUSAND: 1e3, MoneyUnit.WAN: 1e4, MoneyUnit.YI: 1e8}
    return value * factors[unit]


def to_share(value: float, unit: ShareUnit) -> float:
    factors = {ShareUnit.SHARE: 1.0, ShareUnit.WAN_SHARE: 1e4, ShareUnit.YI_SHARE: 1e8}
    return value * factors[unit]


def to_share_from_lot(lots: float, lot_size: int = 100) -> float:
    """手 -> 份。A股ETF一手=100份。"""
    return lots * lot_size


def shares_to_yi(value: float) -> float:
    return value / 1e8


def yuan_to_yi(value: float) -> float:
    return value / 1e8


def estimate_turnover_yi(typical_price: float, volume_lots: float) -> float:
    """参考站估算成交额（亿元）：typical_price × 量(手) × 100 / 1e8。"""
    return typical_price * volume_lots * 100 / 1e8


def convert_money(value: float, from_unit: MoneyUnit, to_unit: MoneyUnit) -> Converted:
    """通用货币转换，记录来源与转换路径。"""
    yuan = to_yuan(value, from_unit)
    factors = {MoneyUnit.YUAN: 1.0, MoneyUnit.THOUSAND: 1e3, MoneyUnit.WAN: 1e4, MoneyUnit.YI: 1e8}
    return Converted(
        value=yuan / factors[to_unit],
        unit=to_unit.value,
        source_unit=from_unit.value,
        conversion=f"{from_unit.value}->{to_unit.value}",
    )
