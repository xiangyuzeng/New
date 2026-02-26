# Luckin Coffee USA — Graviton Migration Execution Tracker

**Created:** 2026-02-26
**Region:** us-east-1
**EDP Discount:** 31% (0.69 multiplier)
**Plan Owner:** DBA/Infrastructure Team

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Monthly Savings Target** | $6,191.50 |
| **Total Annual Savings Target** | $74,298.00 |
| **Services in Scope** | EC2, EKS, RDS/DocumentDB, MSK, OpenSearch |
| **Total Instances/Resources** | 244+ |
| **Execution Timeline** | 12 weeks (4 phases) |
| **Current Phase** | Phase 1 — Not Started |

---

## Savings Summary

| Service | Resources | Monthly Savings | Annual Savings | Phase | Status |
|---------|-----------|-----------------|----------------|-------|--------|
| RDS/DocumentDB Graviton | 11 instances | $131.23 | $1,574.76 | 1 | ⬜ Not Started |
| RDS gp2→gp3 Storage | 3 instances | $2.17 | $26.04 | 1 | ⬜ Not Started |
| EC2 Non-EKS Graviton | 208 instances | $1,882.48 | $22,589.76 | 2 | ⬜ Not Started |
| MSK Graviton | 3 clusters / 9 brokers | $26.97 | $323.64 | 3 | ⬜ Not Started |
| MSK gp2→gp3 Storage | 3 clusters | $111.78 | $1,341.36 | 3 | ⬜ Not Started |
| OpenSearch Graviton | 2 domains / 8 data nodes | $82.39 | $988.68 | 3 | ⬜ Not Started |
| OpenSearch gp2→gp3 | 2 domains | $41.54 | $498.48 | 3 | ⬜ Not Started |
| EKS Node Groups | 20 nodes / 3 groups | $1,914.99 | $22,979.88 | 4 | ⬜ Blocked |
| **TOTAL** | | **$6,193.55** | **$74,322.60** | | |

---

## Phase 1: RDS/DocumentDB — Low-Risk Quick Wins (Week 1–2)

**Target Savings:** $133.40/month ($1,600.80/year)
**Effort:** Low
**Risk:** Low

### Pre-Migration Checklist (Global)

- [ ] Confirm maintenance window policy with application teams (recommended: 2–5 AM ET)
- [ ] Verify application connection retry/reconnect logic for all affected services
- [ ] Confirm monitoring dashboards are in place (Grafana RDS panels)

### Batch 1: Test Instance

| # | Instance | Engine | Current | Target | Multi-AZ | Savings/mo | Status |
|---|----------|--------|---------|--------|----------|------------|--------|
| 1 | `recovery-dbatest` | MySQL 8.0.40 | db.t3.small | db.t4g.small | Yes | $1.51 | ⬜ |

**Pre-flight:**
- [ ] Take manual snapshot of `recovery-dbatest`
- [ ] Confirm MySQL 8.0.40 supports db.t4g.small

**Execute:**
```bash
aws rds modify-db-instance \
  --db-instance-identifier recovery-dbatest \
  --db-instance-class db.t4g.small \
  --apply-immediately
```

**Post-migration:**
- [ ] Verify instance status = `available`
- [ ] Check CloudWatch: CPUUtilization, DatabaseConnections, ReadLatency, WriteLatency (24h)
- [ ] Confirm application connectivity

**Rollback:**
```bash
aws rds modify-db-instance \
  --db-instance-identifier recovery-dbatest \
  --db-instance-class db.t3.small \
  --apply-immediately
```

---

### Batch 2: DocumentDB DevOps (3 instances)

| # | Instance | Engine | Current | Target | Multi-AZ | Savings/mo | Status |
|---|----------|--------|---------|--------|----------|------------|--------|
| 2 | `docdb-devops` | DocumentDB 5.0.0 | db.t3.medium | db.t4g.medium | No | $1.18 | ⬜ |
| 3 | `docdb-devops2` | DocumentDB 5.0.0 | db.t3.medium | db.t4g.medium | No | $1.18 | ⬜ |
| 4 | `docdb-devops3` | DocumentDB 5.0.0 | db.t3.medium | db.t4g.medium | No | $1.18 | ⬜ |

**Execute per instance:**
```bash
aws docdb modify-db-instance \
  --db-instance-identifier <instance-id> \
  --db-instance-class db.t4g.medium \
  --apply-immediately
```

**⚠️ Note:** Single-AZ — expect brief downtime (~5 min) per instance. Migrate sequentially.

**Post-migration:**
- [ ] All 3 instances status = `available`
- [ ] Application connectivity verified
- [ ] CloudWatch metrics stable (24h)

---

### Batch 3: DocumentDB IoT (3 instances)

| # | Instance | Engine | Current | Target | Multi-AZ | Savings/mo | Status |
|---|----------|--------|---------|--------|----------|------------|--------|
| 5 | `docdb-iot` | DocumentDB 5.0.0 | db.t3.medium | db.t4g.medium | No | $1.18 | ⬜ |
| 6 | `docdb-iot2` | DocumentDB 5.0.0 | db.t3.medium | db.t4g.medium | No | $1.18 | ⬜ |
| 7 | `docdb-iot3` | DocumentDB 5.0.0 | db.t3.medium | db.t4g.medium | No | $1.18 | ⬜ |

**Execute:** Same pattern as Batch 2.

**Post-migration:**
- [ ] All 3 instances status = `available`
- [ ] IoT platform connectivity verified
- [ ] CloudWatch metrics stable (24h)

---

### Batch 4: MySQL Production

| # | Instance | Engine | Current | Target | Multi-AZ | Savings/mo | Status |
|---|----------|--------|---------|--------|----------|------------|--------|
| 8 | `aws-luckyus-iluckyhealth-rw` | MySQL 8.0.40 | db.t3.small | db.t4g.small | Yes | $1.51 | ⬜ |

**Pre-flight:**
- [ ] Take manual snapshot
- [ ] Notify Health platform team
- [ ] Schedule during 2–5 AM ET

**Execute:**
```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-iluckyhealth-rw \
  --db-instance-class db.t4g.small \
  --apply-immediately
```

**Downtime:** ~5 min (Multi-AZ failover)

**Post-migration:**
- [ ] Instance status = `available`
- [ ] Health platform functional verification
- [ ] CloudWatch metrics stable (24h)

---

### Batch 5: PostgreSQL (Medium Impact)

| # | Instance | Engine | Current | Target | Multi-AZ | Savings/mo | Status |
|---|----------|--------|---------|--------|----------|------------|--------|
| 9 | `aws-luckyus-pgilkmap-rw` | PostgreSQL 17.4 | db.m5.large | db.m6g.large | Yes | $19.14 | ⬜ |

**Pre-flight:**
- [ ] Take manual snapshot
- [ ] Notify Map services team
- [ ] Schedule during 2–5 AM ET

**Execute:**
```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-pgilkmap-rw \
  --db-instance-class db.m6g.large \
  --apply-immediately
```

**Post-migration:**
- [ ] Instance status = `available`
- [ ] PostGIS map queries functional
- [ ] CloudWatch metrics stable (24h)

---

### Batch 6: Dify PostgreSQL (Highest Impact — $102.06/mo)

| # | Instance | Engine | Current | Target | Multi-AZ | Savings/mo | Status |
|---|----------|--------|---------|--------|----------|------------|--------|
| 10 | `aws-luckyus-dify-rw` | PostgreSQL 16.8 | db.r5.xlarge | db.r6g.xlarge | Yes | $51.03 | ⬜ |
| 11 | `aws-luckyus-difynew-rw` | PostgreSQL 16.10 | db.r5.xlarge | db.r6g.xlarge | Yes | $51.03 | ⬜ |

**Pre-flight:**
- [ ] Take manual snapshots for both instances
- [ ] Notify Dify AI platform team
- [ ] Schedule during 2–5 AM ET
- [ ] Migrate `aws-luckyus-dify-rw` first, verify, then `aws-luckyus-difynew-rw`

**Execute per instance:**
```bash
aws rds modify-db-instance \
  --db-instance-identifier <instance-id> \
  --db-instance-class db.r6g.xlarge \
  --apply-immediately
```

**Post-migration:**
- [ ] Both instances status = `available`
- [ ] Dify AI platform functional (test workflow execution)
- [ ] CloudWatch: compare ReadLatency/WriteLatency against baseline
- [ ] Query performance: check slow query log count before/after

---

### Batch 7: RDS gp2→gp3 Storage (Zero Downtime)

| # | Instance | Storage | Current | Target | Savings/mo | Status |
|---|----------|---------|---------|--------|------------|--------|
| 12 | `aws-luckyus-devops-rw` | 20 GB | gp2 | gp3 | $0.48 | ⬜ |
| 13 | `aws-luckyus-ldas-rw` | 30 GB | gp2 | gp3 | $0.72 | ⬜ |
| 14 | `recovery-dbatest` | 40 GB | gp2 | gp3 | $0.97 | ⬜ |

**Execute per instance (online, no downtime):**
```bash
aws rds modify-db-instance \
  --db-instance-identifier <instance-id> \
  --storage-type gp3 \
  --apply-immediately
```

**Post-migration:**
- [ ] Storage type shows gp3 in console
- [ ] No IO performance degradation

---

### Phase 1 Summary

| Metric | Value |
|--------|-------|
| **Instances Migrated** | 0 / 11 Graviton + 0 / 3 gp3 |
| **Monthly Savings Realized** | $0.00 / $133.40 |
| **Issues Encountered** | — |
| **Phase Start Date** | TBD |
| **Phase Completion Date** | TBD |

---

## Phase 2: EC2 Non-EKS Graviton Migration (Week 3–6)

**Target Savings:** $1,882.48/month ($22,589.76/year)
**Effort:** Medium
**Risk:** Low

### Pre-Migration Requirements

- [ ] ARM64 AL2023 AMI identified and tested
- [ ] Launch template or AMI build process established for ARM64
- [ ] Application deployment scripts support ARM64 targets
- [ ] Monitoring dashboards prepared for new instance types

### Wave 1: Pilot — c6i.large → c7g.large (5 instances)

**Select 5 non-critical c6i.large instances from the pool of 144.**

| Step | Action | Status |
|------|--------|--------|
| 1 | Select 5 pilot instances (low-traffic, non-critical) | ⬜ |
| 2 | Create AMI from each instance | ⬜ |
| 3 | Launch c7g.large from ARM64 AL2023 AMI (same subnet/SG) | ⬜ |
| 4 | Validate application startup and health checks | ⬜ |
| 5 | Shift traffic (update target group / DNS / LB) | ⬜ |
| 6 | Monitor 24h | ⬜ |
| 7 | Terminate old instances (after 48h observation) | ⬜ |

**Rollback:** Start old stopped instance, repoint traffic. Instant.

**Pilot Verification:**
- [ ] Application health checks passing
- [ ] CloudWatch CPU/Memory/Network within normal range
- [ ] No increase in application error rates (Grafana/Loki)
- [ ] Performance benchmarks comparable to x86

---

### Wave 2: c6i.large Bulk (139 remaining instances)

| Instance Type | Count | Target | Savings/mo |
|---------------|-------|--------|------------|
| c6i.large | 139 | c7g.large | $852.46 |

**Migration method per instance:**
1. Stop instance
2. Create AMI
3. Launch c7g.large with ARM64 AMI in same VPC/subnet/SG
4. Attach same EBS volumes (if data volumes) or restore from snapshot
5. Reassign Elastic IP or update target group registration
6. Start and validate
7. Keep old instance stopped 48h, then terminate

**Progress:** 0 / 139 migrated

---

### Wave 3: c6i.xlarge → c7g.xlarge (42 instances)

| Instance Type | Count | Target | Savings/mo |
|---------------|-------|--------|------------|
| c6i.xlarge | 42 | c7g.xlarge | $528.89 |

**Progress:** 0 / 42 migrated

---

### Wave 4: Mixed Instance Types (11 instances)

| Instance Type | Count | Target | Savings/mo |
|---------------|-------|--------|------------|
| m5.xlarge | Various | m7g.xlarge | — |
| c6i.2xlarge | Various | c7g.2xlarge | — |
| **Subtotal** | 11 | | $212.97 |

**Progress:** 0 / 11 migrated

---

### Wave 5: Remaining Types (16 instances)

| Instance Type | Count | Target | Savings/mo |
|---------------|-------|--------|------------|
| r6i.2xlarge / r6i.4xlarge | Various | r7g equivalents | — |
| c6i.4xlarge | Various | c7g.4xlarge | — |
| m6a / t3 / c5 | Various | m7g / t4g / c7g | — |
| **Subtotal** | 16 | | $233.97 |

**Progress:** 0 / 16 migrated

---

### Phase 2 Summary

| Metric | Value |
|--------|-------|
| **Instances Migrated** | 0 / 208 |
| **Monthly Savings Realized** | $0.00 / $1,882.48 |
| **Issues Encountered** | — |
| **Phase Start Date** | TBD |
| **Phase Completion Date** | TBD |

---

## Phase 3: MSK & OpenSearch (Week 5–7)

**Target Savings:** $262.68/month ($3,152.16/year)
**Effort:** Medium
**Risk:** Medium

### 3A. MSK Clusters — kafka.m5.large → kafka.m7g.large

**Sequence:** business (lowest CPU) → architecture → base

#### Pre-Migration Checklist (All Clusters)

- [ ] Verify Kafka version >= 2.8.0 for all clusters
- [ ] Confirm no under-replicated partitions (baseline: 0 for all ✓)
- [ ] Identify low-traffic maintenance windows
- [ ] Ensure clusters in ACTIVE state
- [ ] Take configuration snapshots

#### Cluster 1: iprod-kafka-business-cluster (Lowest Risk)

| Metric | Value |
|--------|-------|
| Brokers | 3 × kafka.m5.large |
| Target | 3 × kafka.m7g.large |
| Partitions | 171 |
| Avg CPU | 12.2% |
| Peak CPU | 64.7% |
| Storage | 2,700 GB (gp2) |
| Graviton Savings | $8.99/mo |
| gp3 Savings | $37.26/mo |
| **Total Savings** | **$46.25/mo** |

**Step 1 — Graviton Migration:**
```bash
aws kafka update-broker-type \
  --cluster-arn <iprod-kafka-business-cluster-arn> \
  --current-version <config-version> \
  --target-instance-type kafka.m7g.large
```

**Verification (allow 30–60 min for rolling update):**
- [ ] Under-replicated partitions = 0
- [ ] Consumer lag stable
- [ ] Broker CPU/memory within range
- [ ] Producer/consumer throughput unchanged

**Step 2 — gp2→gp3 Storage:**
```bash
aws kafka update-storage \
  --cluster-arn <iprod-kafka-business-cluster-arn> \
  --current-version <config-version> \
  --storage-mode LOCAL \
  --provisioned-throughput Enabled=true,VolumeThroughput=125 \
  --target-broker-ebs-volume-info '{"VolumeSizeGB": 900, "ProvisionedThroughput": {"Enabled": true, "VolumeThroughput": 125}}'
```

**Status:** ⬜ Not Started

---

#### Cluster 2: iprod-kafka-architecture-cluster

| Metric | Value |
|--------|-------|
| Brokers | 3 × kafka.m5.large |
| Target | 3 × kafka.m7g.large |
| Partitions | 194 |
| Avg CPU | 16.8% |
| Peak CPU | 83.9% ⚠️ |
| Storage | 2,700 GB (gp2) |
| **Total Savings** | **$46.25/mo** |

**⚠️ CAUTION:** Peak CPU 83.9%. Schedule during off-peak hours. Monitor closely post-migration.

**Execute:** Same commands as Cluster 1, substituting cluster ARN.

**Status:** ⬜ Not Started

---

#### Cluster 3: iprod-kafka-base-cluster

| Metric | Value |
|--------|-------|
| Brokers | 3 × kafka.m5.large |
| Target | 3 × kafka.m7g.large |
| Partitions | 64 |
| Avg CPU | 27.1% |
| Peak CPU | 83.6% ⚠️ |
| Storage | 2,700 GB (gp2) |
| **Total Savings** | **$46.25/mo** |

**⚠️ CAUTION:** Peak CPU 83.6%. Schedule during off-peak hours.

**Execute:** Same commands as Cluster 1, substituting cluster ARN.

**Status:** ⬜ Not Started

---

#### MSK Rollback Procedure
```bash
aws kafka update-broker-type \
  --cluster-arn <cluster-arn> \
  --current-version <config-version> \
  --target-instance-type kafka.m5.large
```

---

### 3B. OpenSearch Domains

#### Domain 1: luckylfe-log (Lower Risk)

| Metric | Value |
|--------|-------|
| Data Nodes | m5.large.search × 4 → m6g.large.search × 4 |
| Master Nodes | t3.medium.search × 3 (NO Graviton — t3 not supported) |
| Storage | gp2 80GB × 4 = 320 GB → gp3 |
| Avg CPU | 8.1% |
| Peak CPU | 50% |
| Graviton Savings | $28.04/mo |
| gp3 Savings | $7.73/mo |
| **Total Savings** | **$35.77/mo** |

**Pre-flight:**
- [ ] Cluster health = green
- [ ] Recent snapshot exists
- [ ] Schedule during low-traffic window

**Step 1 — Graviton (blue/green deployment):**
```bash
aws opensearch update-domain-config \
  --domain-name luckylfe-log \
  --cluster-config InstanceType=m6g.large.search
```

**Step 2 — gp2→gp3 (online, no downtime):**
```bash
aws opensearch update-domain-config \
  --domain-name luckylfe-log \
  --ebs-options VolumeType=gp3,VolumeSize=80,Iops=3000,Throughput=125
```

**Verification:**
- [ ] Cluster health = green
- [ ] Indexing rate stable
- [ ] Search latency within SLA
- [ ] No shard relocation issues

**Status:** ⬜ Not Started

---

#### Domain 2: luckyur-log (Higher Risk — High CPU)

| Metric | Value |
|--------|-------|
| Data Nodes | m5.xlarge.search × 4 → m6g.xlarge.search × 4 |
| Master Nodes | t3.medium.search × 3 (NO Graviton) |
| Storage | gp2 350GB × 4 = 1,400 GB → gp3 |
| Avg CPU | 16.9% |
| Peak CPU | 84% ⚠️ |
| Graviton Savings | $54.35/mo |
| gp3 Savings | $33.81/mo |
| **Total Savings** | **$88.16/mo** |

**⚠️ WARNING:** Peak CPU 84%. Schedule during lowest-traffic period. Consider temporary scale-up if needed.

**Step 1 — Graviton:**
```bash
aws opensearch update-domain-config \
  --domain-name luckyur-log \
  --cluster-config InstanceType=m6g.xlarge.search
```

**Step 2 — gp2→gp3:**
```bash
aws opensearch update-domain-config \
  --domain-name luckyur-log \
  --ebs-options VolumeType=gp3,VolumeSize=350,Iops=3000,Throughput=125
```

**Verification:**
- [ ] Cluster health = green
- [ ] CPU utilization ≤ 84% baseline (monitor 48h)
- [ ] Indexing rate stable
- [ ] Search latency within SLA

**Status:** ⬜ Not Started

---

#### Domains NOT Eligible

| Domain | Reason | Action Required |
|--------|--------|-----------------|
| `luckycommon` | ES 6.8 — no Graviton support | Upgrade to ES 7.x+ or OpenSearch first |
| `luckyus-opensearch-dify` | Already on Graviton (r6g + m7g + gp3) | None — reference architecture |

---

#### OpenSearch Rollback Procedure
```bash
aws opensearch update-domain-config \
  --domain-name <domain-name> \
  --cluster-config InstanceType=<original-type>
```

---

### Phase 3 Summary

| Metric | Value |
|--------|-------|
| **MSK Clusters Migrated** | 0 / 3 |
| **OpenSearch Domains Migrated** | 0 / 2 |
| **Monthly Savings Realized** | $0.00 / $262.68 |
| **Issues Encountered** | — |
| **Phase Start Date** | TBD |
| **Phase Completion Date** | TBD |

---

## Phase 4: EKS Graviton Migration (Week 8–12)

**Target Savings:** $1,914.99/month ($22,979.88/year)
**Effort:** High
**Risk:** Medium
**Status:** ⬜ BLOCKED — Awaiting container team verification

### Blocker: Container Image ARM64 Compatibility

Before any EKS migration can proceed, the Container Team must provide:

- [ ] **Workload Inventory** — List of all deployments, statefulsets, daemonsets, cronjobs
- [ ] **Container Images** — Full list of container images running in clusters
- [ ] **Architecture Checks** — Any nodeSelector or affinity rules
- [ ] **ARM64 Compatibility** — Multi-arch manifest verification for key images

Reference: `/app/eks-graviton-migration/eks_graviton_container_team_request.md`

### Infrastructure Team Pre-requisites

- [ ] CI/CD pipeline updated for multi-arch builds (linux/amd64 + linux/arm64)
- [ ] ARM64 AL2023 EKS AMI identified for K8s 1.34
- [ ] Launch templates prepared with m7g instance types

---

### Node Group Migration Sequence

#### 4A. eksNativeNodegroup (prod-native-eks-us)

| Metric | Value |
|--------|-------|
| Current | 3 × m6i.4xlarge |
| Target | 3 × m7g.4xlarge |
| Savings | $174.09/mo |

**Migration steps:**
1. Create new launch template version with m7g.4xlarge + ARM64 EKS AMI
2. Create new ARM64 node group alongside existing x86 node group
3. `kubectl cordon` old nodes
4. `kubectl drain --ignore-daemonsets --delete-emptydir-data` old nodes
5. Verify all pods running on ARM64 nodes
6. Delete old node group after 48h observation

**Status:** ⬜ Blocked

---

#### 4B. nodegroup (prod-worker01-eks-us)

| Metric | Value |
|--------|-------|
| Current | 4 × m6i.4xlarge |
| Target | 4 × m7g.4xlarge |
| Savings | $232.12/mo |

**Status:** ⬜ Blocked

---

#### 4C. eksnodegroupworker (prod-worker01-eks-us) — Largest Savings

| Metric | Value |
|--------|-------|
| Current | 13 × m6i.8xlarge |
| Target | 13 × m7g.8xlarge |
| Savings | $1,508.78/mo |

**Status:** ⬜ Blocked

---

### EKS Rollback Procedure

Keep old x86 node group running during observation period. If issues:
1. `kubectl uncordon` old nodes
2. `kubectl drain` new ARM64 nodes
3. Delete new node group

### EKS Verification Checklist

- [ ] All pods in Running state
- [ ] No CrashLoopBackOff or ImagePullBackOff errors
- [ ] Application latency/error rates unchanged (Grafana)
- [ ] CPU/memory utilization on new nodes within expected range
- [ ] Full integration test suite passes

---

### Phase 4 Summary

| Metric | Value |
|--------|-------|
| **Node Groups Migrated** | 0 / 3 |
| **Monthly Savings Realized** | $0.00 / $1,914.99 |
| **Blocker Status** | Container Team verification pending |
| **Phase Start Date** | TBD |
| **Phase Completion Date** | TBD |

---

## Risk Matrix

| Risk | Prob. | Impact | Phase | Mitigation |
|------|-------|--------|-------|------------|
| Application incompatibility on ARM64 | Low (RDS), Med (EKS) | High | 1, 4 | Pilot batches; keep old instances 48h for rollback |
| Performance regression | Low | Medium | All | 24h monitoring per batch; compare CloudWatch baselines |
| Extended downtime during RDS modification | Low | Medium | 1 | Multi-AZ failover limits to ~5 min; schedule 2–5 AM ET |
| MSK rolling update causes consumer lag | Low | Medium | 3 | Monitor under-replicated partitions; one cluster at a time |
| OpenSearch luckyur-log high CPU during migration | Medium | High | 3 | Schedule lowest traffic; consider temporary scale-up |
| EKS container image lacks ARM64 support | Medium | High | 4 | Mandatory image audit before Phase 4 |
| gp2→gp3 storage performance difference | Very Low | Low | 1, 3 | gp3 baseline is equal or better than gp2 |

---

## Overall Progress Dashboard

| Phase | Description | Savings/mo | Progress | Status |
|-------|-------------|------------|----------|--------|
| 1 | RDS/DocumentDB | $133.40 | 0 / 14 tasks | ⬜ Not Started |
| 2 | EC2 Non-EKS | $1,882.48 | 0 / 208 instances | ⬜ Not Started |
| 3 | MSK + OpenSearch | $262.68 | 0 / 5 resources | ⬜ Not Started |
| 4 | EKS | $1,914.99 | 0 / 3 node groups | ⬜ Blocked |
| **Total** | | **$6,193.55** | | |

### Cumulative Savings Realized

| Week | Phase Activity | Cumulative Monthly Savings |
|------|---------------|---------------------------|
| 1 | Phase 1 Batches 1–4 | $0.00 |
| 2 | Phase 1 Batches 5–7 | $0.00 |
| 3 | Phase 2 Pilot (5 instances) | $0.00 |
| 4 | Phase 2 Wave 2 (139 instances) | $0.00 |
| 5 | Phase 2 Wave 3 + Phase 3A starts | $0.00 |
| 6 | Phase 2 Wave 4–5 + Phase 3A continues | $0.00 |
| 7 | Phase 3B OpenSearch | $0.00 |
| 8–12 | Phase 4 EKS (if unblocked) | $0.00 |

*Update cumulative savings as each batch completes. Cost Explorer has ~7-day lag.*

---

## Pricing Reference

### EC2 Instance Pricing (On-Demand, us-east-1)

| Current | Target | Current $/hr | Target $/hr | Savings/hr |
|---------|--------|-------------|-------------|------------|
| m6i.4xlarge | m7g.4xlarge | $0.7680 | $0.6528 | $0.1152 |
| m6i.8xlarge | m7g.8xlarge | $1.5360 | $1.3056 | $0.2304 |

### RDS Instance Pricing (On-Demand, us-east-1)

| Current | Target | Current $/hr | Target $/hr |
|---------|--------|-------------|-------------|
| db.r5.xlarge (Multi-AZ) | db.r6g.xlarge (Multi-AZ) | $1.000 | $0.899 |
| db.m5.large (Multi-AZ) | db.m6g.large (Multi-AZ) | $0.356 | $0.318 |
| db.t3.small (Multi-AZ) | db.t4g.small (Multi-AZ) | $0.068 | $0.065 |
| db.t3.medium (Single-AZ) | db.t4g.medium (Single-AZ) | $0.078 | $0.0757 |

### MSK Broker Pricing (On-Demand, us-east-1)

| Current | Target | Current $/hr | Target $/hr |
|---------|--------|-------------|-------------|
| kafka.m5.large | kafka.m7g.large | $0.210 | $0.204 |

### OpenSearch Instance Pricing (On-Demand, us-east-1)

| Current | Target | Current $/hr | Target $/hr |
|---------|--------|-------------|-------------|
| m5.large.search | m6g.large.search | $0.142 | $0.128 |
| m5.xlarge.search | m6g.xlarge.search | $0.283 | $0.256 |

### Storage Pricing (On-Demand, us-east-1)

| Type | $/GB-month | After EDP (×0.69) |
|------|------------|-------------------|
| gp2 (RDS) | $0.115 | $0.07935 |
| gp3 (RDS) | $0.080 | $0.05520 |
| gp2 (MSK) | $0.100 | $0.06900 |
| gp3 (MSK) | $0.080 | $0.05520 |
| gp2 (OpenSearch) | $0.115 | $0.07935 |
| gp3 (OpenSearch) | $0.080 | $0.05520 |

**All final costs include 31% EDP discount (×0.69 multiplier). Monthly hours: 730.**

---

## Source Reports

| Report | Path |
|--------|------|
| EC2 Migration Analysis | `/app/ec2_graviton_migration_report.md` |
| EKS Migration Analysis | `/app/eks-graviton-migration/eks_graviton_migration_report.md` |
| RDS Migration Analysis | `/app/rds-graviton-migration-analysis-2026-02-10.md` |
| MSK Migration Analysis | `/app/msk-graviton-migration-analysis-2026-02-10.md` |
| OpenSearch Migration Analysis | `/app/opensearch-graviton-migration-analysis-2026-02-10.md` |
| Combined Cost Summary | `/app/eks-graviton-migration/combined_cost_optimization_summary.md` |
| Container Team Request | `/app/eks-graviton-migration/eks_graviton_container_team_request.md` |

---

*Report created: 2026-02-26*
*Author: DBA/Infrastructure Team*
*Region: us-east-1*
*Next review: Update after each phase completion*
