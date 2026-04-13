# MySQL 8.0.40 → 8.0.45 参数漂移分析报告

**日期**: 2026-04-13
**作者**: David Zeng (DBA Team)
**范围**: AWS Account 257394478466 (us-east-1) — 62 MySQL RDS 实例
**参数组**: `luckyus-prod-80-new`（56 实例）、`luckyus-prod`（2 实例）、`-groupconcatmaxlen`（1 实例）

---

## 1. 总结

| 检查项 | 结果 |
|--------|------|
| 系统变量默认值变化 | **零** — 8.0.40 至 8.0.45 之间无任何参数默认值变更 |
| 参数组族 | 所有 8.0.x 版本共用 `mysql8.0` 族，AWS 不区分子版本 |
| 新增服务端参数 | 1 个（`--check-table-functions`，8.0.42 引入） |
| 新增客户端选项 | 2 个（`--system-command` 8.0.40、`--commands` 8.0.43） |
| 废弃/移除参数 | **零** |
| 行为变更（类似参数漂移） | 2 项（详见第 3 节） |
| 自定义参数组兼容性 | **全部兼容** — 18 个自定义参数无需调整 |
| `innodb_spin_wait_delay` 是否调整过 | **否** — 参数组为 engine-default，运行时值为默认值 6 |
| 空间索引存在情况 | **零** — 62 个实例中未发现任何空间索引 |

**结论：8.0.40 → 8.0.45 升级路径无参数漂移风险，可安全推进。**

---

## 2. 逐版本参数变化明细

### 8.0.40（RDS 发布: 2024-11-13）

| 类别 | 变更 |
|------|------|
| 默认值变化 | 无 |
| 新增选项 | `--system-command`（mysql 客户端选项，默认 ON，控制 `system` 命令是否可用） |
| 废弃/移除 | 无 |
| 其他 | OpenSSL 升级至 3.0.15；RDS 修复字符集升级失败问题 |

### 8.0.41（RDS 发布: 2025-02-19）

| 类别 | 变更 |
|------|------|
| 默认值变化 | 无 |
| 新增选项 | 无 |
| 废弃/移除 | 无 |
| **行为变更** | 空表 `ALTER TABLE ADD/DROP COLUMN` 从 `INSTANT` 改为 `INPLACE` 算法（Bug #113051） |
| **不兼容变更** | 空间索引可能存在 pre-8.0.41 创建的损坏，升级后需 drop 并重建 |
| 其他 | RDS 更新 tzdata 至 2025a；修复 `mysql.rds_set_configuration` 排序规则错误 |

### 8.0.42（RDS 发布: 2025-04-29）

| 类别 | 变更 |
|------|------|
| 默认值变化 | 无 |
| **新增选项** | `--check-table-functions`（服务端启动选项，默认 `ABORT`） |
| 废弃/移除 | 无 |
| **行为修复** | `innodb_spin_wait_delay` busy-wait 回归修正 — 8.0.30 引入的随机值范围从 [0,N-1] 误改为 [0,N]，导致平均延迟增加约 20%，此版本恢复正确行为（Bug #116463） |
| 其他 | OpenSSL 升级至 3.0.16；Binlog 依赖跟踪内存减少约 60%；RDS 更新 tzdata 至 2025b |

### 8.0.43（RDS 发布: 2025-08-01）

| 类别 | 变更 |
|------|------|
| 默认值变化 | 无 |
| 新增选项 | `--commands`（mysql 客户端选项，默认 ON，控制客户端命令是否可用） |
| 废弃/移除 | 无 |
| 其他 | curl 升级至 8.14.1；InnoDB 全文搜索性能改进 |

### 8.0.44（RDS 发布: 2025-11-13）

| 类别 | 变更 |
|------|------|
| 默认值变化 | 无 |
| 新增选项 | 无 |
| 废弃/移除 | 无 |
| 其他 | 纯 bug 修复版本（Audit Log, InnoDB, Optimizer, Performance Schema） |

### 8.0.45（RDS 发布: 2026-02-03）

| 类别 | 变更 |
|------|------|
| 默认值变化 | 无 |
| 新增选项 | 无 |
| 废弃/移除 | 无 |
| InnoDB 日志变更 | `ER_IB_WRN_REDO_DISABLED` → `ER_IB_WRN_REDO_DISABLED_INFO`（含当前 LSN）；`ER_IB_MSG_LOG_WRITER_WAIT_ON_NEW_LOG_FILE` → `..._INFO`（含 redo 容量信息） |
| 其他 | OpenSSL 升级至 3.0.18；RDS 更新 tzdata 至 2025c；审计日志 SQL 语句遗漏修复 |

---

## 3. 行为变更详细说明（非参数默认值但影响运行行为）

### 3.1 `innodb_spin_wait_delay` 行为修正（8.0.42）

| 项目 | 说明 |
|------|------|
| 问题根源 | MySQL 8.0.30 将 spin-wait 随机延迟范围从 `[0, N-1]` 误改为 `[0, N]`（含边界），导致平均 busy-wait 延迟增加约 20% |
| 修复版本 | 8.0.42（Bug #116463） |
| 默认值 | `6`（未改变） |
| **我们的环境** | 参数组 `luckyus-prod-80-new` 中为 `engine-default`，运行时值为 `6` |
| **影响** | **无需操作** — 从未手动调整过，升级到 8.0.42+ 后自动恢复正确行为 |

验证命令与结果：

```
-- 参数组检查
aws rds describe-db-parameters --db-parameter-group-name luckyus-prod-80-new \
  --query "Parameters[?ParameterName=='innodb_spin_wait_delay']"
→ Source: "engine-default"

-- 运行时检查 (dbatest-rw)
SHOW GLOBAL VARIABLES LIKE 'innodb_spin_wait_delay';
→ Value: 6
```

### 3.2 空表 DDL 算法变更（8.0.41）

| 项目 | 说明 |
|------|------|
| 变更内容 | 空表 `ALTER TABLE ADD/DROP COLUMN` 从 `INSTANT` 改为 `INPLACE` |
| 影响范围 | 仅对空表有效，生产环境影响极低 |
| **我们的环境** | 无需操作 — 空表 DDL 在生产中极少发生 |

### 3.3 空间索引损坏风险（8.0.41 不兼容变更）

| 项目 | 说明 |
|------|------|
| 风险说明 | pre-8.0.41 版本创建的空间索引可能存在损坏，建议升级后 drop 并重建 |
| **我们的环境** | **不受影响** — 全 fleet 62 个实例中零空间索引 |

验证方法：

```sql
-- 对 62 个 MySQL 实例逐一执行
SELECT TABLE_SCHEMA, TABLE_NAME, INDEX_NAME, COLUMN_NAME, INDEX_TYPE 
FROM information_schema.STATISTICS 
WHERE INDEX_TYPE = 'SPATIAL' LIMIT 100;
→ 全部返回空结果集
```

> 注：地理位置相关数据（门店坐标、配送半径等）使用经纬度 DECIMAL 字段 + BTREE 索引，或由 PostgreSQL 实例 `aws-luckyus-pgilkmap-rw`（PostGIS）处理。

---

## 4. 自定义参数组兼容性验证

参数组 `luckyus-prod-80-new` 中 18 个自定义参数在 8.0.45 中的兼容性：

| # | 参数名 | 自定义值 | 8.0.45 兼容 | 备注 |
|---|--------|---------|-------------|------|
| 1 | `binlog_format` | ROW | Yes | |
| 2 | `binlog_checksum` | CRC32 | Yes | |
| 3 | `binlog_order_commits` | 0 | Yes | |
| 4 | `binlog_row_image` | full | Yes | |
| 5 | `character_set_server` | utf8mb4 | Yes | |
| 6 | `enforce_gtid_consistency` | ON | Yes | |
| 7 | `gtid-mode` | ON | Yes | |
| 8 | `innodb_adaptive_hash_index` | 0 | Yes | |
| 9 | `innodb_deadlock_detect` | ON | Yes | |
| 10 | `innodb_lock_wait_timeout` | 20 | Yes | |
| 11 | `innodb_strict_mode` | 0 | Yes | |
| 12 | `log_output` | FILE | Yes | |
| 13 | `log_queries_not_using_indexes` | 1 | Yes | |
| 14 | `log_slow_admin_statements` | 1 | Yes | |
| 15 | `long_query_time` | 0.1 | Yes | |
| 16 | `lower_case_table_names` | 1 | Yes | |
| 17 | `max_connections` | 4000 | Yes | |
| 18 | `optimizer_switch` | prefer_ordering_index=off | Yes | |
| 19 | `performance_schema` | 1 | Yes | |
| 20 | `sql_mode` | STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION | Yes | |
| 21 | `transaction_isolation` | READ-COMMITTED | Yes | |

**结论：全部参数 100% 兼容，无需修改参数组。**

---

## 5. 新增选项汇总

| 版本 | 选项名 | 类型 | 默认值 | 说明 | 是否需要关注 |
|------|--------|------|--------|------|-------------|
| 8.0.40 | `--system-command` | 客户端 | ON | 控制 mysql 客户端 `system` 命令 | 否 — 不影响服务端 |
| 8.0.42 | `--check-table-functions` | 服务端启动 | ABORT | 升级时校验表函数兼容性，不通过则中断升级 | **是** — 升级安全机制，保持默认即可 |
| 8.0.43 | `--commands` | 客户端 | ON | 控制 mysql 客户端命令 | 否 — 不影响服务端 |

---

## 6. InnoDB 错误码变更（8.0.45）

| 旧错误码 | 新错误码 | 变更说明 |
|----------|---------|---------|
| `ER_IB_WRN_REDO_DISABLED` | `ER_IB_WRN_REDO_DISABLED_INFO` | 新增当前 LSN 信息 |
| `ER_IB_MSG_LOG_WRITER_WAIT_ON_NEW_LOG_FILE` | `ER_IB_MSG_LOG_WRITER_WAIT_ON_NEW_LOG_FILE_INFO` | 新增 redo log 容量信息 |

**影响**：如果有监控告警规则基于错误日志文本匹配这些错误码，需更新匹配模式。当前我们的告警主要基于 CloudWatch Metrics 而非日志文本匹配，**影响极低**。

---

## 7. OpenSSL 版本演进

| MySQL 版本 | OpenSSL 版本 | 安全修复 |
|-----------|-------------|---------|
| 8.0.40 | 3.0.15 | 基准 |
| 8.0.42 | 3.0.16 | +1 补丁 |
| 8.0.45 | 3.0.18 | +3 补丁（累计） |

升级到 8.0.45 可获得最新的 OpenSSL 安全修复。

---

## 8. 最终结论与建议

### 参数漂移评估：无风险

MySQL 8.0.40 至 8.0.45 之间：
- **零参数默认值变化**
- **零参数废弃/移除**
- **自定义参数组 100% 兼容**
- **`innodb_spin_wait_delay` 未被调整过**，升级后自动获益于 8.0.42 的行为修正
- **零空间索引**，不受 8.0.41 不兼容变更影响

### 升级前需要做的事

| # | 操作 | 必要性 |
|---|------|--------|
| 1 | 修改参数组 | **不需要** |
| 2 | 重建空间索引 | **不需要**（无空间索引） |
| 3 | 调整 innodb_spin_wait_delay | **不需要**（未修改过） |
| 4 | 更新监控告警规则 | **可选** — 检查是否有基于 InnoDB 错误码文本的告警 |
| 5 | 测试 `--check-table-functions` | **建议** — 在 dbatest 实例先验证，确保无表函数兼容问题 |

### 对比提醒：8.0 → 8.4 才是参数漂移的重灾区

| 对比维度 | 8.0.40 → 8.0.45 | 8.0 → 8.4 |
|---------|-----------------|-----------|
| 参数默认值变化 | 0 | 多项（temptable_use_mmap, sql_mode, innodb_adaptive_hash_index 等） |
| 参数移除 | 0 | 29 个 |
| 参数重命名 | 0 | 19 个（slave_* → replica_*, master_* → source_*） |
| 新增参数 | 1 | 12+ |
| 参数组修改 | 不需要 | 必须新建 8.4 参数组 |

---

*报告生成工具: Claude Code (Opus 4.6)*
*数据来源: MySQL Release Notes (dev.mysql.com), AWS RDS Release Notes, 生产环境实时查询*
