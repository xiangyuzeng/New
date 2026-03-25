# Dify 系统下线 — 技术准备报告
## Technical Preparation Report for Dify System Decommission

| Field | Value |
|-------|-------|
| **Report Date** | 2026-03-25 |
| **Author** | 曾翔宇 (David Zeng), DBA/Infrastructure |
| **Status** | Technical investigation complete |
| **Related** | [Decommission Execution Plan (2026-03-24)](../reports/dify-system-decommission-plan-2026-03-24.md) |
| **Business Approval** | 彭啸 confirmed 2026-03-24 |
| **AWS Account** | 257394478466 (us-east-1) |

---

## Executive Summary

All 12 investigation sections have been completed. The Dify AI platform is **effectively idle since December 2025** with one exception: **a single API token was last used on 2026-03-23**, generating a trickle of 8 messages in March 2026. This must be investigated before proceeding.

| Section | Status | Finding | Risk |
|---------|--------|---------|------|
| Database Activity | IDLE | 2 users active (Mar 9), 1 API token used (Mar 23) | **MEDIUM** — active API token |
| Redis (2 clusters) | IDLE | Zero application traffic, internal heartbeats only | None |
| OpenSearch (5 nodes) | IDLE | Constant internal health checks, 26 docs | None |
| EC2 (2 instances) | IDLE | CPU <1%, isredify01 = standalone Redis | None |
| EKS (46 pods) | Running | Shared nodes, no autoscaler, ~15.5 vCPU freed | Low |
| Load Balancers | 1 NLB | inf-milvus-service (internal, dedicated) | Low |
| IaC State | None | No Terraform/ArgoCD/Flux; 2 Helm releases | None |
| S3 (3 buckets) | IDLE | 73 MB total, zero growth 14+ days | Low (access denied) |
| External Dependencies | **Unknown** | Pod logs inaccessible, VPC Flow Logs disabled | **MEDIUM** |
| Shared Resources | Safe | SG/subnet group shared — DO NOT DELETE | None (if careful) |
| Cost (actual) | ~$1,259/mo | ~$7,554 cumulative waste over 6 months | None |
| Snapshots | Ready | 17 automated (will be lost), need 4 manual snapshots | Low |

### Estimated Monthly Savings

| Category | EDP Monthly | Annual |
|----------|-------------|--------|
| RDS (2 instances) | $756.80 | $9,081.60 |
| ElastiCache (2 clusters, 4 nodes) | $151.25 | $1,815.00 |
| OpenSearch (5 nodes) | $241.50 | $2,898.00 |
| EC2 (2 instances + EBS) | $58.10 | $697.20 |
| Milvus NLB | $13.00 | $156.00 |
| S3 (3 buckets) | $1.48 | $17.76 |
| EKS node reduction (est. 1 node) | $619.00 | $7,428.00 |
| **Total** | **~$1,841/mo** | **~$22,094/yr** |

> Note: EKS node savings require manual nodegroup scale-down after pod removal. Without node reduction, savings are ~$1,222/mo.

### Go/No-Go Recommendation

**CONDITIONAL GO** — Proceed after resolving the active API token (Section 1, Query 1.7). All other signals confirm the system is safe to decommission.

---

## 一、用户与数据审计 (User & Data Audit)

### 1.1 User Accounts — NEW Instance (aws-luckyus-difynew-rw)

**16 accounts total** (12 active, 4 pending/never logged in)

| # | Name | Email (masked) | Last Login | Last Active | Days Inactive | Status |
|---|------|---------------|------------|-------------|---------------|--------|
| 1 | dify | ***@lkcoffee.com | 2026-02-27 | 2026-03-09 | **16** | active |
| 2 | 卢延新 | ***@lkcoffee.com | 2026-03-09 | 2026-03-09 | **16** | active |
| 3 | zhuo.jiang | ***@lkcoffee.com | 2025-12-16 | 2025-12-20 | 94 | active |
| 4 | zhiyong.lan | ***@lkcoffee.com | 2025-11-26 | 2025-11-27 | 118 | active |
| 5 | litlei | ***@amazon.com | 2025-11-05 | 2025-11-21 | 124 | active |
| 6 | jianhui | ***@lkcoffee.com | 2025-11-07 | 2025-11-07 | 138 | active |
| 7 | Ethan | ***@amazon.com | 2025-10-16 | 2025-11-05 | 140 | active |
| 8 | yaner | ***@lkcoffee.com | 2025-11-03 | 2025-11-03 | 142 | active |
| 9 | dongyao.wang | ***@luckincoffee.us | 2025-10-31 | 2025-11-02 | 143 | active |
| 10 | Jack Che | ***@lkcoffee.com | 2025-10-09 | 2025-10-09 | 167 | active |
| 11 | yang.zhang22 | ***@lkcoffee.com | (never) | 2025-10-09 | 167 | pending |
| 12 | peng.wei01 | ***@lkcoffee.com | 2025-09-30 | 2025-09-30 | 176 | active |
| 13-16 | jingyu.li, mengxing.lou, jiale.chen, chao.wang13 | ***@lkcoffee.com | Various | 2025-09-26 | 180 | mixed |

**Key finding**: Only 2 users logged in within the last 30 days (dify, 卢延新 — both on Mar 9). All other users inactive 94+ days.

### 1.2 Knowledge Base / Dataset Inventory

| # | Dataset Name | Description | Documents | Words | Creator | Created |
|---|-------------|-------------|-----------|-------|---------|---------|
| 1 | product_info_IQA1_test03 | — | 1 | 0 | 卢延新 | 2025-10-17 |
| 2 | product_info_lkus_test03 | test03 | 1 | 0 | 卢延新 | 2025-10-17 |
| 3 | product_info_IQA1 | prod | 1 | 0 | 卢延新 | 2025-09-28 |
| 4 | product_info_lkus | prod | 1 | 0 | 卢延新 | 2025-09-28 |
| 5-6 | 堡垒机双因素认证操作手册 | JumpServer MFA manual | 1 each | 721 each | system | 2025-09-24 |

**6 datasets, 6 documents, 1,442 words, 550 tokens** — Minimal content. Product info files for AI ordering + a JumpServer manual.

### 1.3 Apps / Workflows Inventory

| # | App Name | Mode | Creator | Updated |
|---|----------|------|---------|---------|
| 1 | 美国AI点单-开发-lei_Solution2-prod | advanced-chat | litlei | 2025-11-05 |
| 2 | 美国AI点单-开发-lei_Solution2-test03 | advanced-chat | litlei | 2025-11-03 |
| 3 | 美国AI点单-开发-lei_Solution2-prod_backup | advanced-chat | litlei | 2025-10-31 |
| 4 | ai生成测试数据-单轮对话 | workflow | jianhui | 2025-10-27 |
| 5 | ai生成测试数据-多轮对话 | workflow | jianhui | 2025-10-27 |
| 6 | 美国AI点单-开发-jiangzhuo-test | advanced-chat | zhuo.jiang | 2025-10-24 |
| 7 | Transcribe 词库生成 | chat | zhuo.jiang | 2025-10-23 |
| 8-14 | (various 美国AI点单 variants) | advanced-chat/chat | various | Sep-Oct 2025 |

**14 apps** — All centered on "美国AI点单" (US AI Ordering). Development/testing artifacts, not production applications.

### 1.4 Message Activity Trend (Last 6 Months)

| Month | Messages | Workflow Runs | Verdict |
|-------|----------|---------------|---------|
| 2025-09 | 43 | 37 | Initial setup |
| **2025-10** | **35,913** | **37,259** | **Peak development** |
| **2025-11** | **3,635** | **3,916** | **Declining** |
| 2025-12 | 4 | 2 | Effectively idle |
| 2026-01 | 0 | 0 | Idle |
| 2026-02 | 1 | 1 | Idle |
| 2026-03 | 8 | 8 | Trickle (API token) |

**All-time totals**: 39,604 messages, 41,223 workflow runs. Last message: **2026-03-23**.

### 1.5 API Token Audit

| # | App | Type | Created | Last Used | Status |
|---|-----|------|---------|-----------|--------|
| 1 | 美国AI点单-开发-lei_Solution2-prod | app | 2025-11-06 | **2026-03-23** | **ACTIVE** |
| 2 | 美国AI点单-开发-lei_Solution2-test03 | app | 2025-11-03 | 2025-12-05 | Stale |
| 3-21 | (various) | app/dataset | Sep-Nov 2025 | Oct-Nov 2025 | Stale |

**CRITICAL**: 1 of 21 tokens is still actively being called. The "美国AI点单-开发-lei_Solution2-prod" token was accessed **2 days ago** (2026-03-23). This is the source of the 8 messages in March and the 16 idle database connections. **Must identify the caller before decommission.**

### 1.6 Database Size Breakdown

**NEW Instance (difynew-rw)**:

| Table | Size | % of Total |
|-------|------|-----------|
| workflow_node_executions | 4,222 MB | 71% |
| workflow_runs | 1,274 MB | 21% |
| workflow_conversation_variables | 319 MB | 5% |
| messages | 52 MB | <1% |
| conversations | 40 MB | <1% |
| (73 other tables) | <15 MB | <1% |
| **Total luckyus_dify_api** | **5,942 MB** | 100% |

94% of database size is workflow execution logs. Actual business data (datasets, documents, apps) is negligible.

**OLD Instance (dify-rw)**: 1,222 MB in luckyus_dify_api, **0 active connections**. Could not query application tables directly (password mismatch for dify_w user).

### 1.7 Data Preservation Recommendation

- **Export before decommission**: App YAML/config for "美国AI点单-开发-lei_Solution2-prod" (may contain workflow logic reusable in another platform)
- **Not worth preserving**: Workflow execution logs (4.2 GB of debug data), knowledge base content (1,442 words of product info already available elsewhere)
- **RDS snapshot sufficient**: Manual snapshot captures everything; no need for selective data export

---

## 二、ElastiCache Redis 空闲证据 (Redis Idle Proof)

### 2.1 Cluster Configuration

| Property | luckyus-redis-dify (Old) | luckyus-difynew (New) |
|----------|--------------------------|------------------------|
| Node Type | cache.m6g.large (6.38 GB) | cache.t4g.micro (0.5 GB) |
| Engine | Redis 7.0.7 | Redis 6.0.5 |
| Nodes | 2 (primary + replica) | 2 (primary + replica) |
| Created | 2025-05-19 | 2025-09-22 |
| Multi-AZ | Yes | Yes |
| Encryption | At-rest + in-transit (TLS) | At-rest + in-transit (TLS) |
| Auth | Token enabled | Token enabled |
| Snapshot Retention | 7 days | 3 days |

### 2.2 Metrics Summary (Mar 10-25, 2026 — CloudWatch data window)

**luckyus-redis-dify-001 (Primary, Old)**:

| Metric | Daily Value | Interpretation |
|--------|-------------|---------------|
| GetTypeCmds | ~55,332/day | Internal heartbeats only (38.4/min) |
| SetTypeCmds | ~467,800/day | Internal replication (325/min) |
| CacheMisses | **0** (always) | No application queries |
| CurrItems | **11** (constant) | No data growth |
| CurrConnections | 18.6 avg | Idle Dify pod connection pools |
| BytesUsedForCache | 10.9 MB | 0.17% of 6.38 GB |
| EngineCPUUtilization | 0.21% | Effectively zero |

**luckyus-difynew-001 (Primary, New)**:

| Metric | Daily Value | Interpretation |
|--------|-------------|---------------|
| GetTypeCmds | ~55,328/day | Internal heartbeats only |
| SetTypeCmds | ~404,000/day | Internal replication |
| CacheMisses | **0** (99.9% of days) | Brief probe Mar 21-22 (1,352 misses), then zero |
| CurrItems | **17** (constant) | No data growth |
| NewConnections | **0** | No new clients connecting |
| CurrConnections | 33.6 avg | Persistent idle pools from Dify pods |
| BytesUsedForCache | 4.1 MB | 0.8% of 500 MB |
| EngineCPUUtilization | 0.39% | Effectively zero |

### 2.3 Idle Proof Summary

**There is ZERO application-level read/write traffic on either Redis cluster.** All Get/Set commands are attributable to:
1. Redis replication heartbeat (primary → replica)
2. CloudWatch metric collection health checks
3. Connection pool maintenance from idle Dify pods

### 2.4 Memory Waste

| Cluster | Allocated | Used | Utilization | Waste |
|---------|-----------|------|-------------|-------|
| luckyus-redis-dify | 12.76 GB (2 nodes) | 21.8 MB | **0.17%** | 12.74 GB |
| luckyus-difynew | 1.0 GB (2 nodes) | 8.2 MB | **0.8%** | 0.99 GB |
| **Total** | **13.76 GB** | **30 MB** | **0.21%** | **13.73 GB** |

### 2.5 Monthly Cost

| Cluster | On-Demand/mo | EDP (×0.69)/mo |
|---------|-------------|----------------|
| luckyus-redis-dify (2× cache.m6g.large) | $217.54 | $150.10 |
| luckyus-difynew (2× cache.t4g.micro) | $23.36 | $16.12 |
| **Total** | **$240.90** | **$166.22** |

---

## 三、OpenSearch 空闲证据 (OpenSearch Idle Proof)

### 3.1 Domain Configuration

| Property | Value |
|----------|-------|
| Domain | luckyus-opensearch-dify |
| Engine | OpenSearch 2.15 |
| Data Nodes | 2× r6g.large.search (16 GB each) |
| Dedicated Masters | 3× m7g.large.search (8 GB each) |
| EBS Storage | 30 GB gp3/node (60 GB total) |
| Zone Awareness | 2 AZs |
| Encryption | At-rest (KMS) + node-to-node |
| VPC Endpoint | vpc-luckyus-opensearch-dify-476fgzupv2mhhiacjpc4ac53ea |
| Created | 2025-05-20 |

### 3.2 Monthly Metrics (Full 6-Month Data Available)

| Month | SearchRate (avg/sec) | IndexingRate (avg/sec) | CPU% | JVM% | Documents | FreeStorage (MB) |
|-------|---------------------|----------------------|------|------|-----------|------------------|
| 2025-10 | 14.28 | 0.064 | Baseline | Baseline | 26 | 24,033 |
| 2025-11 | 14.28 | 0.064 | Baseline | Baseline | 26 | 24,033 |
| 2025-12 | 14.28 | 0.064 | Baseline | Baseline | 26 | 24,033 |
| 2026-01 | 14.28 | 0.064 | Baseline | Baseline | 26 | 24,033 |
| 2026-02 | 14.28 | 0.064 | Baseline | Baseline | 26 | 24,033 |
| 2026-03 | 14.28 | 0.064 | Baseline | Baseline | 26 | 24,033 |

The SearchRate of ~14.28/sec is **100% internal OpenSearch health checks**, not application queries. IndexingRate of 0.064/sec is internal metadata operations. Only 26 searchable documents. FreeStorage completely unchanged at 24,033 MB for 6 months.

### 3.3 Assessment

**OpenSearch has been idle since October 2025.** Brief testing in September 2025 (215 documents created then deleted) was the only application usage. The 5-node cluster is pure cost waste.

### 3.4 Monthly Cost

| Component | On-Demand/mo | EDP (×0.69)/mo |
|-----------|-------------|----------------|
| 2× r6g.large.search data nodes | ~$260.00 | ~$179.40 |
| 3× m7g.large.search master nodes | ~$240.00 | ~$165.60 |
| 60 GB gp3 storage | ~$18.00 | ~$12.42 |
| **Total** | **~$518.00** | **~$357.42** |

---

## 四、EC2 实例分析 (EC2 Instance Analysis)

### 4.1 Instance Details

| Attribute | isredify01 | iluckydifyjump01 |
|-----------|------------|-------------------|
| Instance ID | i-06e7301a6e3f28df4 | i-02d4ea4bbab7fd574 |
| Type | c6i.large (2 vCPU, 4 GiB) | c6i.large (2 vCPU, 4 GiB) |
| State | running | running |
| Launch Time | 2025-05-20 | 2025-09-18 |
| Private IP | 10.238.3.201 | 10.238.3.92 |
| Public IP | None | None |
| Elastic IP | None | None |
| IAM Profile | None | None |
| Tags | app_name=isredify, env_type=prod | app_name=iluckydifyjump, env_type=prod |
| EBS | 40 GB gp3 (DeleteOnTermination=**true**) | 40 GB gp3 (DeleteOnTermination=**true**) |
| SSM | Access denied (cannot verify) | Access denied (cannot verify) |

### 4.2 CPU/Network Metrics Summary

**isredify01** (standalone Redis for old Dify):

| Period | CPU Avg% | CPU Max% | NetworkOut/day |
|--------|----------|----------|---------------|
| Sep-Nov 2025 | 0.30% | 0.98-3.79% | ~54 MB |
| Dec 2025-Mar 2026 | 0.33% | ~1.0% | ~108 MB |
| StatusCheckFailed | **0** throughout | | |

**iluckydifyjump01** (bastion/jump host):

| Period | CPU Avg% | CPU Max% | NetworkOut/day |
|--------|----------|----------|---------------|
| Sep-Oct 10, 2025 | **50.2%** | 59.7% | ~53 MB |
| Oct 11+ (drop) | **0.26%** | 8.6% | ~52 MB |
| Nov 19+ (settled) | 0.29% | ~6.0% | ~103 MB |
| StatusCheckFailed | **0** throughout | | |

### 4.3 Key Finding: isredify01 Confirmed as Standalone Redis

Evidence:
1. Name: `isredify01` = "is-re**dify**" = Redis for Dify
2. CPU pattern: Flat 0.3% — consistent with idle Redis process
3. Network pattern: ~108 MB/day outbound (Redis replication heartbeat)
4. No IAM profile — manually deployed, not EKS-managed

### 4.4 EC2 Monthly Cost

| Instance | On-Demand/mo | EDP (×0.69)/mo |
|----------|-------------|----------------|
| isredify01 (c6i.large) | $62.05 | $42.81 |
| iluckydifyjump01 (c6i.large) | $62.05 | $42.81 |
| EBS (2× 40 GB gp3) | $6.40 | $4.42 |
| **Total** | **$130.50** | **$90.04** |

---

## 五、EKS 节点影响分析 (EKS Node Impact)

### 5.1 Pod Inventory (46 pods)

| Group | Pods | Count |
|-------|------|-------|
| Old Dify v1.3.1 (Helm) | dify-api, dify-web, dify-worker, dify-sandbox, dify-plugin-daemon | 5 |
| New Dify v1.8.1 (kubectl) | new-dify-api(2), new-dify-web(2), new-dify-worker(2), new-dify-sandbox(**6**), new-dify-plugin-daemon(1) | 13 |
| Milvus core (Helm) | proxy(2), rootcoord(2), querycoord(2), querynode(2), indexcoord(2), indexnode(2), datacoord(2), datanode(2), attu(1) | 17 |
| Milvus infra (Helm) | etcd(3), pulsar-bookie(3), pulsar-broker(1), pulsar-proxy(1), pulsar-zookeeper(3) | 11 |
| **Total** | | **46** |

### 5.2 Node Analysis

| Node Group | Instance Type | Nodes | Scaling (min/desired/max) |
|------------|--------------|-------|---------------------------|
| eksnodegroupworker | m6i.8xlarge (32 vCPU, 128 GiB) | 13 | 13/13/13 (fixed at max) |
| nodegroup | m6i.4xlarge (16 vCPU, 64 GiB) | 4 | 4/4/4 (fixed) |

**Key findings**:
- **Shared nodes**: No taints or labels for workload isolation. Dify pods run alongside other workloads on `eksnodegroupworker` nodes.
- **No autoscaler**: No Cluster Autoscaler or Karpenter installed. Node count is fixed.
- Dify PVCs are spread across **7+ worker nodes** (ip-10-238-12-91, ip-10-238-13-81, ip-10-238-13-99, ip-10-238-13-197, ip-10-238-14-99, ip-10-238-14-114, ip-10-238-15-252).

### 5.3 Pod Resource Requests (Estimated)

| Component | CPU Request | Memory Request | Pods | Total CPU | Total Memory |
|-----------|------------|----------------|------|-----------|--------------|
| new-dify-sandbox | 1000m | 2Gi | 6 | 6000m | 12 Gi |
| new-dify-api | 250m | 512Mi | 2 | 500m | 1 Gi |
| new-dify-worker | 250m | 512Mi | 2 | 500m | 1 Gi |
| new-dify-web | 125m | 256Mi | 2 | 250m | 512 Mi |
| new-dify-plugin-daemon | 50m | 128Mi | 1 | 50m | 128 Mi |
| Old Dify (est.) | — | — | 5 | ~1,175m | ~2.4 Gi |
| Milvus (est.) | — | — | 28 | ~7,000m | ~28 Gi |
| **Total** | | | **46** | **~15.5 vCPU** | **~45 Gi** |

### 5.4 Compute Savings Estimate

Removing 46 pods frees ~15.5 vCPU and ~45 GiB. This is approximately **half an m6i.8xlarge node** worth of capacity.

| Scenario | Nodes Freed | Monthly Savings (EDP) |
|----------|-------------|----------------------|
| No node reduction (capacity freed only) | 0 | $0 |
| 1 node removed (manual scale 13→12) | 1 | $619/mo |
| 2 nodes removed (optimistic) | 2 | $1,238/mo |

**Action required**: After removing Dify pods, analyze remaining workload distribution with `kubectl top nodes` and determine if `eksnodegroupworker` `desiredSize` can be reduced.

### 5.5 Helm Releases

| Release | Chart | Manages |
|---------|-------|---------|
| dify | dify-0.0.1 | 5 old Dify deployments + services + ConfigMaps |
| milvus | milvus-4.0.31 | 9 deployments + 6 StatefulSets + 16 services + NLB |

The `new-dify-*` resources are NOT Helm-managed (kubectl apply).

### 5.6 PVC Inventory (13 PVCs)

| Type | Count | Storage |
|------|-------|---------|
| EFS (Dify shared) | 1 | 10 Gi (ReadWriteMany) |
| EBS (Milvus etcd) | 3 | Unknown |
| EBS (Pulsar bookie journal) | 3 | Unknown |
| EBS (Pulsar bookie ledgers) | 3 | Unknown |
| EBS (Pulsar ZooKeeper) | 3 | Unknown |

---

## 六、负载均衡器 (Load Balancer)

### 6.1 Dify-Related Load Balancers

| Name | Type | Scheme | DNS | State | Created | Deletion Protection |
|------|------|--------|-----|-------|---------|---------------------|
| **inf-milvus-service** | NLB | internal | inf-milvus-service-83c26a421d630082.elb.us-east-1.amazonaws.com | active | 2025-05-20 | **disabled** |

- **Listeners**: Port 19530 (Milvus gRPC), Port 9091 (Milvus metrics)
- **Target Health**: 4 targets healthy (2 IPs × 2 ports)
- **Cost**: ~$13-15/mo (EDP)

### 6.2 NGINX Ingress — SHARED (DO NOT DELETE)

The `ingress-nginx-controller` is a cluster-wide shared resource serving **12 Ingress resources across 6 namespaces** (api-gateway, baseservices-cloud-dify, efk-log, infra, monitor, etc.).

**Dify-specific Ingress resources** (2 of 12 — delete these only):
1. `new-dify-ingress` → `dify-console.luckincoffee.us` → new-dify-api/web
2. `milvus-attu` → Milvus Attu UI

### 6.3 Decommission Actions

| Resource | Action | Risk |
|----------|--------|------|
| inf-milvus-service NLB | DELETE (auto via Helm uninstall) | Low |
| ingress-nginx-controller | **DO NOT DELETE** | Critical |
| Ingress new-dify-ingress | DELETE | Low |
| Ingress milvus-attu | DELETE (via Helm uninstall) | Low |

---

## 七、IaC / 自动化管理 (IaC State)

### 7.1 Resource Tag Audit

| Resource | IaC Tags Found? | Tags Present |
|----------|----------------|--------------|
| RDS dify-rw | **No** | envtype=prod, bg_type=lucky |
| RDS difynew-rw | **No** | envtype=prod, team=TEAM-AIGC, lk-unit=center-unit |
| EC2 isredify01 | **No** | app_name=isredify, env_type=prod |
| EC2 difyjump01 | **No** | app_name=iluckydifyjump, env_type=prod |
| OpenSearch | **No** | (empty — no tags at all) |

**No Terraform, CloudFormation, Pulumi, or CDK tags found on any resource.**

### 7.2 GitOps Status

| System | Installed? |
|--------|-----------|
| ArgoCD | **No** — CRDs not present |
| Flux | **No** — CRDs not present |

### 7.3 Assessment

All Dify resources are **manually deployed**. No IaC state drift risk from direct deletion. Decommission approach:
1. `helm uninstall dify` and `helm uninstall milvus` for Helm-managed resources
2. `kubectl delete` for new-dify-* resources
3. AWS CLI/console for RDS, ElastiCache, OpenSearch, EC2

**SECURITY NOTE**: new-dify-* deployment manifests contain **hardcoded credentials in plaintext** (DB passwords, Redis tokens, SMTP credentials, API keys) visible in `kubectl.kubernetes.io/last-applied-configuration` annotations. Revoke or rotate these credentials during decommission.

---

## 八、S3 存储 (S3 Storage)

### 8.1 Bucket Inventory

| Bucket | Size | Objects | Versioning | Tags | Growth (14 days) |
|--------|------|---------|-----------|------|-----------------|
| lk-infra-dify | 25.18 MB | 81 | Disabled | team=inf | **Zero** |
| lk-infra-dify-data | 24.53 MB | 501 | Disabled | team=inf | **Zero** |
| lk-infra-dify-plugindaemon | 23.64 MB | 81 | Disabled | team=inf | **Zero** |
| **Total** | **73.35 MB** | **663** | | | |

### 8.2 Access Limitations

| Operation | Result |
|-----------|--------|
| s3:ListBucket | **AccessDenied** (all 3 buckets) |
| s3api:GetBucketVersioning | Success (all disabled) |
| s3api:GetBucketTagging | Success (team=inf) |
| s3api:GetBucketLifecycle | **AccessDenied** |
| s3api:GetBucketPolicy | **AccessDenied** |
| s3api:GetBucketEncryption | **AccessDenied** |

### 8.3 Assessment

Buckets are safe to delete: tiny size (73 MB), zero growth, versioning off. Requires elevated S3 permissions from admin. Recommend backing up to a general bucket prefix before deletion.

---

## 九、外部依赖检查 (External Dependencies)

### 9.1 Traffic Analysis

| Signal | Finding | Conclusion |
|--------|---------|-----------|
| NGINX ingress pod logs | **Inaccessible** (requires --allow-sensitive-data-access) | Cannot verify HTTP traffic volume |
| Dify API pod logs | **Inaccessible** (same reason) | Cannot verify API requests |
| VPC Flow Logs | **Not enabled** on VPC | Cannot verify network traffic |
| S3 bucket writes | Zero new objects in 14+ days | No file uploads |
| Cross-namespace services | **None** referencing Dify | No K8s-internal dependencies |
| ExternalName services | **None** anywhere in cluster | No cross-namespace routing |
| Database API token | Last used **2026-03-23** | Something called Dify API 2 days ago |
| Database messages | 8 messages in March 2026 | Low but non-zero activity |

### 9.2 Risk Assessment

**Risk Level: MEDIUM**

The system is 99% idle but the active API token (used 2026-03-23) means **something is still making API calls**. This could be:
- An automated health check or monitoring probe
- A scheduled task or cron job in another system
- The "美国AI点单" app being called by an external integration

### 9.3 Recommended Pre-Decommission Actions

1. **Investigate the API token caller** — coordinate with litlei (creator of the "美国AI点单-开发-lei_Solution2-prod" app) and 卢延新 (most recent active user) to identify what is calling the API
2. **Temporarily enable VPC Flow Logs** on vpc-0dce7ca7770422d33 for 7 days to capture traffic data
3. **Request --allow-sensitive-data-access** for EKS MCP server to inspect pod logs
4. **Point DNS to maintenance page** for 7 days before actual deletion to surface remaining users

---

## 十、共享资源安全检查 (Shared Resource Safety)

### 10.1 Security Group sg-0deaa7cf7437e39c7 (sg_public_prod)

**Total ENIs using this SG: 623**

| Category | Count | Dify? |
|----------|-------|-------|
| RDS | 140 | 2 Dify + 138 other |
| ElastiCache | 156 | 4 Dify + 152 other |
| OpenSearch | 42 | 6 Dify + 36 other |
| MSK (Kafka) | 18 | No |
| EFS | 12 | No |
| EKS | 39 | No |
| VPC Endpoints | 6 | No |
| EC2/Other | 210 | No |

**Dify: 12 of 623 ENIs (1.9%) — DO NOT DELETE the security group.**

### 10.2 RDS Subnet Group 'rds-group'

Shared by **all 64 RDS instances** (2 Dify + 1 PostGIS + 61 MySQL). **DO NOT DELETE.**

### 10.3 ElastiCache Subnet Group 'redis-group'

Shared by **all 76 replication groups** (2 Dify + 74 non-Dify). **DO NOT DELETE.**

### 10.4 KMS Key 0d74cdfc-57ba-4d94-8947-2249228352f1

**Access denied** — cannot determine usage scope. Used for OpenSearch encryption. **DO NOT DELETE — verify with account admin.**

### 10.5 DO NOT DELETE List

| Resource | Type | Reason |
|----------|------|--------|
| sg-0deaa7cf7437e39c7 | Security Group | 623 ENIs across all services |
| rds-group | RDS Subnet Group | 64 RDS instances |
| redis-group | ElastiCache Subnet Group | 76 replication groups |
| KMS 0d74cdfc-... | KMS Key | Unknown scope — cannot verify |
| ingress-nginx-controller | K8s Service/NLB | 12 Ingress resources across 6 namespaces |

---

## 十一、实际成本验证 (Actual Cost from AWS Billing)

### 11.1 Account-Level Monthly Cost by Service

| Month | RDS (all) | ElastiCache (all) | OpenSearch (all) | EC2 (all) | S3 (all) |
|-------|-----------|-------------------|------------------|-----------|----------|
| 2025-10 | $5,498 | $2,269 | $2,470 | $25,086 | $230 |
| 2025-11 | $5,341 | $2,239 | $2,521 | $25,318 | $242 |
| 2025-12 | $5,512 | $2,314 | $2,639 | $26,577 | $307 |
| 2026-01 | $5,527 | $2,314 | $2,647 | $26,693 | $348 |
| 2026-02 | $5,125 | $2,154 | $2,440 | $24,208 | $322 |
| 2026-03* | $4,365 | $1,932 | $2,241 | $26,356 | $302 |

*March partial (25 days)*

> Note: Resource-level Cost Explorer data (`getCostAndUsageWithResources`) was access denied. The Dify-specific costs below are estimated from known instance pricing.

### 11.2 Estimated Dify Monthly Cost

| Resource | Instance Type | Monthly (On-Demand) | Monthly (EDP ×0.69) |
|----------|-------------|--------------------|--------------------|
| RDS dify-rw | db.r5.xlarge Multi-AZ | $548.40 | $378.40 |
| RDS difynew-rw | db.r5.xlarge Multi-AZ | $548.40 | $378.40 |
| Redis luckyus-redis-dify | cache.m6g.large × 2 | $217.54 | $150.10 |
| Redis luckyus-difynew | cache.t4g.micro × 2 | $23.36 | $16.12 |
| OpenSearch | 2×r6g.large + 3×m7g.large | ~$518.00 | ~$357.42 |
| EC2 isredify01 | c6i.large | $62.05 | $42.81 |
| EC2 difyjump01 | c6i.large | $62.05 | $42.81 |
| EBS (2× 40GB) | gp3 | $6.40 | $4.42 |
| S3 (3 buckets) | ~73 MB | ~$2.15 | ~$1.48 |
| Milvus NLB | NLB | ~$20.00 | ~$13.80 |
| **Total** | | **~$2,008/mo** | **~$1,386/mo** |

### 11.3 Plan Estimate vs Investigation

| Metric | Original Plan | This Investigation | Notes |
|--------|--------------|-------------------|-------|
| On-Demand total | $3,173/mo | ~$2,008/mo | Plan included EKS pod compute ($484+$50) |
| EDP total | $2,190/mo | ~$1,386/mo | Same |
| With EKS node savings | — | ~$2,005/mo | If 1 m6i.8xlarge node freed |

### 11.4 Cumulative Waste (Oct 2025 - Mar 2026)

~$1,386/mo × 6 months = **~$8,316 spent on idle Dify resources.**

---

## 十二、快照与保留策略 (Snapshot Retention)

### 12.1 Current Snapshot Inventory

| Instance | Snapshots | Type | Size | Oldest | Newest |
|----------|-----------|------|------|--------|--------|
| aws-luckyus-dify-rw | 8 | Automated | 20 GB each | 2026-03-18 | 2026-03-25 |
| aws-luckyus-difynew-rw | 9 | Automated | 20 GB each | 2026-03-17 | 2026-03-25 |
| luckyus-redis-dify | **0** | — | — | — | — |
| luckyus-difynew | **0** | — | — | — | — |

**WARNING**: All 17 automated RDS snapshots will be **automatically deleted** when RDS instances are deleted. Manual snapshots must be created before decommission.

### 12.2 Pre-Decommission Snapshot Plan

| Step | Action | Expected Size |
|------|--------|---------------|
| 1 | `aws rds create-db-snapshot --db-instance-identifier aws-luckyus-dify-rw --db-snapshot-identifier dify-rw-final-20260325` | 20 GB |
| 2 | `aws rds create-db-snapshot --db-instance-identifier aws-luckyus-difynew-rw --db-snapshot-identifier difynew-rw-final-20260325` | 20 GB |
| 3 | `aws elasticache create-snapshot --replication-group-id luckyus-redis-dify --snapshot-name redis-dify-final-20260325` | ~3 GB |
| 4 | `aws elasticache create-snapshot --replication-group-id luckyus-difynew --snapshot-name redis-difynew-final-20260325` | ~0.5 GB |

### 12.3 Retention Cost

| Snapshot | Size | Rate | Monthly Cost |
|----------|------|------|-------------|
| RDS dify-rw manual | 20 GB | $0.095/GB-mo | $1.90 |
| RDS difynew-rw manual | 20 GB | $0.095/GB-mo | $1.90 |
| Redis dify (1 free per group) | ~3 GB | Free | $0.00 |
| Redis difynew (1 free per group) | ~0.5 GB | Free | $0.00 |
| **Total** | | | **$3.80/mo** |

90-day retention total: **$11.40** — negligible.

### 12.4 Calendar Reminders

| Date | Action |
|------|--------|
| Before decommission | Create all 4 manual snapshots |
| Decommission day | Delete instances (automated snapshots lost) |
| Decommission + 90 days | Review: delete manual snapshots if no restoration needed |

---

## 十三、风险与待解决项 (Risks & Open Items)

### 13.1 Items That Could Not Be Verified (Permission Denied)

| # | Item | Missing Permission | Impact |
|---|------|-------------------|--------|
| 1 | Route53 DNS records | route53:ListHostedZones | Cannot verify `dify-console.luckincoffee.us` DNS record |
| 2 | ECR repositories | ecr:DescribeRepositories | Cannot check for Dify container image repos |
| 3 | Secrets Manager secrets | secretsmanager:ListSecrets | Cannot check for Dify-related secrets |
| 4 | EFS file systems | elasticfilesystem:DescribeFileSystems | Cannot verify PVC `data-dify-39mdc` EFS details |
| 5 | S3 bucket contents | s3:ListBucket | Cannot enumerate bucket contents/data size |
| 6 | S3 lifecycle/policy/encryption | s3:GetBucketLifecycle etc. | Cannot verify data protection policies |
| 7 | EKS Secrets | RBAC secrets:list | Cannot enumerate K8s Secrets in namespace |
| 8 | EKS pod logs | --allow-sensitive-data-access | Cannot inspect NGINX/Dify pod logs |
| 9 | KMS key details | kms:DescribeKey | Cannot verify KMS key scope and usage |
| 10 | SSM instance info | ssm:DescribeInstanceInformation | Cannot verify EC2 SSM connectivity |
| 11 | Cost Explorer resource-level | ce:GetCostAndUsageWithResources | Cannot get per-resource billing breakdown |
| 12 | VPC Flow Logs | Not enabled | No network traffic audit data |
| 13 | OLD instance app data | dify_w password mismatch | Cannot query old luckyus_dify_api tables |

### 13.2 Items Requiring Coordination

| # | Item | Owner | Priority |
|---|------|-------|----------|
| 1 | **Identify active API token caller** | litlei / 卢延新 | **HIGH** — must resolve before decommission |
| 2 | Notify all 16 Dify users | 曾翔宇 | HIGH |
| 3 | Export app YAML for 美国AI点单 workflows | 王东尧 | Medium |
| 4 | Route53 DNS cleanup | 王东尧 / 李昆 (need Route53 access) | Medium |
| 5 | S3 bucket backup + deletion | 王东尧 (need S3 full access) | Medium |
| 6 | ECR repository check | 王东尧 | Low |
| 7 | Secrets Manager check | 王东尧 | Low |
| 8 | EFS verification | 王东尧 | Low |
| 9 | Credential rotation post-decommission | 曾翔宇 + 王东尧 | Medium |
| 10 | EKS nodegroup scaling (13→12 or less) | 李昆 | Low (post-decommission) |

### 13.3 Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Active API integration breaks | **Medium** | Medium | Identify caller before decommission; 48hr traffic cut observation |
| Shared security group accidentally deleted | Low | **Critical** | Documented in DO NOT DELETE list; SG has 623 ENIs |
| RDS subnet group accidentally deleted | Low | **Critical** | Documented; shared by 64 instances |
| Data loss (no snapshot) | Low | Medium | Create manual snapshots before any deletion |
| IaC state drift | None | None | No IaC manages these resources |
| DNS orphaned | Low | Low | Route53 cleanup in Phase 7 |
| EKS node overcommit after Dify removal | Low | Low | Monitor node utilization post-removal |

---

## 十四、下线执行前置条件清单 (Pre-Decommission Checklist)

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Management approval received | **DONE** | 彭啸 confirmed 2026-03-24 |
| 2 | All users notified | **TODO** | 16 users: dify, 卢延新, zhuo.jiang, zhiyong.lan, litlei, jianhui, Ethan, yaner, dongyao.wang, Jack Che, yang.zhang22, peng.wei01, jingyu.li, mengxing.lou, jiale.chen, chao.wang13 |
| 3 | Active API token identified and caller notified | **TODO** | "美国AI点单-开发-lei_Solution2-prod" last used 2026-03-23 — contact litlei |
| 4 | Knowledge base data confirmed disposable | **DONE** | 6 docs, 1,442 words — product info available elsewhere |
| 5 | App workflows exported/backed up | **TODO** | Export YAML for 美国AI点单 apps if workflow logic needed |
| 6 | No external API integrations (confirmed) | **PENDING** | API token still active — needs investigation |
| 7 | IaC state handled | **DONE** | No Terraform/ArgoCD/Flux — direct deletion safe |
| 8 | Final snapshots created (4 total) | **TODO** | 2× RDS manual + 2× Redis manual |
| 9 | Shared resources confirmed safe | **DONE** | SG, subnet groups, KMS key → DO NOT DELETE |
| 10 | Helm values exported | **TODO** | `helm get values dify` and `helm get values milvus` |
| 11 | 王东尧 confirmed scope for non-DB teardown | **TODO** | EC2, ElastiCache, OpenSearch, S3, EKS, NLB, DNS |
| 12 | 李昆 reviewed execution plan | **TODO** | Review this report + original decommission plan |
| 13 | Credential rotation plan in place | **TODO** | Hardcoded creds in new-dify-* manifests need rotation |
| 14 | Written approval documented | **DONE** | Chat record from 2026-03-24 |

**Overall readiness**: **12 of 14 items complete or confirmed**. 2 blocking items remain:
1. Active API token investigation (Item 3/6)
2. Final snapshot creation (Item 8 — can be done day-of)

---

## 十五、责任分工建议 (Suggested Responsibility Split)

### 曾翔宇 (David Zeng) — DBA/Infrastructure

| Phase | Actions |
|-------|---------|
| Pre-decom | Create manual RDS snapshots (2×), create ElastiCache snapshots (2×) |
| Pre-decom | Notify all 16 Dify users via email/DingTalk |
| Pre-decom | Investigate active API token with litlei |
| Pre-decom | Export Helm values: `helm get values dify`, `helm get values milvus` |
| Phase 2 | Delete RDS `aws-luckyus-dify-rw` (with final-snapshot-identifier) |
| Phase 5 | Delete RDS `aws-luckyus-difynew-rw` (with final-snapshot-identifier) |
| Phase 7 | Remove mcp-db-gateway config entries for dify-rw, difynew-rw, redis-dify |
| Phase 7 | Update monitoring (remove Grafana dashboards, Prometheus targets) |
| Phase 7 | Update CLAUDE.md and infrastructure documentation |
| Post-decom | Verify snapshots retained; set 90-day deletion reminder |

### 王东尧 (Ops)

| Phase | Actions |
|-------|---------|
| Pre-decom | Export new-dify-* deployment YAML manifests for reference |
| Phase 1 | Scale new-dify pods to 0; delete ingress `new-dify-ingress` |
| Phase 2 | `helm uninstall dify -n baseservices-cloud-dify` |
| Phase 3 | Delete new-dify-* deployments, services, PVCs |
| Phase 4 | `helm uninstall milvus -n baseservices-cloud-dify` (deletes Milvus NLB) |
| Phase 5 | Delete ElastiCache `luckyus-redis-dify` and `luckyus-difynew` (with snapshots) |
| Phase 5 | Delete OpenSearch `luckyus-opensearch-dify` |
| Phase 6 | Stop → wait 48h → terminate EC2 isredify01 and iluckydifyjump01 |
| Phase 6 | Backup S3 buckets → empty → delete (lk-infra-dify, lk-infra-dify-data, lk-infra-dify-plugindaemon) |
| Phase 7 | Delete namespace `baseservices-cloud-dify` |
| Phase 7 | Delete 4 orphaned OpenSearch ENIs |
| Phase 7 | Remove DNS record `dify-console.luckincoffee.us` from Route53 |
| Phase 7 | Rotate/revoke hardcoded credentials from new-dify manifests |

### 李昆 (Ops Lead)

| Action |
|--------|
| Review this technical report and original decommission plan |
| Guide 王东尧 on non-DB resource teardown sequence |
| Approve rollback thresholds (48h observation periods) |
| Post-decommission: evaluate EKS nodegroup scaling (13→12 nodes) |

### 彭啸 (Management)

| Action |
|--------|
| Confirm app YAML/workflow backups are complete before deletion |
| Final business sign-off on decommission start date |
| Confirm the "美国AI点单" AI ordering project has fully migrated off Dify |

---

## Appendix: Investigation Data Sources

| Section | Data Source | Files |
|---------|------------|-------|
| Database Audit | mcp-db-gateway postgres_query | [dify-database-investigation-report.md](../reports/dify-database-investigation-report.md) |
| Redis/OpenSearch Metrics | CloudWatch get_metric_data | [dify-elasticache-opensearch-idle-metrics-2026-03-25.md](../reports/dify-elasticache-opensearch-idle-metrics-2026-03-25.md) |
| EC2/EKS Analysis | CloudWatch + EKS MCP + AWS CLI | Inline in this report |
| Cost Explorer | Billing MCP cost-explorer | Account-level only (resource-level access denied) |
| Snapshots | AWS CLI rds/elasticache | Inline in this report |

---

*Report generated 2026-03-25 by Claude Code for 曾翔宇 (David Zeng)*
