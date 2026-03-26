# RCA: isalescdp Active Threads Alert — 2026-03-26

## Alert Summary

| Field | Value |
|-------|-------|
| **Alert Name** | MySQL Active Threads High |
| **RDS Instance** | `aws-luckyus-isalescdp-rw` |
| **Instance Class** | db.t4g.medium (2 vCPU, 4 GB RAM, burstable) |
| **Engine** | MySQL 8.0.40 |
| **Multi-AZ** | Yes |
| **Storage** | 40 GB gp3, 3000 IOPS |
| **Alert Threshold** | Active threads > 24 for 2+ minutes |
| **Peak Threads** | 30 |
| **Start Time** | 2026-03-26 04:15:15 UTC (00:15 US-East) |
| **Recovery** | 2026-03-26 04:16:15 UTC |
| **Duration** | 2 minutes 15 seconds |
| **Severity** | L1 (Sales/CDP — important service) |

## Prior Incident History

| Date | Incident | Root Cause | Instance |
|------|----------|------------|----------|
| 2026-02-11 | Multi-AZ failover, exporter timeout | OOM on db.t4g.micro (1 GB) | db.t4g.micro |
| 2026-02-26 | Slow query spike (4,603 queries) | Memory exhaustion, I/O saturation | db.t4g.micro |
| 2026-03-12 | Multi-AZ failover | OOM, swap 530+ MB | db.t4g.micro |
| 2026-03-20 | **Instance upgrade applied** | Upgrade to db.t4g.medium (4 GB) | db.t4g.medium |
| **2026-03-26** | **Active threads alert (this incident)** | **CPU saturation from write storm** | **db.t4g.medium** |

---

## Root Cause Analysis

### Primary Cause: CDP Real-Time Pipeline Write Storm on `t_user_state`

The CDP real-time user event processing pipeline (`icdprealtimeuge_A_w`) fires massive concurrent DELETE + INSERT + COMMIT operations on the `t_user_state` table from 4 application hosts simultaneously. This creates sustained **1,000-1,160 WriteIOPS** for 25+ minutes, saturating the 2 vCPUs at **72.4% peak CPU** and causing InnoDB handler commit queuing that pushes active threads above the 24-thread alert threshold.

### Contributing Factors

1. **Insufficient vCPU count**: 2 vCPUs on db.t4g.medium cannot sustain 1,000+ write IOPS without thread pileup
2. **Per-row transactions**: Each DELETE/INSERT pair commits individually (~100-230ms per operation), creating commit storm
3. **4 concurrent writer hosts**: Application spreads writes across 4 nodes (10.238.33.55, .40.117, .41.114, .46.147) without rate limiting
4. **InnoDB row lock contention**: 460 row lock waits (avg 12ms, peak 68ms) on concurrent DELETEs to same table
5. **max_connections = 4000**: Excessive for 2-vCPU instance; peak reached 155 connections at 04:16:00

### What the Upgrade Fixed (OOM Resolved)

| Metric | Before (db.t4g.micro) | After (db.t4g.medium) | Status |
|--------|----------------------|----------------------|--------|
| SwapUsage | 530+ MB | **0 bytes** | RESOLVED |
| FreeableMemory | 87-104 MB (10%) | **~1,500 MB (37%)** | RESOLVED |
| Buffer Pool | 128 MB (emergency) | **2,048 MB** | RESOLVED |
| Buffer Pool Hit Ratio | Degraded | **99.997%** | RESOLVED |
| OOM Failovers | 2 in 30 days | **0 since upgrade** | RESOLVED |

### What Remains (CPU Bottleneck Exposed)

The upgrade resolved memory pressure but exposed the underlying CPU bottleneck that was previously masked by I/O wait from swapping.

---

## Evidence

### 1. CPU Utilization (1-min granularity, 03:50-04:28 UTC)

```
03:50-03:59  ~4.6-6.3%    ← Baseline
04:00        30.1%         ← Initial batch trigger
04:01        45.9%         ← Ramping
04:02-04:04  4.6-5.0%     ← Brief pause
04:05        28.2%         ← Second wave begins
04:06-04:08  57.5-58.6%   ← Climbing
04:09        62.9%
04:10        65.4%
04:11        68.4%
04:12        71.6%
04:13        72.4%         ← Near peak
04:14        71.8%
04:15        72.4%         ← ALERT FIRES (peak)
04:16        72.0%         ← ALERT RECOVERS
04:17        70.5%         ← Declining
04:18-04:21  66.8-69.7%   ← Still elevated
04:22-04:27  57.5-61.7%   ← Gradually returning
```

### 2. CPU Credit Balance (Not Exhausted)

| Time | Credit Balance | Max Possible | Status |
|------|---------------|-------------|--------|
| 03:50 UTC | 576.0 | 576 | Full |
| 04:03 UTC | 571.4 | 576 | 99.2% |
| 04:16 UTC | 559.0 | 576 | **97.0%** |
| Surplus Credits | 0.0 | — | Never used |

**Conclusion**: CPU credits are NOT depleted. This is genuine CPU saturation from workload, not T-class throttling.

### 3. WriteIOPS (1-min granularity)

```
03:50-03:59  ~8-20 IOPS   ← Baseline
04:00         741 IOPS    ← 40x spike
04:01         656 IOPS
04:02-04:04  ~10-84 IOPS  ← Brief pause
04:05         775 IOPS    ← Second sustained wave
04:06-04:28  1,013-1,159 IOPS  ← SUSTAINED 1,000+ IOPS for 23 minutes
```

**Pattern**: Baseline 10-20 IOPS → **sustained 1,000-1,160 IOPS** for 23+ minutes. The gp3 3,000 IOPS limit is not reached, but 2 vCPUs cannot process this write volume without thread queuing.

### 4. Slow Query Analysis (04:10-04:20 UTC)

- **566 slow queries** in 10-minute window
- **100% from user**: `icdprealtimeuge_A_w` (CDP real-time pipeline)
- **100% on table**: `t_user_state`
- **Query patterns**:
  - `DELETE FROM t_user_state WHERE user_no = ? AND event_type = ? AND tenant = 'LKUS'` (100-230ms)
  - `INSERT INTO t_user_state (user_no, event_type, event_state_value, ...) VALUES (...)` (100-230ms)
  - `commit` (100-230ms)
  - `SELECT 1 FROM t_user_event WHERE ... (subquery on t_user_state)` (100-210ms, from `icdprealtimeuge_A_o`)
- **Lock contention**: One DELETE showed Lock_time of **68ms** (normal is <1ms)
- **All queries from 4 hosts**: 10.238.33.55, 10.238.40.117, 10.238.41.114, 10.238.46.147

### 5. Connection Analysis

**Current state** (post-alert):

| Host | Connections | Active | Sleeping |
|------|------------|--------|----------|
| 10.238.40.117 | 24 | 4 | 20 |
| 10.238.39.228 | 8 | 0 | 8 |
| 10.238.34.19 | 6 | 0 | 6 |
| 10.238.46.147 | 4 | 0 | 4 |
| 10.238.33.55 | 4 | 0 | 4 |
| 10.238.41.114 | 4 | 0 | 4 |
| Others | 23 | 2 | 21 |
| **Total** | **76** | **8** | **68** |

**Peak during alert**: Max_used_connections = **155** at 2026-03-26 04:16:00

### 6. Thread Status

| Metric | Current | At Alert Peak |
|--------|---------|---------------|
| Threads_connected | 73 | ~155 |
| Threads_running | 8 | ~30 (alert threshold: 24) |
| Max_used_connections | 155 | — |
| Max_used_connections_time | 04:16:00 | — |

### 7. Table & Index Analysis

**Target table** — `t_user_state`:
- 1,094,863 rows, 231 MB data + 88 MB index = **320 MB**
- Fragmentation: 3.1% (acceptable)
- Index: `idx_user_state(user_no, event_type, event_value, event_state_value)`
- DELETE WHERE clause: `user_no = ? AND event_type = ? AND tenant = ?`
- **`tenant` column is NOT indexed** — requires post-index-lookup filtering

**Other tables**:

| Table | Rows | Size (MB) | Frag % |
|-------|------|-----------|--------|
| t_realtime_user_group_log | 4.3M | 873 | 0.5% |
| t_user_state | 1.1M | 320 | 3.1% |
| t_user_event_track | 371K | 111 | 6.3% |
| t_user_event | 108K | 52 | **125.8%** |

### 8. InnoDB Buffer Pool Health

| Metric | Value | Status |
|--------|-------|--------|
| Total pages | 131,072 (2 GB) | Correctly sized |
| Data pages | 61,668 (47%) | Healthy |
| Free pages | 69,391 (53%) | Ample headroom |
| Dirty pages | 6,214 (5%) | Normal |
| Wait_free | 0 | No buffer pool pressure |
| Hit ratio | 99.997% | Excellent |
| Row lock waits | 460 | Moderate |
| Row lock avg time | 12 ms | Moderate |
| Log waits | 0 | No redo log bottleneck |

### 9. Memory Health (Post-Upgrade Validation)

| Metric | 24h Range | Status |
|--------|-----------|--------|
| FreeableMemory | 1,512-1,625 MB | Healthy (~37% of 4 GB) |
| SwapUsage | **0 bytes** | RESOLVED (was 530+ MB) |

### 10. Historical CPU Pattern (7-Day)

| Date | Peak CPU % | Time (UTC) | Pattern |
|------|-----------|------------|---------|
| Mar 19 | 72.2% | 04:00 | Daily CDP batch |
| Mar 20 | 55.9% | 03:28 | (post-upgrade, re-stabilizing) |
| Mar 21 | 61.2% | 02:56 | Daily CDP batch |
| Mar 22 | 62.7% | 02:24 | Daily CDP batch |
| Mar 23 | 60.4% | 04:00 | Daily CDP batch |
| Mar 24 | 63.2% | 03:28 | Daily CDP batch |
| Mar 25 | 67.3% | 02:56 | Daily CDP batch |
| **Mar 26** | **72.4%** | **04:15** | **ALERT — trending upward** |

**Trend**: Daily peak CPU is trending upward (55.9% → 72.4% over 6 days post-upgrade), suggesting workload volume is growing. The secondary peak at ~08:16-10:00 UTC (50-54%) corresponds to US business hours.

### 11. RDS Events (Past 7 Days)

| Date | Event |
|------|-------|
| Mar 20 01:42 | Instance class modification started |
| Mar 20 01:45 | Multi-AZ failover (during upgrade) |
| Mar 20 01:52 | Instance class modification completed |
| Mar 20-26 | Daily automated backups ~03:51 UTC |
| Mar 23 | Security patching available notification |

No error events or unplanned failovers since the upgrade.

---

## Sizing Recommendation

### Recommended: Upgrade to db.r6g.xlarge (4 vCPU, 32 GB)

The root cause is **2 vCPUs being saturated at 72% by 1,000+ sustained WriteIOPS**. Since CPU credits are NOT the issue (97% remaining), moving to a non-burstable instance with the same 2 vCPUs (db.r6g.large) would provide only marginal improvement. The workload needs **more vCPUs**.

| Instance | vCPU | RAM | On-Demand/mo | EDP (31%)/mo | CPU at Current Load |
|----------|------|-----|-------------|-------------|-------------------|
| db.t4g.medium (current) | 2 | 4 GB | ~$47 | ~$32 | **72%** (alerting) |
| db.r6g.large | 2 | 16 GB | ~$168 | ~$116 | ~65-70% (still tight) |
| **db.r6g.xlarge** | **4** | **32 GB** | **~$336** | **~$232** | **~35%** (comfortable) |
| db.r6g.2xlarge | 8 | 64 GB | ~$672 | ~$464 | ~18% (overkill) |

**Why r6g.xlarge over r6g.large**:
- r6g.large still has 2 vCPUs — same thread pileup risk since the bottleneck is CPU core count, not burstability
- r6g.xlarge doubles the vCPU count (4), cutting CPU utilization to ~35% and providing headroom for the growing workload trend
- The growing trend (55.9% → 72.4% over 6 days) suggests r6g.large would be undersized within weeks

**Cost impact**: +$200/month (+$2,400/year) after EDP discount. This is the cost of eliminating active thread alerts and providing growth headroom.

---

## Recommendations

| Priority | Action | Owner | Timeline | Impact |
|----------|--------|-------|----------|--------|
| **P1** | Upgrade to db.r6g.xlarge (4 vCPU, 32 GB) | DBA | This week | Eliminates CPU bottleneck, drops peak CPU to ~35% |
| **P1** | Coordinate with ops team on CDP batch scheduling | DBA + Ops | This week | Understand if the 04:00 UTC batch can be staggered |
| **P2** | Application optimization: batch DELETE+INSERT into multi-row transactions | App Dev | 2 weeks | Reduce commit count by 10-50x, lower WriteIOPS |
| **P2** | Add composite index `idx_user_state_tenant(user_no, event_type, tenant)` | DBA | 1 week | Improve DELETE efficiency, reduce lock contention |
| **P2** | Reduce `max_connections` from 4000 to 300 | DBA | 1 week | Prevent connection stampede, reduce per-connection memory |
| **P3** | OPTIMIZE TABLE `t_user_event` (125.8% fragmentation) | DBA | 2 weeks | Reclaim 65 MB, improve read performance |
| **P3** | Consider `REPLACE INTO` or `INSERT ON DUPLICATE KEY UPDATE` instead of DELETE+INSERT | App Dev | 1 month | Eliminate lock contention from paired operations |
| **P3** | Adjust alert threshold from 24 to 32 if r6g.xlarge handles the load | DBA | After upgrade | Reduce noise if upgraded instance handles the burst |

---

## Appendix: Alert vs. Batch Job Timeline

The known batch job previously ran at **05:00 UTC** (00:00 EST). Today's alert fired at **04:15 UTC**. The CDP real-time pipeline processing starts at **04:00 UTC** based on WriteIOPS data. Historical 7-day data shows the peak window varies between 02:24–04:15 UTC, suggesting this is a **continuous real-time stream with variable burst timing**, not a fixed cron job.

The backup job also runs at ~03:51 UTC daily and overlaps with the CDP write storm, adding ~100 IOPS of read I/O from the backup process.

---

*Report generated: 2026-03-26 | Investigator: David Zeng (DBA)*
*Instance: aws-luckyus-isalescdp-rw | Account: 257394478466 | Region: us-east-1*
