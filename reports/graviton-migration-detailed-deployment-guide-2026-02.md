# Graviton Migration — Detailed Blue/Green Deployment Guide

**Date:** February 26, 2026
**Region:** us-east-1
**EDP Discount:** 31% (0.69 multiplier)
**Prepared by:** DBA/Infrastructure Team

---

## Executive Summary

| Metric | RDS/DocDB | OpenSearch | Combined |
|--------|-----------|------------|----------|
| **Targets** | 11 instances | 2 domains (data nodes only) | 13 targets |
| **Monthly Graviton Savings** | $131.30 | $82.39 | $213.69 |
| **Monthly Storage Savings** | $2.17 | $41.54 | $43.71 |
| **Total Monthly Savings** | $133.47 | $123.93 | **$257.40** |
| **Annual Savings** | $1,601.64 | $1,487.16 | **$3,088.80** |

All metrics below are based on **7-day CloudWatch observations** (Feb 19–26, 2026).

---

## Part 1: RDS & DocumentDB Migrations

### 1.1 Migration Target Overview with Live Metrics

| # | Instance | Engine | Current → Target | Multi-AZ | Avg CPU | Max CPU | Avg Conn | Max Conn | Savings/mo | Risk |
|---|----------|--------|------------------|----------|---------|---------|----------|----------|------------|------|
| 1 | aws-luckyus-difynew-rw | PG 16.10 | db.r5.xlarge → db.r6g.xlarge | Yes | 3.0% | 5.5% | 14 | 14 | $51.03 | **VERY LOW** |
| 2 | aws-luckyus-dify-rw | PG 16.8 | db.r5.xlarge → db.r6g.xlarge | Yes | 2.9% | 3.4% | 1 | 1 | $51.03 | **VERY LOW** |
| 3 | aws-luckyus-pgilkmap-rw | PG 17.4 | db.m5.large → db.m6g.large | Yes | 5.8% | 6.4% | 0 | 0 | $19.14 | **VERY LOW** |
| 4 | aws-luckyus-iluckyhealth-rw | MySQL 8.0.40 | db.t3.small → db.t4g.small | Yes | 10% | 33.9% | 5 | 13 | $1.51 | **LOW** |
| 5 | recovery-dbatest | MySQL 8.0.40 | db.t3.small → db.t4g.small | Yes | 9% | 18.4% | 0 | 0 | $1.51 | **VERY LOW** |
| 6 | docdb-devops (×3 nodes) | DocDB 5.0 | db.t3.medium → db.t4g.medium | No | 31% | 35.6% | 101 | 170 | $3.54 | **MODERATE** |
| 7 | docdb-devops2 | DocDB 5.0 | db.t3.medium → db.t4g.medium | No | — | — | — | — | $1.18 | **LOW** |
| 8 | docdb-devops3 | DocDB 5.0 | db.t3.medium → db.t4g.medium | No | — | — | — | — | $1.18 | **LOW** |
| 9 | docdb-iot (×3 nodes) | DocDB 5.0 | db.t3.medium → db.t4g.medium | No | 23% | 24.8% | 8 | 16 | $3.54 | **LOW** |
| 10 | docdb-iot2 | DocDB 5.0 | db.t3.medium → db.t4g.medium | No | — | — | — | — | $1.18 | **LOW** |
| 11 | docdb-iot3 | DocDB 5.0 | db.t3.medium → db.t4g.medium | No | — | — | — | — | $1.18 | **LOW** |

> **Note:** docdb-devops and docdb-iot metrics are cluster-level (shared across all nodes in each cluster).

---

### 1.2 Detailed Per-Instance Deployment Plans

---

#### Instance 1: aws-luckyus-difynew-rw (PostgreSQL 16.10)

| Attribute | Value |
|-----------|-------|
| **Current Class** | db.r5.xlarge (4 vCPU, 32 GiB) |
| **Target Class** | db.r6g.xlarge (4 vCPU, 32 GiB, Graviton2) |
| **Multi-AZ** | Yes |
| **7-day Avg CPU** | 3.0% |
| **7-day Max CPU** | 5.5% |
| **Avg Connections** | 14 (steady) |
| **Max Connections** | 14 |
| **Monthly Savings** | $51.03 (10.1%) |
| **Risk Level** | VERY LOW |
| **Downtime Impact** | ~30-60 seconds (Multi-AZ failover) |

**Recommended Maintenance Window:** Any time — extremely low utilization, steady connections.

**Pre-Migration Steps:**
```bash
# 1. Verify current instance status
aws rds describe-db-instances --db-instance-identifier aws-luckyus-difynew-rw \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Class:DBInstanceClass,AZ:MultiAZ,Engine:EngineVersion}'

# 2. Create manual snapshot (safety net)
aws rds create-db-snapshot \
  --db-instance-identifier aws-luckyus-difynew-rw \
  --db-snapshot-identifier aws-luckyus-difynew-rw-pre-graviton-$(date +%Y%m%d)

# 3. Wait for snapshot completion
aws rds wait db-snapshot-available \
  --db-snapshot-identifier aws-luckyus-difynew-rw-pre-graviton-$(date +%Y%m%d)
```

**Migration Command:**
```bash
# 4. Modify instance class (Multi-AZ: automatic failover, ~30-60s downtime)
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-difynew-rw \
  --db-instance-class db.r6g.xlarge \
  --apply-immediately

# 5. Monitor progress
aws rds describe-db-instances --db-instance-identifier aws-luckyus-difynew-rw \
  --query 'DBInstances[0].{Status:DBInstanceStatus,PendingValues:PendingModifiedValues}'
```

**Post-Migration Validation:**
```bash
# 6. Confirm new instance class
aws rds describe-db-instances --db-instance-identifier aws-luckyus-difynew-rw \
  --query 'DBInstances[0].{Class:DBInstanceClass,Status:DBInstanceStatus}'
# Expected: db.r6g.xlarge, available

# 7. Verify connectivity (run from application host)
psql -h aws-luckyus-difynew-rw.cluster-xxxx.us-east-1.rds.amazonaws.com -U admin -c "SELECT version();"
# Expected: Contains "aarch64" indicating Graviton

# 8. Check CPU after migration (wait 15 min)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=aws-luckyus-difynew-rw \
  --start-time $(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Average
```

**Rollback Plan:**
```bash
# If issues detected, revert to x86
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-difynew-rw \
  --db-instance-class db.r5.xlarge \
  --apply-immediately
```

---

#### Instance 2: aws-luckyus-dify-rw (PostgreSQL 16.8)

| Attribute | Value |
|-----------|-------|
| **Current Class** | db.r5.xlarge (4 vCPU, 32 GiB) |
| **Target Class** | db.r6g.xlarge (4 vCPU, 32 GiB, Graviton2) |
| **Multi-AZ** | Yes |
| **7-day Avg CPU** | 2.9% |
| **7-day Max CPU** | 3.4% |
| **Avg Connections** | 1 (minimal) |
| **Max Connections** | 1 |
| **Monthly Savings** | $51.03 (10.1%) |
| **Risk Level** | VERY LOW |
| **Downtime Impact** | ~30-60 seconds (Multi-AZ failover) |

**Recommended Maintenance Window:** Any time — near-idle instance.

> **Observation:** With only 1 connection and <4% CPU, this instance may be a candidate for **downsizing** (e.g., db.r6g.large instead of xlarge) for additional $226/month savings. Recommend investigating workload before migration.

**Pre-Migration Steps:**
```bash
aws rds create-db-snapshot \
  --db-instance-identifier aws-luckyus-dify-rw \
  --db-snapshot-identifier aws-luckyus-dify-rw-pre-graviton-$(date +%Y%m%d)
aws rds wait db-snapshot-available \
  --db-snapshot-identifier aws-luckyus-dify-rw-pre-graviton-$(date +%Y%m%d)
```

**Migration Command:**
```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-dify-rw \
  --db-instance-class db.r6g.xlarge \
  --apply-immediately
```

**Post-Migration Validation:**
```bash
aws rds describe-db-instances --db-instance-identifier aws-luckyus-dify-rw \
  --query 'DBInstances[0].{Class:DBInstanceClass,Status:DBInstanceStatus}'
psql -h aws-luckyus-dify-rw.cluster-xxxx.us-east-1.rds.amazonaws.com -U admin -c "SELECT version();"
```

---

#### Instance 3: aws-luckyus-pgilkmap-rw (PostgreSQL 17.4)

| Attribute | Value |
|-----------|-------|
| **Current Class** | db.m5.large (2 vCPU, 8 GiB) |
| **Target Class** | db.m6g.large (2 vCPU, 8 GiB, Graviton2) |
| **Multi-AZ** | Yes |
| **7-day Avg CPU** | 5.8% |
| **7-day Max CPU** | 6.4% |
| **Avg Connections** | 0 |
| **Max Connections** | 0 |
| **Monthly Savings** | $19.14 (10.7%) |
| **Risk Level** | VERY LOW |
| **Downtime Impact** | ~30-60 seconds (Multi-AZ failover) |

> **IMPORTANT FINDING:** This instance has **zero connections over 7 days**. It appears to be **unused**. Before migrating, confirm if this instance should be **decommissioned** instead — that would save the full $160.13/month vs $19.14 from Graviton migration alone.

**Decision Required:**
- **Option A:** Migrate to Graviton (saves $19.14/mo)
- **Option B:** Decommission if unused (saves $160.13/mo) — **recommended if confirmed unused**

**If proceeding with migration:**
```bash
aws rds create-db-snapshot \
  --db-instance-identifier aws-luckyus-pgilkmap-rw \
  --db-snapshot-identifier aws-luckyus-pgilkmap-rw-pre-graviton-$(date +%Y%m%d)
aws rds wait db-snapshot-available \
  --db-snapshot-identifier aws-luckyus-pgilkmap-rw-pre-graviton-$(date +%Y%m%d)

aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-pgilkmap-rw \
  --db-instance-class db.m6g.large \
  --apply-immediately
```

---

#### Instance 4: aws-luckyus-iluckyhealth-rw (MySQL 8.0.40)

| Attribute | Value |
|-----------|-------|
| **Current Class** | db.t3.small (2 vCPU, 2 GiB) |
| **Target Class** | db.t4g.small (2 vCPU, 2 GiB, Graviton2) |
| **Multi-AZ** | Yes |
| **7-day Avg CPU** | 10% |
| **7-day Max CPU** | 33.9% (spike) |
| **Avg Connections** | 5 |
| **Max Connections** | 13 |
| **Monthly Savings** | $1.51 (4.4%) |
| **Risk Level** | LOW |
| **Downtime Impact** | ~30-60 seconds (Multi-AZ failover) |

**Recommended Maintenance Window:** Off-peak hours (US Eastern late night / early morning) due to occasional CPU spikes.

**Pre-Migration Steps:**
```bash
aws rds create-db-snapshot \
  --db-instance-identifier aws-luckyus-iluckyhealth-rw \
  --db-snapshot-identifier aws-luckyus-iluckyhealth-rw-pre-graviton-$(date +%Y%m%d)
aws rds wait db-snapshot-available \
  --db-snapshot-identifier aws-luckyus-iluckyhealth-rw-pre-graviton-$(date +%Y%m%d)
```

**Migration Command:**
```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-iluckyhealth-rw \
  --db-instance-class db.t4g.small \
  --apply-immediately
```

**Post-Migration Validation:**
```bash
aws rds describe-db-instances --db-instance-identifier aws-luckyus-iluckyhealth-rw \
  --query 'DBInstances[0].{Class:DBInstanceClass,Status:DBInstanceStatus}'
mysql -h aws-luckyus-iluckyhealth-rw.cluster-xxxx.us-east-1.rds.amazonaws.com -u admin -p -e "SHOW VARIABLES LIKE 'version_compile_machine';"
# Expected: aarch64
```

---

#### Instance 5: recovery-dbatest (MySQL 8.0.40)

| Attribute | Value |
|-----------|-------|
| **Current Class** | db.t3.small (2 vCPU, 2 GiB) |
| **Target Class** | db.t4g.small (2 vCPU, 2 GiB, Graviton2) |
| **Multi-AZ** | Yes |
| **7-day Avg CPU** | 9% |
| **7-day Max CPU** | 18.4% |
| **Avg Connections** | 0 |
| **Max Connections** | 0 |
| **Monthly Savings** | $1.51 (4.4%) |
| **Risk Level** | VERY LOW |
| **Downtime Impact** | ~30-60 seconds (Multi-AZ failover) |

> **Observation:** Zero connections — this is a DBA test/recovery instance. Very safe to migrate at any time. Could also be a candidate for decommission review.

**Migration Command:**
```bash
aws rds create-db-snapshot \
  --db-instance-identifier recovery-dbatest \
  --db-snapshot-identifier recovery-dbatest-pre-graviton-$(date +%Y%m%d)
aws rds wait db-snapshot-available \
  --db-snapshot-identifier recovery-dbatest-pre-graviton-$(date +%Y%m%d)

aws rds modify-db-instance \
  --db-instance-identifier recovery-dbatest \
  --db-instance-class db.t4g.small \
  --apply-immediately
```

---

#### Instances 6-8: docdb-devops Cluster (DocumentDB 5.0, 3 nodes)

| Attribute | Value |
|-----------|-------|
| **Current Class** | db.t3.medium (2 vCPU, 4 GiB) × 3 nodes |
| **Target Class** | db.t4g.medium (2 vCPU, 4 GiB, Graviton2) × 3 nodes |
| **Multi-AZ** | No (Single-AZ cluster) |
| **7-day Avg CPU** | 31-32% |
| **7-day Max CPU** | 35.6% |
| **Avg Connections** | 101 |
| **Max Connections** | 170 |
| **Monthly Savings** | $3.54 total ($1.18 × 3) |
| **Risk Level** | **MODERATE** |
| **Downtime Impact** | **Minutes per node** (rolling modification recommended) |

> **CAUTION:** This is the highest-traffic migration target with 170 peak connections. Must be done during off-peak hours with rolling node-by-node migration.

**Recommended Maintenance Window:** Saturday/Sunday 2:00-6:00 AM ET (lowest traffic period). Coordinate with DevOps team.

**Migration Strategy — Rolling Node-by-Node:**
```bash
# Step 1: Identify cluster members
aws docdb describe-db-clusters --db-cluster-identifier docdb-devops \
  --query 'DBClusters[0].DBClusterMembers[*].{Instance:DBInstanceIdentifier,IsWriter:IsClusterWriter}'

# Step 2: Migrate READER nodes first (one at a time, wait for each to complete)
# Replace <reader-instance-id> with actual reader instance IDs

# Migrate reader 1
aws docdb modify-db-instance \
  --db-instance-identifier docdb-devops2 \
  --db-instance-class db.t4g.medium \
  --apply-immediately

# Wait for completion (~10-15 min)
aws docdb wait db-instance-available --db-instance-identifier docdb-devops2

# Verify reader 1 is healthy
aws docdb describe-db-instances --db-instance-identifier docdb-devops2 \
  --query 'DBInstances[0].{Class:DBInstanceClass,Status:DBInstanceStatus}'

# Migrate reader 2
aws docdb modify-db-instance \
  --db-instance-identifier docdb-devops3 \
  --db-instance-class db.t4g.medium \
  --apply-immediately

aws docdb wait db-instance-available --db-instance-identifier docdb-devops3

# Step 3: Failover writer to a Graviton reader, then migrate old writer
aws docdb failover-db-cluster --db-cluster-identifier docdb-devops

# Wait for failover completion (~30-60s)
sleep 120

# Migrate the former writer (now reader)
aws docdb modify-db-instance \
  --db-instance-identifier docdb-devops \
  --db-instance-class db.t4g.medium \
  --apply-immediately

aws docdb wait db-instance-available --db-instance-identifier docdb-devops
```

**Post-Migration Validation:**
```bash
# Verify all nodes on Graviton
aws docdb describe-db-clusters --db-cluster-identifier docdb-devops \
  --query 'DBClusters[0].DBClusterMembers[*].DBInstanceIdentifier' --output text | \
  xargs -I{} aws docdb describe-db-instances --db-instance-identifier {} \
  --query 'DBInstances[0].{Instance:DBInstanceIdentifier,Class:DBInstanceClass,Status:DBInstanceStatus}'

# Verify connections recovered
aws cloudwatch get-metric-statistics \
  --namespace AWS/DocDB --metric-name DatabaseConnections \
  --dimensions Name=DBClusterIdentifier,Value=docdb-devops \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Average
```

---

#### Instances 9-11: docdb-iot Cluster (DocumentDB 5.0, 3 nodes)

| Attribute | Value |
|-----------|-------|
| **Current Class** | db.t3.medium (2 vCPU, 4 GiB) × 3 nodes |
| **Target Class** | db.t4g.medium (2 vCPU, 4 GiB, Graviton2) × 3 nodes |
| **Multi-AZ** | No (Single-AZ cluster) |
| **7-day Avg CPU** | 23% |
| **7-day Max CPU** | 24.8% |
| **Avg Connections** | 8 |
| **Max Connections** | 16 |
| **Monthly Savings** | $3.54 total ($1.18 × 3) |
| **Risk Level** | LOW |
| **Downtime Impact** | Minutes per node (rolling modification) |

**Recommended Maintenance Window:** Any off-peak period — low traffic and connections.

**Migration Strategy — Same rolling approach as docdb-devops:**
```bash
# Migrate readers first, then failover and migrate writer
# Reader 1
aws docdb modify-db-instance --db-instance-identifier docdb-iot2 \
  --db-instance-class db.t4g.medium --apply-immediately
aws docdb wait db-instance-available --db-instance-identifier docdb-iot2

# Reader 2
aws docdb modify-db-instance --db-instance-identifier docdb-iot3 \
  --db-instance-class db.t4g.medium --apply-immediately
aws docdb wait db-instance-available --db-instance-identifier docdb-iot3

# Failover writer
aws docdb failover-db-cluster --db-cluster-identifier docdb-iot
sleep 120

# Migrate former writer
aws docdb modify-db-instance --db-instance-identifier docdb-iot \
  --db-instance-class db.t4g.medium --apply-immediately
aws docdb wait db-instance-available --db-instance-identifier docdb-iot
```

---

### 1.3 gp2 → gp3 Storage Migrations (Zero Downtime)

| Instance | Size | Current | Target | Savings/mo | Command |
|----------|------|---------|--------|------------|---------|
| aws-luckyus-devops-rw | 20 GB | gp2 | gp3 | $0.48 | See below |
| aws-luckyus-ldas-rw | 30 GB | gp2 | gp3 | $0.72 | See below |
| recovery-dbatest | 40 GB | gp2 | gp3 | $0.97 | See below |

```bash
# These are online operations — no downtime, can run anytime
aws rds modify-db-instance --db-instance-identifier aws-luckyus-devops-rw \
  --storage-type gp3 --apply-immediately

aws rds modify-db-instance --db-instance-identifier aws-luckyus-ldas-rw \
  --storage-type gp3 --apply-immediately

aws rds modify-db-instance --db-instance-identifier recovery-dbatest \
  --storage-type gp3 --apply-immediately
```

---

## Part 2: OpenSearch Migrations

### 2.1 Migration Target Overview with Live Metrics

| Domain | Engine | Data Nodes | Master Nodes | Avg CPU | Max CPU | JVM Avg | JVM Max | Storage Used | Risk |
|--------|--------|------------|--------------|---------|---------|---------|---------|-------------|------|
| **luckylfe-log** | ES 7.10 | m5.large × 4 → m6g.large × 4 | t3.medium × 3 (no change) | 8% | 62% | 45% | 76% | 156/320 GB (49%) | **LOW-MODERATE** |
| **luckyur-log** | ES 7.10 | m5.xlarge × 4 → m6g.xlarge × 4 | t3.medium × 3 (no change) | 16% | 78% | 58% | 76% | 1,059/1,400 GB (77%) | **MODERATE-HIGH** |

> **Note:** Master nodes (t3.*) have no Graviton equivalent in OpenSearch — only data nodes are migrated.

---

### 2.2 Detailed Per-Domain Deployment Plans

---

#### Domain 1: luckylfe-log (Elasticsearch 7.10)

| Attribute | Value |
|-----------|-------|
| **Data Nodes Current** | m5.large.search × 4 (2 vCPU, 8 GiB each) |
| **Data Nodes Target** | m6g.large.search × 4 (2 vCPU, 8 GiB, Graviton2) |
| **Master Nodes** | t3.medium.search × 3 (unchanged) |
| **Storage Current** | gp2 80 GB × 4 = 320 GB total |
| **Storage Target** | gp3 80 GB × 4 = 320 GB total |
| **7-day Avg CPU** | 8% |
| **7-day Max CPU** | 62% |
| **7-day Avg JVM Memory Pressure** | 45% |
| **7-day Max JVM Memory Pressure** | 76% |
| **Storage Used** | 156 GB / 320 GB (49%) |
| **Monthly Savings (Graviton)** | $28.04 |
| **Monthly Savings (gp2→gp3)** | $7.73 |
| **Total Monthly Savings** | $35.77 |
| **Risk Level** | LOW-MODERATE |
| **Downtime Impact** | Minimal (blue/green deployment, AWS-managed) |

**Recommended Maintenance Window:** Any off-peak period. Storage has 51% headroom — safe for blue/green temporary additional storage needs.

**Pre-Migration Steps:**
```bash
# 1. Verify domain health
aws opensearch describe-domain --domain-name luckylfe-log \
  --query 'DomainStatus.{Processing:Processing,EngineVersion:EngineVersion,ClusterConfig:ClusterConfig}'

# 2. Check cluster health (should be GREEN)
# Via Kibana/OpenSearch Dashboards: GET _cluster/health

# 3. Create manual snapshot (if snapshot repo configured)
# Via Kibana: PUT _snapshot/manual/pre-graviton-$(date +%Y%m%d)
```

**Migration Command (combined Graviton + gp3):**
```bash
# Migrate data nodes to Graviton AND storage to gp3 in a single blue/green deployment
aws opensearch update-domain-config \
  --domain-name luckylfe-log \
  --cluster-config '{
    "InstanceType": "m6g.large.search",
    "InstanceCount": 4,
    "DedicatedMasterEnabled": true,
    "DedicatedMasterType": "t3.medium.search",
    "DedicatedMasterCount": 3
  }' \
  --ebs-options '{
    "EBSEnabled": true,
    "VolumeType": "gp3",
    "VolumeSize": 80,
    "Iops": 3000,
    "Throughput": 125
  }'
```

> **Blue/Green Process:** AWS will automatically:
> 1. Provision new Graviton nodes with gp3 storage alongside existing nodes
> 2. Migrate shards to new nodes (may take 1-3 hours depending on data size)
> 3. Switch traffic to new nodes
> 4. Terminate old nodes
>
> **Expected Duration:** 2-4 hours for 156 GB of data

**Monitor Deployment Progress:**
```bash
# Check processing status (will be true during migration)
aws opensearch describe-domain --domain-name luckylfe-log \
  --query 'DomainStatus.Processing'

# Check domain config change status
aws opensearch describe-domain-config --domain-name luckylfe-log \
  --query 'DomainConfig.ClusterConfig.Status'
```

**Post-Migration Validation:**
```bash
# 1. Verify new instance type
aws opensearch describe-domain --domain-name luckylfe-log \
  --query 'DomainStatus.ClusterConfig.{DataType:InstanceType,DataCount:InstanceCount,MasterType:DedicatedMasterType}'
# Expected: m6g.large.search

# 2. Verify gp3 storage
aws opensearch describe-domain --domain-name luckylfe-log \
  --query 'DomainStatus.EBSOptions.{Type:VolumeType,Size:VolumeSize}'
# Expected: gp3, 80

# 3. Check cluster health via Kibana
# GET _cluster/health
# Expected: status: green

# 4. Check CPU metrics after 30 min
aws cloudwatch get-metric-statistics \
  --namespace AWS/ES --metric-name CPUUtilization \
  --dimensions Name=DomainName,Value=luckylfe-log Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average Maximum
```

---

#### Domain 2: luckyur-log (Elasticsearch 7.10)

| Attribute | Value |
|-----------|-------|
| **Data Nodes Current** | m5.xlarge.search × 4 (4 vCPU, 16 GiB each) |
| **Data Nodes Target** | m6g.xlarge.search × 4 (4 vCPU, 16 GiB, Graviton2) |
| **Master Nodes** | t3.medium.search × 3 (unchanged) |
| **Storage Current** | gp2 350 GB × 4 = 1,400 GB total |
| **Storage Target** | gp3 350 GB × 4 = 1,400 GB total |
| **7-day Avg CPU** | 16% |
| **7-day Max CPU** | 78% |
| **7-day Avg JVM Memory Pressure** | 58% |
| **7-day Max JVM Memory Pressure** | 76.3% |
| **Storage Used** | 1,059 GB / 1,400 GB (77%) |
| **Monthly Savings (Graviton)** | $54.35 |
| **Monthly Savings (gp2→gp3)** | $33.81 |
| **Total Monthly Savings** | $88.16 |
| **Risk Level** | **MODERATE-HIGH** |
| **Downtime Impact** | Minimal (blue/green) but longer migration time |

> **WARNINGS:**
> - **Storage at 77%** — During blue/green deployment, AWS temporarily needs additional storage capacity. Ensure the account has sufficient EBS volume limits.
> - **Max CPU 78%** — Close to the 80% caution threshold. Schedule during guaranteed low-traffic period.
> - **JVM Memory Pressure 76%** — Elevated but within acceptable range. Monitor for GC pressure during migration.

**Recommended Maintenance Window:** Saturday 2:00-8:00 AM ET — requires extended window due to 1+ TB data migration during blue/green.

**Pre-Migration Steps:**
```bash
# 1. Verify domain health and storage
aws opensearch describe-domain --domain-name luckyur-log \
  --query 'DomainStatus.{Processing:Processing,EngineVersion:EngineVersion,ClusterConfig:ClusterConfig,EBSOptions:EBSOptions}'

# 2. Check free storage space (CRITICAL — must have sufficient headroom)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ES --metric-name FreeStorageSpace \
  --dimensions Name=DomainName,Value=luckyur-log Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Minimum

# 3. Verify cluster is GREEN
# Via Kibana: GET _cluster/health

# 4. Consider deleting old indices to free storage before migration
# Via Kibana: DELETE /old-log-index-2025.*
```

**Migration Command:**
```bash
aws opensearch update-domain-config \
  --domain-name luckyur-log \
  --cluster-config '{
    "InstanceType": "m6g.xlarge.search",
    "InstanceCount": 4,
    "DedicatedMasterEnabled": true,
    "DedicatedMasterType": "t3.medium.search",
    "DedicatedMasterCount": 3
  }' \
  --ebs-options '{
    "EBSEnabled": true,
    "VolumeType": "gp3",
    "VolumeSize": 350,
    "Iops": 3000,
    "Throughput": 125
  }'
```

> **Expected Duration:** 4-8 hours for ~1 TB data migration during blue/green deployment.

**Monitor Deployment Progress:**
```bash
# Check every 30 minutes
watch -n 1800 'aws opensearch describe-domain --domain-name luckyur-log \
  --query "DomainStatus.Processing" --output text'
```

**Post-Migration Validation:**
```bash
# 1. Verify instance type
aws opensearch describe-domain --domain-name luckyur-log \
  --query 'DomainStatus.ClusterConfig.InstanceType'
# Expected: m6g.xlarge.search

# 2. Verify storage type
aws opensearch describe-domain --domain-name luckyur-log \
  --query 'DomainStatus.EBSOptions.VolumeType'
# Expected: gp3

# 3. Monitor CPU for 1 hour post-migration
aws cloudwatch get-metric-statistics \
  --namespace AWS/ES --metric-name CPUUtilization \
  --dimensions Name=DomainName,Value=luckyur-log Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '60 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average Maximum

# 4. Monitor JVM Memory Pressure
aws cloudwatch get-metric-statistics \
  --namespace AWS/ES --metric-name JVMMemoryPressure \
  --dimensions Name=DomainName,Value=luckyur-log Name=ClientId,Value=257394478466 \
  --start-time $(date -u -d '60 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average Maximum
```

**Rollback Plan:**
```bash
# Revert to x86 + gp2 if issues detected
aws opensearch update-domain-config \
  --domain-name luckyur-log \
  --cluster-config '{"InstanceType": "m5.xlarge.search", "InstanceCount": 4}' \
  --ebs-options '{"VolumeType": "gp2", "VolumeSize": 350}'
```

---

## Part 3: Recommended Execution Schedule

### Week 1: Zero-Risk Quick Wins
| Day | Target | Type | Savings/mo | Risk | Downtime |
|-----|--------|------|------------|------|----------|
| Mon | gp2→gp3 (3 instances) | Storage | $2.17 | Very Low | None |
| Mon | recovery-dbatest | RDS MySQL | $1.51 | Very Low | ~60s |

### Week 2: Low-Risk PostgreSQL
| Day | Target | Type | Savings/mo | Risk | Downtime |
|-----|--------|------|------------|------|----------|
| Tue | aws-luckyus-dify-rw | RDS PG | $51.03 | Very Low | ~60s |
| Thu | aws-luckyus-difynew-rw | RDS PG | $51.03 | Very Low | ~60s |
| Fri | aws-luckyus-pgilkmap-rw* | RDS PG | $19.14 | Very Low | ~60s |

> *Pending confirmation that pgilkmap-rw is still in use (0 connections).

### Week 3: DocumentDB Clusters
| Day | Target | Type | Savings/mo | Risk | Downtime |
|-----|--------|------|------------|------|----------|
| Sat AM | docdb-iot (3 nodes, rolling) | DocDB | $3.54 | Low | ~5 min/node |
| Sat PM | docdb-devops (3 nodes, rolling) | DocDB | $3.54 | Moderate | ~5 min/node |

### Week 4: MySQL + OpenSearch (Lower Risk)
| Day | Target | Type | Savings/mo | Risk | Downtime |
|-----|--------|------|------------|------|----------|
| Tue | aws-luckyus-iluckyhealth-rw | RDS MySQL | $1.51 | Low | ~60s |
| Sat | luckylfe-log (data nodes + gp3) | OpenSearch | $35.77 | Low-Moderate | ~2-4 hrs (blue/green) |

### Week 5: OpenSearch (Higher Risk)
| Day | Target | Type | Savings/mo | Risk | Downtime |
|-----|--------|------|------------|------|----------|
| Sat 2AM | luckyur-log (data nodes + gp3) | OpenSearch | $88.16 | Moderate-High | ~4-8 hrs (blue/green) |

---

## Part 4: Risk Matrix Summary

| Risk Level | Targets | Count | Monthly Savings | Key Concerns |
|------------|---------|-------|-----------------|--------------|
| **VERY LOW** | difynew-rw, dify-rw, pgilkmap-rw, recovery-dbatest, gp2→gp3 | 5 | $124.88 | None — idle or minimal traffic |
| **LOW** | iluckyhealth-rw, docdb-iot cluster | 4 | $5.05 | Moderate connections, schedule off-peak |
| **LOW-MODERATE** | luckylfe-log | 1 | $35.77 | CPU spikes to 62%, JVM 76% max |
| **MODERATE** | docdb-devops cluster | 3 | $3.54 | 170 peak connections, rolling migration required |
| **MODERATE-HIGH** | luckyur-log | 1 | $88.16 | CPU 78% max, storage 77% used, 1TB blue/green |

---

## Part 5: Key Findings & Recommendations

### 1. Potential Decommission Candidates (Additional Savings)
| Instance | Connections | CPU | Monthly Cost | Action |
|----------|-------------|-----|-------------|--------|
| aws-luckyus-pgilkmap-rw | 0 | 6% | $160.13 | **Investigate — may be unused** |
| aws-luckyus-dify-rw | 1 | 3% | $452.67 | **Investigate downsizing to r6g.large ($226/mo savings)** |
| recovery-dbatest | 0 | 9% | $32.74 | Test instance — confirm if needed |

**Potential additional savings if decommissioned/downsized: up to $419/month ($5,028/year)**

### 2. luckyur-log Storage Capacity Warning
- Storage is at **77% utilization** (1,059 GB / 1,400 GB)
- Blue/green deployment temporarily requires additional EBS capacity
- **Action:** Clean up old log indices before migration, or increase volume size to 500 GB during migration

### 3. luckycommon (ES 6.8) — Upgrade Path Required
- Cannot migrate to Graviton until upgraded from ES 6.8 to 7.x or OpenSearch 1.x+
- Estimated savings after upgrade: ~$28/month
- **This should be a separate project** due to the complexity of major version upgrades

### 4. docdb-devops Connection Management
- 170 peak connections across 3 nodes requires careful rolling migration
- **Action:** Coordinate with DevOps team on maintenance window; ensure application connection pooling handles brief node unavailability

---

## Appendix A: CloudWatch Metric Sources

All metrics collected February 19-26, 2026 using CloudWatch `get-metric-statistics` API:

| Namespace | Metrics | Dimensions |
|-----------|---------|------------|
| AWS/RDS | CPUUtilization, DatabaseConnections | DBInstanceIdentifier |
| AWS/DocDB | CPUUtilization, DatabaseConnections | DBClusterIdentifier |
| AWS/ES | CPUUtilization, JVMMemoryPressure, FreeStorageSpace | DomainName, ClientId=257394478466 |

---

## Appendix B: Complete Cost Summary

| Category | Targets | Current $/mo | Target $/mo | Savings $/mo | Annual |
|----------|---------|-------------|-------------|-------------|--------|
| RDS Graviton (PG r5→r6g) | 2 | $1,007.40 | $905.34 | $102.06 | $1,224.72 |
| RDS Graviton (PG m5→m6g) | 1 | $179.27 | $160.13 | $19.14 | $229.68 |
| RDS Graviton (MySQL t3→t4g) | 2 | $68.50 | $65.48 | $3.02 | $36.24 |
| DocDB Graviton (t3→t4g) | 6 | $235.74 | $228.66 | $7.08 | $84.96 |
| RDS gp2→gp3 | 3 | $7.14 | $4.97 | $2.17 | $26.04 |
| OS Graviton (m5→m6g) | 8 data nodes | $856.30 | $773.91 | $82.39 | $988.68 |
| OS gp2→gp3 | 2 domains | $136.51 | $94.97 | $41.54 | $498.48 |
| **GRAND TOTAL** | **24 targets** | **$2,490.86** | **$2,233.46** | **$257.40** | **$3,088.80** |

---

*Report generated: February 26, 2026*
*AWS Region: us-east-1*
*Data sources: CloudWatch metrics (7-day window), AWS Price List API, 31% EDP discount*
*Reference documents: rds-graviton-migration-analysis-2026-02-10.md, opensearch-graviton-migration-analysis-2026-02-10.md*
