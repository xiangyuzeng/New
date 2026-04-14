# MySQL 8.4 参数组配置文档 — luckyus-prod-84

**日期**: 2026-04-10 (更新: 2026-04-14)  
**编制**: David Zeng (DBA)  
**用途**: RDS MySQL 8.0 → 8.4 升级配套参数组

---

## 一、参数组对比：luckyus-prod-80-new vs luckyus-prod-84

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

### 1.4 8.4 兼容性说明（2026-04-14 更新）

#### ~~mysql_native_password~~ — 无需设置

RDS MySQL 8.4 中 `mysql_native_password` 已默认 `ON` 且 `IsModifiable=False`（不可修改）。
AWS 主动保持了向后兼容，**无需也不能在参数组中设置此参数**。
原脚本中包含此参数会导致 `modify-db-parameter-group` 直接报错。

#### lower_case_table_names — 仅限创建实例时设定

RDS MySQL 8.0+ 的 `lower_case_table_names` **只能在实例创建时通过参数组设定**，已有实例不可变更。
对已有实例应用含不同 `lower_case_table_names` 值的参数组会报错：
> *"The parameter value for lower_case_table_names can't be changed for RDS for MySQL DB instances running version 8.0 or higher."*

因此需要两个主参数组：
- `luckyus-prod-84`（含 `lower_case_table_names=1`，17 个参数）— 适用于原 `luckyus-prod-80-new` 的 53 个实例（创建时已为 1）
- `luckyus-prod-84-lctn0`（不设 `lower_case_table_names`，16 个参数）— 适用于 devops, ldas, dba84test, datalink-84test（创建时为 0，共 4 个）

---

## 二、参数组总览

### 2.1 luckyus-prod-84（共 17 个自定义参数）

| # | 参数 | 值 | ApplyMethod | 类型 |
|---|------|-----|-------------|------|
| 1 | binlog_order_commits | 0 | immediate | dynamic |
| 2 | binlog_rows_query_log_events | 0 | immediate | dynamic |
| 3 | enforce_gtid_consistency | ON | pending-reboot | static |
| 4 | gtid-mode | ON | pending-reboot | static |
| 5 | innodb_adaptive_hash_index | 0 | immediate | dynamic |
| 6 | innodb_lock_wait_timeout | 20 | immediate | dynamic |
| 7 | innodb_print_all_deadlocks | 1 | immediate | dynamic |
| 8 | innodb_strict_mode | 0 | immediate | dynamic |
| 9 | log_bin_trust_function_creators | 1 | immediate | dynamic |
| 10 | long_query_time | 0.1 | immediate | dynamic |
| 11 | lower_case_table_names | 1 | pending-reboot | static |
| 12 | max_connections | 4000 | immediate | dynamic |
| 13 | optimizer_switch | *(见下方完整值)* | immediate | dynamic |
| 14 | performance_schema | 1 | pending-reboot | static |
| 15 | slow_query_log | 1 | immediate | dynamic |
| 16 | sql_mode | STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION | immediate | dynamic |
| 17 | transaction_isolation | READ-COMMITTED | immediate | dynamic |

### 2.2 luckyus-prod-84-lctn0（共 16 个自定义参数）

与 `luckyus-prod-84` 完全相同，**但不设置 `lower_case_table_names`**（保持实例创建时的默认值 0）。

### 2.3 luckyus-prod-84-groupconcatmaxlen（共 18 个自定义参数）

与 `luckyus-prod-84` 完全相同 + `group_concat_max_len=1048576`。

**optimizer_switch 完整值**:
```
index_merge=on,index_merge_union=on,index_merge_sort_union=on,index_merge_intersection=on,engine_condition_pushdown=on,index_condition_pushdown=on,mrr=on,mrr_cost_based=on,block_nested_loop=on,batched_key_access=off,materialization=on,semijoin=on,loosescan=on,firstmatch=on,subquery_materialization_cost_based=on,use_index_extensions=on,prefer_ordering_index=off
```

> **3 个 static 参数** (enforce_gtid_consistency, gtid-mode, performance_schema) 需要实例重启才能生效。
> `lower_case_table_names` 也是 static，但仅在创建实例时生效，重启不会改变其值。

---

## 三、需创建的参数组列表

| 参数组名称 | Family | 用途 | 自定义参数数 |
|-----------|--------|------|------------|
| `luckyus-prod-84` | mysql8.4 | 主参数组，含 lctn=1 | 17 个 |
| `luckyus-prod-84-lctn0` | mysql8.4 | lctn=0 实例专用 | 16 个 |
| `luckyus-prod-84-groupconcatmaxlen` | mysql8.4 | salesorder 专用 | 18 个 |

### 实例与参数组映射

| 当前参数组 | 实例数 | 升级后参数组 | 说明 |
|-----------|--------|------------|------|
| `luckyus-prod-80-new` | 53 | `luckyus-prod-84` | lctn=1，直接切换 |
| `luckyus-prod` | 2 (devops, ldas) | `luckyus-prod-84-lctn0` | lctn=0，不可变更 |
| `luckyus-prod-80-new-groupconcatmaxlen` | 1 (salesorder) | `luckyus-prod-84-groupconcatmaxlen` | lctn=1，直接切换 |
| `default.mysql8.4` | 2 (dba84test, datalink-84test) | `luckyus-prod-84-lctn0` | lctn=0，不可变更 |

---

## 四、创建脚本

### 4.1 创建主参数组 luckyus-prod-84（17 个参数，含 lctn=1）

```bash
#!/bin/bash
# =============================================================================
# Script: create-luckyus-prod-84.sh
# Purpose: Create MySQL 8.4 parameter group for Luckin USA RDS production
# Date: 2026-04-10 (updated 2026-04-14)
# Author: David Zeng (DBA)
#
# NOTE: mysql_native_password is NOT included — RDS 8.4 defaults to ON
#       and marks it IsModifiable=False (cannot be set in parameter groups).
# =============================================================================

set -euo pipefail
REGION="us-east-1"
PG_NAME="luckyus-prod-84"
PG_FAMILY="mysql8.4"

echo "=== Step 1: Creating parameter group ${PG_NAME} ==="
aws rds create-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --db-parameter-group-family "${PG_FAMILY}" \
  --description "Luckin USA production MySQL 8.4 with lower_case_table_names=1 (migrated from luckyus-prod-80-new)" \
  --region "${REGION}"

echo "=== Step 2: Setting 15 dynamic + static parameters ==="
aws rds modify-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --region "${REGION}" \
  --parameters \
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

echo "=== Done: ${PG_NAME} created with 17 custom parameters ==="
```

### 4.2 创建 lctn0 参数组 luckyus-prod-84-lctn0（16 个参数，不设 lctn）

```bash
#!/bin/bash
# =============================================================================
# Script: create-luckyus-prod-84-lctn0.sh
# Purpose: Create MySQL 8.4 parameter group for instances with lower_case_table_names=0
#          (devops, ldas, dba84test, datalink-84test)
# Date: 2026-04-14
# Author: David Zeng (DBA)
#
# NOTE: This is identical to luckyus-prod-84 EXCEPT:
#       - lower_case_table_names is NOT set (stays at instance creation default=0)
#       - mysql_native_password is NOT included (RDS 8.4 default=ON, IsModifiable=False)
# =============================================================================

set -euo pipefail
REGION="us-east-1"
PG_NAME="luckyus-prod-84-lctn0"
PG_FAMILY="mysql8.4"

echo "=== Step 1: Creating parameter group ${PG_NAME} ==="
aws rds create-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --db-parameter-group-family "${PG_FAMILY}" \
  --description "Luckin USA production MySQL 8.4 WITHOUT lower_case_table_names (for lctn=0 instances)" \
  --region "${REGION}"

echo "=== Step 2: Setting 14 dynamic + static parameters ==="
aws rds modify-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --region "${REGION}" \
  --parameters \
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

echo "=== Done: ${PG_NAME} created with 16 custom parameters ==="
```

### 4.3 创建 salesorder 专用参数组 luckyus-prod-84-groupconcatmaxlen（18 个参数）

```bash
#!/bin/bash
# =============================================================================
# Script: create-luckyus-prod-84-groupconcatmaxlen.sh
# Purpose: Create MySQL 8.4 parameter group for salesorder (extra group_concat_max_len)
# Date: 2026-04-10 (updated 2026-04-14)
# Author: David Zeng (DBA)
# =============================================================================

set -euo pipefail
REGION="us-east-1"
PG_NAME="luckyus-prod-84-groupconcatmaxlen"
PG_FAMILY="mysql8.4"

echo "=== Step 1: Creating parameter group ${PG_NAME} ==="
aws rds create-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --db-parameter-group-family "${PG_FAMILY}" \
  --description "Luckin USA production MySQL 8.4 with group_concat_max_len=1048576 (for salesorder)" \
  --region "${REGION}"

echo "=== Step 2: Setting 15 dynamic + static parameters ==="
aws rds modify-db-parameter-group \
  --db-parameter-group-name "${PG_NAME}" \
  --region "${REGION}" \
  --parameters \
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

echo "=== Done: ${PG_NAME} created with 18 custom parameters ==="
```

### 4.4 验证脚本

```bash
#!/bin/bash
# =============================================================================
# Script: verify-parameter-groups.sh
# Purpose: Compare 8.0 vs 8.4 parameter groups to confirm migration correctness
# Date: 2026-04-10 (updated 2026-04-14)
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
echo "  luckyus-prod-84 (MySQL 8.4, lctn=1)"
echo "========================================"
aws rds describe-db-parameters \
  --db-parameter-group-name luckyus-prod-84 \
  --region "${REGION}" \
  --query "Parameters[?Source!='system' && Source!='engine-default'].[ParameterName,ParameterValue]" \
  --output table

echo ""
echo "========================================"
echo "  luckyus-prod-84-lctn0 (MySQL 8.4, lctn=0)"
echo "========================================"
aws rds describe-db-parameters \
  --db-parameter-group-name luckyus-prod-84-lctn0 \
  --region "${REGION}" \
  --query "Parameters[?Source!='system' && Source!='engine-default'].[ParameterName,ParameterValue]" \
  --output table

echo ""
echo "========================================"
echo "  luckyus-prod-84-groupconcatmaxlen"
echo "========================================"
aws rds describe-db-parameters \
  --db-parameter-group-name luckyus-prod-84-groupconcatmaxlen \
  --region "${REGION}" \
  --query "Parameters[?Source!='system' && Source!='engine-default'].[ParameterName,ParameterValue]" \
  --output table

echo ""
echo "========================================"
echo "  Diff: luckyus-prod-84 vs lctn0"
echo "========================================"
echo "Expected difference: lctn0 should NOT have lower_case_table_names"
```

### 4.5 将现有 8.4 测试实例切换到 lctn0 参数组

```bash
#!/bin/bash
# =============================================================================
# Script: apply-pg-to-84test.sh
# Purpose: Switch existing 8.4 test instances from default.mysql8.4 to luckyus-prod-84-lctn0
# Date: 2026-04-14
# Author: David Zeng (DBA)
#
# NOTE: These instances have lower_case_table_names=0, so they MUST use the
#       lctn0 variant. Using luckyus-prod-84 (lctn=1) will fail.
# =============================================================================

REGION="us-east-1"
PG_NAME="luckyus-prod-84-lctn0"

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
echo "NOTE: static parameters (enforce_gtid_consistency, gtid-mode,"
echo "      performance_schema) require reboot to take effect."
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

使用 `luckyus-prod` 的 2 个实例 (`devops`, `ldas`) 升级后使用 `luckyus-prod-84-lctn0`。
这 2 个实例会获得 `log_bin_trust_function_creators=1`，但 `lower_case_table_names` 保持为 0（不可变更）。

> **已验证 (2026-04-14)**:
> - `devops`: 111 个活跃连接，承载 auth/izeus/PTS/UAM/Grafana/datalink canal 等核心服务
> - `ldas`: 24 个活跃连接，承载 ozono/kafadmin/apigateway/nacos/cmdb 等服务
> - 两个实例均为重度使用的生产库，`lower_case_table_names` 无法变更
> - RDS MySQL 8.0+ 中 `lower_case_table_names` 只能在实例创建时设定

### 附录 B: luckyus-prod-80-new-groupconcatmaxlen 与 luckyus-prod-80-new 差异

仅多 1 个参数:

| 参数 | 值 | 说明 |
|------|-----|------|
| group_concat_max_len | 1048576 (1MB) | salesorder 业务需要大 GROUP_CONCAT 结果 |

### 附录 C: mysql_native_password 不可修改验证记录

```
$ aws rds describe-db-parameters --db-parameter-group-name default.mysql8.4 \
    --query "Parameters[?ParameterName=='mysql_native_password']" --output table

+------------------------+-----+--------+----------+
|  mysql_native_password |  ON |  False |  static  |
+------------------------+-----+--------+----------+
```

RDS MySQL 8.4 中此参数已由 AWS 强制设为 `ON`，`IsModifiable=False`。
在参数组中设置此参数会导致 `modify-db-parameter-group` API 调用失败。

### 附录 D: 参数组矩阵对照

| 参数 | prod-84 | prod-84-lctn0 | prod-84-groupconcatmaxlen |
|------|:-----------:|:-----------------:|:----------------------------:|
| binlog_order_commits=0 | ✅ | ✅ | ✅ |
| binlog_rows_query_log_events=0 | ✅ | ✅ | ✅ |
| enforce_gtid_consistency=ON | ✅ | ✅ | ✅ |
| gtid-mode=ON | ✅ | ✅ | ✅ |
| innodb_adaptive_hash_index=0 | ✅ | ✅ | ✅ |
| innodb_lock_wait_timeout=20 | ✅ | ✅ | ✅ |
| innodb_print_all_deadlocks=1 | ✅ | ✅ | ✅ |
| innodb_strict_mode=0 | ✅ | ✅ | ✅ |
| log_bin_trust_function_creators=1 | ✅ | ✅ | ✅ |
| long_query_time=0.1 | ✅ | ✅ | ✅ |
| **lower_case_table_names=1** | **✅** | **—** | **✅** |
| max_connections=4000 | ✅ | ✅ | ✅ |
| optimizer_switch (prefer_ordering_index=off) | ✅ | ✅ | ✅ |
| performance_schema=1 | ✅ | ✅ | ✅ |
| slow_query_log=1 | ✅ | ✅ | ✅ |
| sql_mode (5 modes) | ✅ | ✅ | ✅ |
| transaction_isolation=READ-COMMITTED | ✅ | ✅ | ✅ |
| **group_concat_max_len=1048576** | **—** | **—** | **✅** |
| **合计** | **17** | **16** | **18** |
