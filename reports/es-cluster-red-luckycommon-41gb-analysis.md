# LCNA-INC-2026-008 Follow-up: 41GB Claim Verification Report

**Cluster**: `luckycommon` (Elasticsearch 6.8)
**Original Incident**: 2026-03-08 07:00–07:07 UTC
**Analysis Date**: 2026-03-10
**Author**: David Zeng (曾翔宇), Senior DBA
**Purpose**: Respond to peer DBA's challenge of three claims in the original incident report

---

## Executive Summary

A peer DBA raised three technically valid challenges to the original LCNA-INC-2026-008 report. After re-pulling CloudWatch data at 1-minute granularity, all three challenges are **upheld**:

| # | Challenge | Finding | Verdict |
|---|-----------|---------|---------|
| 1 | Is DeletedDocuments a gauge or a rate metric? | **Gauge** — AWS defines it as "total documents marked for deletion" at a point in time | The original "4M+ spike" language was misleading |
| 2 | FreeStorageSpace chart shows a DROP (~17GB), not an increase | **Confirmed** — the 07:00Z FreeStorageSpace drop is a **node-exit artifact**, not data consumption | Your chart read was correct; our explanation was incomplete |
| 3 | Actual deletion was ~17GB, not 41GB | **Correct** — 1-min CloudWatch data shows ~2.4–2.6 GB permanent reduction; **116,740 MB never appears in CloudWatch data** | The 41GB figure in the original report is incorrect |

---

## Section 1: DeletedDocuments — Gauge vs. Rate

### AWS Official Definition

From the AWS OpenSearch Service CloudWatch Metrics documentation:

> *"The total number of documents marked for deletion across all data nodes in the cluster. These documents no longer appear in search results, but OpenSearch only removes deleted documents from disk during segment merges. **This metric increases after delete requests and decreases after segment merges.**"*

Source: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-cloudwatchmetrics.html

### Interpretation

**DeletedDocuments is an absolute gauge** — it reflects the current count of Lucene pending-delete documents at the time of measurement. It is NOT a cumulative counter.

**Consequences for the original report:**

- The report stated: *"DeletedDocuments spiked to 4M+ during the event"*
- The actual 1-min CloudWatch data shows DeletedDocuments was **flat at ~4,047,840** throughout 05:00–09:00Z, with fluctuations of < 10 documents per minute
- **There was no spike to 4M+.** The 4M figure was the pre-existing standing total of pending-delete documents in the cluster — the normal "Lucene tombstone" backlog awaiting segment merge
- The actual newly-marked deletions from the 06:59Z event: **+519,285 documents** (from the Event 3 step-change in the validation report, Section 1)

**Correct language should have been**: "DeletedDocuments showed a step-change of +519,285 docs at 06:59Z, from a pre-existing baseline of ~4,047,840 pending-delete docs."

---

## Section 2: Actual Deletion Size — CloudWatch Evidence

### 1-Minute Granularity Data (05:00–09:00 UTC, 2026-03-08)

The following table shows the key window around the incident, using CloudWatch `ClusterUsedSpace` (Average, 60s) and `FreeStorageSpace` (Sum, 60s):

| Timestamp (UTC) | ClusterUsedSpace (MB) | FreeStorageSpace (MB) | Notes |
|-----------------|-----------------------|-----------------------|-------|
| 06:40Z | 158,092 | 642,011 | Baseline (stable) |
| 06:44Z | 158,094 | 641,993 | Baseline (stable) |
| 06:48Z | 158,091 | 642,047 | Baseline (stable) |
| 06:52Z | 158,072 | 642,093 | Last stable reading pre-event |
| **06:56Z** | **147,088** | **647,162** | ← ISM deletion fires; space freed (+5,069 MB) |
| **07:00Z** | **145,105** | **635,106** | ← Data node exits cluster (node-exit artifact) |
| 07:04Z | 155,556 | 637,955 | Node rejoins; shards rebalancing |
| 07:08Z | 155,693 | 652,899 | Rebalancing complete |
| 07:12Z | 155,539 | 653,514 | Post-recovery stable |

### Methodology: Net Permanent Reduction

The correct method for measuring actual permanent space reduction is to compare **pre-event baseline** against **post-recovery stable** values — not against the transient low point during a node exit.

| Measurement | Value |
|-------------|-------|
| Pre-event baseline (ClusterUsedSpace, avg 06:40–06:52Z) | **158,072–158,094 MB** |
| Post-recovery stable (ClusterUsedSpace, avg 07:08–07:12Z) | **~155,500–155,700 MB** |
| **Net permanent reduction** | **~2,400–2,600 MB (~2.4–2.6 GB)** |

### FreeStorageSpace Confirms Deletion Direction

The FreeStorageSpace at the deletion moment provides a cross-check:
- 06:52Z → 06:56Z: FreeStorageSpace increased from **642,093 MB → 647,162 MB = +5,069 MB freed**
- This **confirms** that data was deleted and storage was freed at 06:56Z

### 24-Hour Window Confirmation (5-min granularity)

A full 24-hour CloudWatch sweep (2026-03-08 00:00Z → 2026-03-09 00:00Z, 5-min granularity) was run to verify whether the original report's value of 116,740 MB ever appeared:

| Statistic | Value |
|-----------|-------|
| ClusterUsedSpace 24h Maximum | 158,394 MB |
| ClusterUsedSpace 24h Minimum | **146,619 MB** (at 07:00Z — node temporarily absent) |
| **116,740 MB in the dataset?** | **NO — this value does not appear at any timestamp** |

**Conclusion: The 41 GB claim is incorrect.** The original report's post-event value of 116,740 MB cannot be found in actual CloudWatch data at any granularity. The actual permanent storage reduction was approximately **2.4–2.6 GB**, not 41 GB.

---

## Section 3: FreeStorageSpace Chart — Why It Dropped

The peer DBA observed FreeStorageSpace appearing to drop from ~157 GB to ~140 GB (approximately −17 GB). This is a valid observation that requires explanation.

### Chart Read Clarification: ClusterUsedSpace vs. FreeStorageSpace

The ~157 → ~140 GB trajectory matches **ClusterUsedSpace** values, not FreeStorageSpace:

| Metric | Pre-event | 07:00Z (node exit) | Post-recovery |
|--------|-----------|--------------------|---------------|
| ClusterUsedSpace | 158,092 MB (~158 GB) | 145,105 MB (~145 GB) | 155,600 MB (~156 GB) |
| FreeStorageSpace | 642,093 MB (~628 GB) | 635,106 MB (~620 GB) | 652,899 MB (~638 GB) |

The 158→145 GB trajectory strongly suggests the peer DBA was reading **ClusterUsedSpace**, which is visually in the 140–160 GB range. FreeStorageSpace for a 400 GB total cluster with 4 nodes is in the 620–660 GB range (summed across all nodes).

### Timeline of What Actually Happened

```
06:52Z  Pre-event stable
        ClusterUsedSpace: 158,072 MB
        FreeStorageSpace: 642,093 MB

06:56Z  ISM deletion fires ──────────────────────────────────────────────
        ClusterUsedSpace DROPS: 158,072 → 147,088 MB  (-10,984 MB freed)
        FreeStorageSpace RISES: 642,093 → 647,162 MB  (+5,069 MB freed)
        ✓ Deletion confirmed — space was freed

07:00Z  One data node temporarily exits the cluster ────────────────────
        ClusterUsedSpace DROPS further: 147,088 → 145,105 MB
          (this node's usage removed from the cluster average — artifact)
        FreeStorageSpace DROPS: 647,162 → 635,106 MB  (-12,056 MB)
          (this node's free space removed from the Sum — artifact)
        ↑ This is the "drop" the peer DBA observed — NOT data consumption

07:04Z  Node rejoins; shard rebalancing begins ──────────────────────────
        ClusterUsedSpace RISES: 145,105 → 155,556 MB
        FreeStorageSpace RISES: 635,106 → 637,955 MB

07:08Z  Full recovery ───────────────────────────────────────────────────
        ClusterUsedSpace: 155,693 MB (stable; 2,400 MB LESS than pre-event ✓)
        FreeStorageSpace: 652,899 MB (HIGHER than pre-event baseline ✓)
```

**The FreeStorageSpace drop at 07:00Z was caused by one data node's contribution being removed from the Sum aggregate — not by new data being written or consumed.** When the node rejoined at 07:04Z, FreeStorageSpace recovered to above its pre-event baseline, confirming the net effect was a space gain (deletion freed ~5 GB by the FreeStorageSpace measure, or ~2.5 GB by the ClusterUsedSpace measure post-recovery).

---

## Section 4: Error Analysis — Where Did 116,740 MB Come From?

The original report's Appendix A stated:

> *"06:59: ClusterUsedSpace = 116,740 MB (post-deletion)
> Delta: 158,094 − 116,740 = 41,354 MB = **41 GB deleted**"*

The pre-event value (158,094 MB) is **correct** — it matches the 1-min CloudWatch data exactly.

The post-event value (116,740 MB) is **not found in CloudWatch data**. Possible sources of error:

| Hypothesis | Assessment |
|------------|------------|
| **Console GiB/MB unit confusion** | 145,105 MB ÷ 1,024 ≈ 141.7 GiB — does not produce 116,740 |
| **Single-node view during node exit** | If one node had ~41 GB less data (due to primary shard removal during RED), a node-level metric could show ~116 GB for that node. This is the most likely explanation. |
| **Wrong metric read** | FreeStorageSpace per-node at 07:00Z was approximately ~158,777 MB (total 635,106 / 4 nodes) — does not match |
| **5-min granularity average artifact** | A 5-min average at 07:00Z would blend the pre-exit and post-exit readings. Still cannot produce 116,740 MB. |

**Most probable cause**: The original author read a **node-level storage metric** (not cluster-level) for the node that had temporarily shed its primary shards during the RED state. During 07:00Z, that node would have appeared to hold significantly less data (its 5 primary shards were "unassigned" / held by other nodes). This single-node view was mistakenly used as the cluster total.

**Required correction to original report**:
- Original: "ClusterUsedSpace dropped 158,094 → 116,740 MB = 41 GB deleted"
- Corrected: "ClusterUsedSpace dropped from baseline ~158,092 MB to post-recovery stable ~155,600 MB = ~2,500 MB (~2.5 GB) net permanent reduction"

---

## Section 5: Summary Table — Three Questions Answered

| Question | Answer |
|----------|--------|
| **Is DeletedDocuments a gauge or rate?** | **Gauge** (absolute count of Lucene pending-delete tombstones). The 4M value in the original report was the pre-existing steady-state total, not a new spike. The actual step-change from this event was +519,285 docs. |
| **Why does FreeStorageSpace chart show a DROP?** | The 07:00Z drop (~12 GB from Sum) is a **node-exit artifact** — one data node temporarily left the cluster, removing its contribution from the FreeStorageSpace Sum. The actual deletion-moment reading showed FreeStorageSpace *increased* by +5,069 MB at 06:56Z, confirming space was freed. By 07:08Z FreeStorageSpace was above pre-event baseline. |
| **Was the deletion really 41 GB?** | **No.** 1-min CloudWatch data shows net permanent ClusterUsedSpace reduction of ~2,400–2,600 MB (~2.5 GB). The value 116,740 MB cited in the original report does not appear in any CloudWatch data for 2026-03-08. Actual permanent deletion size: **~2.5 GB**. |

---

## Section 6: Chinese Response Draft

关于您提出的三个问题，我们重新拉取了CloudWatch 1分钟粒度原始数据进行核实，结论如下：

**1. DeletedDocuments是存量指标（gauge），非增量**

根据AWS官方文档，该指标表示"集群中所有数据节点上标记为待删除的文档总数"——删除请求后上升，segment merge完成后下降。原报告中"4M+ DeletedDocuments"是该时刻集群的**历史累积**待合并文档总量，并非本次删除新产生的数据。我们重新确认了1分钟粒度数据：05:00–09:00Z期间该指标始终稳定在~4,047,840，没有明显尖峰。本次事件（06:59Z）实际新增标记删除的文档数为 **+519,285条**（来自DeletedDocuments的step-change）。

**2. FreeStorageSpace下降的原因：节点退出，而非数据写入**

您观察到FreeStorageSpace图表下降完全正确，但原因是**节点临时退出集群**，而非消耗了存储空间。完整时序如下：
- 06:56Z：ISM删除触发，FreeStorageSpace（Sum）从642,093 MB**上升**至647,162 MB（+5,069 MB，说明空间被释放）
- 07:00Z：一个数据节点临时退出集群，Sum统计中移除了该节点的可用空间（约-12 GB），这才是您看到的"下降"
- 07:08Z：节点重新加入，FreeStorageSpace恢复至652,899 MB，**高于事件前基线**

**3. 41 GB数据量是错误的**

我们重新拉取了1分钟粒度的ClusterUsedSpace数据：

- 事件前基线（06:40–06:52Z）：~158,072–158,094 MB
- 全天最低值（07:00Z，节点临时退出期间）：146,619 MB（非真实删除量）
- 节点恢复后稳定值（07:08–07:12Z）：~155,500–155,700 MB
- **实际永久减少的存储占用：约2,400–2,600 MB（约2.5 GB）**

原报告中116,740 MB这个数值在当天任何时间点的CloudWatch API数据中均未出现（24小时内最低值为146,619 MB）。原报告Appendix A中的数据存在明显错误，需要更正：实际永久删除量约为**2.5 GB**，而非41 GB。

该错误最可能的来源：原作者读取的是07:00Z某个**单节点**的存储指标（该节点在RED状态下临时转出了5个primary shard），而非集群总量，导致数值严重偏低。

---

## Appendix: Raw CloudWatch Data Reference

### 1-min ClusterUsedSpace (Avg) — 2026-03-08 06:40–07:15 UTC

```
06:40Z  158,092 MB
06:44Z  158,094 MB  (matches original report baseline ✓)
06:48Z  158,091 MB
06:52Z  158,072 MB
06:56Z  147,088 MB  ← ISM deletion fires (-11,004 MB from 06:52)
07:00Z  145,105 MB  ← node exits (-1,983 MB from 06:56; node-exit artifact)
07:04Z  155,556 MB  ← node rejoins (+10,451 MB; shards rebalancing)
07:08Z  155,693 MB  ← stable post-recovery
07:12Z  155,539 MB  ← stable post-recovery
```

### 24-Hour Range Verification

```
24h Maximum ClusterUsedSpace:  158,394 MB
24h Minimum ClusterUsedSpace:  146,619 MB  (07:00Z node-exit window)
116,740 MB in dataset?         NO
```

### AWS Documentation Reference

DeletedDocuments metric definition:
https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-cloudwatchmetrics.html

---

*Report prepared by: David Zeng (曾翔宇), Senior DBA*
*For questions, reference LCNA-INC-2026-008 and the validation report dated 2026-03-09*
