# MySQL 8.0 → 8.4 升级方案 — Luckin USA RDS

**日期**: 2026-04-10  
**编制**: David Zeng (DBA)  
**目标版本**: MySQL 8.4.8 (RDS 最新 LTS)  
**参数组**: `luckyus-prod-84-new` (mysql8.4 family)

---

## 一、现状总览

### 1.1 实例分布

| 当前版本 | 实例数 | 参数组 | 说明 |
|---------|--------|--------|------|
| 8.0.40 | 55 | `luckyus-prod-80-new` (53) / `luckyus-prod` (2) / `luckyus-prod-80-new-groupconcatmaxlen` (1) | 生产主力 |
| 8.0.41 | 1 | `luckyus-prod-80-new` | ldas01 |
| 8.0.42 | 1 | `luckyus-prod-80-new` | dbatest |
| 8.0.44 | 1 | `luckyus-prod-80-new` | iluckyams |
| **8.4.7** | **2** | `default.mysql8.4` | **已有测试实例** (dba84test, datalink-84test) |
| **合计** | **60** | | 需升级 58 个 8.0.x 实例 |

### 1.2 实例规格分布

| 规格 | 数量 | 典型实例 |
|------|------|---------|
| db.t4g.micro | 38 | 大部分业务库 |
| db.t4g.medium | 16 | salescrm, framework, iotplatform 等 |
| db.t4g.large | 2 | ldas, ldas01 (数据分析) |
| db.t4g.xlarge | 1 | salesmarketing (最大 46GB 数据) |
| db.t3.small | 1 | iluckyhealth |

### 1.3 关键发现

- **全部 Multi-AZ**: 所有 58 个实例均开启 Multi-AZ，升级时有 failover 保护
- **无 Read Replica**: 没有只读副本，简化升级流程
- **全部 InnoDB**: 无 MyISAM 表，兼容性好
- **无 Trigger/Routine/View**: salesmarketing 等核心库无存储过程、触发器、视图
- **AutoMinorVersionUpgrade**: 绝大多数为 False（手动控制），仅 iluckyams 和 2 个 8.4 测试实例为 True

### 1.4 为什么选择 8.4.8 而非 8.4.7？

AWS 控制台新建实例时默认版本为 8.4.7，但 **8.4.8 已可用**且是更优选择：

| 对比项 | 8.4.7 | 8.4.8 |
|--------|-------|-------|
| 社区发布日期 | 2025-10-21 | 2026-01-20 |
| RDS 上线日期 | 2025-11-13 | 2026-02-03 |
| 标准支持截止 | 2026-11-30 | 2027-02-03 |

8.4.8 相比 8.4.7 的主要变化：
- **安全补丁**: 包含 Oracle 2026 年 1 月关键补丁更新 (Critical Patch Update)
- **审计日志修复**: 修复了某些 SQL 语句未被审计日志记录的问题
- **时区数据更新**: 升级到 `tzdata2025c`
- 其他社区 bug 修复

> `8.0.40 → 8.4.8` 和 `8.0.40 → 8.4.7` 均为 AWS 支持的直接升级路径。选择 8.4.8 可获得最新安全补丁和更长的标准支持周期（多 2 个月）。

### 1.5 AWS RDS MySQL 版本生命周期

来源: `aws rds describe-db-major-engine-versions --engine mysql` (verified 2026-04-02)

| 大版本 | 标准支持截止 | Extended Support 开始 | Extended Support 费用 | Extended Support 截止 |
|--------|------------|----------------------|----------------------|----------------------|
| MySQL 5.7 | 2024-02-29 (已过期) | 2024-03-01 | $0.11/vCPU-hour | 2027-02-28 |
| **MySQL 8.0** | **2026-07-31** | **2026-08-01** | **$0.11/vCPU-hour** | **2029-07-31** |
| MySQL 8.4 LTS | 2029-07-31 | 2029-08-01 | $0.11/vCPU-hour | 2032-07-31 |

**两个并行的淘汰机制：**

1. **小版本 EOL (2026-05-31)**: AWS Health Event 仅针对 8.0.40/8.0.41。升级到 8.0.42+ 即可解除此强制升级威胁。

2. **大版本标准支持终止 (2026-07-31)**: 整个 MySQL 8.0 系列（含 8.0.45）失去标准支持。AWS 自动将所有 8.0.x 实例纳入 Extended Support，按 $0.11/vCPU-hour 收费。

| 日期 | 事件 | 停留 8.0.40 | 升到 8.0.45 | 升到 8.4.8 |
|------|------|------------|------------|------------|
| 2026-05-31 | 小版本 EOL | **被强制升级（停机！）** | 安全 | 安全 |
| 2026-08-01 | 8.0 进入 Extended Support | 额外收费 | 额外收费 | **免费** |
| 2029-07-31 | 8.0 Extended Support 终止 | 必须升到 8.4+ | 必须升到 8.4+ | 安全 |

### 1.6 两阶段升级策略

**Phase A（紧急 — 4 月底前完成）**: 将所有 55 个 8.0.40 + 1 个 8.0.41 实例升级到 **8.0.45**（最新小版本）。解除 5 月 31 日强制升级威胁。小版本升级简单：5-10 分钟停机，无兼容性变化。注意：8.0.45 仍属 MySQL 8.0，8 月 1 日起产生 Extended Support 费用。

**Phase B（必须 7 月 31 日前完成）**: 将全部实例从 8.0.45 升级到 **8.4.8 LTS**（蓝绿部署）。消除 Extended Support 费用，获得标准支持至 2029-07-31。大版本升级需谨慎测试 — 5-7 批次，4-6 周。

**为什么不跳过 Phase A 直接升 8.4？** 蓝绿部署 58 个实例需 4-6 周（含测试浸泡），时间紧张且风险集中。Phase A（小版本升级，每个 5-10 分钟，每晚可做 10-15 个）1 周内即可完成，先解除 5 月 31 日强制升级威胁，再从容推进 Phase B。

### 1.7 认证插件分布（抽样）

| 实例 | mysql_native_password | caching_sha2_password | auth_socket |
|------|----------------------|----------------------|-------------|
| dbatest | 11 | 3 | 1 |
| salesmarketing | 25 | 3 | 1 |
| framework01 | 33 | 3 | 1 |
| ldas | 26 | 3 | 1 |
| devops | 32 | 3 | 1 |

> **结论**: 绝大多数用户使用 `mysql_native_password`，`caching_sha2_password` 仅有系统内置的 3 个用户（rdsadmin 等）。  
> **必须在参数组中设置 `mysql_native_password=ON`**，否则升级后所有应用连接将失败。

---

## 二、MySQL 8.4 关键变化与影响分析

### 2.1 高风险变化

| 变化 | 影响 | 我们的应对 | 风险等级 |
|------|------|-----------|---------|
| **mysql_native_password 默认禁用** | 所有使用该插件的用户无法认证 → 应用全面中断 | 参数组中设置 `mysql_native_password=ON` | 🔴 **高** — 已处理 |
| **utf8mb3 charset deprecated** | 使用 utf8mb3 的表会产生 warning | framework01 有 66 张 utf8mb3 表（nacos/sddl_platform/gaea/zkdoctor），icyberdata 有 10 张 | 🟡 **中** — 功能不受影响，仅 warning |
| **GROUP BY 隐式排序完全移除** | 依赖 GROUP BY 排序的查询结果顺序可能变化 | 需排查应用 SQL，确认是否有依赖隐式排序 | 🟡 **中** |
| **optimizer_switch 新增选项** | 8.4 新增多个优化器开关，默认值可能不同 | 我们已显式设置 `prefer_ordering_index=off`，其余保持 8.4 默认 | 🟢 **低** |

### 2.2 中等风险变化

| 变化 | 影响 | 应对 |
|------|------|------|
| **binlog_format deprecated** | 8.4 仅支持 ROW，该参数已无实际作用 | 我们已经是 ROW，无影响 |
| **默认 collation 变为 utf8mb4_0900_ai_ci** | 新建表默认使用新 collation | 我们 `character_set_server=utf8mb4` 已显式设置，现有表不受影响 |
| **INFORMATION_SCHEMA 变更** | 部分系统表结构调整 | 监控脚本/exporter 需验证 |
| **Performance Schema 增强** | 新增 instrument，内存开销可能微增 | t4g.micro (1GB) 实例需关注内存 |

### 2.3 低风险/正面变化

| 变化 | 影响 |
|------|------|
| InnoDB 性能提升 | redo log 优化，高并发场景受益 |
| 连接管理改进 | 更好的线程池支持 |
| LTS 支持 | 8.4 是 LTS 版本，支持到 2032 年 |

---

## 三、需创建的参数组

### 3.1 主参数组: `luckyus-prod-84-new`

用于 58 个 8.0 实例中的 56 个（含当前使用 `luckyus-prod-80-new` 和 `luckyus-prod` 的）。

完整参数设置命令：

```bash
aws rds modify-db-parameter-group \
  --db-parameter-group-name luckyus-prod-84-new \
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

> 注: `mysql_native_password=ON` 确保迁移期间向后兼容。全部用户迁移到 `caching_sha2_password` 后再设为 OFF。

### 3.2 特殊参数组: `luckyus-prod-84-new-groupconcatmaxlen`

用于 `aws-luckyus-salesorder-rw`，在 `luckyus-prod-84-new` 基础上额外增加:

```
group_concat_max_len = 1048576
```

### 3.3 现有 8.4 测试实例处理

`aws-luckyus-dba84test-rw` 和 `aws-luckyus-datalink-84test-rw` 当前使用 `default.mysql8.4`，建议也切换到 `luckyus-prod-84-new` 以保持一致。

---

## 四、升级流程

### 4.1 升级路径验证

| 源版本 | 目标版本 | 是否支持直接升级 | 类型 |
|--------|---------|----------------|------|
| 8.0.40 | 8.4.8 | ✅ 支持 | Major Version Upgrade |
| 8.0.41 | 8.4.8 | ✅ 支持 | Major Version Upgrade |
| 8.0.42 | 8.4.8 | ✅ 支持 | Major Version Upgrade |
| 8.0.44 | 8.4.8 | ✅ 支持 | Major Version Upgrade |

> 所有 8.0.x 版本均可直接升级至 8.4.3 ~ 8.4.8 任意版本，无需中间跳板。

### 4.2 升级方式对比

| 方式 | 停机时间 | 回滚能力 | 适用场景 |
|------|---------|---------|---------|
| **Blue/Green 部署（首选）** | ~30 秒（switchover） | 切换前可零影响取消 | 所有生产实例 |
| In-Place 升级（备用） | 10-30 分钟 | 仅 snapshot 恢复 | Blue/Green 不可用时 |

### 4.3 Blue/Green 部署流程（首选方案）

#### T-48h: 升级前准备

```bash
INSTANCE="aws-luckyus-<service>-rw"

# 1. 创建手动快照
aws rds create-db-snapshot \
  --db-instance-identifier $INSTANCE \
  --db-snapshot-identifier ${INSTANCE}-pre-84-upgrade-$(date +%Y%m%d) \
  --region us-east-1

# 2. 确认无待处理的修改
aws rds describe-db-instances \
  --db-instance-identifier $INSTANCE \
  --region us-east-1 \
  --query 'DBInstances[0].PendingModifiedValues'

# 3. 记录基线指标 (7天 CPU)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=$INSTANCE \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average --region us-east-1

# 4. 兼容性检查 (via mcp-db-gateway)
# SELECT @@version, @@sql_mode, @@default_authentication_plugin;
# SELECT user, host, plugin FROM mysql.user WHERE plugin='mysql_native_password';
```

#### T-24h: 创建蓝绿部署

```bash
INSTANCE="aws-luckyus-<service>-rw"
INSTANCE_ARN="arn:aws:rds:us-east-1:257394478466:db:$INSTANCE"

aws rds create-blue-green-deployment \
  --blue-green-deployment-name "${INSTANCE}-84-upgrade" \
  --source "$INSTANCE_ARN" \
  --target-engine-version "8.4.8" \
  --target-db-parameter-group-name "luckyus-prod-84-new" \
  --region us-east-1
```

#### T-24h ~ T-0: 监控 Green 环境

```bash
# 检查蓝绿部署状态
aws rds describe-blue-green-deployments \
  --region us-east-1 \
  --query "BlueGreenDeployments[?BlueGreenDeploymentName=='${INSTANCE}-84-upgrade']"

# 确认 green 实例可用
# 确认复制延迟为 0
# 在 green endpoint 执行测试查询验证
```

#### T-0: 执行切换（维护窗口 02:00-06:00 UTC）

```bash
DEPLOYMENT_ID="<blue-green-deployment-id>"

aws rds switchover-blue-green-deployment \
  --blue-green-deployment-identifier "$DEPLOYMENT_ID" \
  --switchover-timeout 300 \
  --region us-east-1
```

> 预计停机: **~30 秒**（DNS 切换）

#### T+0 ~ T+1h: 切换后验证

```sql
-- Via mcp-db-gateway: 验证版本
SELECT @@version, @@hostname, @@default_authentication_plugin;

-- 验证用户认证
SELECT user, host, plugin FROM mysql.user LIMIT 50;

-- 检查错误计数
SHOW GLOBAL STATUS LIKE 'Aborted_%';

-- 验证关键参数
SHOW VARIABLES WHERE Variable_name IN (
  'innodb_buffer_pool_size', 'max_connections', 'sql_mode',
  'character_set_server', 'lower_case_table_names', 'gtid_mode'
);
```

```bash
# CloudWatch — 确认无异常
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=$INSTANCE \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average Maximum --region us-east-1
```

#### T+1h ~ T+72h: 浸泡观察期

- 通过 CloudWatch Logs Insights 监控 error log
- 与升级前基线对比各项指标
- 关注应用层错误（与 Ops 团队配合）
- 监控慢查询日志，是否出现新的慢查询模式

#### T+72h: 清理

```bash
# 删除蓝绿部署元数据（保留两个实例）
aws rds delete-blue-green-deployment \
  --blue-green-deployment-identifier "$DEPLOYMENT_ID" \
  --delete-target false \
  --region us-east-1

# 确认稳定后，可选删除旧 (blue) 实例
# aws rds delete-db-instance --db-instance-identifier "${INSTANCE}-old" --skip-final-snapshot --region us-east-1
```

### 4.4 In-Place 升级流程（备用方案）

当 Blue/Green 部署不可用时使用：

```bash
# 执行升级
aws rds modify-db-instance \
  --db-instance-identifier {INSTANCE} \
  --engine-version 8.4.8 \
  --db-parameter-group-name luckyus-prod-84-new \
  --allow-major-version-upgrade \
  --apply-immediately \
  --region us-east-1

# 预计停机: 10-30 分钟 (Multi-AZ failover)
#   - micro 实例: ~10-15 分钟
#   - large/xlarge: ~20-30 分钟 (数据量大)
```

### 4.5 回滚方案

#### 方案 A: Blue/Green 切换前（首选 — 零影响）

```bash
# 直接删除 green 部署，生产 (blue) 完全不受影响
aws rds delete-blue-green-deployment \
  --blue-green-deployment-identifier "$DEPLOYMENT_ID" \
  --delete-target true \
  --region us-east-1
```

#### 方案 B: Blue/Green 切换后 / In-Place 升级后（应急 — 15-30 分钟停机）

```bash
# 1. 从升级前快照恢复
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier ${INSTANCE}-restored \
  --db-snapshot-identifier ${INSTANCE}-pre-84-upgrade-$(date +%Y%m%d) \
  --db-instance-class <ORIGINAL_CLASS> \
  --region us-east-1

# 2. 等待实例可用
aws rds wait db-instance-available \
  --db-instance-identifier ${INSTANCE}-restored \
  --region us-east-1

# 3. 协调 Ops 团队切换应用连接到恢复实例

# 4. 重命名实例恢复原名
aws rds modify-db-instance \
  --db-instance-identifier $INSTANCE \
  --new-db-instance-identifier ${INSTANCE}-bad-upgrade \
  --apply-immediately --region us-east-1

aws rds modify-db-instance \
  --db-instance-identifier ${INSTANCE}-restored \
  --new-db-instance-identifier $INSTANCE \
  --apply-immediately --region us-east-1
```

> **重要**: MySQL major version 升级是**不可逆**的。唯一回滚方式是从升级前的 snapshot 恢复新实例，然后切换 endpoint。

---

## 五、Go/No-Go 检查清单

### Go 条件（全部满足方可执行）
- [ ] MySQL 8.4 参数组已创建并在测试实例验证
- [ ] 维护窗口已调整到 02:00-06:00 UTC
- [ ] 目标实例的手动快照已创建
- [ ] 无活跃生产事故或高优先级告警
- [ ] Ops 团队已通知并在升级窗口内待命
- [ ] 应用负责人已确认知晓
- [ ] Batch 0（测试实例）已成功完成并经过 72 小时浸泡

### No-Go 条件（任一触发则推迟）
- 存在活跃生产事故
- RDS 预检查失败（升级自动取消）
- 应用团队无法参与验证
- 异常流量模式（营销活动、促销）
- 与每日批处理窗口重叠 (05:00 UTC)

---

## 六、分批升级策略

### 6.1 推荐分批顺序

| 批次 | 时间 | 实例 | 理由 |
|------|------|------|------|
| **Batch 0: 测试验证** | Week 1 | `aws-luckyus-dbatest-rw` (8.0.42) | 测试库，验证全流程 |
| **Batch 1: 数据分析** | Week 1-2 | ldas (8.0.40, db.t4g.large), ldas01 (8.0.41, db.t4g.large) | 仅运维内部使用的监控分析库，对业务零影响，无需跨团队沟通，便于发现和处理问题。数据量最大 (86GB+128GB)，提前验证大实例升级耗时 |
| **Batch 2: 低风险** | Week 2-3 | 内部工具 (12个): ijumpserver, ilsopdevopsdata, iluckydorisops, iadmin, ipermission, igers, iehr, oplog, pubdm, iluckymedia, iriskcontrolservice, mfranchise | 内部/低流量，影响面小 |
| **Batch 3: 中风险** | Week 3-4 | 运维/运营 (14个): devops, opshop, opshopsale, opproduction, opqualitycontrol, opempefficiency, iopocp, iopshopexpand, fichargecontrol, fitax, ifiaccounting, ibillingcentersrv, iunifiedreconcile, iluckyhealth | 运营后台，非直接面客 |
| **Batch 4: SCM/平台** | Week 4-5 | SCM + Platform (18个): scm-*, scmcommodity, scmsrm, ireplenishment, iopenadmin, iopenlinker, iopenservice, ibizconfigcenter, iluckyams, iotplatform, upush | 供应链和平台服务 |
| **Batch 5: 核心业务** | Week 5-6 | Framework + DevOps (4个): framework01, framework02, devops, iworkflowmidlayer | Nacos 配置中心、核心框架 — **有 66 张 utf8mb3 表需提前验证** |
| **Batch 6: 营销/订单** | Week 6-7 | Sales 全系 + 数据 (10个): salesmarketing, salescrm, salesorder, salespayment, isalescdp, isalesdatamarketing, isalesmembermarketing, isalesprivatedomain, cdpactivity, icyberdata | **最核心**，直接影响门店运营，放最后充分积累经验 |

### 6.2 升级窗口

- **推荐时间**: 北京时间周二/周三 17:00-20:00 (EST 05:00-08:00)
  - 美国门店尚未高峰（门店 7AM EST 开门）
  - 中国同事可协助值守
  - 避开每日批处理 05:00 UTC (00:00 EST)
- **每批次预留**: micro 实例批量 2-3 个同时升级，medium/large 逐个升级

---

## 七、升级前必须完成的准备工作

### 7.1 参数组创建

参数组创建及完整参数设置命令见第三节。

### 7.2 调整维护窗口

将所有 35 个处于高峰时段维护窗口的实例调整到 02:00-06:00 UTC。详见 `maintenance_window_report.md`。

### 7.3 应用兼容性检查（需协调 Ops 团队）

| 检查项 | 方法 | 负责 |
|--------|------|------|
| **JDBC 驱动版本** | MySQL Connector/J >= 8.0.28 (推荐 8.4.x) | Ops/Dev |
| **连接字符串参数** | 确认无 deprecated 参数（如 useSSL → sslMode） | Ops/Dev |
| **SQL 兼容性** | 在 `dba84test-rw` 上回放慢查询日志验证 | DBA |
| **ORM 框架** | MyBatis/JPA 版本是否支持 8.4 | Dev |
| **GROUP BY 排序依赖** | `grep -r "GROUP BY" 应用代码`，确认无隐式排序依赖 | Dev |

### 7.4 监控准备

| 检查项 | 操作 |
|--------|------|
| **RDS Exporter** | 确认 exporter 兼容 MySQL 8.4（在 dba84test 验证） |
| **Grafana Dashboard** | 确认仪表盘指标在 8.4 下正常显示 |
| **CloudWatch Alarms** | 确认告警不会因版本变更误触发 |
| **慢查询日志** | 确认 8.4 下 slowquery log group 自动创建 |

### 7.5 utf8mb3 表处理（可升级后逐步处理）

| 实例 | 数据库 | utf8mb3 表数 | 建议 |
|------|--------|------------|------|
| framework01 | luckyus_nacos | 9 | 升级后逐步 ALTER 至 utf8mb4（Nacos 表小） |
| framework01 | luckyus_sddl_platform | 54 | 评估后批量转换 |
| framework01 | luckyus_gaea | 2 | 升级后转换 |
| framework01 | luckyus_zkdoctor | 1 | 升级后转换 |
| icyberdata | luckyus_icyberdata_nacos | 9 | 升级后转换 |
| icyberdata | luckyus_icyberdata | 1 | 升级后转换 |
| ldas01 | luckyus_db_collection | 1 | 升级后转换 |

> utf8mb3 在 8.4 中 deprecated 但仍可用，不影响升级。建议升级后择期转换。

---

## 八、风险评估总结

| # | 风险项 | 概率 | 影响 | 缓解措施 |
|---|--------|------|------|---------|
| R1 | RDS 预检查失败，阻塞升级 | 中 | 🟢 低 | 预检查在停机前执行。检查 PrePatchCompatibility.log 并修复 |
| R2 | 认证失败（mysql_native_password） | 低（已处理） | 🔴 致命 | 参数组已设 `mysql_native_password=ON` |
| R3 | 查询计划变化导致慢查询 | 中 | 🟡 中 | 升级前在测试库回放，`prefer_ordering_index=off` 已设。Blue/Green 允许切换前测试 |
| R4 | salesmarketing-rw (46GB) 蓝绿创建时间长 | 高 | 🟢 低 | 预留 2-4 小时创建 green 环境，安排周末窗口 |
| R5 | db.t4g.micro 实例升级时 OOM | 中 | 🟡 中 | 监控 FreeableMemory，SwapUsage > 400MB 时推迟升级 |
| R6 | JDBC 驱动与 caching_sha2_password 不兼容 | 低 | 🔴 高 | 保持 `mysql_native_password=ON`，认证插件迁移作为独立项目 |
| R7 | Prometheus exporter 不兼容 | 低 | 🟡 中 | 验证 exporter 兼容 8.4，需将 `SHOW SLAVE STATUS` 改为 `SHOW REPLICA STATUS` |
| R8 | 5 月 31 日截止日期未赶上 | 中 | 🔴 高 | Phase A: 先升到 8.0.45 解除强制升级威胁（快速、低风险） |
| R9 | GROUP BY 结果顺序变化 | 低 | 🟡 中 | 应用团队排查 SQL 依赖 |
| R10 | utf8mb3 warning 刷日志 | 中 | 🟢 低 | 功能不受影响，升级后逐步转换 |

---

## 九、沟通计划

### 干系人矩阵

| 干系人 | 角色 | 通知方式 |
|--------|------|---------|
| Michael (CTO) | 审批 | 每周状态报告，Batch 5 (营销/订单) 需单独 go/no-go |
| Ops 团队 | 应用验证 | 每批次提前 48 小时通知，切换期间实时沟通 |
| 中国总部 DBA | 交叉验证 | 每周同步，共享升级发现 |
| 各服务负责人 | 升级后测试 | 每批次发送邮件，含时间线和验证步骤 |

### 通知模板

```
Subject: [RDS 升级] MySQL 8.0→8.4 — 第 {N} 批 — {日期} {时间} UTC

升级实例: {列表}
预计停机: Blue/Green 切换 ~30 秒 / In-Place ~10-30 分钟
维护窗口: 02:00-06:00 UTC

需要配合: 切换后 1 小时内验证应用功能。
回滚方案: 快照恢复可用。

联系人: David Zeng (DBA)
```

---

## 十、时间线

```
Week 0 (当前):  创建参数组 + 在 dba84test/datalink-84test 切换参数组验证
Week 1:         Batch 0 — 升级 dbatest → 全流程验证 + 应用兼容性检查
Week 1-2:       Batch 1 — 数据分析 (ldas, ldas01) — 运维内部，零业务影响
Week 2-3:       Batch 2 — 低风险内部工具 (12个)
Week 3-4:       Batch 3 — 运营后台 (14个)
Week 4-5:       Batch 4 — SCM/平台 (18个)
Week 5-6:       Batch 5 — 核心框架 (4个，含 utf8mb3 表实例)
Week 6-7:       Batch 6 — 营销/订单核心 (10个)
```

**预计全量完成: 6-7 周**

---

## 附录 A: utf8mb3 表影响分析

### A.1 utf8mb3 表分布总览

共 **77 张** utf8mb3 表，分布在 3 个实例，全部数据量极小（总计 < 2MB）：

| 实例 | 数据库 | utf8mb3 表数 | utf8mb4 表数 | 混用情况 | 数据量 |
|------|--------|-------------|-------------|---------|--------|
| framework01 | luckyus_nacos | 9 | 3 | 混用 | ~0.18 MB |
| framework01 | luckyus_sddl_platform | 54 | 5 | 混用 | ~1.1 MB |
| framework01 | luckyus_gaea | 2 | 25 | 混用 | ~0.11 MB |
| framework01 | luckyus_zkdoctor | 1 | 43 | 混用 | ~0.02 MB |
| icyberdata | luckyus_icyberdata_nacos | 9 | 0 | 全 utf8mb3 | ~0.28 MB |
| icyberdata | luckyus_icyberdata | 1 | 0 | 仅 1 张 | ~0.02 MB |
| ldas01 | luckyus_db_collection | 1 | 0 | 仅 1 张 | ~0.02 MB |

### A.2 Collation 分布

| Collation | 表数 | 所在数据库 |
|-----------|------|-----------|
| `utf8mb3_bin` | 20 | luckyus_nacos (9), luckyus_icyberdata_nacos (9), luckyus_gaea (2) |
| `utf8mb3_general_ci` | 57 | luckyus_sddl_platform (54), luckyus_zkdoctor (1), luckyus_icyberdata (1), luckyus_db_collection (1) |

### A.3 影响评估

| 影响项 | 严重程度 | 说明 |
|--------|---------|------|
| 升级是否会失败 | **无影响** | utf8mb3 在 8.4 中 deprecated 但仍完全可用，不阻塞升级 |
| 现有数据读写 | **无影响** | SELECT/INSERT/UPDATE/DELETE 完全正常 |
| 跨 charset JOIN 索引失效 | **理论有风险，实际影响极小** | utf8mb3 列与 utf8mb4 列 JOIN 时，MySQL 做隐式转换导致索引失效。但涉及的表数据量 < 2MB，几乎全是空表 |
| Warning 日志 | **极低** | 仅 DDL（CREATE/ALTER TABLE）时产生 deprecation warning，DML 不受影响 |
| 新增列 charset 继承 | **需注意** | 在 utf8mb3 表上新增列若不指定 charset，将继承表级 utf8mb3 而非服务器默认 utf8mb4 |

### A.4 framework01 关键风险：同库混用 charset

`luckyus_nacos`、`luckyus_gaea`、`luckyus_sddl_platform`、`luckyus_zkdoctor` 这 4 个库同时存在 utf8mb3 和 utf8mb4 表。如果应用 SQL 涉及跨表 JOIN：

```sql
-- 示例: utf8mb3 表 JOIN utf8mb4 表
SELECT * FROM nacos_utf8mb3_table a
JOIN other_utf8mb4_table b ON a.name = b.name;
```

MySQL 会执行隐式 charset 转换（utf8mb3 → utf8mb4），导致被驱动表 JOIN 列上的索引失效，查询退化为全表扫描。

> 由于这些表数据量极小（大部分 0 行），即使全表扫描性能影响也可忽略。

### A.5 建议处理方案

**优先级**: 低。升级后择期批量转换即可，不阻塞升级计划。

转换原则：
- `utf8mb3_bin` 的表 → 转为 `utf8mb4_bin`
- `utf8mb3_general_ci` 的表 → 转为 `utf8mb4_general_ci`

```sql
-- nacos 表示例 (utf8mb3_bin → utf8mb4_bin)
ALTER TABLE luckyus_nacos.config_info CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
ALTER TABLE luckyus_nacos.config_info_aggr CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
ALTER TABLE luckyus_nacos.config_info_beta CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
ALTER TABLE luckyus_nacos.config_info_tag CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
ALTER TABLE luckyus_nacos.config_tags_relation CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
ALTER TABLE luckyus_nacos.group_capacity CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
ALTER TABLE luckyus_nacos.his_config_info CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
ALTER TABLE luckyus_nacos.tenant_capacity CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
ALTER TABLE luckyus_nacos.tenant_info CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

-- sddl_platform 表示例 (utf8mb3_general_ci → utf8mb4_general_ci，共 54 张)
-- 数据量极小，可一次性执行:
ALTER TABLE luckyus_sddl_platform.t_base_apply CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
-- ... (其余 53 张同理)

-- gaea 表 (utf8mb3_bin → utf8mb4_bin)
ALTER TABLE luckyus_gaea.t_config_center_project CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
ALTER TABLE luckyus_gaea.t_config_center_user_relation CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

-- zkdoctor 表 (utf8mb3_general_ci → utf8mb4_general_ci)
ALTER TABLE luckyus_zkdoctor.zk_nosql_cache CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

-- icyberdata nacos 表 (utf8mb3_bin → utf8mb4_bin，共 9 张，同 nacos 结构)
-- icyberdata 业务表 (utf8mb3_general_ci → utf8mb4_general_ci)
ALTER TABLE luckyus_icyberdata.batch_generatetask_record CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

-- ldas01
ALTER TABLE luckyus_db_collection.t_dba_bakstatus CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

> 所有表数据量 < 0.3 MB，ALTER 操作预计秒级完成，无需申请维护窗口。
