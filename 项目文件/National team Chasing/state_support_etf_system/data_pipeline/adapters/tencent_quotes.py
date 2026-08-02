"""腾讯行情适配器（qt.gtimg.cn 实时 + ifzq.gtimg.cn 前复权K线）。

- 实时行情 f72/f73/f76 = 当日总份额（CONFIRMED_BEHAVIOR EV015）
- K线仅 OHLC + 成交量（单位：手），不含份额（EV016）
- 腾讯为"独立供应商对账源"，不作官方源（补丁12-7）
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

QT_URL = "https://qt.gtimg.cn/q={symbols}"
FQKLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


@dataclass
class TencentQuote:
    code: str
    name: str
    close: float
    prev_close: float
    open: float
    high: float
    low: float
    volume: float  # 手
    amount_wan: float  # 万元
    total_shares: float | None  # 份（f72）
    timestamp: str


class TencentQuotesAdapter:
    SOURCE = "TENCENT_QUOTES"

    def __init__(self, timeout: int = 15) -> None:
        self._timeout = timeout

    def _symbol(self, code: str, exchange: str) -> str:
        prefix = "sh" if exchange == "SH" else "sz"
        return f"{prefix}{code}"

    def fetch_quote(self, code: str, exchange: str) -> TencentQuote | None:
        symbol = self._symbol(code, exchange)
        resp = requests.get(QT_URL.format(symbols=symbol), headers=HEADERS, timeout=self._timeout)
        resp.raise_for_status()
        text = resp.content.decode("gbk", errors="replace")
        if "~" not in text:
            return None
        parts = text.split("~")
        if len(parts) < 50:
            return None
        try:
            total_shares = float(parts[72]) if parts[72] else None
        except (ValueError, IndexError):
            total_shares = None
        return TencentQuote(
            code=parts[2],
            name=parts[1],
            close=float(parts[3]),
            prev_close=float(parts[4]),
            open=float(parts[5]),
            high=float(parts[33]),
            low=float(parts[34]),
            volume=float(parts[36]),  # 手
            amount_wan=float(parts[37]),  # 万元
            total_shares=total_shares,
            timestamp=parts[30],
        )

    def fetch_fqkline(self, code: str, exchange: str, start: str, end: str, count: int = 300) -> list[dict[str, Any]]:
        """前复权K线：date, open, close, high, low, volume(手)。分年度请求避免空/截断。"""
        out: list[dict[str, Any]] = []
        start_y = int(start[:4])
        end_y = int(end[:4])
        for y in range(start_y, end_y + 1):
            y_start = f"{y}-01-01"
            y_end = f"{y}-12-31"
            if y == start_y:
                y_start = start
            if y == end_y:
                y_end = end
            symbol = self._symbol(code, exchange)
            params = {"param": f"{symbol},day,{y_start},{y_end},{count},qfq"}
            resp = requests.get(FQKLINE_URL, params=params, headers=HEADERS, timeout=self._timeout)
            resp.raise_for_status()
            payload = resp.json()
            data = payload.get("data")
            if isinstance(data, dict):
                data = data.get(symbol, {})
            if not isinstance(data, dict):
                continue
            rows = data.get("qfqday") or data.get("day") or []
            for r in rows:
                out.append(
                    {
                        "date": r[0],
                        "open": float(r[1]),
                        "close": float(r[2]),
                        "high": float(r[3]),
                        "low": float(r[4]),
                        "volume": float(r[5]),  # 手
                        "source": self.SOURCE,
                        "fetched_at": datetime.now().isoformat(timespec="seconds"),
                    }
                )
        return out
