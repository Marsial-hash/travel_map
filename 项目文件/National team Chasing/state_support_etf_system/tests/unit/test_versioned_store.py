"""Append-only 双时间版本模型测试。"""
from __future__ import annotations

from datetime import UTC, datetime

from data_pipeline.execution.versioned_store import AppendOnlyStore


def ts(y: int, m: int, d: int, h: int = 10) -> datetime:
    return datetime(y, m, d, h, 0, tzinfo=UTC)


class TestAppendOnlyStore:
    def test_insert_and_current(self) -> None:
        store = AppendOnlyStore()
        store.insert("510300.SH#2026-01-27", {"fd_share": 100.0}, ts(2026, 1, 28))
        cur = store.current("510300.SH#2026-01-27")
        assert cur is not None
        assert cur.record_version == 1
        assert cur.payload["fd_share"] == 100.0

    def test_revision_appends_not_overwrites(self) -> None:
        """初始100 → 修订105：v1不删除，as-of查询返回旧值。"""
        store = AppendOnlyStore()
        bk = "510300.SH#2026-01-27"
        store.insert(bk, {"fd_share": 100.0}, ts(2026, 1, 28, 10))
        store.insert(bk, {"fd_share": 105.0}, ts(2026, 1, 28, 15), revision_reason="source revision")

        assert store.current(bk) is not None
        assert store.current(bk).payload["fd_share"] == 105.0  # type: ignore[union-attr]
        assert store.current(bk).record_version == 2  # type: ignore[union-attr]

        # as-of 修订前 → 100
        as_of_old = store.as_of(bk, ts(2026, 1, 28, 11))
        assert as_of_old is not None
        assert as_of_old.payload["fd_share"] == 100.0
        # 恰好等于修订生效时刻 → 新版本生效（system_valid_to 为开区间，as_of >= to 时旧版失效）
        as_of_boundary = store.as_of(bk, ts(2026, 1, 28, 15))
        assert as_of_boundary is not None
        assert as_of_boundary.payload["fd_share"] == 105.0

        # as-of 修订后 → 105
        as_of_new = store.as_of(bk, ts(2026, 1, 28, 16))
        assert as_of_new is not None
        assert as_of_new.payload["fd_share"] == 105.0

        # v1 未被删除
        assert len(store.history(bk)) == 2
        assert store.history(bk)[0].record_version == 1

    def test_payload_hash_immutable(self) -> None:
        store = AppendOnlyStore()
        bk = "test#1"
        r1 = store.insert(bk, {"fd_share": 100.0}, ts(2026, 1, 1))
        # 修改payload对象（模拟误改）不影响已存哈希
        assert store.payload_hash({"fd_share": 100.0}) == r1.source_payload_hash

    def test_supersedes_chain(self) -> None:
        store = AppendOnlyStore()
        bk = "test#2"
        r1 = store.insert(bk, {"v": 1}, ts(2026, 1, 1))
        r2 = store.insert(bk, {"v": 2}, ts(2026, 1, 2))
        assert r2.supersedes_record_id == r1.record_id
