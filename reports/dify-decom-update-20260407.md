# Dify Decommission Project — Data Collection Update (2026-04-07)

| Field | Value |
|-------|-------|
| **Report Date** | 2026-04-07 |
| **Author** | 曾翔宇 (David Zeng), DBA/Infrastructure |
| **Type** | Data collection update (v3) |
| **Previous Reports** | v1 评估报告 (2026-03-24), v2 技术准备报告 (2026-03-25) |
| **AWS Account** | 257394478466 (us-east-1) |
| **Data Sources** | MCP postgres_query, redis_command, eks-server; AWS CloudWatch, RDS, ElastiCache, OpenSearch, EC2, ELBv2, S3, Cost Explorer |

---

## 一、Executive Summary

### Project Status Update

Per DevOps lead 彭啸 (2026-04-07):
- **Project is PAUSED, not cancelled.** At least 6 months before restart.
- **Cost optimization (降本) is APPROVED to proceed.**
- Three major decommission areas: (1) K8s namespace resources, (2) Milvus vector DB + storage, (3) AWS managed services
- 彭啸 (DevOps) coordinates non-DB resource reclamation with 王东尧 (Ops)
- David (DBA) responsible for database-side decommission + technical investigation + reporting

### Key Findings Delta from Previous Report (2026-03-25)

| Item | Previous (03-25) | Current (04-07) | Delta |
|------|-------------------|------------------|-------|
| API token last used | 2026-03-23 | **2026-03-23** (unchanged) | No new activity in 15 days |
| Messages since blocker | 7 on 03-23 | **7 on 03-23** (zero since) | Blocker effectively resolved |
| User logins (last 30d) | 2 users (03-09) | **0 users since 03-09** | 29 days no login |
| OLD RDS connections | Avg ~1 | **Avg 1.0** (Apr) | Unchanged — idle |
| NEW RDS connections | Avg ~16 | **Avg 16.0** (Apr) | Unchanged — pod connections only |
| Redis old keys | 28 | **11** (3 in db0 + 8 in db1) | Keys decreased |
| Redis old memory | 10.41 MB used / 4.79 GB max | **10.41 MB / 4.79 GB** | Unchanged |
| OpenSearch docs | 26 | **26** | Unchanged |
| S3 total | 73 MB / 663 objects | **73.37 MB / 663 objects** | Zero growth |
| NLB traffic | 0 since Oct 2025 | **0 since Oct 2025** | Confirmed 6+ months zero |
| EC2 CPU | <1% | **<0.35%** | Confirmed idle |
| Total namespace pods | 46 | **46** | Unchanged |
| Monthly cost | ~$2,190 (plan) / ~$1,841 (tech report) | **~$2,190** | Unchanged |

### Recommendation

**Scenario A: Full Shutdown** is recommended for the 6-month pause period.
- Net savings: **~$12,000** over 6 months
- Snapshot retention cost: ~$4/mo
- Restore time: 2-4 hours
- Zero business impact — no active users or API consumers for 15+ days

---

## 二、API Token Blocker Status

### 2.1 Token Activity (as of 2026-04-07)

| # | App Name | Token Prefix | Last Used | Status |
|---|----------|-------------|-----------|--------|
| 1 | 美国AI点单-开发-lei_Solution2-prod | app-M3BRuBlA... | **2026-03-23 06:55** | Last active token |
| 2 | 美国AI点单-开发-lei_Solution2-test03 | app-A8GUgy6g... | 2025-12-05 | Dormant |
| 3 | 美国AI点单-开发-lei_Solution1-prod | app-42CswaB4... | 2025-11-07 | Dormant |
| 4-21 | Various | — | Before 2025-11-07 | Dormant or never used |

**Total tokens: 21** (unchanged). Only 1 was active in March 2026 — now **15 days dormant**.

### 2.2 Message Activity Since Blocker

| Day | Messages | Workflow Runs |
|-----|----------|--------------|
| 2026-03-23 | 7 | 7 |
| 2026-03-24 to 04-07 | **0** | **0** |

**Conclusion: The token is no longer in active use.** The blocker is effectively resolved. Recommend disabling the token as the first decommission step — no user coordination needed.

### 2.3 Message Lifecycle (Full Trend)

| Month | Messages | Notes |
|-------|----------|-------|
| 2025-09 | 43 | Initial deployment |
| 2025-10 | **35,913** | Peak usage (AI ordering dev) |
| 2025-11 | 3,635 | Declining |
| 2025-12 | 4 | Near-zero |
| 2026-01 | 0 | — |
| 2026-02 | 1 | Single test |
| 2026-03 | 8 | lei_Solution2-prod final burst |
| 2026-04 | 0 | — |

### 2.4 User Activity

Only 2 accounts showed any activity since March 1:
- **dify** (xia***@lkcoffee.com): last active 2026-03-09
- **卢延新** (yan***@lkcoffee.com): last active 2026-03-09

No new accounts created. No logins for **29 days**.

---

## 三、Infrastructure Metrics Update (7-Month Trends: Sep 2025 – Apr 2026)

### 3.1 RDS PostgreSQL

#### DatabaseConnections (Monthly Averages)

| Month | OLD (dify-rw) Avg | OLD Max | NEW (difynew-rw) Avg | NEW Max |
|-------|-------------------|---------|----------------------|---------|
| 2025-09 | 20.2 | 25 | 16.7 | 37 |
| 2025-10 | 23.0 | 24 | 36.0 | 61 |
| 2025-11 | 20.2 | 24 | 42.8 | 58 |
| 2025-12 | **1.0** | 2 | **15.0** | 18 |
| 2026-01 | 1.7 | 2 | 12.9 | 15 |
| 2026-02 | 1.1 | 2 | 14.1 | 16 |
| 2026-03 | 1.7 | 2 | 16.2 | 20 |
| 2026-04 | **1.0** | 1 | **16.0** | 17 |

OLD instance: effectively zero application connections since Dec 2025 (only rdsadmin + MCP probe).
NEW instance: 16 idle connections from new-dify pods (dify_w user, all state=idle).

#### CPUUtilization (Monthly Averages)

| Month | OLD Avg% | OLD Max% | NEW Avg% | NEW Max% |
|-------|----------|----------|----------|----------|
| 2025-09 | 1.57 | 3.7 | 1.99 | 13.5 |
| 2025-10 | 1.57 | 28.0 | 2.06 | 26.2 |
| 2025-11 | 1.58 | 24.9 | 1.93 | 30.7 |
| 2025-12 | 1.57 | 5.3 | 1.77 | 4.2 |
| 2026-01 | 1.56 | 28.1 | 1.74 | 23.7 |
| 2026-02 | 1.57 | 3.4 | 2.02 | 5.5 |
| 2026-03 | 1.51 | 23.4 | 1.90 | 24.2 |
| 2026-04 | **1.52** | 2.8 | **1.67** | 2.8 |

CPU averages ~1.5-2% on both — purely RDS internal overhead. Max spikes are periodic RDS maintenance (Multi-AZ sync checks).

#### WriteIOPS (Monthly Averages)

| Month | OLD Avg | NEW Avg | Notes |
|-------|---------|---------|-------|
| 2025-09 | 1.48 | 1.52 | — |
| 2025-10 | 1.47 | **2.69** | Peak usage |
| 2025-11 | 1.49 | **1.63** | Declining |
| 2025-12 – 2026-04 | ~1.50 | ~1.48 | Baseline noise only |

WriteIOPS at baseline (~1.5) = RDS checkpoint/WAL overhead, zero application writes.

#### FreeableMemory

| Instance | Avg Free | % of 32 GiB |
|----------|----------|-------------|
| OLD (dify-rw) | 21.3 GiB | **67% free** |
| NEW (difynew-rw) | 21.2 GiB | **66% free** |

Both instances: db.r5.xlarge (32 GiB RAM), 2/3 of memory unused. Massively oversized.

#### Database Sizes

| Instance | Database | Size |
|----------|----------|------|
| OLD (dify-rw) | luckyus_dify_api | 1,222 MB |
| OLD (dify-rw) | luckyus_dify_plugin | 8.8 MB |
| NEW (difynew-rw) | luckyus_dify_api | **5,942 MB** |
| NEW (difynew-rw) | luckyus_dify_plugin | 8.5 MB |

#### Current Live Connections (2026-04-07)

**OLD instance (dify-rw):**
| Database | User | State | Count |
|----------|------|-------|-------|
| (background) | — | — | 5 |
| rdsadmin | rdsadmin | idle | 2 |
| rdsadmin | rdsadmin | — | 1 |
| postgres | dba_admin | active | 1 |
| luckyus_dify_plugin | dify_w | idle | 1 |
| **Total** | | | **10** |

**NEW instance (difynew-rw):**
| Database | User | State | Count |
|----------|------|-------|-------|
| luckyus_dify_api | **dify_w** | **idle** | **16** |
| (background) | — | — | 5 |
| rdsadmin | rdsadmin | idle | 2 |
| rdsadmin | rdsadmin | — | 1 |
| postgres | dba_admin | active | 1 |
| **Total** | | | **25** |

16 idle dify_w connections on NEW = new-dify pods (api x2, worker x2, plugin-daemon x1, sandbox x6 = connections from pool).

#### RDS Instance Status

| Property | OLD (dify-rw) | NEW (difynew-rw) |
|----------|---------------|-------------------|
| Status | available | available |
| Class | db.r5.xlarge | db.r5.xlarge |
| Engine | PostgreSQL 16.8 | PostgreSQL 16.10 |
| Multi-AZ | Yes | Yes |
| Storage | 20 GB gp3 | 20 GB gp3 |

---

### 3.2 ElastiCache Redis

#### Old Cluster: luckyus-redis-dify (cache.m6g.large x2)

| Metric | Sep | Oct | Nov | Dec | Jan | Feb | Mar | Apr |
|--------|-----|-----|-----|-----|-----|-----|-----|-----|
| CurrConnections Avg | 34 | 32 | 30 | 18 | 18 | 18 | 18 | 18 |
| EngineCPU Avg% | 0.21 | 0.21 | 0.21 | 0.21 | 0.21 | 0.21 | 0.22 | 0.22 |
| GetTypeCmds Avg | 39 | 38 | 38 | 38 | 38 | 38 | 38 | 38 |
| SetTypeCmds Avg | 321 | 321 | 321 | 321 | 321 | 321 | 321 | 321 |
| CurrItems | 31 | 20 | 10 | 11 | 11 | 11 | 11 | 11 |
| CacheMisses | 0.21 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Connections dropped from ~34 to ~18 in Dec (old Dify pods disconnected). Get/Set commands are constant — internal Redis background operations. **Zero application cache hits since Oct 2025.**

#### New Cluster: luckyus-difynew (cache.t4g.micro x2)

| Metric | Sep | Oct | Nov | Dec | Jan | Feb | Mar | Apr |
|--------|-----|-----|-----|-----|-----|-----|-----|-----|
| CurrConnections Avg | 34 | 51 | 53 | 34 | 34 | 34 | 34 | 34 |
| EngineCPU Avg% | 0.37 | 0.43 | 0.41 | 0.39 | 0.40 | 0.40 | 0.39 | 0.39 |
| GetTypeCmds Avg | 38 | 203 | 53 | 38 | 38 | 38 | 38 | 38 |
| SetTypeCmds Avg | 247 | 288 | 279 | 278 | 278 | 278 | 277 | 278 |
| CurrItems | 27 | 75 | 52 | 22 | 14 | 14 | 16 | 17 |
| CacheMisses | 0.84 | 154 | 14 | 0.03 | 0 | 0 | 0.03 | 0 |

Peak usage in Oct-Nov (during AI ordering development). Since Dec, constant baseline = new-dify pod connection pool + internal ops.

#### Redis Memory (Old Cluster via MCP, 2026-04-07)

| Metric | Value |
|--------|-------|
| used_memory_human | **10.41 MB** |
| used_memory_rss | 29.05 MB |
| maxmemory | 4.79 GB |
| Utilization | **0.22%** |
| DBSIZE (db0) | 3 keys (1 with TTL) |
| DBSIZE (db1) | 8 keys (0 with TTL) |
| Total keys | **11** |
| mem_fragmentation_ratio | 2.79 |

Previous report: 28 keys. Now 11 — keys have expired naturally. **99.78% of memory is unused.**

#### Cluster Status

| Property | Old (luckyus-redis-dify) | New (luckyus-difynew) |
|----------|--------------------------|------------------------|
| Status | available | available |
| Node Type | cache.m6g.large | cache.t4g.micro |
| Members | 2 nodes | 2 nodes |
| MCP Access | Yes | **NOT in gateway** |

---

### 3.3 OpenSearch

#### luckyus-opensearch-dify Metrics (Monthly Averages)

| Metric | Sep | Oct | Nov | Dec | Jan | Feb | Mar | Apr |
|--------|-----|-----|-----|-----|-----|-----|-----|-----|
| SearchRate Avg | 14.2 | 14.2 | 19.7 | 14.3 | 15.8 | 14.3 | 14.3 | 14.3 |
| IndexingRate Avg | 0.07 | 0.06 | 0.09 | 0.06 | 0.07 | 0.06 | 0.06 | 0.06 |
| CPUUtilization Avg% | 11.0 | 7.9 | 8.6 | 8.4 | 8.4 | 8.2 | 8.3 | 8.4 |
| FreeStorageSpace MB | 24,033 | 24,033 | 24,033 | 24,033 | 24,033 | 24,033 | 24,033 | 24,033 |
| SearchableDocuments | 24.4 | **26** | 26 | 26 | 26 | 26 | 26 | 26 |

SearchRate ~14/sec = internal health check heartbeats. IndexingRate ~0.06/sec = internal bookkeeping. **26 documents unchanged since October 2025.** Storage 24 GB free of ~30 GB (total 60 GB across 2 data nodes).

#### OpenSearch Domain Status

| Property | Value |
|----------|-------|
| Engine | OpenSearch 2.15 |
| Data nodes | 2x r6g.large.search |
| Master nodes | 3x m7g.large.search |
| Volume per node | 30 GB |
| Processing | False (stable) |

---

### 3.4 EC2 Instances

#### CPUUtilization (Monthly Averages)

| Month | isredify01 (i-06e...df4) | iluckydifyjump01 (i-02d...574) |
|-------|--------------------------|-------------------------------|
| 2025-09 | 0.30% | 26.27% |
| 2025-10 | 0.30% | 14.12% |
| 2025-11 | 0.31% | **0.27%** |
| 2025-12 | 0.34% | 0.29% |
| 2026-01 | 0.33% | 0.30% |
| 2026-02 | 0.33% | 0.30% |
| 2026-03 | 0.33% | 0.29% |
| 2026-04 | **0.33%** | **0.29%** |

isredify01 has been idle since launch (standalone Redis for Dify, replaced by ElastiCache).
iluckydifyjump01 had activity in Sep-Oct (Dify jump/bastion host), idle since Nov.

#### Network Traffic

Both instances: **<0.1 MB/day average** (negligible). iluckydifyjump01 shows periodic spikes to ~140 MB (likely automated backup/sync, not user activity).

#### Instance Status (2026-04-07)

| Property | isredify01 | iluckydifyjump01 |
|----------|-----------|------------------|
| ID | i-06e7301a6e3f28df4 | i-02d4ea4bbab7fd574 |
| Type | c6i.large | c6i.large |
| State | **running** | **running** |
| Private IP | 10.238.3.201 | 10.238.3.92 |
| Key Name | sre_aws2573 | sre_aws2573 |
| Launch Time | 2025-05-20 | 2025-09-18 |
| EBS | vol-00f8df5db42547f32 (DeleteOnTerm=True) | vol-00419fed999cc4e01 (DeleteOnTerm=True) |

Both EBS volumes have DeleteOnTermination=True — they will be automatically cleaned up when instances are terminated.

---

## 四、EKS Namespace Resource Inventory

**Cluster:** prod-worker01-eks-us
**Namespace:** baseservices-cloud-dify

### 4.1 Resource Summary

| Resource Type | Count | Details |
|---------------|-------|---------|
| Deployments | 19 | 5 old-dify + 5 new-dify + 9 milvus |
| StatefulSets | 6 | All Milvus/Pulsar (etcd, bookie, broker, proxy, recovery, zookeeper) |
| Pods | **46** | 5 old + 13 new + 20 milvus + 8 pulsar |
| Services | 25 | 5 old + 5 new + 14 milvus + 1 test (hello-world) |
| PVCs | 13 | 1 EFS (shared new-dify) + 12 EBS (milvus) |
| Ingresses | 2 | new-dify-ingress + milvus-attu |
| ConfigMaps | 13 | 6 dify + 6 milvus/pulsar + 1 kube-root-ca |
| Jobs | 0 | — |
| CronJobs | 0 | — |

### 4.2 Deployment Details

**Old Dify (Helm-managed, v1.3.1):**
| Deployment | Replicas | Created |
|-----------|----------|---------|
| dify-api | 1 | 2025-05-21 |
| dify-web | 1 | 2025-05-21 |
| dify-worker | 1 | 2025-05-21 |
| dify-sandbox | 1 | 2025-05-21 |
| dify-plugin-daemon | 1 | 2025-05-26 |

**New Dify (kubectl-applied, v1.8.1):**
| Deployment | Replicas | CPU Request | Memory Request | Created |
|-----------|----------|-------------|----------------|---------|
| new-dify-api | 2 | 250m | 512Mi | 2025-09-30 |
| new-dify-web | 2 | 125m | 256Mi | 2025-09-24 |
| new-dify-worker | 2 | 250m | 512Mi | 2025-09-26 |
| new-dify-sandbox | **6** | **1000m** | **2Gi** | 2025-09-23 |
| new-dify-plugin-daemon | 1 | 50m | 128Mi | 2025-09-30 |
| **Subtotal** | **13** | **7.175 vCPU** | **14.9 GiB** | |

**Milvus (Helm-managed, v2.2.13) — 9 Deployments + 6 StatefulSets:**
| Component | Pods | Type |
|-----------|------|------|
| milvus-datacoord | 2 | Deployment |
| milvus-datanode | 2 | Deployment |
| milvus-indexcoord | 2 | Deployment |
| milvus-indexnode | 2 | Deployment |
| milvus-proxy | 2 | Deployment |
| milvus-querycoord | 2 | Deployment |
| milvus-querynode | 2 | Deployment |
| milvus-rootcoord | 2 | Deployment |
| milvus-attu | 1 | Deployment |
| milvus-etcd | 3 | StatefulSet |
| milvus-pulsar-bookie | 3 | StatefulSet |
| milvus-pulsar-broker | 1 | StatefulSet |
| milvus-pulsar-proxy | 1 | StatefulSet |
| milvus-pulsar-zookeeper | 3 | StatefulSet |
| milvus-pulsar-recovery | 0 | StatefulSet |
| **Subtotal** | **28** | |

### 4.3 PVC Details

| # | Name | Provisioner | Capacity | Bound Node |
|---|------|-------------|----------|-----------|
| 1 | data-dify-39mdc | **efs.csi.aws.com** | 10Gi | Shared (RWX) |
| 2 | data-milvus-etcd-0 | ebs.csi.aws.com | — | ip-10-238-13-197 |
| 3 | data-milvus-etcd-1 | ebs.csi.aws.com | — | ip-10-238-12-91 |
| 4 | data-milvus-etcd-2 | ebs.csi.aws.com | — | ip-10-238-13-81 |
| 5 | pulsar-bookie-journal-0 | ebs.csi.aws.com | — | ip-10-238-13-99 |
| 6 | pulsar-bookie-journal-1 | ebs.csi.aws.com | — | ip-10-238-14-114 |
| 7 | pulsar-bookie-journal-2 | ebs.csi.aws.com | — | ip-10-238-15-252 |
| 8 | pulsar-bookie-ledgers-0 | ebs.csi.aws.com | — | ip-10-238-13-99 |
| 9 | pulsar-bookie-ledgers-1 | ebs.csi.aws.com | — | ip-10-238-14-114 |
| 10 | pulsar-bookie-ledgers-2 | ebs.csi.aws.com | — | ip-10-238-15-252 |
| 11 | pulsar-zookeeper-data-0 | ebs.csi.aws.com | — | ip-10-238-13-99 |
| 12 | pulsar-zookeeper-data-1 | ebs.csi.aws.com | — | ip-10-238-14-99 |
| 13 | pulsar-zookeeper-data-2 | ebs.csi.aws.com | — | ip-10-238-13-81 |

PVCs spread across **7 unique nodes** (statefulset scheduling).

### 4.4 Ingresses

| Name | Host | Backend |
|------|------|---------|
| new-dify-ingress | dify-console.luckincoffee.us | /console,/api,/v1 → new-dify-api:5001; / → new-dify-web:3000 |
| milvus-attu | — | Milvus UI (internal) |

### 4.5 Total Resource Footprint (New Dify only — requests from deployment specs)

| Component | CPU Request | Memory Request |
|-----------|-------------|----------------|
| new-dify-api (x2) | 500m | 1,024 Mi |
| new-dify-web (x2) | 250m | 512 Mi |
| new-dify-worker (x2) | 500m | 1,024 Mi |
| new-dify-sandbox (x6) | **6,000m** | **12,288 Mi** |
| new-dify-plugin-daemon (x1) | 50m | 128 Mi |
| **New Dify Subtotal** | **7,300m (7.3 vCPU)** | **14,976 Mi (14.6 GiB)** |

Note: Old Dify and Milvus resource requests not extracted in this collection — previous report estimated ~8.2 vCPU for Milvus. **Total namespace estimate: ~15.5 vCPU, ~30+ GiB.**

---

## 五、EKS Node Impact Analysis

### 5.1 Node Group Configuration

| Node Group | Desired | Min | Max | AMI | Instance Type | Status |
|-----------|---------|-----|-----|-----|---------------|--------|
| **eksnodegroupworker** | **13** | 1 | **13** | CUSTOM | m6i.8xlarge (inferred) | ACTIVE |
| nodegroup | 4 | 4 | 4 | CUSTOM | — | ACTIVE |

**Critical: eksnodegroupworker has Min=1, Max=13, Desired=13.** This means:
- No cluster autoscaler — desired = max (fixed size)
- **Can manually reduce desired from 13 to 12 or fewer** after removing Dify pods
- Each m6i.8xlarge node = 32 vCPU, 128 GiB RAM

### 5.2 Dify Pod Distribution

Dify PVCs are bound to **7 unique nodes** (from PVC volume.kubernetes.io/selected-node annotations):
- ip-10-238-12-91, ip-10-238-13-81, ip-10-238-13-99, ip-10-238-13-197
- ip-10-238-14-99, ip-10-238-14-114, ip-10-238-15-252

These nodes are **shared with other workloads** from other namespaces. Dify pods are not pinned — no nodeSelector, tolerations, or affinity rules found in deployment specs. They are scheduled by default scheduler across the general pool.

### 5.3 Node Freeing Potential

**Dify total: ~15.5 vCPU / ~30 GiB** across 13 nodes with 32 vCPU / 128 GiB each.
- Per node: ~416 vCPU total cluster capacity, ~1,664 GiB total memory
- Dify footprint: ~3.7% of cluster CPU, ~1.8% of cluster memory
- **Removing Dify likely frees enough capacity to reduce by 1 node** (15.5 vCPU ≈ 0.5 node equivalent)
- Node reduction from 13 → 12 saves **~$619/mo** (m6i.8xlarge: $1.2288/hr × 730h × 0.69 EDP)

### 5.4 Cluster Autoscaler

No cluster-autoscaler deployment found in kube-system (from previous report). Node scaling is **manual only**.

---

## 六、Milvus Vector Database Analysis

### 6.1 Component Inventory

| Component | Pods | Role |
|-----------|------|------|
| Milvus Deployments | 17 | datacoord(2), datanode(2), indexcoord(2), indexnode(2), proxy(2), querycoord(2), querynode(2), rootcoord(2), attu(1) |
| Pulsar StatefulSets | 8 | bookie(3), broker(1), proxy(1), zookeeper(3) |
| etcd StatefulSet | 3 | Metadata store |
| **Total Milvus** | **28 pods** | |

### 6.2 PVC / Storage

12 EBS PVCs for Milvus (etcd x3, bookie-journal x3, bookie-ledgers x3, zookeeper-data x3).
1 EFS PVC for Dify shared storage (data-dify-39mdc, 10Gi).

### 6.3 NLB (inf-milvus-service)

| Property | Value |
|----------|-------|
| Name | inf-milvus-service |
| Type | Network (internal) |
| State | active |
| DNS | inf-milvus-service-83c26a421d630082.elb.us-east-1.amazonaws.com |
| Target Groups | 2 (port 19530 + port 9091) |
| Healthy Targets | 4 (2 IPs × 2 ports) |

#### NLB Traffic (7-Month Trend)

| Month | ActiveFlowCount | ProcessedBytes |
|-------|----------------|----------------|
| 2025-09 | Avg=0.05, Max=2 | Avg=537, Max=985K |
| 2025-10 to 2026-04 | **0** | **0** |

**Zero traffic since October 2025 (6+ months).** The NLB targets are healthy (health checks pass) but no actual application traffic.

---

## 七、S3 Bucket Status

| Bucket | Size (MB) | Objects | Access |
|--------|-----------|---------|--------|
| lk-infra-dify | 25.18 | 81 | DENIED |
| lk-infra-dify-data | 24.54 | 501 | DENIED |
| lk-infra-dify-plugindaemon | 23.65 | 81 | DENIED |
| **Total** | **73.37** | **663** | |

**Previous (2026-03-25): 73 MB / 663 objects. Delta: +0.37 MB / 0 new objects.**

Growth is negligible — no application writes. S3 ListBucket still denied for databasecheck IAM user.

---

## 八、Cost Validation

### 8.1 Total AWS Spend by Service (March 2026)

| Service | March Cost |
|---------|-----------|
| Amazon RDS | $5,543.24 |
| EC2 - Other | $3,094.07 |
| Amazon EC2 - Compute | $2,973.17 |
| Amazon MSK | $2,314.80 |
| Amazon ElastiCache | $2,287.06 |
| Amazon OpenSearch | $2,138.85 |
| Amazon CloudWatch | $1,987.17 |
| Amazon DocumentDB | $1,009.33 |
| Others | <$3,000 combined |
| **Total** | **~$24,742** |

### 8.2 Dify Cost Estimation vs Actual

Dify-specific tagging search returned $0 — resources are **not tagged with "dify" in the Name tag** (they use AWS-generated names). Cost must be estimated from pricing.

| Resource | Spec | On-Demand/mo | After EDP (×0.69) |
|----------|------|-------------|-------------------|
| RDS dify-rw | db.r5.xlarge Multi-AZ | $739.60 | **$510.32** |
| RDS difynew-rw | db.r5.xlarge Multi-AZ | $739.60 | **$510.32** |
| Redis luckyus-redis-dify | cache.m6g.large ×2 | $217.54 | **$150.10** |
| Redis luckyus-difynew | cache.t4g.micro ×2 | $23.36 | **$16.12** |
| OpenSearch | 2×r6g.large + 3×m7g.large + 60GB | $546.79 | **$377.29** |
| EC2 isredify01 | c6i.large | $62.05 | **$42.81** |
| EC2 iluckydifyjump01 | c6i.large | $62.05 | **$42.81** |
| EBS (2×40GB gp3) | — | $6.40 | **$4.42** |
| S3 (3 buckets, ~73MB) | — | ~$2.15 | **~$1.48** |
| EKS compute (~15.5 vCPU) | Shared nodes | ~$700.80 | **~$483.55** |
| NLB (inf-milvus-service) | Network LB | ~$18.84 | **~$13.00** |
| EKS control plane (shared) | — | $73.00 | **$50.37** |
| **TOTAL** | | **$3,192** | **$2,203** |

**Estimated Dify monthly cost: ~$2,200/mo** (consistent with previous $2,190 estimate). This represents **~8.9% of total monthly AWS spend ($24,742).**

---

## 九、Permission Gap Matrix (Updated 2026-04-07)

| Operation | Status | Last Checked | Notes |
|-----------|--------|-------------|-------|
| ec2:StopInstances | **DENIED** | 2026-04-07 | Still blocked by IAM policy |
| ec2:TerminateInstances | **DENIED** | 2026-03-25 | — |
| iam:SimulatePrincipalPolicy | **DENIED** | 2026-04-07 | Explicit deny via luckin-deny-iam-write |
| s3:ListBucket | **DENIED** | 2026-04-07 | All 3 Dify buckets |
| s3:DeleteObject / DeleteBucket | **DENIED** (presumed) | — | Cannot test |
| route53:ListHostedZones | **DENIED** | 2026-04-07 | Cannot manage DNS records |
| rds:CreateDBSnapshot | **UNTESTED** | — | No dry-run, must test day-of |
| rds:DeleteDBInstance | **UNTESTED** | — | — |
| elasticache:CreateSnapshot | **UNTESTED** | — | 0 existing snapshots found |
| elasticache:DeleteReplicationGroup | **UNTESTED** | — | — |
| opensearch:DeleteDomain | **UNTESTED** | — | — |
| elbv2:DeleteLoadBalancer | **UNTESTED** | — | — |
| EKS read (via MCP) | **GRANTED** | 2026-04-07 | Full namespace visibility |
| EKS write (via MCP) | **UNTESTED** | — | Requires --allow-write on eks-server |
| Secrets (EKS) | **DENIED** | 2026-03-25 | RBAC 403 |

**Summary: EC2 stop/terminate and S3 access remain blocked. Must request IAM policy update from AWS admin before execution.**

---

## 十、Credential Exposure Scope

### 10.1 dify_w User Check

| PostgreSQL Server | dify_w Exists? |
|-------------------|---------------|
| aws-luckyus-dify-rw | Yes (Dify) |
| aws-luckyus-difynew-rw | Yes (Dify) |
| aws-luckyus-pgilkmap-rw | **No** |

**dify_w is Dify-only** — safe to drop during decommission.

### 10.2 Credentials in Deployment Annotations (7 plaintext secrets)

These are embedded in `kubectl.kubernetes.io/last-applied-configuration` annotations on new-dify-* deployments:

| Credential | Scope | Shared? |
|-----------|-------|---------|
| DB_PASSWORD (dify_w) | RDS PostgreSQL | Dify-only |
| REDIS_PASSWORD | luckyus-difynew cluster | Dify-only |
| SMTP_PASSWORD (dify@luckincoffee.us) | AWS WorkMail SMTP | **Potentially shared** — needs WorkMail admin check |
| SECRET_KEY | Dify app signing | Dify-only |
| OPENSEARCH_PASSWORD | luckyus-opensearch-dify | Dify-only |
| PLUGIN_DAEMON_KEY | Dify internal | Dify-only |
| CODE_EXECUTION_API_KEY | Dify sandbox | Dify-only |

**6 of 7 credentials are Dify-only** — will be invalidated automatically when resources are deleted.
**1 credential (SMTP/dify@luckincoffee.us)** may be shared with other WorkMail users — check with admin before deletion.

### 10.3 MCP Gateway Registered Servers

62 MySQL + 3 PostgreSQL + 75 Redis servers registered. Only 3 reference Dify:
- PostgreSQL: aws-luckyus-dify-rw, aws-luckyus-difynew-rw
- Redis: luckyus-redis-dify

**Note: luckyus-difynew (new Redis) is NOT in the MCP gateway.** No gateway config change needed for old Redis decommission.

---

## 十一、Three-Scenario Cost Model (6-Month Pause)

### Side-by-Side Comparison

| | Scenario A: Full Shutdown | Scenario B: Aggressive Reduction | Scenario C: Do Nothing |
|---|---|---|---|
| **Monthly savings** | ~$2,200 | ~$1,550 | $0 |
| **6-month savings** | **~$13,200** | ~$9,300 | **$0** |
| **Residual cost** | ~$4/mo (snapshots) | ~$650/mo (minimal RDS+Redis) | $2,200/mo |
| **Snapshot cost** | ~$4/mo (2 RDS + 2 Redis) | ~$2/mo (old instance only) | N/A |
| **Net 6-month savings** | **~$13,176** | ~$9,288 | **-$13,200 wasted** |
| **Restore time** | 2-4 hours | 30 min | 0 |
| **Risk** | Low (snapshots, calendar reminder) | Low | Zero |
| **Effort** | Medium (8-10 hrs) | Low (4-5 hrs) | Zero |
| **Data loss risk** | None (manual snapshots) | None (live RDS retained) | None |

### Scenario A: Full Shutdown (Recommended)

| Action | Savings/mo |
|--------|-----------|
| Delete OLD RDS (dify-rw) after snapshot | $510 |
| Delete NEW RDS (difynew-rw) after snapshot | $510 |
| Delete OLD Redis (luckyus-redis-dify) after snapshot | $150 |
| Delete NEW Redis (luckyus-difynew) after snapshot | $16 |
| Delete OpenSearch (luckyus-opensearch-dify) | $377 |
| Stop EC2 isredify01 | $43 |
| Stop EC2 iluckydifyjump01 | $43 |
| Delete NLB inf-milvus-service | $13 |
| Delete all K8s resources in namespace | Frees ~15.5 vCPU |
| Scale node group 13→12 | $619 |
| S3 keep (negligible) | -$1.48 |
| **Total** | **~$2,280/mo** |

Snapshot retention:
- 2 RDS manual snapshots (~6 GB total at $0.095/GB) = ~$0.57/mo
- 2 Redis manual snapshots (~4.8 GB + ~0.5 GB at $0.085/GB) = ~$0.45/mo
- **Total snapshot cost: ~$1/mo**

### Scenario B: Aggressive Reduction

| Action | Savings/mo |
|--------|-----------|
| Delete OLD Dify entirely (RDS + Redis + 5 pods) | $660 |
| Modify NEW RDS to db.t4g.micro Single-AZ | $490 (save from $510 → ~$20) |
| Delete OLD Redis (m6g.large), keep NEW (t4g.micro) | $150 |
| Delete OpenSearch entirely | $377 |
| Stop both EC2 instances | $86 |
| Delete NLB | $13 |
| Scale all Milvus to 0 replicas | Frees ~8 vCPU |
| **Total** | **~$1,776/mo** |
| **Residual** | ~$424/mo (minimal RDS + Redis + S3 + EKS overhead) |

### Scenario C: Do Nothing

**Cost: $2,200/mo × 6 = $13,200 wasted over 6 months.**

---

## 十二、Action Items

### Immediate (This Week)

1. **Share this report** with 彭啸 and 王东尧 for review
2. **Confirm Scenario A** (Full Shutdown) with CTO Michael
3. **Request IAM policy update** from AWS admin:
   - Need: ec2:StopInstances, ec2:TerminateInstances, s3:ListBucket, s3:DeleteObject
   - Need: rds:CreateDBSnapshot, rds:DeleteDBInstance (if not already granted)
   - Need: elasticache:CreateSnapshot, elasticache:DeleteReplicationGroup
4. **Request eks-server --allow-write** from MCP admin for namespace deletion

### Before Execution

5. **Disable API token** lei_Solution2-prod — notify litlei@amazon.com (token creator) courtesy
6. **Export Dify app DSL workflows** (14 apps) as backup from difynew-rw database
7. **Verify snapshot permissions** by creating a test snapshot (RDS + Redis)
8. **Check SMTP credential** (dify@luckincoffee.us) — confirm Dify-only via WorkMail admin

### During Execution (Estimated 8-10 hrs)

9. Create manual RDS snapshots (2 instances) — **name: dify-rw-final-20260407, difynew-rw-final-20260407**
10. Create Redis snapshots (2 clusters)
11. Scale old Dify deployments to 0 → Delete old Dify pods/services
12. Scale new Dify deployments to 0 → Delete new Dify pods/services
13. Delete Milvus + Pulsar + etcd (helm uninstall or kubectl delete)
14. Delete PVCs (12 EBS + 1 EFS)
15. Delete NLB inf-milvus-service
16. Stop EC2 instances (or terminate if permitted)
17. Delete RDS instances (skip final snapshot — already taken)
18. Delete ElastiCache clusters
19. Delete OpenSearch domain
20. Scale eksnodegroupworker: desired 13 → 12
21. Remove DNS record for dify-console.luckincoffee.us (requires Route53 access)

### Post-Execution

22. **Verify** all resources deleted via CloudWatch + Cost Explorer
23. **Set calendar reminder** (90 days) to renew or confirm snapshot retention
24. **Update Grafana dashboards** to remove Dify-related panels
25. **Remove MCP gateway entries**: aws-luckyus-dify-rw, aws-luckyus-difynew-rw, luckyus-redis-dify
26. **Document completion** in final decommission report

---

**Report generated: 2026-04-07 by David Zeng (DBA/Infrastructure)**
**Data sources: AWS CloudWatch (7-month), MCP postgres_query, redis_command, eks-server, Cost Explorer**
**All operations: READ-ONLY — no modifications made**
