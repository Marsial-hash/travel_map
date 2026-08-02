"""Tushare fund_share 适配器（方案B首选）。

官方字段仅 ts_code/trade_date/fd_share（万份）。
- 2000 行上限：returned_rows>=2000 → is_potentially_truncated=true
- 自动递归拆分（J-03）：按交易日历二分日期区间，合并去重+边界验证
- 记录语义（DAILY_SNAPSHOT/CHANGE_EVENT/MIXED_OR_UNKNOWN）由独立模块判定
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from data_pipeline.adapters.tushare_calendar import ApiCallResult, get_token
from data_pipeline.calendar.market_calendar import MarketCalendar

ROW_LIMIT = 2000
MAX_SPLIT_DEPTH = 8
MINIMUM_WINDOW_OPEN_DAYS = 5


@dataclass
class FundShareResult:
    """单次查询结果。"""

    ts_code: str
    api_result: ApiCallResult
    data: pd.DataFrame = field(default_factory=pd.DataFrame)


class FundShareAdapter:
    """fund_share 适配器。"""

    SOURCE = "TUSHARE_FUND_SHARE"
    ROW_LIMIT = ROW_LIMIT

    def __init__(self, token: str | None = None) -> None:
        import tushare as ts

        self._ts = ts
        self._token = token or get_token()

    @property
    def token_available(self) -> bool:
        return bool(self._token)

    def _query_single(self, ts_code: str, start: str, end: str) -> ApiCallResult:
        """单次查询（不拆分）。"""
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
            df = pro.fund_share(ts_code=ts_code, start_date=start.replace("-", ""), end_date=end.replace("-", ""))
            finished = dt.now()
            if df is None or df.empty:
                return ApiCallResult(
                    requested_start_date=start, requested_end_date=end, returned_min_date=None, returned_max_date=None,
                    returned_rows=0, hit_row_limit=False, is_potentially_truncated=False,
                    api_status="SUCCESS_EMPTY_VALID", api_error_code=None, api_error_message=None, retry_count=0,
                    request_started_at=started, request_finished_at=finished, request_parameters_hash=None,
                )
            rows = len(df)
            truncated = rows >= ROW_LIMIT
            min_d = df["trade_date"].min()
            max_d = df["trade_date"].max()
            return ApiCallResult(
                requested_start_date=start, requested_end_date=end,
                returned_min_date=f"{min_d[:4]}-{min_d[4:6]}-{min_d[6:]}",
                returned_max_date=f"{max_d[:4]}-{max_d[4:6]}-{max_d[6:]}",
                returned_rows=rows, hit_row_limit=truncated, is_potentially_truncated=truncated,
                api_status="POTENTIALLY_TRUNCATED" if truncated else "SUCCESS_WITH_DATA",
                api_error_code=None, api_error_message=None, retry_count=0,
                request_started_at=started, request_finished_at=finished, request_parameters_hash=None,
                data=df,
            )
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            status = "SOURCE_INTERNAL_ERROR"
            if "权限" in msg or "permission" in msg.lower() or "积分" in msg:
                status = "PERMISSION_DENIED"
            elif "限" in msg or "rate" in msg.lower():
                status = "RATE_LIMITED"
            return ApiCallResult(
                requested_start_date=start, requested_end_date=end, returned_min_date=None, returned_max_date=None,
                returned_rows=0, hit_row_limit=False, is_potentially_truncated=False,
                api_status=status, api_error_code=None, api_error_message=msg[:300], retry_count=0,
                request_started_at=started, request_finished_at=dt.now(), request_parameters_hash=None,
            )

    def fetch_complete_range(
        self,
        ts_code: str,
        start: date,
        end: date,
        calendar: MarketCalendar,
        depth: int = 0,
    ) -> ApiCallResult:
        """递归拆分查询（J-03）：>=2000 行自动二分。"""
        if depth > MAX_SPLIT_DEPTH:
            raise RecursionError(f"max split depth {MAX_SPLIT_DEPTH} exceeded for {ts_code}")
        open_days = [d for d in calendar.rows if calendar.is_open(d) and start <= d <= end]
        if len(open_days) < MINIMUM_WINDOW_OPEN_DAYS:
            # 窗口太小不再拆分
            pass
        result = self._query_single(ts_code, start.isoformat(), end.isoformat())
        if not result.is_potentially_truncated:
            return result
        # 需要拆分
        if len(open_days) <= MINIMUM_WINDOW_OPEN_DAYS:
            # 无法再拆，保持截断标记
            return result
        mid = open_days[len(open_days) // 2]
        left = self.fetch_complete_range(ts_code, start, mid, calendar, depth + 1)
        right_start = calendar.next_open_date(mid)
        if right_start is None or right_start > end:
            return left
        right = self.fetch_complete_range(ts_code, right_start, end, calendar, depth + 1)
        # 合并去重
        frames = [f for f in (left.data, right.data) if f is not None and not f.empty]
        if not frames:
            merged = pd.DataFrame()
        else:
            merged = pd.concat(frames).drop_duplicates(subset=["trade_date"]).sort_values("trade_date")
        merged_rows = len(merged)
        # 边界覆盖验证
        min_d = merged["trade_date"].min() if merged_rows else None
        max_d = merged["trade_date"].max() if merged_rows else None
        any_truncated = left.is_potentially_truncated or right.is_potentially_truncated
        return ApiCallResult(
            requested_start_date=start.isoformat(), requested_end_date=end.isoformat(),
            returned_min_date=min_d, returned_max_date=max_d,
            returned_rows=merged_rows, hit_row_limit=any_truncated, is_potentially_truncated=any_truncated,
            api_status="POTENTIALLY_TRUNCATED" if any_truncated else "SUCCESS_WITH_DATA",
            api_error_code=left.api_error_code or right.api_error_code,
            api_error_message=left.api_error_message or right.api_error_message,
            retry_count=left.retry_count + right.retry_count + 1,
            request_started_at=left.request_started_at,
            request_finished_at=right.request_finished_at,
            request_parameters_hash=None,
            data=merged,
        )
