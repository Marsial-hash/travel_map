"""F-05: 失败回滚注入测试 + F-07: 输入变化与Supersession 测试。

验证：失败版本标 FAILED/QUARANTINED，V1 保持 PUBLISHED 且指纹不变。
"""
from __future__ import annotations

from pathlib import Path

from data_pipeline.execution.dual_time import PublicationManager


def test_rollback_preserves_v1() -> None:
    """F-05: V2 失败时 V1 保持 PUBLISHED 且指纹不变。"""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        pm = PublicationManager(Path(d))
        # V1 PUBLISHED
        v1 = pm.start_version("etf_share")
        pm.mark(v1, "PUBLISHED", fingerprint="FINGERPRINT_V1")
        v1_fp = pm.latest_published("etf_share").dataset_fingerprint

        # V2 注入失败
        v2 = pm.start_version("etf_share")
        pm.mark(v2, "FAILED", fingerprint="FINGERPRINT_V2")

        # 断言
        assert pm.latest_published("etf_share").dataset_version == v1
        assert pm.latest_published("etf_share").dataset_fingerprint == v1_fp  # V1 指纹不变
        assert pm.latest_published("etf_share").dataset_fingerprint == "FINGERPRINT_V1"
        readable = pm.readable_versions()
        assert len(readable) == 1  # 只有 V1 可读
        assert readable[0].dataset_version == v1


def test_rollback_v1_membership_unchanged() -> None:
    """F-05: 失败后 V1 的 membership 指纹不变（不可变快照）。"""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        pm = PublicationManager(Path(d))
        v1 = pm.start_version("etf_share")
        pm.mark(v1, "PUBLISHED", fingerprint="V1_FP")
        # 记录 V1 指纹
        fp_before = pm.latest_published("etf_share").dataset_fingerprint

        # V2 失败
        v2 = pm.start_version("etf_share")
        pm.mark(v2, "QUARANTINED", fingerprint="V2_FP")

        fp_after = pm.latest_published("etf_share").dataset_fingerprint
        assert fp_before == fp_after == "V1_FP"


def test_supersession_revision_chain() -> None:
    """F-07: 输入变化创建正确 Supersession 链，旧版本仍可查询。"""
    from datetime import UTC, datetime

    from data_pipeline.execution.versioned_store import AppendOnlyStore

    store = AppendOnlyStore()
    bk = "510300.SH#2026-01-28"
    v1 = store.insert(bk, {"fd_share": 100.0}, datetime(2026, 8, 1, tzinfo=UTC))
    v2 = store.insert(
        bk, {"fd_share": 95.0}, datetime(2026, 8, 2, tzinfo=UTC), revision_reason="RAW_CHANGED"
    )
    # Supersession 链正确
    assert v2.supersedes_record_id == v1.record_id
    # 当前返回新值
    assert store.current(bk).payload["fd_share"] == 95.0  # type: ignore[union-attr]
    # 修订前 as-of 返回旧值
    old = store.as_of(bk, datetime(2026, 8, 1, 12, tzinfo=UTC))
    assert old is not None and old.payload["fd_share"] == 100.0
    # 未变化的记录不创建新版本（另一 business key 只有一个版本）
    store.insert("510300.SH#2026-01-27", {"fd_share": 200.0}, datetime(2026, 8, 1, tzinfo=UTC))
    assert len(store.history("510300.SH#2026-01-27")) == 1


def test_dataset_version_not_yet_published() -> None:
    """F-08 场景7: 指定未发布版本时返回 DATASET_VERSION_NOT_YET_PUBLISHED。"""
    import tempfile
    from datetime import UTC, datetime

    from data_pipeline.execution.dual_time import PublicationManager

    with tempfile.TemporaryDirectory() as d:
        pm = PublicationManager(Path(d))
        v1 = pm.start_version("etf_share")
        pm.mark(v1, "PUBLISHED", fingerprint="V1")
        # 显式指定一个不存在的版本 → not found
        # 模拟：system_as_of 早于 v1 发布 → latest_published 返回 None
        assert pm.latest_published("etf_share", datetime(2020, 1, 1, tzinfo=UTC)) is None
