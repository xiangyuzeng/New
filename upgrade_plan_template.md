# MySQL 8.0 to 8.4 Upgrade Runbook — Blue/Green Deployment

**Date**: 2026-04-02 | **Account**: 257394478466 | **Region**: us-east-1
**Prepared by**: David Zeng (DBA/Infrastructure)
**Deadline**: May 31, 2026 (minor version EOL) | July 31, 2026 (MySQL 8.0 end of standard support)

---

## 1. Project Overview

| Item | Detail |
|------|--------|
| Scope | 61 MySQL RDS instances (59 on EOL versions 8.0.40/8.0.41) |
| Current versions | 8.0.40 (58), 8.0.41 (1), 8.0.42 (1), 8.0.44 (1) |
| Target version | 8.4.8 (latest LTS) |
| Upgrade method | RDS Blue/Green Deployment (primary) or In-Place (fallback) |
| Downtime per instance | ~30 seconds (Blue/Green switchover) |
| Timeline | 5 batches over 4-6 weeks |
| Rollback capability | Delete green before switchover (zero impact); restore from snapshot post-switchover |

### Upgrade Path
```
8.0.40 ──→ 8.4.8 (direct major version upgrade supported)
8.0.41 ──→ 8.4.8 (direct major version upgrade supported)
8.0.42 ──→ 8.4.8 (direct major version upgrade supported)
8.0.44 ──→ 8.4.8 (direct major version upgrade supported)
```

### Why 8.4.8 Instead of 8.4.7?

AWS console defaults to 8.4.7 when creating new instances, but **8.4.8 is already available** and is the better target.

| Item | 8.4.7 | 8.4.8 |
|------|-------|-------|
| Community release | 2025-10-21 | 2026-01-20 |
| RDS availability | 2025-11-13 | 2026-02-03 |
| Standard support ends | 2026-11-30 | 2027-02-03 |

Key changes in 8.4.8 over 8.4.7:
- **Security patches**: Oracle January 2026 Critical Patch Update (CPU)
- **Audit log fix**: resolved an issue where some SQL statements were not logged
- **Timezone data**: updated to `tzdata2025c`
- Standard community bug fixes

Both `8.0.40 → 8.4.8` and `8.0.40 → 8.4.7` are supported direct upgrade paths. We choose 8.4.8 for the latest security patches and longer standard support window (+2 months).

### AWS RDS MySQL Version Lifecycle (Key Dates)

Source: `aws rds describe-db-major-engine-versions --engine mysql` (verified 2026-04-02)

| Major Version | Standard Support Ends | Extended Support Starts | Extended Support Cost | Extended Support Ends |
|--------------|----------------------|------------------------|----------------------|----------------------|
| MySQL 5.7 | 2024-02-29 (ended) | 2024-03-01 | $0.11/vCPU-hour | 2027-02-28 |
| **MySQL 8.0** | **2026-07-31** | **2026-08-01** | **$0.11/vCPU-hour** | **2029-07-31** |
| MySQL 8.4 LTS | 2029-07-31 | 2029-08-01 | $0.11/vCPU-hour | 2032-07-31 |

**Two separate deprecation mechanisms are at play:**

1. **Minor version EOL (May 31, 2026)**: AWS Health Event targets specific versions 8.0.40/8.0.41 only. Versions 8.0.42-8.0.45 are NOT on this list. Upgrading to 8.0.45 removes this immediate auto-upgrade threat.

2. **Major version end of standard support (July 31, 2026)**: The entire MySQL 8.0 family (including 8.0.45) loses standard support. AWS auto-enrolls all 8.0.x instances in Extended Support at $0.11/vCPU-hour. Instances can still run but incur extra charges.

| Date | Event | On 8.0.40 | On 8.0.45 | On 8.4.8 |
|------|-------|-----------|-----------|----------|
| May 31, 2026 | Minor version EOL | AUTO-UPGRADED (downtime!) | Safe | Safe |
| Aug 1, 2026 | 8.0 enters Extended Support | Extra charges | Extra charges | Free |
| Jul 31, 2029 | 8.0 Extended Support ends | Must be on 8.4+ | Must be on 8.4+ | Safe |

### Two-Phase Strategy

**Phase A (Immediate — by April 30)**: Upgrade all 59 EOL instances from 8.0.40/8.0.41 to **8.0.45** (latest minor). This removes the May 31 forced auto-upgrade threat. Simple minor version upgrade: 5-10 min downtime, no compatibility changes. Note: 8.0.45 still falls under MySQL 8.0 major version, which enters Extended Support ($0.11/vCPU-hour) on August 1, 2026.

**Phase B (Must complete by July 31)**: Upgrade all 61 instances from 8.0.45 to **8.4.8 LTS** via Blue/Green Deployments. This eliminates Extended Support charges and provides standard support until 2029-07-31. Major version upgrade requires careful testing — 5 batches over 4-6 weeks.

**Why not skip Phase A and go directly to 8.4?** Blue/Green deployment for 59 instances takes 4-6 weeks. With only ~4 weeks until May 31, we cannot complete 8.4 migration for all instances in time. Phase A (minor upgrade, 5-10 min each, can do 10-15/night) can finish in 1 week.

---

## 2. Prerequisites — Must Complete Before Any Upgrade

### 2.1 Create MySQL 8.4 Parameter Groups

```bash
# Primary parameter group (mirrors luckyus-prod-80-new)
aws rds create-db-parameter-group \
  --db-parameter-group-name luckyus-prod-84 \
  --db-parameter-group-family mysql8.4 \
  --description "Luckin US Production MySQL 8.4 - migrated from luckyus-prod-80-new" \
  --region us-east-1

# Secondary (mirrors luckyus-prod for devops/ldas)
aws rds create-db-parameter-group \
  --db-parameter-group-name luckyus-prod-84-infra \
  --db-parameter-group-family mysql8.4 \
  --description "Luckin US Infrastructure MySQL 8.4 - migrated from luckyus-prod" \
  --region us-east-1

# Special (mirrors luckyus-prod-80-new-groupconcatmaxlen for salesorder)
aws rds create-db-parameter-group \
  --db-parameter-group-name luckyus-prod-84-groupconcatmaxlen \
  --db-parameter-group-family mysql8.4 \
  --description "Luckin US MySQL 8.4 with group_concat_max_len" \
  --region us-east-1
```

### 2.2 Configure 8.4 Parameter Groups

Apply the 25 custom parameters from `luckyus-prod-80-new` to the new 8.4 groups. Key parameters:

```bash
aws rds modify-db-parameter-group \
  --db-parameter-group-name luckyus-prod-84 \
  --parameters \
    "ParameterName=binlog_checksum,ParameterValue=CRC32,ApplyMethod=immediate" \
    "ParameterName=binlog_format,ParameterValue=ROW,ApplyMethod=immediate" \
    "ParameterName=binlog_order_commits,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=binlog_row_image,ParameterValue=full,ApplyMethod=immediate" \
    "ParameterName=binlog_rows_query_log_events,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=character_set_server,ParameterValue=utf8mb4,ApplyMethod=immediate" \
    "ParameterName=enforce_gtid_consistency,ParameterValue=ON,ApplyMethod=pending-reboot" \
    "ParameterName=gtid-mode,ParameterValue=ON,ApplyMethod=pending-reboot" \
    "ParameterName=innodb_adaptive_hash_index,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=innodb_deadlock_detect,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=innodb_lock_wait_timeout,ParameterValue=20,ApplyMethod=immediate" \
    "ParameterName=innodb_print_all_deadlocks,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=innodb_strict_mode,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=log_bin_trust_function_creators,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=log_output,ParameterValue=FILE,ApplyMethod=immediate" \
    "ParameterName=log_queries_not_using_indexes,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=log_slow_admin_statements,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=long_query_time,ParameterValue=0.1,ApplyMethod=immediate" \
    "ParameterName=lower_case_table_names,ParameterValue=1,ApplyMethod=pending-reboot" \
    "ParameterName=max_connections,ParameterValue=4000,ApplyMethod=immediate" \
    "ParameterName=performance_schema,ParameterValue=1,ApplyMethod=pending-reboot" \
    "ParameterName=slow_query_log,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=sql_mode,ParameterValue='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION',ApplyMethod=immediate" \
    "ParameterName=transaction_isolation,ParameterValue=READ-COMMITTED,ApplyMethod=immediate" \
    "ParameterName=mysql_native_password,ParameterValue=ON,ApplyMethod=pending-reboot" \
  --region us-east-1
```

Note: `mysql_native_password=ON` ensures backward compatibility during migration. Set to OFF after migrating all users to `caching_sha2_password`.

### 2.3 Adjust Maintenance Windows

Move all 35 instances with peak-hour maintenance windows to 02:00-06:00 UTC. See `maintenance_window_report.md` for commands.

### 2.4 Verify Application Driver Compatibility

Ensure all applications use MySQL Connector/J 8.0.12+ (Java), PyMySQL 1.0+ (Python), or equivalent drivers that support `caching_sha2_password`.

---

## 3. Go/No-Go Criteria

### Go Criteria (all must be met)
- [ ] MySQL 8.4 parameter groups created and tested
- [ ] Maintenance windows adjusted to 02:00-06:00 UTC
- [ ] Manual snapshot taken of target instance
- [ ] No active incidents or high-priority alerts
- [ ] Ops team notified and available during upgrade window
- [ ] Application owners confirmed awareness
- [ ] Batch 0 (test instances) completed successfully with 72-hour soak

### No-Go Criteria (any triggers postponement)
- Active production incident
- RDS prechecks fail (upgrade automatically cancelled)
- Application team unavailable for validation
- Unusual load pattern (campaigns, promotions)
- Daily batch job window overlap (05:00 UTC)

---

## 4. Batch Schedule

### Batch 0: Test Instances (Week 1)
| Instance | Version | Class | Risk |
|----------|---------|-------|------|
| aws-luckyus-dbatest-rw | 8.0.42 | db.t4g.micro | LOW |

**Purpose**: Validate full upgrade procedure. Run all post-upgrade checks. 72-hour soak period.

### Batch 1: Infrastructure & DevOps (Week 2)
| Instance | Version | Class | Risk |
|----------|---------|-------|------|
| aws-luckyus-devops-rw | 8.0.40 | db.t4g.medium | MEDIUM |
| aws-luckyus-framework01-rw | 8.0.40 | db.t4g.medium | MEDIUM |
| aws-luckyus-framework02-rw | 8.0.40 | db.t4g.medium | MEDIUM |
| aws-luckyus-ldas-rw | 8.0.40 | db.t4g.large | MEDIUM |
| aws-luckyus-ldas01-rw | 8.0.41 | db.t4g.large | MEDIUM |
| aws-luckyus-iluckyhealth-rw | 8.0.40 | db.t3.small | MEDIUM |
| aws-luckyus-iluckydorisops-rw | 8.0.40 | db.t4g.micro | LOW |
| aws-luckyus-ijumpserver-jumpserver-rw | 8.0.40 | db.t4g.micro | LOW |
| aws-luckyus-oplog-rw | 8.0.40 | db.t4g.micro | LOW |

### Batch 2: Low-Traffic Production (Week 3-4)
42 instances — all db.t4g.micro with 20 GB storage. Upgrade 10-15 per night.

Includes: All SCM, Operations, Finance, HR, Platform micro instances.

### Batch 3: Medium-Traffic Production (Week 4-5)
| Instance | Version | Class | Risk |
|----------|---------|-------|------|
| aws-luckyus-upush-rw | 8.0.40 | db.t4g.medium | HIGH |
| aws-luckyus-cdpactivity-rw | 8.0.40 | db.t4g.medium | MEDIUM |
| aws-luckyus-icyberdata-rw | 8.0.40 | db.t4g.medium | HIGH |
| aws-luckyus-iotplatform-rw | 8.0.40 | db.t4g.medium | MEDIUM |
| aws-luckyus-opshop-rw | 8.0.40 | db.t4g.medium | HIGH |
| aws-luckyus-isalesprivatedomain-rw | 8.0.40 | db.t4g.medium | MEDIUM |
| aws-luckyus-isalesmembermarketing-rw | 8.0.40 | db.t4g.micro | MEDIUM |
| aws-luckyus-iluckyams-rw | 8.0.44 | db.t4g.micro | MEDIUM |
| aws-luckyus-scm-shopstock-rw | 8.0.40 | db.t4g.medium | MEDIUM |
| aws-luckyus-scmcommodity-rw | 8.0.40 | db.t4g.medium | MEDIUM |

### Batch 4: Critical Sales Production (Week 5-6)
| Instance | Version | Class | Size | Risk |
|----------|---------|-------|------|------|
| aws-luckyus-salesmarketing-rw | 8.0.40 | db.t4g.xlarge | 43.7 GB | HIGH |
| aws-luckyus-salesorder-rw | 8.0.40 | db.t4g.medium | 4.6 GB | HIGH |
| aws-luckyus-salescrm-rw | 8.0.40 | db.t4g.medium | - | HIGH |
| aws-luckyus-salespayment-rw | 8.0.40 | db.t4g.medium | - | HIGH |
| aws-luckyus-isalescdp-rw | 8.0.40 | db.t4g.medium | - | HIGH |
| aws-luckyus-isalesdatamarketing-rw | 8.0.40 | db.t4g.medium | - | HIGH |

---

## 5. Per-Instance Blue/Green Deployment Procedure

### T-48h: Pre-Upgrade Preparation

```bash
INSTANCE="aws-luckyus-<service>-rw"

# 1. Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier $INSTANCE \
  --db-snapshot-identifier ${INSTANCE}-pre-84-upgrade-$(date +%Y%m%d) \
  --region us-east-1

# 2. Verify no pending modifications
aws rds describe-db-instances \
  --db-instance-identifier $INSTANCE \
  --region us-east-1 \
  --query 'DBInstances[0].PendingModifiedValues'

# 3. Record baseline metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=$INSTANCE \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average --region us-east-1

# 4. Run compatibility check via MCP
# SELECT @@version, @@sql_mode, @@default_authentication_plugin;
# SELECT user, host, plugin FROM mysql.user WHERE plugin='mysql_native_password';
```

### T-24h: Create Blue/Green Deployment

```bash
INSTANCE="aws-luckyus-<service>-rw"
INSTANCE_ARN="arn:aws:rds:us-east-1:257394478466:db:$INSTANCE"

aws rds create-blue-green-deployment \
  --blue-green-deployment-name "${INSTANCE}-84-upgrade" \
  --source "$INSTANCE_ARN" \
  --target-engine-version "8.4.8" \
  --target-db-parameter-group-name "luckyus-prod-84" \
  --region us-east-1
```

### T-24h to T-0: Monitor Green Environment

```bash
# Check Blue/Green deployment status
aws rds describe-blue-green-deployments \
  --region us-east-1 \
  --query "BlueGreenDeployments[?BlueGreenDeploymentName=='${INSTANCE}-84-upgrade']"

# Verify green instance is available
# Verify replication lag is 0
# Run test queries against green endpoint to validate
```

### T-0: Switchover (During Maintenance Window, 02:00-06:00 UTC)

```bash
DEPLOYMENT_ID="<blue-green-deployment-id>"

aws rds switchover-blue-green-deployment \
  --blue-green-deployment-identifier "$DEPLOYMENT_ID" \
  --switchover-timeout 300 \
  --region us-east-1
```

### T+0 to T+1h: Post-Switchover Validation

```sql
-- Via mcp-db-gateway: verify version
SELECT @@version, @@hostname, @@default_authentication_plugin;

-- Verify all users can authenticate
SELECT user, host, plugin FROM mysql.user LIMIT 50;

-- Check for errors
SHOW GLOBAL STATUS LIKE 'Aborted_%';

-- Verify key parameters
SHOW VARIABLES WHERE Variable_name IN (
  'innodb_buffer_pool_size', 'max_connections', 'sql_mode',
  'character_set_server', 'lower_case_table_names', 'gtid_mode'
);
```

```bash
# CloudWatch — verify no error spike
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=$INSTANCE \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average Maximum --region us-east-1
```

### T+1h to T+72h: Soak Period

- Monitor error logs via CloudWatch Logs Insights
- Compare metrics against pre-upgrade baseline
- Watch for application errors (check with ops team)
- Monitor slow query log for new patterns

### T+72h: Cleanup

```bash
# Delete Blue/Green deployment (keeps both instances, deletes deployment metadata)
aws rds delete-blue-green-deployment \
  --blue-green-deployment-identifier "$DEPLOYMENT_ID" \
  --delete-target false \
  --region us-east-1

# Optionally delete the old (blue) instance after confirmed stable
# aws rds delete-db-instance --db-instance-identifier "${INSTANCE}-old" --skip-final-snapshot --region us-east-1
```

---

## 6. Rollback Procedure

### Before Switchover (preferred — zero impact)
```bash
# Simply delete the green deployment
aws rds delete-blue-green-deployment \
  --blue-green-deployment-identifier "$DEPLOYMENT_ID" \
  --delete-target true \
  --region us-east-1
```
Production (blue) instance is untouched. Zero downtime.

### After Switchover (emergency — 15-30 min downtime)
```bash
# 1. Restore from pre-upgrade snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier ${INSTANCE}-restored \
  --db-snapshot-identifier ${INSTANCE}-pre-84-upgrade-$(date +%Y%m%d) \
  --db-instance-class <ORIGINAL_CLASS> \
  --region us-east-1

# 2. Wait for instance to become available
aws rds wait db-instance-available \
  --db-instance-identifier ${INSTANCE}-restored \
  --region us-east-1

# 3. Update application connection to restored instance
# (coordinate with ops team for DNS/endpoint change)

# 4. Rename instances to restore original names
aws rds modify-db-instance \
  --db-instance-identifier $INSTANCE \
  --new-db-instance-identifier ${INSTANCE}-bad-upgrade \
  --apply-immediately --region us-east-1

aws rds modify-db-instance \
  --db-instance-identifier ${INSTANCE}-restored \
  --new-db-instance-identifier $INSTANCE \
  --apply-immediately --region us-east-1
```

---

## 7. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | RDS prechecks fail, blocking upgrade | Medium | Low | Prechecks run before downtime. Review PrePatchCompatibility.log and fix issues. |
| R2 | Application authentication failure post-upgrade | Low | High | `mysql_native_password=ON` in 8.4 param group preserves compatibility. |
| R3 | Query performance regression in 8.4 | Low | Medium | Test on dbatest first. Compare query plans. Blue/Green allows pre-switchover testing. |
| R4 | salesmarketing-rw (43.7 GB) — long Blue/Green creation time | High | Low | Allow 2-4 hours for green environment creation. Plan for weekend window. |
| R5 | OOM on db.t4g.micro instances during upgrade | Medium | Medium | Upgrade adds memory pressure. Monitor FreeableMemory. Consider deferring micro instance upgrades if SwapUsage > 400 MB. |
| R6 | JDBC driver incompatibility with caching_sha2_password | Low | High | Keep `mysql_native_password=ON` during initial upgrade. Migrate auth plugins as separate project. |
| R7 | Monitoring (Prometheus exporter) breaks | Low | Medium | Verify exporter compatibility with 8.4. Update `SHOW SLAVE STATUS` to `SHOW REPLICA STATUS` if needed. |
| R8 | May 31 deadline missed for some instances | Medium | High | Priority: minor-version upgrade all to 8.0.45 first (fast, low risk) to remove EOL auto-upgrade threat. |

---

## 8. Communication Plan

### Stakeholders
| Stakeholder | Role | Notification |
|------------|------|-------------|
| Michael (CTO) | Approval | Weekly status report, go/no-go for Batch 4 |
| Ops team | Application validation | 48h advance notice per batch, real-time during switchover |
| China HQ DBA | Cross-reference | Weekly sync, share findings |
| Service owners | Post-upgrade testing | Email per batch with timeline and validation steps |

### Notification Template
```
Subject: [RDS Upgrade] MySQL 8.0→8.4 — Batch {N} — {date} {time} UTC

Instances: {list}
Expected downtime: ~30 seconds per instance (Blue/Green switchover)
Maintenance window: 02:00-06:00 UTC

Action required: Verify application functionality within 1 hour of switchover.
Rollback plan: Snapshot restore available if issues detected.

Contact: David Zeng (DBA)
```
