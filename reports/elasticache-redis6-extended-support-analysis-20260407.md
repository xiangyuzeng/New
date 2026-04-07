# ElastiCache Redis 6.x Extended Support 调查报告

**日期**: 2026-04-07  
**编制**: David Zeng (Senior DBA / Infrastructure Engineer)  
**AWS 账号**: 257394478466 (us-east-1)  
**数据来源**: AWS Pricing API + AWS 官方文档（docs.aws.amazon.com/AmazonElastiCache）

---

## 执行摘要

| 项目 | 结论 |
|------|------|
| Redis 6.x 标准支持终止 | **2027-01-31** |
| Extended Support 自动注册 | **2027-02-01**（无需操作，AWS 自动执行）|
| 3 年 Extended Support 总费用（EDP 后） | **$63,388**（$1,323/月 起，第 3 年翻倍至 $2,636/月）|
| 6.0.5 → 6.2.6 是否改变 deadline | **不会**（同属 redis6.x 大版本，deadline 相同）|
| 2027-02-01 发生什么 | 自动 patch 到 6.2.latest + 自动注册 ES + 开始计费 |
| 最优升级路径 | **Valkey 8.x**（省 20% 基础费用 + 无 ES 费用）|
| 紧迫性 vs MySQL | MySQL P0（55 天），Redis P1（9 个月），可以串行推进 |

---

## 一、Redis 6.0.5 EOL 时间线确认

### 1.1 官方 Extended Support 时间表（来源：AWS 官方文档）

| 大版本 | 标准支持终止 | ES Year 1 开始 | ES Year 2 开始 | ES Year 3 开始 | ES 终止 & 版本 EOL |
|--------|------------|---------------|---------------|---------------|-------------------|
| Redis OSS v4 | 2026-01-31 | 2026-02-01 | 2027-02-01 | 2028-02-01 | 2029-01-31 |
| Redis OSS v5 | 2026-01-31 | 2026-02-01 | 2027-02-01 | 2028-02-01 | 2029-01-31 |
| **Redis OSS v6** | **2027-01-31** | **2027-02-01** | **2028-02-01** | **2029-02-01** | **2030-01-31** |

> **关键点**：表格中是 `Redis OSS v6` **整个大版本**，不区分 6.0.x 和 6.2.x。  
> 6.0.5 和 6.2.6 的 deadline **完全相同**，均为 **2027-01-31**。

### 1.2 2027-02-01 会发生什么（AWS 行为）

根据 AWS 官方文档（参照 v4/v5 在 2026-02-01 的先例）：

```
2027-01-31 23:59 UTC
        │
        ▼
2027-02-01 00:00 UTC
        │
        ├─① 仍在 6.0.5 的集群：AWS 自动 patch 升级到 6.2.latest
        │   （因为 AWS 政策："ES 只对每个大版本的最新 patch 版提供"）
        │
        ├─② 所有 Redis 6.x 集群（含 6.2.6）：自动注册 Extended Support
        │
        └─③ 立即开始按 ES Year 1 费率计费
```

**引用原文**：
> *"Extended Support will only be offered for the latest supported patch version of each major Redis OSS version. If your Redis OSS v4 and v5 clusters are not already on the latest patch versions, they will be automatically upgraded before being enrolled in Extended Support."*

### 1.3 Extended Support 结束后（2030-01-31）

```
2030-01-31 之后（若仍在 Redis 6.x）：
  1. AWS 尝试自动升级到当时最新的 Valkey 版本（有停机风险）
  2. 若升级失败：AWS 保留删除该集群的权利
     （但会先保存数据快照）
```

**引用原文**：
> *"After the ElastiCache end of Extended Support date, Amazon ElastiCache will attempt to upgrade your engine to a newer engine version. If the upgrade fails, Amazon ElastiCache reserves the right to delete the cache. However, before doing so, Amazon ElastiCache will preserve your data."*

---

## 二、6.0.5 → 6.2.6 升级是否有意义

### 2.1 对 Extended Support 截止日期的影响

**答：完全没有影响。**

从 AWS 引擎版本 API 验证：

```
EngineVersion: "6.0"  → CacheParameterGroupFamily: "redis6.x"
EngineVersion: "6.2"  → CacheParameterGroupFamily: "redis6.x"
```

两者属于同一个参数组家族 `redis6.x`，AWS 视为同一大版本。  
**标准支持截止日期均为 2027-01-31，Extended Support 均从 2027-02-01 开始。**

### 2.2 6.0.5 → 6.2.6 的实际收益分析

| 收益维度 | 评估 | 说明 |
|---------|------|------|
| 改变 ES deadline | ❌ 无 | 同属 redis6.x，deadline 相同 |
| 额外安全补丁 | ✅ 有 | 6.2.6 > 6.0.5，有更多安全修复 |
| 提前获得 6.2 新特性 | ✅ 轻微 | ACL 增强、LMPOP 等命令 |
| 避免 2027-02-01 的自动 patch | ✅ 有 | 可以受控升级而非被动升级 |
| 减少 ES 总费用 | ❌ 无 | 费率相同 |

### 2.3 结论

**6.0.5 → 6.2.6 作为中间步骤意义有限**，但有一个合理场景：

> 如果不打算在 2027-01-31 前升级到 7.x 或 Valkey，  
> 那么提前在受控条件下升级到 6.2.6，比让 AWS 在 2027-02-01 自动 patch 更安全  
> （自动 patch 的维护窗口和停机时间由 AWS 控制）。

**但如果计划 6-12 个月内升级到 7.x 或 Valkey，直接跳过 6.2.6。**

---

## 三、实际 Extended Support 费用（精确计算）

### 3.1 各节点类型定价（AWS Pricing API 直接提取，us-east-1）

| 节点类型 | 数量 | Redis 基础价 $/hr | ES Yr1-2 额外费率 $/hr | ES Yr3 额外费率 $/hr | Valkey 基础价 $/hr |
|---------|------|-----------------|----------------------|--------------------|--------------------|
| cache.t4g.micro | 121 | $0.0160 | $0.0130（+81%）| $0.0260（+163%）| $0.0128（-20%）|
| cache.t4g.small | 15  | $0.0320 | $0.0260（+81%）| $0.0510（+159%）| $0.0256（-20%）|
| cache.t3.micro  | 6   | $0.0170 | $0.0140（+82%）| $0.0270（+159%）| $0.0136（-20%）|
| cache.t4g.medium| 2   | $0.0650 | $0.0520（+80%）| $0.1040（+160%）| $0.0520（-20%）|
| cache.m6g.large | 4 * | $0.1490 | $0.1190（+80%）| $0.2380（+160%）| $0.1192（-20%）|

> **\* 重要注记**：4 个 cache.m6g.large 节点中，2 个属于 `luckyus-redis-dify`（Redis 7.0.7），  
> **不受 Extended Support 影响**。以下计算采用保守估计（4 个全算），实际费用可能低约 9%。

### 3.2 按节点类型年度 ES 费用明细

| 节点类型 | 数量 | ES Year 1-2（年费）| ES Year 3（年费）|
|---------|------|--------------------|-----------------|
| cache.t4g.micro | 121 | **$13,779** | **$27,559** |
| cache.t4g.small | 15  | $3,416      | $6,701       |
| cache.t3.micro  | 6   | $736        | $1,419       |
| cache.t4g.medium| 2   | $911        | $1,822       |
| cache.m6g.large | 4   | $4,170      | $8,340       |
| **合计**        |**148** | **$23,012/年** | **$45,841/年** |

### 3.3 三年 Extended Support 总费用

| 年份 | 时间段 | On-Demand 价 | EDP 折后（×0.69）| 月均费用（EDP）|
|------|--------|-------------|-----------------|--------------|
| Year 1 | 2027-02-01 ~ 2028-01-31 | $23,013 | **$15,879** | **$1,323/月** |
| Year 2 | 2028-02-01 ~ 2029-01-31 | $23,013 | **$15,879** | **$1,323/月** |
| Year 3 | 2029-02-01 ~ 2030-01-31 | $45,841 | **$31,630** | **$2,636/月** |
| **3年总计** | | **$91,866** | **$63,388** | |

> **费率模型说明**：ElastiCache Extended Support 费用是按**节点小时**叠加收取，  
> Year 1-2 约为基础价的 +80%，Year 3 约为基础价的 +160%。  
> 这与 RDS Extended Support（按 vCPU 收费）不同，ElastiCache 按节点数计费。

### 3.4 当前基础成本参考

| 引擎 | 月费（EDP）| 年费（EDP）|
|------|-----------|-----------|
| 当前 Redis（156 节点）| $1,634 | $19,609 |
| 切换 Valkey（156 节点）| $1,307 | $15,687 |
| 月均节省（Valkey）| **$327** | **$3,922** |

---

## 四、推荐升级路径和时间线

### 4.1 升级路径对比

```
当前状态（154 节点 Redis 6.x）
         │
         ├─── 选项 A: 6.0.5 → 6.2.6 ──────────────────────────────── 不推荐
         │    停机: ~30s × 集群数（Multi-AZ failover）
         │    风险: 低（同 redis6.x 参数组，无需重建参数组）
         │    结果: 仍面临 2027-02-01 ES 注册，无法节省费用
         │
         ├─── 选项 B: 6.0.5 → 7.0.7 ──────────────────────────────── 推荐中期
         │    停机: ~30s × 集群数（Major version upgrade + failover）
         │    风险: 中（大版本升级，需兼容性测试）
         │    结果: 跳过 Redis 6.x 的 Extended Support
         │    注意: Redis 7.0 的 EOL 日期 AWS 尚未公布
         │    参数组: 需要从 redis6.x 迁移到 redis7 参数组
         │
         └─── 选项 C: 6.0.5 → Valkey 8.x ────────────────────────── 最优长期
              停机: ~30s × 集群数（Multi-AZ failover）
              风险: 中高（跨引擎迁移，但 API 兼容性极高）
              结果: 跳过 ES + 节省 20% 基础费用
              额外收益: Valkey 8.1 内存优化（最多 20% 减少内存占用）
              参数组: 需要新建 valkey8 参数组
```

### 4.2 推荐时间线

```
2026 年 4 月                    完成本次 Redis 6.x ES 调研（本文档）
2026 年 4-5 月       ██████████  【P0】集中完成 MySQL 8.0 → 8.4.8 升级（Deadline: 5月31日）
2026 年 6-7 月                  MySQL 升级扫尾 + Redis 升级前期规划
  ├─ 选定升级目标版本（Valkey 8.x 推荐）
  ├─ 在 dbatest 集群测试升级路径兼容性
  └─ 联系应用团队确认 Redis 命令兼容性（重点检查特殊命令）
2026 年 8-10 月      ██████████  【P1】Redis 6.x 批次升级
  ├─ Batch 1: DevOps 工具类（风险低）
  ├─ Batch 2: 平台/内部系统
  ├─ Batch 3: 销售/CRM/运营
  └─ Batch 4: 核心业务（最后升级）
2026 年 11-12 月                扫尾 + 验证（留 2 个月缓冲）
2027 年 01 月 31 日             ⚠️ Redis 6.x 标准支持终止 → 届时应已全部升完
```

### 4.3 各路径关键技术考量

**选项 B（6.x → 7.0.7）注意事项**：
- `redis6.x` → `redis7` 参数组不兼容，升级时需创建新参数组
- Redis 7.0 引入 SINTERCARD、LMPOP、ZMPOP 等新命令（应用代码无影响，向后兼容）
- Redis 7.0 的 ACL 行为有细微变化，使用 ACL 的集群需验证
- AutoMinorVersionUpgrade 当前全部为 OFF，升级后建议按需开启

**选项 C（6.x → Valkey 8.x）注意事项**：
- 需要使用 ElastiCache 跨引擎升级功能（`modify-replication-group` 指定 engine=valkey）
- Valkey 与 Redis OSS 7.2 功能等价，命令 API 100% 兼容
- 参数组需从 `redis6.x` 换为 `valkey8` 系列
- 不支持 Redis 专有模块（如 RedisJSON、RediSearch），但我们的用法未见使用这些模块
- **强烈推荐**：比 Redis 便宜 20%，且 AWS 明确将 Valkey 作为未来主力引擎

---

## 五、与 MySQL 升级项目的优先级对比

| 项目 | Deadline | 距今 | 风险等级 | 不升级的后果 |
|------|----------|------|---------|------------|
| **MySQL 8.0 → 8.4.8** | **2026-05-31** | **55 天** | **🔴 P0** | AWS 在维护窗口自动强制升级（有停机风险）|
| Redis 6.x → 7.x/Valkey | 2027-01-31 | ~9 个月 | 🟡 P1 | 自动注册 ES，开始收费（**不强制停机**）|

### 关键区别

| | MySQL | Redis |
|--|-------|-------|
| 不升级的后果 | **强制停机升级**（AWS 控制窗口）| **额外收费**（无立即停机）|
| 可接受的临时状态 | ❌ 不可接受 | ✅ 可以接受（付费续命）|
| 费用压力 | Extended Support $0.11/vCPU/hr（RDS）| ES Year 1-2 $1,323/月（EDP）|

### 建议

```
Phase 1（现在 - 2026年5月）: 100% 专注 MySQL 升级
  ├─ MySQL 必须在 5/31 前完成 Phase 1（8.0.x → 8.0.45）
  └─ 6/15 完成 Phase 2（8.0.45 → 8.4.8）

Phase 2（2026年6-12月）: Redis 升级
  ├─ 目标：2027-01-31 前完成全部 154 个 Redis 6.x 节点升级
  └─ 即使未完成，也只是 2027-02-01 起多付 $1,323/月，不会强制停机
```

---

## 六、关于 ElastiCache Extended Support 与 RDS Extended Support 的差异

> **重要区别**：ElastiCache 没有 `EngineLifecycleSupport=disabled` 机制。
> 
> - **RDS**：可以主动设置 `EngineLifecycleSupport=open-source-rds-extended-support-disabled`，使实例在标准支持到期后被 AWS **强制升级**（而非付费续命）
> - **ElastiCache**：**没有这个选项**。到期后强制自动注册 Extended Support 并收费。唯一避免方式是**主动升级**到受支持版本。
> 
> 我们的 MySQL 全部设为 `disabled`（适合我们主动升级的策略）。Redis 没有对应设置。

---

## 七、现有环境快照（本次调查时确认）

```bash
# 引擎版本确认
aws elasticache describe-cache-clusters \
  --cache-cluster-id luckyus-devops-001 --region us-east-1
→ EngineVersion: "6.0.5", CacheNodeType: "cache.t4g.micro", AutoMinorVersionUpgrade: false

aws elasticache describe-cache-clusters \
  --cache-cluster-id luckyus-iopenlinker-001 --region us-east-1
→ EngineVersion: "6.2.6", CacheNodeType: "cache.t4g.micro", AutoMinorVersionUpgrade: false

aws elasticache describe-cache-clusters \
  --cache-cluster-id luckyus-redis-dify-001 --region us-east-1
→ EngineVersion: "7.0.7", CacheNodeType: "cache.m6g.large", AutoMinorVersionUpgrade: true ✅
```

**可用版本（ElastiCache）**：
- Redis OSS: 4.0.10, 5.0.6, 6.0, 6.2, 7.0, 7.1
- Valkey: **7.2, 8.0, 8.1, 8.2**（推荐 8.2 — 最新，支持向量搜索）

**AWS Health Events**：0 条 ES/EOL 相关事件（正常，距离 deadline 还有 9 个月）

---

## 八、行动项总结

| 优先级 | 行动 | 负责人 | 截止 |
|--------|------|--------|------|
| P0 | 完成 MySQL 8.0 → 8.4.8 升级（Phase 1: 5/11，Phase 2: 6/15）| David | 2026-06-15 |
| P1 | 选定 Redis 升级目标版本（推荐 Valkey 8.2）| David + Michael | 2026-06-30 |
| P1 | 在 luckyus-devops 测试 Redis 6.0.5 → Valkey 8.2 升级（或 7.0.7）| David | 2026-07-15 |
| P1 | 联系应用团队确认 Redis 命令兼容性 | DBA + Ops | 2026-07-31 |
| P2 | 按批次完成全部 154 个 Redis 6.x 节点升级 | David | 2026-12-31 |
| P2 | 验证升级完成，确认 2027-01-31 前无 Redis 6.x 节点 | David | 2027-01-15 |

---

*报告生成时间：2026-04-07*  
*数据来源：AWS Pricing API（2026-04-07 实时提取）+ AWS 官方文档（docs.aws.amazon.com）*  
*联系：David Zeng — Senior DBA / Infrastructure Engineer*
