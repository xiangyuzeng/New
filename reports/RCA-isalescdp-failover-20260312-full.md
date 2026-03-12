# RDS Multi-AZ Failover Incident Report
## aws-luckyus-isalescdp-rw (Production)
**Incident Date:** 2026-03-12 | **Failover Time:** 04:42–04:43 UTC (12:42–12:43 CST)
**Severity:** P0 | **Status:** Resolved (active secondary risk remains)
**Report Author:** David Zeng (DBA) | **Report Date:** 2026-03-12

---

## 1. Executive Summary

The `isalescdp` MySQL RDS instance experienced an unplanned Multi-AZ failover caused by **sustained write I/O saturation combined with critical memory exhaustion on a severely undersized db.t4g.micro instance**.

Starting at ~04:05 UTC, an unidentified batch/ETL workload drove WriteIOPS to ~1,000 IOPS for 20+ consecutive minutes. With only 82–103 MB of RAM free (baseline swap already at 517–539 MB), the primary instance exhausted available memory and became "busy and unresponsive." RDS automatically promoted the standby replica at 04:43 UTC. The RTO was approximately 42 seconds.

**Root cause:** A recurring early-morning write-intensive workload (distinct from the known 05:00 UTC daily batch, occurring 1 hour earlier) exceeded the capacity of a db.t4g.micro (1 GB RAM, 1 vCPU) instance that was already running at critical memory pressure due to persistent swap thrashing.

**Active production risk:** `innodb_buffer_pool_size` is currently locked at 128 MB (RDS auto-reduced from ~768 MB as an OOM mitigation). Post-failover swap is already rebuilding to 365–407 MB. Without intervention, a repeat OOM event is likely.

---

## 2. Incident Timeline

| Time (UTC) | Time (CST) | Event |
|---|---|---|
| 03:51:58 | 11:51 | RDS automated daily backup started |
| 03:58:01 | 11:58 | Daily backup completed |
| ~04:00 | ~12:00 | WriteIOPS begins spiking (936 IOPS at 04:01) |
| 04:05 | 12:05 | CPU jumps to 59.9%; FreeableMemory already at ~82 MB |
| 04:06–04:27 | 12:06–12:27 | Sustained stress: CPU 59–67%, WriteIOPS 986–1,088, Connections 87–111 |
| 04:26 | 12:26 | Peak DatabaseConnections: 111 |
| ~04:28 | ~12:28 | Prometheus exporter loses MySQL connection (primary unresponsive) |
| 04:28–04:42 | 12:28–12:42 | **DATA GAP** — metrics unavailable (exporter disconnected) |
| 04:42 | 12:42 | **P0 ALR-050 fired** (exporter down alert) |
| 04:42:55 | 12:42 | RDS event: "Multi-AZ instance failover started" |
| 04:43:22 | 12:43 | RDS event: "DB instance restarted" |
| 04:43:37 | 12:43 | RDS event: "Multi-AZ instance failover completed" |
| 04:43:37 | 12:43 | RDS event: "Primary instance was busy and unresponsive" |
| ~04:43 | ~12:43 | **MySQL uptime restart alert fired** |
| 04:44:47 | 12:44 | RDS event: OOM mitigation — `innodb_buffer_pool_size` auto-reduced to 134217728 (128 MB) |
| 04:59+ | 12:59+ | Instance stabilized; 29 connections, but swap already at 365–407 MB |

**Recovery Time Objective (actual):** 04:42:55 → 04:43:37 = **~42 seconds**

---

## 3. Instance Profile

| Property | Value | Assessment |
|---|---|---|
| Instance Class | db.t4g.micro | ⚠️ UNDERSIZED — 1 vCPU, 1 GB RAM |
| Engine | MySQL 8.0.40 | OK |
| Multi-AZ | Enabled | ✅ Correct (failover worked) |
| Storage | 40 GB gp3 | OK (baseline 3,000 IOPS available) |
| Performance Insights | **DISABLED** | ❌ No SQL-level visibility |
| Enhanced Monitoring | **DISABLED** | ❌ No OS-level memory stats |
| Parameter Group | luckyus-prod-80-new | Note: `ApplyMethod: pending-reboot` |
| `innodb_buffer_pool_size` (configured) | `{DBInstanceClassMemory*3/4}` ≈ 768 MB | — |
| `innodb_buffer_pool_size` (actual NOW) | **134,217,728 bytes (128 MB)** | ❌ STUCK AT OOM-REDUCED VALUE |
| `max_connections` | **4,000** | ❌ DANGEROUSLY HIGH for 1 GB RAM |

---

## 4. Metric Analysis (04:00–05:00 UTC, 60s granularity)

### 4.1 CPU Utilization

```
04:00 → 59.0%   (already critical at start of window)
04:01 → 50.8%
04:02-04:04 → 6-10%   (brief anomalous dip — may be I/O wait reclassification)
04:05 → 59.9%
04:06 → 66.3%
04:07-04:27 → 59-67%  SUSTAINED (20+ minutes)
[GAP: 04:28-04:42]
04:42 → 1.7%   (failover — primary unloaded)
04:43 → 23.0%  (standby coming up)
04:44+ → 5-8%  (normal post-failover)
```

### 4.2 FreeableMemory

```
04:00-04:27 → 82-103 MB   ❌ CRITICAL (8-10% of 1GB RAM)
[GAP: 04:28-04:42]
04:43-04:59 → 85-124 MB   Still critically low post-failover
```

### 4.3 SwapUsage (CRITICAL INDICATOR)

```
04:00-04:27 → 517-539 MB   ❌ >50% of total RAM in swap
[GAP: 04:28-04:42]
04:43 → 305 MB   (partially released on restart)
04:44-04:59 → 365-407 MB  ⚠️ REBUILDING — heading back toward threshold
```

### 4.4 DatabaseConnections

```
04:00 → 70    → 04:01 → 99 (spike at workload start)
04:05-04:27 → 87-111 (peak 111 at 04:26)
[GAP: 04:28-04:42]
04:43 → 3     (post-restart: almost all connections dropped)
04:59 → 29    (recovery in progress)
```

### 4.5 WriteIOPS — THE SMOKING GUN

```
04:01 → 936 IOPS
04:06 → 986 IOPS
04:07-04:27 → 986-1,088 IOPS  ❌ SUSTAINED ~1,000 IOPS FOR 20+ MINUTES
[GAP: 04:28-04:42]
04:43+ → 0.7-9 IOPS   ✅ Write workload COMPLETELY STOPPED (100x reduction)
```

The 100x drop in WriteIOPS post-failover confirms the write workload was coming from **a process that either failed, was killed by the restart, or naturally completed** during the failover window. This is not a traffic pattern that continues continuously — it is a **batch/ETL job**.

### 4.6 ReadIOPS

```
04:01 → 504 IOPS
04:06-04:27 → 163-405 IOPS sustained
Post-failover → 7-190 IOPS (significantly reduced)
```

---

## 5. Root Cause Analysis

### 5.1 Causal Chain

```
Unknown batch/ETL job triggered at ~04:00 UTC
    ↓
WriteIOPS: 936-1,088 IOPS for 20+ minutes (exhausting I/O capacity)
    ↓
CPU: 59-67% sustained (write-amplified workload, temp table creation, index updates)
    ↓
Buffer pool thrashing: With only 128-768 MB buffer pool on 1 GB RAM,
working set couldn't fit → constant disk I/O
    ↓
FreeableMemory: 82-103 MB (already at critical floor due to chronic swap)
SwapUsage: 517-539 MB baseline → expanded further under load
    ↓
Primary instance OOM: memory fully exhausted, becomes unresponsive
    ↓
RDS detects primary unresponsive → triggers Multi-AZ failover
    ↓
Standby promoted (04:43:37 UTC, ~42s RTO)
    ↓
RDS OOM mitigation: innodb_buffer_pool_size auto-reduced to 128MB
```

### 5.2 Contributing Factors

| Factor | Detail | Severity |
|---|---|---|
| Instance undersizing | db.t4g.micro (1 GB RAM) for production CDP workload | Critical |
| Chronic swap thrashing | 517-539 MB swap BEFORE the incident started | Critical |
| `max_connections = 4000` | 4,000 connections × ~100-200 KB overhead = 400-800 MB potential RAM drain | High |
| Performance Insights disabled | No SQL-level visibility — cannot identify which queries caused write storm | High |
| Enhanced Monitoring disabled | No OS-level memory breakdown | Medium |
| `innodb_buffer_pool_size` still at 128 MB | Post-OOM reduction never restored; configuration requires reboot | Active Critical |
| Backup window proximity | Backup completed at 03:58 — may have triggered downstream ETL | Medium |
| Long-running connection | 28,554-second (~7.9 hour) connection in processlist — potential resource leak | Medium |

### 5.3 What We Don't Know (Gaps)

- **Identity of the write workload**: `slow_query_log` appears disabled or not logging to table — zero slow query records found for 03:50–04:45 UTC window. Cannot determine which SQL statements caused the write storm.
- **04:28–04:42 UTC**: 14-minute data gap during primary unresponsiveness.
- **The long-running connection**: A 28,554-second (~7.9 hour) connection was active at time of investigation. This predates the incident by hours and may be a Canal CDC connection or a hung application session.

---

## 6. Recurring Pattern Analysis (7-Day History)

**Daily early-morning CPU peaks in the 03:00–05:00 UTC window:**

| Date (UTC) | Peak CPU | Peak Time | Notes |
|---|---|---|---|
| Mar 5 | ~28.5% | 05:01 | Batch at 05:00 — normal |
| Mar 6 | ~15.0% | 04:24 | Elevated |
| Mar 7 | ~15.8% | 04:48 | Elevated |
| Mar 8 | ~12.9% | 04:11 | Elevated |
| Mar 9 | ~5.3% | 04:35 | No spike (anomaly or holiday) |
| Mar 10 | ~22.3% | 03:58 | Increasing severity |
| Mar 11 | ~23.2% | 03:21 | Increasing severity |
| Mar 12 | **36.0% → 67%** | 03:45 → 04:05+ | **INCIDENT DAY** |

**Conclusion:** This is a **progressively worsening weekly pattern**. CPU peaks in the 03:00–05:00 UTC window have been building from ~13% to 23% to 36% to 67% over 7 days. This strongly indicates:
1. An accumulating data volume (more rows to process each day), OR
2. A changing workload pattern (job running earlier and earlier in the window), OR
3. A data retention problem (no TTL/cleanup on historical data the job processes)

The instance was going to fail — today's incident was not an isolated event, it was the **inevitable outcome of a week of escalating stress on an undersized instance**.

---

## 7. Alert Evaluation

### Alert 1: P0 ALR-050 — Exporter Down
```
Expression: up{job=~".*exporter.*"} == 0
Fired at: ~04:42 UTC
```
**Assessment: CORRECT behavior, but LATE warning.**
- The exporter correctly detected the primary was unreachable.
- However, this alert fired after ~14 minutes of the primary being unresponsive.
- **Gap identified:** No proactive memory/swap alert exists. By the time the exporter alert fires, the instance is already unresponsive and the failover is underway.

### Alert 2: MySQL Uptime Restart
```
Expression: max_over_time(mysql_global_status_uptime[1m]) < max_over_time(mysql_global_status_uptime[1m] offset 2m)
Fired at: ~04:43 UTC (post-failover)
```
**Assessment: CORRECT and TIMELY.** Fired correctly after the standby was promoted and MySQL uptime reset.

### Missing Alerts (Gaps):

| Metric | Recommended Threshold | Priority |
|---|---|---|
| FreeableMemory < 200 MB | CloudWatch alarm on FreeableMemory | P1 |
| SwapUsage > 256 MB | CloudWatch alarm on SwapUsage | P1 |
| WriteIOPS > 800 IOPS sustained 5m | CloudWatch alarm | P2 |
| CPU > 80% for 5 min | CloudWatch alarm on CPUUtilization | P2 |
| DatabaseConnections > 200 | Alarm (relative to appropriate max_connections) | P2 |

---

## 8. Remediation Plan

### Priority 1 — IMMEDIATE (Today, within hours)

#### 8.1 Restore innodb_buffer_pool_size
The buffer pool is currently at 128 MB (OOM-reduced). Parameter group already has the correct formula, but it requires a reboot to take effect.

**Option A (immediate, brief downtime): Force parameter reapplication**
```bash
# Multi-AZ reboot — short failover, ~30s downtime
aws rds reboot-db-instance \
  --db-instance-identifier aws-luckyus-isalescdp-rw \
  --force-failover \
  --region us-east-1
```
After reboot, verify:
```sql
SHOW GLOBAL VARIABLES LIKE 'innodb_buffer_pool_size';
-- Expected: ~805306368 (768MB)
```

**Option B (no downtime, temporary): SET GLOBAL**
```sql
SET GLOBAL innodb_buffer_pool_size = 536870912;  -- 512MB (conservative for 1GB RAM)
```
Note: This is lost on next restart. The parameter group fix (via reboot) is the permanent solution.

**Recommendation:** Do Option A in a scheduled maintenance window (low traffic period), or Option B immediately as a stopgap.

#### 8.2 Reduce max_connections
```sql
-- Current: 4000 (catastrophically wrong for 1GB RAM)
-- ~100-200 KB per connection × 4000 = 400-800 MB RAM overhead
-- Recommendation: reduce to 200 for db.t4g.micro
```
Update in RDS parameter group `luckyus-prod-80-new`:
- `max_connections = 200` (or `{DBInstanceClassMemory/12582880}` ≈ 83 for auto-scaling)

#### 8.3 Identify the write workload
Check application teams and ETL job schedulers for any job that:
- Runs at ~04:00 UTC (not 05:00 UTC)
- Issues heavy bulk writes to isalescdp tables
- May be related to the daily backup completion at 03:58 UTC triggering downstream processing

```sql
-- Check slow_query_log configuration
SHOW GLOBAL VARIABLES LIKE 'slow_query_log%';
SHOW GLOBAL VARIABLES LIKE 'log_output%';
-- Enable if needed:
SET GLOBAL slow_query_log = ON;
SET GLOBAL log_output = 'TABLE';
SET GLOBAL long_query_time = 1;
```

#### 8.4 Investigate the long-running connection
```sql
SELECT id, user, host, db, command, time, state, LEFT(info, 200)
FROM information_schema.processlist
WHERE time > 3600  -- connections open > 1 hour
ORDER BY time DESC;
-- Found: 28,554s connection (likely Canal CDC or hung app)
-- If Canal: check canal replication lag and connection health
-- If application: kill the connection and trace the source
```

### Priority 2 — URGENT (This week)

#### 8.5 Upgrade instance class
The db.t4g.micro **cannot support this workload**. This was reportedly recommended after a **previous failover on Feb 11** and never implemented.

| Option | RAM | vCPU | On-Demand/hr | EDP cost/month | Assessment |
|---|---|---|---|---|---|
| db.t4g.micro (current) | 1 GB | 2 | $0.016 | ~$8 | ❌ Insufficient |
| db.t4g.small | 2 GB | 2 | $0.032 | ~$16 | ✅ Minimum viable |
| db.t4g.medium | 4 GB | 2 | $0.065 | ~$33 | ✅ Recommended |
| db.t4g.large | 8 GB | 2 | $0.129 | ~$65 | ✅ Comfortable headroom |

**Recommendation: db.t4g.medium (4 GB RAM)** — provides 4x RAM headroom, eliminates swap thrashing, costs only ~$25/month more than current, and prevents repeat OOM incidents. For an instance that just caused a P0 production outage, this is a minimal investment.

```bash
# Modify instance class (requires brief failover for Multi-AZ)
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-isalescdp-rw \
  --db-instance-class db.t4g.medium \
  --apply-immediately \
  --region us-east-1
```

#### 8.6 Enable Performance Insights
```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-isalescdp-rw \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --region us-east-1
```
Cost: ~$0.02/vCPU/hour for retention beyond 7 days (7-day free tier applies).

#### 8.7 Enable Enhanced Monitoring
```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-isalescdp-rw \
  --monitoring-interval 60 \
  --monitoring-role-arn arn:aws:iam::257394478466:role/rds-monitoring-role \
  --region us-east-1
```

### Priority 3 — FOLLOW-UP (This sprint)

#### 8.8 Create proactive CloudWatch alarms
```bash
# FreeableMemory < 200MB alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "RDS-isalescdp-LowFreeableMemory" \
  --metric-name FreeableMemory \
  --namespace AWS/RDS \
  --dimensions Name=DBInstanceIdentifier,Value=aws-luckyus-isalescdp-rw \
  --period 300 --evaluation-periods 2 \
  --threshold 209715200 --comparison-operator LessThanThreshold \
  --statistic Average --alarm-actions <SNS_TOPIC_ARN> \
  --region us-east-1

# SwapUsage > 256MB alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "RDS-isalescdp-HighSwapUsage" \
  --metric-name SwapUsage \
  --namespace AWS/RDS \
  --dimensions Name=DBInstanceIdentifier,Value=aws-luckyus-isalescdp-rw \
  --period 300 --evaluation-periods 2 \
  --threshold 268435456 --comparison-operator GreaterThanThreshold \
  --statistic Average --alarm-actions <SNS_TOPIC_ARN> \
  --region us-east-1
```

#### 8.9 Review write workload and consider write optimization
Once the write workload is identified:
- Batch size tuning (reduce commit frequency to lower WriteIOPS)
- Schedule adjustment (push to off-peak window, or distribute load)
- Index review on tables receiving bulk writes
- Consider read replica for analytics queries hitting isalescdp

---

## 9. Summary of Findings

| # | Finding | Severity |
|---|---|---|
| 1 | Write storm: ~1,000 WriteIOPS sustained 20+ min caused the OOM | Root Cause |
| 2 | db.t4g.micro (1GB RAM) is critically undersized for this workload | Critical |
| 3 | `innodb_buffer_pool_size` still at 128 MB (OOM-reduced) — active risk | Active Critical |
| 4 | SwapUsage already rebuilding to 365-407 MB post-failover | Active Critical |
| 5 | Recurring pattern: 7-day escalating CPU in 03:00-05:00 UTC window | Critical |
| 6 | `max_connections = 4000` is dangerous for 1GB RAM instance | High |
| 7 | Performance Insights + Enhanced Monitoring both disabled | High |
| 8 | No proactive memory/swap alerts — failover was the first notification | High |
| 9 | slow_query_log disabled — unable to identify specific queries | Medium |
| 10 | 28,554s long-running connection requires investigation | Medium |
| 11 | Instance upgrade recommended after Feb 11 failover — not yet done | High |

---

## 10. Next Actions (Assigned: David Zeng)

- [ ] **URGENT**: Discuss with application team: identify what batch/ETL job runs at ~04:00 UTC
- [ ] **URGENT**: Apply innodb_buffer_pool_size fix (schedule maintenance window with team)
- [ ] **URGENT**: Update `max_connections` parameter to ≤ 300
- [ ] **THIS WEEK**: Submit change request to upgrade isalescdp to db.t4g.medium
- [ ] **THIS WEEK**: Enable Performance Insights and Enhanced Monitoring
- [ ] **THIS WEEK**: Create CloudWatch alarms for FreeableMemory and SwapUsage
- [ ] **THIS WEEK**: Enable slow_query_log to TABLE for future visibility
- [ ] **FOLLOW-UP**: Review and kill/investigate 28,554s long-running connection
- [ ] **FOLLOW-UP**: Review Canal CDC connection health and replication lag
- [ ] **ESCALATE**: Report to Michael (CTO): repeat failover despite Feb 11 recommendation not being actioned

---

*Report generated: 2026-03-12 | All times UTC unless noted | Based on CloudWatch metrics, RDS events, and MySQL processlist data*
