"""A股交易日历与交易时段模型。

- market_calendar: 交易日历（Tushare trade_cal 或备用公开源）
- market_session_calendar: 交易时段（Asia/Shanghai）
- next_open_date 为派生字段（lead over open dates），记计算版本
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ASIA_SHANGHAI = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class MarketSession:
    """A股交易时段（默认沪深一致，可按交易所覆盖）。"""

    exchange: str
    timezone: str = "Asia/Shanghai"
    pre_open_auction_start: time = time(9, 15)
    pre_open_auction_end: time = time(9, 25)
    morning_session_start: time = time(9, 30)
    morning_session_end: time = time(11, 30)
    afternoon_session_start: time = time(13, 0)
    afternoon_session_end: time = time(15, 0)
    closing_auction_start: time = time(14, 57)
    closing_auction_end: time = time(15, 0)


DEFAULT_SESSIONS: dict[str, MarketSession] = {
    "SSE": MarketSession("SSE"),
    "SZSE": MarketSession("SZSE"),
}


@dataclass
class MarketCalendar:
    """交易日历。

    字段: exchange/calendar_date/is_open/previous_open_date/next_open_date/source/calendar_version
    next_open_date 为派生字段（J-04），由开放日序列 lead() 计算并记版本。
    """

    rows: dict[date, dict[str, object]]  # calendar_date -> row
    source: str = ""
    calendar_version: str = ""
    next_open_date_calculation_version: str = "v1-lead-over-open-dates"

    @classmethod
    def from_open_dates(cls, exchange: str, open_dates: list[date], source: str, version: str) -> MarketCalendar:
        set(open_dates)
        all_dates = sorted(open_dates)
        # 前一个开放日
        prev: dict[date, date | None] = {}
        last_open: date | None = None
        for d in all_dates:
            prev[d] = last_open
            last_open = d
        # 下一个开放日（lead）
        nxt: dict[date, date | None] = {}
        for i, d in enumerate(all_dates):
            nxt[d] = all_dates[i + 1] if i + 1 < len(all_dates) else None
        rows: dict[date, dict[str, object]] = {}
        for d in all_dates:
            rows[d] = {
                "exchange": exchange,
                "calendar_date": d,
                "is_open": True,
                "previous_open_date": prev[d],
                "next_open_date": nxt[d],
                "source": source,
                "calendar_version": version,
            }
        return cls(rows=rows, source=source, calendar_version=version)

    def is_open(self, d: date) -> bool:
        row = self.rows.get(d)
        return bool(row and row["is_open"])

    def previous_open_date(self, d: date) -> date | None:
        row = self.rows.get(d)
        if row:
            return row["previous_open_date"]  # type: ignore[return-value]
        # 非开放日：找最近开放日
        for offset in range(1, 30):
            cand = d - timedelta(days=offset)
            if cand in self.rows:
                return cand
        return None

    def next_open_date(self, d: date) -> date | None:
        row = self.rows.get(d)
        if row:
            return row["next_open_date"]  # type: ignore[return-value]
        for offset in range(1, 30):
            cand = d + timedelta(days=offset)
            if cand in self.rows:
                return cand
        return None

    def open_session_distance(self, d1: date, d2: date) -> int:
        """两个观测日之间的开放日距离（周一->周二=1，J-01）。"""
        if d1 == d2:
            return 0
        if d2 < d1:
            d1, d2 = d2, d1
        count = 0
        cur = d1
        while cur < d2:
            nxt = self.next_open_date(cur)
            if nxt is None or nxt > d2:
                # 最后一个开放日不足；按日历逐日计数开放日
                break
            count += 1
            cur = nxt
        if cur == d1:
            # 直接逐日数
            count = sum(1 for offset in range(1, (d2 - d1).days + 1) if self.is_open(d1 + timedelta(days=offset)))
        return count

    def missing_open_session_count(self, d1: date, d2: date) -> int:
        """两观测日之间缺失的开放日数量（周一->周三且周二缺数据=1）。"""
        if d2 < d1:
            d1, d2 = d2, d1
        expected = self.open_session_distance(d1, d2)
        # 若d2的previous_open_date不是d1，则中间有缺失
        prev_of_d2 = self.previous_open_date(d2)
        if prev_of_d2 is None:
            return expected
        if prev_of_d2 == d1:
            return 0
        # 从d1到d2之间开放日数量 - 1（d2自身）
        return self.open_session_distance(d1, d2) - 1

    def add_open_days(self, d: date, n: int) -> date:
        """从d开始往后第n个开放日（n>=1）。"""
        cur = d
        for _ in range(n):
            nxt = self.next_open_date(cur)
            if nxt is None:
                raise ValueError(f"no next open date after {cur}")
            cur = nxt
        return cur


def is_within_session(dt: datetime, session: MarketSession) -> bool:
    """判断时间是否处于连续竞价时段（09:30-11:30, 13:00-15:00）。"""
    t = dt.astimezone(ASIA_SHANGHAI).time()
    if session.morning_session_start <= t < session.morning_session_end:
        return True
    if session.afternoon_session_start <= t < session.afternoon_session_end:
        return True
    return False


def next_valid_execution_time(
    dt: datetime,
    calendar: MarketCalendar,
    session: MarketSession,
) -> datetime:
    """数据可用/决策时间之后第一个合法交易时段时间点（最小粒度1分钟）。

    硬规则：不在午休/收盘后/节假日生成非法时间。
    """
    cur = dt.astimezone(ASIA_SHANGHAI)
    # 先移到当天开放日检查
    day = cur.date()
    while not calendar.is_open(day):
        nxt = calendar.next_open_date(day)
        if nxt is None:
            raise ValueError(f"no next open date after {day}")
        day = nxt
        cur = datetime.combine(day, session.morning_session_start, tzinfo=ASIA_SHANGHAI)
    t = cur.time()
    if t < session.morning_session_start:
        return datetime.combine(day, session.morning_session_start, tzinfo=ASIA_SHANGHAI)
    if session.morning_session_start <= t < session.morning_session_end:
        # 同日上午，最小1分钟
        return cur.replace(second=0, microsecond=0) + timedelta(minutes=1)
    if session.morning_session_end <= t < session.afternoon_session_start:
        # 午休：返回13:00
        return datetime.combine(day, session.afternoon_session_start, tzinfo=ASIA_SHANGHAI)
    if session.afternoon_session_start <= t < session.afternoon_session_end:
        return cur.replace(second=0, microsecond=0) + timedelta(minutes=1)
    # 收盘后：下一开放日09:30
    nxt = calendar.next_open_date(day)
    if nxt is None:
        raise ValueError(f"no next open date after {day}")
    return datetime.combine(nxt, session.morning_session_start, tzinfo=ASIA_SHANGHAI)


def load_calendar_from_parquet(path: str, exchange: str = "SSE") -> MarketCalendar:
    """从Parquet加载日历（备用路径）。"""
    import polars as pl

    df = pl.read_parquet(path)
    open_dates = [d for d in df.filter(pl.col("is_open")).get_column("calendar_date").to_list()]
    return MarketCalendar.from_open_dates(
        exchange=exchange,
        open_dates=open_dates,
        source=path,
        version="loaded",
    )
