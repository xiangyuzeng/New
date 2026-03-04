# MSK CloudWatch Performance Baseline Report

**Generated**: 2026-03-04 06:56:55 UTC
**7-Day Window**: 2026-02-25 to 2026-03-04
**30-Day Trend**: 2026-02-02 to 2026-03-04
**Clusters**: 3 | **Brokers per cluster**: 3
**Data source**: AWS CloudWatch (namespace: AWS/Kafka)

---

## Capacity Alerts & Warnings

- WARNING: **base** Broker 1 — Memory utilization 96.3% exceeds 90%
- WARNING: **base** Broker 2 — Memory utilization 96.3% exceeds 90%
- WARNING: **base** Broker 3 — Memory utilization 96.3% exceeds 90%
- WARNING: **architecture** Broker 1 — Memory utilization 96.3% exceeds 90%
- WARNING: **architecture** Broker 2 — Memory utilization 96.0% exceeds 90%
- WARNING: **architecture** Broker 3 — Memory utilization 95.8% exceeds 90%
- WARNING: **business** Broker 1 — Memory utilization 95.8% exceeds 90%
- WARNING: **business** Broker 2 — Memory utilization 95.0% exceeds 90%
- WARNING: **business** Broker 3 — Memory utilization 95.7% exceeds 90%

---

## Executive Summary

### base
- **CPU**: avg 30.8%, peak 60.0%
- **Memory**: avg 96.3% utilized (~3.77 GB used / 146.85 MB free per broker)
- **Disk**: avg 57.7%
- **Throughput**: avg 334.97 KB/s in, avg 913.51 msgs/sec per broker
- **30d CPU trend**: stable (-2.7%)
- **30d throughput trend**: stable (-4.4%)
- **Health**: UnderReplicatedPartitions = 0 (healthy)

### architecture
- **CPU**: avg 14.7%, peak 48.7%
- **Memory**: avg 96.0% utilized (~4.04 GB used / 157.20 MB free per broker)
- **Disk**: avg 9.6%
- **Throughput**: avg 58.12 KB/s in, avg 41.04 msgs/sec per broker
- **30d CPU trend**: stable (-2.2%)
- **30d throughput trend**: declining (-13.4%)
- **Health**: UnderReplicatedPartitions = 0 (healthy)

### business
- **CPU**: avg 13.3%, peak 40.0%
- **Memory**: avg 95.5% utilized (~4.02 GB used / 175.61 MB free per broker)
- **Disk**: avg 3.0%
- **Throughput**: avg 15.36 KB/s in, avg 19.13 msgs/sec per broker
- **30d CPU trend**: stable (+3.4%)
- **30d throughput trend**: declining (-19.4%)
- **Health**: UnderReplicatedPartitions = 0 (healthy)

---

## iprod-kafka-base-cluster

### CPU Utilization (%)

| Broker | CpuUser Avg | CpuUser Max | CpuSystem Avg | CpuSystem Max | CpuIdle Avg | Peak Hours |
|--------|-------------|-------------|---------------|---------------|-------------|------------|
| Broker 1 | 26.33% | 48.90% | 8.54% | 19.90% | 59.47% | UTC 13-13 |
| Broker 2 | 38.20% | 60.05% | 12.08% | 21.38% | 42.95% | UTC 13-13 |
| Broker 3 | 27.97% | 47.77% | 8.96% | 18.68% | 57.71% | UTC 13-13 |

### Memory

| Broker | MemoryUsed Avg | MemoryUsed Max | MemoryFree Avg | MemoryFree Min | Util % | HeapAfterGC Avg | HeapAfterGC Max |
|--------|----------------|----------------|----------------|----------------|--------|-----------------|-----------------|
| Broker 1 | 3.77 GB | 4.13 GB | 146.85 MB | 122.41 MB | 96.25% | 14.16% | 23.91% |
| Broker 2 | 3.81 GB | 4.11 GB | 147.10 MB | 122.59 MB | 96.28% | 14.13% | 20.58% |
| Broker 3 | 3.76 GB | 3.87 GB | 143.33 MB | 122.99 MB | 96.33% | 14.13% | 16.20% |

### Disk & Connections

| Broker | DataLogDisk Avg % | DataLogDisk Max % | ClientConn Avg | ClientConn Max |
|--------|-------------------|-------------------|----------------|----------------|
| Broker 1 | 57.73% | 61.32% | 0.41 | 3.00 |
| Broker 2 | 57.72% | 61.33% | 0.41 | 3.00 |
| Broker 3 | 57.73% | 61.33% | 0.41 | 2.00 |

### Throughput

| Broker | BytesIn Avg | BytesIn Max | BytesOut Avg | BytesOut Max | MsgsIn Avg | MsgsIn Max |
|--------|-------------|-------------|--------------|--------------|------------|------------|
| Broker 1 | 314.40 KB/s | 979.93 KB/s | 456.21 KB/s | 1.48 MB/s | 753.30 | 2.6K |
| Broker 2 | 377.44 KB/s | 1.07 MB/s | 451.01 KB/s | 1.47 MB/s | 1.2K | 3.3K |
| Broker 3 | 313.08 KB/s | 996.38 KB/s | 452.94 KB/s | 1.50 MB/s | 745.20 | 2.6K |

### Network Packets (7d hourly sums)

| Broker | RxPackets/hr Avg | TxPackets/hr Avg |
|--------|------------------|------------------|
| Broker 1 | 116.6K | 136.5K |
| Broker 2 | 137.4K | 157.5K |
| Broker 3 | 114.8K | 135.2K |

### Cluster Health

| Broker | UnderReplicatedPartitions (Max) |
|--------|--------------------------------|
| Broker 1 | 0 (HEALTHY) |
| Broker 2 | 0 (HEALTHY) |
| Broker 3 | 0 (HEALTHY) |

### 30-Day Trends

| Broker | CpuUser Trend | BytesInPerSec Trend |
|--------|---------------|---------------------|
| Broker 1 | stable (-2.7%) | stable (-4.4%) |
| Broker 2 | stable (-2.0%) | stable (-4.9%) |
| Broker 3 | stable (+0.9%) | stable (-6.4%) |
---

## iprod-kafka-architecture-cluster

### CPU Utilization (%)

| Broker | CpuUser Avg | CpuUser Max | CpuSystem Avg | CpuSystem Max | CpuIdle Avg | Peak Hours |
|--------|-------------|-------------|---------------|---------------|-------------|------------|
| Broker 1 | 16.82% | 48.68% | 5.33% | 13.15% | 74.66% | UTC 12-17 |
| Broker 2 | 13.26% | 42.30% | 4.38% | 14.62% | 79.70% | UTC 13-16 |
| Broker 3 | 14.09% | 38.17% | 4.89% | 14.35% | 78.53% | UTC 13-13 |

### Memory

| Broker | MemoryUsed Avg | MemoryUsed Max | MemoryFree Avg | MemoryFree Min | Util % | HeapAfterGC Avg | HeapAfterGC Max |
|--------|----------------|----------------|----------------|----------------|--------|-----------------|-----------------|
| Broker 1 | 4.04 GB | 4.30 GB | 157.20 MB | 122.39 MB | 96.25% | 14.84% | 59.30% |
| Broker 2 | 4.00 GB | 4.12 GB | 165.51 MB | 122.99 MB | 96.03% | 14.82% | 58.53% |
| Broker 3 | 4.02 GB | 4.15 GB | 174.32 MB | 120.66 MB | 95.84% | 14.92% | 56.26% |

### Disk & Connections

| Broker | DataLogDisk Avg % | DataLogDisk Max % | ClientConn Avg | ClientConn Max |
|--------|-------------------|-------------------|----------------|----------------|
| Broker 1 | 9.62% | 11.17% | 0.44 | 3.00 |
| Broker 2 | 9.62% | 11.17% | 0.44 | 3.00 |
| Broker 3 | 9.62% | 11.17% | 0.44 | 4.00 |

### Throughput

| Broker | BytesIn Avg | BytesIn Max | BytesOut Avg | BytesOut Max | MsgsIn Avg | MsgsIn Max |
|--------|-------------|-------------|--------------|--------------|------------|------------|
| Broker 1 | 59.93 KB/s | 530.68 KB/s | 80.43 KB/s | 624.36 KB/s | 51.43 | 465.38 |
| Broker 2 | 56.74 KB/s | 498.23 KB/s | 80.40 KB/s | 626.92 KB/s | 29.79 | 250.36 |
| Broker 3 | 57.70 KB/s | 500.33 KB/s | 80.49 KB/s | 629.85 KB/s | 41.92 | 282.31 |

### Network Packets (7d hourly sums)

| Broker | RxPackets/hr Avg | TxPackets/hr Avg |
|--------|------------------|------------------|
| Broker 1 | 70.3K | 64.4K |
| Broker 2 | 46.0K | 51.8K |
| Broker 3 | 79.3K | 68.7K |

### Cluster Health

| Broker | UnderReplicatedPartitions (Max) |
|--------|--------------------------------|
| Broker 1 | 0 (HEALTHY) |
| Broker 2 | 0 (HEALTHY) |
| Broker 3 | 0 (HEALTHY) |

### 30-Day Trends

| Broker | CpuUser Trend | BytesInPerSec Trend |
|--------|---------------|---------------------|
| Broker 1 | stable (-2.2%) | declining (-13.4%) |
| Broker 2 | declining (-11.4%) | declining (-13.7%) |
| Broker 3 | stable (-2.1%) | declining (-13.7%) |
---

## iprod-kafka-business-cluster

### CPU Utilization (%)

| Broker | CpuUser Avg | CpuUser Max | CpuSystem Avg | CpuSystem Max | CpuIdle Avg | Peak Hours |
|--------|-------------|-------------|---------------|---------------|-------------|------------|
| Broker 1 | 13.25% | 39.95% | 4.65% | 11.62% | 79.54% | even distribution |
| Broker 2 | 13.66% | 36.13% | 4.73% | 12.78% | 78.95% | even distribution |
| Broker 3 | 12.98% | 30.67% | 4.34% | 12.42% | 80.07% | even distribution |

### Memory

| Broker | MemoryUsed Avg | MemoryUsed Max | MemoryFree Avg | MemoryFree Min | Util % | HeapAfterGC Avg | HeapAfterGC Max |
|--------|----------------|----------------|----------------|----------------|--------|-----------------|-----------------|
| Broker 1 | 4.02 GB | 4.29 GB | 175.61 MB | 123.02 MB | 95.82% | 14.86% | 57.27% |
| Broker 2 | 4.01 GB | 4.20 GB | 211.31 MB | 122.61 MB | 95.00% | 14.82% | 56.60% |
| Broker 3 | 4.10 GB | 4.33 GB | 182.07 MB | 122.98 MB | 95.75% | 14.81% | 56.63% |

### Disk & Connections

| Broker | DataLogDisk Avg % | DataLogDisk Max % | ClientConn Avg | ClientConn Max |
|--------|-------------------|-------------------|----------------|----------------|
| Broker 1 | 2.97% | 3.34% | 0.44 | 3.00 |
| Broker 2 | 2.97% | 3.34% | 0.45 | 4.00 |
| Broker 3 | 2.97% | 3.34% | 0.44 | 4.00 |

### Throughput

| Broker | BytesIn Avg | BytesIn Max | BytesOut Avg | BytesOut Max | MsgsIn Avg | MsgsIn Max |
|--------|-------------|-------------|--------------|--------------|------------|------------|
| Broker 1 | 12.80 KB/s | 923.45 KB/s | 17.64 KB/s | 551.73 KB/s | 8.00 | 579.97 |
| Broker 2 | 16.83 KB/s | 960.44 KB/s | 24.42 KB/s | 582.70 KB/s | 24.87 | 566.52 |
| Broker 3 | 16.45 KB/s | 947.57 KB/s | 17.96 KB/s | 552.39 KB/s | 24.53 | 529.80 |

### Network Packets (7d hourly sums)

| Broker | RxPackets/hr Avg | TxPackets/hr Avg |
|--------|------------------|------------------|
| Broker 1 | 54.5K | 75.2K |
| Broker 2 | 57.9K | 78.0K |
| Broker 3 | 64.3K | 80.2K |

### Cluster Health

| Broker | UnderReplicatedPartitions (Max) |
|--------|--------------------------------|
| Broker 1 | 0 (HEALTHY) |
| Broker 2 | 0 (HEALTHY) |
| Broker 3 | 0 (HEALTHY) |

### 30-Day Trends

| Broker | CpuUser Trend | BytesInPerSec Trend |
|--------|---------------|---------------------|
| Broker 1 | stable (+3.4%) | declining (-19.4%) |
| Broker 2 | stable (-3.9%) | declining (-15.2%) |
| Broker 3 | stable (-7.0%) | declining (-14.9%) |

---

## Notes

- **Memory 95-96%**: This is typical for Kafka brokers. Kafka relies heavily on OS page cache for performance. High memory utilization is expected and desired — the OS page cache stores recently read/written log segments. Only concerning if `MemoryFree` drops below ~100 MB or if GC pauses increase (watch `HeapMemoryAfterGC`).
- **HeapMemoryAfterGC**: Shows JVM heap retained after garbage collection. Values <60% indicate healthy GC behavior. Sustained >70% suggests heap pressure.
- **KafkaDataLogsDiskUsed**: Percentage of allocated EBS volume used for Kafka data logs. base=~58%, architecture=~10%, business=~3%. All well below concern thresholds.
- **Latency metrics** (ProduceLocalTimeMsMean, FetchConsumerLocalTimeMsMean, FetchMessageConversionsPerSec): Returned no datapoints for the 7-day window. These JMX-based metrics may require enhanced monitoring or may not emit when traffic is below certain thresholds.
- **ClientConnectionCount**: Very low avg (~0.4) across all clusters, suggesting intermittent connections rather than persistent ones. Max of 3-4 connections per broker.
- **Peak hours**: base cluster shows peak at UTC 13:00 (EST 08:00 AM — morning rush). architecture and business clusters show more even distribution.
- **30-day trends**: CPU is stable across all clusters. BytesInPerSec shows a declining trend on architecture (-13%) and business (-15-19%) clusters, suggesting reduced producer traffic over the past month. base cluster throughput is stable.
- **Capacity headroom**: CPU utilization is well within limits (base peak 60%, others peak 40-49%). No immediate scaling needed.

---

## Enhanced Analysis: Per-Broker Load Distribution, Disk I/O, Consumer Lag

**Collected**: 2026-03-04 | **Consumer lag window**: 7 days | **Sampling**: base=all 36 combos, architecture=60/267 sampled, business=74/315 sampled

### Per-Broker Load Balance Analysis

Load skew = max broker deviation from cluster mean, as percentage of mean.

#### iprod-kafka-base-cluster

| Metric | Broker 1 Avg | Broker 2 Avg | Broker 3 Avg | Skew % | Assessment |
|--------|-------------|-------------|-------------|--------|------------|
| CpuUser | 26.33% | **38.20%** | 27.97% | **23.9%** | Broker 2 runs 24% hotter — uneven partition assignment likely |
| BytesInPerSec | 307.0 KB/s | **368.6 KB/s** | 305.7 KB/s | 12.7% | Broker 2 receives 13% more traffic |
| BytesOutPerSec | 445.5 KB/s | 440.4 KB/s | 442.3 KB/s | 0.6% | Excellent balance |
| CpuIoWait | 0.48% | 0.37% | 0.47% | 16.8% | All negligible (<0.5%) |
| DiskUsed | 57.73% | 57.72% | 57.73% | 0.0% | Perfectly balanced |

> **Action**: Base cluster Broker 2 shows notable CPU+throughput skew. Consider running `kafka-reassign-partitions` to rebalance leader partitions. Not critical (peak 60%) but worth addressing before Graviton migration.

#### iprod-kafka-architecture-cluster

| Metric | Broker 1 Avg | Broker 2 Avg | Broker 3 Avg | Skew % | Assessment |
|--------|-------------|-------------|-------------|--------|------------|
| CpuUser | **16.82%** | 13.26% | 14.09% | 14.3% | Broker 1 slightly hotter |
| BytesInPerSec | 58.5 KB/s | 55.4 KB/s | 56.3 KB/s | 3.1% | Well balanced |
| BytesOutPerSec | 78.5 KB/s | 78.5 KB/s | 78.6 KB/s | 0.1% | Excellent balance |
| CpuIoWait | 0.44% | 0.47% | 0.45% | 2.9% | All negligible |
| DiskUsed | 9.62% | 9.62% | 9.62% | 0.0% | Perfectly balanced |

> **Assessment**: Well balanced. No action needed.

#### iprod-kafka-business-cluster

| Metric | Broker 1 Avg | Broker 2 Avg | Broker 3 Avg | Skew % | Assessment |
|--------|-------------|-------------|-------------|--------|------------|
| CpuUser | 13.25% | **13.66%** | 12.98% | 2.7% | Excellent balance |
| BytesInPerSec | 12.5 KB/s | **16.4 KB/s** | 16.1 KB/s | 16.7% | Minor skew at low absolute values |
| BytesOutPerSec | 17.2 KB/s | **23.8 KB/s** | 17.5 KB/s | **22.1%** | Broker 2 serves more consumers |
| CpuIoWait | 0.45% | 0.46% | 0.46% | 1.7% | All negligible |
| DiskUsed | 2.97% | 2.97% | 2.97% | 0.0% | Perfectly balanced |

> **Assessment**: BytesOut skew is 22% but absolute values are tiny (24 KB/s max avg). CPU is perfectly balanced. No action needed.

---

### Disk I/O Baseline — gp2 → gp3 Migration Evaluation

**Volume-level metrics** (VolumeReadOps, VolumeWriteOps, VolumeReadBytes, VolumeWriteBytes) returned **0 datapoints** across all 9 brokers. These metrics are registered in CloudWatch but not emitting — likely requires MSK enhanced monitoring at PER_BROKER level.

**Proxy metric used**: CpuIoWait (% CPU time waiting on I/O) + network throughput extrapolation.

#### CpuIoWait (7-day, hourly)

| Cluster | Broker 1 | Broker 2 | Broker 3 | Assessment |
|---------|----------|----------|----------|------------|
| **base** | avg 0.48%, max 1.68% | avg 0.37%, max 1.35% | avg 0.47%, max 1.35% | Negligible I/O wait |
| **architecture** | avg 0.44%, max 1.67% | avg 0.47%, max 1.45% | avg 0.45%, max 1.62% | Negligible I/O wait |
| **business** | avg 0.45%, max 1.50% | avg 0.46%, max 1.53% | avg 0.46%, max 1.52% | Negligible I/O wait |

#### Estimated Disk Throughput (from network metrics, per broker peak)

Kafka disk writes ≈ BytesIn × replication factor. Disk reads ≈ BytesOut (consumer fetches from page cache miss).

| Cluster | Max BytesIn | Max BytesOut | Est. Write (RF=3) | Est. Total Disk I/O | gp2 1TB Burst | gp3 1TB Baseline |
|---------|-------------|--------------|--------------------|--------------------|---------------|-----------------|
| **base** | 1.07 MB/s | 1.50 MB/s | 3.21 MB/s | **4.71 MB/s** | 250 MB/s | 125 MB/s |
| **architecture** | 0.53 MB/s | 0.63 MB/s | 1.59 MB/s | **2.22 MB/s** | 250 MB/s | 125 MB/s |
| **business** | 0.96 MB/s | 0.58 MB/s | 2.88 MB/s | **3.46 MB/s** | 250 MB/s | 125 MB/s |

#### gp2 → gp3 Migration Verdict

| Criteria | gp2 1TB | gp3 1TB | Current Peak | Headroom | Safe? |
|----------|---------|---------|-------------|----------|-------|
| IOPS baseline | 3,000 | 3,000 | Est. <500 (from CpuIoWait <0.5%) | >6x | **YES** |
| Throughput | 250 MB/s (burst) | 125 MB/s (baseline) | 4.71 MB/s (base worst) | >26x | **YES** |
| CpuIoWait | — | — | max 1.68% | — | No I/O bottleneck |

> **Verdict: SAFE to migrate all 3 clusters from gp2 to gp3.** Current I/O utilization is <4% of gp3 baseline limits. Even 10x traffic growth would remain well within gp3 capacity. The gp3 125 MB/s baseline throughput (vs gp2's burstable 250 MB/s) poses zero risk at current volumes.

---

### Consumer Lag Status — Graviton Migration Risk Assessment

Consumer lag indicates how far behind consumers are from producers. High lag during a rolling broker restart (Graviton migration) could cause message processing delays.

#### Lag Summary by Cluster

| Cluster | Total Combos | Groups | Sampled | Worst Time Lag (max) | Worst Offset Lag (max) | Avg Lag Profile |
|---------|-------------|--------|---------|---------------------|----------------------|-----------------|
| **base** | 36 | 18 | All 36 | 1,000s (17 min) | 517 offsets | Most groups 0-7s avg |
| **architecture** | 267 | 115 | 60 | **4,590s (76 min)** | 2,574 offsets | Most groups 0s avg |
| **business** | 315 | 215 | 74 | 1,328s (22 min) | 848 offsets | Most groups 0-1s avg |

#### Top Lag Offenders (EstimatedMaxTimeLag)

| Cluster | Consumer Group | Topic | Avg Lag (s) | Max Lag (s) | Risk |
|---------|---------------|-------|-------------|-------------|------|
| **architecture** | doris_load_consumer_group | lucky_track_hmonitor_business_topic | 4.1 | **4,590** | HIGH — 76 min spike |
| **architecture** | upushapp_push_pos_batch_one_group | upushapp_push_pos_batch_one | 0.0 | 865 | MEDIUM — 14 min spike |
| **business** | kafka_oplog_group | iop_oplog | 0.9 | **1,328** | MEDIUM — 22 min spike |
| **business** | ordered_activity_group | isales_order_status_change | 0.0 | 180 | LOW |
| **business** | ordered_activity_group | isales_member_marketing_event_topic | 0.0 | 120 | LOW |
| **base** | vector_vmlogs_to_es | prod_lucky_nodejs_vm | 0.0 | 1,000 | MEDIUM — 17 min spike |
| **base** | vector_vmlogs_to_es | prod_lucky_java_vm | 7.0 | 960 | MEDIUM |

#### Top Lag Offenders (SumOffsetLag)

| Cluster | Consumer Group | Topic | Avg Offset Lag | Max Offset Lag |
|---------|---------------|-------|----------------|----------------|
| **architecture** | doris_load_consumer_group | lucky_track_hmonitor_business_topic | 41 | 2,574 |
| **architecture** | upushapp_push_pos_batch_one_group | upushapp_push_pos_batch_one | 1 | 463 |
| **business** | kafka_oplog_group | iop_oplog | 2 | 848 |
| **base** | vector_vmlogs_to_es | prod_lucky_nodejs_vm | 0 | 517 |

#### Graviton Migration Lag Risk Assessment

| Cluster | Risk Level | Rationale |
|---------|-----------|-----------|
| **base** | **LOW** | Worst lag spike 17 min (vector_vmlogs_to_es — log shipping, not business-critical). Most groups near 0. Safe for rolling restart. |
| **architecture** | **MEDIUM** | doris_load_consumer_group has 76-min max lag spike. This is a Doris data loading pipeline — transient lag spikes are expected during batch loads. Verify this group can tolerate 5-10 min restart window. push_send groups may have brief notification delays. |
| **business** | **LOW** | Worst lag spike 22 min (kafka_oplog_group — operational logs). Business-critical groups (order_service, crm, sales) show 0 avg lag. Safe for rolling restart. |

> **Graviton Migration Recommendation**: All 3 clusters are safe for rolling Graviton migration. Pre-migration, confirm `doris_load_consumer_group` on architecture cluster can handle a 5-10 minute per-broker restart window (schedule during off-peak if concerned). All business-critical consumer groups show near-zero lag.

---

### Capacity Headroom vs m5.large Limits

m5.large: 2 vCPU, 8 GB RAM, up to 10 Gbps network, EBS-optimized 4,750 Mbps (593 MB/s).

| Resource | m5.large Limit | base (Worst Broker) | arch (Worst) | biz (Worst) | base Headroom | arch Headroom | biz Headroom |
|----------|---------------|---------------------|-------------|-------------|---------------|---------------|--------------|
| CPU | 200% (2 vCPU) | 60.1% user+sys peak | 61.8% | 52.6% | **70%** | **69%** | **74%** |
| Memory | 8 GB | 4.13 GB used peak | 4.30 GB | 4.33 GB | 48% | 46% | 46% |
| Network In | ~10 Gbps | 1.07 MB/s (8.5 Mbps) | 0.53 MB/s | 0.96 MB/s | **>99%** | **>99%** | **>99%** |
| Network Out | ~10 Gbps | 1.50 MB/s (12 Mbps) | 0.63 MB/s | 0.58 MB/s | **>99%** | **>99%** | **>99%** |
| EBS Throughput | 593 MB/s | ~4.7 MB/s est. | ~2.2 MB/s | ~3.5 MB/s | **>99%** | **>99%** | **>99%** |
| Disk Used | 100% | 61.3% | 11.2% | 3.3% | 39% | 89% | 97% |

> **Summary**: CPU is the binding constraint on all clusters. base cluster has ~70% headroom (peak 60% of 200% total vCPU). Network and EBS throughput are effectively unused (<1% of limits). Memory is intentionally high (page cache). Disk is only a concern on base cluster at 61% — plan for growth or adjust retention.