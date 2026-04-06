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

## 四、Phase 1 — 小版本升级 (8.0.x → 8.0.45)

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

## 五、Phase 1 与 Phase 2 之间 — 准备工作

在所有实例升级到 8.0.45 后，Phase 2（大版本升级到 8.4.8）之前需要完成：

### 5.1 创建 MySQL 8.4 参数组

```bash
# 主参数组
aws rds create-db-parameter-group \
  --db-parameter-group-name luckyus-prod-84 \
  --db-parameter-group-family mysql8.4 \
  --description "Luckin US production MySQL 8.4" \
  --region us-east-1

# salesorder 专用参数组
aws rds create-db-parameter-group \
  --db-parameter-group-name luckyus-prod-84-groupconcatmaxlen \
  --db-parameter-group-family mysql8.4 \
  --description "Luckin US production MySQL 8.4 - custom group_concat_max_len" \
  --region us-east-1
```

然后将 8.0 参数组的自定义参数逐一复制到 8.4 参数组（所有参数已验证兼容）。

### 5.2 验证 optimizer_switch

8.4 中 optimizer_switch 有新增/变更的选项，需要对比确认：

```bash
# 查看 8.4 默认 optimizer_switch
aws rds describe-db-parameters \
  --db-parameter-group-name default.mysql8.4 \
  --query "Parameters[?ParameterName=='optimizer_switch'].ParameterValue" \
  --region us-east-1
```

### 5.3 兼容性预检（在 dbatest 上）

在 dbatest-rw 上先执行 8.0.45 → 8.4.8 升级，检查 `PrePatchCompatibility.log`：

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
- [ ] 升级完成，版本 = 8.4.8
- [ ] utf8mb3 相关 warning 检查
- [ ] 保留字冲突检查
- [ ] sql_mode 兼容性
- [ ] 存储过程/触发器/视图正常
- [ ] 应用端全功能回归测试

---

## 六、Phase 2 — 大版本升级 (8.0.45 → 8.4.8)

### 6.1 前提条件

- [ ] Phase 1 全部 61 个实例已升级到 8.0.45
- [ ] dbatest-rw 已成功升级到 8.4.8 并验证
- [ ] MySQL 8.4 参数组已创建并配置
- [ ] 应用团队确认 8.4 兼容性测试通过
- [ ] 通知运维团队升级计划

### 6.2 升级批次

与 Phase 1 相同的批次划分（Batch 0-7），但每批次间隔拉长到 **3-5 天**观察期。

### 6.3 Phase 2 每批次操作 SOP

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

### 6.4 Phase 2 特别注意

- **slow_log 和 general_log 会被清空**: 升级前备份慢查询日志
- **mysql_upgrade 自动运行**: RDS 会自动执行，无需手动操作
- **升级失败自动回滚**: 如果 precheck 或升级失败，自动回退到 8.0.45
- **salesorder-rw**: 使用 `luckyus-prod-84-groupconcatmaxlen` 参数组

---

## 七、时间线总览

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

## 八、回滚方案

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

## 九、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 小版本升级导致性能回退 | 低 | 低 | 8.0.45 仅为 bug fix + 安全补丁 |
| 大版本 precheck 失败 | 中 | 无 | 自动取消，根据日志修复后重试 |
| 大版本升级后 SQL 不兼容 | 低 | 高 | dbatest 先行验证；每批次升级前快照 |
| 升级窗口时间不够 | 低 | 中 | 大实例（icyberdata 635GB）单独安排充裕窗口 |
| Multi-AZ failover 影响业务 | 低 | 低 | failover 通常 30s 以内；避开业务高峰 |
| 批量升级的一天内发现多个问题 | 低 | 高 | 每批次留 24h+ 观察期 |

---

## 十、升级完成后清理

- [ ] 删除旧的 `luckyus-prod` (mysql8.0) 参数组（确认无实例引用后）
- [ ] 删除旧的 `luckyus-prod-80-new` (mysql8.0) 参数组
- [ ] 删除旧的 `luckyus-prod-80-new-groupconcatmaxlen` (mysql8.0) 参数组
- [ ] 清理升级前手动快照（保留 30 天后删除）
- [ ] 更新 Grafana 仪表板和告警中的版本相关配置
- [ ] 更新 CLAUDE.md 和基础设施文档
