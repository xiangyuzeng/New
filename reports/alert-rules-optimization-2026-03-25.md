# Alert Rules Optimization Report
**Date:** 2026-03-25
**Scope:** 72 alert rules across 10 categories
**Source:** https://luckin-alert-dashboard-new.vercel.app/

---

## Executive Summary

| Issue Type | Count | Top Priority |
|---|---|---|
| Thresholds too aggressive (noise) | 6 rules | BIZ-04, RDS-01, RDS-07, K8S-01, REDIS-01, APM-04 |
| Thresholds too lax (miss incidents) | 5 rules | RDS-10, REDIS-04, MONGO-03/04, APM-03, ES-01 |
| Missing critical alerts | 8 gaps | RDS FreeableMemory/Swap, Exporter Down, MSK Lag |
| Must change to percentage-based | 5 rules | BIZ-04, BIZ-05, RDS-10, APM-01, APM-04 |
| Suppression/inhibition gaps | 6 gaps | Severity cascade, failover cascade, maintenance window |
| Logical errors / anti-patterns | 4 issues | BIZ-01~03 simultaneous fire, PLAT-04 no Warning level |

**Estimated noise reduction after all changes: ~50-60% fewer pages per incident.**

---

## Priority 1 — 最高优先级（阻止已知故障重发）

### 新增 RDS FreeableMemory 和 SwapUsage 告警
**背景：** isalescdp OOM failover（2026-03-12）事前 FreeableMemory 已降至 82–102 MB，SwapUsage 达 530 MB，但当前告警规则中**完全没有这两个指标**。

```yaml
# 新增 RDS-13
alert: RDS_FreeableMemoryWarning
expr: aws_rds_freeable_memory_average < 268435456  # 256 MB
for: 5m
severity: warning

# 新增 RDS-14
alert: RDS_FreeableMemoryCritical
expr: aws_rds_freeable_memory_average < 134217728  # 128 MB
for: 3m
severity: critical

# 新增 RDS-15
alert: RDS_SwapUsageWarning
expr: aws_rds_swap_usage_average > 268435456  # 256 MB
for: 5m
severity: warning
```

---

## Priority 2 — 减少告警风暴（实现 Severity Inhibition）

**当前问题：** 每个多级告警组（BIZ-01/02/03, RDS-01/02/03, REDIS-01/02/03 等）在同一事件中会同时触发所有级别，产生多条重复通知。

**修复：** 在 Alertmanager 配置中全局添加 inhibit_rules：

```yaml
inhibit_rules:
  # Critical 抑制同目标的 Warning 和 Info
  - source_match:
      severity: critical
    target_match_re:
      severity: "warning|info"
    equal: [alertname_prefix, instance]  # 按 alert 名称前缀 + 实例匹配

  # RDS Failover 抑制同实例的次生告警
  - source_match:
      alertname: RDS_FailoverCritical
    target_match_re:
      alertname: "RDS_VipUnreachable.*|RDS_CpuUsage.*|RDS_ActiveThreads.*"
    equal: [instance]

  # 业务指标 OrderVolumeCritical 触发时，抑制同原因产生的支付告警
  - source_match:
      alertname: RDS_VipUnreachableCritical
    target_match_re:
      alertname: "BIZ_OrderVolume.*|BIZ_PaymentAmount.*"
    equal: [env]

  # OOMKilled 抑制同 Pod 的 PodRestartWarning
  - source_match:
      alertname: K8S_OomKilledCritical
    target_match:
      alertname: K8S_PodRestartWarning
    equal: [pod, namespace]
```

---

## Priority 3 — 阈值修正

### BIZ-04: CancellationSpikeWarning — 从绝对值改为比率
**当前：** `> 1 cancel/5min`（每天正常运营就会触发）
**修改为：**
```promql
# 取消率 > 10%，且窗口内至少有 5 个订单
(sum(increase(business_cancelled_orders_total[5m])) /
 sum(increase(business_completed_orders_total[5m]))) > 0.10
AND sum(increase(business_completed_orders_total[5m])) > 5
```
`for: 10m`

---

### BIZ-05: PaymentAmountWarning — 增加订单量前置条件
**当前问题：** 订单量低时（深夜）必然触发，与 BIZ-01/02 重复报警。
**修改为：** 仅当订单量正常但支付金额异常时触发：
```promql
sum(increase(business_payment_amount_total[10m])) < 500
AND sum(increase(business_completed_orders_total[10m])) > 5
```

---

### BIZ-07: RegistrationZeroWarning — 增加时段抑制
**当前问题：** 每天凌晨 00:00–06:00 EST 注册量本就为零，每晚误报。
**修改为：** 添加 UTC 时段排除（00:00–06:00 EST = 05:00–11:00 UTC）：
```promql
sum(increase(business_registration_total[10m])) == 0
AND (hour() < 5 OR hour() >= 11)  # 排除 05:00-11:00 UTC
```
或在 Alertmanager 中配置 `time_intervals` 静默窗口。

---

### BIZ-10: LatencyP99Warning — 增加 Critical 级别
**当前：** 只有 Warning（> 3000ms），无 Critical。
**新增：**
```yaml
# 新增 BIZ-10b
alert: BIZ_LatencyP99Critical
expr: histogram_quantile(0.99, rate(order_service_duration_bucket[5m])) > 8
for: 3m
severity: critical
```

---

### RDS-01: CpuUsageInfo — 提高阈值或删除
**当前：** `> 50%, 10m`，在 62 个实例上每晚批处理（05:00 UTC）都会触发。
**修改：** 阈值提高至 65%，或完全删除 Info 级别（保留 Warning 70% + Critical 90%）。
**同时：** 在 04:30–06:30 UTC 添加批处理静默窗口覆盖 Info/Warning 级别的 RDS CPU。

---

### RDS-07/08/09: ActiveThreads — 提高阈值
**当前：** Info > 12，Warning > 24，Critical > 48（阈值过低，正常峰值就会触发）
**修改为：**

| 级别 | 旧值 | 新值 |
|---|---|---|
| Info | > 12 | > 25 |
| Warning | > 24 | > 50 |
| Critical | > 48 | > 100 |

---

### RDS-10: DiskFreeWarning — 从绝对值改为百分比 + 新增 Critical
**当前：** `< 15GB`（在小实例上是 37%，在大实例上是 1.5%，标准完全不一致）
**修改为：**
```yaml
# RDS-10（修改）Warning
expr: (aws_rds_free_storage_space_average / aws_rds_allocated_storage_average) < 0.15
for: 5m
severity: warning

# 新增 RDS-10b Critical
alert: RDS_DiskFreeCritical
expr: (aws_rds_free_storage_space_average / aws_rds_allocated_storage_average) < 0.08
for: 2m
severity: critical
```

---

### REDIS-04: MemoryUsageWarning — 降低阈值 + 增加中间级别
**背景：** isales-market 事件（2026-02-12）显示内存从 61% 飙升至 87% 仅用 20 分钟，80% 预警留给响应的时间不足。
**修改为：**

| 级别 | 旧值 | 新值 |
|---|---|---|
| Warning | > 80% | > 75% |
| PreCritical（新增） | — | > 88%, for 3m |
| Critical | > 95% | > 95%（保持） |

---

### REDIS-06: LatencyP99Warning — 降低阈值
**当前：** `p99 > 5ms`（Redis 正常应在微秒级响应，5ms 已是严重延迟）
**修改为：** `p99 > 2ms, for: 5m`

---

### PLAT-04: GatewayErrorRateCritical — 增加 Warning 级别
**当前：** 直接从 0 跳到 Critical（> 15%），无渐进响应。
**修改为：**
```yaml
# 新增 PLAT-04b Warning
alert: PLAT_GatewayErrorRateWarning
expr: gateway_error_rate > 0.05
for: 5m
severity: warning

# PLAT-04 Critical 阈值调整
expr: gateway_error_rate > 0.20  # 从 15% 提高到 20%，配合新增的 Warning
for: 3m
```

---

### APM-01/04: 从绝对值改为比率
**APM-01 修改：**
```promql
# 旧：> 5 exceptions/min
# 新：异常率 > 2% 且请求量 > 20
(sum(rate(service_exceptions_total[5m])) / sum(rate(service_requests_total[5m]))) > 0.02
AND sum(rate(service_requests_total[5m])) * 60 > 20
```

**APM-04 修改：**
```promql
# 旧：> 2 failures/min（极易误报）
# 新：失败率 > 1% 且请求量 > 20
(sum(rate(endpoint_failures_total[5m])) / sum(rate(endpoint_requests_total[5m]))) > 0.01
AND sum(rate(endpoint_requests_total[5m])) * 60 > 20
```

---

### MONGO-03/04: 从绝对值改为百分比
**当前：** `< 500MB`/`< 200MB`（未考虑实例规格差异）
**新增百分比版本：**
```yaml
# MONGO-03b
alert: MONGO_MemoryFreePercentWarning
expr: (mongo_mem_available_bytes / mongo_mem_total_bytes) < 0.20
for: 5m
severity: warning

# MONGO-04b
alert: MONGO_MemoryFreePercentCritical
expr: (mongo_mem_available_bytes / mongo_mem_total_bytes) < 0.10
for: 3m
severity: critical
```

---

## Priority 4 — 补充缺失告警

### 新增 REDIS-11: Redis Exporter Down
```yaml
alert: REDIS_ExporterDown
expr: up{job="redis-exporter"} == 0
for: 3m
severity: warning
annotations:
  summary: "Redis exporter {{ $labels.instance }} 已停止上报，监控盲区"
```

### 新增 RDS-18: RDS Exporter Down
```yaml
alert: RDS_ExporterDown
expr: up{job="rds-exporter"} == 0
for: 3m
severity: warning
```

### 新增 RDS-16/17: Replica Lag
```yaml
alert: RDS_ReplicaLagWarning
expr: aws_rds_replica_lag_average > 30
for: 5m
severity: warning

alert: RDS_ReplicaLagCritical
expr: aws_rds_replica_lag_average > 120
for: 3m
severity: critical
```

### 新增 MSK-01/02: Kafka Consumer Lag
```yaml
alert: MSK_ConsumerLagWarning
expr: kafka_consumer_group_lag > 10000
for: 5m
severity: warning

alert: MSK_ConsumerLagCritical
expr: kafka_consumer_group_lag > 100000
for: 3m
severity: critical
```

### 新增 K8S-08/09: Node Pressure Conditions
```yaml
alert: K8S_NodeDiskPressureCritical
expr: kube_node_status_condition{condition="DiskPressure",status="true"} == 1
for: 3m
severity: critical

alert: K8S_NodeMemoryPressureWarning
expr: kube_node_status_condition{condition="MemoryPressure",status="true"} == 1
for: 5m
severity: warning
```

### 新增 APM-03b: Latency P99 Critical
```yaml
alert: APM_LatencyP99Critical
expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 5
for: 3m
severity: critical
```

---

## Priority 5 — 逻辑修正

### BIZ-09: TrafficAnomalyWarning 拆分
**当前问题：** 流量激增 3 倍（营销活动成功）也会告警，产生混淆。
**拆分为两条：**
```yaml
# 流量骤降（真正需要告警）
alert: BIZ_TrafficDropAnomaly
expr: traffic_rate < 0.20 * traffic_daily_avg_same_hour
for: 10m
severity: warning

# 流量激增（仅 Info，不呼叫）
alert: BIZ_TrafficSpikeInfo
expr: traffic_rate > 3 * traffic_daily_avg_same_hour
for: 5m
severity: info
```

### ES-02: ClusterRedCritical — 调整 duration
**当前：** `0m`（瞬时触发）。luckycommon 事件显示 RED 状态仅持续约 1 分钟即自愈，0m 会在深夜为短暂抖动呼叫人员。
**修改为：** `for: 1m`（过滤 <1 分钟的瞬时 RED）

---

## 维护窗口静默配置

在 Alertmanager 中新增以下定期静默：

```yaml
time_intervals:
  - name: nightly_batch_window
    time_intervals:
      - times:
          - start_time: "04:30"
            end_time: "06:30"
        weekdays: ["monday:sunday"]
        # UTC 时间，对应 EST 00:30-02:30
```

**适用规则（批处理期间降噪）：**
- RDS-01: CpuUsageInfo
- RDS-04: SlowQueriesInfo
- K8S-01: PodCpuUsageInfo

---

## 变更汇总

| ID | 变更类型 | 具体内容 |
|---|---|---|
| RDS-13/14/15 | **新增** | FreeableMemory Warning/Critical + SwapUsage Warning |
| RDS-10 | **修改** | 绝对值 → 百分比；新增 Critical 级别 |
| RDS-16/17 | **新增** | Replica Lag Warning/Critical |
| RDS-18 | **新增** | RDS Exporter Down |
| RDS-01 | **修改** | Info 阈值 50%→65% 或删除 Info 级别 |
| RDS-07/08/09 | **修改** | ActiveThreads 阈值 12/24/48 → 25/50/100 |
| REDIS-04 | **修改** | Warning 80%→75%；新增 PreCritical 88% |
| REDIS-06 | **修改** | Latency 阈值 5ms→2ms |
| REDIS-11 | **新增** | Redis Exporter Down |
| BIZ-04 | **修改** | 绝对值 → 取消率比率 > 10% |
| BIZ-05 | **修改** | 增加订单量前置条件 |
| BIZ-07 | **修改** | 增加凌晨时段静默 |
| BIZ-09 | **修改** | 拆分为 TrafficDrop（Warning）+ TrafficSpike（Info） |
| BIZ-10b | **新增** | LatencyP99Critical > 8s |
| APM-01/04 | **修改** | 绝对值 → 错误率百分比 |
| APM-03b | **新增** | LatencyP99Critical > 5s |
| MONGO-03b/04b | **新增** | 内存百分比版本 Warning/Critical |
| PLAT-04b | **新增** | GatewayErrorRateWarning > 5% |
| K8S-08/09 | **新增** | Node DiskPressure/MemoryPressure |
| MSK-01/02 | **新增** | Kafka Consumer Lag Warning/Critical |
| ES-01 | **修改** | duration 5m→3m |
| ES-02 | **修改** | duration 0m→1m |
| Inhibition | **新增** | Severity 级联抑制（全局）+ Failover 级联抑制 + OOMKilled 抑制 PodRestart |
| Maintenance | **新增** | 04:30–06:30 UTC 批处理静默窗口 |

**新增规则总计：** 15 条
**修改规则总计：** 14 条
**预计降噪效果：** 故障期间告警数量减少约 50–60%
