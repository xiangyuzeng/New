# LCNA-DBA-2026-022: Phase A MySQL Minor Version Upgrade Plan

**MySQL 8.0.40/41 → 8.0.45 | 59 Instances | Luckin Coffee North America**

| Field | Value |
|-------|-------|
| Document ID | LCNA-DBA-2026-022 |
| Date | 2026-04-11 |
| Author | David Zeng (DBA) |
| Account | 257394478466 (us-east-1) |
| Target Version | **8.0.45** (confirmed latest available 8.0.x) |
| Deadline | **May 31, 2026** (AWS forced auto-upgrade) |
| Status | **READY TO EXECUTE** — discovery complete, script generated |

---

## 1. Executive Summary

Phase A upgrades all MySQL 8.0.40 and 8.0.41 RDS instances to 8.0.45 to eliminate the May 31, 2026 AWS forced auto-upgrade threat. This is a minor version upgrade — in-place restart with Multi-AZ failover, no compatibility changes, no parameter group migration needed.

### Fleet Snapshot (Live Data — 2026-04-11 20:41 UTC)

| Version | Count | Action |
|---------|-------|--------|
| **8.0.40** | **58** | **MUST UPGRADE** — affected by 5/31 EOL |
| **8.0.41** | **1** (ldas01) | **MUST UPGRADE** — affected by 5/31 EOL |
| 8.0.42 | 1 (dbatest) | Safe — optional consistency upgrade |
| 8.0.44 | 1 (iluckyams) | Safe — optional consistency upgrade |
| 8.4.7 | 2 (test instances) | Skip |
| **Total** | **63** | **59 must upgrade** |

### Key Findings

| Check | Result |
|-------|--------|
| Upgrade path validated | 8.0.40→8.0.45 and 8.0.41→8.0.45 (AWS API confirmed) |
| Pre-flight blockers | **NONE** — all 59 instances: available, in-sync, no pending changes |
| Recent production incidents (7d) | **NONE** — only 8.4 test instance restarts |
| OOM risk (RED) | **39 instances** (all db.t4g.micro, systemic) |
| OOM risk (YELLOW) | **1 instance** (upush, db.t4g.medium) |
| GREEN (safe) | **19 instances** (all medium/large/xlarge) |

---

## 2. Health Assessment — OOM Risk Analysis

### Overview

| Risk | Count | Criteria | Recommendation |
|------|-------|----------|----------------|
| RED | 39 | FreeableMemory < 150 MB | Systemic for 1GB tier — proceed with monitoring |
| YELLOW | 1 | FreeableMemory 150-300 MB | Proceed with caution |
| GREEN | 19 | FreeableMemory > 300 MB | Safe |

**39 RED instances are entirely db.t4g.micro (1GB RAM) + 1 db.t3.small (2GB RAM)**. This is the fleet's chronic operating state, not an upgrade-specific risk. Precedent: `iluckyams-rw` successfully auto-upgraded 8.0.42→8.0.44 on March 31 with only 83-148 MB free memory and 437 MB swap.

### Top 5 Highest-Risk Instances

| Instance | Class | RAM | FreeMemMin | SwapAvg | Notes |
|----------|-------|-----|-----------|---------|-------|
| **iluckyhealth** | db.t3.small | 2GB | **46 MB** | 870 MB | Worst in fleet. 2GB but behaves like micro |
| opqualitycontrol | db.t4g.micro | 1GB | 63 MB | 746 MB | |
| opshopsale | db.t4g.micro | 1GB | 81 MB | 649 MB | |
| scm-ordering | db.t4g.micro | 1GB | 83 MB | 765 MB | |
| **iriskcontrolservice** | db.t4g.micro | 1GB | 90 MB | **1,224 MB** | Highest swap in fleet |

### All GREEN Instances (medium/large/xlarge)

| Instance | Class | RAM | FreeMemMin | SwapAvg |
|----------|-------|-----|-----------|---------|
| opshop | db.t4g.medium | 4GB | 2,224 MB | 0 MB |
| scmcommodity | db.t4g.medium | 4GB | 2,054 MB | 0 MB |
| salescrm | db.t4g.medium | 4GB | 1,790 MB | 0 MB |
| salespayment | db.t4g.medium | 4GB | 1,683 MB | 0 MB |
| devops | db.t4g.medium | 4GB | 1,600 MB | 7 MB |
| framework01 | db.t4g.medium | 4GB | 1,584 MB | 26 MB |
| iotplatform | db.t4g.medium | 4GB | 1,496 MB | 3 MB |
| salesmarketing | db.t4g.xlarge | 16GB | 1,460 MB | 204 MB |
| ldas | db.t4g.large | 8GB | 1,026 MB | 312 MB |
| isalescdp | db.t4g.medium | 4GB | 1,018 MB | 0 MB |
| framework02 | db.t4g.medium | 4GB | 1,001 MB | 88 MB |
| isalesprivatedomain | db.t4g.medium | 4GB | 639 MB | 135 MB |
| isalesdatamarketing | db.t4g.medium | 4GB | 619 MB | 488 MB |
| ldas01 | db.t4g.large | 8GB | 599 MB | 219 MB |
| icyberdata | db.t4g.medium | 4GB | 567 MB | 1,399 MB |
| scm-shopstock | db.t4g.medium | 4GB | 461 MB | 331 MB |
| iworkflowmidlayer | db.t4g.medium | 4GB | 458 MB | 191 MB |
| cdpactivity | db.t4g.medium | 4GB | 457 MB | 368 MB |
| salesorder | db.t4g.medium | 4GB | 375 MB | 214 MB |

### Post-Upgrade Risk: Buffer Pool Reduction

After restart, AWS may auto-reduce `innodb_buffer_pool_size` to 128 MB on memory-pressured instances (observed in Jan 31 iworkflowmidlayer and Mar 12 isalescdp incidents). **Post-upgrade check required**:

```sql
-- Run via MCP on any instance with FreeableMemory < 100 MB after upgrade:
SHOW GLOBAL VARIABLES LIKE 'innodb_buffer_pool_size';
-- If value = 134217728 (128 MB) → CRITICAL, needs immediate remediation
```

---

## 3. Batch Plan

### Batch 1 — PILOT (DBA Internal Analytics) — 2 instances | ~40 min

| # | Instance | Version | Class | RAM | Storage | ParamGroup | FreeMem | Risk |
|---|----------|---------|-------|-----|---------|------------|---------|------|
| 1 | ldas | 8.0.40 | db.t4g.large | 8GB | 30GB | luckyus-prod | 1,026 MB | GREEN |
| 2 | ldas01 | 8.0.41 | db.t4g.large | 8GB | 128GB | luckyus-prod-80-new | 599 MB | GREEN |

**Purpose**: Validate upgrade procedure and timing. Zero business impact.

### Batch 2 — LOW-RISK INTERNAL TOOLS — 37 instances | ~5.7 hr

All 37 are db.t4g.micro (1GB RAM). Internal tools, SCM support, DevOps.

| # | Instance | FreeMem | Swap | # | Instance | FreeMem | Swap |
|---|----------|---------|------|---|----------|---------|------|
| 1 | fichargecontrol | 87 MB | 565 MB | 20 | ireplenishment | 87 MB | 648 MB |
| 2 | fitax | 93 MB | 394 MB | 21 | iriskcontrolservice | 90 MB | 1224 MB |
| 3 | iadmin | 96 MB | 510 MB | 22 | iunifiedreconcile | 101 MB | 426 MB |
| 4 | ibillingcentersrv | 90 MB | 680 MB | 23 | mfranchise | 100 MB | 461 MB |
| 5 | ibizconfigcenter | 99 MB | 434 MB | 24 | opempefficiency | 89 MB | 546 MB |
| 6 | iehr | 90 MB | 557 MB | 25 | oplog | 93 MB | 409 MB |
| 7 | ifiaccounting | 93 MB | 865 MB | 26 | opproduction | 88 MB | 603 MB |
| 8 | igers | 104 MB | 398 MB | 27 | opqualitycontrol | 63 MB | 746 MB |
| 9 | ijumpserver | 90 MB | 624 MB | 28 | opshopsale | 81 MB | 649 MB |
| 10 | ilsopdevopsdata | 98 MB | 380 MB | 29 | pubdm | 87 MB | 505 MB |
| 11 | iluckyauthapi | 98 MB | 403 MB | 30 | scm-asset | 94 MB | 594 MB |
| 12 | iluckydorisops | 95 MB | 407 MB | 31 | scm-openapi | 93 MB | 579 MB |
| 13 | iluckymedia | 98 MB | 415 MB | 32 | scm-ordering | 83 MB | 765 MB |
| 14 | iopenadmin | 103 MB | 420 MB | 33 | scm-plan | 93 MB | 470 MB |
| 15 | iopenlinker | 90 MB | 502 MB | 34 | scm-purchase | 91 MB | 792 MB |
| 16 | iopenservice | 96 MB | 406 MB | 35 | scm-wds | 91 MB | 716 MB |
| 17 | iopocp | 91 MB | 619 MB | 36 | scm-wmssimulate | 90 MB | 535 MB |
| 18 | iopshopexpand | 99 MB | 428 MB | 37 | scmsrm | 90 MB | 730 MB |
| 19 | ipermission | 90 MB | 591 MB | | | | |

**Note**: Exceeds single 4-hour window. Split: Evening 1 (#1-20), Evening 2 (#21-37).

### Batch 3 — OPS/FINANCE + MEDIUM INSTANCES — 9 instances | ~2.0 hr

| # | Instance | Version | Class | RAM | Storage | FreeMem | Risk |
|---|----------|---------|-------|-----|---------|---------|------|
| 1 | isalesmembermarketing | 8.0.40 | db.t4g.micro | 1GB | 20GB | 94 MB | RED |
| 2 | **iluckyhealth** | 8.0.40 | db.t3.small | **2GB** | 50GB | **46 MB** | **RED** |
| 3 | devops | 8.0.40 | db.t4g.medium | 4GB | 20GB | 1,600 MB | GREEN |
| 4 | iotplatform | 8.0.40 | db.t4g.medium | 4GB | 20GB | 1,496 MB | GREEN |
| 5 | iworkflowmidlayer | 8.0.40 | db.t4g.medium | 4GB | 20GB | 458 MB | GREEN |
| 6 | opshop | 8.0.40 | db.t4g.medium | 4GB | 20GB | 2,224 MB | GREEN |
| 7 | scm-shopstock | 8.0.40 | db.t4g.medium | 4GB | 30GB | 461 MB | GREEN |
| 8 | scmcommodity | 8.0.40 | db.t4g.medium | 4GB | 20GB | 2,054 MB | GREEN |
| 9 | upush | 8.0.40 | db.t4g.medium | 4GB | 40GB | 251 MB | YELLOW |

**Watch**: iluckyhealth (46 MB free — worst in fleet), upush (YELLOW), iworkflowmidlayer (P0 OOM history Jan 31 — now stable on medium)

### Batch 5 — CORE FRAMEWORK (ONE AT A TIME) — 2 instances | ~36 min

| # | Instance | Version | Class | RAM | Storage | FreeMem | Risk |
|---|----------|---------|-------|-----|---------|---------|------|
| 1 | framework01 | 8.0.40 | db.t4g.medium | 4GB | 20GB | 1,584 MB | GREEN |
| 2 | framework02 | 8.0.40 | db.t4g.medium | 4GB | 40GB | 1,001 MB | GREEN |

**Protocol**: Upgrade ONE AT A TIME. After each, verify via MCP:
```sql
SELECT @@version, @@sql_mode, @@character_set_server;
SHOW GLOBAL STATUS LIKE 'Threads_connected';
SHOW GLOBAL STATUS LIKE 'Aborted_%';
SHOW GLOBAL STATUS LIKE 'Max_used_connections';
```

### Batch 6 — SALES + MARKETING CORE — 9 instances | ~2.2 hr

| # | Instance | Version | Class | RAM | Storage | ParamGroup | FreeMem | Risk |
|---|----------|---------|-------|-----|---------|------------|---------|------|
| 1 | cdpactivity | 8.0.40 | medium | 4GB | 40GB | luckyus-prod-80-new | 457 MB | GREEN |
| 2 | icyberdata | 8.0.40 | medium | 4GB | **635GB** | luckyus-prod-80-new | 567 MB | GREEN |
| 3 | isalescdp | 8.0.40 | medium | 4GB | 40GB | luckyus-prod-80-new | 1,018 MB | GREEN |
| 4 | isalesdatamarketing | 8.0.40 | medium | 4GB | 40GB | luckyus-prod-80-new | 619 MB | GREEN |
| 5 | isalesprivatedomain | 8.0.40 | medium | 4GB | 20GB | luckyus-prod-80-new | 639 MB | GREEN |
| 6 | salescrm | 8.0.40 | medium | 4GB | 20GB | luckyus-prod-80-new | 1,790 MB | GREEN |
| 7 | salespayment | 8.0.40 | medium | 4GB | 20GB | luckyus-prod-80-new | 1,683 MB | GREEN |
| 8 | **salesorder** | 8.0.40 | medium | 4GB | 20GB | **groupconcatmaxlen** | 375 MB | GREEN |
| 9 | **salesmarketing** | 8.0.40 | **xlarge** | **16GB** | **100GB** | luckyus-prod-80-new | 1,460 MB | GREEN |

**Special post-upgrade checks**:
- **salesorder**: `SHOW VARIABLES LIKE 'group_concat_max_len'` must be `1048576`
- **isalescdp**: Extended CloudWatch FreeableMemory check (P0 OOM history Mar 12)
- **salesmarketing**: Full MCP + CloudWatch CPU/Memory verification (largest instance)
- **icyberdata**: 635GB storage — in-place upgrade, storage size has no impact

---

## 4. Parameter Group Reference (Pre-Upgrade Baseline)

### luckyus-prod (devops-rw, ldas-rw) — 22 custom params

| Parameter | Value |
|-----------|-------|
| binlog_checksum | CRC32 |
| binlog_format | ROW |
| binlog_order_commits | 0 |
| binlog_row_image | full |
| character_set_server | utf8mb4 |
| enforce_gtid_consistency | ON |
| gtid-mode | ON |
| innodb_adaptive_hash_index | 0 |
| innodb_deadlock_detect | 1 |
| innodb_lock_wait_timeout | 20 |
| innodb_print_all_deadlocks | 1 |
| innodb_strict_mode | 0 |
| log_output | FILE |
| long_query_time | 0.1 |
| max_connections | 4000 |
| performance_schema | 1 |
| slow_query_log | 1 |
| sql_mode | STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION |
| transaction_isolation | READ-COMMITTED |
| optimizer_switch | ...prefer_ordering_index=off |

### luckyus-prod-80-new (56 instances) — 25 custom params

Same as above **plus**:
- `log_bin_trust_function_creators = 1`
- `lower_case_table_names = 1`
- `binlog_rows_query_log_events = 0`
- `log_queries_not_using_indexes = 0`
- `log_slow_admin_statements = 0`

### luckyus-prod-80-new-groupconcatmaxlen (salesorder-rw) — 26 params

Same as luckyus-prod-80-new **plus**:
- **`group_concat_max_len = 1048576`**

---

## 5. Timeline & Schedule

### Timing by Instance Class

| Class | Count | Avg Time | Range |
|-------|-------|----------|-------|
| db.t4g.micro | 42 | 6 min | 5-8 min |
| db.t3.small | 1 | 8 min | 6-10 min |
| db.t4g.medium | 14 | 10 min | 8-12 min |
| db.t4g.large | 2 | 12 min | 10-15 min |
| db.t4g.xlarge | 1 | 15 min | 12-18 min |

### Recommended Schedule (3-4 Evenings)

| Evening | UTC Window | Batches | Instances | Est. Duration |
|---------|-----------|---------|-----------|---------------|
| **1** | 06:00-10:00 | Batch 1 + Batch 2 (first 20) | 22 | ~3.5 hr |
| **2** | 06:00-10:00 | Batch 2 (remaining 17) + Batch 3 | 26 | ~3.8 hr |
| **3** | 06:00-10:00 | Batch 5 + Batch 6 | 11 | ~2.8 hr |

**AVOID**: 04:30-05:30 UTC (daily batch processing at 05:00 UTC / 00:00 EST)

---

## 6. Execution Script

A ready-to-run bash script is provided at:

```
/home/claude/phase-a/phase-a-upgrade.sh
```

### Prerequisites
1. **IAM Permission**: The executing user/role needs `rds:ModifyDBInstance` and `rds:DescribeDBInstances`
   - Current user `databasecheck` has read-only access — needs write permission or a different profile
   - Option: `export AWS_PROFILE=<write-capable-profile>` before running

2. **Usage**:
   ```bash
   ./phase-a-upgrade.sh 1      # Batch 1 only (pilot)
   ./phase-a-upgrade.sh 2      # Batch 2 only
   ./phase-a-upgrade.sh 3      # Batch 3 only
   ./phase-a-upgrade.sh 5      # Batch 5 (framework, one at a time)
   ./phase-a-upgrade.sh 6      # Batch 6 (sales/marketing)
   ./phase-a-upgrade.sh verify # Post-upgrade fleet verification
   ./phase-a-upgrade.sh all    # All batches sequentially
   ```

### Safety Controls (Built into Script)
- Operator confirmation prompt before each batch
- Per-instance pre-check: version, status, pending mods, FreeableMemory
- FreeableMemory < 100 MB → interactive warning with skip option
- Post-upgrade verification: version, status, param group unchanged, param in-sync
- Max 2 failures per batch → automatic halt
- All actions timestamped in `execution.log`

---

## 7. Upgrade Path Confirmation

| Source | Target | Valid | Type | AWS API Verified |
|--------|--------|-------|------|-----------------|
| 8.0.40 | 8.0.45 | YES | Minor (in-place) | `describe-db-engine-versions` |
| 8.0.41 | 8.0.45 | YES | Minor (in-place) | `describe-db-engine-versions` |

Available 8.0.x versions: 8.0.40, 8.0.41, 8.0.42, 8.0.43, 8.0.44, **8.0.45** (latest)

---

## 8. Category B — Optional Consistency Upgrade

After Phase A completes, optionally upgrade for fleet uniformity:

| Instance | Current | Target | Blocker |
|----------|---------|--------|---------|
| dbatest-rw | 8.0.42 | 8.0.45 | param pending-reboot (resolve first) |
| iluckyams-rw | 8.0.44 | 8.0.45 | Chronic memory pressure on micro (46-148 MB free) |

---

## 9. Phase B Prerequisites Checklist

After Phase A eliminates the 5/31 threat, prepare for Phase B (8.0.45 → 8.4.8):

| # | Task | Priority | Status |
|---|------|----------|--------|
| 1 | Create `luckyus-prod-84-new` param group (mysql8.4 family, 25 params + mysql_native_password=ON) | Critical | Not started |
| 2 | Create `luckyus-prod-84-new-groupconcatmaxlen` for salesorder | Critical | Not started |
| 3 | Update Prometheus exporter: `SHOW SLAVE STATUS` → `SHOW REPLICA STATUS` | Critical | Tested on dba84test |
| 4 | Grant `REPLICATION CLIENT` to diagtools user on all instances | High | Not started |
| 5 | Evaluate salesorder memory (375 MB avg free) — consider upsizing | Medium | Monitored |
| 6 | Switch dba84test/datalink-84test from `default.mysql8.4` to `luckyus-prod-84-new` | Medium | Not started |
| 7 | Coordinate Phase B schedule with Ops team and CTO Michael | High | Not started |
| 8 | **Extended Support cost if Phase B delayed past 7/31: ~$9,957/month** | — | — |

Extended Support calculation: $0.11/vCPU-hr × 124 total vCPU × 730 hr/month = $9,957/month

---

## 10. Discovery Output Files

All in `/home/claude/phase-a/`:

| File | Size | Description |
|------|------|-------------|
| `fleet-inventory.json` | 36 KB | Raw AWS API: all 63 MySQL instances with full metadata |
| `available-80-versions.txt` | 0.3 KB | Available 8.0.x versions (8.0.40-8.0.45) |
| `upgrade-path-validation.txt` | 0.5 KB | API-confirmed: 8.0.40→8.0.45, 8.0.41→8.0.45 |
| `classification.txt` | 6 KB | Category A (59), B (2), C (2), D (0) with full details |
| `pre-flight-blockers.txt` | 0.1 KB | No blockers found |
| `health-assessment.txt` | 5 KB | FreeableMemory/SwapUsage per instance, sorted by risk |
| `health-raw.json` | 241 KB | Raw CloudWatch metric data (118 queries, 24h) |
| `health-data.json` | 12 KB | Parsed health metrics as JSON |
| `recent-incidents.txt` | 0.5 KB | Past 7 days: only 8.4 test restarts |
| `param-groups-pre-upgrade.txt` | 34 KB | All 3 param groups' custom settings |
| `batch-plan.txt` | 8 KB | Complete batch assignments with health status |
| `batch-assignments.json` | 5 KB | Machine-readable batch data |
| `timeline-estimate.txt` | 1 KB | Per-batch and total time estimates |
| `cat_a_data.json` | 15 KB | Category A instance data |
| `phase-a-upgrade.sh` | 10 KB | Ready-to-run upgrade script with safety controls |

---

*Report generated 2026-04-11 by Claude Code. All data sourced live from AWS APIs (describe-db-instances, describe-db-engine-versions, cloudwatch get-metric-data, describe-events, describe-db-parameters).*
