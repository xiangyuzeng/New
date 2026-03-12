# RCA: RDS Multi-AZ Failover — aws-luckyus-isalescdp-rw

**Date of Incident:** 2026-03-12, 12:42 UTC+8 (04:42 UTC)
**Database:** luckyus_isales_cdp
**Instance:** aws-luckyus-isalescdp-rw
**Investigator:** David Zeng (DBA)
**Report Date:** 2026-03-12

---

## 1. Executive Summary

The RDS instance `aws-luckyus-isalescdp-rw` experienced a **Multi-AZ failover triggered by an Out-of-Memory (OOM) condition**. The root cause is a critically undersized instance (`db.t4g.micro` — 1 GB RAM) running with `max_connections=4000` and ~100+ active connections that exhausted all available memory. Pre-failover swap usage was **530+ MB on a 1 GB instance**. RDS auto-reduced `innodb_buffer_pool_size` to 128 MB during recovery, which **remains in effect and must be restored**.

**Severity:** HIGH — Buffer pool is still emergency-reduced; instance is fundamentally undersized.

---

## 2. Instance Profile

| Parameter | Value | Assessment |
|-----------|-------|------------|
| Instance Class | `db.t4g.micro` | **CRITICAL — 1 GB RAM, 2 vCPUs** |
| Engine | MySQL 8.0.40 | Current |
| Multi-AZ | Enabled | Saved availability |
| Storage | gp3, 40 GB, 3000 IOPS | Adequate |
| Created | 2025-03-10 | ~1 year old |
| Performance Insights | **Disabled** | Blind spot for investigation |
| Database Size | **1,058 MB** (~1 GB) | Larger than total RAM! |
| Table Count | 4 | Low |

### Top Tables

| Table | Size (MB) | Rows | Fragmentation |
|-------|-----------|------|---------------|
| t_realtime_user_group_log | 733.5 | 3.3M | 0.7% |
| t_user_state | 309.8 | 1.1M | 6.8% |
| t_user_event_track | 14.0 | 34K | **662.8%** ⚠️ |
| t_user_event | 1.5 | 3K | **6262.4%** ⚠️ |

> `t_user_event_track` and `t_user_event` have extreme fragmentation (93 MB and 91 MB of free space respectively). These should be optimized.

---

## 3. Failover Event Timeline

| Time (UTC) | Event |
|------------|-------|
| 03:51:58 | Automated backup started |
| 03:58:01 | Automated backup completed |
| ~04:05 | CPU spikes from ~6% to **59-67%** (workload begins) |
| 04:00-04:42 | FreeableMemory: **82-102 MB**, SwapUsage: **517-540 MB** |
| 04:00-04:42 | Connections: **70-111 active** |
| **04:42:55** | **Multi-AZ failover started** |
| 04:43:22 | DB instance restarted |
| 04:43:37 | Failover completed — "primary instance is busy and unresponsive" |
| **04:44:47** | **RDS OOM mitigation: auto-set innodb_buffer_pool_size to 128 MB** |
| Post-failover | CPU: ~5-7%, Connections: 13-33, Swap: ~305-406 MB |

---

## 4. Root Cause Analysis

### Primary Cause: Instance Critically Undersized (OOM)

The `db.t4g.micro` instance has only **1 GB RAM**. The database itself is **1,058 MB** — already larger than total instance memory. Combined with:

- **`max_connections = 4000`** — Each connection can allocate up to 17 MB of per-session buffers (sort_buffer 256KB + join_buffer 256KB + read_buffer 256KB + read_rnd_buffer 512KB + tmp_table_size 16MB). With 100+ concurrent connections, session memory alone could demand **1,700+ MB** — far exceeding total RAM.
- **530 MB swap usage** on a 1 GB instance — the system was thrashing heavily
- **Only 82-102 MB free memory** before failover — no headroom at all
- **Automated backup at 03:51-03:58** added I/O pressure right before the workload spike

### Contributing Factors

1. **Backup + workload overlap:** The automated backup (03:51-03:58) completed just minutes before the CPU/memory spike at 04:05, potentially leaving the system in a stressed state.
2. **Connection count surge:** 70-111 connections against a 1 GB instance with per-connection memory of up to 17 MB each.
3. **No Performance Insights:** Without PI enabled, we cannot identify which specific SQL statements drove the CPU/memory spike.
4. **Slow query log empty during incident window:** Likely cleared during the failover restart, losing forensic data.

### Failover Trigger

RDS detected the primary instance was "busy and unresponsive" due to OOM-induced swap thrashing. The Multi-AZ standby was promoted, and RDS applied the emergency OOM mitigation by reducing `innodb_buffer_pool_size` from its previous value down to **128 MB (134217728 bytes)**.

---

## 5. 7-Day CPU History (03:00-06:00 UTC Window)

| Date | 03:00 | 04:00 | 05:00 | 06:00 | Pattern |
|------|-------|-------|-------|-------|---------|
| Mar 05 | — | 5.4% | **29.2%** | 5.4% | Spike at 05:00 |
| Mar 06 | 5.4% | 5.3% | **15.2%** | 5.1% | Spike at 05:00 |
| Mar 07 | 5.5% | 5.3% | **15.9%** | 5.0% | Spike at 05:00 |
| Mar 08 | 5.3% | 5.4% | **16.0%** | 5.5% | Spike at 05:00 |
| Mar 09 | 5.3% | **11.3%** | 5.2% | 6.3% | Shifted to 04:00 |
| Mar 10 | 5.4% | **22.6%** | 5.2% | 6.4% | Spike at 04:00, growing |
| Mar 11 | 5.6% | **25.7%** | 5.2% | **19.8%** | Spike at 04:00 + 06:00 |
| **Mar 12** | 5.8% | **36.8%** ⚠️ | — | — | **FAILOVER at 04:42** |

**Pattern:** A recurring daily batch job runs in the 04:00-05:00 UTC window. The hourly-average CPU has been **escalating** over the past week:
- Mar 05-08: 15-29% (manageable on this tiny instance)
- Mar 09-11: 11-26% (shifting earlier, growing)
- **Mar 12: 36.8%** — but the 1-minute granularity data showed **59-67% sustained** peaks, which combined with memory pressure, tipped the instance into OOM.

This confirms a **progressively worsening daily batch workload** that finally exceeded the instance's capacity on March 12.

---

## 6. Current State (Post-Failover)

| Metric | Value | Assessment |
|--------|-------|------------|
| innodb_buffer_pool_size | **128 MB** | **🔴 CRITICAL — Emergency-reduced, must restore** |
| Buffer Pool Hit Ratio | 99.90% | Good (low load post-failover) |
| Buffer Pool Used | 87.5% (7169/8192 pages) | Already filling at 128 MB |
| Threads Connected | 64 | Moderate |
| Threads Running | 3 | Low (post-failover) |
| Slow Queries (8h) | 1,033 | High — ~129/hour |
| QPS | 46 | Light |
| Swap Usage | 305-406 MB | **Still very high** |
| Uptime | 8.0 hours | Since failover restart |
| tmp_disk_table ratio | 9.5% | Acceptable |

---

## 7. Critical Configuration Issues

| Parameter | Current | Problem | Recommended |
|-----------|---------|---------|-------------|
| `innodb_buffer_pool_size` | **128 MB** | Emergency OOM value; not restored | See sizing below |
| `max_connections` | **4000** | **Absurd for 1 GB RAM**; 100 connections can demand 1.7 GB | **100-150** |
| `table_open_cache` | 4000 | Too high for this instance size | 400-800 |
| `long_query_time` | 0.1s | Fine, but consider 0.5s to reduce log noise | 0.5 |
| Performance Insights | Disabled | Cannot investigate SQL-level issues | **Enable** |

### Memory Budget at Current Sizing (1 GB RAM)

```
Total RAM:                    1,024 MB
  - OS + MySQL overhead:       ~300 MB
  - Buffer Pool (current):      128 MB
  - Available for sessions:    ~596 MB

Per-connection worst case:      ~17 MB
  At 64 connections:          1,088 MB ← EXCEEDS TOTAL RAM
  At 30 connections:            510 MB ← barely fits
```

This is why the instance is **still using 305-406 MB of swap even after failover** — 64 connections on 1 GB RAM is unsustainable.

---

## 8. Recommendations

### 🔴 IMMEDIATE (Today)

1. **Reduce `max_connections` to 150** via RDS Parameter Group
   - Current 4000 is the single biggest risk factor
   - Application connection pools should be audited and limited to 30-50 total
   - This prevents a future OOM even before resizing

2. **Restore `innodb_buffer_pool_size`**
   - Cannot safely increase on db.t4g.micro without reducing max_connections first
   - After max_connections is reduced to 150, set buffer pool to **256 MB** (safe for 1 GB with fewer connections)
   - Both changes require Parameter Group update + reboot (schedule during low-traffic window)

### 🟠 SHORT-TERM (This Week)

3. **Upgrade instance to `db.t4g.small` (2 GB RAM) or `db.t4g.medium` (4 GB RAM)**

   | Instance | RAM | vCPU | On-Demand/mo | With EDP 31% |
   |----------|-----|------|-------------|--------------|
   | db.t4g.micro (current) | 1 GB | 2 | $11.68 | $8.06 |
   | db.t4g.small | 2 GB | 2 | $23.36 | $16.12 |
   | **db.t4g.medium** | **4 GB** | **2** | **$46.72** | **$32.24** |

   **Recommendation: `db.t4g.medium` (4 GB)** — DB size is 1 GB, buffer pool should be ~2 GB (2x data), plus room for connections. Monthly cost increase: **~$24** after EDP discount.

   Post-upgrade settings:
   - `innodb_buffer_pool_size` = 2 GB (on 4 GB instance)
   - `max_connections` = 300 (adequate with more RAM)

4. **Enable Performance Insights** — essential for future incident investigation.

5. **OPTIMIZE TABLE** for fragmented tables:
   - `t_user_event` — 91 MB free space on a 1.5 MB table (6262% fragmentation)
   - `t_user_event_track` — 93 MB free space on a 14 MB table (663% fragmentation)
   - Reclaims ~184 MB of wasted storage

### 🟢 MEDIUM-TERM

6. **Investigate the daily batch job** running at 04:00-05:00 UTC (midnight EST)
   - The CPU load has been growing daily over the past week
   - Identify the application/cron job and optimize its queries
   - Consider shifting batch timing away from backup window (03:51 UTC)

7. **Set up CloudWatch alarms:**
   - FreeableMemory < 200 MB → Warning
   - FreeableMemory < 100 MB → Critical
   - SwapUsage > 100 MB → Warning
   - CPUUtilization > 80% sustained 5 min → Warning

---

## 9. Conclusion

| Item | Finding |
|------|---------|
| **Root Cause** | OOM on db.t4g.micro (1 GB RAM) caused by 100+ connections with max_connections=4000 and a growing daily batch workload |
| **Buffer Pool Status** | 🔴 Still at emergency 128 MB — must be restored after fixing max_connections |
| **Instance Sizing** | 🔴 Critically undersized — upgrade to db.t4g.medium (4 GB, $32/mo) recommended |
| **Recurring Pattern** | Yes — daily batch job at 04:00-05:00 UTC with escalating CPU over 7 days |
| **Data Loss** | None — Multi-AZ failover preserved data integrity |
| **Service Impact** | Brief outage during failover (04:42-04:43, ~42 seconds) |

---

*Report generated: 2026-03-12 | Instance: aws-luckyus-isalescdp-rw | Database: luckyus_isales_cdp*
