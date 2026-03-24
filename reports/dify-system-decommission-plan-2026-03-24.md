# Dify System Decommission Plan

**Date**: 2026-03-24
**Author**: David Zeng (DBA/Infrastructure)
**Status**: Draft
**System**: Dify AI Platform (Luckin Coffee USA)
**Objective**: Complete decommission of Dify system and all associated resources

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Complete Resource Inventory](#2-complete-resource-inventory)
3. [Resource Dependency Map](#3-resource-dependency-map)
4. [Cost Impact Analysis](#4-cost-impact-analysis)
5. [Pre-Decommission Checklist](#5-pre-decommission-checklist)
6. [Decommission Execution Plan](#6-decommission-execution-plan)
7. [Rollback Plan](#7-rollback-plan)
8. [Post-Decommission Verification](#8-post-decommission-verification)
9. [Pending Items (Insufficient Permissions)](#9-pending-items-insufficient-permissions)

---

## 1. System Overview

Dify is an open-source LLM application development platform deployed for Luckin Coffee USA's AI initiatives. The system consists of **two parallel deployments**:

| Generation | Version | Status | Created | Notes |
|------------|---------|--------|---------|-------|
| Original (dify) | v1.3.1 | **Idle** — 1 active DB connection | 2025-05-19 | Helm-managed, no traffic |
| New (difynew) | v1.8.1 | **Active** — 16 DB connections | 2025-09-22 | kubectl-applied, serving production traffic |

**Access URL**: `https://dify-console.luckincoffee.us`

Both generations are deployed in EKS cluster `prod-worker01-eks-us`, namespace `baseservices-cloud-dify`, alongside a full **Milvus v2.2.13** vector database cluster.

---

## 2. Complete Resource Inventory

### 2.1 RDS PostgreSQL (2 Instances)

| # | Instance Identifier | Instance Class | Engine | Storage | Multi-AZ | Endpoint | DB Size | Active Conns | Status |
|---|---------------------|---------------|--------|---------|----------|----------|---------|-------------|--------|
| 1 | `aws-luckyus-dify-rw` | db.r5.xlarge | PostgreSQL 16.8 | 20 GB gp3 | Yes | `aws-luckyus-dify-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com:5432` | 1.2 GB | 1 (idle) | Old — decommission first |
| 2 | `aws-luckyus-difynew-rw` | db.r5.xlarge | PostgreSQL 16.10 | 20 GB gp3 | Yes | `aws-luckyus-difynew-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com:5432` | 5.9 GB | 16 (active) | Current production |

**RDS Configuration Details:**

| Parameter | aws-luckyus-dify-rw | aws-luckyus-difynew-rw |
|-----------|---------------------|------------------------|
| Subnet Group | rds-group | rds-group |
| Security Group | sg-0deaa7cf7437e39c7 (sg_public_prod) | sg-0deaa7cf7437e39c7 (sg_public_prod) |
| Parameter Group | default.postgres16 | default.postgres16 |
| Backup Retention | 7 days | 7 days |
| Backup Window | 05:05-05:35 UTC | 06:31-07:01 UTC |
| Maintenance Window | Thu 08:11-08:41 UTC | Fri 07:44-08:14 UTC |
| Storage Encrypted | Yes | Yes |
| Auto Minor Upgrade | Yes | No |

**Databases on each instance:**

| Database | dify-rw Size | difynew-rw Size |
|----------|-------------|-----------------|
| luckyus_dify_api | 1,222 MB | 5,942 MB |
| luckyus_dify_plugin | 8,828 KB | 8,524 KB |
| postgres | 7,724 KB | 7,724 KB |

---

### 2.2 ElastiCache Redis (2 Replication Groups, 4 Nodes)

| # | Replication Group | Node Type | Engine | Nodes | Primary Endpoint | Status |
|---|-------------------|-----------|--------|-------|------------------|--------|
| 1 | `luckyus-redis-dify` | cache.m6g.large | Redis 7.0.7 | 2 (primary + replica) | `master.luckyus-redis-dify.vyllrs.use1.cache.amazonaws.com:6379` | Old — 11 keys only |
| 2 | `luckyus-difynew` | cache.t4g.micro | Redis 6.0.5 | 2 (primary + replica) | `master.luckyus-difynew.vyllrs.use1.cache.amazonaws.com:6379` | Current production |

**ElastiCache Configuration Details:**

| Parameter | luckyus-redis-dify | luckyus-difynew |
|-----------|-------------------|-----------------|
| Member Nodes | luckyus-redis-dify-001 (primary, us-east-1b) | luckyus-difynew-001 (primary, us-east-1b) |
| | luckyus-redis-dify-002 (replica, us-east-1a) | luckyus-difynew-002 (replica, us-east-1a) |
| Auto Failover | Enabled | Enabled |
| Multi-AZ | Enabled | Enabled |
| Encryption Transit | Required (TLS) | Required (TLS) |
| Encryption At-Rest | Enabled | Enabled |
| Auth Token | Enabled | Enabled |
| Snapshot Retention | 7 days | 3 days |
| Snapshot Window | 06:30-07:30 UTC | 06:00-07:00 UTC |
| Created | 2025-05-19 | 2025-09-22 |
| Memory Used | 10.4 MB / 4.79 GB (0.21%) | — |
| Total Keys | 11 (db0: 3, db1: 8) | — |
| Log Delivery | ERROR (access denied for `redis-log`) | None configured |

---

### 2.3 OpenSearch (1 Domain, 5 Nodes)

| # | Domain Name | Engine | Data Nodes | Master Nodes | Storage |
|---|-------------|--------|------------|--------------|---------|
| 1 | `luckyus-opensearch-dify` | OpenSearch 2.15 | 2x r6g.large.search | 3x m7g.large.search | 30 GB gp3/node (3000 IOPS) |

**OpenSearch Configuration Details:**

| Parameter | Value |
|-----------|-------|
| Domain ID | 257394478466/luckyus-opensearch-dify |
| VPC | vpc-0dce7ca7770422d33 |
| Subnets | subnet-01608eef3ea13c7d3 (us-east-1a), subnet-0acd412a7bc5ebc55 (us-east-1b) |
| Security Group | sg-0deaa7cf7437e39c7 (sg_public_prod) |
| Zone Awareness | Enabled (2 AZs) |
| Encryption At-Rest | Enabled (KMS key: 0d74cdfc-57ba-4d94-8947-2249228352f1) |
| Node-to-Node Encryption | Enabled |
| VPC Endpoint | `vpc-luckyus-opensearch-dify-476fgzupv2mhhiacjpc4ac53ea.us-east-1.es.amazonaws.com` |
| Purpose | Dify vector store / knowledge base search |

---

### 2.4 EC2 Instances (2 Instances)

| # | Instance ID | Name | Type | State | Private IP | Subnet | VPC | Launched |
|---|-------------|------|------|-------|------------|--------|-----|----------|
| 1 | `i-06e7301a6e3f28df4` | isredify01-prod-usa-aws | c6i.large | running | 10.238.3.201 | subnet-0828db1b483e7e580 | vpc-0dce7ca7770422d33 | 2025-05-20 |
| 2 | `i-02d4ea4bbab7fd574` | iluckydifyjump01-prod-usa-aws | c6i.large | running | 10.238.3.92 | subnet-0828db1b483e7e580 | vpc-0dce7ca7770422d33 | 2025-09-18 |

**EC2 Configuration Details:**

| Parameter | isredify01 | iluckydifyjump01 |
|-----------|-----------|------------------|
| Security Group | sg-0deaa7cf7437e39c7 (sg_public_prod) | sg-0deaa7cf7437e39c7 (sg_public_prod) |
| Purpose | Dify Redis/support server | Dify jump/bastion host |

---

### 2.5 EBS Volumes (2 Volumes)

| # | Volume ID | Size | Type | IOPS | Device | Attached To |
|---|-----------|------|------|------|--------|-------------|
| 1 | `vol-00f8df5db42547f32` | 40 GB | gp3 | 3000 | /dev/xvda | i-06e7301a6e3f28df4 (isredify01) |
| 2 | `vol-00419fed999cc4e01` | 40 GB | gp3 | 3000 | /dev/xvda | i-02d4ea4bbab7fd574 (iluckydifyjump01) |

---

### 2.6 S3 Buckets (3 Buckets)

| # | Bucket Name | Created | Purpose |
|---|-------------|---------|---------|
| 1 | `lk-infra-dify` | 2025-05-19 | Dify main storage |
| 2 | `lk-infra-dify-data` | 2025-05-21 | Dify data/knowledge base files |
| 3 | `lk-infra-dify-plugindaemon` | 2025-05-27 | Dify plugin daemon artifacts |

> **Note**: Bucket contents cannot be enumerated — `databasecheck` IAM user lacks `s3:ListBucket` permission. Data size TBD.

---

### 2.7 Elastic Network Interfaces (10 ENIs)

| # | ENI ID | Description | Private IP | Status |
|---|--------|-------------|------------|--------|
| 1 | `eni-0fa215efb45ac815f` | ES luckyus-opensearch-dify | 10.238.9.63 | in-use |
| 2 | `eni-0f9ea6d3cf0d9f254` | ES luckyus-opensearch-dify | 10.238.4.187 | in-use |
| 3 | `eni-0d623c6205c24d3a7` | ES luckyus-opensearch-dify | 10.238.9.89 | available (orphaned) |
| 4 | `eni-0ba40d95964577c62` | ES luckyus-opensearch-dify | 10.238.9.137 | available (orphaned) |
| 5 | `eni-0d7735e22a081705c` | ES luckyus-opensearch-dify | 10.238.4.167 | available (orphaned) |
| 6 | `eni-0f2adc1cdec3cab8a` | ES luckyus-opensearch-dify | 10.238.4.154 | available (orphaned) |
| 7 | `eni-047d8532b08196faa` | ElastiCache luckyus-redis-dify-001 | 10.238.9.8 | in-use |
| 8 | `eni-0dac9e0c33ca1f318` | ElastiCache luckyus-redis-dify-002 | 10.238.4.169 | in-use |
| 9 | `eni-0689080b85179b84d` | ElastiCache luckyus-difynew-001 | 10.238.9.176 | in-use |
| 10 | `eni-0914ee82dcec533dd` | ElastiCache luckyus-difynew-002 | 10.238.4.197 | in-use |

> 4 orphaned ENIs (#3-#6) from OpenSearch scaling events — clean up after domain deletion.

---

### 2.8 EKS Resources (Cluster: `prod-worker01-eks-us`, Namespace: `baseservices-cloud-dify`)

#### 2.8.1 Deployments (19)

**Old Dify v1.3.1 (Helm-managed, chart dify-0.0.1):**

| # | Deployment | Component | Replicas | Created | Revision |
|---|------------|-----------|----------|---------|----------|
| 1 | `dify-api` | API server | 1 | 2025-05-21 | 45 |
| 2 | `dify-web` | Web frontend | 1 | 2025-05-21 | 11 |
| 3 | `dify-worker` | Celery worker | 1 | 2025-05-21 | 31 |
| 4 | `dify-sandbox` | Code sandbox | 1 | 2025-05-21 | 3 |
| 5 | `dify-plugin-daemon` | Plugin daemon | 1 | 2025-05-26 | 7 |

**New Dify v1.8.1 (kubectl-applied):**

| # | Deployment | Component | Replicas | Image | Created |
|---|------------|-----------|----------|-------|---------|
| 6 | `new-dify-api` | API server | 2 | langgenius/dify-api:1.8.1 | 2025-09-30 |
| 7 | `new-dify-web` | Web frontend | 2 | langgenius/dify-web:1.8.1 | 2025-09-24 |
| 8 | `new-dify-worker` | Celery worker | 2 | langgenius/dify-api:1.8.1 | 2025-09-26 |
| 9 | `new-dify-sandbox` | Code sandbox | 6 | langgenius/dify-sandbox:0.2.12 | 2025-09-23 |
| 10 | `new-dify-plugin-daemon` | Plugin daemon | 1 | langgenius/dify-plugin-daemon:0.2.0-local | 2025-09-30 |

**Milvus v2.2.13 (Helm-managed, chart milvus-4.0.31):**

| # | Deployment | Component | Created |
|---|------------|-----------|---------|
| 11 | `milvus-proxy` | Proxy gateway | 2025-05-20 |
| 12 | `milvus-rootcoord` | Root coordinator | 2025-05-20 |
| 13 | `milvus-querycoord` | Query coordinator | 2025-05-20 |
| 14 | `milvus-querynode` | Query node | 2025-05-20 |
| 15 | `milvus-indexcoord` | Index coordinator | 2025-05-20 |
| 16 | `milvus-indexnode` | Index node | 2025-05-20 |
| 17 | `milvus-datacoord` | Data coordinator | 2025-05-20 |
| 18 | `milvus-datanode` | Data node | 2025-05-20 |
| 19 | `milvus-attu` | Attu Web UI | 2025-05-20 |

#### 2.8.2 StatefulSets (6)

| # | StatefulSet | Component | Pods | Chart |
|---|-------------|-----------|------|-------|
| 1 | `milvus-etcd` | etcd cluster | 3 | etcd-6.3.3 |
| 2 | `milvus-pulsar-bookie` | Pulsar bookie | 3 | pulsar-2.7.8 |
| 3 | `milvus-pulsar-broker` | Pulsar broker | 1 | pulsar-2.7.8 |
| 4 | `milvus-pulsar-proxy` | Pulsar proxy | 1 | pulsar-2.7.8 |
| 5 | `milvus-pulsar-recovery` | Pulsar recovery | 0 | pulsar-2.7.8 |
| 6 | `milvus-pulsar-zookeeper` | ZooKeeper | 3 | pulsar-2.7.8 |

#### 2.8.3 Services (25)

**Dify Services (9):**

| # | Service | Port | Type |
|---|---------|------|------|
| 1 | `dify-api` | 5001/TCP | ClusterIP |
| 2 | `dify-web` | — | ClusterIP |
| 3 | `dify-sandbox` | — | ClusterIP |
| 4 | `dify-plugin-daemon` | 5002/TCP | ClusterIP |
| 5 | `new-dify-api` | 5001/TCP | ClusterIP |
| 6 | `new-dify-web` | 3000/TCP | ClusterIP |
| 7 | `new-dify-sandbox` | 8194/TCP | ClusterIP |
| 8 | `new-dify-plugin-daemon` | 5002/TCP | ClusterIP |
| 9 | `hello-world` | — | ClusterIP |

**Milvus Services (16):**

| # | Service | Type | Notes |
|---|---------|------|-------|
| 10 | `milvus` | **LoadBalancer** | Internal NLB: `inf-milvus-service` |
| 11 | `milvus-attu` | ClusterIP | Attu Web UI |
| 12 | `milvus-datacoord` | ClusterIP | |
| 13 | `milvus-datanode` | ClusterIP | |
| 14 | `milvus-etcd` | ClusterIP | |
| 15 | `milvus-etcd-headless` | Headless | |
| 16 | `milvus-indexcoord` | ClusterIP | |
| 17 | `milvus-indexnode` | ClusterIP | |
| 18 | `milvus-querycoord` | ClusterIP | |
| 19 | `milvus-querynode` | ClusterIP | |
| 20 | `milvus-rootcoord` | ClusterIP | |
| 21 | `milvus-pulsar-bookie` | ClusterIP | |
| 22 | `milvus-pulsar-broker` | ClusterIP | |
| 23 | `milvus-pulsar-proxy` | ClusterIP | |
| 24 | `milvus-pulsar-recovery` | ClusterIP | |
| 25 | `milvus-pulsar-zookeeper` | Headless | |

#### 2.8.4 Ingresses (2)

| # | Ingress | Host | Paths | Ingress Class |
|---|---------|------|-------|---------------|
| 1 | `new-dify-ingress` | `dify-console.luckincoffee.us` | `/console` -> new-dify-api:5001, `/api` -> new-dify-api:5001, `/v1` -> new-dify-api:5001, `/` -> new-dify-web:3000 | nginx |
| 2 | `milvus-attu` | — | Milvus Attu UI | nginx |

#### 2.8.5 ConfigMaps (13)

| # | ConfigMap | Managed By |
|---|-----------|------------|
| 1 | `dify-api` | Helm (dify) |
| 2 | `dify-plugin-daemon` | Helm (dify) |
| 3 | `dify-proxy` | Helm (dify) |
| 4 | `dify-sandbox` | Helm (dify) |
| 5 | `dify-web` | Helm (dify) |
| 6 | `dify-worker` | Helm (dify) |
| 7 | `kube-root-ca.crt` | System (skip) |
| 8 | `milvus` | Helm (milvus) |
| 9 | `milvus-pulsar-bookie` | Helm (milvus) |
| 10 | `milvus-pulsar-broker` | Helm (milvus) |
| 11 | `milvus-pulsar-proxy` | Helm (milvus) |
| 12 | `milvus-pulsar-recovery` | Helm (milvus) |
| 13 | `milvus-pulsar-zookeeper` | Helm (milvus) |

#### 2.8.6 PersistentVolumeClaims (13)

**Dify EFS PVC (1):**

| # | PVC Name | Storage Class | Size | Access Mode | Created |
|---|----------|--------------|------|-------------|---------|
| 1 | `data-dify-39mdc` | efs-sc (EFS) | 10 Gi | ReadWriteMany | 2025-09-25 |

**Milvus etcd EBS PVCs (3):**

| # | PVC Name | Storage Class | Node |
|---|----------|--------------|------|
| 2 | `data-milvus-etcd-0` | ebs.csi.aws.com | ip-10-238-13-197 |
| 3 | `data-milvus-etcd-1` | ebs.csi.aws.com | ip-10-238-12-91 |
| 4 | `data-milvus-etcd-2` | ebs.csi.aws.com | ip-10-238-13-81 |

**Milvus Pulsar Bookie Journal PVCs (3):**

| # | PVC Name | Node |
|---|----------|------|
| 5 | `milvus-pulsar-bookie-journal-...-bookie-0` | ip-10-238-13-99 |
| 6 | `milvus-pulsar-bookie-journal-...-bookie-1` | ip-10-238-14-114 |
| 7 | `milvus-pulsar-bookie-journal-...-bookie-2` | ip-10-238-15-252 |

**Milvus Pulsar Bookie Ledger PVCs (3):**

| # | PVC Name | Node |
|---|----------|------|
| 8 | `milvus-pulsar-bookie-ledgers-...-bookie-0` | ip-10-238-13-99 |
| 9 | `milvus-pulsar-bookie-ledgers-...-bookie-1` | ip-10-238-14-114 |
| 10 | `milvus-pulsar-bookie-ledgers-...-bookie-2` | ip-10-238-15-252 |

**Milvus Pulsar ZooKeeper PVCs (3):**

| # | PVC Name | Node |
|---|----------|------|
| 11 | `milvus-pulsar-zookeeper-data-...-zookeeper-0` | ip-10-238-13-99 |
| 12 | `milvus-pulsar-zookeeper-data-...-zookeeper-1` | ip-10-238-14-99 |
| 13 | `milvus-pulsar-zookeeper-data-...-zookeeper-2` | ip-10-238-13-81 |

#### 2.8.7 Pods Summary (46)

| Group | Pods | Count |
|-------|------|-------|
| Old Dify v1.3.1 | dify-api, dify-web, dify-worker, dify-sandbox, dify-plugin-daemon | 5 |
| New Dify v1.8.1 | new-dify-api(2), new-dify-web(2), new-dify-worker(2), new-dify-sandbox(6), new-dify-plugin-daemon(1) | 13 |
| Milvus core | proxy(2), rootcoord(2), querycoord(2), querynode(2), indexcoord(2), indexnode(2), datacoord(2), datanode(2), attu(1) | 17 |
| Milvus etcd | etcd-0, etcd-1, etcd-2 | 3 |
| Milvus Pulsar | bookie(3), broker(1), proxy(1), zookeeper(3) | 8 |
| **Total** | | **46** |

#### 2.8.8 Secrets

> **Access denied** — `databasecheck` IAM user lacks RBAC permission to list Secrets. Requires `--allow-sensitive-data-access` flag or RBAC update. **Action**: coordinate with EKS admin to enumerate before decommission.

---

### 2.9 DNS Records (TBD)

| # | Record | Type | Value | Notes |
|---|--------|------|-------|-------|
| 1 | `dify-console.luckincoffee.us` | — | Points to NGINX Ingress | Needs Route53 verification |

> Route53 access denied for `databasecheck`. Coordinate with infra team.

---

## 3. Resource Dependency Map

```
                     Internet
                        |
              dify-console.luckincoffee.us (DNS)
                        |
                  NGINX Ingress
                        |
         +---------- new-dify-ingress ----------+
         |              |            |           |
    new-dify-web   new-dify-api  /console   /v1, /api
         |              |
         |    +---------+---------+----------+
         |    |         |         |          |
         | new-dify-   Redis    PgSQL    OpenSearch
         | worker    (difynew) (difynew-rw) (dify)
         |    |                              |
         | new-dify-sandbox              Milvus
         |    |                         (vector DB)
         | new-dify-plugin-daemon          |
         |                          +-+--+-+--+-+
         |                          | etcd      |
         |                          | Pulsar    |
         |                          | (bookie,  |
         |                          |  broker,  |
         |                          |  zk)      |
         |                          +-----------+
         |
    S3 Buckets (lk-infra-dify-*)
         |
    EC2 (isredify01, iluckydifyjump01)
```

**Data Flow:**
1. User -> DNS -> NGINX Ingress -> new-dify-web (frontend) / new-dify-api (backend)
2. new-dify-api -> PostgreSQL `aws-luckyus-difynew-rw` (app data)
3. new-dify-api -> Redis `luckyus-difynew` (cache/session)
4. new-dify-api -> OpenSearch `luckyus-opensearch-dify` (vector search)
5. new-dify-api -> Milvus -> etcd + Pulsar (alternative vector DB)
6. new-dify-api -> S3 `lk-infra-dify-*` (file storage)
7. new-dify-worker -> same backends (async task processing)

---

## 4. Cost Impact Analysis

### Monthly Cost Breakdown (EDP 31% Discount Applied)

| # | Resource | Specification | On-Demand/mo | After EDP (x0.69) |
|---|----------|--------------|--------------|-------------------|
| 1 | RDS `aws-luckyus-dify-rw` | db.r5.xlarge Multi-AZ + 20GB | $739.60 | **$510.32** |
| 2 | RDS `aws-luckyus-difynew-rw` | db.r5.xlarge Multi-AZ + 20GB | $739.60 | **$510.32** |
| 3 | Redis `luckyus-redis-dify` | cache.m6g.large x 2 nodes | $217.54 | **$150.10** |
| 4 | Redis `luckyus-difynew` | cache.t4g.micro x 2 nodes | $23.36 | **$16.12** |
| 5 | OpenSearch `luckyus-opensearch-dify` | 2x r6g.large + 3x m7g.large + 60GB | $546.79 | **$377.29** |
| 6 | EC2 `isredify01` | c6i.large | $62.05 | **$42.81** |
| 7 | EC2 `iluckydifyjump01` | c6i.large | $62.05 | **$42.81** |
| 8 | EBS Volumes (2x 40GB) | gp3 | $6.40 | **$4.42** |
| 9 | S3 (3 buckets) | Estimated ~50GB | ~$2.15 | **~$1.48** |
| 10 | EKS Pods (~46 pods, ~5x m5.xlarge equiv.) | Worker node compute | $700.80 | **$483.55** |
| 11 | EKS Control Plane (shared) | $0.10/hr | $73.00 | **$50.37** |
| | **TOTAL** | | **$3,173.34** | **$2,189.59** |

### Annual Savings from Full Decommission

| Metric | Amount |
|--------|--------|
| Monthly savings (after EDP) | **~$2,190** |
| Annual savings (after EDP) | **~$26,280** |

> Note: EKS control plane is shared — actual savings depend on whether other workloads use the same cluster. Worker node savings depend on whether the freed capacity can be reclaimed (node scale-down).

---

## 5. Pre-Decommission Checklist

Complete ALL items before starting the decommission execution.

### 5.1 Business Confirmation

- [ ] **Confirm with all stakeholders** that Dify is no longer needed
- [ ] **Identify all Dify users** — check `luckyus_dify_api` user table on `difynew-rw`
- [ ] **Notify all users** with decommission timeline (at least 2 weeks notice)
- [ ] **Get written approval** from CTO (Michael) for decommission
- [ ] **Confirm no other systems depend on Dify** — check for API integrations calling `dify-console.luckincoffee.us`

### 5.2 Data Backup

- [ ] **RDS Final Snapshot** — `aws-luckyus-dify-rw` (create manual snapshot with retention)
- [ ] **RDS Final Snapshot** — `aws-luckyus-difynew-rw` (create manual snapshot with retention)
- [ ] **Redis RDB Snapshot** — `luckyus-redis-dify` (trigger manual backup)
- [ ] **Redis RDB Snapshot** — `luckyus-difynew` (trigger manual backup)
- [ ] **S3 Data Backup** — inventory and archive `lk-infra-dify`, `lk-infra-dify-data`, `lk-infra-dify-plugindaemon`
- [ ] **OpenSearch Snapshot** — create manual snapshot of `luckyus-opensearch-dify`
- [ ] **Export Dify knowledge base data** if there is reusable content (documents, datasets)
- [ ] **Milvus data export** — if vector embeddings are needed elsewhere

### 5.3 Documentation

- [ ] **Document all Dify configurations** (environment variables, API keys, integrations)
- [ ] **Record current Helm release values** for old Dify: `helm get values dify -n baseservices-cloud-dify`
- [ ] **Record current Helm release values** for Milvus: `helm get values milvus -n baseservices-cloud-dify`
- [ ] **Screenshot the Dify console** for reference

### 5.4 Permission Verification

- [ ] **Verify IAM permissions** — ensure operator has RDS, ElastiCache, OpenSearch, EC2, S3 delete permissions
- [ ] **Verify EKS RBAC** — ensure operator can delete resources in `baseservices-cloud-dify` namespace
- [ ] **Verify Route53 access** — for DNS record cleanup

---

## 6. Decommission Execution Plan

### Phase 1: Stop Traffic (Day 1)

**Objective**: Cut all external access to Dify while keeping backends running for rollback capability.

| Step | Action | Command / Method | Verify |
|------|--------|-----------------|--------|
| 1.1 | Scale new-dify-web to 0 | `kubectl scale deployment new-dify-web -n baseservices-cloud-dify --replicas=0 --context prod-worker01-eks-us` | `kubectl get pods -n baseservices-cloud-dify -l app=new-dify-web` → 0 pods |
| 1.2 | Scale new-dify-api to 0 | `kubectl scale deployment new-dify-api -n baseservices-cloud-dify --replicas=0 --context prod-worker01-eks-us` | `kubectl get pods -n baseservices-cloud-dify -l app=new-dify-api` → 0 pods |
| 1.3 | Delete ingress | `kubectl delete ingress new-dify-ingress -n baseservices-cloud-dify --context prod-worker01-eks-us` | `kubectl get ingress -n baseservices-cloud-dify` → no new-dify-ingress |
| 1.4 | Monitor for errors | Check Grafana / logs for any 502/503 errors from dependent systems | No unexpected errors in other services |
| 1.5 | **Wait 24-48 hours** | Observation period — confirm no business impact | No escalations or complaints |

---

### Phase 2: Remove Old Dify v1.3.1 (Day 3)

**Objective**: Clean up the idle legacy Dify deployment.

| Step | Action | Command / Method | Verify |
|------|--------|-----------------|--------|
| 2.1 | Uninstall old Dify Helm release | `helm uninstall dify -n baseservices-cloud-dify --kube-context prod-worker01-eks-us` | `helm list -n baseservices-cloud-dify` → no `dify` release |
| 2.2 | Verify old pods terminated | `kubectl get pods -n baseservices-cloud-dify -l app.kubernetes.io/instance=dify` | 0 pods |
| 2.3 | Create RDS final snapshot (old) | `aws rds create-db-snapshot --db-instance-identifier aws-luckyus-dify-rw --db-snapshot-identifier dify-rw-final-20260324 --region us-east-1` | Snapshot status: available |
| 2.4 | Delete old RDS instance | `aws rds delete-db-instance --db-instance-identifier aws-luckyus-dify-rw --final-db-snapshot-identifier dify-rw-decommission-final --skip-final-snapshot false --region us-east-1` | Instance status: deleting |
| 2.5 | Create Redis snapshot (old) | ElastiCache console → `luckyus-redis-dify` → Create Backup | Backup completed |
| 2.6 | Delete old Redis cluster | `aws elasticache delete-replication-group --replication-group-id luckyus-redis-dify --final-snapshot-identifier redis-dify-final-20260324 --region us-east-1` | Status: deleting |

---

### Phase 3: Remove New Dify v1.8.1 (Day 5)

**Objective**: Remove all new Dify application components.

| Step | Action | Command / Method | Verify |
|------|--------|-----------------|--------|
| 3.1 | Scale all new-dify deployments to 0 | `kubectl scale deployment new-dify-worker new-dify-sandbox new-dify-plugin-daemon -n baseservices-cloud-dify --replicas=0 --context prod-worker01-eks-us` | All new-dify pods terminated |
| 3.2 | Delete new-dify deployments | `kubectl delete deployment new-dify-api new-dify-web new-dify-worker new-dify-sandbox new-dify-plugin-daemon -n baseservices-cloud-dify --context prod-worker01-eks-us` | No new-dify deployments |
| 3.3 | Delete new-dify services | `kubectl delete svc new-dify-api new-dify-web new-dify-sandbox new-dify-plugin-daemon -n baseservices-cloud-dify --context prod-worker01-eks-us` | No new-dify services |
| 3.4 | Delete Dify EFS PVC | `kubectl delete pvc data-dify-39mdc -n baseservices-cloud-dify --context prod-worker01-eks-us` | PVC deleted |
| 3.5 | Delete hello-world service | `kubectl delete svc hello-world -n baseservices-cloud-dify --context prod-worker01-eks-us` | Service deleted |

---

### Phase 4: Remove Milvus (Day 5)

**Objective**: Completely remove the Milvus vector database cluster.

| Step | Action | Command / Method | Verify |
|------|--------|-----------------|--------|
| 4.1 | Delete Milvus Attu ingress | `kubectl delete ingress milvus-attu -n baseservices-cloud-dify --context prod-worker01-eks-us` | Ingress deleted |
| 4.2 | Uninstall Milvus Helm release | `helm uninstall milvus -n baseservices-cloud-dify --kube-context prod-worker01-eks-us` | `helm list -n baseservices-cloud-dify` → no `milvus` release |
| 4.3 | Delete remaining Milvus PVCs | `kubectl delete pvc -l app.kubernetes.io/instance=milvus -n baseservices-cloud-dify --context prod-worker01-eks-us` | All Milvus PVCs deleted |
| 4.4 | If PVCs remain, delete individually | `kubectl delete pvc data-milvus-etcd-0 data-milvus-etcd-1 data-milvus-etcd-2 -n baseservices-cloud-dify` and repeat for all pulsar PVCs | 0 PVCs remaining |
| 4.5 | Verify no dangling PVs | `kubectl get pv | grep baseservices-cloud-dify` | No PVs bound to this namespace |

---

### Phase 5: Remove AWS Managed Services (Day 7)

**Objective**: Delete RDS, ElastiCache, OpenSearch for the new Dify environment.

| Step | Action | Command / Method | Verify |
|------|--------|-----------------|--------|
| 5.1 | Create RDS final snapshot (new) | `aws rds create-db-snapshot --db-instance-identifier aws-luckyus-difynew-rw --db-snapshot-identifier difynew-rw-final-20260324 --region us-east-1` | Snapshot: available |
| 5.2 | Delete new RDS instance | `aws rds delete-db-instance --db-instance-identifier aws-luckyus-difynew-rw --final-db-snapshot-identifier difynew-rw-decommission-final --skip-final-snapshot false --region us-east-1` | Status: deleting |
| 5.3 | Create Redis snapshot (new) | `aws elasticache create-snapshot --replication-group-id luckyus-difynew --snapshot-name redis-difynew-final-20260324 --region us-east-1` | Snapshot completed |
| 5.4 | Delete new Redis cluster | `aws elasticache delete-replication-group --replication-group-id luckyus-difynew --final-snapshot-identifier redis-difynew-final-20260324 --region us-east-1` | Status: deleting |
| 5.5 | Create OpenSearch snapshot | Follow OpenSearch manual snapshot procedure (register S3 repo, take snapshot) | Snapshot completed |
| 5.6 | Delete OpenSearch domain | `aws opensearch delete-domain --domain-name luckyus-opensearch-dify --region us-east-1` | Domain: deleting |
| 5.7 | Wait for all deletions | Monitor RDS, ElastiCache, OpenSearch deletion progress (~15-30 min each) | All resources deleted |

---

### Phase 6: Remove EC2 and Storage (Day 8)

| Step | Action | Command / Method | Verify |
|------|--------|-----------------|--------|
| 6.1 | Stop EC2 isredify01 | `aws ec2 stop-instances --instance-ids i-06e7301a6e3f28df4 --region us-east-1` | State: stopped |
| 6.2 | Stop EC2 iluckydifyjump01 | `aws ec2 stop-instances --instance-ids i-02d4ea4bbab7fd574 --region us-east-1` | State: stopped |
| 6.3 | **Wait 48 hours** after stop | Observation period — confirm no impact | No escalations |
| 6.4 | Terminate EC2 isredify01 | `aws ec2 terminate-instances --instance-ids i-06e7301a6e3f28df4 --region us-east-1` | State: terminated |
| 6.5 | Terminate EC2 iluckydifyjump01 | `aws ec2 terminate-instances --instance-ids i-02d4ea4bbab7fd574 --region us-east-1` | State: terminated |
| 6.6 | Verify EBS volumes auto-deleted | `aws ec2 describe-volumes --volume-ids vol-00f8df5db42547f32 vol-00419fed999cc4e01 --region us-east-1` | Volumes not found (auto-deleted) or delete manually |
| 6.7 | Empty S3 buckets | `aws s3 rm s3://lk-infra-dify --recursive` (repeat for each bucket) | Buckets empty |
| 6.8 | Delete S3 buckets | `aws s3 rb s3://lk-infra-dify` (repeat for `lk-infra-dify-data`, `lk-infra-dify-plugindaemon`) | Buckets deleted |

---

### Phase 7: Cleanup (Day 10)

| Step | Action | Command / Method | Verify |
|------|--------|-----------------|--------|
| 7.1 | Delete namespace | `kubectl delete namespace baseservices-cloud-dify --context prod-worker01-eks-us` | Namespace deleted |
| 7.2 | Clean up orphaned ENIs | Delete 4 orphaned OpenSearch ENIs: `eni-0d623c6205c24d3a7`, `eni-0ba40d95964577c62`, `eni-0d7735e22a081705c`, `eni-0f2adc1cdec3cab8a` | ENIs deleted |
| 7.3 | Clean up DNS record | Remove `dify-console.luckincoffee.us` from Route53 | DNS record removed |
| 7.4 | Remove from monitoring | Delete any Grafana dashboards, Prometheus scrape configs, alerting rules for Dify | Monitoring cleaned |
| 7.5 | Remove from mcp-db-gateway | Remove `aws-luckyus-dify-rw`, `aws-luckyus-difynew-rw`, `luckyus-redis-dify` entries from mcp-db-gateway config | Config updated |
| 7.6 | Update documentation | Update CLAUDE.md, infrastructure reports, and inventory docs | Docs updated |
| 7.7 | Verify RDS snapshots retained | `aws rds describe-db-snapshots --db-snapshot-identifier dify-rw-decommission-final --region us-east-1` | Snapshots exist |

---

## 7. Rollback Plan

If business impact is detected during any phase, follow these rollback steps:

### Phase 1 Rollback (Traffic cut)
```bash
# Re-apply the ingress
kubectl apply -f <saved-ingress-yaml> -n baseservices-cloud-dify --context prod-worker01-eks-us
# Scale back up
kubectl scale deployment new-dify-api -n baseservices-cloud-dify --replicas=2 --context prod-worker01-eks-us
kubectl scale deployment new-dify-web -n baseservices-cloud-dify --replicas=2 --context prod-worker01-eks-us
```

### Phase 2 Rollback (Old Dify removed)
- Old Dify was already idle — no rollback needed for v1.3.1.
- Old RDS can be restored from snapshot if needed.

### Phase 3-4 Rollback (New Dify + Milvus removed)
- Restore RDS from snapshot: `aws rds restore-db-instance-from-db-snapshot`
- Restore Redis from backup
- Redeploy Dify via kubectl apply
- Redeploy Milvus via Helm
- Re-apply ingress and DNS

### Phase 5+ Rollback (AWS services deleted)
- Full restoration required from snapshots — estimated 2-4 hours recovery time
- RDS restore: ~15-30 minutes
- ElastiCache restore: ~15-30 minutes
- OpenSearch restore: ~30-60 minutes

---

## 8. Post-Decommission Verification

| # | Check | Method | Expected |
|---|-------|--------|----------|
| 1 | No Dify pods running | `kubectl get pods -n baseservices-cloud-dify` | Namespace not found |
| 2 | No RDS instances | `aws rds describe-db-instances --query "DBInstances[?contains(DBInstanceIdentifier,'dify')]"` | Empty |
| 3 | No ElastiCache clusters | `aws elasticache describe-replication-groups --query "ReplicationGroups[?contains(ReplicationGroupId,'dify')]"` | Empty |
| 4 | No OpenSearch domains | `aws opensearch list-domain-names --query "DomainNames[?contains(DomainName,'dify')]"` | Empty |
| 5 | No EC2 instances | `aws ec2 describe-instances --filters "Name=tag:Name,Values=*dify*" --query "Reservations[].Instances[?State.Name!='terminated']"` | Empty |
| 6 | No S3 buckets | `aws s3api list-buckets --query "Buckets[?contains(Name,'dify')]"` | Empty |
| 7 | DNS removed | `dig dify-console.luckincoffee.us` | NXDOMAIN |
| 8 | RDS snapshots retained | Check snapshots: `dify-rw-decommission-final`, `difynew-rw-decommission-final` | Available |
| 9 | Redis snapshots retained | Check ElastiCache backups | Available |
| 10 | Cost reduction verified | Check Cost Explorer after 1 billing cycle | ~$2,190/month reduction |

---

## 9. Pending Items (Insufficient Permissions)

The following items could not be verified with the `databasecheck` IAM user and require coordination:

| # | Service | Missing Permission | Action Required |
|---|---------|-------------------|-----------------|
| 1 | Route53 | `route53:ListHostedZones`, `route53:ListResourceRecordSets` | Verify DNS record `dify-console.luckincoffee.us` |
| 2 | ECR | `ecr:DescribeRepositories` | Check for Dify container image repositories |
| 3 | Secrets Manager | `secretsmanager:ListSecrets` | Check for Dify-related secrets |
| 4 | EFS | `elasticfilesystem:DescribeFileSystems` | Check for Dify EFS file systems (PVC `data-dify-39mdc` uses EFS) |
| 5 | S3 | `s3:ListBucket` | Enumerate bucket contents and data size |
| 6 | EKS Secrets | RBAC `secrets:list` in namespace | Enumerate Kubernetes Secrets in `baseservices-cloud-dify` |
| 7 | IAM | `iam:ListRoles` | Check for Dify-specific IAM roles |
| 8 | KMS | `kms:DescribeKey` | Verify KMS key `0d74cdfc-57ba-4d94-8947-2249228352f1` usage (OpenSearch encryption) |

> **Recommendation**: Request temporary elevated permissions or coordinate with AWS admin to complete these checks before executing the decommission.

---

## Document History

| Date | Author | Change |
|------|--------|--------|
| 2026-03-24 | David Zeng | Initial draft — full resource inventory and decommission plan |
