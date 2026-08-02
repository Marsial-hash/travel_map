# Universe 政策（Universe Policy）

- 版本：1.0.0
- 关联：registry/reference_universe.csv、registry/research_universe.csv

## 一、双 Universe 分离

### Reference Replication Universe（reference_universe.csv）
- 41只ETF、16个方向分组、9个趋势映射、dashboard_eligible
- 来源：参考站 universe.json 快照（EV004，sha256=791c461a2b2b9b64）
- 用途：仅复刻参考网站；**不得作为Canonical研究池**
- 有效区间：按快照日期 2026-08-02 起

### State Support Research Universe（research_universe.csv）
- 只纳入在对应历史时间点**已有公开证据**支持的ETF
- 字段：internal_instrument_id / institution_id / evidence_type / evidence_document / evidence_report_period / evidence_published_at / research_available_at / valid_from / valid_to / confidence_level / verification_status / reviewer / notes
- 证据类型：OFFICIAL_ANNOUNCEMENT / FUND_PERIODIC_REPORT / REGULATORY_CONFIRMATION / MANUAL_VERIFIED_DISCLOSURE / REFERENCE_SITE_ONLY / MEDIA_REPORT / UNKNOWN
- **REFERENCE_SITE_ONLY 与 MEDIA_REPORT 不得作为高置信度研究证据**

## 二、历史查询规则（防未来披露污染）

```sql
WHERE research_available_at <= :evaluation_timestamp
  AND valid_from <= :trade_date
  AND (valid_to IS NULL OR :trade_date <= valid_to)
```

**禁止**：使用2026年披露的持仓信息把某ETF放进2024年的研究池。

## 三、历史范围目标

- MVP可视化窗口：参考站现有区间（2024-01 ~ 今）
- 最低研究窗口：2018至今
- 理想研究窗口：2015至今
- 若份额历史无法覆盖至2018，第一版只能输出证据分，不得称为统计校准概率

## 四、份额源决策（Phase 0B 输出）

- FREE_PUBLIC_SOURCE_SELECTED / TUSHARE_OR_PAID_API_SELECTED / COMMERCIAL_VENDOR_SELECTED / NO_SUSTAINABLE_SOURCE
- 未批准前：canonical 历史份额与资金流阻断（Track B阻断）
