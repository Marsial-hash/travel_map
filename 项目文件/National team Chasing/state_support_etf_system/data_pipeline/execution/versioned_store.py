"""Append-only 双时间版本模型（严格 append-only）。

- 业务载荷不可变（source_payload_hash 对应内容一旦写入不变更）
- 修订通过追加新版本 + supersedes_record_id 链实现
- 历史 as-of 查询返回当时有效版本
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class VersionedRecord:
    record_id: str
    business_key: str
    record_version: int
    system_valid_from: datetime
    system_valid_to: datetime | None
    is_current: bool
    supersedes_record_id: str | None
    revision_reason: str | None
    source_payload_hash: str
    calculation_input_fingerprint: str | None
    calculation_version: str | None
    metric_contract_version: str | None
    payload: dict[str, Any] = field(default_factory=dict)

    def effective_at(self, as_of: datetime) -> bool:
        return self.system_valid_from <= as_of and (self.system_valid_to is None or as_of < self.system_valid_to)

    def is_effective_at(self, as_of: datetime) -> bool:
        return self.system_valid_from <= as_of and (self.system_valid_to is None or as_of < self.system_valid_to)


class AppendOnlyStore:
    """严格 append-only 存储：payload 不可变，修订追加新版本。"""

    def __init__(self) -> None:
        self._records: list[VersionedRecord] = []

    @staticmethod
    def payload_hash(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def insert(
        self,
        business_key: str,
        payload: dict[str, Any],
        system_valid_from: datetime,
        *,
        revision_reason: str | None = None,
        calculation_version: str | None = None,
        metric_contract_version: str | None = None,
    ) -> VersionedRecord:
        """新增版本。若 business_key 已有当前版本，将其 system_valid_to 关闭并追加新版本。"""
        existing_current = [r for r in self._records if r.business_key == business_key and r.is_current]
        new_version = (max((r.record_version for r in self._records if r.business_key == business_key), default=0)) + 1
        # 关闭旧版本（仅更新 system_valid_to/is_current，payload 不变）
        for r in existing_current:
            r.system_valid_to = system_valid_from
            r.is_current = False
        record = VersionedRecord(
            record_id=f"{business_key}#v{new_version}",
            business_key=business_key,
            record_version=new_version,
            system_valid_from=system_valid_from,
            system_valid_to=None,
            is_current=True,
            supersedes_record_id=existing_current[-1].record_id if existing_current else None,
            revision_reason=revision_reason,
            source_payload_hash=self.payload_hash(payload),
            calculation_input_fingerprint=payload.get("_input_fingerprint"),
            calculation_version=calculation_version,
            metric_contract_version=metric_contract_version,
            payload=payload,
        )
        self._records.append(record)
        return record

    def current(self, business_key: str) -> VersionedRecord | None:
        for r in reversed(self._records):
            if r.business_key == business_key and r.is_current:
                return r
        return None

    def as_of(self, business_key: str, as_of_ts: datetime) -> VersionedRecord | None:
        """历史 as-of 查询：system_valid_from <= as_of < system_valid_to。"""
        candidates = [r for r in self._records if r.business_key == business_key and r.is_effective_at(as_of_ts)]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.system_valid_from)

    def history(self, business_key: str) -> list[VersionedRecord]:
        return [r for r in self._records if r.business_key == business_key]
