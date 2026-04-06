# MySQL RDS 升级计划：8.0.x → 8.0.45 → 8.4.8

**制定日期**: 2026-04-06
**制定人**: David Zeng (DBA)
**AWS Account**: 257394478466 (us-east-1)

---

## 一、背景与紧迫性

| 项目 | 详情 |
|------|------|
| 当前状态 | 61 个 MySQL RDS 实例，全部 `extended-support-disabled` |
| 当前版本 | 58 个 8.0.40 + 1 个 8.0.41 + 1 个 8.0.42 + 1 个 8.0.44 |
| 8.0.40/41 标准支持到期 | **2026-05-31**（仅剩 55 天） |
| 8.0 大版本标准支持到期 | **2026-07-31**（仅剩 116 天） |
| 到期后果 | Extended Support 已禁用 → AWS 将**自动强制升级大版本**到 8.4 |

**目标**: 在标准支持到期前，主动完成 8.0.x → 8.0.45 → 8.4.8 两阶段升级，确保可控、可验证、可回滚。

---

## 二、升级路径

```
Phase 1 (小版本)                Phase 2 (大版本)
8.0.40 ─┐
8.0.41 ─┤
8.0.42 ─┼──→ 8.0.45 ──────────→ 8.4.8
8.0.44 ─┘
```

| 阶段 | 类型 | 风险等级 | 预计停机(Multi-AZ) | 备注 |
|------|------|---------|-------------------|------|
| Phase 1 | 小版本升级 | 低 | ~30s failover | 无兼容性问题，仅 bug fix + 安全补丁 |
| Phase 2 | 大版本升级 | 中 | ~10min + failover | RDS 自动 precheck，失败自动回滚 |

---

## 三、环境现状

### 3.1 版本分布

| 当前版本 | 实例数 | 标准支持到期 |
|---------|--------|------------|
| 8.0.40 | 58 | 2026-05-31 |
| 8.0.41 | 1 (ldas01) | 2026-05-31 |
| 8.0.42 | 1 (dbatest) | 2026-07-31 |
| 8.0.44 | 1 (iluckyams) | 2026-07-31 |

### 3.2 实例规格分布

| 实例类型 | 数量 | vCPU | 内存 |
|---------|------|------|------|
| db.t4g.micro | 40 | 2 | 1 GB |
| db.t4g.medium | 17 | 2 | 4 GB |
| db.t4g.large | 2 | 2 | 8 GB |
| db.t4g.xlarge | 1 | 4 | 16 GB |
| db.t3.small | 1 | 2 | 2 GB |

### 3.3 关键环境特征

- **全部 Multi-AZ**: 61/61 — 升级时先升 standby 再 failover，停机时间短
- **无 Read Replica**: 无需处理副本升级顺序
- **全部当前代实例类型 (t4g/t3)**: 无需先升级实例 Class
- **所有实例 extended-support-disabled**: 不会产生 Extended Support 费用

### 3.4 参数组

| 参数组 | Family | 实例数 | 使用者 |
|--------|--------|--------|--------|
| `luckyus-prod-80-new` | mysql8.0 | 58 | 大部分实例 |
| `luckyus-prod` | mysql8.0 | 2 | devops-rw, ldas-rw |
| `luckyus-prod-80-new-groupconcatmaxlen` | mysql8.0 | 1 | salesorder-rw |

**自定义参数（需迁移到 8.4 参数组的）**:

| 参数 | 值 | 8.4 兼容性 |
|------|-----|-----------|
| binlog_checksum | CRC32 | ✅ 兼容 |
| binlog_format | ROW | ✅ 兼容（8.4 中已废弃但仍可设置，ROW 为唯一推荐值） |
| binlog_order_commits | 0 | ✅ 兼容 |
| binlog_row_image | full | ✅ 兼容 |
| binlog_rows_query_log_events | 0 | ✅ 兼容 |
| character_set_server | utf8mb4 | ✅ 兼容（8.4 默认即为 utf8mb4） |
| enforce_gtid_consistency | ON | ✅ 兼容 |
| gtid-mode | ON | ✅ 兼容 |
| innodb_adaptive_hash_index | 0 | ✅ 兼容 |
| innodb_deadlock_detect | 1 | ✅ 兼容 |
| innodb_lock_wait_timeout | 20 | ✅ 兼容 |
| innodb_print_all_deadlocks | 1 | ✅ 兼容 |
| innodb_strict_mode | 0 | ✅ 兼容 |
| log_bin_trust_function_creators | 1 | ✅ 兼容（8.4 中已废弃但仍可设置） |
| log_output | FILE | ✅ 兼容 |
| log_queries_not_using_indexes | 0 | ✅ 兼容 |
| log_slow_admin_statements | 0 | ✅ 兼容 |
| long_query_time | 0.1 | ✅ 兼容 |
| lower_case_table_names | 1 | ✅ 兼容 |
| max_connections | 4000 | ✅ 兼容 |
| optimizer_switch | (自定义值) | ⚠️ 需验证 8.4 新增/移除的 switch |
| performance_schema | 1 | ✅ 兼容 |
| slow_query_log | 1 | ✅ 兼容 |
| sql_mode | STRICT_TRANS_TABLES,... | ✅ 兼容 |
| transaction_isolation | READ-COMMITTED | ✅ 兼容 |
| group_concat_max_len | 1048576 | ✅ 兼容（仅 salesorder-rw） |

---

## 四、兼容性调查结果（2026-04-02 审计）

> 以下内容来自 Phase 2（8.4 大版本升级）的前期兼容性调查，包括废弃 SQL 审计、参数兼容性检查、字符集审计等。
> 详细报告：[compatibility_checklist.md](../../compatibility_checklist.md)、[mysql-deprecated-sql-audit-20260402.md](mysql-deprecated-sql-audit-20260402.md)、[mysql-8045-upgrade-compatibility-report.md](mysql-8045-upgrade-compatibility-report.md)

### 4.1 问题总览

| # | 问题 | 严重级别 | 影响范围 | 影响阶段 | 必须在升级前修复 |
|---|------|---------|---------|---------|----------------|
| 1 | `SHOW SLAVE STATUS` 在 8.4 中已移除 | **CRITICAL** | 全部 61 实例，~120 万次执行/实例 | Phase 2 | **是** |
| 2 | `information_schema.PROCESSLIST` 在 8.4 中已移除 | **HIGH** | 全部 61 实例，~37 万次执行/实例 | Phase 2 | **是** |
| 3 | `mysql_native_password` 在 8.4 中已废弃 | **CRITICAL** | 全部 61 实例，所有 90+ 用户 | Phase 2 | 部分（见说明） |
| 4 | `utf8mb3` 字符集表 | **MEDIUM** | 4 个实例，~850+ 列 | Phase 2 | 建议 |
| 5 | `SHOW MASTER STATUS` 在 8.4 中已移除 | **MEDIUM** | 全部实例（cactistats） | Phase 2 | **是** |
| 6 | 8.4 参数组不存在 | **CRITICAL** | Phase 2 前提 | Phase 2 | **是** |
| 7 | db.t4g.micro 内存压力 | **MEDIUM** | 40 个实例，~100-150MB 可用内存 | Phase 1 & 2 | 注意窗口 |

> **已排除项**：初始审计中标记的 `GROUP BY ... ASC/DESC` 问题（2.5M+ 调用）经复查为**误报**。
> 实际查询均为标准 `GROUP BY col ORDER BY col DESC` 写法，DESC 修饰的是 ORDER BY 而非 GROUP BY。
> 审计中使用的正则 `REGEXP 'GROUP BY.*DESC'` 过于宽泛，错误匹配了 ORDER BY 子句中的 DESC。

### 4.2 CRITICAL — `SHOW SLAVE STATUS` 已移除（Issue #1）

**MySQL 8.4 已完全移除此命令**，必须使用 `SHOW REPLICA STATUS` 替代。

**调用来源（仅 2 个工具）**：

| 工具 | 来源 IP | 频率 | 每日总执行量(61 实例) |
|------|---------|------|---------------------|
| **monitor_exporter** | 10.238.3.136 | 每 ~30s/实例 | ~175,000 |
| **diagtools** | 10.238.3.43, 10.238.10.251 | 每 ~30s/实例 | ~350,000 |

**修复方案**：将两个工具中的 `SHOW SLAVE STATUS` 替换为 `SHOW REPLICA STATUS`。
- `SHOW REPLICA STATUS` 自 MySQL 8.0.22 起可用，当前 8.0.40+ 环境完全兼容
- **可以立即部署**，无需等待 8.4 升级

> 同时发现 ldas-rw 上有 `SHOW SLAVE HOSTS`（2 次），需改为 `SHOW REPLICAS`。

### 4.3 HIGH — `information_schema.PROCESSLIST` 已移除（Issue #2）

**MySQL 8.4 已移除此视图**，必须使用 `performance_schema.processlist` 替代。

**调用来源**：`diagtools`（与 Issue #1 同一工具），两种查询模式：

```sql
-- 模式1: 简单进程列表（每 ~30s）
-- 修复: information_schema.PROCESSLIST → performance_schema.processlist
SELECT id AS pid, ... FROM performance_schema.processlist
WHERE command NOT IN ('Sleep', 'Binlog Dump GTID', ...);

-- 模式2: 事务监控 JOIN（每 ~30s）
-- 修复: information_schema.PROCESSLIST → performance_schema.processlist
SELECT d.trx_id, ...
FROM performance_schema.events_statements_current a
JOIN performance_schema.threads b ON a.thread_id = b.thread_id
JOIN performance_schema.processlist c ON b.processlist_id = c.id  -- 此处替换
JOIN information_schema.innodb_trx d ON c.id = d.trx_mysql_thread_id;
```

- `performance_schema.processlist` 自 MySQL 5.7.22 起可用，**可以立即部署**
- 前提：`performance_schema = ON`（我们的参数组已开启 ✅）

### 4.4 CRITICAL — `mysql_native_password` 已废弃（Issue #3）

**MySQL 8.4 中 `mysql_native_password` 已废弃**（RDS 8.4 通过 `mysql_native_password=ON` 参数仍可加载，但未来版本将彻底移除）。

**当前状态**：全部 61 实例 100% 的用户使用 `mysql_native_password`，共 90+ 账户。

**每实例典型账户（11 个基础设施账户 + 应用账户）**：

| 用户 | Host | 用途 |
|------|------|------|
| admin | % | RDS master 用户 |
| monitor_exporter | 10.% | Prometheus exporter |
| datalink_canal | 10.% | Canal binlog 同步 |
| datalink_dep | 10.% | 数据复制 |
| dbms_accountnew | 10.% | DBMS 账户管理 |
| dbms_dbsearch | 10.% | DBMS 搜索 |
| dbms_deploy | 10.% | DBMS 部署 |
| cactistats | 10.% | 监控 (Cacti) |
| diagtools | 10.% | 诊断工具 |
| xiangyu.zeng | 10.% | DBA 账户 |
| *_A_w / *_A_o | 10.% | 应用读写账户（每实例不同） |

**Phase 2 升级策略**：
1. 在 8.4 参数组中设置 `mysql_native_password=ON`（保持兼容，确保升级不中断）
2. 升级到 8.4 后，逐步迁移用户到 `caching_sha2_password`
3. 迁移前需确认所有 JDBC/连接器版本支持 sha2 认证

```sql
-- 迁移命令（升级 8.4 后逐步执行）：
ALTER USER 'username'@'host' IDENTIFIED WITH caching_sha2_password BY '<password>';
```

### 4.5 MEDIUM — `utf8mb3` 字符集表（Issue #4）

MySQL 8.4 中 `utf8mb3` 已废弃（仍可用，但会产生 warning）。

**受影响实例**（初始审计 3 个 + 扩展审计新增 1 个）：

| 实例 | Schema | 表/列数 | 来源 |
|------|--------|---------|------|
| framework01-rw | luckyus_gaea, luckyus_nacos, luckyus_sddl_platform, luckyus_zkdoctor | 69 表 | 中国 HQ 部署的中间件 |
| devops-rw | luckyus_uam | 6 表 | 用户访问管理 |
| icyberdata-rw | luckyus_icyberdata_nacos, luckyus_icyberdata | 79 列 | 数据分析 + Nacos |
| **mfranchise-rw** | luckyus_mfranchise | **769 列** | 加盟管理（扩展审计新发现） |

**其他已检查无 utf8mb3 的实例**: salesorder, salesmarketing, salespayment, isalescdp, ldas, scmcommodity, opshop, ijumpserver, iadmin, ibizconfigcenter, iotplatform, iworkflowmidlayer 等 55 个实例

**修复方案**（Phase 2 前或后均可，建议 Phase 2 前完成）：
```sql
ALTER TABLE {schema}.{table}
  CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

**风险**：索引大小增加 ~33%（3 字节→4 字节/字符），需检查是否有列达到最大索引长度限制。

### 4.6 MEDIUM — `SHOW MASTER STATUS` 已移除（Issue #5）

**MySQL 8.4 已移除此命令**，需使用 `SHOW BINARY LOG STATUS` 替代。

| 工具 | 来源 | 频率 | 每实例调用量 |
|------|------|------|------------|
| **cactistats** | 10.238.x.x | 定期 | 3~9,635 次/实例 |

修复方式与 Issue #1 类似，`SHOW BINARY LOG STATUS` 在 8.0.22+ 即可用。

### 4.8 审计结果：无问题项（Clean）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| `SQL_CALC_FOUND_ROWS` / `FOUND_ROWS()` | 0 出现 | 安全 |
| `FLUSH HOSTS` | 0 出现 | 安全 |
| `CHANGE MASTER TO` / `RESET SLAVE` | 0 出现 | 安全 |
| `START SLAVE` / `STOP SLAVE` | 0 出现 | 安全 |
| `GROUP BY col ASC/DESC`（真正的 GROUP BY 修饰符） | 0 出现（初始审计误报已排除） | 安全 |
| 存储过程/函数/触发器/事件中的废弃语法 | 0 出现 | 安全 |
| 空间索引（8.0.41 不兼容变更） | 0 个 | 不受影响 |
| sql_mode 废弃值 | 无 | 当前值全部兼容 8.4 |
| GTID 模式 | 全部 ON | 理想状态 |
| 字符集 (server level) | 全部 utf8mb4 | 理想状态 |

### 4.9 实例风险评级

#### HIGH 风险（7 个实例）

| 实例 | 类型 | 用户数 | 风险因素 |
|------|------|--------|---------|
| salesmarketing-rw | db.t4g.xlarge | 25 | 最大数据库 (43.7 GB)，高流量 |
| salesorder-rw | db.t4g.medium | 27 | 核心订单处理，特殊参数组 |
| salescrm-rw | db.t4g.medium | 25 | 核心 CRM |
| salespayment-rw | db.t4g.medium | 23 | 支付处理 |
| isalescdp-rw | db.t4g.medium | 17 | CDP，已知内存问题 |
| isalesdatamarketing-rw | db.t4g.medium | 17 | 营销数据 |
| upush-rw | db.t4g.medium | 31 | 最多用户 (31)，推送通知 |

#### MEDIUM 风险（12 个实例）

| 实例 | 类型 | 用户数 | 风险因素 |
|------|------|--------|---------|
| framework01-rw | db.t4g.medium | 33 | 多遗留应用账户 + utf8mb3 表 |
| framework02-rw | db.t4g.medium | 31 | 多应用账户 |
| devops-rw | db.t4g.medium | 30 | 基础设施数据库 + utf8mb3 表 |
| icyberdata-rw | db.t4g.medium | 25 | 最大存储 (635 GB) + utf8mb3 列 |
| ldas-rw | db.t4g.large | 26 | 分析平台 |
| ldas01-rw | db.t4g.large | N/A | 审计时访问受限 |
| iluckyams-rw | db.t4g.micro | 15 | 已知内存压力 |
| iluckyhealth-rw | db.t3.small | 13 | 健康监控 |
| cdpactivity-rw | db.t4g.medium | 19 | CDP 活动 |
| iotplatform-rw | db.t4g.medium | 19 | IoT 平台 |
| scm-shopstock-rw | db.t4g.medium | 17 | SCM 库存 |
| scmcommodity-rw | db.t4g.medium | 17 | SCM 商品 |

#### LOW 风险（42 个实例）

全部 db.t4g.micro，20 GB 存储，13-17 个用户。标准升级流程。

---

## 五、Phase 1 — 小版本升级 (8.0.x → 8.0.45)

> Phase 1 为小版本升级，无兼容性变更，上述兼容性问题均不影响 Phase 1。
> 但注意 db.t4g.micro 实例内存压力（~100-150MB 可用），升级应安排在低流量窗口，避开 05:00 UTC 批处理。

### 4.1 升级批次

#### Batch 0 — 测试验证（第 1 周）

| 实例 | 当前版本 | 类型 | 存储 | 维护窗口(UTC) |
|------|---------|------|------|--------------|
| aws-luckyus-dbatest-rw | 8.0.42 | db.t4g.micro | 20GB | Thu 06:38-07:08 |

**目标**: 验证 8.0.45 小版本升级流程，确认应用兼容性。

**操作命令**:
```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-dbatest-rw \
  --engine-version 8.0.45 \
  --apply-immediately \
  --region us-east-1
```

**验证清单**:
- [ ] 实例状态恢复为 `available`
- [ ] `SELECT VERSION()` 返回 8.0.45
- [ ] 连接数正常
- [ ] 应用基本功能测试通过
- [ ] slow_query_log 正常工作
- [ ] Prometheus exporter 正常采集

---

#### Batch 1 — 低风险运维工具（第 2 周）

| # | 实例 | 当前版本 | 类型 | 存储 | 维护窗口(UTC) |
|---|------|---------|------|------|--------------|
| 1 | aws-luckyus-ijumpserver-jumpserver-rw | 8.0.40 | db.t4g.micro | 20GB | Mon 03:18-03:48 |
| 2 | aws-luckyus-iluckydorisops-rw | 8.0.40 | db.t4g.micro | 20GB | Sun 06:52-07:22 |
| 3 | aws-luckyus-ilsopdevopsdata-rw | 8.0.40 | db.t4g.micro | 20GB | Sun 08:53-09:23 |
| 4 | aws-luckyus-oplog-rw | 8.0.40 | db.t4g.micro | 20GB | Thu 03:04-03:34 |
| 5 | aws-luckyus-iluckyams-rw | 8.0.44 | db.t4g.micro | 20GB | Tue 05:29-05:59 |
| 6 | aws-luckyus-devops-rw | 8.0.40 | db.t4g.medium | 20GB | Wed 08:06-08:36 |
| 7 | aws-luckyus-pubdm-rw | 8.0.40 | db.t4g.micro | 20GB | Fri 06:34-07:04 |

**说明**: 运维工具、日志、监控类实例，影响范围小。

---

#### Batch 2 — 内部管理系统（第 2-3 周）

| # | 实例 | 当前版本 | 类型 | 存储 |
|---|------|---------|------|------|
| 1 | aws-luckyus-iehr-rw | 8.0.40 | db.t4g.micro | 20GB |
| 2 | aws-luckyus-igers-rw | 8.0.40 | db.t4g.micro | 20GB |
| 3 | aws-luckyus-mfranchise-rw | 8.0.40 | db.t4g.micro | 20GB |
| 4 | aws-luckyus-iadmin-rw | 8.0.40 | db.t4g.micro | 20GB |
| 5 | aws-luckyus-ipermission-rw | 8.0.40 | db.t4g.micro | 20GB |
| 6 | aws-luckyus-iluckyauthapi-rw | 8.0.40 | db.t4g.micro | 20GB |
| 7 | aws-luckyus-iopenadmin-rw | 8.0.40 | db.t4g.micro | 20GB |
| 8 | aws-luckyus-iopenlinker-rw | 8.0.40 | db.t4g.micro | 20GB |
| 9 | aws-luckyus-iopenservice-rw | 8.0.40 | db.t4g.micro | 20GB |
| 10 | aws-luckyus-ibizconfigcenter-rw | 8.0.40 | db.t4g.micro | 20GB |
| 11 | aws-luckyus-iluckyhealth-rw | 8.0.40 | db.t3.small | 50GB |
| 12 | aws-luckyus-iluckymedia-rw | 8.0.40 | db.t4g.micro | 20GB |
| 13 | aws-luckyus-iriskcontrolservice-rw | 8.0.40 | db.t4g.micro | 40GB |
| 14 | aws-luckyus-iworkflowmidlayer-rw | 8.0.40 | db.t4g.medium | 20GB |
| 15 | aws-luckyus-upush-rw | 8.0.40 | db.t4g.medium | 40GB |
| 16 | aws-luckyus-iotplatform-rw | 8.0.40 | db.t4g.medium | 20GB |

**说明**: 认证、权限、HR、媒体、推送等内部平台服务。

---

#### Batch 3 — 运营/门店系统（第 3 周）

| # | 实例 | 当前版本 | 类型 | 存储 |
|---|------|---------|------|------|
| 1 | aws-luckyus-opempefficiency-rw | 8.0.40 | db.t4g.micro | 20GB |
| 2 | aws-luckyus-opproduction-rw | 8.0.40 | db.t4g.micro | 20GB |
| 3 | aws-luckyus-opqualitycontrol-rw | 8.0.40 | db.t4g.micro | 20GB |
| 4 | aws-luckyus-opshop-rw | 8.0.40 | db.t4g.medium | 20GB |
| 5 | aws-luckyus-opshopsale-rw | 8.0.40 | db.t4g.micro | 20GB |
| 6 | aws-luckyus-iopshopexpand-rw | 8.0.40 | db.t4g.micro | 20GB |
| 7 | aws-luckyus-iopocp-rw | 8.0.40 | db.t4g.micro | 20GB |

**说明**: 门店运营、品控、排产等业务系统。

---

#### Batch 4 — 供应链系统（第 3-4 周）

| # | 实例 | 当前版本 | 类型 | 存储 |
|---|------|---------|------|------|
| 1 | aws-luckyus-scm-asset-rw | 8.0.40 | db.t4g.micro | 20GB |
| 2 | aws-luckyus-scm-openapi-rw | 8.0.40 | db.t4g.micro | 20GB |
| 3 | aws-luckyus-scm-ordering-rw | 8.0.40 | db.t4g.micro | 20GB |
| 4 | aws-luckyus-scm-plan-rw | 8.0.40 | db.t4g.micro | 20GB |
| 5 | aws-luckyus-scm-purchase-rw | 8.0.40 | db.t4g.micro | 20GB |
| 6 | aws-luckyus-scm-shopstock-rw | 8.0.40 | db.t4g.medium | 30GB |
| 7 | aws-luckyus-scm-wds-rw | 8.0.40 | db.t4g.micro | 20GB |
| 8 | aws-luckyus-scm-wmssimulate-rw | 8.0.40 | db.t4g.micro | 20GB |
| 9 | aws-luckyus-scmcommodity-rw | 8.0.40 | db.t4g.medium | 20GB |
| 10 | aws-luckyus-scmsrm-rw | 8.0.40 | db.t4g.micro | 20GB |
| 11 | aws-luckyus-ireplenishment-rw | 8.0.40 | db.t4g.micro | 20GB |

**说明**: 供应链全链路，建议同一批次升级以保持版本一致。

---

#### Batch 5 — 财务系统（第 4 周）

| # | 实例 | 当前版本 | 类型 | 存储 |
|---|------|---------|------|------|
| 1 | aws-luckyus-fichargecontrol-rw | 8.0.40 | db.t4g.micro | 20GB |
| 2 | aws-luckyus-fitax-rw | 8.0.40 | db.t4g.micro | 20GB |
| 3 | aws-luckyus-ifiaccounting-rw | 8.0.40 | db.t4g.micro | 20GB |
| 4 | aws-luckyus-ibillingcentersrv-rw | 8.0.40 | db.t4g.micro | 20GB |
| 5 | aws-luckyus-iunifiedreconcile-rw | 8.0.40 | db.t4g.micro | 20GB |

**说明**: 财务系统对数据一致性要求高，安排在前批次验证后执行。

---

#### Batch 6 — 销售/CRM 核心（第 4-5 周）

| # | 实例 | 当前版本 | 类型 | 存储 |
|---|------|---------|------|------|
| 1 | aws-luckyus-cdpactivity-rw | 8.0.40 | db.t4g.medium | 40GB |
| 2 | aws-luckyus-isalescdp-rw | 8.0.40 | db.t4g.medium | 40GB |
| 3 | aws-luckyus-isalesdatamarketing-rw | 8.0.40 | db.t4g.medium | 40GB |
| 4 | aws-luckyus-isalesmembermarketing-rw | 8.0.40 | db.t4g.micro | 20GB |
| 5 | aws-luckyus-isalesprivatedomain-rw | 8.0.40 | db.t4g.medium | 20GB |
| 6 | aws-luckyus-salescrm-rw | 8.0.40 | db.t4g.medium | 20GB |
| 7 | aws-luckyus-salespayment-rw | 8.0.40 | db.t4g.medium | 20GB |
| 8 | aws-luckyus-salesorder-rw | 8.0.40 | db.t4g.medium | 20GB |
| 9 | aws-luckyus-salesmarketing-rw | 8.0.40 | db.t4g.xlarge | 100GB |

**说明**: 销售核心系统，包含最大实例 salesmarketing (xlarge, 100GB)。salesorder 使用特殊参数组。

---

#### Batch 7 — 数据平台/框架（第 5 周）

| # | 实例 | 当前版本 | 类型 | 存储 |
|---|------|---------|------|------|
| 1 | aws-luckyus-framework01-rw | 8.0.40 | db.t4g.medium | 20GB |
| 2 | aws-luckyus-framework02-rw | 8.0.40 | db.t4g.medium | 40GB |
| 3 | aws-luckyus-ldas-rw | 8.0.40 | db.t4g.large | 30GB |
| 4 | aws-luckyus-ldas01-rw | 8.0.41 | db.t4g.large | 128GB |
| 5 | aws-luckyus-icyberdata-rw | 8.0.40 | db.t4g.medium | 635GB |

**说明**: 数据平台核心，包含最大存储实例 icyberdata (635GB)。安排在最后以获得最大验证覆盖。

---

### 4.2 Phase 1 每批次操作 SOP

```bash
# ===== PRE-UPGRADE =====

# 1. 创建手动快照（安全网）
aws rds create-db-snapshot \
  --db-instance-identifier {INSTANCE} \
  --db-snapshot-identifier {INSTANCE}-pre-8045-$(date +%Y%m%d) \
  --region us-east-1

# 2. 确认快照完成
aws rds wait db-snapshot-available \
  --db-snapshot-identifier {INSTANCE}-pre-8045-$(date +%Y%m%d) \
  --region us-east-1

# ===== UPGRADE =====

# 3. 执行小版本升级（立即执行）
aws rds modify-db-instance \
  --db-instance-identifier {INSTANCE} \
  --engine-version 8.0.45 \
  --apply-immediately \
  --region us-east-1

# 4. 等待升级完成
aws rds wait db-instance-available \
  --db-instance-identifier {INSTANCE} \
  --region us-east-1

# ===== POST-UPGRADE =====

# 5. 确认版本
aws rds describe-db-instances \
  --db-instance-identifier {INSTANCE} \
  --query 'DBInstances[0].[EngineVersion,DBInstanceStatus]' \
  --region us-east-1

# 6. 检查 RDS 事件（是否有异常）
aws rds describe-events \
  --source-identifier {INSTANCE} \
  --source-type db-instance \
  --duration 60 \
  --region us-east-1
```

### 4.3 Phase 1 验证清单

每批次完成后检查：

- [ ] 所有实例 `EngineVersion` = 8.0.45，`Status` = available
- [ ] 应用连接正常，无报错
- [ ] Prometheus RDS exporter 正常采集
- [ ] Grafana 仪表板数据连续
- [ ] CloudWatch 指标无异常（CPU、连接数、慢查询）
- [ ] 观察 24 小时，确认批处理任务（05:00 UTC）正常

---

## 六、Phase 1 与 Phase 2 之间 — 兼容性修复与准备工作

在所有实例升级到 8.0.45 后、Phase 2 开始前，**必须**完成以下修复和准备工作。

### 6.1 【必须】修复废弃 SQL（可与 Phase 1 并行）

> 这些修复使用的替代语法在 8.0.22+ 上即可工作，**建议立即开始**，不必等到 Phase 1 完成。

#### 6.1.1 更新 monitor_exporter — `SHOW SLAVE STATUS` → `SHOW REPLICA STATUS`

| 项目 | 详情 |
|------|------|
| 工具 | Prometheus MySQL exporter (`monitor_exporter`) |
| 部署位置 | 10.238.3.136 (EKS Pod) |
| 当前 SQL | `SHOW SLAVE STATUS` |
| 替换为 | `SHOW REPLICA STATUS` |
| 影响量 | ~175,000 次/天（全部 61 实例） |

#### 6.1.2 更新 diagtools — `SHOW SLAVE STATUS` + `information_schema.PROCESSLIST`

| 项目 | 详情 |
|------|------|
| 工具 | DBA 诊断工具 (`diagtools`) |
| 部署位置 | 10.238.3.43, 10.238.10.251 |
| 修复 1 | `SHOW SLAVE STATUS` → `SHOW REPLICA STATUS` |
| 修复 2 | `information_schema.PROCESSLIST` → `performance_schema.processlist` |
| 影响量 | ~525,000 次/天（全部 61 实例） |

#### 6.1.3 更新 cactistats — `SHOW MASTER STATUS` → `SHOW BINARY LOG STATUS`

| 项目 | 详情 |
|------|------|
| 工具 | Cacti 监控 (`cactistats`) |
| 当前 SQL | `SHOW MASTER STATUS` |
| 替换为 | `SHOW BINARY LOG STATUS` |
| 影响量 | ~15,000 次/天（全部 61 实例） |

**修复这 3 个工具即可消除 100% 的废弃 SQL 调用量。**

#### 6.1.4 修复验证

```sql
-- 在任意实例上确认无残留废弃 SQL（升级前跑一次）：
SELECT DIGEST_TEXT, COUNT_STAR, LAST_SEEN
FROM performance_schema.events_statements_summary_by_digest
WHERE DIGEST_TEXT LIKE '%SLAVE%'
   OR DIGEST_TEXT LIKE '%MASTER STATUS%'
   OR DIGEST_TEXT LIKE '%information_schema%PROCESSLIST%'
ORDER BY LAST_SEEN DESC;
-- 期望：COUNT_STAR 不再增长，或查询结果为空
```

### 6.2 【必须】创建 MySQL 8.4 参数组

```bash
# 主参数组（对应 luckyus-prod-80-new，58 个实例使用）
aws rds create-db-parameter-group \
  --db-parameter-group-name luckyus-prod-84 \
  --db-parameter-group-family mysql8.4 \
  --description "Luckin US Production MySQL 8.4" \
  --region us-east-1

# 基础设施参数组（对应 luckyus-prod，devops-rw + ldas-rw 使用）
aws rds create-db-parameter-group \
  --db-parameter-group-name luckyus-prod-84-infra \
  --db-parameter-group-family mysql8.4 \
  --description "Luckin US Infrastructure MySQL 8.4" \
  --region us-east-1

# salesorder 专用参数组（对应 luckyus-prod-80-new-groupconcatmaxlen）
aws rds create-db-parameter-group \
  --db-parameter-group-name luckyus-prod-84-groupconcatmaxlen \
  --db-parameter-group-family mysql8.4 \
  --description "Luckin US MySQL 8.4 with group_concat_max_len" \
  --region us-east-1
```

#### 配置参数（以 luckyus-prod-84 为例）

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

> **关键**：`mysql_native_password=ON` 确保 8.4 升级后所有现有用户仍可认证。全部迁移到 `caching_sha2_password` 后再设为 OFF。

#### 参数名变更映射（RDS 自动处理，仅需知晓）

| 8.0 参数名 | 8.4 参数名 | 说明 |
|-----------|-----------|------|
| `default_authentication_plugin` | `authentication_policy` | 已重命名，不要在 8.4 参数组中设置旧名 |
| `log_slave_updates` | `log_replica_updates` | 自动映射 |
| `slave_*` | `replica_*` | 自动映射 |
| `binlog_format` | `binlog_format` | 8.4 中已废弃但可设置，ROW 为唯一推荐值 |
| `innodb_undo_tablespaces` | — | 8.4 中已废弃，不要在 8.4 参数组中设置 |

### 6.3 【建议】修复 utf8mb3 表

在 Phase 2 前将 3 个实例上的 utf8mb3 表转换为 utf8mb4：

| 实例 | Schema | 表/列数 |
|------|--------|---------|
| framework01-rw | gaea, nacos, sddl_platform, zkdoctor | 69 表 |
| devops-rw | luckyus_uam | 6 表 |
| icyberdata-rw | icyberdata_nacos, icyberdata | 79 列 |
| mfranchise-rw | luckyus_mfranchise | 769 列 |

```sql
-- 逐表执行（维护窗口内）：
ALTER TABLE {schema}.{table}
  CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

> 风险：索引大小增加 ~33%，需检查是否有列达到最大索引长度限制。

### 6.4 验证 optimizer_switch

```bash
aws rds describe-db-parameters \
  --db-parameter-group-name default.mysql8.4 \
  --query "Parameters[?ParameterName=='optimizer_switch'].ParameterValue" \
  --region us-east-1
```

### 6.5 兼容性预检（在 dbatest 上）

```bash
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-dbatest-rw \
  --engine-version 8.4.8 \
  --db-parameter-group-name luckyus-prod-84 \
  --allow-major-version-upgrade \
  --apply-immediately \
  --region us-east-1
```

**重点验证**:
- [ ] precheck 通过（无不兼容项）
- [ ] `PrePatchCompatibility.log` 无错误
- [ ] 升级完成，版本 = 8.4.8
- [ ] monitor_exporter 正常（`SHOW REPLICA STATUS`）
- [ ] diagtools 正常（`performance_schema.processlist`）
- [ ] utf8mb3 相关 warning 检查
- [ ] 保留字冲突检查
- [ ] 应用端全功能回归测试

### 6.6 Phase 2 Go/No-Go 检查清单

| # | 检查项 | 状态 |
|---|--------|------|
| 1 | Phase 1 全部 61 实例已升级到 8.0.45 | [ ] |
| 2 | monitor_exporter 已切换到 `SHOW REPLICA STATUS` | [ ] |
| 3 | diagtools 已切换到 `SHOW REPLICA STATUS` + `performance_schema.processlist` | [ ] |
| 4 | MySQL 8.4 参数组已创建并配置（含 `mysql_native_password=ON`） | [ ] |
| 5 | dbatest-rw 已成功升级到 8.4.8 并稳定运行 72h | [ ] |
| 6 | utf8mb3 表已转换（或确认接受 warning） | [ ] |
| 7 | 应用团队确认 8.4 兼容性测试通过 | [ ] |
| 8 | 运维团队已通知升级计划 | [ ] |
| 9 | 无活跃生产事故 / 无促销活动冲突 | [ ] |

---

## 七、Phase 2 — 大版本升级 (8.0.45 → 8.4.8)

### 7.1 前提条件

见第六节 6.6 Go/No-Go 检查清单（全部 9 项必须通过）。

### 7.2 升级批次

与 Phase 1 相同的批次划分（Batch 0-7），但每批次间隔拉长到 **3-5 天**观察期。

### 7.3 Phase 2 每批次操作 SOP

```bash
# ===== PRE-UPGRADE =====

# 1. 创建手动快照
aws rds create-db-snapshot \
  --db-instance-identifier {INSTANCE} \
  --db-snapshot-identifier {INSTANCE}-pre-848-$(date +%Y%m%d) \
  --region us-east-1

# 2. 等待快照完成
aws rds wait db-snapshot-available \
  --db-snapshot-identifier {INSTANCE}-pre-848-$(date +%Y%m%d) \
  --region us-east-1

# ===== UPGRADE =====

# 3. 执行大版本升级（指定新参数组）
aws rds modify-db-instance \
  --db-instance-identifier {INSTANCE} \
  --engine-version 8.4.8 \
  --db-parameter-group-name luckyus-prod-84 \
  --allow-major-version-upgrade \
  --apply-immediately \
  --region us-east-1

# 4. 等待升级完成（大版本升级时间较长，设置较长超时）
aws rds wait db-instance-available \
  --db-instance-identifier {INSTANCE} \
  --region us-east-1

# ===== POST-UPGRADE =====

# 5. 确认版本和参数组
aws rds describe-db-instances \
  --db-instance-identifier {INSTANCE} \
  --query 'DBInstances[0].[EngineVersion,DBInstanceStatus,DBParameterGroups[0].DBParameterGroupName]' \
  --region us-east-1

# 6. 检查 PrePatchCompatibility.log
aws rds download-db-log-file-portion \
  --db-instance-identifier {INSTANCE} \
  --log-file-name PrePatchCompatibility.log \
  --region us-east-1

# 7. 检查事件
aws rds describe-events \
  --source-identifier {INSTANCE} \
  --source-type db-instance \
  --duration 120 \
  --region us-east-1
```

### 7.4 Phase 2 特别注意

- **slow_log 和 general_log 会被清空**: 升级前备份慢查询日志
- **mysql_upgrade 自动运行**: RDS 会自动执行，无需手动操作
- **升级失败自动回滚**: 如果 precheck 或升级失败，自动回退到 8.0.45
- **salesorder-rw**: 使用 `luckyus-prod-84-groupconcatmaxlen` 参数组

---

## 八、时间线总览

```
Week 1  (04/07 - 04/13)  Phase 1 Batch 0: dbatest (验证)
Week 2  (04/14 - 04/20)  Phase 1 Batch 1-2: 运维工具 + 内部系统 (23个)
Week 3  (04/21 - 04/27)  Phase 1 Batch 3-4: 运营 + 供应链 (18个)
Week 4  (04/28 - 05/04)  Phase 1 Batch 5-6: 财务 + 销售核心 (14个)
Week 5  (05/05 - 05/11)  Phase 1 Batch 7: 数据平台 (5个) ← Phase 1 完成
                          准备 8.4 参数组，dbatest 验证 8.4.8
Week 6  (05/12 - 05/18)  Phase 2 Batch 0-1: dbatest + 运维工具
Week 7  (05/19 - 05/25)  Phase 2 Batch 2-3: 内部系统 + 运营  ← 8.0.40 到期前
Week 8  (05/26 - 06/01)  Phase 2 Batch 4-5: 供应链 + 财务
Week 9  (06/02 - 06/08)  Phase 2 Batch 6: 销售核心
Week 10 (06/09 - 06/15)  Phase 2 Batch 7: 数据平台 ← 全部完成
                                                      (7/31 大版本到期前 6 周)
```

**关键里程碑**:
- **05/11**: Phase 1 完成 — 全部 61 实例升级到 8.0.45
- **05/31**: 8.0.40/41 标准支持到期（已无影响，因为已升级到 8.0.45）
- **06/15**: Phase 2 完成 — 全部 61 实例升级到 8.4.8
- **07/31**: 8.0 大版本标准支持到期（已无影响，因为已升级到 8.4.8）

---

## 九、回滚方案

### Phase 1 回滚（小版本）
小版本升级无法直接回滚。如需回退：
1. 使用升级前创建的手动快照恢复新实例
2. 切换应用到新实例
3. 删除旧实例

### Phase 2 回滚（大版本）
- **precheck 失败**: 自动取消，无停机，无需回滚
- **升级过程中失败**: RDS 自动回滚到 8.0.45
- **升级后应用不兼容**: 使用升级前快照恢复

---

## 十、风险与缓解

| # | 风险 | 概率 | 影响 | 缓解措施 |
|---|------|------|------|---------|
| R1 | 小版本升级导致性能回退 | 低 | 低 | 8.0.45 仅为 bug fix + 安全补丁；iluckyams-rw 已在 8.0.44 上稳定运行 |
| R2 | db.t4g.micro 升级时 OOM | 中 | 中 | 40 个实例仅 ~100-150MB 可用内存；升级安排在低流量窗口，避开 05:00 UTC 批处理 |
| R3 | 大版本 precheck 失败 | 中 | 无 | 自动取消，无停机；根据 `PrePatchCompatibility.log` 修复后重试 |
| R4 | `SHOW SLAVE STATUS` 在 8.4 上报错 | 高 | 高 | **必须在 Phase 2 前修复** monitor_exporter 和 diagtools（见 6.1 节） |
| R5 | `information_schema.PROCESSLIST` 在 8.4 上报错 | 高 | 高 | **必须在 Phase 2 前修复** diagtools（见 6.1 节） |
| R6 | mysql_native_password 认证失败 | 低 | 高 | 8.4 参数组设置 `mysql_native_password=ON` 保持兼容；升级后再逐步迁移认证方式 |
| R7 | JDBC/连接器不兼容 caching_sha2_password | 低 | 高 | Phase 2 期间保持 `mysql_native_password=ON`；认证迁移作为独立项目 |
| R8 | utf8mb3 表在 8.4 上产生 warning | 低 | 低 | 功能不受影响；建议升级前转换（见 6.3 节） |
| R9 | salesmarketing-rw (43.7GB) 升级时间长 | 高 | 低 | 预留 2-4 小时窗口；安排在周末执行 |
| R10 | Canal binlog 同步 (datalink_canal) 中断 | 中 | 中 | dbatest 上先验证 Canal 重连；升级前确认 Canal 连接器版本 |
| R11 | 批量升级一天内发现多个问题 | 低 | 高 | 每批次留 24h+ 观察期；Phase 2 批次间隔 3-5 天 |

---

## 十一、升级完成后工作

### 11.1 认证迁移（Phase 3 — 升级 8.4 完成后）

全部 61 实例 90+ 用户从 `mysql_native_password` 迁移到 `caching_sha2_password`：

1. 确认所有 JDBC/连接器版本支持 sha2：MySQL Connector/J 8.0.12+、PyMySQL 1.0+、Go mysql driver 1.4+
2. 确认 Canal binlog 连接器支持 sha2
3. 逐实例、逐用户迁移：
```sql
ALTER USER 'username'@'host' IDENTIFIED WITH caching_sha2_password BY '<password>';
```
4. 全部迁移完成后，将 8.4 参数组中 `mysql_native_password` 设为 `OFF`

### 11.2 清理

- [ ] 删除旧的 `luckyus-prod` (mysql8.0) 参数组（确认无实例引用后）
- [ ] 删除旧的 `luckyus-prod-80-new` (mysql8.0) 参数组
- [ ] 删除旧的 `luckyus-prod-80-new-groupconcatmaxlen` (mysql8.0) 参数组
- [ ] 清理升级前手动快照（保留 30 天后删除）
- [ ] 更新 Grafana 仪表板和告警中的版本相关配置
- [ ] 更新 CLAUDE.md 和基础设施文档

---

## 附录：相关调查报告

| 报告 | 日期 | 说明 |
|------|------|------|
| [compatibility_checklist.md](../../compatibility_checklist.md) | 2026-04-02 | MySQL 8.0→8.4 兼容性检查清单（CRITICAL/HIGH/MEDIUM/LOW 分级） |
| [mysql-8045-upgrade-compatibility-report.md](mysql-8045-upgrade-compatibility-report.md) | 2026-04-02 | MySQL 8.0.45 小版本升级兼容性报告 |
| [mysql-deprecated-sql-audit-20260402.md](mysql-deprecated-sql-audit-20260402.md) | 2026-04-02 | 废弃 SQL 审计报告（SHOW SLAVE STATUS、information_schema.PROCESSLIST 等） |
| [rds-extended-support-upgrade-brief-20260406.md](rds-extended-support-upgrade-brief-20260406.md) | 2026-04-06 | RDS Extended Support 与升级关系简要说明 |
