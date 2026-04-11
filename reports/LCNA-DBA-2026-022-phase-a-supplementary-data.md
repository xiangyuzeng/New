# LCNA-DBA-2026-022: Phase A Supplementary Data — Comprehensive Fleet Analysis

**Companion to**: LCNA-DBA-2026-022-phase-a-upgrade-plan.md
**Date**: 2026-04-11
**Data Source**: Live AWS APIs + MCP database queries + CloudWatch metrics

---

## A. Infrastructure Metadata

### A.1 Encryption & Security

| Attribute | Value |
|-----------|-------|
| Storage encryption (at rest) | **59/59 encrypted** (100%) |
| KMS key | AWS-managed (`aws/rds`) |
| CA certificate | `rds-ca-rsa2048-g1` (all 59 instances) |
| Deletion protection | **59/59 enabled** (100%) |
| IAM database auth | 0/59 enabled |
| Performance Insights | 2/59 enabled (only test instances) |

### A.2 Storage Configuration

| Type | Count | Notes |
|------|-------|-------|
| gp3 | 57 | Current standard |
| gp2 | 2 | Legacy (devops-rw, ldas-rw) — consider migrating to gp3 |
| Storage autoscaling | 59/59 configured | All instances have MaxAllocatedStorage set |

### A.3 Auto Minor Version Upgrade

| Setting | Count | Impact |
|---------|-------|--------|
| **Disabled** | **59/59** | All Category A instances under manual control |
| Enabled | 0/59 | No instances at risk of uncontrolled auto-upgrade |

This is good — means AWS won't auto-upgrade during random maintenance windows before our controlled Phase A execution. However, on May 31 the forced upgrade ignores this setting.

### A.4 Engine Lifecycle Support

| Setting | Count |
|---------|-------|
| open-source-rds-extended-support-disabled | 59/59 |

Extended Support is **disabled** on all instances. Confirmed: this does NOT block the May 31 forced minor version upgrade (per AWS support ticket and China team Ethan). It means if we don't complete Phase B by July 31, we'll incur $0.11/vCPU-hour charges.

### A.5 Backup Configuration

| Attribute | Value |
|-----------|-------|
| Backup retention | **7 days** (all 59 instances) |
| Backup window distribution | Spread across 05:00-10:00 UTC |
| Automated backups | Enabled on all |

**Note**: 7-day retention provides adequate rollback window for Phase A (minor version upgrade). No backup window conflicts with the upgrade window (06:00-10:00 UTC) since most backups complete by 06:30 UTC.

### A.6 Maintenance Window Distribution

| Day | Instances | % |
|-----|-----------|---|
| Sunday | 11 | 18.6% |
| Monday | 6 | 10.2% |
| Tuesday | 10 | 16.9% |
| Wednesday | 7 | 11.9% |
| Thursday | 10 | 16.9% |
| Friday | 6 | 10.2% |
| Saturday | 9 | 15.3% |

Maintenance windows are well-distributed across the week. If AWS forced upgrade hits on May 31, instances would be upgraded during their respective maintenance windows — potentially causing rolling outages over 7 days.

### A.7 VPC & Network

| Attribute | Value |
|-----------|-------|
| VPC | `vpc-0dce7ca7770422d33` (single VPC for all 59 instances) |
| Subnet group | Single subnet group across us-east-1a and us-east-1b |
| Multi-AZ | **59/59 enabled** (100%) |

### A.8 Instance Age (Creation Date Range)

| Period | Instances | Notable |
|--------|-----------|---------|
| 2025-02 (oldest) | 2 | devops (Feb 12), ldas (Feb 19) — 14 months old |
| 2025-03 | ~20 | Main fleet buildout |
| 2025-04 to 2025-07 | ~35 | Expansion phase |
| 2026-01 (newest) | 1 | ilsopdevopsdata (Jan 6) — 3 months old |

Fleet age: **3 to 14 months**. All instances created on MySQL 8.0.40 except ldas01 (8.0.41).

---

## B. Database Size Analysis (Live MCP Queries)

### B.1 Actual Data Sizes — Top Instances

| Instance | Class | Allocated | Actual Data | Utilization | Top Database | Tables |
|----------|-------|-----------|-------------|-------------|--------------|--------|
| **ldas01** | db.t4g.large | 128 GB | **86.1 GB** | 67.3% | db_collection (86 GB) | 66 |
| **salesmarketing** | db.t4g.xlarge | 100 GB | **46.1 GB** | 46.1% | sales_marketing (46 GB) | 171 |
| **iluckyhealth** | db.t3.small | 50 GB | **29.4 GB** | 58.9% | iluckyhealth (29 GB) | 15 |
| **icyberdata** | db.t4g.medium | 635 GB | **22.6 GB** | 3.6% | icyberdata (22.6 GB) | 440 |
| **iriskcontrolservice** | db.t4g.micro | 40 GB | **18.1 GB** | 45.3% | iriskcontrolservice (18.1 GB) | 157 |
| **upush** | db.t4g.medium | 40 GB | **17.5 GB** | 43.8% | iupushapp (10.4 GB) + iupushsms (5.1 GB) | 865 |
| **cdpactivity** | db.t4g.medium | 40 GB | **15.5 GB** | 38.7% | cdp_activity (15.5 GB) | 36 |
| **isalesdatamarketing** | db.t4g.medium | 40 GB | **6.9 GB** | 17.3% | isalesdatamarketing (6.9 GB) | 26 |
| **scm-shopstock** | db.t4g.medium | 30 GB | **6.2 GB** | 20.8% | scm_shopstock (6.2 GB) | 192 |
| **iworkflowmidlayer** | db.t4g.medium | 20 GB | **5.2 GB** | 25.8% | iworkflowmidlayer (5.2 GB) | 26 |
| **salesorder** | db.t4g.medium | 20 GB | **4.6 GB** | 22.8% | sales_order (4.6 GB) | 40 |
| **isalesprivatedomain** | db.t4g.medium | 20 GB | **1.8 GB** | 9.2% | isales_privatedomain (1.8 GB) | 25 |
| **ldas** | db.t4g.large | 30 GB | **1.6 GB** | 5.2% | ikafadmin (1.3 GB) | 110 |
| **isalescdp** | db.t4g.medium | 40 GB | **1.5 GB** | 3.7% | isales_cdp (1.5 GB) | 4 |
| **salespayment** | db.t4g.medium | 20 GB | **0.6 GB** | 2.9% | sales_payment (0.6 GB) | 28 |
| **salescrm** | db.t4g.medium | 20 GB | **0.5 GB** | 2.6% | sales_crm (0.5 GB) | 29 |
| **iotplatform** | db.t4g.medium | 20 GB | **0.5 GB** | 2.4% | iot_platform (0.5 GB) | 93 |
| **framework01** | db.t4g.medium | 20 GB | **0.3 GB** | 1.4% | 12 databases (Nacos, Gaea, etc.) | 303 |
| **devops** | db.t4g.medium | 20 GB | **0.2 GB** | 1.2% | 7 databases (Zeus, Grafana, etc.) | 299 |
| **opshop** | db.t4g.medium | 20 GB | **0.03 GB** | 0.1% | opshop (30 MB) | 34 |

### B.2 Critical Data-Size-to-RAM Mismatches

These instances have **data larger than available RAM** — upgrade restart will require cold cache warmup:

| Instance | Class | RAM | Data Size | Data:RAM Ratio | Risk |
|----------|-------|-----|-----------|---------------|------|
| **iluckyhealth** | db.t3.small | **2 GB** | **29.4 GB** | **14.7x** | CRITICAL — 46 MB free, 870 MB swap |
| **iriskcontrolservice** | db.t4g.micro | **1 GB** | **18.1 GB** | **18.1x** | CRITICAL — 90 MB free, 1224 MB swap |
| **upush** | db.t4g.medium | 4 GB | 17.5 GB | 4.4x | MODERATE — only YELLOW instance |
| **cdpactivity** | db.t4g.medium | 4 GB | 15.5 GB | 3.9x | Moderate |
| **icyberdata** | db.t4g.medium | 4 GB | 22.6 GB | 5.7x | Moderate — but 635 GB allocated |
| **isalesdatamarketing** | db.t4g.medium | 4 GB | 6.9 GB | 1.7x | Low |
| **scm-shopstock** | db.t4g.medium | 4 GB | 6.2 GB | 1.6x | Low |
| **iworkflowmidlayer** | db.t4g.medium | 4 GB | 5.2 GB | 1.3x | Low — P0 OOM history |

### B.3 Over-Provisioned Storage (icyberdata)

**icyberdata-rw**: 635 GB allocated but only 22.6 GB actual data (**3.6% utilization**). Paying for 612 GB of unused gp3 storage. Storage cost: ~$0.08/GB/month × 635 GB × 2 (Multi-AZ) = ~$101.60/month for mostly empty storage.

**Note**: RDS does not support storage shrinking. This can only be addressed by migrating to a new instance with correct storage allocation.

### B.4 Fragmentation Analysis

| Instance | Data Size | Free Space (data_free) | Fragmentation |
|----------|-----------|----------------------|---------------|
| icyberdata | 22.6 GB | 4.8 GB | **21.2%** — needs OPTIMIZE TABLE |
| cdpactivity | 15.5 GB | 0.7 GB | 4.8% |
| upush | 17.5 GB | 0.7 GB | 4.0% |
| iriskcontrolservice | 18.1 GB | 0.4 GB | 2.0% |
| salesmarketing | 46.1 GB | 0.3 GB | 0.7% |

---

## C. Performance Baseline (24-Hour Snapshot)

### C.1 CPU Utilization

| Instance | Class | CPU Avg | CPU Max | Assessment |
|----------|-------|---------|---------|------------|
| **icyberdata** | db.t4g.medium | **24.8%** | — | Highest CPU — write-heavy data pipeline |
| isalescdp | db.t4g.medium | 8.5% | — | Moderate — post-OOM upsizing helped |
| framework01 | db.t4g.medium | 7.9% | — | Nacos config server — connection-heavy |
| iotplatform | db.t4g.medium | 7.3% | — | IoT event processing |
| salesmarketing | db.t4g.xlarge | 5.8% | — | Well-sized for workload |
| *Fleet average* | — | *5.4%* | — | Generally underutilized |

**No CPU bottlenecks for Phase A**. Minor version upgrade doesn't change CPU characteristics. icyberdata at 24.8% is notable but not critical (2 vCPU burstable).

### C.2 Connection Patterns (Live MCP Snapshot + CloudWatch Max)

| Instance | Current Conn | Max Used | Max (24h CW) | max_connections | Utilization |
|----------|-------------|----------|------------|-----------------|-------------|
| **ldas01** | 202 | **644** | **411** | 4,000 | 16.1% peak |
| icyberdata | 191 | 215 | 196 | 4,000 | 5.4% |
| framework01 | 124 | 149 | 127 | 4,000 | 3.7% |
| salesmarketing | 63 | 150 | — | 4,000 | 3.8% |
| isalescdp | 61 | 155 | 126 | 4,000 | 3.9% |
| devops | — | — | 117 | 4,000 | 2.9% |

**Key insight**: `max_connections=4000` on all instances is massively over-provisioned. Highest observed is 644 (ldas01). On db.t4g.micro (1GB RAM), each connection thread reserves ~256KB stack = potential 1GB for 4000 threads, which equals the total instance RAM. This is the root cause of the fleet-wide OOM/swap pressure.

**Recommendation**: Reduce `max_connections` to 200-500 on micro instances as a separate initiative. This would dramatically improve FreeableMemory across 38 instances.

### C.3 Write IOPS (24h Average)

| Instance | Class | Write IOPS | Read IOPS | Assessment |
|----------|-------|-----------|-----------|------------|
| **icyberdata** | medium | **138** | — | Write-heavy data pipeline |
| isalescdp | medium | 51 | — | CDP write bursts |
| framework01 | medium | 48 | — | Nacos config updates |
| iotplatform | medium | 42 | — | IoT telemetry |
| salesmarketing | xlarge | 40 | — | Marketing data |
| cdpactivity | medium | 35 | — | Activity logging |
| ldas | large | 27 | — | Analytics ETL |
| isalesdatamarketing | medium | 26 | — | Marketing data |
| upush | medium | 24 | — | Push notification logs |
| ldas01 | large | 20 | — | Analytics collection |

All instances well within gp3 baseline (3,000 IOPS). No IOPS bottleneck concerns for upgrade.

### C.4 Network Throughput

Fleet average: <1 MB/s receive, <1 MB/s transmit. No network throughput concerns.

### C.5 Uptime (Since Last Restart)

| Instance | Uptime | Last Restart (approx) | Notes |
|----------|--------|-----------------------|-------|
| ldas01 | 285 days | ~Jul 2025 | Longest running — 8.0.41 |
| framework01 | 269 days | ~Jul 2025 | |
| salesmarketing | 267 days | ~Jul 2025 | |
| isalescdp | 23 days | Mar 19, 2026 | Recent — post-OOM upsizing |
| icyberdata | 179 days | ~Oct 2025 | |

**isalescdp**: Only 23 days uptime confirms the recent class upgrade from micro→medium (Mar 2026 post-OOM incident). This is actually positive — the instance has stabilized with 1,018 MB free memory.

---

## D. Cost Analysis

### D.1 RDS Monthly Cost Breakdown (March 2026, Pre-EDP)

| Usage Type | Cost | % |
|-----------|------|---|
| Multi-AZ db.t4g.medium (17 instances) | $1,572.53 | 28.0% |
| Multi-AZ db.r5.xlarge (DocumentDB, not MySQL) | $1,488.00 | 26.5% |
| Multi-AZ db.t4g.micro (42 instances) | $871.74 | 15.5% |
| Multi-AZ gp3 Storage | $506.23 | 9.0% |
| Multi-AZ db.t4g.xlarge (1 instance) | $384.65 | 6.9% |
| Multi-AZ db.t4g.large (2 instances) | $383.90 | 6.8% |
| Multi-AZ db.m5.large (DocumentDB) | $264.86 | 4.7% |
| Reserved Instance db.t4g.medium | $69.19 | 1.2% |
| Multi-AZ db.t3.small (1 instance) | $50.59 | 0.9% |
| Other (storage, CPU credits, backup, transfer) | $20.73 | 0.4% |
| **TOTAL RDS (us-east-1)** | **$5,612.43** | |
| **After 31% EDP discount** | **$3,872.58** | |

### D.2 Category A Instance Cost (Phase A Scope)

| Class | Count | Monthly (On-Demand) | Monthly (EDP) | Per Instance (EDP) |
|-------|-------|-------------------|---------------|-------------------|
| db.t4g.micro | 38 | $776.72 | $535.94 | $14.10 |
| db.t3.small | 1 | $51.10 | $35.26 | $35.26 |
| db.t4g.medium | 17 | $1,402.33 | $967.61 | $56.92 |
| db.t4g.large | 2 | $329.96 | $227.67 | $113.84 |
| db.t4g.xlarge | 1 | $329.96 | $227.67 | $227.67 |
| **Total (59 instances)** | | **$2,890.07** | **$1,994.15** | |

### D.3 Extended Support Penalty (if Phase B delayed past July 31, 2026)

| Metric | Value |
|--------|-------|
| Total vCPUs (Category A) | 120 |
| Extended Support rate | $0.11/vCPU-hour |
| **Monthly penalty** | **$9,636.00** |
| Current MySQL RDS cost (EDP) | $1,994.15 |
| **Total with penalty** | **$11,630.15/month** |
| **Cost increase** | **+483%** |

This $9,636/month penalty applies to ALL instances still on MySQL 8.0.x after July 31, 2026 — even 8.0.45. Phase A eliminates the May 31 threat but does NOT prevent Extended Support charges. Phase B (→ 8.4.8) is required by July 31.

---

## E. Application/Service Domain Mapping

| Domain | Instances (Category A) | Key Databases | Business Criticality |
|--------|----------------------|---------------|---------------------|
| **Sales/CRM** | salesmarketing (xlarge), salescrm, salesorder, salespayment, isalescdp, isalesdatamarketing, isalesprivatedomain, isalesmembermarketing, cdpactivity | sales_marketing (46 GB), sales_order (4.6 GB), sales_crm (0.5 GB), cdp_activity (15.5 GB) | **CRITICAL** — revenue, payments, customer data |
| **Data/Analytics** | ldas (large), ldas01 (large), icyberdata, pubdm | db_collection (86 GB), icyberdata (22.6 GB), ikafadmin (1.3 GB) | HIGH — analytics pipeline, reporting |
| **SCM** | scm-shopstock, scmcommodity, scm-asset, scm-openapi, scm-ordering, scm-plan, scm-purchase, scm-wds, scm-wmssimulate, scmsrm, ireplenishment | scm_shopstock (6.2 GB) | MEDIUM — supply chain, inventory |
| **Platform** | framework01, framework02, iotplatform, iopenadmin, iopenlinker, iopenservice, ibizconfigcenter, upush, iluckyams (Cat B) | iworkflowmidlayer (5.2 GB), iupushapp (10.4 GB) | **CRITICAL** — Nacos config, workflow, push notifications |
| **Operations** | opshop, opshopsale, opproduction, opqualitycontrol, opempefficiency, iopshopexpand, iopocp, iluckyhealth | iluckyhealth (29 GB), opshop (30 MB) | MEDIUM — store operations |
| **Finance** | fichargecontrol, fitax, ifiaccounting, ibillingcentersrv, iunifiedreconcile | All < 1 GB | MEDIUM — financial records |
| **DevOps** | devops, ijumpserver, ilsopdevopsdata, iluckydorisops, oplog | izeus (124 MB), grafana (47 MB) | LOW — internal tools |
| **HR/Other** | iehr, igers, iriskcontrolservice, mfranchise, iluckyauthapi, ipermission, iluckymedia, iworkflowmidlayer, iadmin | iriskcontrolservice (18.1 GB) | LOW-MEDIUM |

---

## F. Instance-Level Comprehensive Matrix

Complete per-instance data for all 59 Category A instances:

### F.1 Medium/Large/XLarge Instances (20 instances)

| Instance | Class | RAM | Storage | Data MB | CPU% | MaxConn | FreeMem MB | Swap MB | Risk | Domain | ParamGroup | Created |
|----------|-------|-----|---------|---------|------|---------|-----------|---------|------|--------|------------|---------|
| salesmarketing | xlarge | 16GB | 100GB | 47,169 | 5.8 | 150 | 1,460 | 204 | GREEN | Sales | prod-80-new | 2025-03 |
| ldas | large | 8GB | 30GB | 1,598 | 4.3 | — | 1,026 | 312 | GREEN | Analytics | prod | 2025-02 |
| ldas01 | large | 8GB | 128GB | 99,075 | 4.5 | 644 | 599 | 219 | GREEN | Analytics | prod-80-new | 2025-03 |
| cdpactivity | medium | 4GB | 40GB | 15,838 | 4.9 | — | 457 | 368 | GREEN | Sales | prod-80-new | 2025-04 |
| devops | medium | 4GB | 20GB | 244 | 5.3 | 117 | 1,600 | 7 | GREEN | DevOps | prod | 2025-02 |
| framework01 | medium | 4GB | 20GB | 280 | 7.9 | 149 | 1,584 | 26 | GREEN | Platform | prod-80-new | 2025-03 |
| framework02 | medium | 4GB | 40GB | — | 4.3 | — | 1,001 | 88 | GREEN | Platform | prod-80-new | 2025-03 |
| icyberdata | medium | 4GB | 635GB | 23,192 | 24.8 | 215 | 567 | 1,399 | GREEN | Analytics | prod-80-new | 2025-05 |
| iotplatform | medium | 4GB | 20GB | 492 | 7.3 | — | 1,496 | 3 | GREEN | Platform | prod-80-new | 2025-04 |
| isalescdp | medium | 4GB | 40GB | 1,492 | 8.5 | 155 | 1,018 | 0 | GREEN | Sales | prod-80-new | 2025-03 |
| isalesdatamarketing | medium | 4GB | 40GB | 7,065 | 4.2 | — | 619 | 488 | GREEN | Sales | prod-80-new | 2025-04 |
| isalesprivatedomain | medium | 4GB | 20GB | 1,890 | 4.1 | — | 639 | 135 | GREEN | Sales | prod-80-new | 2025-03 |
| iworkflowmidlayer | medium | 4GB | 20GB | 5,298 | 4.5 | — | 458 | 191 | GREEN | Platform | prod-80-new | 2025-03 |
| opshop | medium | 4GB | 20GB | 30 | 4.0 | — | 2,224 | 0 | GREEN | Operations | prod-80-new | 2025-04 |
| salescrm | medium | 4GB | 20GB | 525 | 4.3 | — | 1,790 | 0 | GREEN | Sales | prod-80-new | 2025-03 |
| salesorder | medium | 4GB | 20GB | 4,671 | 4.2 | — | 375 | 214 | GREEN | Sales | groupconcat | 2025-03 |
| salespayment | medium | 4GB | 20GB | 595 | 4.0 | — | 1,683 | 0 | GREEN | Sales | prod-80-new | 2025-03 |
| scm-shopstock | medium | 4GB | 30GB | 6,387 | 4.4 | — | 461 | 331 | GREEN | SCM | prod-80-new | 2025-04 |
| scmcommodity | medium | 4GB | 20GB | — | 4.2 | — | 2,054 | 0 | GREEN | SCM | prod-80-new | 2025-04 |
| upush | medium | 4GB | 40GB | 18,163 | 4.2 | — | 251 | 328 | YELLOW | Platform | prod-80-new | 2025-05 |

### F.2 Micro/Small Instances (39 instances) — Sorted by FreeableMemory

| Instance | Class | RAM | Storage | FreeMem MB | Swap MB | Risk | Domain |
|----------|-------|-----|---------|-----------|---------|------|--------|
| **iluckyhealth** | **t3.small** | **2GB** | 50GB | **46** | **870** | **RED** | Operations |
| opqualitycontrol | micro | 1GB | 20GB | 63 | 746 | RED | Operations |
| opshopsale | micro | 1GB | 20GB | 81 | 649 | RED | Operations |
| scm-ordering | micro | 1GB | 20GB | 83 | 765 | RED | SCM |
| pubdm | micro | 1GB | 20GB | 87 | 505 | RED | Analytics |
| ireplenishment | micro | 1GB | 20GB | 87 | 648 | RED | SCM |
| fichargecontrol | micro | 1GB | 20GB | 87 | 565 | RED | Finance |
| opproduction | micro | 1GB | 20GB | 88 | 603 | RED | Operations |
| opempefficiency | micro | 1GB | 20GB | 89 | 546 | RED | Operations |
| **iriskcontrolservice** | micro | 1GB | **40GB** | 90 | **1,224** | **RED** | Risk |
| ipermission | micro | 1GB | 20GB | 90 | 591 | RED | Platform |
| scm-wmssimulate | micro | 1GB | 20GB | 90 | 535 | RED | SCM |
| iopenlinker | micro | 1GB | 20GB | 90 | 502 | RED | Platform |
| scmsrm | micro | 1GB | 20GB | 90 | 730 | RED | SCM |
| iehr | micro | 1GB | 20GB | 90 | 557 | RED | HR |
| ijumpserver | micro | 1GB | 20GB | 90 | 624 | RED | DevOps |
| ibillingcentersrv | micro | 1GB | 20GB | 90 | 680 | RED | Finance |
| iopocp | micro | 1GB | 20GB | 91 | 619 | RED | Operations |
| scm-purchase | micro | 1GB | 20GB | 91 | 792 | RED | SCM |
| scm-wds | micro | 1GB | 20GB | 91 | 716 | RED | SCM |
| ifiaccounting | micro | 1GB | 20GB | 93 | 865 | RED | Finance |
| fitax | micro | 1GB | 20GB | 93 | 394 | RED | Finance |
| oplog | micro | 1GB | 20GB | 93 | 409 | RED | DevOps |
| scm-openapi | micro | 1GB | 20GB | 93 | 579 | RED | SCM |
| scm-plan | micro | 1GB | 20GB | 93 | 470 | RED | SCM |
| isalesmembermarketing | micro | 1GB | 20GB | 94 | 427 | RED | Sales |
| scm-asset | micro | 1GB | 20GB | 94 | 594 | RED | SCM |
| iluckydorisops | micro | 1GB | 20GB | 95 | 407 | RED | DevOps |
| iopenservice | micro | 1GB | 20GB | 96 | 406 | RED | Platform |
| iadmin | micro | 1GB | 20GB | 96 | 510 | RED | Platform |
| ilsopdevopsdata | micro | 1GB | 20GB | 98 | 380 | RED | DevOps |
| iluckymedia | micro | 1GB | 20GB | 98 | 415 | RED | Platform |
| iluckyauthapi | micro | 1GB | 20GB | 98 | 403 | RED | Platform |
| ibizconfigcenter | micro | 1GB | 20GB | 99 | 434 | RED | Platform |
| iopshopexpand | micro | 1GB | 20GB | 99 | 428 | RED | Operations |
| mfranchise | micro | 1GB | 20GB | 100 | 461 | RED | Operations |
| iunifiedreconcile | micro | 1GB | 20GB | 101 | 426 | RED | Finance |
| iopenadmin | micro | 1GB | 20GB | 103 | 420 | RED | Platform |
| igers | micro | 1GB | 20GB | 104 | 398 | RED | HR |

---

## G. Risk Register

### G.1 Upgrade-Specific Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | Buffer pool auto-reduction to 128MB after restart on micro instances | Medium | High | Post-upgrade check: `SHOW GLOBAL VARIABLES LIKE 'innodb_buffer_pool_size'`. If 134217728 → immediate remediation |
| R2 | iluckyhealth OOM during upgrade (46 MB free, 29 GB data) | Medium | Medium | Upgrade during lowest traffic; consider upsizing to db.t4g.medium first ($22/mo increase with EDP) |
| R3 | iriskcontrolservice OOM (18.1 GB data on 1 GB RAM, 1.2 GB swap) | Low | Low | Low-traffic instance; Multi-AZ failover provides protection |
| R4 | upush memory pressure during restart (YELLOW, 251 MB free) | Low | Medium | Monitor closely; 17.5 GB data with 4 GB RAM, will need cold cache warmup |
| R5 | icyberdata extended restart time (635 GB allocated) | Very Low | Low | Minor upgrade is in-place — storage size is irrelevant. Actual data only 22.6 GB |
| R6 | ldas01 connection surge post-restart (644 max historical connections) | Low | Medium | Nacos/app reconnection storm possible; monitor Threads_connected for 5 min after |
| R7 | framework01/02 Nacos disruption | Low | High | Upgrade ONE AT A TIME; verify `@@version` and `Threads_connected` via MCP between |

### G.2 Fleet-Wide Systemic Risks (Pre-Existing, Not Upgrade-Specific)

| # | Risk | Current Status | Recommendation |
|---|------|---------------|----------------|
| S1 | **max_connections=4000 on all instances** | 38 micro instances (1GB RAM) each reserving up to 1GB for thread stacks | Reduce to 200-500; highest observed usage is 644 (ldas01) |
| S2 | **39 instances with FreeableMemory < 150 MB** | Chronic — all micros at 46-104 MB free | Right-sizing initiative: batch upgrade critical micros to db.t4g.small ($28.47/mo EDP) |
| S3 | **Performance Insights disabled on 57/59 instances** | No historical query-level performance data | Enable on at least Batch 5/6 instances before Phase B |
| S4 | **2 instances still on gp2 storage** (devops, ldas) | Missing gp3 IOPS/throughput baseline of 3000/125 | Migrate to gp3 (zero downtime, $0 cost change for ≤20 GB) |
| S5 | **icyberdata 635 GB over-provisioned** | 3.6% utilization, ~$102/mo wasted | Cannot shrink — would need new instance migration |

---

## H. Execution Readiness Checklist

| # | Item | Status | Details |
|---|------|--------|---------|
| 1 | Target version confirmed | **READY** | 8.0.45 (latest available, AWS API verified) |
| 2 | Upgrade paths validated | **READY** | 8.0.40→8.0.45 and 8.0.41→8.0.45 (AWS API verified) |
| 3 | Pre-flight blockers | **CLEAR** | 0 blockers across 59 instances |
| 4 | Batch plan defined | **READY** | 5 batches, 59 instances, all assigned |
| 5 | Health assessment complete | **READY** | 39 RED, 1 YELLOW, 19 GREEN (24h CloudWatch data) |
| 6 | Performance baseline captured | **READY** | CPU, IOPS, connections, network for all 59 instances |
| 7 | Database sizes audited | **READY** | Top 20 instances queried via MCP |
| 8 | Parameter groups documented | **READY** | All 3 groups' custom params recorded |
| 9 | Recent incidents checked | **CLEAR** | No production incidents in past 7 days |
| 10 | Upgrade script generated | **READY** | `/home/claude/phase-a/phase-a-upgrade.sh` |
| 11 | **IAM write permission** | **BLOCKED** | `databasecheck` user lacks `rds:ModifyDBInstance` |
| 12 | Rollback plan | **READY** | Minor version downgrade not supported by AWS; restore from automated backup (7-day retention) if critical issue |

---

## I. Files Inventory

All in `/home/claude/phase-a/`:

| File | Size | Description |
|------|------|-------------|
| `fleet-inventory.json` | 36 KB | Core instance metadata (63 instances) |
| `fleet-extended-metadata.json` | 55 KB | Extended metadata: encryption, backup, VPC, creation dates |
| `available-80-versions.txt` | 0.3 KB | Available 8.0.x versions |
| `upgrade-path-validation.txt` | 0.5 KB | Upgrade path confirmation |
| `classification.txt` | 6 KB | Category A/B/C/D breakdown |
| `pre-flight-blockers.txt` | 0.1 KB | No blockers |
| `health-assessment.txt` | 5 KB | FreeableMemory/SwapUsage per instance |
| `health-raw.json` | 241 KB | Raw CloudWatch memory metrics (118 queries) |
| `perf-raw.json` | 143 KB | Raw CloudWatch performance metrics (472 queries) |
| `performance-baseline.txt` | 7 KB | CPU/IOPS/connections/slow query baseline |
| `recent-incidents.txt` | 0.5 KB | Past 7 days events |
| `param-groups-pre-upgrade.txt` | 34 KB | Parameter group settings |
| `batch-plan.txt` | 8 KB | Batch assignments with health status |
| `batch-assignments.json` | 5 KB | Machine-readable batch data |
| `timeline-estimate.txt` | 1 KB | Time estimates |
| `rds-cost-march.json` | 5 KB | March 2026 RDS cost data |
| `rds-alarms.txt` | 0 KB | No CloudWatch alarms configured for RDS |
| `phase-a-upgrade.sh` | 10 KB | Ready-to-run upgrade script |

---

*All data collected 2026-04-11 20:41-21:15 UTC via live AWS APIs (describe-db-instances, describe-db-engine-versions, cloudwatch get-metric-data, ce get-cost-and-usage, describe-events, describe-db-parameters) and MCP database queries (information_schema.TABLES, performance_schema.global_status).*
