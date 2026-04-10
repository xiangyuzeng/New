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

### 1.5 认证插件分布（抽样）

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

共 18 个自定义参数，详见上次对话。

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

### 4.2 单实例升级步骤

```
┌─────────────────────────────────────────────────────┐
│ Phase 0: 升级前准备 (T-7天)                          │
├─────────────────────────────────────────────────────┤
│ 1. 创建参数组 luckyus-prod-84-new                    │
│ 2. 在 8.4 测试实例验证参数组生效                       │
│ 3. 确认应用连接器兼容 8.4                             │
│ 4. 通知应用团队升级窗口                               │
└────────────────────┬────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│ Phase 1: 升级前检查 (T-1小时)                         │
├─────────────────────────────────────────────────────┤
│ 1. 手动创建 snapshot (命名: {instance}-pre84-YYYYMMDD)│
│ 2. 检查 SHOW PROCESSLIST — 无长事务                   │
│ 3. 检查 CloudWatch 指标基线 (CPU/Mem/IOPS/Conn)      │
│ 4. 记录当前慢查询 baseline                            │
│ 5. 确认没有正在运行的 DDL 操作                         │
└────────────────────┬────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│ Phase 2: 执行升级                                     │
├─────────────────────────────────────────────────────┤
│ aws rds modify-db-instance \                         │
│   --db-instance-identifier {INSTANCE} \              │
│   --engine-version 8.4.8 \                           │
│   --db-parameter-group-name luckyus-prod-84-new \    │
│   --allow-major-version-upgrade \                    │
│   --apply-immediately                                │
│                                                      │
│ ⏱ 预计停机: 10-30 分钟 (Multi-AZ failover)           │
│   - micro 实例: ~10-15 分钟                           │
│   - large/xlarge: ~20-30 分钟 (数据量大)              │
└────────────────────┬────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│ Phase 3: 升级后验证 (T+0)                             │
├─────────────────────────────────────────────────────┤
│ 1. SELECT VERSION() — 确认 8.4.8                     │
│ 2. SELECT plugin FROM mysql.user — 确认认证插件正常    │
│ 3. 应用连接测试 — 各服务能正常读写                     │
│ 4. 检查 error log — CloudWatch /error 日志            │
│ 5. SHOW VARIABLES LIKE 'mysql_native_password'       │
│ 6. 检查 Grafana 监控 — exporter 数据正常              │
│ 7. 确认参数组状态为 in-sync (可能需要 reboot)          │
└────────────────────┬────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│ Phase 4: 升级后观察 (T+24h)                           │
├─────────────────────────────────────────────────────┤
│ 1. 慢查询对比 — 是否有新增慢查询                       │
│ 2. CPU/内存趋势 — 是否有异常升高                       │
│ 3. 连接数监控 — 是否正常                              │
│ 4. 应用错误日志 — 是否有 SQL 兼容性问题                │
└─────────────────────────────────────────────────────┘
```

### 4.3 回滚方案

| 方案 | 适用场景 | RTO |
|------|---------|-----|
| **从 snapshot 恢复** | 升级后出现严重兼容性问题 | 15-30 分钟 (需改 endpoint 或 rename) |
| **降级不支持** | RDS MySQL 不支持 major version 降级 | N/A |

> **重要**: MySQL major version 升级是**不可逆**的。唯一回滚方式是从升级前的 snapshot 恢复新实例，然后切换 endpoint。

---

## 五、分批升级策略

### 5.1 推荐分批顺序

| 批次 | 时间 | 实例 | 理由 |
|------|------|------|------|
| **Batch 0: 测试验证** | Week 1 | `aws-luckyus-dbatest-rw` (8.0.42) | 测试库，验证全流程 |
| **Batch 1: 低风险** | Week 2 | 内部工具 (12个): ijumpserver, ilsopdevopsdata, iluckydorisops, iadmin, ipermission, igers, iehr, oplog, pubdm, iluckymedia, iriskcontrolservice, mfranchise | 内部/低流量，影响面小 |
| **Batch 2: 中风险** | Week 3 | 运维/运营 (14个): devops, opshop, opshopsale, opproduction, opqualitycontrol, opempefficiency, iopocp, iopshopexpand, fichargecontrol, fitax, ifiaccounting, ibillingcentersrv, iunifiedreconcile, iluckyhealth | 运营后台，非直接面客 |
| **Batch 3: SCM/平台** | Week 4 | SCM + Platform (18个): scm-*, scmcommodity, scmsrm, ireplenishment, iopenadmin, iopenlinker, iopenservice, ibizconfigcenter, iluckyams, iotplatform, upush | 供应链和平台服务 |
| **Batch 4: 核心业务** | Week 5 | Framework + DevOps (4个): framework01, framework02, devops, iworkflowmidlayer | Nacos 配置中心、核心框架 — **有 66 张 utf8mb3 表需提前验证** |
| **Batch 5: 营销/订单** | Week 6 | Sales 全系 + 数据 (10个): salesmarketing, salescrm, salesorder, salespayment, isalescdp, isalesdatamarketing, isalesmembermarketing, isalesprivatedomain, cdpactivity, icyberdata | **最核心**，直接影响门店运营 |
| **Batch 6: 数据分析** | Week 6+ | ldas, ldas01 | 最大数据量 (86GB+128GB)，升级时间最长 |

### 5.2 升级窗口

- **推荐时间**: 北京时间周二/周三 17:00-20:00 (EST 05:00-08:00)
  - 美国门店尚未高峰（门店 7AM EST 开门）
  - 中国同事可协助值守
  - 避开每日批处理 05:00 UTC (00:00 EST)
- **每批次预留**: micro 实例批量 2-3 个同时升级，medium/large 逐个升级

---

## 六、升级前必须完成的准备工作

### 6.1 参数组创建（需 IAM 权限）

```bash
# 1. 创建主参数组
aws rds create-db-parameter-group \
  --db-parameter-group-name luckyus-prod-84-new \
  --db-parameter-group-family mysql8.4 \
  --description "Luckin USA production MySQL 8.4 (migrated from luckyus-prod-80-new)" \
  --region us-east-1

# 2. 设置参数 (18个，见上次对话)

# 3. 创建 salesorder 专用参数组
aws rds create-db-parameter-group \
  --db-parameter-group-name luckyus-prod-84-new-groupconcatmaxlen \
  --db-parameter-group-family mysql8.4 \
  --description "Luckin USA production MySQL 8.4 with group_concat_max_len=1048576" \
  --region us-east-1

# 4. 设置参数 (在主参数组基础上 +1 个 group_concat_max_len)
```

### 6.2 应用兼容性检查（需协调 Ops 团队）

| 检查项 | 方法 | 负责 |
|--------|------|------|
| **JDBC 驱动版本** | MySQL Connector/J >= 8.0.28 (推荐 8.4.x) | Ops/Dev |
| **连接字符串参数** | 确认无 deprecated 参数（如 useSSL → sslMode） | Ops/Dev |
| **SQL 兼容性** | 在 `dba84test-rw` 上回放慢查询日志验证 | DBA |
| **ORM 框架** | MyBatis/JPA 版本是否支持 8.4 | Dev |
| **GROUP BY 排序依赖** | `grep -r "GROUP BY" 应用代码`，确认无隐式排序依赖 | Dev |

### 6.3 监控准备

| 检查项 | 操作 |
|--------|------|
| **RDS Exporter** | 确认 exporter 兼容 MySQL 8.4（在 dba84test 验证） |
| **Grafana Dashboard** | 确认仪表盘指标在 8.4 下正常显示 |
| **CloudWatch Alarms** | 确认告警不会因版本变更误触发 |
| **慢查询日志** | 确认 8.4 下 slowquery log group 自动创建 |

### 6.4 utf8mb3 表处理（可升级后逐步处理）

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

## 七、单实例升级命令模板

```bash
# Step 1: 创建升级前快照
aws rds create-db-snapshot \
  --db-instance-identifier {INSTANCE} \
  --db-snapshot-identifier {INSTANCE}-pre84-$(date +%Y%m%d) \
  --region us-east-1

# Step 2: 等待快照完成
aws rds wait db-snapshot-available \
  --db-snapshot-identifier {INSTANCE}-pre84-$(date +%Y%m%d) \
  --region us-east-1

# Step 3: 执行升级
aws rds modify-db-instance \
  --db-instance-identifier {INSTANCE} \
  --engine-version 8.4.8 \
  --db-parameter-group-name luckyus-prod-84-new \
  --allow-major-version-upgrade \
  --apply-immediately \
  --region us-east-1

# Step 4: 等待升级完成
aws rds wait db-instance-available \
  --db-instance-identifier {INSTANCE} \
  --region us-east-1

# Step 5: 如果参数组状态为 pending-reboot，执行重启
aws rds reboot-db-instance \
  --db-instance-identifier {INSTANCE} \
  --region us-east-1

# Step 6: 验证
# SELECT VERSION();
# SHOW VARIABLES LIKE 'mysql_native_password';
# SELECT user,host,plugin FROM mysql.user;
```

---

## 八、风险评估总结

| 风险项 | 概率 | 影响 | 缓解措施 |
|--------|------|------|---------|
| 认证失败（mysql_native_password） | 低（已处理） | 🔴 致命 | 参数组已设 ON |
| 查询计划变化导致慢查询 | 中 | 🟡 中 | 升级前在测试库回放，`prefer_ordering_index=off` 已设 |
| GROUP BY 结果顺序变化 | 低 | 🟡 中 | 应用团队排查 |
| 升级停机超预期 | 低 | 🟡 中 | Multi-AZ failover，大实例预留 30 分钟 |
| Exporter/监控不兼容 | 低 | 🟢 低 | 先在 dba84test 验证 |
| utf8mb3 warning 刷日志 | 中 | 🟢 低 | 功能不受影响，升级后逐步转换 |
| t4g.micro 内存不足 | 低 | 🟡 中 | 8.4 内存优化有改善，但 performance_schema=1 有开销，需观察 |

---

## 九、时间线

```
Week 0 (当前):  创建参数组 + 在 dba84test/datalink-84test 切换参数组验证
Week 1:         升级 dbatest → 全流程验证 + 应用兼容性检查
Week 2:         Batch 1 — 低风险内部工具 (12个)
Week 3:         Batch 2 — 运营后台 (14个)
Week 4:         Batch 3 — SCM/平台 (18个)
Week 5:         Batch 4 — 核心框架 (4个，含 utf8mb3 表实例)
Week 6:         Batch 5 — 营销/订单核心 (10个)
Week 6+:        Batch 6 — 数据分析 (2个，最大实例)
```

**预计全量完成: 6-7 周**
