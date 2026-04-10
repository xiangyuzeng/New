# MySQL 8.4 参数组配置文档 — luckyus-prod-84-new

**日期**: 2026-04-10  
**编制**: David Zeng (DBA)  
**用途**: RDS MySQL 8.0 → 8.4 升级配套参数组

---

## 一、参数组对比：luckyus-prod-80-new vs luckyus-prod-84-new

### 1.1 当前 8.0 参数组信息

| 属性 | 值 |
|------|-----|
| 参数组名称 | `luckyus-prod-80-new` |
| Family | `mysql8.0` |
| 自定义参数数 | 25 个（含 8 个与默认值相同的显式设置） |
| 实际差异参数 | 17 个 |
| 使用实例数 | 55 个 |

### 1.2 显式设置但与 default.mysql8.0 值相同的参数（8个）

以下参数被显式"锁定"，防止引擎默认值变更导致行为漂移，但值与默认完全一致：

| 参数 | 设置值 | 默认值 | 一致 |
|------|--------|--------|------|
| binlog_checksum | CRC32 | CRC32 | ✅ |
| binlog_format | ROW | ROW | ✅ |
| binlog_row_image | full | full | ✅ |
| character_set_server | utf8mb4 | utf8mb4 | ✅ |
| innodb_deadlock_detect | 1 | 1 | ✅ |
| log_output | FILE | FILE | ✅ |
| log_queries_not_using_indexes | 0 | 0 | ✅ |
| log_slow_admin_statements | 0 | 0 | ✅ |

> 在 8.4 参数组中不再显式设置这些参数，减少维护复杂度。

### 1.3 实际差异参数（17个）：8.0 默认 → 自定义值

| # | 参数 | MySQL 8.0 默认值 | 自定义值 | 类别 | 说明 |
|---|------|-----------------|---------|------|------|
| 1 | `binlog_order_commits` | 1 | **0** | 复制 | 关闭 binlog 提交排序，提升并发写入 |
| 2 | `binlog_rows_query_log_events` | 1 | **0** | 复制 | 不在 binlog 中记录原始 SQL 文本 |
| 3 | `enforce_gtid_consistency` | OFF | **ON** | 复制 | GTID 复制一致性 |
| 4 | `gtid-mode` | OFF | **ON** | 复制 | 启用 GTID 复制 |
| 5 | `innodb_adaptive_hash_index` | 1 | **0** | 性能 | 关闭 AHI，避免高并发下锁争用 |
| 6 | `innodb_lock_wait_timeout` | 50 | **20** | 性能 | 缩短锁等待超时（秒） |
| 7 | `innodb_print_all_deadlocks` | 0 | **1** | 监控 | 记录所有死锁到 error log |
| 8 | `innodb_strict_mode` | 1 | **0** | 兼容 | 放宽 InnoDB 严格模式 |
| 9 | `log_bin_trust_function_creators` | 0 | **1** | 兼容 | 允许非 SUPER 用户创建函数 |
| 10 | `long_query_time` | 10 | **0.1** | 监控 | 慢查询阈值从 10s 降至 100ms |
| 11 | `lower_case_table_names` | 0 | **1** | 兼容 | 表名不区分大小写 |
| 12 | `max_connections` | 动态(按内存) | **4000** | 性能 | 固定最大连接数 |
| 13 | `optimizer_switch` | 默认全部 | **prefer_ordering_index=off** | 性能 | 关闭排序索引优先，避免 8.0 回归 |
| 14 | `performance_schema` | 0 | **1** | 监控 | 开启性能监控 |
| 15 | `slow_query_log` | 0 | **1** | 监控 | 开启慢查询日志 |
| 16 | `sql_mode` | 含 ONLY_FULL_GROUP_BY 等 | **精简为 5 个** | 兼容 | 移除 ONLY_FULL_GROUP_BY |
| 17 | `transaction_isolation` | REPEATABLE-READ | **READ-COMMITTED** | 性能 | RC 隔离级别，减少间隙锁 |

### 1.4 8.4 新增参数（1个）

| # | 参数 | MySQL 8.4 默认值 | 自定义值 | 说明 |
|---|------|-----------------|---------|------|
| 18 | `mysql_native_password` | **OFF** | **ON** | 8.4 默认禁用该认证插件，必须开启以兼容现有用户 |

---

## 二、参数组总览：luckyus-prod-84-new（共 18 个自定义参数）

| # | 参数 | 值 | ApplyMethod | 类型 |
|---|------|-----|-------------|------|
| 1 | mysql_native_password | ON | pending-reboot | static |
| 2 | binlog_order_commits | 0 | immediate | dynamic |
| 3 | binlog_rows_query_log_events | 0 | immediate | dynamic |
| 4 | enforce_gtid_consistency | ON | pending-reboot | static |
| 5 | gtid-mode | ON | pending-reboot | static |
| 6 | innodb_adaptive_hash_index | 0 | immediate | dynamic |
| 7 | innodb_lock_wait_timeout | 20 | immediate | dynamic |
| 8 | innodb_print_all_deadlocks | 1 | immediate | dynamic |
| 9 | innodb_strict_mode | 0 | immediate | dynamic |
| 10 | log_bin_trust_function_creators | 1 | immediate | dynamic |
| 11 | long_query_time | 0.1 | immediate | dynamic |
| 12 | lower_case_table_names | 1 | pending-reboot | static |
| 13 | max_connections | 4000 | immediate | dynamic |
| 14 | optimizer_switch | *(见下方完整值)* | immediate | dynamic |
| 15 | performance_schema | 1 | pending-reboot | static |
| 16 | slow_query_log | 1 | immediate | dynamic |
| 17 | sql_mode | STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION | immediate | dynamic |
| 18 | transaction_isolation | READ-COMMITTED | immediate | dynamic |

**optimizer_switch 完整值**:
```
index_merge=on,index_merge_union=on,index_merge_sort_union=on,index_merge_intersection=on,engine_condition_pushdown=on,index_condition_pushdown=on,mrr=on,mrr_cost_based=on,block_nested_loop=on,batched_key_access=off,materialization=on,semijoin=on,loosescan=on,firstmatch=on,subquery_materialization_cost_based=on,use_index_extensions=on,prefer_ordering_index=off
```

> **5 个 static 参数** (mysql_native_password, enforce_gtid_consistency, gtid-mode, lower_case_table_names, performance_schema) 需要实例重启才能生效。

---

## 三、需创建的参数组列表

| 参数组名称 | Family | 用途 | 差异 |
|-----------|--------|------|------|
| `luckyus-prod-84-new` | mysql8.4 | 主参数组 (57 个实例) | 18 个自定义参数 |
| `luckyus-prod-84-new-groupconcatmaxlen` | mysql8.4 | salesorder 专用 (1 个实例) | 18 + 1 个 (group_concat_max_len=1048576) |

### 实例与参数组映射

| 当前参数组 | 实例数 | 升级后参数组 |
|-----------|--------|------------|
| `luckyus-prod-80-new` | 53 | `luckyus-prod-84-new` |
| `luckyus-prod` | 2 (devops, ldas) | `luckyus-prod-84-new` |
| `luckyus-prod-80-new-groupconcatmaxlen` | 1 (salesorder) | `luckyus-prod-84-new-groupconcatmaxlen` |
| `default.mysql8.4` | 2 (dba84test, datalink-84test) | `luckyus-prod-84-new` |

> **注**: `luckyus-prod` 与 `luckyus-prod-80-new` 差异仅为缺少 `log_bin_trust_function_creators=1` 和 `lower_case_table_names=1`（`luckyus-prod` 少 2 个参数），合并到新参数组后统一。

---

## 四、创建脚本

### 4.1 创建主参数组 luckyus-prod-84-new

```bash
#!/bin/bash
# =============================================================================
# Script: create-luckyus-prod-84-new.sh
# Purpose: Create MySQL 8.4 parameter group for Luckin USA RDS production
# Date: 2026-04-10
# Author: David Zeng (DBA)
# =============================================================================

set -euo pipefail
REGION="us-east-1"
PG_NAME="luckyus-prod-84-new"
PG_FAMILY="mysql8.4"

echo "=== Step 1: Creating parameter group ${PG_NAME} ==="
aws rds create-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --db-parameter-group-family "${PG_FAMILY}" \
  --description "Luckin USA production MySQL 8.4 (migrated from luckyus-prod-80-new)" \
  --region "${REGION}"

echo "=== Step 2: Setting 18 custom parameters ==="
aws rds modify-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --region "${REGION}" \
  --parameters \
    "ParameterName=mysql_native_password,ParameterValue=ON,ApplyMethod=pending-reboot" \
    "ParameterName=binlog_order_commits,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=binlog_rows_query_log_events,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=enforce_gtid_consistency,ParameterValue=ON,ApplyMethod=pending-reboot" \
    "ParameterName=gtid-mode,ParameterValue=ON,ApplyMethod=pending-reboot" \
    "ParameterName=innodb_adaptive_hash_index,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=innodb_lock_wait_timeout,ParameterValue=20,ApplyMethod=immediate" \
    "ParameterName=innodb_print_all_deadlocks,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=innodb_strict_mode,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=log_bin_trust_function_creators,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=long_query_time,ParameterValue=0.1,ApplyMethod=immediate" \
    "ParameterName=lower_case_table_names,ParameterValue=1,ApplyMethod=pending-reboot" \
    "ParameterName=max_connections,ParameterValue=4000,ApplyMethod=immediate" \
    "ParameterName=performance_schema,ParameterValue=1,ApplyMethod=pending-reboot" \
    "ParameterName=slow_query_log,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=transaction_isolation,ParameterValue=READ-COMMITTED,ApplyMethod=immediate"

echo "=== Step 3: Setting optimizer_switch (long value, separate call) ==="
aws rds modify-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --region "${REGION}" \
  --parameters \
    "ParameterName=optimizer_switch,ParameterValue='index_merge=on,index_merge_union=on,index_merge_sort_union=on,index_merge_intersection=on,engine_condition_pushdown=on,index_condition_pushdown=on,mrr=on,mrr_cost_based=on,block_nested_loop=on,batched_key_access=off,materialization=on,semijoin=on,loosescan=on,firstmatch=on,subquery_materialization_cost_based=on,use_index_extensions=on,prefer_ordering_index=off',ApplyMethod=immediate"

echo "=== Step 4: Setting sql_mode (separate call for clarity) ==="
aws rds modify-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --region "${REGION}" \
  --parameters \
    "ParameterName=sql_mode,ParameterValue='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION',ApplyMethod=immediate"

echo "=== Step 5: Verifying custom parameters ==="
aws rds describe-db-parameters \
  --db-parameter-group-name "${PG_NAME}" \
  --region "${REGION}" \
  --query "Parameters[?Source!='system' && Source!='engine-default'].[ParameterName,ParameterValue]" \
  --output table

echo "=== Done: ${PG_NAME} created with 18 custom parameters ==="
```

### 4.2 创建 salesorder 专用参数组 luckyus-prod-84-new-groupconcatmaxlen

```bash
#!/bin/bash
# =============================================================================
# Script: create-luckyus-prod-84-new-groupconcatmaxlen.sh
# Purpose: Create MySQL 8.4 parameter group for salesorder (extra group_concat_max_len)
# Date: 2026-04-10
# Author: David Zeng (DBA)
# =============================================================================

set -euo pipefail
REGION="us-east-1"
PG_NAME="luckyus-prod-84-new-groupconcatmaxlen"
PG_FAMILY="mysql8.4"

echo "=== Step 1: Creating parameter group ${PG_NAME} ==="
aws rds create-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --db-parameter-group-family "${PG_FAMILY}" \
  --description "Luckin USA production MySQL 8.4 with group_concat_max_len=1048576 (for salesorder)" \
  --region "${REGION}"

echo "=== Step 2: Setting 18 base parameters (same as luckyus-prod-84-new) ==="
aws rds modify-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --region "${REGION}" \
  --parameters \
    "ParameterName=mysql_native_password,ParameterValue=ON,ApplyMethod=pending-reboot" \
    "ParameterName=binlog_order_commits,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=binlog_rows_query_log_events,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=enforce_gtid_consistency,ParameterValue=ON,ApplyMethod=pending-reboot" \
    "ParameterName=gtid-mode,ParameterValue=ON,ApplyMethod=pending-reboot" \
    "ParameterName=innodb_adaptive_hash_index,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=innodb_lock_wait_timeout,ParameterValue=20,ApplyMethod=immediate" \
    "ParameterName=innodb_print_all_deadlocks,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=innodb_strict_mode,ParameterValue=0,ApplyMethod=immediate" \
    "ParameterName=log_bin_trust_function_creators,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=long_query_time,ParameterValue=0.1,ApplyMethod=immediate" \
    "ParameterName=lower_case_table_names,ParameterValue=1,ApplyMethod=pending-reboot" \
    "ParameterName=max_connections,ParameterValue=4000,ApplyMethod=immediate" \
    "ParameterName=performance_schema,ParameterValue=1,ApplyMethod=pending-reboot" \
    "ParameterName=slow_query_log,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=transaction_isolation,ParameterValue=READ-COMMITTED,ApplyMethod=immediate"

echo "=== Step 3: Setting optimizer_switch ==="
aws rds modify-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --region "${REGION}" \
  --parameters \
    "ParameterName=optimizer_switch,ParameterValue='index_merge=on,index_merge_union=on,index_merge_sort_union=on,index_merge_intersection=on,engine_condition_pushdown=on,index_condition_pushdown=on,mrr=on,mrr_cost_based=on,block_nested_loop=on,batched_key_access=off,materialization=on,semijoin=on,loosescan=on,firstmatch=on,subquery_materialization_cost_based=on,use_index_extensions=on,prefer_ordering_index=off',ApplyMethod=immediate"

echo "=== Step 4: Setting sql_mode ==="
aws rds modify-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --region "${REGION}" \
  --parameters \
    "ParameterName=sql_mode,ParameterValue='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION',ApplyMethod=immediate"

echo "=== Step 5: Setting extra parameter — group_concat_max_len ==="
aws rds modify-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --region "${REGION}" \
  --parameters \
    "ParameterName=group_concat_max_len,ParameterValue=1048576,ApplyMethod=immediate"

echo "=== Step 6: Verifying custom parameters ==="
aws rds describe-db-parameters \
  --db-parameter-group-name "${PG_NAME}" \
  --region "${REGION}" \
  --query "Parameters[?Source!='system' && Source!='engine-default'].[ParameterName,ParameterValue]" \
  --output table

echo "=== Done: ${PG_NAME} created with 19 custom parameters ==="
```

### 4.3 验证脚本

```bash
#!/bin/bash
# =============================================================================
# Script: verify-parameter-groups.sh
# Purpose: Compare 8.0 vs 8.4 parameter groups to confirm migration correctness
# Date: 2026-04-10
# Author: David Zeng (DBA)
# =============================================================================

REGION="us-east-1"

echo "========================================"
echo "  luckyus-prod-80-new (MySQL 8.0)"
echo "========================================"
aws rds describe-db-parameters \
  --db-parameter-group-name luckyus-prod-80-new \
  --region "${REGION}" \
  --query "Parameters[?Source!='system' && Source!='engine-default'].[ParameterName,ParameterValue]" \
  --output table

echo ""
echo "========================================"
echo "  luckyus-prod-84-new (MySQL 8.4)"
echo "========================================"
aws rds describe-db-parameters \
  --db-parameter-group-name luckyus-prod-84-new \
  --region "${REGION}" \
  --query "Parameters[?Source!='system' && Source!='engine-default'].[ParameterName,ParameterValue]" \
  --output table

echo ""
echo "========================================"
echo "  luckyus-prod-84-new-groupconcatmaxlen"
echo "========================================"
aws rds describe-db-parameters \
  --db-parameter-group-name luckyus-prod-84-new-groupconcatmaxlen \
  --region "${REGION}" \
  --query "Parameters[?Source!='system' && Source!='engine-default'].[ParameterName,ParameterValue]" \
  --output table
```

### 4.4 将现有 8.4 测试实例切换到新参数组

```bash
#!/bin/bash
# =============================================================================
# Script: apply-pg-to-84test.sh
# Purpose: Switch existing 8.4 test instances from default.mysql8.4 to luckyus-prod-84-new
# Date: 2026-04-10
# Author: David Zeng (DBA)
# =============================================================================

REGION="us-east-1"
PG_NAME="luckyus-prod-84-new"

for INSTANCE in aws-luckyus-dba84test-rw aws-luckyus-datalink-84test-rw; do
  echo "=== Applying ${PG_NAME} to ${INSTANCE} ==="
  aws rds modify-db-instance \
    --db-instance-identifier "${INSTANCE}" \
    --db-parameter-group-name "${PG_NAME}" \
    --apply-immediately \
    --region "${REGION}"
done

echo ""
echo "=== Waiting for instances to be available ==="
for INSTANCE in aws-luckyus-dba84test-rw aws-luckyus-datalink-84test-rw; do
  aws rds wait db-instance-available \
    --db-instance-identifier "${INSTANCE}" \
    --region "${REGION}"
  echo "${INSTANCE}: available"
done

echo ""
echo "NOTE: static parameters (mysql_native_password, enforce_gtid_consistency,"
echo "      gtid-mode, lower_case_table_names, performance_schema) require reboot."
echo "Run the following to reboot:"
echo ""
for INSTANCE in aws-luckyus-dba84test-rw aws-luckyus-datalink-84test-rw; do
  echo "  aws rds reboot-db-instance --db-instance-identifier ${INSTANCE} --region ${REGION}"
done
```

---

## 五、附录

### 附录 A: luckyus-prod (旧参数组) 与 luckyus-prod-80-new 差异

`luckyus-prod` 比 `luckyus-prod-80-new` 少 2 个参数:

| 参数 | luckyus-prod | luckyus-prod-80-new |
|------|-------------|-------------------|
| log_bin_trust_function_creators | *(未设置, 默认=0)* | 1 |
| lower_case_table_names | *(未设置, 默认=0)* | 1 |

使用 `luckyus-prod` 的 2 个实例 (`devops`, `ldas`) 升级后统一到 `luckyus-prod-84-new`，将获得这 2 个参数。

> **已验证 (2026-04-10)**: `devops` 和 `ldas` 当前 `lower_case_table_names=0`，但经检查两个实例的所有库名和表名均为纯小写，无大小写混用。可以安全切换到 `lower_case_table_names=1`，无需单独建参数组。

### 附录 B: luckyus-prod-80-new-groupconcatmaxlen 与 luckyus-prod-80-new 差异

仅多 1 个参数:

| 参数 | 值 | 说明 |
|------|-----|------|
| group_concat_max_len | 1048576 (1MB) | salesorder 业务需要大 GROUP_CONCAT 结果 |
