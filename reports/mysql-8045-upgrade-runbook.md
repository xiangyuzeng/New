# RDS MySQL 8.0.x → 8.0.45 升级操作手册 (Runbook)

**制定日期**: 2026-04-14  
**制定人**: David Zeng (DBA)  
**AWS Account**: 257394478466 (us-east-1)  
**目标版本**: MySQL 8.0.45  
**适用范围**: 58 个 MySQL RDS 实例（当前 8.0.40 为主）

---

## 一、升级概览

| 项目 | 说明 |
|------|------|
| 升级类型 | 小版本升级（8.0.40/41/42/44 → 8.0.45） |
| 风险等级 | **低** — 无参数默认值变化、无参数废弃/移除、无不兼容变更 |
| 预计停机 | Multi-AZ：~30 秒 failover；Single-AZ：1-3 分钟 |
| 参数组 | **无需修改** — `luckyus-prod-80-new` 全部参数 100% 兼容 8.0.45 |
| 回滚方式 | 升级前全量快照恢复 + binlog 增量追回 |

### 批次计划（4 周 4 阶段）

| 阶段 | 周期 | 实例数 | 范围 | 说明 |
|------|------|--------|------|------|
| Phase 1 | 第 1 周 | 2 | dbatest, ilsopdevopsdata | 验证环境 |
| Phase 2 | 第 2 周 | 15 | DevOps/HR/内管平台 | 低影响 |
| Phase 3 | 第 3 周 | 27 | SCM/运营/财务 | 中影响 |
| Phase 4 | 第 4 周 | 16 | 销售/CRM/数据/框架 | 高影响/核心 |

### 升级窗口

- **首选**: 周二至周四，09:00-11:00 UTC（04:00-06:00 EST）
- **禁止**: 05:00 UTC（每日批处理窗口）、周一上午、周五下午
- **批量**: micro 实例 5-8 台/窗口，medium 以上 2-3 台/窗口

---

## 二、单实例升级全流程

> 以下为每个实例升级的完整 SOP。变量 `${INSTANCE}` 替换为实例标识符，如 `aws-luckyus-salesorder-rw`。

---

### Step 1: 事前检查（T-1 天或升级当天）

#### 1.1 确认实例当前状态

```bash
# 实例基本信息
aws rds describe-db-instances \
  --db-instance-identifier ${INSTANCE} \
  --region us-east-1 \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Version:EngineVersion,Class:DBInstanceClass,MultiAZ:MultiAZ,Storage:AllocatedStorage,PG:DBParameterGroups[0].DBParameterGroupName,PendingMaint:PendingMaintenanceActions}' \
  --output table
```

**检查项**：
- [ ] Status = `available`
- [ ] EngineVersion = 8.0.40/41/42/44（确认需要升级）
- [ ] MultiAZ = true（确认有 failover 能力）
- [ ] 无 pending 维护操作冲突

#### 1.2 检查实例健康指标

```bash
# 最近 1 小时 FreeableMemory（单位 Bytes）
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeableMemory \
  --dimensions Name=DBInstanceIdentifier,Value=${INSTANCE} \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average,Minimum \
  --region us-east-1 --output table

# 最近 1 小时 CPUUtilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=${INSTANCE} \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average,Maximum \
  --region us-east-1 --output table
```

**检查项**：
- [ ] FreeableMemory > 80MB（db.t4g.micro）或 > 500MB（其他）
- [ ] CPUUtilization < 50%
- [ ] 无异常 Swap 使用

#### 1.3 检查当前连接和长事务

```sql
-- 通过 mcp-db-gateway 执行
-- 活跃连接数
SELECT COUNT(*) as total_connections,
       SUM(CASE WHEN Command != 'Sleep' THEN 1 ELSE 0 END) as active_queries
FROM information_schema.PROCESSLIST
WHERE User NOT IN ('rdsadmin', 'event_scheduler');

-- 长事务检查（> 60 秒）
SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE, LEFT(INFO, 100) as query_preview
FROM information_schema.PROCESSLIST
WHERE TIME > 60 AND Command != 'Sleep' AND User NOT IN ('rdsadmin')
ORDER BY TIME DESC LIMIT 20;

-- 未关闭事务检查
SELECT trx_id, trx_state, trx_started, TIMESTAMPDIFF(SECOND, trx_started, NOW()) as duration_sec,
       trx_rows_locked, trx_rows_modified, trx_query
FROM information_schema.INNODB_TRX
ORDER BY trx_started LIMIT 10;
```

**检查项**：
- [ ] 无超过 300 秒的长事务
- [ ] 无大量等待锁的会话
- [ ] Canal 连接（`datalink_canal`）如有，记录当前 GTID 位置

#### 1.4 记录升级前基线

```sql
-- 记录当前版本
SELECT VERSION();

-- 记录当前 GTID 执行集合（用于回滚后增量追回）
SELECT @@global.gtid_executed;

-- 记录关键状态变量
SHOW GLOBAL STATUS WHERE Variable_name IN (
  'Uptime', 'Threads_connected', 'Threads_running',
  'Slow_queries', 'Questions', 'Com_select', 'Com_insert', 'Com_update', 'Com_delete',
  'Innodb_buffer_pool_pages_total', 'Innodb_buffer_pool_pages_free'
);
```

> **将以上输出保存到 `/app/reports/upgrade-logs/${INSTANCE}-pre-upgrade.txt`**

---

### Step 2: 全量备份（升级前快照）

#### 2.1 创建手动快照

```bash
SNAPSHOT_ID="${INSTANCE}-pre-8045-$(date +%Y%m%d%H%M)"

aws rds create-db-snapshot \
  --db-instance-identifier ${INSTANCE} \
  --db-snapshot-identifier ${SNAPSHOT_ID} \
  --region us-east-1

echo "Snapshot ID: ${SNAPSHOT_ID}"
```

#### 2.2 等待快照完成

```bash
aws rds wait db-snapshot-available \
  --db-snapshot-identifier ${SNAPSHOT_ID} \
  --region us-east-1

# 确认快照状态
aws rds describe-db-snapshots \
  --db-snapshot-identifier ${SNAPSHOT_ID} \
  --region us-east-1 \
  --query 'DBSnapshots[0].{Status:Status,SnapshotCreateTime:SnapshotCreateTime,AllocatedStorage:AllocatedStorage,Engine:Engine,EngineVersion:EngineVersion}' \
  --output table
```

**检查项**：
- [ ] 快照状态 = `available`
- [ ] EngineVersion = 升级前版本
- [ ] 记录快照 ID 和创建时间

> **重要**: 此快照是回滚的基础，保留至升级验证完成后至少 7 天。

---

### Step 3: 通知研发人员

#### 3.1 升级通知模板

```
Subject: [维护通知] MySQL 实例 ${INSTANCE} 升级至 8.0.45

各位研发同事：

计划于 YYYY-MM-DD HH:MM UTC 对 MySQL 实例 ${INSTANCE} 执行小版本升级：
  - 升级路径: 8.0.XX → 8.0.45
  - 预计停机: ~30 秒（Multi-AZ failover）
  - 影响: 升级期间数据库连接会短暂中断，应用需依赖连接池自动重连

请确认：
  1. 升级窗口内无重要批处理任务或上线部署
  2. 应用连接池已配置自动重连（建议验证）
  3. 如有问题请在 YYYY-MM-DD HH:MM 前反馈

回滚方案：已创建升级前快照，如升级后发现问题可在 30 分钟内恢复。

DBA Team — David Zeng
```

#### 3.2 获取确认

- [ ] 相关业务研发确认无冲突
- [ ] 确认升级窗口无部署计划
- [ ] 对核心实例（salesorder, framework01, devops 等），需等业务方明确回复

---

### Step 4: 执行升级

#### 4.1 升级前最终确认

```bash
# 再次确认实例状态
aws rds describe-db-instances \
  --db-instance-identifier ${INSTANCE} \
  --region us-east-1 \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Version:EngineVersion}' \
  --output text
```

- [ ] 快照已完成（Step 2）
- [ ] 研发已确认（Step 3）
- [ ] 当前无长事务（重新检查 Step 1.3）

#### 4.2 执行升级命令

```bash
echo "=== $(date -u) — Starting upgrade: ${INSTANCE} → 8.0.45 ==="

aws rds modify-db-instance \
  --db-instance-identifier ${INSTANCE} \
  --engine-version 8.0.45 \
  --apply-immediately \
  --region us-east-1

echo "=== Upgrade initiated, monitoring status... ==="
```

#### 4.3 监控升级进度

```bash
# 轮询实例状态，直到 available
while true; do
  STATUS=$(aws rds describe-db-instances \
    --db-instance-identifier ${INSTANCE} \
    --region us-east-1 \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text)
  VERSION=$(aws rds describe-db-instances \
    --db-instance-identifier ${INSTANCE} \
    --region us-east-1 \
    --query 'DBInstances[0].EngineVersion' \
    --output text)
  echo "$(date -u) | Status: ${STATUS} | Version: ${VERSION}"
  if [ "${STATUS}" = "available" ] && [ "${VERSION}" = "8.0.45" ]; then
    echo "=== Upgrade completed! ==="
    break
  fi
  sleep 30
done
```

**典型状态流转**: `available` → `modifying` → `upgrading` → `available`

---

### Step 5: DBA 技术验证（升级后立即执行）

#### 5.1 版本与参数确认

```sql
-- 确认版本
SELECT VERSION();
-- 预期结果: 8.0.45

-- 确认参数组生效（抽查关键参数）
SHOW GLOBAL VARIABLES WHERE Variable_name IN (
  'transaction_isolation', 'long_query_time', 'max_connections',
  'innodb_lock_wait_timeout', 'innodb_adaptive_hash_index',
  'lower_case_table_names', 'gtid_mode', 'enforce_gtid_consistency',
  'performance_schema', 'slow_query_log'
);
```

**检查项**：
- [ ] VERSION() = 8.0.45
- [ ] transaction_isolation = READ-COMMITTED
- [ ] long_query_time = 0.100000
- [ ] max_connections = 4000
- [ ] gtid_mode = ON
- [ ] performance_schema = ON
- [ ] slow_query_log = ON

#### 5.2 连接与进程检查

```sql
-- 应用连接是否恢复
SELECT User, COUNT(*) as conn_count, GROUP_CONCAT(DISTINCT DB) as databases
FROM information_schema.PROCESSLIST
WHERE User NOT IN ('rdsadmin', 'event_scheduler')
GROUP BY User ORDER BY conn_count DESC;

-- Canal 连接是否恢复（如适用）
SELECT ID, User, Host, Command, Time, State
FROM information_schema.PROCESSLIST
WHERE User = 'datalink_canal';
```

**检查项**：
- [ ] 应用用户连接已恢复（对比升级前基线）
- [ ] Canal binlog dump 连接已恢复（Command = `Binlog Dump GTID`）
- [ ] monitor_exporter 连接正常

#### 5.3 Prometheus/Grafana 监控确认

```promql
# 确认 exporter 正常采集
up{dbinstance_identifier="${INSTANCE}"}

# 确认无慢查询突增
rate(mysql_global_status_slow_queries{dbinstance_identifier="${INSTANCE}"}[5m])

# 确认内存稳定
mysql_global_status_innodb_buffer_pool_pages_free{dbinstance_identifier="${INSTANCE}"}
```

**检查项**：
- [ ] Prometheus exporter up = 1
- [ ] 慢查询率无异常飙升
- [ ] Buffer pool free pages 稳定

#### 5.4 CloudWatch 指标确认

```bash
# 升级后 15 分钟内的关键指标
for METRIC in FreeableMemory CPUUtilization DatabaseConnections ReadIOPS WriteIOPS; do
  echo "=== ${METRIC} ==="
  aws cloudwatch get-metric-statistics \
    --namespace AWS/RDS \
    --metric-name ${METRIC} \
    --dimensions Name=DBInstanceIdentifier,Value=${INSTANCE} \
    --start-time $(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 60 --statistics Average \
    --region us-east-1 \
    --query 'Datapoints | sort_by(@, &Timestamp) | [-3:].[Timestamp,Average]' \
    --output table
done
```

**检查项**：
- [ ] FreeableMemory 稳定，无持续下降趋势
- [ ] CPUUtilization 无异常升高
- [ ] DatabaseConnections 恢复到升级前水平
- [ ] IOPS 正常

#### 5.5 慢查询日志确认

```bash
# 确认慢查询日志流向 CloudWatch
aws logs describe-log-streams \
  --log-group-name /aws/rds/instance/${INSTANCE}/slowquery \
  --order-by LastEventTime --descending --limit 1 \
  --region us-east-1 \
  --query 'logStreams[0].{LastEvent:lastEventTimestamp,StoredBytes:storedBytes}' \
  --output table
```

---

### Step 6: 研发业务验证

#### 6.1 通知研发执行验证

```
Subject: [验证请求] MySQL ${INSTANCE} 已升级至 8.0.45，请验证业务功能

升级已完成，DBA 技术验证通过。请各业务方验证以下内容：

  1. 核心业务流程是否正常（下单、支付、查询等）
  2. 应用日志中是否有数据库相关错误
  3. 定时任务/批处理是否正常执行
  4. 接口响应时间是否正常

请在 2 小时内反馈验证结果。如发现问题请立即联系 DBA。

DBA Team — David Zeng
```

#### 6.2 验证清单

- [ ] 业务方确认核心功能正常
- [ ] 应用日志无数据库连接错误
- [ ] 无 SQL 执行异常
- [ ] 响应时间无明显退化

#### 6.3 观察期

- **Phase 1（测试实例）**: 观察 **48 小时**
- **Phase 2（低影响）**: 观察 **24 小时**
- **Phase 3/4（中/高影响）**: 观察 **24 小时**，含一个完整的批处理周期（05:00 UTC）

---

### Step 7: 升级后备份

#### 7.1 创建升级后快照

```bash
POST_SNAPSHOT_ID="${INSTANCE}-post-8045-$(date +%Y%m%d%H%M)"

aws rds create-db-snapshot \
  --db-instance-identifier ${INSTANCE} \
  --db-snapshot-identifier ${POST_SNAPSHOT_ID} \
  --region us-east-1

aws rds wait db-snapshot-available \
  --db-snapshot-identifier ${POST_SNAPSHOT_ID} \
  --region us-east-1

echo "Post-upgrade snapshot: ${POST_SNAPSHOT_ID}"
```

#### 7.2 快照保留策略

| 快照 | 保留时长 | 用途 |
|------|---------|------|
| 升级前快照 (`*-pre-8045-*`) | **7 天**（验证完成后可删除） | 回滚基础 |
| 升级后快照 (`*-post-8045-*`) | **30 天** | 升级后基线 |

---

### Step 8: 更新跟踪表

#### 8.1 升级跟踪表模板

在 `/app/reports/mysql-8045-upgrade-tracker.md` 中更新：

```markdown
| 实例 | 升级前版本 | 升级时间(UTC) | 升级后版本 | DBA验证 | 研发验证 | 升级前快照 | 升级后快照 | 备注 |
|------|-----------|-------------|-----------|---------|---------|-----------|-----------|------|
| aws-luckyus-dbatest-rw | 8.0.42 | 2026-04-XX HH:MM | 8.0.45 | ✅ | ✅ | ...-pre-8045-... | ...-post-8045-... | Phase 1 |
```

#### 8.2 更新内容

- [ ] 记录升级前后版本
- [ ] 记录升级执行时间
- [ ] 记录 DBA 验证结果（通过/失败）
- [ ] 记录研发验证结果（通过/失败/待确认）
- [ ] 记录升级前后快照 ID
- [ ] 记录任何异常或备注

---

## 三、回滚方案

> 当升级后发现严重问题（如应用无法连接、数据损坏、性能严重退化），需要回滚到升级前版本。

### 回滚决策条件

| 条件 | 触发回滚 |
|------|---------|
| 应用无法连接数据库且连接池重试无效 | 是 |
| 数据查询结果异常/数据损坏 | 是 |
| 性能退化超过 50% 且持续 15 分钟以上 | 是 |
| 慢查询率升高但可忽略（< 10%） | 否，继续观察 |
| 个别连接超时但自动恢复 | 否，继续观察 |

### 回滚流程

#### R1: 从升级前快照恢复新实例

```bash
RESTORE_INSTANCE="${INSTANCE}-restore"
SNAPSHOT_ID="${INSTANCE}-pre-8045-YYYYMMDDHHMM"  # 替换为实际快照 ID

aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier ${RESTORE_INSTANCE} \
  --db-snapshot-identifier ${SNAPSHOT_ID} \
  --db-instance-class <原实例类型> \
  --db-subnet-group-name <原子网组> \
  --vpc-security-group-ids <原安全组> \
  --multi-az \
  --region us-east-1

# 等待恢复完成
aws rds wait db-instance-available \
  --db-instance-identifier ${RESTORE_INSTANCE} \
  --region us-east-1
```

#### R2: 用 binlog 追回增量数据

快照恢复的是升级前的时间点，升级后到回滚期间产生的增量数据需要通过 binlog 追回。

##### R2.1 确认升级前 GTID 位置

```sql
-- 在恢复出的实例上执行
SELECT @@global.gtid_executed;
-- 此为快照时间点的 GTID 集合
```

##### R2.2 从升级后实例导出 binlog

```bash
# 查看可用的 binlog 文件
aws rds describe-db-log-files \
  --db-instance-identifier ${INSTANCE} \
  --region us-east-1 \
  --query 'DescribeDBLogFiles[?contains(LogFileName, `mysql-bin-changelog`)].[LogFileName,Size,LastWritten]' \
  --output table

# 下载 binlog（从升级前快照时间点到现在）
aws rds download-db-log-file-portion \
  --db-instance-identifier ${INSTANCE} \
  --log-file-name mysql-bin-changelog.XXXXXX \
  --region us-east-1 \
  --output text > /tmp/${INSTANCE}-binlog.sql
```

##### R2.3 使用 mysqlbinlog 过滤并应用增量

```bash
# 使用 GTID 过滤，只应用快照之后的事务
mysqlbinlog \
  --exclude-gtids='<快照时的GTID集合>' \
  /tmp/${INSTANCE}-binlog.sql \
  | mysql -h <恢复实例endpoint> -u admin -p
```

> **注意**: RDS 不直接提供 binlog 文件下载。实际操作中，增量追回的替代方案：
> 
> 1. **RDS Point-in-Time Recovery (PITR)** — 更推荐的方式：
>    ```bash
>    aws rds restore-db-instance-to-point-in-time \
>      --source-db-instance-identifier ${INSTANCE} \
>      --target-db-instance-identifier ${RESTORE_INSTANCE} \
>      --restore-time "2026-04-XX T HH:MM:SSZ" \
>      --region us-east-1
>    ```
>    PITR 会自动应用 binlog 到指定时间点，**无需手动处理增量**。
>
> 2. **如果升级后实例仍可访问**，可用 mysqldump/mydumper 导出升级后有变化的表，导入到恢复实例。

#### R3: 验证恢复实例

```sql
-- 确认版本是升级前的
SELECT VERSION();

-- 确认数据完整性
SHOW DATABASES;

-- 抽查关键表数据量
SELECT COUNT(*) FROM <关键业务表>;
```

#### R4: 切换流量到恢复实例

**方式一：Rename 实例（推荐，对应用透明）**

```bash
# 1. 将当前有问题的实例改名
aws rds modify-db-instance \
  --db-instance-identifier ${INSTANCE} \
  --new-db-instance-identifier ${INSTANCE}-broken \
  --apply-immediately \
  --region us-east-1

# 等待改名完成
aws rds wait db-instance-available \
  --db-instance-identifier ${INSTANCE}-broken \
  --region us-east-1

# 2. 将恢复实例改名为原名
aws rds modify-db-instance \
  --db-instance-identifier ${RESTORE_INSTANCE} \
  --new-db-instance-identifier ${INSTANCE} \
  --apply-immediately \
  --region us-east-1

aws rds wait db-instance-available \
  --db-instance-identifier ${INSTANCE} \
  --region us-east-1
```

> **注意**: Rename 会改变 endpoint DNS，需要等待 DNS 传播（通常 1-2 分钟）。

**方式二：修改应用配置/DNS 指向恢复实例**

如果使用 Route53 CNAME 或应用配置管理（如 Nacos），直接修改指向。

#### R5: 回滚后验证

- [ ] 应用连接恢复正常
- [ ] 业务功能验证通过
- [ ] Canal 连接恢复（如适用，可能需要重新配置 GTID 位置）
- [ ] 监控指标恢复正常
- [ ] 通知研发回滚完成

#### R6: 回滚后清理

```bash
# 确认回滚成功且运行稳定 24 小时后
# 删除有问题的实例
aws rds delete-db-instance \
  --db-instance-identifier ${INSTANCE}-broken \
  --skip-final-snapshot \
  --region us-east-1
```

### 回滚时间预估

| 步骤 | 预计耗时 | 说明 |
|------|---------|------|
| R1: 快照恢复 | 10-30 min | 取决于数据量 |
| R2: PITR 增量追回 | 5-15 min | 使用 PITR 自动完成 |
| R3: 验证 | 5-10 min | |
| R4: 切换流量 | 5-10 min | Rename + DNS 传播 |
| **总计** | **25-65 min** | |

---

## 四、特殊实例注意事项

### 4.1 db.t4g.micro 实例（40 台）

- 仅 1 GB 内存，升级过程会临时消耗额外内存
- **升级前**: 确认 FreeableMemory > 80 MB
- **升级前**: 检查并 KILL 长运行查询释放内存
- **升级窗口**: 避开 05:00 UTC 批处理高峰
- **已验证**: iluckyams-rw (8.0.44, db.t4g.micro) 运行稳定，内存无异常

### 4.2 Canal 实例（~10 台有 datalink_canal 连接）

- Canal 使用 `Binlog Dump GTID` 同步数据
- 升级 failover 后 Canal 需要自动重连
- **升级后**: 确认 Canal 连接恢复（PROCESSLIST 中 Command = `Binlog Dump GTID`）
- **如未恢复**: 联系中间件团队重启 Canal 实例

### 4.3 大数据量实例

| 实例 | 数据量 | 额外注意 |
|------|--------|---------|
| ldas01 | 86 GB | 快照时间较长，预留充足窗口 |
| salesmarketing | 43 GB | 核心销售，需业务强确认 |
| iluckyhealth | 29 GB | 快照可能需要 15-20 分钟 |
| icyberdata | 23 GB | 数据分析库 |

### 4.4 已在 8.0.40 以上版本的实例

| 实例 | 当前版本 | 说明 |
|------|---------|------|
| iluckyams-rw | 8.0.44 | 8.0.44 → 8.0.45 变化极小 |
| ldas01-rw | 8.0.41 | 正常升级 |
| dbatest-rw | 8.0.42 | Phase 1 优先测试 |

---

## 五、升级命令速查

### 批量升级脚本（谨慎使用）

```bash
#!/bin/bash
# =============================================================================
# Script: batch-upgrade-8045.sh
# Purpose: Batch upgrade MySQL instances to 8.0.45
# Usage: ./batch-upgrade-8045.sh instance1 instance2 instance3 ...
# Date: 2026-04-14
# Author: David Zeng (DBA)
#
# WARNING: 只在 DBA 手动确认每个实例的事前检查和快照后使用
# =============================================================================

set -euo pipefail
REGION="us-east-1"
TARGET_VERSION="8.0.45"

for INSTANCE in "$@"; do
  echo ""
  echo "============================================"
  echo "  Upgrading: ${INSTANCE} → ${TARGET_VERSION}"
  echo "  Time: $(date -u)"
  echo "============================================"

  # 确认当前状态
  CURRENT=$(aws rds describe-db-instances \
    --db-instance-identifier "${INSTANCE}" \
    --region "${REGION}" \
    --query 'DBInstances[0].[DBInstanceStatus,EngineVersion]' \
    --output text)
  echo "Current: ${CURRENT}"

  # 执行升级
  aws rds modify-db-instance \
    --db-instance-identifier "${INSTANCE}" \
    --engine-version "${TARGET_VERSION}" \
    --apply-immediately \
    --region "${REGION}" \
    --query 'DBInstance.{Status:DBInstanceStatus,PendingVersion:PendingModifiedValues.EngineVersion}' \
    --output table

  echo "Upgrade initiated for ${INSTANCE}"
  echo ""
done

echo "=== All upgrades initiated. Monitor with: ==="
echo 'aws rds describe-db-instances --query "DBInstances[?EngineVersion!='"'"'8.0.45'"'"'].[DBInstanceIdentifier,EngineVersion,DBInstanceStatus]" --output table --region us-east-1'
```

### 单实例完整升级一键脚本

```bash
#!/bin/bash
# Usage: ./upgrade-single.sh <instance-identifier>
# 此脚本包含：快照 → 升级 → 等待 → 基础验证
set -euo pipefail

INSTANCE=$1
REGION="us-east-1"
TARGET="8.0.45"
SNAPSHOT_ID="${INSTANCE}-pre-8045-$(date +%Y%m%d%H%M)"

echo "=== [1/4] Creating pre-upgrade snapshot: ${SNAPSHOT_ID} ==="
aws rds create-db-snapshot \
  --db-instance-identifier "${INSTANCE}" \
  --db-snapshot-identifier "${SNAPSHOT_ID}" \
  --region "${REGION}"
aws rds wait db-snapshot-available \
  --db-snapshot-identifier "${SNAPSHOT_ID}" \
  --region "${REGION}"
echo "Snapshot ready."

echo "=== [2/4] Upgrading ${INSTANCE} → ${TARGET} ==="
aws rds modify-db-instance \
  --db-instance-identifier "${INSTANCE}" \
  --engine-version "${TARGET}" \
  --apply-immediately \
  --region "${REGION}"

echo "=== [3/4] Waiting for upgrade to complete... ==="
while true; do
  STATUS=$(aws rds describe-db-instances \
    --db-instance-identifier "${INSTANCE}" \
    --region "${REGION}" \
    --query 'DBInstances[0].DBInstanceStatus' --output text)
  VERSION=$(aws rds describe-db-instances \
    --db-instance-identifier "${INSTANCE}" \
    --region "${REGION}" \
    --query 'DBInstances[0].EngineVersion' --output text)
  echo "$(date -u) | ${STATUS} | ${VERSION}"
  [ "${STATUS}" = "available" ] && [ "${VERSION}" = "${TARGET}" ] && break
  sleep 30
done

echo "=== [4/4] Creating post-upgrade snapshot ==="
POST_SNAPSHOT="${INSTANCE}-post-8045-$(date +%Y%m%d%H%M)"
aws rds create-db-snapshot \
  --db-instance-identifier "${INSTANCE}" \
  --db-snapshot-identifier "${POST_SNAPSHOT}" \
  --region "${REGION}"

echo ""
echo "=========================================="
echo "  UPGRADE COMPLETE"
echo "  Instance:        ${INSTANCE}"
echo "  Version:         ${TARGET}"
echo "  Pre-snapshot:    ${SNAPSHOT_ID}"
echo "  Post-snapshot:   ${POST_SNAPSHOT}"
echo "  Next: Run DBA technical validation (Step 5)"
echo "=========================================="
```

---

## 六、检查清单总表

### 每实例必检项（可打印）

```
实例: ________________________  升级日期: ____________

事前检查:
  [ ] 实例状态 = available
  [ ] 当前版本确认: ____________
  [ ] FreeableMemory > 阈值
  [ ] CPU < 50%
  [ ] 无长事务 (> 300s)
  [ ] 升级前基线已记录

全量备份:
  [ ] 快照已创建: ________________________
  [ ] 快照状态 = available

通知:
  [ ] 研发已通知
  [ ] 研发已确认无冲突

执行升级:
  [ ] 升级命令已执行
  [ ] 版本确认 = 8.0.45

DBA 验证:
  [ ] 参数组生效
  [ ] 应用连接恢复
  [ ] Canal 连接恢复（如适用）
  [ ] Prometheus exporter 正常
  [ ] CloudWatch 指标正常
  [ ] 慢查询日志正常

研发验证:
  [ ] 业务功能正常
  [ ] 无异常错误日志
  [ ] 响应时间正常

升级后备份:
  [ ] 升级后快照已创建: ________________________

跟踪表:
  [ ] 已更新升级跟踪表

签字: ____________  日期: ____________
```

---

*文档生成: Claude Code (Opus 4.6) | 数据来源: 历史调查报告、生产环境实时数据*
