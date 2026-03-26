# Alert Rules Optimization — Validation Report

**Date:** 2026-03-26
**Validator:** Claude Code (DBA Infrastructure Team)
**Inputs:**
- Current rules: `/app/reports/alert-rules-three-tier-full-2026-03-25.yaml` (165 rules, 1878 lines)
- Optimization report: `/app/reports/alert-rules-optimization-2026-03-25.md` (29 proposals)
- Alertmanager config: `/app/alertrebuild/alertmanager-config.yml` (existing inhibition + routing)
- Previous rules: `/app/alertrebuild/alert-rules-complete.yml` (72 rules, 2026-02-14)

---

## Critical Meta-Finding

> **The optimization report is stale.** The three-tier YAML (2026-03-25) already implements ~85% of the report's proposals. The report's "current" descriptions match the older `alert-rules-complete.yml` (2026-02-14), not the YAML it claims to reference. Of 29 proposed changes, only 3 remain unimplemented.

This does not invalidate the report's analysis — it means the YAML was built from the same analysis. But anyone reading the report today will get a false impression of what "current" looks like. **The report should be updated to reflect the three-tier YAML as the new baseline, and focus on the remaining gaps.**

---

## Section 1: Current State Inventory

### Rule Counts by Category

| Category | Group Name | Metrics | Rules (Info+Warn+Crit) | Notes |
|----------|-----------|---------|------------------------|-------|
| BIZ | biz.rules | 6 | 18 | OrderVolume, Cancellation, Payment, Registration, TrafficDrop, LatencyP99 |
| RDS | rds.rules | 10 | 30 | CPU, SlowQueries, ActiveThreads, DiskFree, FreeableMemory, SwapUsage, ReplicaLag, VipUnreachable, Failover, ExporterDown |
| REDIS | redis.rules | 8 | 24 | CPU, Memory, Latency, Evictions, ConnectionRatio, NetworkBandwidth, InstanceDown, ExporterDown |
| ES | es.rules | 4 | 12 | ClusterHealth, NodeCpu, NodeDisk, JvmHeap |
| MONGO | mongo.rules | 3 | 9 | CPU, MemoryFree, ConnectionRatio |
| K8S | k8s.rules | 6 | 18 | PodCPU, PodRestart, PodDiskIO, OomKilled, NodeHeartbeat, NodeDiskPressure |
| VM | vm.rules | 5 | 15 | CPU, Memory, Disk, NetworkErrors, InstanceDown |
| APM | apm.rules | 5 | 15 | ServiceExceptions, LatencyP99, EndpointFailures, JvmFullGc, InfraHealth |
| PIPE | pipe.rules | 4 | 12 | GoldenFlow, Core, Important, Standard |
| PLAT | plat.rules | 3 | 9 | SmsDelivery, RiskControl, GatewayErrorRate |
| MSK | msk.rules | 1 | 3 | ConsumerLag |
| **Total** | **11 groups** | **55** | **165** | |

**Discrepancy:** Report claims "72 rules across 10 categories" and lists CERT as a category. The YAML has 165 rules across 11 categories (no CERT). The 72 count matches the older 2026-02-14 file.

### Expression Pattern Classification

| Pattern Type | Count | Examples |
|-------------|-------|---------|
| **Compound (pct OR abs)** | 30 | RDS DiskFree, FreeableMemory; REDIS Memory; VM Memory, Disk; ES NodeDisk; MONGO Memory |
| **Absolute threshold** | 48 | RDS CPU (>65%), ActiveThreads (>25), SlowQueries; REDIS CPU; VM CPU; ES CPU; MONGO CPU; MSK Lag |
| **Ratio / Percentage** | 33 | BIZ Cancellation (cancel/total), APM Exceptions (err/req), REDIS ConnectionRatio, PLAT SmsDelivery, GatewayError |
| **Rate-of-change** | 18 | RDS SlowQueries (rate()*60), REDIS Evictions, K8S PodDiskIO, VM NetworkErrors, APM JvmFullGc |
| **Boolean / condition** | 24 | RDS VipUnreachable (mysql_up==0), Failover, ExporterDown (up==0), K8S OomKilled, NodeHeartbeat, NodeDiskPressure, PLAT RiskControl |
| **Histogram quantile** | 6 | BIZ LatencyP99, APM LatencyP99 |
| **Custom metric** | 6 | BIZ TrafficDrop (traffic_rate vs daily avg), PIPE (datalink_pipeline_delay), APM InfraHealth |

### Absolute Thresholds That Should Be Percentage-Based

| Rule | Current Expr | Issue |
|------|-------------|-------|
| RDS_ActiveThreads (Info/Warn/Crit) | `threads_running > 25/50/100` | db.t4g.micro has ~87 max connections; db.r6g.4xlarge has ~5000. Flat thresholds don't scale. Should use `threads_running / max_connections`. |
| RDS_SlowQueries (Info/Warn/Crit) | `rate(slow_queries) > 10/50/200 per min` | A high-throughput instance doing 50K QPS might legitimately have 200 slow queries/min at 0.4%. A low-throughput instance at 200/min might be 100% slow. Should normalize by total queries. |
| REDIS_NetworkBandwidth (Info/Warn/Crit) | `> 20/32/50 Mbps` | ElastiCache node types range from 1.6Gbps (cache.t3.micro) to 25Gbps (cache.r6g.16xlarge). 50 Mbps is 3% of micro but 0.2% of 16xlarge. Should use percentage of baseline throughput. |
| K8S_PodDiskIO (Info/Warn/Crit) | `> 30/50/100 MB/s` | EBS gp3 baseline is 125 MB/s; io2 can do 4000 MB/s. 100 MB/s is near-limit for gp3 but trivial for io2. |
| MSK_ConsumerLag (Info/Warn/Crit) | `> 5K/10K/100K` | Lag meaning depends on topic throughput. 10K lag on a 1M msg/s topic = 10ms behind; on a 100 msg/s topic = 100s behind. Should use lag-in-seconds or normalize by production rate. |
| VM_NetworkErrors (Info/Warn/Crit) | `> 50/200/500 errors/s` | Should be expressed as error rate relative to total packets. 500 errors/s is noise on a 1M pps link but catastrophic on a 1K pps link. |

---

## Section 2: Cross-Validation Results

### Summary

| Category | Proposed | Already Done | Partially Done | Not Done |
|----------|----------|-------------|---------------|----------|
| Modified rules | 14 | 12 | 1 (BIZ-09) | 1 (REDIS-04) |
| New rules | 15 | 13 | 0 | 2 (K8S-09, BIZ TrafficSpike) |
| Inhibition | 4 rules | 0 | 0 | 4 (all broken) |
| Maintenance window | 1 | 0 | 0 | 1 |
| **Total** | **34** | **25** | **1** | **8** |

### Per-Proposal Detail

| # | Report ID | Proposal | Status | Discrepancy |
|---|-----------|----------|--------|-------------|
| 1 | RDS-13 | FreeableMemory Warning < 256MB | **DONE** | YAML is superior: `< 15% OR < 256MB` (dual condition) vs report's abs-only |
| 2 | RDS-14 | FreeableMemory Critical < 128MB | **DONE** | YAML: `< 10% OR < 128MB`. Also added Info tier (< 20% OR < 512MB) |
| 3 | RDS-15 | SwapUsage Warning > 256MB | **DONE** | YAML adds Info (>100MB) and Critical (>500MB) beyond report |
| 4 | RDS-10 | DiskFree → percentage | **DONE** | YAML: pct OR abs dual condition at all 3 tiers. Report said "current: < 15GB" — wrong for this YAML |
| 5 | RDS-10b | DiskFree Critical < 8% | **DONE** | YAML: `< 8% OR < 2GB` |
| 6 | RDS-16/17 | ReplicaLag Warn/Crit | **DONE** | YAML adds Info > 10s tier |
| 7 | RDS-18 | ExporterDown Warning | **DONE** | YAML has full 3-tier (1m/3m/10m) vs report's single Warning |
| 8 | RDS-01 | CpuUsage Info 50% → 65% | **DONE** | YAML at 65% |
| 9 | RDS-07/08/09 | ActiveThreads 12/24/48 → 25/50/100 | **DONE** | YAML at 25/50/100 |
| 10 | REDIS-04 | Memory Warning 80% → 75%, add PreCritical 88% | **NOT DONE** | YAML still at 80% Warning. No PreCritical tier. This is the highest-priority remaining item per the isales-market incident (2026-02-12) |
| 11 | REDIS-06 | Latency 5ms → 2ms | **DONE** | YAML Warning at 2ms. Also added Info at 1ms, Critical at 10ms |
| 12 | REDIS-11 | ExporterDown | **DONE** | Full 3-tier |
| 13 | BIZ-04 | Cancellation → ratio > 10% | **DONE** | YAML has 3-tier: 5%/10%/25%, all with `completed > 5` guard |
| 14 | BIZ-05 | Payment + order guard | **DONE** | All tiers have `completed > 5` (Info/Warn) or `> 3` (Critical) guard |
| 15 | BIZ-07 | Registration + time filter | **DONE** | `AND (hour() < 5 OR hour() >= 11)` on all tiers |
| 16 | BIZ-09 | Traffic split → Drop + Spike | **PARTIAL** | Drop alerts implemented (3 tiers). **TrafficSpikeInfo not implemented.** |
| 17 | BIZ-10b | LatencyP99 Critical > 8s | **DONE** | Full 3-tier: 1.5s/3s/8s |
| 18 | APM-01 | Exceptions → ratio > 2% | **DONE** | YAML: 1%/2%/5% with `sum by (service)`. Report lacked `by (service)` |
| 19 | APM-04 | Failures → ratio > 1% | **DONE** | YAML: 0.5%/1%/5%. But see PromQL issue in Section 3 |
| 20 | APM-03b | LatencyP99 Critical > 5s | **DONE** | Full 3-tier: 0.8s/1.5s/5s |
| 21 | MONGO-03b/04b | Memory → percentage | **DONE** | YAML uses `aws_docdb_*` metrics, not `mongo_mem_*` as report proposed. Dual condition. |
| 22 | PLAT-04b | GatewayErrorRate Warning > 5% | **DONE** | Full 3-tier: 2%/5%/15%. Report wanted Critical at 20%, YAML kept 15% |
| 23 | K8S-08 | NodeDiskPressure | **DONE** | Full 3-tier at 1m/3m/5m |
| 24 | K8S-09 | NodeMemoryPressure | **NOT DONE** | Completely absent from YAML. Coverage gap. |
| 25 | MSK-01/02 | ConsumerLag | **DONE** | Full 3-tier: 5K/10K/100K |
| 26 | ES-01 | ClusterHealth duration | **DONE** | Info/Warning at 3m |
| 27 | ES-02 | ClusterRed 0m → 1m | **DONE** | Critical at `for: 1m` |
| 28 | Inhibition | 4 inhibit_rules | **BROKEN** | See Section 4 — labels don't exist |
| 29 | Maintenance | 04:30–06:30 UTC batch window | **NOT DONE** | Alertmanager has different window (07:00–12:00 UTC for non-BIZ). Proposed batch-specific window not configured. |

### Items Still Outstanding

1. **REDIS-04 Memory Warning threshold** — lower from 80% to 75%, add PreCritical 88% tier
2. **K8S NodeMemoryPressure** — add 3-tier alert
3. **BIZ TrafficSpikeInfo** — add info-only alert for traffic > 3x daily avg
4. **Inhibition rules** — current implementation is non-functional (see Section 4)
5. **Batch maintenance window** — 04:30–06:30 UTC not configured in Alertmanager
6. **PLAT Gateway Critical threshold** — report proposed 20%, YAML has 15% (keep 15%)

---

## Section 3: PromQL Validation

### Issues in Report's Proposed Expressions

| # | Rule | Issue | Severity | Fix |
|---|------|-------|----------|-----|
| 1 | APM-01 | `sum(rate(service_exceptions_total[5m]))` missing `by (service)` — aggregates globally, masking per-service issues | **High** | YAML correctly uses `sum by (service)(...)`. Report expression would never fire unless overall exception rate exceeds threshold. |
| 2 | APM-04 | Same: `sum(rate(endpoint_failures_total[5m]))` missing `by (endpoint)` | **High** | Same fix needed. |
| 3 | MONGO-03b/04b | Uses `mongo_mem_available_bytes / mongo_mem_total_bytes` — metric names don't match YAML convention `aws_docdb_freeable_memory_average / aws_docdb_total_memory_average` | **High** | Use `aws_docdb_*` prefix consistent with CloudWatch exporter. |
| 4 | Inhibit rules | Uses deprecated `source_match` / `target_match` syntax | **Medium** | Use `source_matchers` / `target_matchers` per Alertmanager >= 0.22. Existing config already uses correct syntax. |
| 5 | BIZ-04/05 | Division-by-zero risk when `business_completed_orders_total` has zero increase | **Low** | Prometheus returns NaN, which fails `> 0.10` comparison, so functionally safe. But `AND completed > 5` guard already prevents this in practice. No fix needed. |
| 6 | RDS-10 | `aws_rds_allocated_storage_average` — may not be available as a Prometheus metric if using CloudWatch exporter. CloudWatch has `AllocatedStorage` but it's a static property, not a metric. | **Medium** | Verify metric availability. May need to use a recording rule or static label. |

### Issues in YAML Expressions

| # | Rule | Issue | Severity |
|---|------|-------|----------|
| 1 | RDS_FailoverInfo + RDS_FailoverCritical | **Identical condition**: both `aws_rds_failover_event == 1, for: 0m`. Info and Critical fire simultaneously — Info is completely redundant since Critical inhibition (if working) would suppress it. | **Medium** |
| 2 | APM_EndpointFailures (Info/Warn/Crit) | Uses raw `rate()` without `sum()` or `sum by (endpoint)()`. Evaluates per time series. If `endpoint_failures_total` has labels like `{method, path, status}`, the ratio is computed per label combination, potentially giving false positives on low-traffic sub-slices. | **Medium** |
| 3 | K8S_PodCpuUsage | `rate(...) / container_spec_cpu_quota * container_spec_cpu_period` — operator precedence is correct (left-to-right gives `rate * period / quota`), but the expression is confusing. Better written as `rate(...) * container_spec_cpu_period / container_spec_cpu_quota` or use `kube_pod_container_resource_limits` instead. | **Low** |
| 4 | PIPE_GoldenFlowCritical | `delay > 300 OR exceptions > 0` — the OR mixes two different failure modes into one alert. An exception count of 1 in 3 minutes fires as Critical, which may be too aggressive. Consider separating exception alerting from delay alerting. | **Low** |

---

## Section 4: Inhibition Feasibility Assessment

### Current State: Non-Functional

The Alertmanager config at `/app/alertrebuild/alertmanager-config.yml` has 3 inhibition rules. **Rule 1 does not work as intended:**

```yaml
# Existing Rule 1
- source_matchers:
    - severity = "critical"
  target_matchers:
    - severity =~ "warning|info"
  equal: ['alertname', 'service']
```

**Problem:** `equal: ['alertname']` requires the source and target alerts to have the **same** `alertname`. But `BIZ_OrderVolumeCritical` and `BIZ_OrderVolumeInfo` are different alertnames. This rule **never fires** for multi-tier suppression.

### Report's Proposed Inhibition: Also Non-Functional

| Report Proposal | Blocking Issue |
|-----------------|----------------|
| `equal: [alertname_prefix, instance]` | **`alertname_prefix` label does not exist** on any rule in the YAML. No rule has this label defined. |
| `equal: [instance]` for RDS Failover → RDS_VipUnreachable | RDS rules expose `dbinstance_identifier`, not `instance`. Label name mismatch. |
| `equal: [env]` for VIP → BIZ | **`env` label does not exist** on any rule. No rule has `env` in its labels block. |
| `equal: [pod, namespace]` for OomKilled → PodRestart | These labels come from the metric dimensions (kube-state-metrics), so they **should work** — this is the only viable inhibition proposal. |

### Recommended Fix

To make inhibition functional, add synthetic labels to all alert rules:

```yaml
# Add to EVERY rule's labels block:
labels:
  severity: warning
  category: rds
  alert_group: RDS_CpuUsage        # NEW: shared across Info/Warn/Crit tiers
  env: production                    # NEW: environment label
  instance: "{{ $labels.dbinstance_identifier }}"  # NEW: normalized instance label for RDS
```

Then rewrite inhibition rules:

```yaml
inhibit_rules:
  # Critical suppresses Warning+Info for same alert group and instance
  - source_matchers:
      - severity = "critical"
    target_matchers:
      - severity =~ "warning|info"
    equal: ['alert_group', 'instance']  # Uses new shared label

  # RDS Failover suppresses secondary RDS alerts
  - source_matchers:
      - alertname = "RDS_FailoverCritical"
    target_matchers:
      - category = "rds"
      - severity =~ "warning|info"
    equal: ['instance']  # Now normalized

  # OomKilled suppresses PodRestart (already works)
  - source_matchers:
      - alertname =~ "K8S_OomKilledCritical"
    target_matchers:
      - alert_group = "K8S_PodRestart"
    equal: ['pod', 'namespace']

  # VIP Unreachable suppresses BIZ order/payment alerts
  - source_matchers:
      - alertname = "RDS_VipUnreachableCritical"
    target_matchers:
      - category = "biz"
    equal: ['env']  # Now exists on all rules
```

**Effort estimate:** Medium. Requires adding 2-3 labels to all 165 rules (mechanical change) plus updating alertmanager config.

---

## Section 5: Additional Gaps Found

### Instant-Fire Rules (`for: 0m`)

| Rule | Condition | Risk | Recommendation |
|------|-----------|------|---------------|
| RDS_FailoverInfo | `failover_event == 1` | Low — event-driven, not threshold | Keep 0m but deduplicate with Critical (identical) |
| RDS_FailoverCritical | `failover_event == 1` | Low — but **identical to Info** | Remove Info tier or differentiate conditions |
| K8S_PodRestartInfo | `increase(restarts[10m]) > 1` | Medium — `increase()` over 10m window means this is effectively smoothed | Acceptable |
| K8S_PodRestartWarning | `increase(restarts[10m]) > 3` | Low | Acceptable |
| K8S_PodRestartCritical | `increase(restarts[10m]) > 5` | Low | Acceptable |
| K8S_OomKilledInfo | `last_terminated_reason=="OOMKilled"` | Low — event-based | Acceptable |
| K8S_OomKilledWarning | compound condition | Low | Acceptable |
| K8S_OomKilledCritical | compound condition | Low | Acceptable |

**Action needed:** Only RDS_Failover Info/Critical duplication needs fixing.

### Narrow Tier Gaps

| Rules | Info Threshold | Warning Threshold | Gap | Issue |
|-------|---------------|-------------------|-----|-------|
| REDIS Memory | 70% | 80% | 10pp | During rapid memory growth (isales-market: 61%→87% in 20min), both tiers fire within ~7 minutes of each other. Limited actionable window between Info and Warning. |
| RDS VipUnreachable | 30s | 45s | 15s | All 3 tiers fire within 30 seconds of each other during a real outage. Info adds no value — by the time you read it, Warning and Critical have fired. |
| K8S PodRestart | > 1 restart | > 3 restarts | 2 restarts | Info/Warning tiers are close enough to fire within one CrashLoop cycle. |
| K8S NodeHeartbeat | 2m | 3m | 1m | Same event, just escalating. Consider 2m/5m/10m for more breathing room. |

### Missing Annotations

**No rule has `runbook_url` or `dashboard_url`.** This is a significant operational gap:
- On-call engineers receiving a 3 AM Critical alert have no link to investigation steps
- No deep-link to the relevant Grafana dashboard for the firing metric
- Best practice: every Warning/Critical alert should have at minimum `runbook_url`

**~20 rules have no `description`** (mostly Info tiers and ExporterDown/InstanceDown rules). While less critical for Info, Warning and Critical alerts should always have actionable descriptions.

Missing description examples:
- `RDS_ExporterDownInfo`, `REDIS_InstanceDownInfo/Warning`, `REDIS_ExporterDown` (all tiers)
- `K8S_NodeHeartbeatInfo`, `K8S_NodeDiskPressureInfo/Warning`
- `VM_InstanceDown` (all tiers), `APM_InfraHealthInfo`

### Missing Labels for Routing

| Label | Present? | Impact |
|-------|----------|--------|
| `severity` | Yes, all rules | Routing works |
| `category` | Yes, all rules | Grouping works |
| `team` | **No** | Cannot route to specific teams (e.g., BIZ→product team, RDS→DBA team) |
| `service` | **No** (only from metric labels on APM rules) | Alertmanager `group_by: ['service']` only works for APM; other categories group on empty label |
| `env` | **No** | Cannot distinguish prod vs staging alerts; inhibition on `env` broken |
| `alert_group` | **No** | Cannot group multi-tier alerts for inhibition |

### Uncovered Categories

**VM (15 rules)** and **PIPE (12 rules)** are present in the YAML but completely unmentioned in the optimization report. No analysis of whether their thresholds are appropriate.

**CERT** is listed in the report's category enumeration but has zero rules in the YAML. Certificate expiry monitoring is industry-standard and should exist.

### Other Issues

- **APM EndpointFailures** uses raw `rate()` per time series without `sum by (endpoint)()`. On high-cardinality metrics, this creates per-label-combination ratio calculations that may not reflect true endpoint health.
- **BIZ TrafficSpikeInfo** proposed in report but not implemented — marketing campaign traffic surges still trigger TrafficDrop Warning false positives if they end abruptly.

---

## Section 6: Risk Flags on Proposed Changes

### RDS ActiveThreads: Flat Thresholds on Heterogeneous Fleet

| Instance Class | vCPUs | max_connections | Threads at 100 (Crit threshold) |
|---------------|-------|-----------------|-------------------------------|
| db.t4g.micro | 2 | ~87 | **115% of max** — impossible to reach; Critical never fires |
| db.t4g.medium | 2 | ~150 | 67% of max — reasonable |
| db.r6g.large | 2 | ~1000 | 10% — may be too lax |
| db.r6g.xlarge | 4 | ~2000 | 5% — very lax |
| db.r6g.4xlarge | 16 | ~5000 | 2% — effectively disabled |

**Verdict:** The flat threshold of 100 is **appropriate for Luckin's fleet** which is predominantly small instances (t4g/r6g.large). For the few large instances, ActiveThreads > 100 is still meaningful as an indicator of unusual concurrency. However, a long-term improvement would be `threads_running / max_connections > 0.30` for Warning and `> 0.60` for Critical.

### REDIS Latency 2ms Warning

- Redis P99 at 2ms is 2000x the typical sub-microsecond operation
- `for: 5m` provides adequate smoothing against network jitter
- Luckin operates in single-region (us-east-1), minimizing network variance
- **Verdict: Low risk.** 2ms with 5m duration is appropriate. The 10ms Critical threshold provides headroom.

### BIZ-04 Cancellation Rate: Min 5 Orders Sample Size

| Scenario | Orders | Cancels | Rate | Fires? |
|----------|--------|---------|------|--------|
| Normal slow hour | 6 | 1 | 16.7% | **Yes** (false positive) |
| Normal slow hour | 8 | 1 | 12.5% | **Yes** (false positive) |
| Genuine issue | 50 | 6 | 12% | Yes (true positive) |
| Micro volume | 3 | 1 | 33% | No (< 5 orders guard) |

**Verdict: Moderate risk.** The min-5-orders guard is too low. During slow but not zero-traffic periods (early morning in EST, late evening), a single cancellation out of 6-8 orders triggers Warning. Combined with `for: 10m`, this requires sustained low volume + cancellations, which reduces false positives somewhat. **Recommend raising to 15 orders minimum for Warning tier, keeping 5 for Info tier.**

### PLAT Gateway Critical: 15% vs Report's 20%

The YAML keeps Critical at 15% instead of the report's proposed 20%. For an API gateway serving all mobile app traffic, 15% error rate is already catastrophic — 1 in 7 requests failing. **Keep 15%.** The report's 20% suggestion was overly conservative.

### Maintenance Window: 04:30-06:30 UTC

| Time (UTC) | Time (EST) | Activity |
|------------|------------|----------|
| 04:30 | 00:30 | Window opens — batch jobs haven't started yet |
| 05:00 | 01:00 | Batch jobs typically start |
| 06:00 | 02:00 | Most batch jobs complete |
| 06:30 | 02:30 | Window closes |
| 07:00 | 03:00 | Existing non-BIZ mute starts (alertmanager) |

**Verdict: Acceptable but has a gap.** The proposed batch window (04:30-06:30) doesn't overlap with the existing off-hours mute (07:00-12:00). Between 06:30-07:00 UTC, a late-running batch job would trigger alerts that would have been silenced either before or after. Consider extending the batch window to 07:00 UTC to merge cleanly with the existing mute, or extending the existing mute to start at 04:30.

---

## Section 7: Recommended Additions (Coverage Gaps)

### High Priority — Standard Metrics Without Alerts

| Metric | Category | Suggested Expression | Severity | Rationale |
|--------|----------|---------------------|----------|-----------|
| K8S NodeMemoryPressure | K8S | `kube_node_status_condition{condition="MemoryPressure",status="true"} == 1` | Info 1m / Warn 3m / Crit 5m | Proposed in report but not implemented. Pod eviction risk. |
| BIZ TrafficSpikeInfo | BIZ | `traffic_rate > 3 * traffic_daily_avg_same_hour` | Info only, for 5m | Marketing events cause 3x+ surges; need awareness without pages. |
| RDS DatabaseConnections | RDS | `aws_rds_database_connections_average / aws_rds_max_connections > 0.70 / 0.85 / 0.95` | 3-tier | Active threads measures concurrency; total connections measures exhaustion. Both matter. |
| RDS DBLoad | RDS | `aws_rds_dbload_average > 2*vcpu_count / 4*vcpu_count` | Warn / Crit | Better indicator of contention than raw CPU. Requires recording rule for `vcpu_count`. |
| DocumentDB DiskUsage | MONGO | `aws_docdb_free_local_storage_average < 20% / 10% / 5%` | 3-tier | Zero disk alerts for MongoDB — complete blind spot. |
| CERT Expiry | CERT | `ssl_certificate_expiry_seconds < 30d / 14d / 7d` | 3-tier | Report lists CERT as a category but no rules exist. Certificate expiry is a high-impact, easily-preventable outage cause. |

### Medium Priority

| Metric | Category | Suggested Expression | Rationale |
|--------|----------|---------------------|-----------|
| Redis keyspace_misses ratio | REDIS | `rate(redis_keyspace_misses_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m])) > 0.20` | Cache effectiveness degradation. High miss ratio means cache is cold or undersized. |
| Redis rejected_connections | REDIS | `increase(redis_rejected_connections_total[5m]) > 0` | Hard signal that maxclients was hit. Even 1 rejection is actionable. |
| K8S PVC Usage | K8S | `kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes > 0.80 / 0.90 / 0.95` | PersistentVolume filling up causes application failures. |
| K8S HPA MaxReplicas | K8S | `kube_horizontalpodautoscaler_status_current_replicas == kube_horizontalpodautoscaler_spec_max_replicas` | Service at scaling ceiling — more load can't be absorbed. |
| K8S Deployment Unavailable | K8S | `kube_deployment_status_replicas_unavailable > 0` | Partial outage — some pods not serving traffic. |
| ES Unassigned Shards | ES | `elasticsearch_cluster_health_unassigned_shards > 0` | Data not fully replicated. Already detected by Yellow status but gives shard-level visibility. |
| ES Pending Tasks | ES | `elasticsearch_cluster_health_number_of_pending_tasks > 50 / 100 / 500` | Cluster overwhelmed with administrative work. |
| MSK UnderReplicated | MSK | `kafka_server_ReplicaManager_UnderReplicatedPartitions > 0` | Data durability at risk — replicas falling behind. |
| RDS ReadIOPS Spike | RDS | `aws_rds_read_iops_average > 3 * avg_over_time(aws_rds_read_iops_average[1h] offset 1d)` | Detect IO storms relative to baseline. |

### Low Priority

| Metric | Category | Rationale |
|--------|----------|-----------|
| RDS BinlogDiskUsage | RDS | Only relevant if using replication with binlog retention. Check if applicable. |
| DocumentDB OplogWindow | MONGO | Replication window shrinking means risk of replica falling off. |
| K8S CronJob Failure | K8S | `kube_job_status_failed > 0` for batch job monitoring. |
| MSK ActiveControllerCount | MSK | Controller failover detection. |

---

## Section 8: Implementation Priority Matrix

| Priority | Item | Effort | Impact | Dependencies |
|----------|------|--------|--------|-------------|
| **P0** | **Fix inhibition: add `alert_group`, `env` labels to all 165 rules; rewrite inhibit_rules** | Medium (mechanical) | **Critical** — current inhibition is completely non-functional; all multi-tier alerts fire simultaneously | None |
| **P0** | **Add K8S NodeMemoryPressure** (3 rules) | Low | High — proposed in report, missing in YAML | None |
| **P1** | **REDIS-04: lower Warning to 75%, add PreCritical 88%** | Low | High — directly addresses isales-market incident response gap | None |
| **P1** | **Add runbook_url to all Critical/Warning rules** | Medium (55+ rules) | High — reduces MTTR significantly | Requires runbook authoring |
| **P1** | **Fix RDS Failover Info/Critical duplication** | Low | Medium — noise reduction | None |
| **P1** | **Add BIZ TrafficSpikeInfo** | Low | Medium — prevents confusion on marketing events | None |
| **P1** | **Add DocumentDB disk alerts** (3 rules) | Low | Medium — complete blind spot | Verify metric name |
| **P1** | **Configure batch maintenance window** (04:30-07:00 UTC) | Low | Medium — batch job noise reduction | Alertmanager config |
| **P2** | Add RDS DatabaseConnections alert (3 rules) | Low | Medium | None |
| **P2** | Add RDS DBLoad alert (2 rules) | Low | Medium | Recording rule for vCPU count |
| **P2** | Add CERT expiry alerts (3 rules) | Medium | Medium | Deploy cert-exporter or probe |
| **P2** | Add Redis keyspace_misses + rejected_connections (4 rules) | Low | Medium | None |
| **P2** | Add K8S PVC, HPA, Deployment alerts (9 rules) | Medium | Medium | None |
| **P2** | Add ES unassigned_shards + pending_tasks (4-6 rules) | Low | Medium | None |
| **P2** | Add MSK under-replicated partitions (3 rules) | Low | Medium | Verify metric name |
| **P2** | Increase BIZ-04 min orders from 5 to 15 | Low | Low-Medium | None |
| **P2** | Fix APM EndpointFailures: add `sum by (endpoint)()` | Low | Low-Medium | None |
| **P3** | Add dashboard_url to all rules | Medium | Low-Medium | Requires dashboard UID mapping |
| **P3** | Parameterize ActiveThreads by instance class | High | Medium | Recording rules per instance class |
| **P3** | Normalize RDS SlowQueries to ratio | Medium | Low | Recording rule for total QPS |
| **P3** | Add VM and PIPE categories to optimization review | Low | Low | None |

### Implementation Order Recommendation

**Week 1 (P0):**
1. Add `alert_group` and `env: production` labels to all 165 rules
2. Add normalized `instance` label via template for RDS rules
3. Rewrite alertmanager inhibit_rules
4. Add K8S NodeMemoryPressure (3 rules)
5. Test inhibition with `amtool check-config`

**Week 2 (P1):**
6. REDIS-04 Warning → 75%, add PreCritical 88%
7. Fix RDS Failover duplication
8. Add BIZ TrafficSpikeInfo
9. Add DocumentDB disk alerts
10. Configure batch maintenance window
11. Begin runbook authoring for Critical alerts

**Week 3-4 (P2):**
12. Add remaining coverage gap alerts (RDS connections/DBLoad, Redis miss ratio, K8S PVC/HPA, ES shards)
13. Adjust BIZ-04 sample size
14. Fix APM EndpointFailures aggregation
15. Add CERT monitoring (requires exporter deployment)

---

## Appendix A: Complete Rule Inventory

<details>
<summary>Click to expand full 165-rule table</summary>

### BIZ Rules (18)

| # | Alert Name | Expr Type | For | Severity |
|---|-----------|-----------|-----|----------|
| 1 | BIZ_OrderVolumeInfo | rate-of-change | 10m | info |
| 2 | BIZ_OrderVolumeWarning | rate-of-change | 10m | warning |
| 3 | BIZ_OrderVolumeCritical | rate-of-change | 5m | critical |
| 4 | BIZ_CancellationSpikeInfo | ratio + guard | 10m | info |
| 5 | BIZ_CancellationSpikeWarning | ratio + guard | 10m | warning |
| 6 | BIZ_CancellationSpikeCritical | ratio + guard | 5m | critical |
| 7 | BIZ_PaymentAmountInfo | rate-of-change + guard | 5m | info |
| 8 | BIZ_PaymentAmountWarning | rate-of-change + guard | 5m | warning |
| 9 | BIZ_PaymentAmountCritical | rate-of-change + guard | 5m | critical |
| 10 | BIZ_RegistrationDropInfo | rate + time-filter | 10m | info |
| 11 | BIZ_RegistrationDropWarning | rate + time-filter | 5m | warning |
| 12 | BIZ_RegistrationDropCritical | rate + time-filter | 5m | critical |
| 13 | BIZ_TrafficDropInfo | custom (vs daily avg) | 10m | info |
| 14 | BIZ_TrafficDropWarning | custom (vs daily avg) | 10m | warning |
| 15 | BIZ_TrafficDropCritical | custom (vs daily avg) | 5m | critical |
| 16 | BIZ_LatencyP99Info | histogram quantile | 5m | info |
| 17 | BIZ_LatencyP99Warning | histogram quantile | 5m | warning |
| 18 | BIZ_LatencyP99Critical | histogram quantile | 3m | critical |

### RDS Rules (30)

| # | Alert Name | Expr Type | For | Severity |
|---|-----------|-----------|-----|----------|
| 19 | RDS_CpuUsageInfo | absolute (>65%) | 10m | info |
| 20 | RDS_CpuUsageWarning | absolute (>80%) | 5m | warning |
| 21 | RDS_CpuUsageCritical | absolute (>90%) | 3m | critical |
| 22 | RDS_SlowQueriesInfo | rate (>10/min) | 5m | info |
| 23 | RDS_SlowQueriesWarning | rate (>50/min) | 5m | warning |
| 24 | RDS_SlowQueriesCritical | rate (>200/min) | 3m | critical |
| 25 | RDS_ActiveThreadsInfo | absolute (>25) | 5m | info |
| 26 | RDS_ActiveThreadsWarning | absolute (>50) | 3m | warning |
| 27 | RDS_ActiveThreadsCritical | absolute (>100) | 2m | critical |
| 28 | RDS_DiskFreeInfo | compound (<20% OR <10GB) | 10m | info |
| 29 | RDS_DiskFreeWarning | compound (<15% OR <5GB) | 5m | warning |
| 30 | RDS_DiskFreeCritical | compound (<8% OR <2GB) | 2m | critical |
| 31 | RDS_FreeableMemoryInfo | compound (<20% OR <512MB) | 10m | info |
| 32 | RDS_FreeableMemoryWarning | compound (<15% OR <256MB) | 5m | warning |
| 33 | RDS_FreeableMemoryCritical | compound (<10% OR <128MB) | 3m | critical |
| 34 | RDS_SwapUsageInfo | absolute (>100MB) | 10m | info |
| 35 | RDS_SwapUsageWarning | absolute (>256MB) | 5m | warning |
| 36 | RDS_SwapUsageCritical | absolute (>500MB) | 3m | critical |
| 37 | RDS_ReplicaLagInfo | absolute (>10s) | 5m | info |
| 38 | RDS_ReplicaLagWarning | absolute (>30s) | 5m | warning |
| 39 | RDS_ReplicaLagCritical | absolute (>120s) | 3m | critical |
| 40 | RDS_VipUnreachableInfo | boolean (mysql_up==0) | 30s | info |
| 41 | RDS_VipUnreachableWarning | boolean (mysql_up==0) | 45s | warning |
| 42 | RDS_VipUnreachableCritical | boolean (mysql_up==0) | 1m | critical |
| 43 | RDS_FailoverInfo | boolean (event==1) | 0m | info |
| 44 | RDS_FailoverWarning | absolute (duration>120s) | 0m | warning |
| 45 | RDS_FailoverCritical | boolean (event==1) | 0m | critical |
| 46 | RDS_ExporterDownInfo | boolean (up==0) | 1m | info |
| 47 | RDS_ExporterDownWarning | boolean (up==0) | 3m | warning |
| 48 | RDS_ExporterDownCritical | boolean (up==0) | 10m | critical |

### REDIS Rules (24)

| # | Alert Name | Expr Type | For | Severity |
|---|-----------|-----------|-----|----------|
| 49 | REDIS_CpuUsageInfo | absolute (>50%) | 5m | info |
| 50 | REDIS_CpuUsageWarning | absolute (>70%) | 5m | warning |
| 51 | REDIS_CpuUsageCritical | absolute (>90%) | 3m | critical |
| 52 | REDIS_MemoryUsageInfo | compound (>70% OR rem<512MB) | 5m | info |
| 53 | REDIS_MemoryUsageWarning | compound (>80% OR rem<256MB) | 5m | warning |
| 54 | REDIS_MemoryUsageCritical | compound (>95% OR rem<64MB) | 1m | critical |
| 55 | REDIS_LatencyInfo | absolute (>1ms) | 5m | info |
| 56 | REDIS_LatencyWarning | absolute (>2ms) | 5m | warning |
| 57 | REDIS_LatencyCritical | absolute (>10ms) | 3m | critical |
| 58 | REDIS_EvictionsInfo | rate (>100/min) | 5m | info |
| 59 | REDIS_EvictionsWarning | rate (>1K/min) | 5m | warning |
| 60 | REDIS_EvictionsCritical | rate (>10K/min) | 3m | critical |
| 61 | REDIS_ConnectionRatioInfo | ratio (>50%) | 5m | info |
| 62 | REDIS_ConnectionRatioWarning | ratio (>70%) | 5m | warning |
| 63 | REDIS_ConnectionRatioCritical | ratio (>90%) | 3m | critical |
| 64 | REDIS_NetworkBandwidthInfo | absolute (>20Mbps) | 5m | info |
| 65 | REDIS_NetworkBandwidthWarning | absolute (>32Mbps) | 5m | warning |
| 66 | REDIS_NetworkBandwidthCritical | absolute (>50Mbps) | 3m | critical |
| 67 | REDIS_InstanceDownInfo | boolean (redis_up==0) | 30s | info |
| 68 | REDIS_InstanceDownWarning | boolean (redis_up==0) | 45s | warning |
| 69 | REDIS_InstanceDownCritical | boolean (redis_up==0) | 1m | critical |
| 70 | REDIS_ExporterDownInfo | boolean (up==0) | 1m | info |
| 71 | REDIS_ExporterDownWarning | boolean (up==0) | 3m | warning |
| 72 | REDIS_ExporterDownCritical | boolean (up==0) | 10m | critical |

### ES Rules (12)

| # | Alert Name | Expr Type | For | Severity |
|---|-----------|-----------|-----|----------|
| 73 | ES_ClusterHealthInfo | boolean (green==0) | 3m | info |
| 74 | ES_ClusterHealthWarning | boolean (yellow==1) | 3m | warning |
| 75 | ES_ClusterHealthCritical | boolean (red==1) | 1m | critical |
| 76 | ES_NodeCpuInfo | absolute (>60%) | 5m | info |
| 77 | ES_NodeCpuWarning | absolute (>75%) | 5m | warning |
| 78 | ES_NodeCpuCritical | absolute (>85%) | 3m | critical |
| 79 | ES_NodeDiskInfo | compound (<25% OR <20GB) | 5m | info |
| 80 | ES_NodeDiskWarning | compound (<15% OR <10GB) | 5m | warning |
| 81 | ES_NodeDiskCritical | compound (<10% OR <5GB) | 3m | critical |
| 82 | ES_JvmHeapInfo | ratio (>70%) | 5m | info |
| 83 | ES_JvmHeapWarning | ratio (>80%) | 5m | warning |
| 84 | ES_JvmHeapCritical | ratio (>90%) | 3m | critical |

### MONGO Rules (9)

| # | Alert Name | Expr Type | For | Severity |
|---|-----------|-----------|-----|----------|
| 85 | MONGO_CpuUsageInfo | absolute (>50%) | 10m | info |
| 86 | MONGO_CpuUsageWarning | absolute (>70%) | 5m | warning |
| 87 | MONGO_CpuUsageCritical | absolute (>90%) | 3m | critical |
| 88 | MONGO_MemoryFreeInfo | compound (<30% OR <1GB) | 10m | info |
| 89 | MONGO_MemoryFreeWarning | compound (<20% OR <512MB) | 5m | warning |
| 90 | MONGO_MemoryFreeCritical | compound (<10% OR <256MB) | 3m | critical |
| 91 | MONGO_ConnectionRatioInfo | ratio (>60%) | 10m | info |
| 92 | MONGO_ConnectionRatioWarning | ratio (>80%) | 5m | warning |
| 93 | MONGO_ConnectionRatioCritical | ratio (>95%) | 3m | critical |

### K8S Rules (18)

| # | Alert Name | Expr Type | For | Severity |
|---|-----------|-----------|-----|----------|
| 94 | K8S_PodCpuUsageInfo | ratio (>50% limit) | 10m | info |
| 95 | K8S_PodCpuUsageWarning | ratio (>70% limit) | 5m | warning |
| 96 | K8S_PodCpuUsageCritical | ratio (>90% limit) | 3m | critical |
| 97 | K8S_PodRestartInfo | rate (>1 in 10m) | 0m | info |
| 98 | K8S_PodRestartWarning | rate (>3 in 10m) | 0m | warning |
| 99 | K8S_PodRestartCritical | rate (>5 in 10m) | 0m | critical |
| 100 | K8S_PodDiskIoInfo | rate (>30 MB/s) | 5m | info |
| 101 | K8S_PodDiskIoWarning | rate (>50 MB/s) | 5m | warning |
| 102 | K8S_PodDiskIoCritical | rate (>100 MB/s) | 3m | critical |
| 103 | K8S_OomKilledInfo | boolean (reason==OOMKilled) | 0m | info |
| 104 | K8S_OomKilledWarning | compound (restarts>2 AND OOM) | 0m | warning |
| 105 | K8S_OomKilledCritical | compound (restarts>5 AND OOM) | 0m | critical |
| 106 | K8S_NodeHeartbeatInfo | boolean (Ready==false) | 2m | info |
| 107 | K8S_NodeHeartbeatWarning | boolean (Ready==false) | 3m | warning |
| 108 | K8S_NodeHeartbeatCritical | boolean (Ready==false) | 5m | critical |
| 109 | K8S_NodeDiskPressureInfo | boolean (DiskPressure==true) | 1m | info |
| 110 | K8S_NodeDiskPressureWarning | boolean (DiskPressure==true) | 3m | warning |
| 111 | K8S_NodeDiskPressureCritical | boolean (DiskPressure==true) | 5m | critical |

### VM Rules (15)

| # | Alert Name | Expr Type | For | Severity |
|---|-----------|-----------|-----|----------|
| 112 | VM_CpuUsageInfo | absolute (>65%) | 10m | info |
| 113 | VM_CpuUsageWarning | absolute (>80%) | 5m | warning |
| 114 | VM_CpuUsageCritical | absolute (>95%) | 3m | critical |
| 115 | VM_MemoryUsageInfo | compound (>75% OR avail<512MB) | 10m | info |
| 116 | VM_MemoryUsageWarning | compound (>85% OR avail<256MB) | 5m | warning |
| 117 | VM_MemoryUsageCritical | compound (>95% OR avail<100MB) | 3m | critical |
| 118 | VM_DiskUsageInfo | compound (>75% OR avail<10GB) | 10m | info |
| 119 | VM_DiskUsageWarning | compound (>85% OR avail<5GB) | 5m | warning |
| 120 | VM_DiskUsageCritical | compound (>95% OR avail<2GB) | 3m | critical |
| 121 | VM_NetworkErrorsInfo | rate (>50/s) | 5m | info |
| 122 | VM_NetworkErrorsWarning | rate (>200/s) | 5m | warning |
| 123 | VM_NetworkErrorsCritical | rate (>500/s) | 3m | critical |
| 124 | VM_InstanceDownInfo | boolean (up==0) | 30s | info |
| 125 | VM_InstanceDownWarning | boolean (up==0) | 45s | warning |
| 126 | VM_InstanceDownCritical | boolean (up==0) | 1m | critical |

### APM Rules (15)

| # | Alert Name | Expr Type | For | Severity |
|---|-----------|-----------|-----|----------|
| 127 | APM_ServiceExceptionsInfo | ratio + guard (>1%, >10rpm) | 5m | info |
| 128 | APM_ServiceExceptionsWarning | ratio + guard (>2%, >10rpm) | 5m | warning |
| 129 | APM_ServiceExceptionsCritical | ratio + guard (>5%, >10rpm) | 3m | critical |
| 130 | APM_LatencyP99Info | histogram quantile (>800ms) | 5m | info |
| 131 | APM_LatencyP99Warning | histogram quantile (>1.5s) | 5m | warning |
| 132 | APM_LatencyP99Critical | histogram quantile (>5s) | 3m | critical |
| 133 | APM_EndpointFailuresInfo | ratio + guard (>0.5%, >10rpm) | 5m | info |
| 134 | APM_EndpointFailuresWarning | ratio + guard (>1%, >10rpm) | 5m | warning |
| 135 | APM_EndpointFailuresCritical | ratio + guard (>5%, >10rpm) | 3m | critical |
| 136 | APM_JvmFullGcInfo | rate (>2 in 5m) | 5m | info |
| 137 | APM_JvmFullGcWarning | rate (>5 in 5m) | 5m | warning |
| 138 | APM_JvmFullGcCritical | rate (>10 in 5m) | 3m | critical |
| 139 | APM_InfraHealthInfo | boolean (component_up==0) | 2m | info |
| 140 | APM_InfraHealthWarning | boolean (component_up==0) | 5m | warning |
| 141 | APM_InfraHealthCritical | boolean (component_up==0) | 10m | critical |

### PIPE Rules (12)

| # | Alert Name | Expr Type | For | Severity |
|---|-----------|-----------|-----|----------|
| 142 | PIPE_GoldenFlowInfo | absolute (>120s) | 3m | info |
| 143 | PIPE_GoldenFlowWarning | absolute (>180s) | 3m | warning |
| 144 | PIPE_GoldenFlowCritical | compound (>300s OR exceptions>0) | 3m | critical |
| 145 | PIPE_CoreInfo | absolute (>300s) | 5m | info |
| 146 | PIPE_CoreWarning | compound (>600s OR exceptions>0) | 5m | warning |
| 147 | PIPE_CoreCritical | absolute (>1800s) | 5m | critical |
| 148 | PIPE_ImportantInfo | absolute (>900s) | 10m | info |
| 149 | PIPE_ImportantWarning | compound (>1200s OR exceptions>0) | 10m | warning |
| 150 | PIPE_ImportantCritical | absolute (>3600s) | 10m | critical |
| 151 | PIPE_StandardInfo | absolute (>1800s) | 15m | info |
| 152 | PIPE_StandardWarning | compound (>3600s OR exceptions>0) | 15m | warning |
| 153 | PIPE_StandardCritical | absolute (>14400s) | 15m | critical |

### PLAT Rules (9)

| # | Alert Name | Expr Type | For | Severity |
|---|-----------|-----------|-----|----------|
| 154 | PLAT_SmsDeliveryInfo | ratio (>2%) | 5m | info |
| 155 | PLAT_SmsDeliveryWarning | ratio (>5%) | 5m | warning |
| 156 | PLAT_SmsDeliveryCritical | ratio (>20%) | 3m | critical |
| 157 | PLAT_RiskControlInfo | boolean (prewarning==1) | 5m | info |
| 158 | PLAT_RiskControlWarning | boolean (threshold_exceeded==1) | 5m | warning |
| 159 | PLAT_RiskControlCritical | boolean (circuit_breaker==1) | 1m | critical |
| 160 | PLAT_GatewayErrorRateInfo | ratio (>2%) | 5m | info |
| 161 | PLAT_GatewayErrorRateWarning | ratio (>5%) | 5m | warning |
| 162 | PLAT_GatewayErrorRateCritical | ratio (>15%) | 3m | critical |

### MSK Rules (3)

| # | Alert Name | Expr Type | For | Severity |
|---|-----------|-----------|-----|----------|
| 163 | MSK_ConsumerLagInfo | absolute (>5K) | 5m | info |
| 164 | MSK_ConsumerLagWarning | absolute (>10K) | 5m | warning |
| 165 | MSK_ConsumerLagCritical | absolute (>100K) | 3m | critical |

</details>

---

*Report generated by Claude Code for the Luckin Coffee NA DBA/Infrastructure team.*
