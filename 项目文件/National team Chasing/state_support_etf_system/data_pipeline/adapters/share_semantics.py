"""fund_share 记录语义判定（DAILY_SNAPSHOT / CHANGE_EVENT / MIXED_OR_UNKNOWN）。

验证流程（依据规格）：
1. 6只ETF完整区间数据
2. 与交易日历连接，检查开放日是否有记录
3. 份额不变日是否有记录
4. 找 ≥5 个"相邻开放日份额相同"的转移样本（不要求连续）
5. 缺失日前后份额是否一致
6. 判断能否无歧义前向填充
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import pandas as pd


class FundShareRecordSemantics(StrEnum):
    DAILY_SNAPSHOT = "DAILY_SNAPSHOT"
    CHANGE_EVENT = "CHANGE_EVENT"
    MIXED_OR_UNKNOWN = "MIXED_OR_UNKNOWN"


@dataclass
class SemanticsVerdict:
    semantics: FundShareRecordSemantics
    open_days_total: int
    records_count: int
    records_per_open_day: float
    unchanged_transfer_samples: int
    missing_days_with_same_value: int
    missing_days_with_changed_value: int
    forward_fill_unambiguous: bool
    evidence: str


def determine_record_semantics(
    df: pd.DataFrame,
    open_dates: list[date],
) -> SemanticsVerdict:
    """判定记录语义。

    df: trade_date(YYYYMMDD或YYYY-MM-DD) + fd_share
    open_dates: 区间内全部开放日
    """
    if df is None or df.empty:
        return SemanticsVerdict(
            semantics=FundShareRecordSemantics.MIXED_OR_UNKNOWN,
            open_days_total=len(open_dates), records_count=0, records_per_open_day=0.0,
            unchanged_transfer_samples=0, missing_days_with_same_value=0, missing_days_with_changed_value=0,
            forward_fill_unambiguous=False, evidence="empty dataframe",
        )

    def norm(d: str) -> str:
        return d.replace("-", "")

    records: dict[str, float] = {}
    for _, row in df.iterrows():
        records[norm(str(row["trade_date"]))] = float(row["fd_share"])

    open_days_norm = [norm(d.isoformat()) for d in open_dates]

    # 1) 开放日覆盖率
    covered = sum(1 for d in open_days_norm if d in records)
    missing_days = [d for d in open_days_norm if d not in records]

    # 2) 相邻开放日份额相同转移样本（不要求连续出现，只统计出现过的"份额不变"转移）
    unchanged_samples = 0
    checked_pairs = 0
    for i in range(len(open_days_norm) - 1):
        d1, d2 = open_days_norm[i], open_days_norm[i + 1]
        if d1 in records and d2 in records:
            checked_pairs += 1
            if records[d1] == records[d2]:
                unchanged_samples += 1

    # 3) 缺失日前后份额是否一致（事后质量重建，EX_POST）
    missing_same = 0
    missing_changed = 0
    for d in missing_days:
        # 找该缺失日前最近有记录日、后最近有记录日
        before = [x for x in open_days_norm if x < d and x in records]
        after = [x for x in open_days_norm if x > d and x in records]
        if before and after:
            b_val = records[before[-1]]
            a_val = records[after[0]]
            if abs(b_val - a_val) < 1e-12:
                missing_same += 1
            else:
                missing_changed += 1

    # 4) 语义判定
    # 若几乎所有开放日都有记录（>95%）→ DAILY_SNAPSHOT
    coverage_ratio = covered / len(open_days_norm) if open_days_norm else 0.0
    if coverage_ratio >= 0.95:
        semantics = FundShareRecordSemantics.DAILY_SNAPSHOT
        forward_fill = True
        evidence = f"coverage={coverage_ratio:.1%}, unchanged_transfer_samples={unchanged_samples}"
    elif unchanged_samples >= 5:
        # 存在≥5个份额不变转移样本 → 可基于已公开记录前向延续（PIT_FORWARD_ONLY）
        semantics = FundShareRecordSemantics.CHANGE_EVENT
        forward_fill = True
        evidence = (
            f"unchanged_transfer_samples={unchanged_samples}, missing_same={missing_same}, "
            f"missing_changed={missing_changed}, coverage={coverage_ratio:.1%}"
        )
    else:
        semantics = FundShareRecordSemantics.MIXED_OR_UNKNOWN
        forward_fill = False
        evidence = (
            f"coverage={coverage_ratio:.1%}, unchanged_transfer_samples={unchanged_samples}, "
            f"missing_same={missing_same}, missing_changed={missing_changed}"
        )

    return SemanticsVerdict(
        semantics=semantics,
        open_days_total=len(open_days_norm),
        records_count=len(records),
        records_per_open_day=round(len(records) / len(open_days_norm), 3) if open_days_norm else 0.0,
        unchanged_transfer_samples=unchanged_samples,
        missing_days_with_same_value=missing_same,
        missing_days_with_changed_value=missing_changed,
        forward_fill_unambiguous=forward_fill,
        evidence=evidence,
    )


def pit_forward_only_reconstruction(
    records: dict[date, float],
    evaluation_timestamp: date,
) -> float | None:
    """PIT 前向重建（M-02）：value_at_t = 最近一条 research_available_at <= t 的记录。

    不得使用未来记录反向确认。
    """
    applicable = {d: v for d, v in records.items() if d <= evaluation_timestamp}
    if not applicable:
        return None
    latest = max(applicable.keys())
    return applicable[latest]
