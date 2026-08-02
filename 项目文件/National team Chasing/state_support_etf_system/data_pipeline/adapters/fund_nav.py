"""天天基金 NAV 历史适配器（f10/lsjz）。

- 历史覆盖自2014年（510300实测 CONFIRMED_BEHAVIOR EV019）
- 净值发布时点未连续观察 → 保守政策 T+1 09:30
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

LSJZ_URL = "https://api.fund.eastmoney.com/f10/lsjz"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://fundf10.eastmoney.com/",
}


@dataclass
class NavRow:
    trade_date: str
    nav: float  # 单位净值
    cumulative_nav: float  # 累计净值
    daily_change_pct: str


class FundNavAdapter:
    SOURCE = "EM_NAV"

    def __init__(self, timeout: int = 15) -> None:
        self._timeout = timeout

    def fetch_history(self, fund_code: str, start: str | None = None, end: str | None = None) -> list[NavRow]:
        """分页获取NAV历史（实测pageSize上限20，100/500/10000均截断或返回null）。"""
        rows: list[NavRow] = []
        page = 1
        while True:
            params = {"fundCode": fund_code, "pageIndex": str(page), "pageSize": "20"}
            if start:
                params["startDate"] = start  # 天天基金要求 YYYY-MM-DD（实测 dash 格式生效）
            if end:
                params["endDate"] = end
            resp = requests.get(LSJZ_URL, params=params, headers=HEADERS, timeout=self._timeout)
            resp.raise_for_status()
            payload = resp.json()
            data = payload.get("Data") if isinstance(payload, dict) else None
            items = (data or {}).get("LSJZList") or []
            if not items:
                break
            for item in items:
                rows.append(
                    NavRow(
                        trade_date=item["FSRQ"],
                        nav=float(item["DWJZ"]),
                        cumulative_nav=float(item["LJJZ"]) if item.get("LJJZ") else 0.0,
                        daily_change_pct=item.get("JZZZL", ""),
                    )
                )
            if len(items) < 20:
                break
            page += 1
        return rows
