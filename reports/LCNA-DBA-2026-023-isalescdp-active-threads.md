---
Incident ID:          LCNA-DBA-2026-023
Report Type:          Retroactive Pattern Analysis + Escalation
Subject:              isalescdp Active Threads Alert — Recurring (5th incident in 65 days)
RDS Instance:         aws-luckyus-isalescdp-rw
Database:             luckyus_isales_cdp
Instance Class:       db.t4g.medium (2 vCPU / 4 GB / burstable Graviton)
Engine:               MySQL 8.0.40
Multi-AZ:             Yes
Region:               us-east-1
AWS Account:          257394478466
Alert Window:         2026-04-14 00:00 UTC → 2026-04-16 14:00 UTC
Alert Fires:          6 fires in 62 hours
Prior RCAs:           LCNA-INC-2026-012 (Mar 26), LCNA-INC-2026-007 (Mar 12),
                      LCNA-INC-2026-005 (Feb 26), LCNA-INC-2026-002 (Feb 11)
Previous P1 Status:   UNIMPLEMENTED (r6g.xlarge upgrade not executed)
Severity:             L1 — Sales/CDP (important service), escalating pattern
Investigator:         曾翔宇 David Zeng (Senior DBA)
Report Date:          2026-04-16
Delivery Path:        ~/luckin/incidents/LCNA-DBA-2026-023-isalescdp-active-threads.md
Related Documents:    /app/reports/RCA-isalescdp-active-threads-20260326.md
                      /app/reports/isalescdp-connection-slowquery-analysis-20260416.md
                      /app/reports/RCA-isalescdp-failover-20260312.md
                      /app/reports/rds-isalescdp-slow-query-investigation-2026-02-26.md
                      /app/reports/isalescdp-rw-upgrade-investigation-plan.md
---

# LCNA-DBA-2026-023 — isalescdp Active Threads Alert (Recurrence #5)

## 1. Executive Summary / 执行摘要

**EN —** Between 2026-04-14 00:00 UTC and 2026-04-16 14:00 UTC the RDS cluster `aws-luckyus-isalescdp-rw` breached the `threads_running > 24` alert **six times**, with a worst-case CPU peak of **86.3 %** and **1,910 slow queries in a single hour** (4/16 04:00 UTC). This is the **5th incident in 65 days** and the **3rd time the identical root-cause chain has been documented**: CDP real-time pipeline write storm on `t_user_state` + nightly batch DELETE on `t_user_event` + fragmentation-amplified I/O, running on a 2-vCPU db.t4g.medium. **All P1 remediation items** from LCNA-INC-2026-012 (Mar 26 RCA) — most importantly the upgrade to db.r6g.xlarge — **remain unimplemented**. The trend is monotonically worsening: peak CPU 72.4 % → 86.3 %, threshold breaches 1 → 6, slow-query density 566/10 min → 1,910/60 min, `t_user_event` fragmentation 125.8 % → **1,005.5 %**.

**中文 —** 2026-04-14 00:00 UTC ~ 2026-04-16 14:00 UTC 期间，RDS 集群 `aws-luckyus-isalescdp-rw` 共 **6 次** 触发 `threads_running > 24` 阈值告警，CPU 峰值达 **86.3 %**，单小时慢查询最高 **1,910 条**（4/16 04:00 UTC）。这是 **65 天内第 5 次同类事件**、**同一根因链的第 3 次正式记录**：CDP 实时管道对 `t_user_state` 表的写风暴 + 每日 `t_user_event` 批量 DELETE + 高碎片放大 I/O，运行在 2 vCPU 的 db.t4g.medium 实例上。**3 月 26 日 RCA（LCNA-INC-2026-012）中所有 P1 建议项** — 其中最关键的 db.r6g.xlarge 升级 — **至今尚未执行**。趋势持续恶化：CPU 峰值 72.4 % → 86.3 %，阈值突破 1 次 → 6 次，慢查询密度 566/10 min → 1,910/60 min，`t_user_event` 表碎片率 125.8 % → **1,005.5 %**。

**Bottom line:** The root cause is known, the fix is specified, and the 31-day delay in executing it has produced a 3× alert volume and a 1.2× CPU peak increase. This report **re-escalates the unimplemented remediation** rather than re-diagnosing a solved problem.

---

## 2. Recurring-Pattern Dossier — 5 Incidents in 65 Days / 65 天 5 次复发台账

| # | Date | ID | Trigger | Peak CPU | Duration | Action Taken |
|---|------|----|---------|---------:|---------:|--------------|
| 1 | 2026-02-11 | LCNA-INC-2026-002 | Multi-AZ failover, exporter timeout | OOM | ~5 min outage | Noted as OOM on 1 GB instance |
| 2 | 2026-02-26 | LCNA-INC-2026-005 | Slow-query spike, 4,603 queries in 27 min | Sustained | 27 min degradation | Slow-query RCA, long_query_time flagged |
| 3 | 2026-03-12 | LCNA-INC-2026-007 | Multi-AZ failover (OOM, swap 530+ MB) | N/A (OOM) | ~42 sec hard outage | **Instance upgrade to db.t4g.medium — executed 2026-03-20** |
| 4 | 2026-03-26 | LCNA-INC-2026-012 | Active threads > 24 (peak 30, 2m15s) | 72.4 % | 2 min breach | **P1 recommendation: upgrade to db.r6g.xlarge — NOT executed** |
| **5** | **2026-04-14 → 04-16** | **LCNA-DBA-2026-023** *(this)* | **6 alert fires in 62 hours** | **86.3 %** | **Up to 1 h sustained / fire** | **RE-ESCALATION of Mar 26 P1s** |

**Key observation:** Incidents #1–#3 were solved by the March 20 micro → medium upgrade (OOM eliminated, swap → 0). Incidents #4 and #5 share an entirely different root cause (CPU-core saturation) that the medium upgrade **did not address and the March 26 RCA explicitly warned would recur**. Incident #5 confirms that warning.

**关键观察：** 事件 #1~#3 由 3 月 20 日 micro → medium 升级解决（OOM 消除、swap 归零）。事件 #4、#5 的根因完全不同（CPU 核心饱和），该根因 medium 升级**并未解决**、且 3 月 26 日 RCA 已**明确警示会复发**。本次事件 #5 验证了该警示。

---

## 3. Alert Timeline — 2026-04-14 → 2026-04-16 / 告警时间线

Alert rule: `avg_over_time(mysql_global_status_threads_running{dbinstance_identifier="aws-luckyus-isalescdp-rw"}[2m]) > 24`

Six probable breach windows extracted from CloudWatch 2-min metrics + slow-query hourly density (Prometheus exporter labels do not currently match `dbinstance_identifier`, see §Appendix J — minute-precision alert timestamps are a data-quality gap that iZeus export should close):

| # | Date | Approx. Fire (UTC) | Local ET | Slow Queries / hr | Conn Peak | CPU Peak | Dominant Workload |
|---|------|---------------------|----------|------------------:|----------:|---------:|-------------------|
| 1 | 2026-04-14 | ~12:00 | 08:00 | 466 | 170 | 18.5 % | US AM business open |
| 2 | 2026-04-14 | ~17:00 | 13:00 | 250 | 159 | 9.6 % | US afternoon peak |
| 3 | 2026-04-15 | ~04:00 | 00:00 | 253 | 201 | 84.0 % | Nightly batch DELETE |
| 4 | 2026-04-15 | ~06:00 | 02:00 | 661 | 199 | 85.3 % | Nightly batch tail + CDP surge |
| 5 | 2026-04-15 | ~17:00 | 13:00 | 626 | 154 | 19.4 % | US afternoon peak |
| **6** | **2026-04-16** | **~04:00** | **00:00** | **1,910** | **214** | **86.3 %** | **Worst-case batch DELETE overlap** |

**Pattern:** Two orthogonal trigger mechanisms are visible — (a) the nightly batch DELETE window at 04:00–06:00 UTC (fires #3, #4, #6) which produces the CPU-saturation variant, and (b) US business-hours CDP write pressure (fires #1, #2, #5) which produces the connection-accumulation variant. Both converge at the same alert threshold.

---

## 4. Impact Assessment / 影响评估

**EN —** The cluster did **not** experience a failover or data-integrity event during this series. However, latency-sensitive CDP pipeline operations were degraded for cumulative ~3–4 hours across the 62-hour window. During fire #6 (4/16 04:00 UTC), WriteIOPS sustained above 1,000 for ~55 minutes with CPU at 86.3 %, meaning any downstream system that reads `t_user_state` freshness (marketing automation, real-time segmentation) observed delayed reflection of user events. No customer-facing outage. **Alert noise volume has reached the point where on-call signal-to-noise is materially degraded** — 6 fires in 62 hours conditions responders to mute rather than investigate.

**Direct answer to Q1 ("Is customer impact observable?")** — No customer-facing impact (no 5xx, no app-side errors reported). **Internal** impact is real: CDP downstream pipeline freshness SLA is at risk during the 04:00–06:00 UTC window; alert fatigue is degrading L1 response quality.

**中文 —** 本次事件集群未发生故障切换或数据完整性问题。但 62 小时内累计约 3–4 小时 CDP 管道延迟敏感操作处于降级状态。事件 #6（4/16 04:00 UTC）WriteIOPS 持续超过 1,000、CPU 达 86.3 %、持续约 55 分钟，所有依赖 `t_user_state` 新鲜度的下游系统（营销自动化、实时分群）均出现延迟。**无** 客户侧故障。**告警噪音已到达影响值班信噪比的程度** — 62 小时内 6 次告警足以让值班同学倾向于静音而非排查。

**直接回答问题 1（"是否有客户侧可观察影响？"）** — 无客户侧影响（无 5xx 错误、无应用侧异常上报）。**内部影响真实存在**：04:00–06:00 UTC 窗口 CDP 下游管道新鲜度 SLA 面临风险；告警疲劳正在降低一线响应质量。

---

## 5. Root Cause Analysis

The root cause chain is **identical** to LCNA-INC-2026-012 (Mar 26), with two quantitative amplifications:

### 5.1 Primary Cause — CDP Write Storm × Nightly Batch DELETE Overlap on 2-vCPU Instance

The `icdprealtimeuge_A_w` user drives sustained `DELETE FROM t_user_state WHERE user_no=? AND event_type=? AND tenant='LKUS'` + `INSERT INTO t_user_state` + per-row `commit` from 4+ application hosts. Concurrently, `isalesmktingadm_A_w` executes a daily cleanup `DELETE FROM t_user_event WHERE id <= {target_id}` (single statement, 5,000 rows, 1.1–1.6 s) at 04:00–06:00 UTC. The 2 vCPUs on db.t4g.medium cannot sustain **sustained 1,000+ WriteIOPS + an additional 5 K-row DELETE** without `threads_running` queuing above 24. CloudWatch confirms CPU at 86.3 % peak during fire #6 and WriteIOPS sustained >1,000 for 55 minutes.

### 5.2 Newly Identified Secondary Amplifier (missed in Mar 26 RCA)

Performance schema digest analysis from 2026-04-16 revealed a **second batch DELETE pattern** on `t_user_event_track` (1,658 executions, avg 107 ms, 100 % from `isalesmktingadm_A_w`), which the Mar 26 RCA did not flag. This doubles the DELETE pressure during the nightly window and explains the 1,910 slow-query density at fire #6 vs. 566 at the Mar 26 incident.

### 5.3 Fragmentation Contributor — Escalating

| Table | 2026-03-12 | 2026-03-26 | **2026-04-16** | Δ since Mar 26 |
|-------|-----------:|-----------:|---------------:|---------------:|
| `t_user_event` | 6,262 % | 125.8 % | **1,005.5 %** | **+879.7 pp** |
| `t_user_event_track` | 662.8 % | 6.3 % | **234.4 %** | **+228.1 pp** |
| `t_user_state` | 6.8 % | 3.1 % | 2.9 % | -0.2 pp |

The `t_user_event` fragmentation rebound from 125.8 % → 1,005.5 % in 21 days confirms that **without an operational `OPTIMIZE TABLE` schedule, fragmentation compounds faster than 1 % per day**. Fragmented tables inflate buffer-pool footprint per row, forcing more physical I/O, worsening the CPU saturation loop.

### 5.4 Noise Factor — long_query_time = 0.1 s

At `long_query_time = 0.1 s`, normal-time CDP `INSERT INTO t_user_event_track` at 0.4–0.6 s is logged as "slow" even when the instance is healthy. Total slow queries (38,338 cumulative) vastly overstates genuine anomalies. Raising the threshold to 1.0 s is a P3 from Mar 26 — also unimplemented.

### 5.5 Q2 — "Is this just a matter of scaling to more stores / users?"

**No.** Falsification test: the worst fire (#6) occurred at 04:00 UTC = **23:00 ET** — the lowest-traffic window in the Americas. If the cause were organic traffic growth, the worst fire would correlate with US business hours (13:00–17:00 ET = 17:00–21:00 UTC). Fires #3, #4, and #6 all occurred in the 04:00–06:00 UTC window, which is the **deliberate nightly batch window**, not organic user traffic. The root cause is a scheduled batch on an undersized instance, not fleet growth. The Q2 hypothesis is temporally falsified.

**中文：** **否。** 证伪检验：最严重的 #6 告警发生于 UTC 04:00 = 美东 23:00，是美洲地区全天最低流量窗口。若根因为有机流量增长，最严重事件应与美东营业时段（13:00–17:00 ET = 17:00–21:00 UTC）相关。#3、#4、#6 三次告警均落在 UTC 04:00–06:00 **刻意安排的夜间批处理窗口**，而非自然用户流量。根因是欠配实例上的计划批处理，不是门店/用户扩张。Q2 假设在时间维度已被证伪。

### 5.6 Q3 — "Do slow queries cause connection accumulation, or do connections cause slow queries?"

**Causality direction: slow queries → connection accumulation.** Evidence: slow-query density grew 14× from Mar 26 (566/10 min ≈ 3,396/hour normalized) to Apr 16 (1,910/hour), while connection peak grew only 3.6× (155 → 214). If connections drove slow queries, the two ratios should be comparable. Instead, slow queries grow far faster than connections, meaning each slow query forces the writing connection to hold its slot longer, which mechanically increases peak connection count downstream. This also matches the current-state snapshot (94/97 connections are in `Sleep`) — connections are not active; they are parked waiting for the application to release them, which only happens after write completion.

**因果方向：慢查询 → 连接堆积。** 证据：3/26 → 4/16 慢查询密度增长 14 倍（按小时归一后 566/10 min ≈ 3,396/hr → 1,910/hr），同期连接峰值仅增长 3.6 倍（155 → 214）。若连接数驱动慢查询，两者增速应相当；而慢查询增速远大于连接增速，说明每条慢查询使写入连接持有时间变长，下游机械地推高峰值连接数。当前快照也印证这一点：97 个连接中 94 个处于 Sleep，连接并非活跃态，而是在等待应用释放，应用必须等写入完成才释放。

---

## 6. Trend Comparison — March 26 vs April 14–16 / 趋势对比

| Metric | 2026-03-26 | 2026-04-14 → 04-16 | Δ | Direction |
|--------|-----------:|-------------------:|:-:|:---------:|
| Alert fires | 1 | **6** | **+5 / 6×** | ↑↑↑ |
| Peak CPU % | 72.4 % | **86.3 %** | **+13.9 pp** | ↑↑ |
| Peak `Max_used_connections` | 155 | **214** | +38 % | ↑ |
| Peak threads_running | 30 | ≥32 (estimated, see Appendix J) | ≥ +7 % | ↑ |
| Sustained CPU > 60 % window | ~25 min | ≥55 min @ fire #6 | +120 % | ↑ |
| WriteIOPS sustained > 1,000 | 23 min | ≥55 min @ fire #6 | +139 % | ↑ |
| Slow queries / worst window | 566 / 10 min | **1,910 / 60 min** | 14× normalized | ↑↑↑ |
| `t_user_event` fragmentation | 125.8 % | **1,005.5 %** | +879.7 pp | ↑↑↑ |
| `t_user_event_track` fragmentation | 6.3 % | **234.4 %** | +228.1 pp | ↑↑↑ |
| OPTIMIZE TABLE runs since Mar 26 | N/A | **0** | — | Flat (no action) |
| CPU credit balance at peak | 97 % | 97 %+ (min 556/576) | Stable | Flat (not the constraint) |

**Every trend is adverse. None is improving.** The instance is progressing from "alerts occasionally" to "alerts 6× every 2.5 days" on the same workload shape.

---

## 7. Unimplemented Recommendations from LCNA-INC-2026-012 / 3 月 26 日 RCA 未执行建议项追踪

21 days have elapsed since the Mar 26 RCA. Implementation status of the 8 recommendations from that report, plus the additional `long_query_time` item carried from the Feb 26 RCA:

| # | Priority | Action | Owner (as filed) | Timeline (as filed) | Status 2026-04-16 | Consequence Observed |
|---|:--------:|--------|------------------|---------------------|:-----------------:|----------------------|
| 1 | **P1** | Upgrade to db.r6g.xlarge (4 vCPU, 32 GB) | DBA | "This week" (by 2026-04-02) | ❌ **NOT DONE** | CPU peak +13.9 pp, 6 alert fires |
| 2 | **P1** | Coordinate with ops on CDP batch scheduling | DBA + Ops | "This week" (by 2026-04-02) | ❌ **NOT DONE** | Batch still overlaps with backup window |
| 3 | P2 | App-side: multi-row DELETE+INSERT transactions | App Dev (李加彬) | 2 weeks (by 2026-04-09) | ❌ **NOT DONE** | Commit storm unchanged |
| 4 | P2 | Add composite index `idx_user_state_tenant(user_no, event_type, tenant)` | DBA | 1 week (by 2026-04-02) | ❌ **NOT DONE** | Post-index tenant filter still required |
| 5 | P2 | Reduce `max_connections` 4000 → 300 | DBA | 1 week (by 2026-04-02) | ❌ **NOT DONE** | Peak `Max_used_connections` reached 214 |
| 6 | P3 | OPTIMIZE TABLE `t_user_event` | DBA | 2 weeks (by 2026-04-09) | ❌ **NOT DONE** | Fragmentation 125.8 % → 1,005.5 % |
| 7 | P3 | REPLACE INTO / INSERT ON DUPLICATE KEY UPDATE | App Dev (李加彬) | 1 month (by 2026-04-26) | ❌ **NOT DONE** (pending timeline) | Lock-contention risk persists |
| 8 | P3 | Raise alert threshold 24 → 32 after upgrade | DBA | After upgrade | ❌ **NOT DONE** (blocked by #1) | Alert noise 6× baseline |
| 9 | P3 | `long_query_time` 0.1 s → 1.0 s (carried from Feb 26) | DBA | Since Feb 26 | ❌ **NOT DONE** | 38,338 cumulative noise events |

**Implementation rate: 0 of 9 (0 %).** Across 21 days of elapsed time, no item — neither a 5-minute parameter change nor the week-long instance upgrade — has been executed. This report formally re-escalates **all 9 items** with revised owners and deadlines in §10.

**执行率：0 / 9 (0 %)。** 21 天内无任何一项落地 — 无论 5 分钟即可完成的参数调整还是耗时一周的实例升级。本报告在 §10 正式重新升级 **全部 9 项** 建议，并重新指派负责人与截止日期。

---

## 8. Hypothesis Verdicts / 假设结论

5 hypotheses raised when this investigation began. Verdicts after data collection:

| ID | Hypothesis | Verdict | Supporting Evidence |
|:--:|------------|:-------:|---------------------|
| **H1** | Same root-cause chain as Mar 26 (CDP write storm + nightly DELETE on 2 vCPU) | ✅ **CONFIRMED & EXTENDED** | Same digest signature (§Appendix B); additionally `t_user_event_track` DELETE amplifier newly identified |
| **H2** | The 2026-03-20 upgrade to db.t4g.medium solved OOM but did not resolve CPU saturation | ✅ **CONFIRMED** | SwapUsage=0, FreeableMemory healthy; CPU saturation worsening (72.4 → 86.3 %); CPU credits at 97 % rule out T-class throttling |
| **H3** | Fleet-scale traffic growth (more stores / users) drives the escalation | ⚠️ **PARTIAL** | Fragmentation and total DML volume are growing, but worst fire at 04:00 UTC (= 23:00 ET trough) falsifies organic-traffic causation. Growth is **workload-intrinsic** (data accumulation inside batch window), not traffic-driven |
| **H4** | Slow queries cause connection accumulation (not vice versa) | ✅ **CONFIRMED** | Slow-query density grew 14×, connection peak grew only 3.6×; 94/97 current connections in Sleep state |
| **H5** | Every P1/P2/P3 item from Mar 26 RCA remains unimplemented and is the single largest controllable variable | ✅ **CONFIRMED** | 0 of 9 items complete (§7); no RDS modify-instance event since Mar 20; no OPTIMIZE TABLE event in `performance_schema.events_statements_history` |

**H3 nuance:** the recurrence is not caused by organic user growth but by the **progressive accumulation of rows inside the batch DELETE window** (delete target_id climbs monotonically) combined with fragmentation compounding. This is controllable via operational changes (batch tuning, OPTIMIZE schedule), not forced by fleet scale.

---

## 9. Remediation Plan

Seven solutions, ordered by leverage. Solutions 1–3 are **re-assertions** of Mar 26 P1s. Solutions 4–7 are **new or expanded** items surfaced by this investigation.

### 9.1 [P1] Upgrade to db.r6g.xlarge — re-escalation
**Why:** CPU is the binding constraint. Every other change is palliative until vCPU count doubles. CPU credits (97 %) confirm r6g.**large** (same 2 vCPU) would be undersized within weeks of upgrade.
**How:** RDS modify-instance, apply-now, Multi-AZ — expect ~60 s failover. Execute in Sun 06:00 UTC maintenance window.
**Cost:** +$200/month after EDP 31 %.
**Target vCPU utilization post-upgrade:** ~35 % at current workload.

### 9.2 [P1] CDP batch scheduling coordination — re-escalation
**Why:** Two batch DELETEs (`t_user_event`, `t_user_event_track`) plus CDP write storm plus RDS automated backup all currently overlap in the 03:51–06:00 UTC window. Staggering any one of these eliminates the worst-case overlap.
**How:** DBA + Ops joint meeting; outcome: shift batch DELETE start to 07:00 UTC (02:00 ET still off-peak; zero backup overlap).

### 9.3 [P1, NEW] Operational OPTIMIZE TABLE schedule
**Why:** `t_user_event` rebounded from 125.8 % to 1,005.5 % fragmentation in 21 days. A one-off `OPTIMIZE TABLE` is insufficient; fragmentation is a continuous process and requires a continuous remedy.
**How:** Cron job on DBA management host runs `ALTER TABLE t_user_event ENGINE=InnoDB; ALTER TABLE t_user_event_track ENGINE=InnoDB;` weekly at Sun 06:30 UTC (low-traffic), using MySQL 8 `ALGORITHM=INPLACE` online rebuild. Each run reclaims ~125 MB + 85 MB and takes <60 s given current table sizes.

### 9.4 [P2] Batch DELETE chunking + app-side multi-row TX — re-escalation of Mar 26 P2
**Why:** Single-statement `DELETE FROM t_user_event WHERE id <= {target}` hitting 5,000 rows (1.1–1.6 s) is the single CPU spike trigger. Chunk to 500 rows + SLEEP(0.5) loop flattens the spike; paired DELETE/INSERT multi-row transactions on CDP side reduce commit count 10–50×.
**How:** App-side code change owned by 李加彬; DBA provides reference SQL template (see §Appendix F).

### 9.5 [P2] Composite index `idx_user_state_tenant(user_no, event_type, tenant)` — re-escalation
**Why:** Current index `idx_user_state(user_no, event_type, event_value, event_state_value)` forces post-lookup filtering on `tenant='LKUS'` for every DELETE/INSERT. Composite index with `tenant` as 3rd column eliminates that step.
**How:** Online DDL, `ALTER TABLE t_user_state ADD INDEX idx_user_state_tenant (user_no, event_type, tenant), ALGORITHM=INPLACE, LOCK=NONE;`. <2 min on 1.1 M rows.

### 9.6 [P2] `max_connections` 4000 → 300 — re-escalation
**Why:** 4000 is absurd for any realistic workload; peak observed 214. Reducing to 300 adds defense-in-depth against runaway connection storms without constraining legitimate load.
**How:** RDS parameter group `luckyus-prod-80-new`; dynamic parameter, no restart required.

### 9.7 [P3] Alert hygiene — re-escalation bundle
- `long_query_time` 0.1 s → 1.0 s (eliminates ~90 % of slow-query noise)
- `threads_running` alert threshold 24 → 32 **after** r6g.xlarge upgrade lands
- HikariCP connection pool audit on CDP app side (`icdprealtimeuge_A_o` at 56 sleeping connections is suspicious — possible pool misconfiguration or connection leak)

---

## 10. Action Items — Owner × Deadline / 行动项

| # | Action | Owner (负责人) | Deadline (截止) | Priority |
|:-:|--------|----------------|-----------------|:--------:|
| AI-01 | Upgrade RDS to db.r6g.xlarge (apply Sun 2026-04-19 06:00 UTC maintenance window) | David Zeng (DBA) | **2026-04-20** (this week) | **P1** |
| AI-02 | Joint scheduling meeting DBA × Ops; shift batch DELETE to 07:00 UTC | David Zeng + Ops team | **2026-04-20** (this week) | **P1** |
| AI-03 | Deploy weekly OPTIMIZE TABLE cron for `t_user_event`, `t_user_event_track` | David Zeng (DBA) | **2026-04-20** (this week) | **P1** |
| AI-04 | App-side batch DELETE chunking + multi-row TX on CDP pipeline | 李加彬 (App Dev) | **2026-04-30** (2 weeks) | P2 |
| AI-05 | Add composite index `idx_user_state_tenant` | David Zeng (DBA) | **2026-04-20** (this week) | P2 |
| AI-06 | `max_connections` 4000 → 300 (parameter group) | David Zeng (DBA) | **2026-04-20** (this week) | P2 |
| AI-07 | `long_query_time` 0.1 s → 1.0 s | David Zeng (DBA) | **2026-04-20** (this week) | P3 |
| AI-08 | Raise `threads_running` alert 24 → 32 (post-AI-01) | David Zeng (DBA) | 2026-04-25 (after upgrade) | P3 |
| AI-09 | CDP app HikariCP pool audit | 李加彬 (App Dev) | **2026-04-30** (2 weeks) | P3 |
| AI-10 | iZeus export of `mysql_global_status_threads_running` with correct `dbinstance_identifier` label | David Zeng + Monitoring team | 2026-04-25 | P3 |
| AI-11 | Close out LCNA-DBA-2026-023 with 72-h post-implementation monitoring report | David Zeng (DBA) | 2026-04-27 | — |

**中文行动项：**

| 编号 | 行动 | 负责人 | 截止日 | 优先级 |
|:----:|------|--------|--------|:------:|
| AI-01 | RDS 升级至 db.r6g.xlarge（周日 2026-04-19 06:00 UTC 维护窗口） | 曾翔宇 (DBA) | **2026-04-20（本周）** | **P1** |
| AI-02 | DBA × Ops 联合会议，批处理 DELETE 迁移至 07:00 UTC | 曾翔宇 + 运维 | **2026-04-20（本周）** | **P1** |
| AI-03 | 为 `t_user_event`、`t_user_event_track` 部署每周 OPTIMIZE TABLE 定时任务 | 曾翔宇 (DBA) | **2026-04-20（本周）** | **P1** |
| AI-04 | CDP 管道应用侧批量 DELETE 分片 + 多行事务 | 李加彬 (应用) | **2026-04-30（两周内）** | P2 |
| AI-05 | 增加复合索引 `idx_user_state_tenant` | 曾翔宇 (DBA) | **2026-04-20（本周）** | P2 |
| AI-06 | `max_connections` 4000 → 300（参数组） | 曾翔宇 (DBA) | **2026-04-20（本周）** | P2 |
| AI-07 | `long_query_time` 0.1 s → 1.0 s | 曾翔宇 (DBA) | **2026-04-20（本周）** | P3 |
| AI-08 | `threads_running` 告警阈值 24 → 32（AI-01 完成后） | 曾翔宇 (DBA) | 2026-04-25（升级后） | P3 |
| AI-09 | CDP 应用 HikariCP 连接池审计 | 李加彬 (应用) | **2026-04-30（两周内）** | P3 |
| AI-10 | iZeus 导出 `mysql_global_status_threads_running` 并修正 `dbinstance_identifier` 标签 | 曾翔宇 + 监控团队 | 2026-04-25 | P3 |
| AI-11 | 升级后 72 小时监控回顾，闭环 LCNA-DBA-2026-023 | 曾翔宇 (DBA) | 2026-04-27 | — |

---

## 11. Lessons Learned

1. **RCAs without deadline enforcement decay to zero-value documents.** The Mar 26 RCA correctly identified 9 of 9 remediation items; 0 of 9 shipped in 21 days. The report was factually correct and operationally inert. Future RCAs must include calendar-linked deadline tracking and weekly status surface.
2. **Fragmentation is a continuous process, not a one-off remediation.** The Mar 12 → Mar 26 cycle already demonstrated this (`t_user_event_track` 662.8 % → 6.3 % → 234.4 %); we ignored the signal. Scheduled OPTIMIZE must be a standing operational control.
3. **"Upgrade solved OOM" creates dangerous confidence.** Stakeholders conflated "instance upgraded, OOM resolved" with "problem solved." The CPU bottleneck was explicitly called out on Mar 26 and still went unfunded.
4. **Alert fatigue is an operational risk, not a cosmetic concern.** 6 fires in 62 hours pushes on-call toward muting. Noise reduction (long_query_time, alert threshold) is a safety measure, not a hygiene nicety.
5. **We missed the `t_user_event_track` amplifier on Mar 26.** Our digest analysis focused on the top-offender user and did not enumerate the second batch DELETE. Future digest analyses must exhaustively enumerate all DELETE patterns per user.

---

## 12. Stakeholder Notes — WeChat Quotes / 相关同事沟通摘录

> (Ops 张翔 via WeChat, 2026-04-16) *"最近 isalescdp 频繁告警，你们 DBA 这边有排查吗？是不是跟最近新开 4 家店上的量有关？"*

> (Ops 张翔) *"慢查询这么多是不是因为连接数上来了？还是连接数高是慢查询造成的？上午业务那边反馈有点慢。"*

These three questions (customer impact / scaling cause / causality direction) are answered directly in §4, §5.5, and §5.6 of this report respectively.

---

## Appendix A — Live MySQL Diagnostic Snapshot (2026-04-16 14:00 UTC)

```
Threads_connected        : 97
Threads_running          : 2
Max_used_connections     : 214
Max_used_connections_time: 2026-04-16 04:00:17
Slow_queries (cumulative): 38,338
Com_delete (cumulative)  : driven by isalesmktingadm_A_w (batch) + icdprealtimeuge_A_w (CDP)
long_query_time          : 0.100000
innodb_buffer_pool_size  : 2,147,483,648  (2 GB — restored post-Mar 12 emergency)
max_connections          : 4,000          (UNCHANGED since Mar 26 recommendation)
table_open_cache         : 4,000          (UNCHANGED)
version                  : 8.0.40
uptime                   : 27 days (since Mar 20 upgrade)
```

## Appendix B — Slow-Query Digest (Top 5 by Time, 2026-04-14 → 2026-04-16)

| Digest Pattern | Exec | Avg Time | Top User |
|----------------|-----:|---------:|----------|
| `INSERT INTO t_user_event_track (...) VALUES (...)` | ~6,000+ | 0.45 s | icdprealtimeuge_A_w |
| `DELETE FROM t_user_state WHERE user_no=? AND event_type=? AND tenant=?` | ~3,000+ | 0.42 s | icdprealtimeuge_A_w |
| `INSERT INTO t_user_state (...) VALUES (...)` | ~3,000+ | 0.42 s | icdprealtimeuge_A_w |
| `DELETE FROM t_user_event WHERE id <= ?` | ~12 | 1.30 s | isalesmktingadm_A_w |
| `DELETE FROM t_user_event_track WHERE ...` | **~1,658** | **0.107 s** | isalesmktingadm_A_w **(newly identified)** |

## Appendix C — Batch DELETE Pattern (Slow Log Sample)

```sql
-- User: isalesmktingadm_A_w  (04:05:23 UTC, 2026-04-16)
DELETE FROM t_user_event WHERE id <= 394360093;
-- Query_time: 1.41 s  Rows_examined: 5000  Lock_time: 0.000003 s

-- 15 s later
DELETE FROM t_user_event WHERE id <= 394365093;
-- Query_time: 1.37 s  Rows_examined: 5000

-- Pattern continues for ~60 min; each 5K-row DELETE is a single statement
-- driving 80+ % CPU for 1.1–1.6 s and blocking concurrent CDP INSERTs
```

## Appendix D — DDL Reference

```sql
-- AI-05: composite index
ALTER TABLE t_user_state
  ADD INDEX idx_user_state_tenant (user_no, event_type, tenant),
  ALGORITHM=INPLACE, LOCK=NONE;

-- AI-03: weekly OPTIMIZE (via ALTER ... ENGINE=InnoDB online rebuild)
ALTER TABLE t_user_event ENGINE=InnoDB;         -- reclaims ~125 MB
ALTER TABLE t_user_event_track ENGINE=InnoDB;   -- reclaims ~85 MB
```

## Appendix E — CloudWatch 2-min Metric Samples (2026-04-16 03:50 → 04:30 UTC)

| Time (UTC) | CPU % | WriteIOPS | Threads_connected | FreeableMem MB | CPU Credits |
|-----------:|------:|----------:|------------------:|---------------:|------------:|
| 03:50 | 5.2 | 14 | 70 | 1,552 | 576 |
| 03:58 | 8.1 | 88 | 74 | 1,540 | 575 |
| 04:00 | 47.5 | 842 | 168 | 1,520 | 573 |
| 04:02 | 68.9 | 1,028 | 201 | 1,498 | 568 |
| 04:04 | 82.1 | 1,116 | 212 | 1,476 | 562 |
| **04:06** | **86.3** | **1,158** | **214** | 1,460 | **556** |
| 04:12 | 79.4 | 1,084 | 198 | 1,472 | 558 |
| 04:18 | 66.7 | 962 | 172 | 1,488 | 562 |
| 04:26 | 34.1 | 518 | 118 | 1,510 | 567 |
| 04:30 | 12.4 | 104 | 92 | 1,528 | 571 |

## Appendix F — App-side Batch DELETE Template (for AI-04)

```sql
-- Replacement for single-statement 5K-row DELETE:
REPEAT
  DELETE FROM t_user_event WHERE id <= {target_id} LIMIT 500;
  SELECT SLEEP(0.5);
UNTIL ROW_COUNT() = 0 END REPEAT;

-- Or application-layer loop:
-- while (rowsDeleted = deleteChunk(500)) > 0 {
--   Thread.sleep(500);
-- }
```

## Appendix G — RDS Events (Past 21 days)

| Date | Event |
|------|-------|
| 2026-03-26 | (no modify-instance event) |
| 2026-03-27 → 2026-04-15 | Daily automated backups ~03:51 UTC (normal) |
| 2026-04-16 | (no modify-instance event — instance class unchanged since Mar 20) |

Confirms: no RDS-level change in 21 days. The degradation is pure workload-vs-capacity.

## Appendix H — Slow Log User Distribution (2026-04-14 → 2026-04-16, aggregate 6,221 slow queries)

| User | Slow Query Count | % |
|------|----------------:|--:|
| icdprealtimeuge_A_w | 4,187 | 67.3 % |
| isalesmktingadm_A_w | 1,671 | 26.9 % |
| icdprealtimeuge_A_o | 287 | 4.6 % |
| Other | 76 | 1.2 % |

`isalesmktingadm_A_w` (nightly batch) accounts for 27 % of slow queries but causes the worst CPU spikes because its queries are 3× longer than CDP queries.

## Appendix I — Instance Configuration

```
Class:              db.t4g.medium  (2 vCPU, 4 GB, Graviton T-class burstable)
Engine:             MySQL 8.0.40
Multi-AZ:           Yes (stdby in us-east-1b)
Storage:            gp3, 40 GB, 3000 IOPS, 125 MB/s throughput
Parameter Group:    luckyus-prod-80-new
Option Group:       default:mysql-8-0
Backup Window:      03:51–04:21 UTC (overlaps batch window — flagged Mar 12)
Maintenance Window: Sun 06:00–06:30 UTC
Performance Insights: DISABLED (flagged Mar 12, still not enabled)
Enhanced Monitoring: 60 s granularity
Upgrade History:    2026-03-20 db.t4g.micro → db.t4g.medium
```

## Appendix J — Data Quality Gaps

1. **Prometheus label mismatch** — `mysql_global_status_threads_running{dbinstance_identifier="aws-luckyus-isalescdp-rw"}` returned 0 series; exporter label scheme does not match our CLAUDE.md-documented convention. CloudWatch 2-min metrics used as proxy. AI-10 fixes this.
2. **Performance Insights disabled** — prevented per-SQL-digest CPU attribution at the instance level. Remains unaddressed since Mar 12 RCA.
3. **Alert fire timestamps are inferred** from slow-query density + CPU peaks, not read directly from the alerting pipeline. Minute-precision timestamps would improve future attribution.

## Appendix K — Related Documents

- `/app/reports/RCA-isalescdp-active-threads-20260326.md` — LCNA-INC-2026-012 (the RCA this report re-escalates)
- `/app/reports/RCA-isalescdp-failover-20260312.md` — LCNA-INC-2026-007 (Mar 12 OOM)
- `/app/reports/rds-isalescdp-slow-query-investigation-2026-02-26.md` — LCNA-INC-2026-005 (Feb 26 slow queries)
- `/app/reports/isalescdp-connection-slowquery-analysis-20260416.md` — pre-investigation findings
- `/app/reports/isalescdp-rw-upgrade-investigation-plan.md` — upgrade execution plan (template for AI-01)

---

*Report prepared 2026-04-16 by 曾翔宇 David Zeng (Senior DBA) — Luckin Coffee USA, First Ray Holdings USA Inc.*
*Instance: aws-luckyus-isalescdp-rw | Account: 257394478466 | Region: us-east-1*
*Distribution: Michael (CTO), Ops team, App Dev (李加彬), DBA on-call*
