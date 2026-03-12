# MySQL 存储分析报告：aws-luckyus-icyberdata-rw

**日期**：2026-03-12
**分析人**：David Zeng (DBA)
**实例**：`aws-luckyus-icyberdata-rw`
**严重级别**：🟡 中等（存储使用率 78.7%，binlog 写入量异常偏高）

---

## 1. Executive Summary

对数据库实例 `aws-luckyus-icyberdata-rw` 进行全面存储检查，发现以下关键问题：

1. **Binlog 异常膨胀**：`binlog_row_image = FULL` + ROW 格式 + 7天保留，导致 binlog 日均生成 ~68 GB，累计占用磁盘约 **480 GB**（占总存储的 75.6%）
2. **存储使用率 78.7%**：635 GB 已分配，仅剩 ~135 GB 空闲，若写入量波动，约 45 小时内可能耗尽
3. **两张表高度碎片化**：`task_instance`（83.3%）和 `task_instance_content`（83.2%），合计浪费 3.6 GB

**核心优化动作**：将 `binlog_row_image` 从 `FULL` 改为 `MINIMAL`（无需重启，预计释放 300-400 GB binlog 存储）。

---

## 2. 实例概况

| 项目 | 值 |
|------|-----|
| 实例标识 | aws-luckyus-icyberdata-rw |
| 实例规格 | db.t4g.medium |
| 引擎版本 | MySQL 8.0.40 |
| 存储类型 | gp3 |
| 配置 IOPS | 12,000 |
| Multi-AZ | 是 |
| 加密 | 是 |
| 状态 | available |
| 已分配存储 | 635 GB |

---

## 3. 存储使用分析

### 3.1 OS 级别（CloudWatch FreeStorageSpace）

| 时间（UTC） | 剩余空间 |
|------------|---------|
| 2026-03-12 00:00 | 135.2 GB |
| 2026-03-12 05:00 | 134.0 GB |（05:00 批量任务时段，消耗加速）
| 2026-03-12 11:00 | **135.3 GB**（最新） |

```
已分配：635 GB
剩余：  ~135 GB
已用：  ~500 GB (78.7%)
```

### 3.2 数据库数据层（information_schema）

| 数据库 | 数据大小 | 碎片空间 | 碎片率 | 表数量 |
|--------|---------|---------|--------|--------|
| luckyus_icyberdata | 20.48 GB | 4.80 GB | 19.0% | 440 |
| luckyus_icyberdata_nacos | ~0 GB | ~0 GB | 91.4% | 12 |
| luckyus_icyberdata_user | ~0 GB | ~0 GB | 0.0% | 12 |
| **合计** | **~20.5 GB** | | | 464 |

### 3.3 空间缺口分析

```
OS 已用空间：  ~500 GB
DB 数据大小：  ~20.5 GB
━━━━━━━━━━━━━━━━━━━━━━━
不明占用：     ~479.5 GB  ← Binlog 积累
```

---

## 4. 根因分析：Binlog 异常膨胀

### 4.1 配置确认

```sql
mysql> SHOW VARIABLES WHERE Variable_name IN ('binlog_format', 'binlog_row_image');
+-----------------+-------+
| Variable_name   | Value |
+-----------------+-------+
| binlog_format   | ROW   |
| binlog_row_image| FULL  |
+-----------------+-------+

mysql> CALL mysql.rds_show_configuration;
+------------------------+-------+
| name                   | value |
+------------------------+-------+
| binlog retention hours | 168   |  ← 7 天
+------------------------+-------+
```

### 4.2 三因素叠加

| 因素 | 值 | 影响 |
|------|-----|------|
| binlog_format | ROW | 逐行记录，无法压缩 |
| binlog_row_image | **FULL** | UPDATE/DELETE 记录完整行前后镜像 |
| binlog 保留时间 | **168 小时（7天）** | 长期积累 |

**FULL 模式数据放大示意**：

```
DELETE 1行（假设该行 500 字节）
  → MINIMAL 模式：仅记录主键（~20 字节）
  → FULL 模式：记录完整行数据（~500 字节）
  → 放大倍数：25x
```

### 4.3 每日 Binlog 生成量估算

```
binlog 累计占用：~480 GB
保留时间：       168 小时（7天）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
日均 binlog：    ~68.6 GB/天
小时均 binlog：  ~2.86 GB/小时
```

对于一个只有 **20.5 GB** 数据量的库，日均 68 GB binlog 极不正常（比值 = 3.3x/天）。

### 4.4 高写入量来源

结合碎片化分析，核心原因是任务调度系统的**大批量 DELETE 操作**：

- `task_instance` 表：数据仅 0.41 GB，但碎片 2.06 GB（83.3%）—— 大量历史任务被删除
- `task_instance_content` 表：数据仅 0.31 GB，碎片 1.52 GB（83.2%）—— 同上

每次批量清理旧任务时，ROW + FULL 模式将每行完整数据写入 binlog，造成 binlog 体积爆炸式增长。

---

## 5. 大表详情

| 排名 | 表名 | 数据大小 | 碎片空间 | 碎片率 | 行数 | 说明 |
|------|------|---------|---------|--------|------|------|
| 1 | task_instance_content_archive | 8.28 GB | 0.01 GB | 0.1% | 974K | 归档表，健康 |
| 2 | task_instance_history | 8.24 GB | 0.004 GB | 0.0% | 1.54M | 归档表，健康 |
| 3 | core_node_history_archive | 1.01 GB | 0.005 GB | 0.5% | 6.4M | 归档表，健康 |
| 4 | core_node_history_archive202509 | 0.79 GB | 0 GB | 0.0% | 5.0M | 归档表，健康 |
| 5 | task_instance_logpath_archive | 0.40 GB | 0.005 GB | 1.2% | 1.3M | 归档表，健康 |
| 6 | **task_instance** | **0.41 GB** | **2.06 GB** | **83.3% ⚠️** | 54K | 高碎片，需优化 |
| 7 | **task_instance_content** | **0.31 GB** | **1.52 GB** | **83.2% ⚠️** | 28K | 高碎片，需优化 |
| 8 | task_snapshoot | 0.35 GB | 0.005 GB | 1.4% | 43K | 正常 |
| 9 | task_instance_dependency_history | 0.20 GB | 0.004 GB | 1.9% | 1.1M | 正常 |

> 两张归档表（task_instance_content_archive + task_instance_history）合计 **16.5 GB**，占 DB 总量的 80.5%。

---

## 6. 风险评估

| 风险项 | 当前状态 | 风险等级 | 说明 |
|--------|---------|---------|------|
| 存储剩余空间 | 135 GB (21%) | 🟡 中等 | 稳态下不会继续增长，但无充足缓冲 |
| Binlog 日均生成量 | ~68 GB/天 | 🔴 高 | 写入量翻倍即触发磁盘告警 |
| 写入量翻倍时耗尽时间 | ~45 小时 | 🔴 高 | 任何批量数据迁移/清理任务均可触发 |
| 表碎片化 | 两张表 83%+ | 🟡 中等 | 影响查询性能，浪费 3.6 GB |
| 归档表持续增长 | ~17 GB，年增未知 | 🟡 中等 | 需建立数据生命周期策略 |

---

## 7. 优化建议

### 优先级 1：修改 `binlog_row_image`（立即，无停机）

**操作**：在 RDS Parameter Group 中将 `binlog_row_image` 从 `FULL` 改为 `MINIMAL`

```
MINIMAL 模式行为：
  DELETE：仅记录主键列（用于定位行）
  UPDATE：记录主键 + 实际变更的列
  INSERT：记录所有列（无变化）
```

**预期收益**：
- binlog 日均生成量：68 GB → 预计降至 5-15 GB（减少 75-90%）
- 7 天后稳态 binlog 存量：480 GB → 预计降至 35-105 GB
- 释放磁盘空间：~375-445 GB
- 存储使用率：78.7% → 预计降至 10-25%

**执行步骤**：
1. AWS Console → RDS → Parameter Groups → 找到 icyberdata 实例使用的参数组
2. 编辑参数 `binlog_row_image` = `minimal`（动态参数，立即生效，**无需重启**）
3. 修改后观察 1 小时 binlog 生成速率变化
4. 7 天后旧 binlog 自动过期，存储将大幅下降

> **注意**：如果下游有 Canal / Debezium 等 binlog 解析组件，需提前确认其是否依赖 FULL 模式的完整行镜像。

### 优先级 2：缩短 Binlog 保留时间（可选，配合优先级 1）

当前 168 小时（7天）。若无读副本或严格 PITR 需求，可缩短至 48-72 小时：

```sql
-- 缩短至 72 小时（3天）
CALL mysql.rds_set_configuration('binlog retention hours', 72);

-- 验证
CALL mysql.rds_show_configuration;
```

> 建议先完成优先级 1，再评估是否需要调整保留时间。

### 优先级 3：修复碎片化表（低峰期，无停机风险）

在每日业务低峰期（建议 EST 00:00-02:00）执行：

```sql
-- 预估执行时间：task_instance ~5-10 分钟，task_instance_content ~3-5 分钟
OPTIMIZE TABLE luckyus_icyberdata.task_instance;
OPTIMIZE TABLE luckyus_icyberdata.task_instance_content;
```

**预期收益**：回收 ~3.6 GB，同时重建索引提升查询性能。

> **注意**：OPTIMIZE TABLE 会对表加锁，执行期间该表不可写，务必在低峰期操作。

### 优先级 4：归档表数据生命周期策略（中期规划）

两张归档表（16.5 GB）持续增长，建议：
- 评估超过 N 个月的历史任务数据是否需要保留在 MySQL
- 可考虑将 2年以前数据迁移至 S3 + Athena 查询方案
- 对 `core_node_history_archive` 等已有月份分表（202509）的表，继续执行分表策略并 DROP 过期分表

---

## 8. 行动计划

| 序号 | 动作 | 操作人 | 优先级 | 预计收益 | 风险 |
|------|------|--------|--------|---------|------|
| 1 | 修改 Parameter Group：`binlog_row_image=minimal` | DBA | 🔴 本周内 | 释放 ~375-445 GB | 极低（动态参数，无需重启） |
| 2 | 确认无 Canal/Debezium 等 binlog 消费方依赖 FULL 模式 | DBA + Dev | 🔴 执行#1前 | 规避兼容性风险 | — |
| 3 | OPTIMIZE TABLE task_instance & task_instance_content | DBA | 🟡 本周低峰期 | 回收 3.6 GB + 性能提升 | 低（需维护窗口） |
| 4 | 调整 binlog 保留时间至 72h（可选） | DBA | 🟢 优先级1后评估 | 进一步节省存储 | 低 |
| 5 | 制定归档表数据生命周期策略 | DBA + 应用团队 | 🟢 中期 | 长期存储可控 | 低 |

---

## 9. 监控建议

优化完成后，建议在 CloudWatch/Grafana 添加以下告警：

```
FreeStorageSpace < 50 GB  → Warning
FreeStorageSpace < 20 GB  → Critical（立即处理）
```

并在修改 `binlog_row_image` 后，连续观察 3 天的 FreeStorageSpace 趋势，验证 binlog 生成速率下降。

---

*Report generated: 2026-03-12 | Author: David Zeng (DBA) | Instance: aws-luckyus-icyberdata-rw*
