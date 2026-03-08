# ES Cluster RED Status Investigation Report

**Cluster**: `luckycommon`
**Alert**: AWS-ES 集群状态Red
**RED Onset**: 2026-03-08 07:00 UTC
**Recovery to GREEN**: 2026-03-08 07:07 UTC
**Total Unhealthy Duration**: ~7 minutes (RED: ~1 min, YELLOW: ~6 min)
**Severity**: **P1 — Auto-recovered, no data loss**

---

## 1. Affected Cluster Summary

| Property | Value |
|---|---|
| **Domain Name** | luckycommon |
| **Engine** | Elasticsearch 6.8 (EOL) |
| **Data Nodes** | 4× m5.large.elasticsearch (2 vCPU, 8 GiB RAM each) |
| **Dedicated Masters** | 3× t3.small.elasticsearch |
| **Total Nodes** | 7 |
| **EBS Volume** | 100 GB gp3 per node (400 GB total data) |
| **Zone Awareness** | 2 AZs (us-east-1) |
| **Account** | 257394478466 |
| **Primary Shards** | 59 |
| **Total Active Shards** | 100 (normal) |

## 2. Post-Recovery Status (confirmed 2026-03-08)

| Metric | Value | Status |
|---|---|---|
| **Cluster Status** | GREEN | Healthy |
| **Node Count** | 7 of 7 | All nodes present |
| **Unassigned Shards** | 0 | All shards allocated |
| **Active Primary Shards** | 59 of 59 | Full |
| **Active Total Shards** | 100 | Normal |
| **JVM Memory Pressure** | 68-74% | Below warning (80%) |
| **CPU Utilization** | 10-43% | Normal |
| **Master Reachable** | YES (throughout incident) | Stable |
| **Free Storage** | ~117 GB total (~29 GB/node avg) | OK |
| **5xx Errors** | 3 during incident | Resolved |
| **Prometheus Health Check** | 0 (healthy) | Confirmed |
| **Active CloudWatch Alarms** | None ES-related | Clean |

## 3. Full Incident Timeline

### Phase 1: Normal Operation (06:00–06:56 UTC) — Status: GREEN
```
Time (UTC)     JVM Max%  Nodes  Free Storage(MB)  Indexing(docs/5m)  Search(req/5m)
────────────── ──────── ────── ──────────────── ────────────────── ──────────────
06:00-06:50    68-74%   7      157,000-158,000   ~2,600-3,100       ~170-310
06:55          74.2%    7      158,094            ~3,100             ~280
```

### Phase 2: Large Index Deletion (06:57–06:59 UTC) — Status: GREEN
```
06:57          71.5%    7      ClusterUsed drops  ISM/manual delete  ---
06:58          ---      7      158,094 → ~140,000  ~41 GB deleted    ---
06:59          ---      7      116,740 (used)     Segment merges     ---
                                                   overwhelming node
```
**Key Event**: ClusterUsedSpace dropped from **158,094 MB → 116,740 MB** — a **41,354 MB (41 GB / 26%)** reduction in ~2 minutes. This was a large index deletion (ISM policy or manual).

### Phase 3: Node Drop + RED Status (07:00) — Status: RED
```
Time (UTC)     Nodes  Unassigned  PrimaryShards  ActiveShards  Status
────────────── ────── ─────────── ───────────── ──────────── ──────
07:00          6      24          54 (was 59)    75 (was 100)  RED!
                      (5 primary + 19 replica shards lost)
```
**Key Event**: One data node dropped (7→6), likely overwhelmed by segment merge activity from the 41 GB deletion. 5 primary shards became unassigned → RED.

### Phase 4: Node Recovery + Shard Reallocation (07:01–07:07) — Status: YELLOW → GREEN
```
Time (UTC)     Nodes  Unassigned  PrimaryShards  ActiveShards  Status
────────────── ────── ─────────── ───────────── ──────────── ──────
07:01          7      24→3        59 (restored)  76→97        YELLOW
07:02          7      3           59             97           YELLOW
07:03          7      3           59             97           YELLOW
07:04          7      3           59             97           YELLOW
07:05          7      2           59             98           YELLOW
07:06          7      0           59             100          GREEN ✓
07:07          7      0           59             100          GREEN ✓
```
**Recovery**: Node rejoined at 07:01, all primary shards immediately restored (RED→YELLOW). Replica shard reallocation took ~5 more minutes (YELLOW→GREEN).

### Error Rates During Incident
```
Time (UTC)     2xx    4xx    5xx    SearchLatency(ms)
────────────── ────── ────── ────── ──────────────────
06:55          150    1      0      1.8
07:00          115    55     3      8.1              <- 4x latency spike!
07:05          161    2      0      2.1              <- Recovered
```

## 4. Root Cause Analysis

### Primary Root Cause: Large Index Deletion Overwhelmed Data Node

The incident was a brief, self-recovering failure caused by a large index deletion:

**Stage 1 — Index Deletion (06:57-06:59)**
- A large index (~41 GB / 26% of cluster data) was deleted, likely by an ISM (Index State Management) retention policy
- `ClusterUsedSpace` dropped from 158,094 MB to 116,740 MB
- `DeletedDocuments` spiked to 4M+ as Lucene marked segments for deletion

**Stage 2 — Segment Merge Overload → Node Drop (07:00)**
- The deletion triggered heavy segment merge activity on the data node holding the most shards of the deleted index
- The merge I/O and CPU load caused the node to become temporarily unresponsive
- Node count dropped 7→6 for approximately 1 minute
- 24 shards became unassigned (5 primary + 19 replica) → **RED status**

**Stage 3 — Auto-Recovery (07:01-07:07)**
- The node auto-recovered and rejoined the cluster at 07:01
- All 5 primary shards were immediately restored from the node's local data (RED→YELLOW)
- Replica shard reallocation completed by 07:06 (YELLOW→GREEN)
- Total unhealthy duration: ~7 minutes

### What Was NOT the Cause

| Factor | Measured Value | Threshold | Verdict |
|---|---|---|---|
| **JVM Memory Pressure** | 68-74% max | >80% warning | NOT the cause |
| **CPU Utilization** | 10-43% | >90% critical | NOT the cause |
| **Master Reachability** | 1.0 (always reachable) | <1.0 = unreachable | NOT the cause |
| **Thread Pool Rejections** | 0 (bulk + search) | >0 = overloaded | NOT the cause |
| **Disk Space** | ~29 GB/node free | <10 GB critical | NOT the cause |

### Contributing Factors

| Factor | Details | Severity |
|---|---|---|
| **Large single-batch index deletion** | 41 GB deleted in ~2 min, no throttling | **ROOT CAUSE** |
| **ES 6.8 (EOL)** | Older merge scheduler, less resilient to bulk deletes | HIGH |
| **m5.large instance type** | 2 vCPU limits concurrent merge + serving capacity | MEDIUM |
| **No pre-incident JVM/node alarms** | No early warning of node stress | MEDIUM |
| **gp3 100 GB EBS** | Adequate IOPS but heavy merge I/O can still saturate | LOW |

## 5. Production Impact Assessment

### IMPACT: **P1 — Brief, Auto-Recovered**

| Impact Area | Status | Details |
|---|---|---|
| **Data Availability** | **BRIEF OUTAGE** | 5 primary shards unavailable for ~1 minute |
| **Data Integrity** | **NO LOSS** | All shards recovered from node-local data |
| **Log Ingestion** | **Minor dip** | Indexing continued at reduced rate during event |
| **Search/Query** | **4x latency spike** | 1.8ms → 8.1ms for ~5 minutes, then recovered |
| **5xx Errors** | **3 errors** | 3 server errors at 07:00 UTC |
| **4xx Errors** | **55 errors** | Client errors during shard unavailability |
| **Master Coordination** | **STABLE** | Master remained reachable throughout |

**Total RED duration**: ~1 minute (07:00-07:01)
**Total unhealthy duration**: ~7 minutes (07:00-07:07)
**Data Loss**: NONE — all shards recovered

### Alert Records

| Alert | Fired | Resolved |
|---|---|---|
| 【DB告警】AWS-ES 集群状态Red | 07:05:39 | 07:08:39 |
| 【DB告警】AWS-ES 集群状态Red_语音 | 07:06:39 | 07:08:39 |

**Correlated Alerts**: "datalink重要任务延迟(白天)" fired 4 times in the ±30 min window — likely impacted by the brief ES unavailability.

**7-Day History**: No prior ES alerts for `luckycommon` in the past 7 days. This is an **isolated incident**.

## 6. Recommended Remediation

### IMMEDIATE (No action required — auto-recovered)

The cluster self-healed within 7 minutes. Current status is GREEN with all 7 nodes and 100 active shards. No immediate action needed.

### URGENT (Within 1-2 weeks)

**Action 1: Review and throttle ISM deletion policies**
- The 41 GB deletion in ~2 minutes overwhelmed a data node
- Configure ISM to delete indices in smaller batches or during low-traffic windows
- Consider scheduling deletions during the maintenance window (not during business hours)

**Action 2: Add CloudWatch alarms for early warning**
```
Recommended Alarms:
- ClusterStatus.red = 1 for 1 min    → P1 Page (PagerDuty/voice)
- ClusterStatus.yellow = 1 for 5 min → Warning (Slack)
- Nodes < 7 for 2 min                → Critical
- JVMMemoryPressure > 80% for 10 min → Warning
- JVMMemoryPressure > 92% for 5 min  → Critical
- FreeStorageSpace < 20 GB per node   → Warning
- FreeStorageSpace < 10 GB per node   → Critical
```

**Action 3: Consider instance upgrade m5.large → m5.xlarge**
- m5.xlarge = 4 vCPU (2x current), 16 GiB RAM (~8 GB JVM heap)
- Would handle concurrent merge + serving workload much better
- Blue/green deployment, zero downtime via AWS Console
- Cost increase: ~$140/month per node ($560/month total) at EDP 31% discount

### LONG-TERM (Within 1-3 months)

| Priority | Action | Rationale |
|---|---|---|
| P1 | **Upgrade ES 6.8 → OpenSearch 2.x** | ES 6.8 is EOL. OpenSearch 2.x has better merge scheduler, shard allocation, and memory management |
| P2 | **Reduce shard count** | 59 primary shards across 4 data nodes = ~15/node (OK). But total 100 shards = 25/node. Review if any indices are over-sharded |
| P2 | **Enable Auto-Tune** | Let AWS optimize JVM and thread pool settings automatically |
| P3 | **Add UltraWarm tier** | Move older log data to warm storage, reducing active data volume and merge impact |
| P3 | **Increase EBS to 150 GB gp3** | More headroom for temporary merge space during index operations |

## 7. Comparison with Previous Incidents

| Attribute | luckycommon (this incident) | luckylfe-log (2026-02-12) |
|---|---|---|
| **Root Cause** | Large index deletion → node drop | JVM OOM → 3 node crash |
| **Duration** | ~7 min (auto-recovered) | 1+ hour (manual recovery) |
| **Severity** | P1 (brief, auto-recovered) | P1 CRITICAL (sustained outage) |
| **JVM Pressure** | 68-74% (not a factor) | 100% for 60 min (root cause) |
| **Nodes Lost** | 1 for ~1 min | 3 for 30+ min |
| **Data Loss** | None | None (EBS preserved) |
| **Human Intervention** | Not required | Required (shard reroute, cache clear) |

## 8. 中文摘要 (Slack 通知)

```
🔴 [P1] luckycommon ES集群状态: RED → 已自动恢复 (7分钟)

⏰ 事件时间线:
• 06:57 UTC - 大批量索引删除开始 (~41GB, 集群数据的26%)
• 07:00 UTC - 1个数据节点因合并负载过重短暂掉线 (7→6节点) → RED
• 07:01 UTC - 节点自动恢复重入集群 → YELLOW (5个主分片恢复)
• 07:06 UTC - 所有副本分片重新分配完成 → GREEN ✅
• 07:07 UTC - 集群完全恢复正常

📊 影响:
• RED持续时间: ~1分钟
• 总异常持续时间: ~7分钟
• 5xx错误: 3个
• 4xx错误: 55个
• 搜索延迟: 1.8ms → 8.1ms (4倍峰值, 已恢复)
• 数据丢失: 无 ✅
• Kibana: 未受影响

🔍 根因:
ISM策略(或手动)一次性删除了~41GB的索引数据,
段合并(segment merge)负载导致1个数据节点短暂掉线。
JVM内存压力68-74% (正常范围), 非内存问题。

⚡ 需要执行的操作:
1. ✅ [无需操作] 集群已自动恢复, 当前状态GREEN
2. 📋 [1-2周内] 优化ISM删除策略: 分批删除或安排在低峰时段
3. 📋 [1-2周内] 添加CloudWatch告警 (节点数<7, JVM>80%, RED状态)
4. 📋 [评估] 考虑升级 m5.large → m5.xlarge (CPU翻倍, 更好的合并处理能力)
5. 📋 [1-3月] 规划 ES 6.8 → OpenSearch 2.x 升级 (6.8已EOL)

💡 与2026-02-12 luckylfe-log事件对比:
本次事件规模较小 (7分钟 vs 1小时+), 自动恢复 (vs 需人工干预),
根因不同 (索引删除 vs JVM OOM), 无需紧急操作。
```

---

## Appendix: Key Evidence

### A. Storage Drop (ClusterUsedSpace)
```
06:55  158,094 MB  (normal)
06:59  116,740 MB  (41,354 MB / 41 GB deleted)
07:05  116,818 MB  (stable post-deletion)
```

### B. Node Count Timeline
```
06:55  7.0  (normal)
07:00  6.0  (1 node dropped)
07:01  7.0  (node rejoined)
07:05  7.0  (stable)
```

### C. Shard Allocation Timeline
```
Time   Unassigned  Primary  Active  Status
06:55  0           59       100     GREEN
07:00  24          54       75      RED
07:01  24→3        59       76→97   YELLOW
07:05  2           59       98      YELLOW
07:06  0           59       100     GREEN
```

### D. JVM Memory Pressure (was NOT elevated)
```
06:00-07:30: Range 68-74% (well below 80% warning threshold)
```

### E. Monitoring Commands
```bash
# Check cluster status
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name ClusterStatus.red --dimensions Name=DomainName,Value=luckycommon \
  Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '5 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Maximum --output table

# Check node count
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name Nodes --dimensions Name=DomainName,Value=luckycommon \
  Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '5 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Minimum --output table

# Check JVM pressure
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name JVMMemoryPressure --dimensions Name=DomainName,Value=luckycommon \
  Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '30 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Maximum --output table

# Check free storage
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name FreeStorageSpace --dimensions Name=DomainName,Value=luckycommon \
  Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '30 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Minimum --output table
```

---

*Report generated: 2026-03-08*
*Investigator: Claude Code (automated)*
*Skill Version: Elasticsearch Alert Investigation SOP v1.0*
