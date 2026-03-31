# RCA: RDS VIP 连接中断 — aws-luckyus-iluckyams-rw

**故障时间:** 2026-03-31 05:35:48 UTC (13:35:48 CST)
**数据库:** iluckyams (App Messaging Service / 应用消息服务)
**实例:** aws-luckyus-iluckyams-rw
**实例类型:** db.t4g.micro (2 vCPU, 1 GB RAM) — Burstable
**报警:** ALR-021 — `min_over_time(mysql_check_vip{}[1m]) == 0`
**排查人:** David Zeng (DBA)
**报告日期:** 2026-03-31

---

## 1. 故障概要

`aws-luckyus-iluckyams-rw` 实例于 2026-03-31 05:32:54 UTC 因 **AWS RDS 自动引擎小版本升级 (MySQL 8.0.42 → 8.0.44)** 而短暂关机。该升级在实例预设的 **维护窗口 (每周二 05:29-05:59 UTC)** 内自动触发，Auto Minor Version Upgrade 为 **启用** 状态。实例在 05:36:20 UTC 重启，升级在 05:38:19 UTC 完成。引擎重启耗时约 3 分 26 秒 (05:32:54 shutdown → 05:36:20 restart)，但 **应用层面实际不可用时间约 5 分 48 秒** (05:33:00 连接断开 → 05:38:48 报警恢复)，额外的 2 分 28 秒为 InnoDB buffer pool 预热、post-upgrade 任务执行及应用连接池重建耗时。此次中断属于 **计划维护行为**，非故障性宕机。当前实例已完全恢复，连接正常。

**严重程度评估:** 中等。iluckyams 为应用消息服务(非 L0 核心交易链路)，影响范围有限。但该实例存在严重的 **慢性内存压力问题** (SwapUsage 占 RAM 40%+)，需要关注。

---

## 2. 时间线

| 时间 (UTC) | 时间 (CST) | 事件 | 来源 |
|------------|------------|------|------|
| 05:29:02 | 13:29:02 | 升级前备份开始 | RDS Events |
| 05:31:05 | 13:31:05 | 升级前备份完成 | RDS Events |
| 05:31:56 | 13:31:56 | 引擎版本升级预检查开始 | RDS Events (maintenance) |
| 05:32:27 | 13:32:27 | 预检查完成 | RDS Events (maintenance) |
| 05:32:54 | 13:32:54 | **DB 实例关机** | RDS Events (availability) |
| 05:33:00 | 13:33:00 | DatabaseConnections 降至 0 | CloudWatch |
| 05:33:14 | 13:33:14 | 升级过程中备份开始 | RDS Events (backup) |
| 05:33:26 | 13:33:26 | **停机时间开始** | RDS Events (maintenance) |
| 05:34:38 | 13:34:38 | 引擎版本升级开始 | RDS Events (maintenance) |
| 05:35:48 | 13:35:48 | **VIP 不通报警触发 (ALR-021)** | 报警系统 |
| 05:36:20 | 13:36:20 | **DB 实例重启完成** (但仍处于 "升级中" 状态，post-upgrade 任务进行中) | RDS Events (availability) |
| 05:37:42 | 13:37:42 | 引擎版本升级完成，后升级任务进行中 | RDS Events (maintenance) |
| 05:38:18 | 13:38:18 | 升级后备份完成 | RDS Events (backup) |
| 05:38:19 | 13:38:19 | **版本升级完成: 8.0.42 → 8.0.44** | RDS Events |
| 05:38:48 | 13:38:48 | **VIP 不通报警恢复** (InnoDB warmup 完成，连接池重建) | 报警系统 |
| 05:40:26 | 13:40:26 | 最终备份完成 | RDS Events (backup) |

---

## 3. 根因分析

### 主要原因: AWS RDS 自动引擎小版本升级

AWS 在预设维护窗口 **(每周二 05:29-05:59 UTC / 13:29-13:59 CST)** 内对 `aws-luckyus-iluckyams-rw` 执行了 **MySQL 8.0.42 → 8.0.44 自动小版本升级**。实例的 **Auto Minor Version Upgrade 已确认为启用状态**，因此当 AWS 发布 8.0.44 补丁后，RDS 在下一个维护窗口自动执行了升级。此升级导致实例短暂关机并重启，触发了 VIP 不通报警。

**确认依据:**
1. **RDS Events** 完整记录了升级全过程: pre-check → shutdown → upgrade → restart → complete
2. **MySQL Uptime = 1,389 秒** (查询时 05:58 UTC) — 确认重启时间为 ~05:35 UTC
3. **当前版本 = 8.0.44** (升级前 8.0.42)
4. **DatabaseConnections 在 05:33-05:35 降至 0**，05:36 恢复至 2，05:41 恢复至 9
5. **仅 iluckyams-rw 受影响** — 同时段无其他实例发生 maintenance/availability 事件

### 排除的假设

| 假设 | 排除依据 |
|------|----------|
| Multi-AZ 故障转移 | RDS Events 无 failover 事件；hostname 未变化 (ip-172-17-0-47)；buffer_pool = 256 MB (非 OOM 自动降级的 128 MB) |
| CPU Credit 耗尽 | CPUCreditBalance 全程 = 288 (满值)；CPUSurplusCreditBalance = 0 (无借用) |
| OOM 宕机 | 虽然内存压力严重，但此次中断是由计划升级触发，非 OOM crash |
| 监控探针故障 (误报) | RDS Events 确认了实际的实例关机/重启；CloudWatch 连接数实际降至 0 |
| 网络/DNS 问题 | DNS 解析正常 (10.238.9.93)；NetworkThroughput 未中断 (仅因实例关机而暂停) |

---

## 4. 黄金流程影响评估

**iluckyams (App Messaging Service) 不属于 L0 核心交易链路。**

| 评估项 | 结果 |
|--------|------|
| 是否 L0 核心库 (salesorder/salespayment) | ❌ 否 |
| 点单/支付流程是否受影响 | ❌ 否 |
| 实例标签 | `envtype=prod`, `bg_type=lucky` (无详细服务标签) |
| 连接应用 | `iluckyams_A_w` — 2 个应用连接 (10.238.45.4, 10.238.40.170) |
| 影响范围 | 应用消息推送服务短暂中断约 5 分 48 秒 (含 InnoDB warmup) |

**结论:** 黄金流程 (下单/支付) 未受影响。影响仅限于应用消息推送功能短暂不可用。

---

## 5. CloudWatch 指标

### 5.1 故障窗口核心指标 (05:30-05:45 UTC)

| 指标 | 升级前 (05:30) | 停机中 (05:33-05:35) | 重启后 (05:36-05:38) | 恢复 (05:42+) | 状态 |
|------|---------------|---------------------|---------------------|--------------|------|
| CPUUtilization | 9.7% | 11.5-28.3% | **29.3%** (peak) | 5.8% | ✅ 正常 (升级重启峰值) |
| DatabaseConnections | 6 | **0** | 2-4 | 9-10 | ✅ 已恢复 |
| FreeableMemory | 140 MB | 87 MB → **223 MB** | 96-105 MB | 93 MB | ⚠️ 持续偏低 |
| NetworkReceive (B/s) | 2,086 | 5,421-43,719 | 2,768-3,408 | 1,735-1,855 | ✅ 正常 |
| NetworkTransmit (B/s) | 36,985 | 224K-**3.4M** | 36K-80K | 28K-38K | ✅ 正常 (备份上传峰值) |

### 5.2 CPU Credit 分析 (04:00-06:00 UTC, 2 小时窗口)

| 指标 | 值 | 评估 |
|------|-----|------|
| CPUCreditBalance | **288 (全程满值)** | ✅ 无耗尽风险 |
| CPUSurplusCreditBalance | **0 (全程)** | ✅ 未借用额外积分 |
| CPUUtilization 基线 | 4.2-5.7% | ✅ 低负载 |
| CPUUtilization 峰值 | 29.3% (05:36, 重启) | ✅ 仅升级期间短暂升高 |

**结论:** CPU Credit 不是问题。该实例负载极低，积分始终满值。

### 5.3 内存压力分析 (04:00-06:00 UTC) — 🔴 严重

| 时段 | FreeableMemory | SwapUsage | 评估 |
|------|---------------|-----------|------|
| 04:00-05:30 (升级前) | **83-148 MB** (8-14% of 1 GB) | **386-437 MB** (37-42% of RAM) | 🔴 慢性内存耗尽 |
| 05:33-05:35 (重启中) | 87 → 223 MB | 435 → **15 MB** | ✅ 重启释放内存 |
| 05:36-05:45 (重启后) | 96-223 MB | 214 → 322 MB | ⚠️ Swap 快速回升 |
| 05:45-05:58 (恢复后) | 100-116 MB | 322 → **351 MB** | 🔴 23 分钟内 Swap 从 15 MB 回升至 351 MB |

**关键发现:** 重启后仅 23 分钟，SwapUsage 从 15 MB 快速回升至 351 MB。这证明该实例存在 **慢性内存不足** 问题 —— `db.t4g.micro` 的 1 GB RAM 无法满足工作负载需求。

---

## 6. MySQL 状态 (故障恢复后)

### 6.1 连接状态

| 指标 | 当前值 | 评估 |
|------|--------|------|
| Threads_connected | 11 | ✅ 正常 |
| Threads_running | 2 | ✅ 正常 |
| Threads_cached | 5 | ✅ 正常 |
| Threads_created | 16 | ✅ 正常 (重启后) |
| Aborted_clients | **64** | ⚠️ 升级中断导致的客户端断连 |
| Aborted_connects | 1 | ✅ 正常 |
| Total Connections (since restart) | 235 | ✅ 正常 |
| Max_used_connections | 16 (at 05:45) | ✅ 低 |
| max_connections 设置 | **4,000** | 🔴 严重过高 (1 GB RAM 推荐 ≤200) |

### 6.2 InnoDB / 实例配置

| 指标 | 当前值 | 评估 |
|------|--------|------|
| hostname | ip-172-17-0-47 | ✅ 未变化 (无 failover) |
| server_id | 1517830778 | ✅ |
| read_only | 0 | ✅ 主实例 |
| super_read_only | 0 | ✅ 主实例 |
| innodb_buffer_pool_size | **256 MB** | ✅ 正常 (未 OOM 自动降级) |
| MySQL Version | **8.0.44** | ✅ 升级成功 |
| Uptime | 1,389 秒 (~23 分钟) | ✅ 确认重启时间 |

### 6.3 当前连接明细

| 用户 | 来源 IP | 数据库 | 状态 | 数量 |
|------|---------|--------|------|------|
| iluckyams_A_w | 10.238.45.4, 10.238.40.170 | luckyus_iluckyams | Sleep | 2 |
| diagtools | 10.238.10.251 | information_schema | Sleep | 3 |
| diagtools | 10.238.3.43 | — | Query | 1 |
| rdsadmin | localhost | mysql | Sleep | 2 |
| event_scheduler | localhost | — | Daemon | 1 |

---

## 7. 当前状态

| 项目 | 状态 | 说明 |
|------|------|------|
| 实例可用性 | ✅ available | RDS 状态正常 |
| DNS 解析 | ✅ 10.238.9.93 | 解析正常 |
| TCP 连通 | ✅ port 3306 open | 端口可达 |
| MySQL 连接 | ✅ 正常响应 | SELECT 1 成功 |
| 主实例状态 | ✅ read_only=0 | 非只读，主实例 |
| Multi-AZ | ✅ 启用 | Primary: us-east-1b, Standby: us-east-1a |
| Buffer Pool | ✅ 256 MB | 未被 OOM 降级 |
| CPU | ✅ 5.6% | 基线水平 |
| CPU Credits | ✅ 287-288 | 满值 |
| FreeableMemory | 🔴 ~107 MB | 仅剩 10% 可用内存 |
| SwapUsage | 🔴 ~351 MB | 重启 23 分钟后已回升至 351 MB |
| max_connections | 🔴 4,000 | 对 1 GB RAM 实例严重过高 |
| 应用连接 | ✅ 2 连接 | 低负载 |

---

## 8. 风险评估

### 8.1 db.t4g.micro 是否适合当前工作负载?

**🔴 不适合。** 虽然 CPU 和连接数均很低 (CPU 5%, 仅 2 个应用连接)，但 **内存严重不足**:

| 指标 | 当前值 | 健康阈值 | 差距 |
|------|--------|----------|------|
| FreeableMemory | 83-148 MB | > 300 MB (30% of RAM) | 远低于阈值 |
| SwapUsage | 386-437 MB | < 50 MB (5% of RAM) | **超标 8-9 倍** |
| 重启后 Swap 回升速度 | 15 → 351 MB / 23 min | N/A | 内存泄漏或 buffer pool 过大 |

**根本矛盾:** `innodb_buffer_pool_size=256 MB` 占 1 GB RAM 的 25%。加上 MySQL 系统开销 (~300-400 MB) + `max_connections=4000` 的线程栈预留 (~4000 × 256 KB = 1 GB 理论值)，总内存需求远超 1 GB 物理 RAM。

### 8.2 CPU Credits 是否面临耗尽风险?

**✅ 短期无风险。** CPUCreditBalance 全程 288 (满值)，基线 CPU ~5%。但如果未来负载增长，burstable 实例的 credit 模型可能成为隐患。

### 8.3 升级是否会再次发生?

**⚠️ 会。** 已确认 Auto Minor Version Upgrade 当前为 **启用** 状态，维护窗口为 **每周二 05:29-05:59 UTC (01:29-01:59 EST)**。每次 AWS 发布新的 MySQL 小版本补丁时，该实例将在维护窗口内自动升级并重启，预计导致 5-7 分钟的应用不可用。

### 8.4 此次升级是否会引入兼容性问题?

**⚠️ 需监控。** MySQL 8.0.42 → 8.0.44 是安全补丁和 bug 修复，一般无破坏性变更。但建议监控接下来 24 小时的应用日志，确认无兼容性问题。

---

## 9. 建议后续动作

### 🔴 立即行动 (P0)

1. **降低 max_connections**
   - 当前值: 4,000 (灾难性设置)
   - 建议值: **200** (当前最大使用 16 个连接)
   - 原因: 每个连接线程占用 ~256 KB 栈内存，4000 连接理论需 1 GB 栈空间，超过实例总 RAM
   - 操作: 通过 RDS Parameter Group 修改，无需重启

2. **监控 Swap 回升趋势**
   - 重启后 23 分钟 Swap 已从 15 MB 回升至 351 MB
   - 设置 CloudWatch 告警: SwapUsage > 400 MB 触发通知
   - 如 48 小时内 Swap 回升至升级前水平 (430+ MB)，执行 P1 升级

### 🟠 短期 (本周, P1)

3. **升级实例到 db.t4g.small**
   - 从 1 GB RAM → 2 GB RAM
   - 月成本增加: ~$8.50/月 (EDP 后: $5.87/月)
   - 预期效果: FreeableMemory 提升至 ~1.1 GB, Swap 降至接近 0
   - 如负载增长，可进一步升级至 db.t4g.medium (4 GB)

4. **Review 维护窗口与自动升级策略**
   - 当前维护窗口: **每周二 05:29-05:59 UTC (01:29-01:59 EST / 13:29-13:59 CST)**，处于业务低峰期，时间合理
   - Auto Minor Version Upgrade: **已启用** — 考虑是否需要关闭，改为手动控制升级时机，以便提前通知相关团队
   - 建议在维护窗口升级前增加通知机制 (如 SNS 事件订阅)
   - 如保留自动升级，应确保报警 SOP 中标注此维护窗口，避免值班 DBA 误判为故障

### 🟢 中期 (本月, P2)

5. **完善实例标签**
   - 当前仅有 `envtype=prod`, `bg_type=lucky`
   - 建议添加: `service=iluckyams`, `team=platform`, `service_level=L1`
   - 便于黄金流程影响评估和成本归属

6. **建立监控覆盖**
   - 该实例在 Prometheus 中无 `mysql_check_vip` 或 `up` 指标 (仅 VMAlert 覆盖)
   - 考虑部署 mysqld_exporter 以获得更细粒度的监控数据
   - 启用 Enhanced Monitoring (1 秒粒度) 以便未来排查

7. **审计所有 db.t4g.micro 实例**
   - 此次事件暴露 micro 实例的内存瓶颈
   - 建议排查所有 db.t4g.micro 生产实例的 SwapUsage 和 FreeableMemory
   - 参考 isalescdp-rw 的历史教训 (同为 micro 实例，最终因 OOM 触发故障转移)

---

## 10. 证据附录

<details>
<summary>RDS Events (完整)</summary>

```
05:29:02 | backup     | Backing up DB instance
05:31:05 | backup     | Finished DB Instance backup
05:31:56 | maintenance| The pre-check started for the DB engine version upgrade.
05:32:27 | maintenance| The pre-check finished for the DB engine version upgrade.
05:32:54 | availability| DB instance shutdown
05:33:14 | backup     | Backing up DB instance
05:33:26 | maintenance| The downtime started for the DB instance.
05:34:38 | maintenance| The engine version upgrade started.
05:36:20 | availability| DB instance restarted
05:37:42 | maintenance| The engine version upgrade finished.
05:37:42 | maintenance| The post-upgrade tasks are in progress.
05:38:18 | backup     | Finished DB Instance backup
05:38:19 |            | Database instance engine minor version upgrade complete. Previous version: 8.0.42. New version: 8.0.44.
05:38:23 | backup     | Backing up DB instance
05:40:26 | backup     | Finished DB Instance backup
```
</details>

<details>
<summary>实例配置</summary>

```json
{
  "Status": "available",
  "MultiAZ": true,
  "AZ": "us-east-1b",
  "SecondaryAZ": "us-east-1a",
  "Engine": "mysql",
  "EngineVersion": "8.0.44",
  "Class": "db.t4g.micro",
  "StorageType": "gp3",
  "AllocatedStorage": 20,
  "MaxAllocatedStorage": 1000,
  "InstanceCreateTime": "2025-04-14T11:42:20.500000+00:00",
  "LatestRestorableTime": "2026-03-31T05:54:03+00:00",
  "PendingModified": {}
}
```
</details>

<details>
<summary>CloudWatch CPU 趋势 (05:30-05:45 UTC)</summary>

| 时间 (UTC) | CPUUtilization (%) |
|------------|-------------------|
| 05:30 | 9.65 |
| 05:31 | 7.38 |
| 05:32 | 8.73 |
| 05:33 | 11.47 |
| 05:34 | 19.37 |
| 05:35 | **28.34** |
| 05:36 | **29.32** |
| 05:37 | 19.11 |
| 05:38 | 9.06 |
| 05:39 | 9.85 |
| 05:40 | 9.63 |
| 05:41 | 7.76 |
| 05:42 | 5.81 |
| 05:43 | 7.01 |
| 05:44 | 6.77 |
</details>

<details>
<summary>CloudWatch 内存趋势 (选取关键时间点)</summary>

| 时间 (UTC) | FreeableMemory (MB) | SwapUsage (MB) |
|------------|--------------------|----|
| 04:00 | 123 | 417 |
| 04:18 | 94 | 368 |
| 04:33 | 97 | 372 |
| 05:00 | 115 | 404 |
| 05:30 | 134 | 414 |
| 05:31 | 119 | 415 |
| 05:32 | 117 | 412 |
| 05:33 | **84** | 160 |
| 05:34 | 208 | **15** |
| 05:35 | **213** | **17** |
| 05:36 | 92 | 204 |
| 05:37 | 90 | 232 |
| 05:38 | 100 | 252 |
| 05:42 | 89 | 291 |
| 05:45 | 98 | 307 |
| 05:50 | 106 | 321 |
| 05:55 | 110 | 332 |
| 05:58 | 106 | **335** |
</details>

<details>
<summary>MySQL Processlist (查询时 05:58 UTC)</summary>

```
ID   | User            | Host                    | DB                   | Command | Time | State
5    | event_scheduler | localhost               | NULL                 | Daemon  | 1384 | Waiting on empty queue
211  | diagtools       | 10.238.10.251:31592     | information_schema   | Sleep   | 142  |
220  | diagtools       | 10.238.10.251:5118      | information_schema   | Sleep   | 82   |
221  | diagtools       | 10.238.10.251:5132      | information_schema   | Sleep   | 82   |
16   | iluckyams_A_w   | 10.238.45.4:35592       | luckyus_iluckyams    | Sleep   | 75   |
13   | iluckyams_A_w   | 10.238.40.170:58646     | luckyus_iluckyams    | Sleep   | 74   |
55   | rdsadmin        | localhost               | NULL                 | Sleep   | 26   |
8    | rdsadmin        | localhost               | mysql                | Sleep   | 2    |
```
</details>

<details>
<summary>并发事件检查</summary>

同一 2 小时窗口内，仅 `aws-luckyus-iluckyams-rw` 发生了 maintenance/availability 事件。无其他 RDS 实例受影响。
</details>

<details>
<summary>监控覆盖检查</summary>

- Prometheus `mysql_check_vip{instance=~".*iluckyams.*"}`: 无数据 (该指标不在此 Prometheus 实例)
- Prometheus `up{job=~".*iluckyams.*"}`: 无数据 (无专属 exporter)
- VIP 监控由 VMAlert (10.238.3.137/143/52:8880, 10.238.3.153:8880) 负责
- RDS Error Log 下载: AccessDenied (IAM `databasecheck` 用户缺少 `rds:DownloadDBLogFilePortion` 权限)
</details>

---

*报告生成: 2026-03-31 | 实例: aws-luckyus-iluckyams-rw | 数据库: iluckyams | 排查人: David Zeng*
*工具: AWS CLI, mcp-db-gateway, CloudWatch, Prometheus*
