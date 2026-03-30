# AWS OpenSearch / Elasticsearch Cost Analysis Report

**Date**: 2026-03-30 | **Account**: 257394478466 | **Region**: us-east-1
**EDP Discount**: 31% (multiply pre-EDP costs × 0.69 for actual cost)
**Prepared by**: DBA Team (David Zeng)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Domains** | 4 (3 Elasticsearch + 1 OpenSearch) |
| **Monthly Cost (pre-EDP)** | $2,625/mo |
| **Monthly Cost (after EDP)** | $1,811/mo |
| **Annual Cost (after EDP)** | $21,731/yr |
| **Active RI Coverage** | 8× m5.large.search (covers 2 of 4 domains' data nodes) |
| **Top Savings Opportunity** | Decommission idle Dify domain → **$4,543/yr** |
| **Total Identified Savings** | **$6,088/yr after EDP** (28% reduction) |

### Top 3 Action Items

1. **P0 — Decommission `luckyus-opensearch-dify`** — idle 5+ months, $378/mo waste → $4,543/yr saved
2. **P1 — Migrate gp2 → gp3 storage** on luckylfe-log + luckyur-log → $384/yr saved
3. **P2 — Switch to Graviton m6g.large** when m5.large RI expires (Aug 2026) → $1,161/yr saved

---

## 1. Domain Inventory

| Domain | Engine | Data Nodes | Master Nodes | EBS Type | EBS/Node | Total Storage | Warm/Cold |
|--------|--------|-----------|-------------|----------|----------|---------------|-----------|
| **luckycommon** | ES 6.8 | 4× m5.large | 3× t3.small | gp3 | 100 GB | 400 GB | No |
| **luckylfe-log** | ES 7.10 | 4× m5.large | 3× t3.medium | gp2 | 80 GB | 320 GB | No |
| **luckyur-log** | ES 7.10 | 4× m5.xlarge | 3× t3.medium | gp2 | 500 GB | 2,000 GB | No |
| **luckyus-opensearch-dify** | OS 2.15 | 2× r6g.large | 3× m7g.large | gp3 | 30 GB | 60 GB | No |

**Total nodes**: 14 data + 12 master = 26 instances
**Total storage**: 2,780 GB
**Zone awareness**: All domains use 2 AZs (us-east-1a, us-east-1b)
**Encryption**: All domains have encryption at rest (KMS) and node-to-node encryption enabled
**Software updates available**: All 4 domains have pending software updates (not auto-applied)

---

## 2. Monthly Cost Breakdown (6 Months)

### 2a. Total Monthly Cost by Usage Type (Pre-EDP)

| Usage Type | Oct 2025 | Nov 2025 | Dec 2025 | Jan 2026 | Feb 2026 | Mar 2026* |
|-----------|----------|----------|----------|----------|----------|-----------|
| **RI (HeavyUsage:m5.large)** | $583.30 | $564.48 | $583.30 | $583.30 | $526.85 | $583.30 |
| **OD m5.xlarge (luckyur data)** | $842.21 | $815.04 | $842.21 | $841.08 | $760.70 | $793.53 |
| **OD m7g.large (dify master)** | $300.92 | $291.60 | $301.32 | $301.32 | $272.16 | $283.91 |
| **OD r6g.large (dify data)** | $248.16 | $240.48 | $248.50 | $248.50 | $224.45 | $234.13 |
| **OD t3.medium (log masters)** | — | $240.46 | $325.87 | $325.65 | $294.34 | $307.04 |
| **OD t3.small (common master)** | $240.95 | $114.70 | $80.35 | $80.35 | $72.58 | $75.71 |
| **EBS gp2** | $232.20 | $232.20 | $232.20 | $231.95 | $232.20 | $266.25 |
| **EBS gp3** | $21.93 | $21.96 | $24.92 | $34.25 | $56.12 | $52.88 |
| **Data Transfer** | $0.12 | $0.12 | $0.12 | $0.13 | $0.12 | $0.12 |
| **TOTAL pre-EDP** | **$2,469.79** | **$2,521.04** | **$2,638.79** | **$2,646.53** | **$2,439.52** | **$2,596.87** |
| **TOTAL after EDP (×0.69)** | **$1,704.15** | **$1,739.52** | **$1,820.77** | **$1,826.11** | **$1,683.27** | **$1,791.84** |

*\*Mar 2026 is partial month (through Mar 30). GP2 increase in March reflects luckyur-log storage expansion (350→500 GB/node mid-month).*

**6-Month Average**: $2,552/mo pre-EDP → **$1,761/mo after EDP**

### Trend Analysis

- Costs are **stable** ($2,440–$2,647/mo range) with no significant growth trend
- Nov 2025: t3.medium masters added for luckylfe-log and luckyur-log (previously t3.small)
- Mar 2026: GP2 storage increased due to luckyur-log emergency expansion
- Feb 2026: Lower costs reflect shorter month (28 days)
- `m5.large` ESInstance shows $0 in all months — fully covered by active RI

### 2b. Estimated Per-Domain Monthly Cost (Steady State)

| Domain | Data Nodes | Master Nodes | Storage | Total pre-EDP | Total after EDP | % of Total |
|--------|-----------|-------------|---------|---------------|-----------------|------------|
| **luckycommon** | $286 (RI) | $79 | $32 (gp3) | **$397** | **$274** | 15% |
| **luckylfe-log** | $286 (RI) | $160 | $32 (gp2) | **$478** | **$330** | 18% |
| **luckyur-log** | $841 (OD) | $160 | $200 (gp2) | **$1,201** | **$829** | 46% |
| **luckyus-opensearch-dify** | $244 (OD) | $300 (OD) | $5 (gp3) | **$549** | **$379** | 21% |
| **TOTAL** | **$1,657** | **$699** | **$269** | **$2,625** | **$1,811** | 100% |

**Key Insight**: luckyur-log accounts for 46% of total cost. The Dify domain (21%) is entirely wasted spend. Instance costs (63%) dominate over storage (10%) and masters (27%).

**Dify anomaly**: Master nodes ($300/mo) cost MORE than data nodes ($244/mo) — 3× m7g.large masters for just 2× r6g.large data nodes is severely over-provisioned for an idle cluster.

---

## 3. Reserved Instance Analysis

### 3a. Current RI Coverage

| RI Name | Instance Type | Count | State | Rate | Monthly (pre-EDP) | Covers |
|---------|-------------|-------|-------|------|-------------------|--------|
| m5-large-search-8 | m5.large.search | 8 | **Active** | $0.098/hr | $572 | luckycommon + luckylfe-log data |
| m5-xlarge-search-4 | m5.xlarge.search | 4 | Retired | $0.195/hr | — | *(was luckyur-log data)* |
| m7g-large-search-3 | m7g.large.search | 3 | Retired | $0.093/hr | — | *(was dify masters)* |
| r6g-large-search-2 | r6g.large.search | 2 | Retired | $0.115/hr | — | *(was dify data)* |

**Active RI expiry**: ~August 27, 2026 (1 year from start date)

### 3b. RI vs On-Demand with EDP Comparison

| Instance Type | Count | OD Rate | OD+EDP Monthly | RI Rate | RI Monthly | RI Savings vs OD+EDP |
|--------------|-------|---------|----------------|---------|-----------|---------------------|
| m5.large.search | 8 | $0.142/hr | $573* | $0.098/hr | $572 | **~$0** (break-even) |
| m5.xlarge.search | 4 | $0.288/hr | $581 | ~$0.184/hr (All Upfront) | $537 | **$44/mo ($528/yr)** |
| r6g.large.search | 2 | $0.167/hr | $168 | N/A (decommission) | — | — |
| m7g.large.search | 3 | $0.137/hr | $207 | N/A (decommission) | — | — |

*\*OD+EDP = On-Demand rate × 730h × count × 0.69*

**Key Finding**: With the 31% EDP discount, the gap between On-Demand and RI pricing is minimal:

- **m5.large RI savings** = essentially zero after EDP ($572 RI vs $573 OD+EDP). When RI expires in Aug 2026, switching to **Graviton m6g.large OD+EDP** ($476/mo) is the better path.
- **m5.xlarge RI** = saves $44/mo ($528/yr) but requires $6,444 upfront for 4 instances. ROI is only 8.2%. **Not recommended** — stay on-demand with EDP.
- **Dify instances** — should be decommissioned, not renewed.

**Recommendation**: **Do not purchase new RIs.** The 31% EDP discount makes On-Demand pricing competitive with RIs. Let the active m5.large RI expire naturally in Aug 2026, then migrate to Graviton.

---

## 4. Storage Utilization Analysis

### 4a. Storage Utilization by Domain

| Domain | Allocated | Free (Current) | Used | Utilization | CW 30d Avg Free | CW 30d Min Free |
|--------|-----------|---------------|------|-------------|-----------------|-----------------|
| **luckycommon** | 400 GiB | 128.79 GiB | 271 GiB | **67.8%** | 36.8 GiB* | 25.4 GiB* |
| **luckylfe-log** | 320 GiB | 92.10 GiB | 228 GiB | **71.2%** | 24.6 GiB* | 12.0 GiB* |
| **luckyur-log** | 2,000 GiB | 620.52 GiB | 1,380 GiB | **69.0%** | 120.0 GiB* | 3.5 GiB* |
| **luckyus-opensearch-dify** | 60 GiB | 46.94 GiB | 13 GiB | **21.8%** | 23.5 GiB | 23.5 GiB |

*\*CloudWatch FreeStorageSpace can report per-node minimum rather than cluster total. User-provided "current" values are from the latest Grafana snapshot and are the most reliable.*

### 4b. Storage Assessment

- **luckycommon (67.8%)**: Healthy. gp3 volume at 100GB/node. No action needed.
- **luckylfe-log (71.2%)**: Adequate headroom. On gp2 — candidate for gp2→gp3 migration to save $6.40/mo.
- **luckyur-log (69.0%)**: Recently expanded from 350→500 GB/node (March 2026). Resolved previous 96% utilization crisis. Still on gp2 — candidate for gp3 migration to save $40/mo. Monitor growth rate (~5-7 GB/day).
- **luckyus-opensearch-dify (21.8%)**: Massively over-provisioned. Only 13 GiB used of 60 GiB. But the real recommendation is decommission, not right-size.

### 4c. gp2 → gp3 Migration Savings

| Domain | Volume | gp2 Cost | gp3 Cost | Monthly Savings |
|--------|--------|----------|----------|-----------------|
| luckylfe-log | 4× 80 GB = 320 GB | $32.00 | $25.60 | $6.40 |
| luckyur-log | 4× 500 GB = 2,000 GB | $200.00 | $160.00 | $40.00 |
| **Total** | | **$232.00** | **$185.60** | **$46.40/mo** |

After EDP: **$32.02/mo → $384/yr saved**

gp3 includes 3,000 IOPS and 125 MiB/s throughput at no extra cost. gp2 at 500 GB provides 1,500 baseline IOPS — gp3 at 3,000 IOPS is actually an upgrade. Zero downtime blue/green deployment.

---

## 5. Performance Metrics (30-Day Summary)

### 5a. CPU Utilization

| Domain | Average | Maximum | Minimum | Assessment |
|--------|---------|---------|---------|------------|
| luckycommon | 13.4% | 82% | 4% | Low avg, occasional spikes — appropriate sizing |
| luckylfe-log | 8.0% | 66% | 4% | Low utilization — potential downsize candidate |
| luckyur-log | 16.8% | **91%** | 5% | Heavy workload with high peak spikes |
| luckyus-opensearch-dify | 8.2% | 39% | 2% | **IDLE** — minimal activity |

### 5b. JVM Memory Pressure

| Domain | Average | Maximum | Assessment |
|--------|---------|---------|------------|
| luckycommon | 43.3% | 75.8% | Healthy — well under 80% threshold |
| luckylfe-log | 45.6% | 75.8% | Healthy |
| luckyur-log | **59.0%** | **76.6%** | Elevated — approaching 80% warning threshold |
| luckyus-opensearch-dify | 35.3% | 65.1% | Low — consistent with idle state |

### 5c. Search & Indexing Rates (requests/sec)

| Domain | Search Avg | Search Max | Index Avg | Index Max | Workload Profile |
|--------|-----------|-----------|-----------|-----------|------------------|
| luckycommon | 109 | 593 | 942 | 7,200 | Moderate read+write |
| luckylfe-log | 14 | 358 | 1,569 | 14,692 | Write-heavy (log ingestion) |
| luckyur-log | 485 | 4,593 | 37,190 | 192,495 | **Heavy read+write** |
| luckyus-opensearch-dify | 14 | 51 | **0.1** | 46 | **Near-zero write — IDLE** |

### 5d. Right-Sizing Assessment

| Domain | CPU Headroom | JVM Headroom | Verdict |
|--------|-------------|-------------|---------|
| **luckycommon** | High (avg 13%) | Good (43%) | Keep m5.large — migrate to m6g.large after RI expires |
| **luckylfe-log** | Very High (avg 8%) | Good (46%) | Could downsize to m5.medium, but savings minimal. Better: Graviton migration |
| **luckyur-log** | Moderate (avg 17%, peak 91%) | **Tight (59% avg, 77% peak)** | **Do NOT downsize** — already stressed at peak. Consider m5.2xlarge if growth continues |
| **luckyus-opensearch-dify** | Wasted (avg 8%, peak 39%) | Wasted (35%) | **Decommission entirely** |

---

## 6. Optimization Recommendations

### Summary Table

| # | Recommendation | Pre-EDP Savings | After-EDP Savings | Annual (EDP) | Effort | Priority |
|---|---------------|----------------|-------------------|-------------|--------|----------|
| 1 | Decommission luckyus-opensearch-dify | $549/mo | $379/mo | **$4,543** | Low | **P0** |
| 2 | gp2 → gp3 (luckylfe-log + luckyur-log) | $46/mo | $32/mo | **$384** | Low | **P1** |
| 3 | Graviton m6g.large after RI expiry (Aug 2026) | $140/mo | $97/mo | **$1,161** | Medium | **P2** |
| | **TOTAL** | **$735/mo** | **$508/mo** | **$6,088/yr** | | |

Current annual cost after EDP: **$21,731**
Projected annual cost after optimizations: **$15,643** (**28% reduction**)

---

### Recommendation 1: Decommission `luckyus-opensearch-dify` (P0)

**Savings**: $549/mo pre-EDP → **$379/mo after EDP → $4,543/yr**

**Evidence**:
- Idle since October 2025 (5+ months of zero meaningful activity)
- Indexing rate: 0.1/sec average (only internal heartbeats)
- CPU: 8.2% average — no application workload
- Storage: 78% empty (46.94 GiB free of 60 GiB)
- Master nodes ($300/mo) cost more than data nodes ($244/mo) — absurd overprovisioning

**Existing analysis**: `/app/reports/dify-elasticache-opensearch-idle-metrics-2026-03-25.md` confirms idle state with detailed metrics.

**Steps**:
1. Confirm with application team that Dify platform is fully decommissioned
2. Snapshot the domain for archival: `aws opensearch create-domain --domain-name luckyus-opensearch-dify-backup` (or just note the 13 GiB of data is negligible)
3. Delete domain: `aws opensearch delete-domain --domain-name luckyus-opensearch-dify --region us-east-1`
4. Also decommission associated Redis clusters (luckyus-redis-dify, luckyus-difynew) — see Dify idle report

---

### Recommendation 2: Migrate gp2 → gp3 Storage (P1)

**Savings**: $46/mo pre-EDP → **$32/mo after EDP → $384/yr**

**Domains**: luckylfe-log (320 GB) and luckyur-log (2,000 GB)

**Benefits beyond cost**:
- gp3 provides 3,000 baseline IOPS (vs gp2's size-dependent IOPS: 240 for 80GB, 1,500 for 500GB)
- gp3 includes 125 MiB/s throughput at no extra cost
- luckyur-log gets a 2× IOPS improvement (1,500 → 3,000)

**Steps**:
```bash
# luckylfe-log
aws opensearch update-domain-config \
  --domain-name luckylfe-log \
  --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=80,Iops=3000,Throughput=125 \
  --region us-east-1

# luckyur-log
aws opensearch update-domain-config \
  --domain-name luckyur-log \
  --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=500,Iops=3000,Throughput=125 \
  --region us-east-1
```

Blue/green deployment — zero downtime, ~30-60 minutes per domain.

---

### Recommendation 3: Graviton Migration After RI Expiry (P2)

**Savings**: $140/mo pre-EDP → **$97/mo after EDP → $1,161/yr**
**Timeline**: After m5.large RI expires ~August 27, 2026

**Migration path**: 8× m5.large.search → 8× m6g.large.search

| Metric | m5.large (current) | m6g.large (target) |
|--------|-------------------|-------------------|
| vCPU | 2 | 2 |
| Memory | 8 GiB | 8 GiB |
| On-Demand rate | $0.142/hr | $0.118/hr |
| After EDP (8 nodes) | $573/mo | $476/mo |

**Constraints**:
- luckycommon is ES 6.8 — **does NOT support Graviton** (requires ES 7.x or OpenSearch). Must upgrade engine first or skip this domain.
- luckylfe-log is ES 7.10 — supports m6g instances.
- Both domains share the 8× m5.large RI, so migration should happen simultaneously after RI expiry.

**Existing analysis**: `/app/opensearch-graviton-migration-analysis-2026-02-10.md`

---

### Not Recommended: New RI Purchases

| Scenario | RI Monthly | OD+EDP Monthly | Savings | Upfront | ROI |
|----------|-----------|----------------|---------|---------|-----|
| 4× m5.xlarge 1yr All Upfront | $537 | $581 | $44/mo | $6,444 | 8.2% |

The 31% EDP discount narrows the RI gap to the point where the upfront capital commitment and inflexibility aren't justified. This confirms the finding from the previous analysis in `/app/opensearch-master-node-cost-optimization-2026-02.md`.

---

## 7. Cost Category Breakdown (March 2026)

```
Instance Costs (73%)  ████████████████████████████████████░░  $1,915/mo pre-EDP
  ├── Data node RI (m5.large)     $583   (22%)
  ├── Data node OD (m5.xlarge)    $794   (30%)
  ├── Data node OD (r6g.large)    $234   (9%)
  ├── Master OD (m7g.large)       $284   (11%)
  ├── Master OD (t3.medium)       $307   (12%)  [WASTE: $284 dify masters]
  └── Master OD (t3.small)        $76    (3%)

Storage Costs (12%)   ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  $319/mo pre-EDP
  ├── gp2 (luckylfe + luckyur)    $266   (10%)
  └── gp3 (luckycommon + dify)    $53    (2%)

Data Transfer (<1%)   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  $0.12/mo
```

---

## Appendix A: On-Demand Pricing Reference (us-east-1)

| Instance Type | On-Demand/hr | After EDP/hr | Monthly (730h) | Monthly (EDP) |
|--------------|-------------|-------------|-----------------|---------------|
| m5.large.search | $0.142 | $0.098 | $103.66 | $71.52 |
| m5.xlarge.search | $0.288 | $0.199 | $210.24 | $145.07 |
| m6g.large.search | $0.118 | $0.081 | $86.14 | $59.44 |
| r6g.large.search | $0.167 | $0.115 | $121.91 | $84.12 |
| m7g.large.search | $0.137 | $0.095 | $100.01 | $69.01 |
| t3.small.search | $0.036 | $0.025 | $26.28 | $18.13 |
| t3.medium.search | $0.073 | $0.050 | $53.29 | $36.77 |

Storage: gp2 = $0.10/GB/mo, gp3 = $0.08/GB/mo (3,000 IOPS + 125 MiB/s included)

## Appendix B: Historical Cost Trend (After EDP)

```
$1,900 ┤
       │
$1,850 ┤          ┌──────┐
       │          │      │
$1,800 ┤          │      │  ┌──────┐
       │    ┌─────┤      │  │ Mar  │
$1,750 ┤    │ Nov │ Dec  │  │$1,792│
       │    │$1,740│$1,821│  └──────┘
$1,700 ┤ ┌──┤     │      │
       │ │  │     └──────┤
$1,650 ┤ │  │            │
       │ │Oct│           │Feb
$1,600 ┤ │$1,704         │$1,683
       │ └──┘            └──────┘
$1,550 ┤
       └────┴─────┴──────┴──────┴──────┴──────
         Oct   Nov   Dec   Jan   Feb   Mar
```

---

*Report generated 2026-03-30. Cost Explorer data is estimated for the current month (March 2026). All costs are in USD. EDP discount of 31% applied where noted.*
