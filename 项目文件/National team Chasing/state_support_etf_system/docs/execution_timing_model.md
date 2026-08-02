# 交易执行时间模型（Execution Timing Model）

- 版本：1.0.0
- 关联：docs/availability_model.md、contracts/execution/

## 一、字段

- decision_generated_at：模型/规则生成状态的时间
- execution_eligible_at：数据到达+计算+交易规则后最早可执行时间
- execution_price_timestamp：回测实际使用的成交价时间戳
- execution_price_type ∈ {NEXT_MINUTE_OPEN, NEXT_5MIN_VWAP, SAME_DAY_CLOSE, NEXT_DAY_OPEN, NEXT_DAY_CLOSE, CUSTOM_CONSERVATIVE}
- execution_delay_policy_id → contracts/execution/execution_delay_policies.yaml

## 二、硬规则

> **执行价格时间戳必须严格晚于数据可用时间和决策生成时间。**

| 数据可用时间 | 禁止 | 允许 |
|---|---|---|
| T+1 09:30 认定可用（fund_share V1） | T+1 09:30 开盘价 | T+1 09:31后第一合法价 / T+1 09:35 VWAP / T+1收盘 / T+2开盘 |
| T日 15:00 后（行情） | T日收盘价（当决策在收盘后） | T+1开盘或更晚 |
| 数据源延迟 | 原定执行时点 | 同步后移 |

## 三、交易时段（Asia/Shanghai）

- 集合竞价：09:15-09:25（开盘价09:25确定）
- 上午：09:30-11:30
- 午间休市：11:30-13:00（**不得生成11:31成交**）
- 下午：13:00-15:00（**不得生成15:01连续竞价成交**）
- 收盘集合竞价：14:57-15:00
- 节假日：不得生成任何价格

## 四、Execution Delay Policy（版本化）

| policy_id | 规则 | 适用 |
|---|---|---|
| EXEC_DELAY_V1_CONSERVATIVE | 数据可用时间之后第一个合法交易时段价格（NEXT_MINUTE_OPEN），最小粒度1分钟 | 默认 |
| EXEC_DELAY_V2_VWAP5 | 可用后5分钟VWAP | 备选 |
| EXEC_DELAY_V3_NEXT_DAY_OPEN | 下一个开放日开盘价 | 最保守 |
| EXEC_DELAY_V4_SAME_DAY_CLOSE | 当日收盘价（仅当数据在收盘前可用且决策在收盘前） | 特殊 |

## 五、测试断言

1. 09:30可用的数据不能按09:30开盘成交
2. 盘后数据不能按当日收盘价成交
3. 执行价格时间戳必须晚于 decision_generated_at
4. 数据源延迟时执行时间同步后移
5. 午间休市不能生成11:31成交
6. 15:00后不能生成15:01成交
7. 节假日不能生成不存在的交易价格
