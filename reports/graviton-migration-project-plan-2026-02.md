# Graviton Migration Project Plan: RDS & OpenSearch
## Blue/Green Deployment Execution Plan

**Created:** February 26, 2026
**Region:** us-east-1
**EDP Discount:** 31% (0.69 multiplier)
**Project Owner:** DBA/Infrastructure Team
**Target Completion:** April 11, 2026 (7 weeks)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [RDS/DocumentDB Migration Plan](#2-rdsdocumentdb-migration-plan)
3. [OpenSearch Migration Plan](#3-opensearch-migration-plan)
4. [Combined Timeline (Gantt View)](#4-combined-timeline)
5. [Risk Register](#5-risk-register)
6. [Communication Plan](#6-communication-plan)
7. [Rollback Playbooks](#7-rollback-playbooks)
8. [Appendix: Verification Checklists](#8-appendix-verification-checklists)

---

## 1. Project Overview

### 1.1 Scope

| Service | Instances/Domains | Migration Type | Monthly Savings |
|---------|-------------------|----------------|-----------------|
| RDS PostgreSQL | 3 instances | r5/m5 → r6g/m6g | $121.20 |
| RDS MySQL | 2 instances | t3 → t4g | $3.02 |
| DocumentDB | 6 instances | t3 → t4g | $7.08 |
| RDS Storage | 3 instances | gp2 → gp3 | $2.17 |
| OpenSearch Data Nodes | 2 domains (8 nodes) | m5 → m6g | $82.39 |
| OpenSearch Master Nodes | 2 domains (6 nodes) | t3 → m7g | $15.10 |
| OpenSearch Storage | 2 domains | gp2 → gp3 | $41.54 |
| **TOTAL** | **22 targets** | | **$272.50/mo ($3,270/yr)** |

### 1.2 Guiding Principles

1. **One change at a time per domain/cluster** — never stack concurrent modifications
2. **Lowest risk first** — validate process on non-critical instances before touching production-critical ones
3. **Business-hours avoidance** — all changes during US-East maintenance windows (Tue/Wed 2-6 AM ET)
4. **72-hour soak** — minimum observation period between changes within the same service tier
5. **Rollback ready** — every step has a documented reversal procedure tested in advance

### 1.3 Go/No-Go Criteria (applies to every change)

| Check | Requirement |
|-------|-------------|
| Recent backup | Snapshot < 6 hours old |
| Cluster health | GREEN (OpenSearch) / Available (RDS) |
| Active connections | No long-running transactions > 30 min |
| CPU utilization | < 70% at time of change |
| Disk space | > 25% free |
| Team availability | 2+ engineers online during change |
| Rollback tested | Reversal procedure reviewed same day |

---

## 2. RDS/DocumentDB Migration Plan

### 2.1 Instance Inventory & Batch Assignment

Instances are grouped into batches by risk profile and dependency. Each batch executes as a unit across one maintenance window.

#### Batch A — Storage Only (Zero Downtime, Week 1)

These are gp2→gp3 online modifications. No instance restart. Used as a warm-up exercise for the team.

| # | Instance | Change | Current | Target | Savings/mo | Risk |
|---|----------|--------|---------|--------|------------|------|
| A1 | recovery-dbatest | gp2→gp3 | 40 GB gp2 | 40 GB gp3 | $0.97 | Very Low |
| A2 | aws-luckyus-devops-rw | gp2→gp3 | 20 GB gp2 | 20 GB gp3 | $0.48 | Very Low |
| A3 | aws-luckyus-ldas-rw | gp2→gp3 | 30 GB gp2 | 30 GB gp3 | $0.72 | Very Low |

**Execution:** All 3 can run same day (no downtime). Start with recovery-dbatest as canary.

```bash
# Template command
aws rds modify-db-instance \
  --db-instance-identifier <instance-id> \
  --storage-type gp3 \
  --apply-immediately
```

**Verification:** Check `StorageType` = gp3 in console, confirm IOPS baseline 3000, throughput 125 MB/s.

---

#### Batch B — Test/Dev Graviton (Week 2)

Low-impact instances to validate the Graviton migration process end-to-end.

| # | Instance | Engine | Change | Multi-AZ | Savings/mo | Risk |
|---|----------|--------|--------|----------|------------|------|
| B1 | recovery-dbatest | MySQL 8.0.40 | db.t3.small → db.t4g.small | Yes | $1.51 | Very Low |

**Why first:** This is explicitly a test/recovery instance. Perfect canary for the MySQL Graviton process.

**Downtime:** Multi-AZ failover ≈ 30-60 seconds. Application should handle reconnection automatically.

**Process:**
1. Pre-flight: snapshot, verify processlist is clean, confirm app reconnect logic
2. Execute:
   ```bash
   aws rds modify-db-instance \
     --db-instance-identifier recovery-dbatest \
     --db-instance-class db.t4g.small \
     --apply-immediately
   ```
3. Monitor: Watch RDS Events for `DB instance class changed`, confirm `Available` status
4. Post-flight: Run basic CRUD test, verify connections, check error logs for 15 min

---

#### Batch C — DocumentDB Graviton (Week 2-3)

All 6 DocumentDB instances are Single-AZ (no automatic failover). These are grouped by cluster to minimize impact.

| # | Instance | Cluster | Change | Savings/mo | Risk |
|---|----------|---------|--------|------------|------|
| C1 | docdb-devops | devops cluster | db.t3.medium → db.t4g.medium | $1.18 | Low |
| C2 | docdb-devops2 | devops cluster | db.t3.medium → db.t4g.medium | $1.18 | Low |
| C3 | docdb-devops3 | devops cluster | db.t3.medium → db.t4g.medium | $1.18 | Low |
| C4 | docdb-iot | IoT cluster | db.t3.medium → db.t4g.medium | $1.18 | Low |
| C5 | docdb-iot2 | IoT cluster | db.t3.medium → db.t4g.medium | $1.18 | Low |
| C6 | docdb-iot3 | IoT cluster | db.t3.medium → db.t4g.medium | $1.18 | Low |

**CRITICAL: Single-AZ = real downtime.** Each instance will be unavailable during modification (~10-15 min). Applications must tolerate brief outages or be paused.

**Execution order within each cluster:**
1. Modify replica first (least traffic)
2. Verify 24 hours
3. Modify next replica
4. Verify 24 hours
5. Modify primary (requires app coordination)

**Week 2 Schedule:**
- Tue night: docdb-devops (1 instance from devops cluster)
- Wed night: Verify, then docdb-devops2
- Thu: 72-hour soak begins

**Week 3 Schedule:**
- Tue night: docdb-devops3 + docdb-iot
- Wed night: docdb-iot2
- Thu night: docdb-iot3

```bash
# DocumentDB uses same modify command
aws docdb modify-db-instance \
  --db-instance-identifier <instance-id> \
  --db-instance-class db.t4g.medium \
  --apply-immediately
```

---

#### Batch D — MySQL Production (Week 3)

| # | Instance | Engine | Change | Multi-AZ | Savings/mo | Risk |
|---|----------|--------|--------|----------|------------|------|
| D1 | aws-luckyus-iluckyhealth-rw | MySQL 8.0.40 | db.t3.small → db.t4g.small | Yes | $1.51 | Low |

**Why separate batch:** This is a production health-monitoring database. Migration follows the validated process from Batch B.

**Timing:** Wednesday 3 AM ET (lowest traffic, validated from Batch B experience).

---

#### Batch E — PostgreSQL Graviton (Week 4-5) ⭐ HIGHEST VALUE

These 3 instances represent **$121.20/month (91% of RDS Graviton savings)**. They are production-critical and get the most careful treatment.

| # | Instance | Engine | Change | Multi-AZ | Savings/mo | Risk |
|---|----------|--------|--------|----------|------------|------|
| E1 | aws-luckyus-pgilkmap-rw | PG 17.4 | db.m5.large → db.m6g.large | Yes | $19.14 | Low-Med |
| E2 | aws-luckyus-difynew-rw | PG 16.10 | db.r5.xlarge → db.r6g.xlarge | Yes | $51.03 | Medium |
| E3 | aws-luckyus-dify-rw | PG 16.8 | db.r5.xlarge → db.r6g.xlarge | Yes | $51.03 | Medium |

**Execution order rationale:**
1. **pgilkmap first** — PostGIS/map service, lower traffic, validates PG + Graviton process
2. **difynew second** — Newer Dify instance, likely less critical than primary
3. **dify-rw last** — Primary Dify AI platform, highest criticality

**Week 4:**
- Tuesday 3 AM: pgilkmap migration
- Wednesday-Friday: 72-hour soak, monitor query performance, PostGIS spatial operations
- Saturday: Sign-off on pgilkmap

**Week 5:**
- Tuesday 3 AM: difynew migration
- Wednesday: 24-hour soak, verify Dify platform functionality
- Thursday 3 AM: dify-rw migration (if difynew is clean)
- Friday-Sunday: 72-hour soak on both Dify instances

**Special Dify considerations:**
- Dify is the AI platform — coordinate with AI/ML team before changes
- Verify LLM API calls, workflow execution, knowledge base queries post-migration
- These are r5.xlarge (4 vCPU, 32 GB) → r6g.xlarge (4 vCPU, 32 GB) — same specs, ARM architecture
- r6g typically provides 10-20% better price/performance vs r5

```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-pgilkmap-rw \
  --db-instance-class db.m6g.large \
  --apply-immediately
```

### 2.2 RDS Migration Summary Timeline

| Week | Batch | Instances | Change | Savings Unlocked |
|------|-------|-----------|--------|-----------------|
| Week 1 (Mar 4-7) | A | 3 | gp2→gp3 storage | $2.17/mo |
| Week 2 (Mar 11-14) | B + C (partial) | 1 + 3 | MySQL test + DocDB devops | $4.75/mo |
| Week 3 (Mar 18-21) | C (rest) + D | 3 + 1 | DocDB IoT + MySQL prod | $5.05/mo |
| Week 4 (Mar 25-28) | E (pgilkmap) | 1 | PostgreSQL map DB | $19.14/mo |
| Week 5 (Apr 1-4) | E (Dify ×2) | 2 | PostgreSQL Dify platform | $102.06/mo |
| **TOTAL** | | **14** | | **$133.17/mo** |

---

## 3. OpenSearch Migration Plan

### 3.1 Domain Inventory & Migration Scope

| Domain | Engine | Data Nodes | Master Nodes | Storage | Status |
|--------|--------|-----------|--------------|---------|--------|
| luckylfe-log | ES 7.10 | m5.large×4 | t3.medium×3 | gp2 80GB×4 | **Migrate** |
| luckyur-log | ES 7.10 | m5.xlarge×4 | t3.medium×3 | gp2 350GB×4 | **Migrate (caution)** |
| luckycommon | ES 6.8 | m5.large×4 | t3.small×3 | gp3 100GB×4 | **Blocked** (ES 6.8) |
| luckyus-opensearch-dify | OS 2.15 | r6g.large×2 | m7g.large×3 | gp3 30GB×2 | **Already done** |

### 3.2 OpenSearch Blue/Green Deployment Process

Unlike RDS, OpenSearch instance type changes trigger an **automatic blue/green deployment**:

```
1. AWS provisions NEW nodes alongside existing nodes
2. Data replicates from old → new nodes
3. Traffic cuts over to new nodes
4. Old nodes are terminated
```

**Duration:** 30 min to several hours depending on data volume.
**Impact:** Near-zero downtime, but cluster performance may degrade during data migration.
**Constraint:** Only ONE configuration change at a time per domain. Must wait for "Active" status before next change.

### 3.3 Migration Strategy per Domain

Each domain requires up to 3 sequential changes (never parallel):

```
Step 1: gp2 → gp3 storage (online, fastest)
        ↓ wait for Active status + 24hr soak
Step 2: Data nodes m5 → m6g (blue/green, largest change)
        ↓ wait for Active status + 72hr soak
Step 3: Master nodes t3 → m7g (blue/green, riskiest for stability)
        ↓ wait for Active status + 72hr soak
```

**Why this order:**
- Storage change is lowest risk and proves the change pipeline works
- Data nodes are the primary cost savings target
- Master nodes are saved for last because they're the most sensitive to cluster stability

---

#### Domain 1: luckylfe-log (Week 4) — Lower Risk

**Current state:** Avg CPU 8.1%, Max CPU 50%, 616 shards — HEALTHY

| Step | Change | Savings/mo | Duration | Risk |
|------|--------|------------|----------|------|
| 1 | gp2 80GB×4 → gp3 | $7.73 | ~30 min | Very Low |
| 2 | m5.large×4 → m6g.large×4 | $28.04 | 1-3 hours | Low |
| 3 | t3.medium×3 → m7g.medium×3 | ~$3.73 | 1-2 hours | Low |

**Schedule:**
- **Tuesday 2 AM:** Step 1 — gp2→gp3 storage change
  ```bash
  aws opensearch update-domain-config \
    --domain-name luckylfe-log \
    --ebs-options VolumeType=gp3,VolumeSize=80,Iops=3000,Throughput=125
  ```
- **Wednesday:** Verify Active status, confirm storage type in console
- **Thursday 2 AM:** Step 2 — Data node Graviton migration
  ```bash
  aws opensearch update-domain-config \
    --domain-name luckylfe-log \
    --cluster-config InstanceType=m6g.large.search
  ```
- **Thursday-Sunday:** 72-hour soak period
  - Monitor: cluster health, indexing rate, search latency, CPU/memory
  - Check: no increase in rejected search/bulk thread pools
- **Following Tuesday 2 AM:** Step 3 — Master node upgrade
  ```bash
  aws opensearch update-domain-config \
    --domain-name luckylfe-log \
    --cluster-config DedicatedMasterType=m7g.medium.search
  ```
- **Following Wed-Fri:** 72-hour soak on master nodes

**Monitoring during blue/green:**
```
Key metrics to watch (CloudWatch):
- ClusterStatus.green = 1 (must stay green)
- CPUUtilization < 80%
- JVMMemoryPressure < 80%
- ThreadpoolSearchRejected = 0
- ThreadpoolBulkRejected = 0
- FreeStorageSpace > 20% of total
- MasterReachableFromNode = 1
- AutomatedSnapshotFailure = 0
```

---

#### Domain 2: luckyur-log (Week 5-6) — Higher Risk ⚠️

**Current state:** Avg CPU 16.9%, **Max CPU 84%**, **6000 shards** — CAUTION

This domain requires extra care due to:
- **84% peak CPU** — near capacity on current hardware
- **6000 shards** — extremely high shard count puts pressure on master nodes
- Graviton m6g typically matches or exceeds m5 performance, but must verify

| Step | Change | Savings/mo | Duration | Risk |
|------|--------|------------|----------|------|
| 1 | gp2 350GB×4 → gp3 | $33.81 | ~1 hour | Very Low |
| 2 | m5.xlarge×4 → m6g.xlarge×4 | $54.35 | 2-6 hours | Medium |
| 3 | t3.medium×3 → m7g.medium×3 | ~$11.37 | 1-3 hours | **Moderate-High** |

**Pre-migration actions (Week 5, before any changes):**
1. **Shard audit** — Identify and close old indices to reduce shard count below 4000 if possible
   ```
   GET _cat/indices?v&s=creation.date&h=index,health,pri,rep,store.size
   ```
2. **ILM review** — Ensure index lifecycle policies are closing/deleting old indices
3. **Snapshot verification** — Confirm automated snapshots are completing successfully
4. **Baseline metrics** — Record 7-day average for CPU, JVM pressure, search latency, indexing rate

**Schedule:**
- **Week 5 Monday:** Pre-migration shard cleanup and baseline recording
- **Week 5 Tuesday 2 AM:** Step 1 — gp2→gp3 storage
  ```bash
  aws opensearch update-domain-config \
    --domain-name luckyur-log \
    --ebs-options VolumeType=gp3,VolumeSize=350,Iops=3000,Throughput=125
  ```
- **Week 5 Wednesday:** Verify storage change complete
- **Week 5 Thursday 2 AM:** Step 2 — Data node Graviton migration
  ```bash
  aws opensearch update-domain-config \
    --domain-name luckyur-log \
    --cluster-config InstanceType=m6g.xlarge.search
  ```
- **Week 5 Thu → Week 6 Mon:** Extended soak (4+ days for this high-risk domain)
  - **Abort criteria:** If CPU > 90% sustained for 15 min, or JVMMemoryPressure > 85%
  - Compare search latency p95 against baseline — must be within 20%
- **Week 6 Tuesday 2 AM:** Step 3 — Master node upgrade (only if Step 2 is clean)
  ```bash
  aws opensearch update-domain-config \
    --domain-name luckyur-log \
    --cluster-config DedicatedMasterType=m7g.medium.search
  ```
- **Week 6 Wed-Fri:** 72-hour soak on master nodes

**Special master node concerns for luckyur-log:**
- 6000 shards creates significant cluster state management overhead
- m7g.medium (1 vCPU, 4 GB) vs t3.medium (2 vCPU, 4 GB burstable)
- The m7g has fewer vCPUs but they are dedicated (no burst credit depletion)
- Per the evaluation report: MODERATE RISK — 53% max CPU spikes on current t3.medium masters
- **Decision gate:** If shard count cannot be reduced below 4000, consider m7g.large instead of m7g.medium for master nodes (adds cost but ensures stability)

---

### 3.4 What About luckycommon (ES 6.8)?

**Status: BLOCKED** — Elasticsearch 6.8 does not support Graviton instances.

This is **out of scope** for this project. A separate version upgrade project (ES 6.8 → OpenSearch 2.x) is a prerequisite. That upgrade is a significantly larger effort involving:
- API compatibility testing
- Query syntax changes (ES 6→7 breaking changes)
- Plugin compatibility verification
- Full reindex possibility

**Recommendation:** Track as a separate initiative. Estimated Graviton savings after upgrade: ~$28/month.

### 3.5 OpenSearch Migration Summary Timeline

| Week | Domain | Step | Change | Savings Unlocked |
|------|--------|------|--------|-----------------|
| Week 4 Tue | luckylfe-log | 1 | gp2→gp3 storage | $7.73/mo |
| Week 4 Thu | luckylfe-log | 2 | m5→m6g data nodes | $28.04/mo |
| Week 5 Tue | luckylfe-log | 3 | t3→m7g master nodes | $3.73/mo |
| Week 5 Tue | luckyur-log | 1 | gp2→gp3 storage | $33.81/mo |
| Week 5 Thu | luckyur-log | 2 | m5→m6g data nodes | $54.35/mo |
| Week 6 Tue | luckyur-log | 3 | t3→m7g master nodes | $11.37/mo |
| **TOTAL** | | | | **$139.03/mo** |

---

## 4. Combined Timeline (Gantt View)

```
Week 1 (Mar 4-7)     RDS: ████ Batch A — gp2→gp3 storage (3 instances)
                      OS:  ░░░░ (no changes)

Week 2 (Mar 11-14)   RDS: ████ Batch B+C — MySQL test + DocDB devops (4 instances)
                      OS:  ░░░░ (no changes)

Week 3 (Mar 18-21)   RDS: ████ Batch C+D — DocDB IoT + MySQL prod (4 instances)
                      OS:  ░░░░ (no changes)

Week 4 (Mar 25-28)   RDS: ██░░ Batch E — pgilkmap PostgreSQL
                      OS:  ████ luckylfe-log Steps 1+2 (storage + data nodes)

Week 5 (Apr 1-4)     RDS: ████ Batch E — Dify PostgreSQL ×2
                      OS:  ████ luckylfe-log Step 3 + luckyur-log Steps 1+2

Week 6 (Apr 8-11)    RDS: ░░░░ (complete)
                      OS:  ██░░ luckyur-log Step 3 (master nodes)

Legend: ████ = Active changes  ░░░░ = Soak/idle
```

**Key design decisions:**
- RDS and OpenSearch changes run in parallel (different services, no dependency)
- RDS finishes first (simpler process, more instances)
- OpenSearch starts Week 4 after team has warmed up on RDS changes
- luckyur-log is always last (highest risk)

---

## 5. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| R1 | Application incompatibility with ARM64 (Graviton) | Very Low | High | All engines (MySQL 8.0, PG 16/17, DocDB 5.0, ES 7.10) have full Graviton support. No application-level code changes needed — database wire protocol is architecture-independent. |
| R2 | Performance regression on Graviton | Low | Medium | m6g/r6g/t4g provide equal or better single-thread performance vs x86 predecessors. 72-hour soak period catches regressions. Rollback available. |
| R3 | Extended blue/green duration on OpenSearch | Medium | Low | Large data volumes (1.4 TB on luckyur-log) extend blue/green to 4-6 hours. Schedule with buffer. Monitor cluster health throughout. |
| R4 | luckyur-log CPU exceeds capacity post-migration | Medium | High | 84% peak CPU is already near limit. m6g.xlarge has identical specs (4 vCPU, 16 GB). Graviton3 IPC is better than M5, so CPU should improve or stay flat. If worse: rollback to m5.xlarge. |
| R5 | luckyur-log master node instability with m7g.medium | Medium | High | 6000 shards stress single-vCPU master. **Gate decision:** If shard count > 4000 at migration time, use m7g.large ($0.135/hr) instead of m7g.medium ($0.068/hr). |
| R6 | Multi-AZ failover causes app connection drops | Low | Medium | RDS Multi-AZ failover is 30-60 sec. Apps should have retry logic. Verify connection pooling config (HikariCP, pgBouncer) before migration. |
| R7 | DocumentDB Single-AZ downtime exceeds window | Low | Medium | Single-AZ modify = full restart. ~10-15 min downtime per instance. Schedule during 2-4 AM ET. Notify dependent teams 48 hours ahead. |
| R8 | gp3 IOPS baseline insufficient | Very Low | Low | gp3 baseline is 3000 IOPS / 125 MB/s, vs gp2 which scales with size (240 IOPS for 80GB). For all our volumes, gp3 baseline exceeds gp2 performance. |
| R9 | Concurrent change causes cascading failure | Low | High | **Never** make parallel changes to same domain/cluster. One change at a time. 72-hour soak between changes. |
| R10 | luckylfe-log recent yellow cluster event recurs | Low | Medium | Reference: cluster went yellow on Feb 12. Verify root cause is resolved before migration. Check unassigned shards = 0. |

---

## 6. Communication Plan

### 6.1 Stakeholder Notifications

| When | Who | Channel | Content |
|------|-----|---------|---------|
| Week 0 (Feb 26-28) | All engineering leads | Email + Slack #infra | Project announcement, timeline, maintenance windows |
| 48 hours before each batch | Affected service owners | Slack DM + ticket | Specific instance, window, expected impact |
| 15 min before change | On-call + service owner | Slack #ops-alerts | "Starting migration of X, ETA Y minutes" |
| During change | DBA team | Slack #dba-ops | Live status updates every 15 min |
| Post-change | Affected service owners | Slack DM | "Complete. Please verify your service." |
| Weekly | Leadership | Email | Progress report: instances migrated, savings realized, issues |

### 6.2 Escalation Path

```
Level 1: DBA on-call (immediate)
Level 2: Infrastructure lead (15 min)
Level 3: VP Engineering (30 min — only for customer-impacting issues)
```

---

## 7. Rollback Playbooks

### 7.1 RDS Instance Class Rollback

**Trigger:** Performance degradation, application errors, or CPU/memory anomalies within 72-hour soak.

```bash
# Rollback to original instance class
aws rds modify-db-instance \
  --db-instance-identifier <instance-id> \
  --db-instance-class <original-class> \
  --apply-immediately

# Example: revert Dify from r6g back to r5
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-dify-rw \
  --db-instance-class db.r5.xlarge \
  --apply-immediately
```

**Duration:** Multi-AZ ~30-60 sec failover. Single-AZ ~10-15 min.
**Data impact:** None. Instance class change only affects compute, not data.

### 7.2 OpenSearch Instance Type Rollback

**Trigger:** Cluster health RED/YELLOW, sustained high CPU/JVM pressure, rejected threads.

```bash
# Rollback data nodes
aws opensearch update-domain-config \
  --domain-name <domain-name> \
  --cluster-config InstanceType=m5.large.search  # or m5.xlarge.search

# Rollback master nodes
aws opensearch update-domain-config \
  --domain-name <domain-name> \
  --cluster-config DedicatedMasterType=t3.medium.search
```

**Duration:** Another blue/green deployment (1-6 hours depending on data volume).
**IMPORTANT:** You cannot rollback while a blue/green is in progress. If the initial change is still deploying and the cluster goes RED, open an AWS Support case (Severity: Urgent/Production System Down).

### 7.3 gp3 Storage Rollback

**Note:** gp3→gp2 rollback is generally NOT needed (gp3 performs equal or better). If required:

```bash
# RDS
aws rds modify-db-instance \
  --db-instance-identifier <instance-id> \
  --storage-type gp2 \
  --apply-immediately

# OpenSearch — storage type changes require a new domain config update
aws opensearch update-domain-config \
  --domain-name <domain-name> \
  --ebs-options VolumeType=gp2,VolumeSize=<size>
```

---

## 8. Appendix: Verification Checklists

### 8.1 Post-Migration Verification — RDS/DocumentDB

Run within 30 minutes of migration completing:

- [ ] Instance status = "Available"
- [ ] Instance class shows new Graviton type (t4g/m6g/r6g)
- [ ] Multi-AZ status unchanged
- [ ] Storage type and size unchanged (or gp3 if that was the change)
- [ ] Connections are active (check `SHOW PROCESSLIST` or `pg_stat_activity`)
- [ ] No errors in RDS Event log
- [ ] Application health check passing
- [ ] Run representative query and compare latency to baseline
- [ ] CloudWatch: CPUUtilization, FreeableMemory, DatabaseConnections within normal range
- [ ] Replication lag = 0 (for Multi-AZ)

### 8.2 Post-Migration Verification — OpenSearch

Run after domain status returns to "Active":

- [ ] Cluster health = GREEN
- [ ] All nodes visible: `GET _cat/nodes?v`
- [ ] Instance type correct: `GET _cat/nodes?v&h=name,ip,node.role,heap.percent,cpu,load_1m`
- [ ] Shard count matches pre-migration: `GET _cluster/health`
- [ ] No unassigned shards: `GET _cat/shards?v&h=index,shard,prirep,state,unassigned.reason | grep UNASSIGNED`
- [ ] Indexing working: verify new documents appearing in recent indices
- [ ] Search working: run representative search query, compare latency
- [ ] CloudWatch metrics within normal range:
  - CPUUtilization < 80%
  - JVMMemoryPressure < 80%
  - ThreadpoolSearchRejected = 0
  - ThreadpoolBulkRejected = 0
  - ClusterStatus.green = 1
- [ ] Automated snapshots completing
- [ ] Kibana/OpenSearch Dashboards accessible

### 8.3 72-Hour Soak Monitoring

During the 72-hour soak after each change, watch for:

| Metric | Alert Threshold | Action |
|--------|----------------|--------|
| RDS CPU > 80% sustained 15 min | Warning | Investigate, prepare rollback |
| RDS CPU > 95% sustained 5 min | Critical | Rollback immediately |
| OS Cluster status != GREEN | Critical | Investigate immediately |
| OS JVMMemoryPressure > 85% | Warning | Check for shard rebalancing |
| OS ThreadpoolRejected > 0 | Warning | Check indexing rate, may need to throttle |
| App error rate > 2× baseline | Critical | Rollback + investigate |
| Connection timeouts | Critical | Check DNS, security groups, connection limits |

---

## Project Success Metrics

| Metric | Target |
|--------|--------|
| All 14 RDS/DocDB instances migrated | By April 4, 2026 |
| Both OpenSearch domains migrated | By April 11, 2026 |
| Zero customer-impacting incidents | During entire project |
| Monthly savings realized | $272.50/month ($3,270/year) |
| Rollbacks required | 0 (target), ≤2 (acceptable) |

---

## Approval & Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Project Lead (DBA) | | | |
| Infrastructure Manager | | | |
| DevOps Lead | | | |
| AI/ML Team (for Dify) | | | |

---

*Plan created: February 26, 2026*
*Next review: March 3, 2026 (Week 0 kickoff)*
*Author: DBA/Infrastructure Team*
