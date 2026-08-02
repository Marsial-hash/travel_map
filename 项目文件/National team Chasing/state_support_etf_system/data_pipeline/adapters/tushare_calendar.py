"""Tushare 交易日历适配器。

trade_cal 官方字段：exchange/cal_date/is_open/pretrade_date
next_open_date 为派生字段（J-04），不在本适配器生成，由 MarketCalendar 派生。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass
class ApiCallResult:
    requested_start_date: str
    requested_end_date: str
    returned_min_date: str | None
    returned_max_date: str | None
    returned_rows: int
    hit_row_limit: bool
    is_potentially_truncated: bool
    api_status: str
    api_error_code: str | None
    api_error_message: str | None
    retry_count: int
    request_started_at: datetime | None
    request_finished_at: datetime | None
    request_parameters_hash: str | None
    data: pd.DataFrame = field(default_factory=pd.DataFrame)


API_STATUS = {
    "SUCCESS_WITH_DATA": "SUCCESS_WITH_DATA",
    "SUCCESS_EMPTY_VALID": "SUCCESS_EMPTY_VALID",
    "PERMISSION_DENIED": "PERMISSION_DENIED",
    "RATE_LIMITED": "RATE_LIMITED",
    "POTENTIALLY_TRUNCATED": "POTENTIALLY_TRUNCATED",
    "INVALID_INSTRUMENT": "INVALID_INSTRUMENT",
    "INVALID_DATE_RANGE": "INVALID_DATE_RANGE",
    "SOURCE_SCHEMA_CHANGED": "SOURCE_SCHEMA_CHANGED",
    "NETWORK_FAILURE": "NETWORK_FAILURE",
    "SOURCE_INTERNAL_ERROR": "SOURCE_INTERNAL_ERROR",
}


class TokenDetector:
    """Token 检测，日志只允许输出 detected: yes/no。"""

    @staticmethod
    def detected() -> bool:
        env = os.environ.get("TUSHARE_TOKEN")
        if env:
            return True
        # .env 文件（不读取值，仅检测存在且非空）
        try:
            from pathlib import Path

            for p in (Path(".env"), Path.home() / ".env"):
                if p.exists():
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    if "TUSHARE_TOKEN" in text and "=" in text:
                        return True
        except Exception:  # noqa: S110 - Token 检测失败视为未检测到，不输出任何Token信息
            pass
        return False


def get_token() -> str | None:
    """读取 Token（不打印、不哈希、不入日志）。"""
    env = os.environ.get("TUSHARE_TOKEN")
    if env:
        return env.strip()
    try:
        from pathlib import Path

        for p in (Path(".env"), Path.home() / ".env"):
            if p.exists():
                for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if line.startswith("TUSHARE_TOKEN="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
    except Exception:
        return None
    return None


class TushareCalendarAdapter:
    """trade_cal 适配器。"""

    SOURCE = "TUSHARE_TRADE_CAL"

    def __init__(self, token: str | None = None) -> None:
        import tushare as ts

        self._ts = ts
        self._token = token or get_token()

    @property
    def token_available(self) -> bool:
        return bool(self._token)

    def fetch_calendar(self, exchange: str, start: str, end: str) -> ApiCallResult:
        """拉取交易日历。exchange: SSE/SZSE。"""
        from datetime import datetime as dt

        started = dt.now()
        if not self._token:
            return ApiCallResult(
                requested_start_date=start, requested_end_date=end, returned_min_date=None, returned_max_date=None,
                returned_rows=0, hit_row_limit=False, is_potentially_truncated=False,
                api_status="PERMISSION_DENIED", api_error_code="NO_TOKEN",
                api_error_message="TUSHARE_TOKEN not detected", retry_count=0,
                request_started_at=started, request_finished_at=None, request_parameters_hash=None,
            )
        try:
            pro = self._ts.pro_api(self._token)
            df = pro.trade_cal(exchange=exchange, start_date=start.replace("-", ""), end_date=end.replace("-", ""))
            finished = dt.now()
            if df is None or df.empty:
                return ApiCallResult(
                    requested_start_date=start, requested_end_date=end, returned_min_date=None, returned_max_date=None,
                    returned_rows=0, hit_row_limit=False, is_potentially_truncated=False,
                    api_status="SUCCESS_EMPTY_VALID", api_error_code=None, api_error_message=None, retry_count=0,
                    request_started_at=started, request_finished_at=finished, request_parameters_hash=None,
                )
            min_d = df["cal_date"].min()
            max_d = df["cal_date"].max()
            return ApiCallResult(
                requested_start_date=start, requested_end_date=end,
                returned_min_date=f"{min_d[:4]}-{min_d[4:6]}-{min_d[6:]}",
                returned_max_date=f"{max_d[:4]}-{max_d[4:6]}-{max_d[6:]}",
                returned_rows=len(df), hit_row_limit=False, is_potentially_truncated=False,
                api_status="SUCCESS_WITH_DATA", api_error_code=None, api_error_message=None, retry_count=0,
                request_started_at=started, request_finished_at=finished, request_parameters_hash=None,
                data=df,
            )
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            status = "SOURCE_INTERNAL_ERROR"
            if "权限" in msg or "permission" in msg.lower():
                status = "PERMISSION_DENIED"
            elif "限" in msg or "rate" in msg.lower():
                status = "RATE_LIMITED"
            return ApiCallResult(
                requested_start_date=start, requested_end_date=end, returned_min_date=None, returned_max_date=None,
                returned_rows=0, hit_row_limit=False, is_potentially_truncated=False,
                api_status=status, api_error_code=None, api_error_message=msg[:300], retry_count=0,
                request_started_at=started, request_finished_at=dt.now(), request_parameters_hash=None,
            )
