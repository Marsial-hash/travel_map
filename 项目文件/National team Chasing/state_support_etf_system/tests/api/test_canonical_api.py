"""FastAPI 只读 API 测试（双时间参数 + 时区校验 + PUBLISHED 隔离）。"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.canonical_api import app

client = TestClient(app)


class TestAPI:
    def test_health(self) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_instruments(self) -> None:
        r = client.get("/api/v1/instruments")
        assert r.status_code == 200
        assert r.json()["count"] >= 6

    def test_flows_requires_knowledge_as_of(self) -> None:
        """knowledge_as_of_timestamp 必须显式传入（否则422）。"""
        r = client.get("/api/v1/instruments/INST-510300/flows")
        assert r.status_code == 422
        assert "knowledge_as_of_timestamp" in r.json()["detail"]

    def test_flows_with_knowledge_as_of(self) -> None:
        r = client.get(
            "/api/v1/instruments/INST-510300/flows",
            params={"knowledge_as_of_timestamp": "2026-08-01T09:30:00+08:00"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "rows" in body
        assert body["is_estimate"] is True

    def test_missing_timezone_rejected(self) -> None:
        """缺时区的 ISO8601 → 422。"""
        r = client.get(
            "/api/v1/instruments/INST-510300/flows",
            params={"knowledge_as_of_timestamp": "2026-08-01T09:30:00"},  # 无时区
        )
        assert r.status_code == 422

    def test_availability_policies(self) -> None:
        r = client.get("/api/v1/availability-policies")
        assert r.status_code == 200
        assert len(r.json()["policies"]) >= 8

    def test_source_selection_policies(self) -> None:
        r = client.get("/api/v1/source-selection-policies")
        assert r.status_code == 200
        assert len(r.json()["policies"]) >= 10

    def test_data_quality_issues(self) -> None:
        r = client.get("/api/v1/data-quality/issues")
        assert r.status_code == 200

    def test_dataset_versions(self) -> None:
        r = client.get("/api/v1/dataset-versions")
        assert r.status_code == 200

    def test_no_trading_advice(self) -> None:
        """API 不得返回买卖建议或介入概率。"""
        r = client.get(
            "/api/v1/instruments/INST-510300/flows",
            params={"knowledge_as_of_timestamp": "2026-08-01T09:30:00+08:00"},
        )
        body_text = str(r.json()).lower()
        assert "买入" not in body_text and "sell" not in body_text
        assert "介入概率" not in body_text
