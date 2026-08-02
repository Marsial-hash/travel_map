"""搜狐指数/ETF历史行情适配器（hisHq）。

- 指数：zs_{index_code}，成交额字段单位=万元（已REPRODUCED EV017）
- ETF：cn_{code}，成交额字段单位=万元（已REPRODUCED EV018）
- 指数成交额字段语义（成分口径/跨市场/加工）未验证 → 仅称 vendor_reported_index_turnover
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

HISHQ_URL = "https://q.stock.sohu.com/hisHq"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


@dataclass
class SohuRow:
    date: str
    open: float
    close: float
    change: float
    change_pct: float
    low: float
    high: float
    volume: float
    amount_wan: float  # 万元


class SohuHisqAdapter:
    SOURCE = "SOHU_HISQ"

    def __init__(self, timeout: int = 15) -> None:
        self._timeout = timeout

    def _fetch(self, code: str, start: str, end: str) -> list[SohuRow]:
        params = {
            "code": code,
            "start": start.replace("-", ""),
            "end": end.replace("-", ""),
            "stat": "1",
            "order": "D",
            "period": "d",
        }
        resp = requests.get(HISHQ_URL, params=params, headers=HEADERS, timeout=self._timeout)
        resp.raise_for_status()
        payload = resp.json()
        rows: list[SohuRow] = []
        for item in payload:
            for hq in item.get("hq", []):
                # 行结构: date, open, close, change, change_pct(可能为"1.04%"), low, high, volume, amount(万元), ...
                change_pct_raw = hq[4]
                change_pct = float(str(change_pct_raw).replace("%", "")) if change_pct_raw not in ("", "-") else 0.0
                rows.append(
                    SohuRow(
                        date=hq[0],
                        open=float(hq[1]),
                        close=float(hq[2]),
                        change=float(hq[3]),
                        change_pct=change_pct,
                        low=float(hq[5]),
                        high=float(hq[6]),
                        volume=float(hq[7]),
                        amount_wan=float(hq[8]),
                    )
                )
        return rows

    def fetch_index(self, index_code: str, start: str, end: str) -> list[SohuRow]:
        """指数历史：zs_{code}。成交额单位=万元。"""
        return self._fetch(f"zs_{index_code}", start, end)

    def fetch_etf(self, code: str, start: str, end: str) -> list[SohuRow]:
        """ETF历史：cn_{code}。成交额单位=万元。"""
        return self._fetch(f"cn_{code}", start, end)
