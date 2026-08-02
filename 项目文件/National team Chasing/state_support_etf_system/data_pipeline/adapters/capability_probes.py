"""能力探针（J-06）：未实现/未验证的适配器返回结构化 CapabilityProbeResult。

不得用硬编码成功、假DataFrame、参考站数据冒充、静默空表伪装。
"非空壳" = 有可执行Schema + 错误分类 + 能力检测 + 真实失败报告。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ProbeStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class CapabilityProbeResult:
    source_id: str
    status: ProbeStatus
    supported: bool
    reason: str
    evidence_ids: list[str] = field(default_factory=list)
    detail: str = ""


class ExchangeSharesAdapter:
    """交易所历史份额适配器（A1候选）。

    本轮实测：上交所 query 6 sqlId 全空、深交所 ShowReport 空/404（EV022/EV023）。
    因此真实数据路径未建立 → 返回 UNVERIFIED 探针结果。
    """

    SOURCE = "SSE_QUERY/SZSE_REPORT"

    def probe(self) -> CapabilityProbeResult:
        return CapabilityProbeResult(
            source_id=self.SOURCE,
            status=ProbeStatus.UNVERIFIED,
            supported=False,
            reason="NO_VALIDATED_ENDPOINT",
            evidence_ids=["EV022", "EV023"],
            detail="上交所query接口6个sqlId全空；深交所ShowReport/GetEtfDaily空/404；无outstanding_total_shares稳定接口",
        )

    def fetch_outstanding_total_shares(self, code: str, start: str, end: str) -> CapabilityProbeResult:
        """A1：交易所历史总份额。未建立真实路径，禁止返回假数据。"""
        return self.probe()

    def fetch_pcf(self, code: str, start: str, end: str) -> CapabilityProbeResult:
        """A2：PCF数据（最小申赎单位/现金替代等）。与存量份额严格分离。"""
        return CapabilityProbeResult(
            source_id=self.SOURCE,
            status=ProbeStatus.UNVERIFIED,
            supported=False,
            reason="NO_VALIDATED_ENDPOINT",
            evidence_ids=["EV022", "EV023"],
            detail="PCF数据路径未建立；PCF不得映射为canonical_raw_total_shares",
        )


class FundDisclosuresAdapter:
    """基金持仓披露适配器。

    流程：自动下载PDF → 保存PDF+SHA-256 → 定位前十大持有人候选页 → 抽取候选表格
    → 识别机构名称 → 人工复核。Phase 0B 至少测试两家管理人。
    扫描版标 MANUAL_REVIEW_REQUIRED。
    """

    SOURCE = "FUND_DISCLOSURE"

    def probe(self) -> CapabilityProbeResult:
        return CapabilityProbeResult(
            source_id=self.SOURCE,
            status=ProbeStatus.UNVERIFIED,
            supported=False,
            reason="NO_VALIDATED_ENDPOINT",
            evidence_ids=[],
            detail="PDF下载/解析路径待Phase 0B建立；需≥2家管理人样本",
        )

    def download_and_extract(self, fund_code: str, report_period: str) -> CapabilityProbeResult:
        return self.probe()


class TushareFundDailyAdapter:
    """Tushare fund_daily（ETF行情）适配器（Canonical行情候选）。

    需2000积分；本轮作为候选记录，权限实测在Phase 0B进行。
    """

    SOURCE = "TUSHARE_FUND_DAILY"

    def probe(self) -> CapabilityProbeResult:
        return CapabilityProbeResult(
            source_id=self.SOURCE,
            status=ProbeStatus.UNVERIFIED,
            supported=False,
            reason="PENDING_PERMISSION_TEST",
            evidence_ids=[],
            detail="fund_daily需2000积分；Phase 0B以真实Token实测",
        )
