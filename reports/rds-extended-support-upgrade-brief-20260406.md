# RDS Extended Support 与 MySQL 升级问题简要说明

**日期**: 2026-04-06
**编制**: David Zeng (Senior DBA)
**AWS Account**: 257394478466 (us-east-1)

---

## 1. 什么是 RDS Extended Support？

RDS Extended Support 是 AWS 提供的付费服务，允许数据库实例在大版本标准支持到期后继续运行旧版本，并获得安全补丁。

| 阶段 | 费用 (On-Demand) | 套 EDP 69 折后 |
|------|------------------|---------------|
| 标准支持期内 | 免费 | 免费 |
| Extended Support Year 1-2 | $0.11/vCPU/hr | $0.0759/vCPU/hr |
| Extended Support Year 3 | $0.22/vCPU/hr | $0.1518/vCPU/hr |

---

## 2. 我们的实例状态

通过 `aws rds describe-db-instances` 的 `EngineLifecycleSupport` 字段检查，结果如下：

| 引擎 | 实例数 | Extended Support 状态 |
|------|--------|----------------------|
| MySQL 8.0 | 61 | **全部 disabled（禁用）** |
| PostgreSQL | 3 | 全部 disabled |
| DocumentDB | 12 | 不适用 (N/A) |

**检查方法**：
```bash
aws rds describe-db-instances --region us-east-1 \
  --query 'DBInstances[*].[DBInstanceIdentifier,Engine,EngineVersion,EngineLifecycleSupport]' \
  --output table
```

---

## 3. Extended Support 与升级的关系

`EngineLifecycleSupport` 的设置直接决定标准支持到期后 AWS 如何处理实例：

```
                     标准支持到期
                         │
              ┌──────────┴──────────┐
              │                     │
     Extended Support          Extended Support
        ENABLED                  DISABLED ← 我们
              │                     │
      保持旧版本运行            AWS 自动强制
      额外付费续命              升级到下一大版本
     ($0.11/vCPU/hr)           (8.0 → 8.4)
```

### 对我们的影响

我们 61 个 MySQL 实例全部设置为 `disabled`，这意味着：

- **不会产生 Extended Support 额外费用**（好处）
- **标准支持到期后，AWS 将在维护窗口内自动强制升级大版本**（风险）
- **已有实例无法修改此设置**，只能通过快照恢复重建来更改

### 关键时间节点

| 版本 | 实例数 | 标准支持到期 | 距今 |
|------|--------|------------|------|
| MySQL 8.0.40 | 58 | **2026-05-31** | **55 天** |
| MySQL 8.0.41 | 1 | 2026-05-31 | 55 天 |
| MySQL 8.0.42 | 1 | 2026-07-31 | 116 天 |
| MySQL 8.0.44 | 1 | 2026-07-31 | 116 天 |
| **MySQL 8.0 大版本** | **全部** | **2026-07-31** | **116 天** |

---

## 4. 是否可以手动升级？

**可以。** 经验证，AWS 支持以下升级路径：

```
8.0.40/41/42/44 → 8.0.45（小版本升级）→ 8.4.8（大版本升级）
```

### 有利条件

| 条件 | 状态 | 说明 |
|------|------|------|
| 实例类型 | 全部 t4g/t3（当前代） | 无需先升级实例 Class |
| Multi-AZ | 全部 61 个启用 | 升级先在 standby 执行再 failover，停机约 30 秒 |
| Read Replica | 无 | 不需要处理副本升级顺序 |
| 参数兼容性 | 25 个自定义参数全部兼容 8.4 | 参数迁移无障碍 |
| 升级失败保护 | RDS 自动 precheck + 自动回滚 | precheck 失败不会造成停机 |

### 采用两阶段升级策略

| 阶段 | 操作 | 风险 | 停机时间 |
|------|------|------|---------|
| Phase 1 | 8.0.x → 8.0.45 (小版本) | 低 | ~30s (Multi-AZ failover) |
| Phase 2 | 8.0.45 → 8.4.8 (大版本) | 中 | ~10min + failover |

先升级到 8.0.45（最新小版本），确保所有实例统一版本后，再统一升级到 8.4.8。比直接跨版本升级更稳妥。

---

## 5. 升级计划概要

分 8 个批次、按业务风险从低到高推进：

| 批次 | 内容 | 实例数 | 计划周次 |
|------|------|--------|---------|
| Batch 0 | dbatest（测试验证） | 1 | Week 1 |
| Batch 1 | 运维工具（jumpserver, dorisops, oplog 等） | 7 | Week 2 |
| Batch 2 | 内部管理系统（HR, 权限, 媒体, 推送等） | 16 | Week 2-3 |
| Batch 3 | 运营/门店系统 | 7 | Week 3 |
| Batch 4 | 供应链系统 | 11 | Week 3-4 |
| Batch 5 | 财务系统 | 5 | Week 4 |
| Batch 6 | 销售/CRM 核心 | 9 | Week 4-5 |
| Batch 7 | 数据平台/框架（含 635GB 最大实例） | 5 | Week 5 |

### 里程碑

| 时间 | 里程碑 |
|------|--------|
| **05/11** | Phase 1 完成 — 全部 61 实例升级到 8.0.45 |
| **05/31** | 8.0.40/41 标准支持到期（已无影响） |
| **06/15** | Phase 2 完成 — 全部 61 实例升级到 8.4.8 |
| **07/31** | 8.0 大版本标准支持到期（已无影响） |

详细升级计划见：[mysql-upgrade-plan-8045-848.md](mysql-upgrade-plan-8045-848.md)

---

## 6. 行动项

| 优先级 | 行动 | 负责人 | 截止日期 |
|--------|------|--------|---------|
| P0 | 在 dbatest-rw 执行 8.0.42 → 8.0.45 测试升级 | DBA | 04/13 |
| P0 | 按批次执行 Phase 1 小版本升级 | DBA | 05/11 |
| P1 | 创建 mysql8.4 参数组并配置自定义参数 | DBA | 05/11 |
| P1 | 在 dbatest-rw 执行 8.0.45 → 8.4.8 大版本测试 | DBA | 05/18 |
| P1 | 协调应用团队进行 8.4 兼容性测试 | DBA + Ops | 05/18 |
| P1 | 按批次执行 Phase 2 大版本升级 | DBA | 06/15 |
| P2 | 升级完成后清理旧参数组和过期快照 | DBA | 06/30 |
