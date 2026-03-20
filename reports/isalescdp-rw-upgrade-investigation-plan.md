# isalescdp-rw Post-Upgrade Investigation Plan

**Instance:** `aws-luckyus-isalescdp-rw`
**Upgrade:** db.t4g.micro → db.t4g.medium
**Issue:** Multi-AZ failover during upgrade terminated TCP connections; JDBC pool held stale connections and threw `CommunicationsException` (285,263ms timeout).
**Root Cause Type:** Post-upgrade application connection pool problem (NOT OOM).

**Related RCAs:**
- `/app/reports/RCA-isalescdp-failover-20260312.md` — original OOM failover on 2026-03-12 (db.t4g.micro)

---

## Section 1 — UPGRADE EVENT TIMELINE

**Goal:** Capture modification, failover, and recovery timestamps.

```bash
# Instance event history (past 7 days)
aws rds describe-events \
  --source-identifier aws-luckyus-isalescdp-rw \
  --source-type db-instance \
  --start-time 2026-03-13T00:00:00Z \
  --end-time 2026-03-20T23:59:59Z \
  --region us-east-1 \
  --output json

# Current instance status + pending modifications
aws rds describe-db-instances \
  --db-instance-identifier aws-luckyus-isalescdp-rw \
  --region us-east-1 \
  --query 'DBInstances[0].{
    Class:DBInstanceClass,
    EngineVersion:EngineVersion,
    Status:DBInstanceStatus,
    MultiAZ:MultiAZ,
    PendingValues:PendingModifiedValues,
    ParameterGroup:DBParameterGroups[0].{Name:DBParameterGroupName,Status:ParameterApplyStatus},
    MaintenanceWindow:PreferredMaintenanceWindow,
    Endpoint:Endpoint.Address,
    StorageType:StorageType
  }' \
  --output json
```

**Look for events:**
- `DB instance class changed`
- `Multi-AZ instance failover`
- `Finished DB Instance backup`
- `Recovered from a reboot`

---

## Section 2 — POST-UPGRADE HEALTH

**Goal:** Confirm Swap ≈ 0 and FreeableMemory ~2.5–3 GB on the new 4 GB instance. 5-minute granularity for past 24 hours.

```bash
# FreeableMemory — expect >2.5GB (2,684,354,560 bytes)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeableMemory \
  --dimensions Name=DBInstanceIdentifier,Value=aws-luckyus-isalescdp-rw \
  --start-time 2026-03-19T00:00:00Z \
  --end-time 2026-03-20T00:00:00Z \
  --period 300 \
  --statistics Average Minimum \
  --region us-east-1 \
  --output json

# SwapUsage — expect ≈ 0 (was 365-407MB on db.t4g.micro)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name SwapUsage \
  --dimensions Name=DBInstanceIdentifier,Value=aws-luckyus-isalescdp-rw \
  --start-time 2026-03-19T00:00:00Z \
  --end-time 2026-03-20T00:00:00Z \
  --period 300 \
  --statistics Average Maximum \
  --region us-east-1 \
  --output json

# CPUUtilization — confirm no post-upgrade CPU spike
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=aws-luckyus-isalescdp-rw \
  --start-time 2026-03-19T00:00:00Z \
  --end-time 2026-03-20T00:00:00Z \
  --period 300 \
  --statistics Average Maximum \
  --region us-east-1 \
  --output json

# DatabaseConnections — confirm reconnection after failover
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=aws-luckyus-isalescdp-rw \
  --start-time 2026-03-19T00:00:00Z \
  --end-time 2026-03-20T00:00:00Z \
  --period 300 \
  --statistics Average Maximum \
  --region us-east-1 \
  --output json
```

---

## Section 3 — PARAMETER VALIDATION

**Goal:** Confirm `innodb_buffer_pool_size` is NOT stuck at the OOM-degraded 128 MB value.

### Step 1 — Get parameter group name:
```bash
aws rds describe-db-instances \
  --db-instance-identifier aws-luckyus-isalescdp-rw \
  --region us-east-1 \
  --query 'DBInstances[0].DBParameterGroups[0].DBParameterGroupName' \
  --output text
```

### Step 2 — Query critical parameters (replace `<PARAM_GROUP_NAME>` with output from step 1):
```bash
aws rds describe-db-parameters \
  --db-parameter-group-name <PARAM_GROUP_NAME> \
  --region us-east-1 \
  --query "Parameters[?ParameterName=='innodb_buffer_pool_size' || \
           ParameterName=='innodb_buffer_pool_instances' || \
           ParameterName=='max_connections' || \
           ParameterName=='wait_timeout' || \
           ParameterName=='net_read_timeout' || \
           ParameterName=='net_write_timeout' || \
           ParameterName=='interactive_timeout'].{
             Name:ParameterName,
             Value:ParameterValue,
             Source:Source,
             ApplyType:ApplyType,
             ApplyMethod:ApplyMethod
           }" \
  --output table
```

### Expected values for db.t4g.medium (4 GB RAM):

| Parameter | Expected Value | Flag if |
|-----------|---------------|---------|
| innodb_buffer_pool_size | 2684354560 (2.5 GB) | Still 134217728 (128 MB) → OOM remnant not cleared |
| max_connections | 200–300 | Still 4000 → misconfigured |
| wait_timeout | ≤ 300 | > 28800 → connection leak risk |
| net_read_timeout | 60 | < 30 → CommunicationsException risk |
| net_write_timeout | 120 | < 60 → write timeout risk |

### Step 3 — Live confirmation via MySQL (run via mcp-db-gateway after connectivity restored):
```sql
SHOW VARIABLES WHERE Variable_name IN (
  'innodb_buffer_pool_size',
  'innodb_buffer_pool_instances',
  'max_connections',
  'wait_timeout',
  'net_read_timeout',
  'net_write_timeout'
);
```

---

## Section 4 — CONNECTION LOGS

**Goal:** Find evidence of aborted connections, killed connections, and reconnection patterns around the upgrade window.

### Step 1 — List available RDS log files:
```bash
aws rds describe-db-log-files \
  --db-instance-identifier aws-luckyus-isalescdp-rw \
  --region us-east-1 \
  --filename-contains error \
  --output table

aws rds describe-db-log-files \
  --db-instance-identifier aws-luckyus-isalescdp-rw \
  --region us-east-1 \
  --filename-contains slow \
  --output table
```

### Step 2 — Download error log (replace `<LOG_FILE_NAME>` with the most recent error log from step 1):
```bash
aws rds download-db-log-file-portion \
  --db-instance-identifier aws-luckyus-isalescdp-rw \
  --log-file-name <LOG_FILE_NAME> \
  --region us-east-1 \
  --output text > /tmp/isalescdp-error.log

# Grep for connection errors around upgrade window
grep -E "Aborted|Got an error reading|Lost connection|Communication|killed|closed" \
  /tmp/isalescdp-error.log | head -100
```

### Step 3 — CloudWatch Logs Insights (if error logs go to CloudWatch at `/aws/rds/instance/aws-luckyus-isalescdp-rw/error`):
```bash
aws logs start-query \
  --log-group-name /aws/rds/instance/aws-luckyus-isalescdp-rw/error \
  --start-time $(date -d "2026-03-18T00:00:00Z" +%s) \
  --end-time $(date -d "2026-03-20T00:00:00Z" +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /Aborted|CommunicationsException|Lost connection/ | sort @timestamp desc | limit 200' \
  --region us-east-1

# Then retrieve results (replace <QUERY_ID> with output above):
aws logs get-query-results \
  --query-id <QUERY_ID> \
  --region us-east-1
```

### Step 4 — Check `Aborted_connects` and `Aborted_clients` counters (via mcp-db-gateway after recovery):
```sql
SHOW GLOBAL STATUS WHERE Variable_name IN (
  'Aborted_connects',
  'Aborted_clients',
  'Connection_errors_max_connections',
  'Threads_connected',
  'Max_used_connections'
);
```

---

## Section 5 — APPLICATION-SIDE FIX

**Goal:** Document JDBC URL and HikariCP settings to prevent CommunicationsException during future failovers.

### Recommended JDBC URL Parameters
```
jdbc:mysql://aws-luckyus-isalescdp-rw:3306/isalescdp
  ?autoReconnect=false
  &failOverReadOnly=false
  &connectTimeout=5000
  &socketTimeout=30000
  &useSSL=true
  &requireSSL=false
  &serverTimezone=UTC
  &characterEncoding=UTF-8
```

> **Note:** `autoReconnect=true` is deprecated and unreliable. Use HikariCP's connection validation instead.

### Recommended HikariCP Settings
```yaml
spring:
  datasource:
    hikari:
      # Evict connections older than 270 seconds (just under wait_timeout=300s)
      maxLifetime: 270000            # 270 seconds — just under wait_timeout=300
      # Test connection before borrow — prevents handing out stale connections after failover
      connectionTestQuery: "SELECT 1"
      connectionTimeout: 5000        # 5 seconds to acquire from pool (fail fast)
      validationTimeout: 3000        # 3 seconds for SELECT 1 validation
      idleTimeout: 120000            # 2 minutes idle eviction
      keepaliveTime: 60000           # Keepalive ping every 60 seconds
      minimumIdle: 5
      maximumPoolSize: 50            # Well under max_connections=200
      # Don't fail startup if DB unavailable during rolling deploy
      initializationFailTimeout: -1
```

### Root Cause Summary

During RDS instance class upgrade, Multi-AZ failover terminates all TCP connections. Without `keepaliveTime` or `maxLifetime` shorter than `wait_timeout`, the pool retains dead connections. The first query on a stale connection throws `CommunicationsException`. Setting `connectionTestQuery` ensures HikariCP validates before use.

| Config Gap | Effect | Fix |
|-----------|--------|-----|
| No `keepaliveTime` | Pool holds dead connections after failover | Set `keepaliveTime: 60000` |
| No `connectionTestQuery` | Stale connections handed to application | Set `connectionTestQuery: "SELECT 1"` |
| `maxLifetime` > `wait_timeout` | Connections expire server-side before pool evicts them | Set `maxLifetime` < `wait_timeout` |
| `autoReconnect=true` in JDBC URL | Deprecated, causes race conditions | Remove; rely on HikariCP validation |

---

## Section 6 — FLEET RISK SCAN

**Goal:** Identify all other db.t4g.micro/db.t3.micro instances at risk of the same OOM pattern.

### Step 1 — List all micro instances:
```bash
aws rds describe-db-instances \
  --region us-east-1 \
  --query "DBInstances[?DBInstanceClass=='db.t4g.micro' || DBInstanceClass=='db.t3.micro'].{
    ID:DBInstanceIdentifier,
    Class:DBInstanceClass,
    Engine:Engine,
    EngineVersion:EngineVersion,
    Status:DBInstanceStatus,
    MultiAZ:MultiAZ,
    Storage:AllocatedStorage
  }" \
  --output table
```

### Step 2 — Per-instance metrics check (replace `<INSTANCE_ID>` for each instance from step 1):

```bash
# SwapUsage — flag if Average > 104,857,600 bytes (100 MB)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name SwapUsage \
  --dimensions Name=DBInstanceIdentifier,Value=<INSTANCE_ID> \
  --start-time 2026-03-13T00:00:00Z \
  --end-time 2026-03-20T00:00:00Z \
  --period 86400 \
  --statistics Average Maximum \
  --region us-east-1 \
  --output json

# FreeableMemory — flag if Average < 209,715,200 bytes (200 MB)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeableMemory \
  --dimensions Name=DBInstanceIdentifier,Value=<INSTANCE_ID> \
  --start-time 2026-03-13T00:00:00Z \
  --end-time 2026-03-20T00:00:00Z \
  --period 86400 \
  --statistics Average Minimum \
  --region us-east-1 \
  --output json
```

### Triage Criteria:

| Condition | Flag Level | Action |
|-----------|-----------|--------|
| SwapUsage avg > 104,857,600 (100 MB) | CRITICAL | Schedule upgrade immediately |
| FreeableMemory avg < 209,715,200 (200 MB) | CRITICAL | Schedule upgrade immediately |
| SwapUsage avg > 52,428,800 (50 MB) | WARNING | Monitor closely, plan upgrade |
| FreeableMemory avg < 419,430,400 (400 MB) | WARNING | Monitor closely, plan upgrade |

### Step 3 — Batch script to scan all micro instances at once:
```bash
# Get all micro instance IDs
INSTANCES=$(aws rds describe-db-instances \
  --region us-east-1 \
  --query "DBInstances[?DBInstanceClass=='db.t4g.micro' || DBInstanceClass=='db.t3.micro'].DBInstanceIdentifier" \
  --output text)

echo "Fleet scan results: $(date -u +%Y-%m-%dT%H:%M:%SZ)" > /tmp/fleet-risk-scan.txt
echo "============================================" >> /tmp/fleet-risk-scan.txt

for INSTANCE_ID in $INSTANCES; do
  echo "" >> /tmp/fleet-risk-scan.txt
  echo "--- $INSTANCE_ID ---" >> /tmp/fleet-risk-scan.txt

  echo "[SwapUsage]" >> /tmp/fleet-risk-scan.txt
  aws cloudwatch get-metric-statistics \
    --namespace AWS/RDS --metric-name SwapUsage \
    --dimensions Name=DBInstanceIdentifier,Value=$INSTANCE_ID \
    --start-time 2026-03-13T00:00:00Z --end-time 2026-03-20T00:00:00Z \
    --period 604800 --statistics Average Maximum \
    --region us-east-1 --output json >> /tmp/fleet-risk-scan.txt

  echo "[FreeableMemory]" >> /tmp/fleet-risk-scan.txt
  aws cloudwatch get-metric-statistics \
    --namespace AWS/RDS --metric-name FreeableMemory \
    --dimensions Name=DBInstanceIdentifier,Value=$INSTANCE_ID \
    --start-time 2026-03-13T00:00:00Z --end-time 2026-03-20T00:00:00Z \
    --period 604800 --statistics Average Minimum \
    --region us-east-1 --output json >> /tmp/fleet-risk-scan.txt
done

echo "" >> /tmp/fleet-risk-scan.txt
echo "Scan complete." >> /tmp/fleet-risk-scan.txt
cat /tmp/fleet-risk-scan.txt
```

---

## Quick Reference — Investigation Order

1. **Section 1** — Confirm upgrade event timestamps and instance status
2. **Section 2** — Validate post-upgrade health metrics (Swap ≈ 0, FreeableMemory > 2.5 GB)
3. **Section 3** — Verify parameter group values (especially `innodb_buffer_pool_size`)
4. **Section 4** — Review connection logs for aborted/stale connection evidence
5. **Section 5** — Share JDBC/HikariCP fix with app team (isalescdp service owner)
6. **Section 6** — Scan fleet for other micro instances at OOM risk
