# OpenSearch luckycommon 集群 RED 告警调查报告

**事件编号**: LCNA-INC-2026-XXX（待分配）
**集群**: luckycommon (AWS OpenSearch / Elasticsearch 6.8)
**告警**: 【DB告警】AWS-ES 集群状态 Red_语音, 级别 P2
**调查时间**: 2026-04-23
**调查人**: 曾翔宇 (David Zeng) / Claude Code

---

## 一、事件概要

2026年4月20日 18:18:00 UTC，luckycommon OpenSearch 集群触发 RED 状态告警（P2级别），告警类型为语音告警（Red_语音）。该告警于 18:24:05 UTC 自动恢复，持续时间约 6分05秒。经详细调查，CloudWatch 在整个事件窗口内以1分钟粒度采集的所有指标均显示集群状态正常：ClusterStatus.red = 0、Nodes = 7、Shards.active = 100、Shards.unassigned = 0。**这表明 RED 事件极为短暂（亚分钟级），未被 CloudWatch 最小1分钟聚合周期捕获**，但被监控系统（宙斯）以更高频率的采样检测到。集群当前状态为 GREEN，未造成可观测的应用层影响。

---

## 二、时间线

| 时间 (UTC) | 事件 | 来源 |
|---|---|---|
| 18:00:00 | 集群状态正常，JVMMemoryPressure 50.5%，Nodes=7，Shards.active=100 | CloudWatch |
| 18:09:00 | SearchLatency 出现短暂峰值 59.5ms（平时 1-25ms） | CloudWatch |
| 18:12:00 | ClusterUsedSpace 出现微小下降 223,518→223,309 MB（~210MB / 0.09%） | CloudWatch |
| 18:13:00 | ClusterUsedSpace 恢复正常水平 | CloudWatch |
| 18:17:00 | JVMMemoryPressure 达到窗口内峰值 61%（非告警级别） | CloudWatch |
| **18:18:00** | **RED 告警触发**（宙斯检测到，CloudWatch 未捕获） | 宙斯告警系统 |
| 18:18:00-18:24:00 | CloudWatch 所有指标保持正常：red=0, nodes=7, shards=100, unassigned=0 | CloudWatch |
| **18:24:05** | **宙斯恢复通知** — 集群自动恢复 | 宙斯告警系统 |
| 18:24:00+ | JVMMemoryPressure 继续上升至 63-66%，属正常波动 | CloudWatch |

**关键发现**: RED 事件持续时间极短（可能仅数秒），完全未被 CloudWatch 1分钟粒度指标捕获。所有 CloudWatch 指标在整个事件窗口内保持正常。

---

## 三、根因分析

### 直接原因：亚分钟级瞬态 RED 状态

基于 CloudWatch 数据，本次事件呈现以下特征：
- **无节点丢失**: Nodes 指标始终为 7（Min 统计量）
- **无分片丢失**: Shards.active 始终为 100，Shards.unassigned 始终为 0
- **无大量索引删除**: DeletedDocuments 保持稳定在 ~4,956,500，ClusterUsedSpace 仅有 ~210MB 微小波动
- **无写入阻塞**: ClusterIndexWritesBlocked = 0
- **无线程池拒绝**: ThreadpoolWriteRejected = 0, ThreadpoolSearchRejected = 0
- **无 HTTP 错误**: 5xx = 0, 4xx = 0
- **JVM 压力中等**: 事件时刻 58.6%，远低于 80% 告警阈值

**最可能的根因**: 瞬态主节点（master）选举波动或极短暂的分片状态转换。t3.small.search 作为 dedicated master 是突发性能实例（burstable），在 CPU credit 耗尽或网络微抖动时可能导致极短暂的集群状态异常。master JVM 压力在 56-69% 之间呈锯齿波动，且 18:08 时 MasterCPUUtilization 出现 34% 短暂峰值。

另一可能原因：18:12-18:13 的 ~210MB 存储波动可能是一次小规模 segment merge 或 ISM 操作，在极短时间内导致某个无副本分片暂时不可用。

### 底层原因（结构性风险）

1. **0副本分片策略未整改**: 集群仍有 ~18 个主分片没有副本（59 primary, 仅 41 replica = 100 total shards）。任何持有这些无副本分片的节点出现哪怕极短暂的不可达，都会立即触发 RED。
2. **Elasticsearch 6.8 (EOL)**: 已过维护期，缺少新版本的分片分配恢复机制和稳定性改进。
3. **t3.small dedicated master**: 突发性能实例作为 master 节点，在 CPU/内存压力下可能出现微秒级延迟。
4. **JVM 压力慢性偏高**: 24小时基线显示 JVM 压力呈锯齿波形，峰值达 74-76%，GC 后降至 34-42%，然后持续爬升。长期运行在高位。

### 是否为 LCNA-INC-2026-008 的复发？

**部分是**。虽然本次事件的直接触发机制不同（非大量索引删除），但底层结构性风险与上次完全一致：
- 无副本分片数量未变（仍为 ~18 个）
- 实例类型未升级（仍为 m5.large）
- ES 版本未升级（仍为 6.8 EOL）
- AutoTune 仍处于禁用状态

**这是同一结构性脆弱性的不同表现形式。**

---

## 四、影响评估

| 影响维度 | 状态 | 详情 |
|---|---|---|
| **数据可用性** | **无影响** | CloudWatch 未检测到分片丢失或不可用 |
| **数据完整性** | **无影响** | 无数据丢失 |
| **写入操作** | **无影响** | ClusterIndexWritesBlocked = 0, IndexingLatency 正常 (0.23-0.56ms) |
| **搜索/查询** | **极微影响** | SearchLatency 在 18:09 有一次 59.5ms 峰值，其余正常 |
| **HTTP 错误** | **无影响** | 5xx = 0, 4xx = 0 |
| **2xx 吞吐量** | **正常** | 3,100-4,400/5min，无异常波动 |
| **Kibana** | **无影响** | KibanaHealthyNodes = 1 始终稳定 |
| **自动快照** | **无影响** | AutomatedSnapshotFailure = 0 |
| **应用侧影响** | **不可确定** | 需与 Ops 团队确认是否有应用日志异常 |

**总体评估**: P3 级别（低影响），无实际业务影响。告警有效但事件本身未造成损害。

---

## 五、与上次 RED 告警 (LCNA-INC-2026-008) 对比

| 对比维度 | 2026-03-08 事件 | 2026-04-20 事件 (本次) |
|---|---|---|
| **事件编号** | LCNA-INC-2026-008 | LCNA-INC-2026-XXX |
| **持续时间** | ~7 分钟 (RED ~1min, YELLOW ~6min) | ~6 分05秒 (CloudWatch 未捕获) |
| **CloudWatch 可见** | 是 — 节点下降、分片丢失清晰可见 | 否 — 所有1分钟指标正常 |
| **触发机制** | 41GB 大索引删除 → 节点过载掉线 | 未知（可能 master 瞬态波动或微 segment merge） |
| **节点丢失** | 7→6 (1节点掉线~1分钟) | 无 (始终7节点) |
| **Shards.unassigned 峰值** | 24 (5 primary + 19 replica) | 0 (CloudWatch 未检测到) |
| **JVMMemoryPressure** | 68-74% (非根因) | 50-66% (非根因) |
| **CPUUtilization** | 10-43% | 16-48% |
| **5xx 错误** | 3 | 0 |
| **4xx 错误** | 55 | 0 |
| **SearchLatency 峰值** | 8.1ms (4x 正常) | 59.5ms (孤立峰值，非持续) |
| **ClusterUsedSpace 变化** | -41,354 MB (26% 下降) | -210 MB (0.09% 波动) |
| **DeletedDocuments 变化** | +4M spike | 无变化 |
| **应用影响** | 有（5xx/4xx 错误，延迟升高） | 无可观测影响 |
| **根因类别** | 大索引删除 + 无副本分片 | 瞬态波动 + 无副本分片 (结构性) |
| **严重程度** | P1 (短暂但有影响) | P3 (无实际影响) |

**结论**: 本次事件规模远小于上次，但暴露了相同的底层结构性风险。

---

## 六、是否已整改

### 上次事件 (LCNA-INC-2026-008) 提出的整改项执行情况

| 整改项 | 建议日期 | 当前状态 | 备注 |
|---|---|---|---|
| **ISM 删除策略优化** | 2026-03-08 | ⚠️ 未确认 | 无法直接访问 REST API 验证 ISM 策略，但本次未触发大量删除 |
| **实例升级 m5.large → m5.xlarge/r5.large** | 2026-03-08 | ❌ 未执行 | 仍为 m5.large.search (4节点)，describe-domain 确认 |
| **ES 6.8 → OpenSearch 2.x 升级** | 2026-03-08 | ❌ 未执行 | 仍为 Elasticsearch_6.8 (EOL) |
| **添加 CloudWatch 告警** | 2026-03-08 | ⚠️ 部分 | 宙斯告警生效，但 CloudWatch 原生告警未确认 |
| **启用 AutoTune** | 2026-03-08 | ❌ 未执行 | AutoTuneOptions.DesiredState = DISABLED |
| **分片副本策略调整** | 2026-03-08 | ❌ 未执行 | 仍为 100 total shards (59 pri + 41 rep)，~18 个主分片无副本 |
| **EBS 扩容至 150GB** | 2026-03-08 | ❌ 未执行 | 仍为 100GB gp3（但改为gp3类型，2026-01-28执行）|

### 集群变更记录

自上次事件以来唯一的配置变更：
- **2026-01-28**: EBS 卷类型/配置调整 → gp3, 100GB, 3000 IOPS, 125 MB/s throughput（在上次事件之前）

**总结: 上次事件的6项整改建议中，0项完全执行。集群结构性风险未改善。**

---

## 七、后续行动项

### 紧急 (1-2周内)

| 序号 | 行动项 | 负责人 | 优先级 |
|---|---|---|---|
| 1 | **为所有主分片添加至少1个副本**：通过 VPC 内访问 REST API，将 ~18 个无副本索引的 `number_of_replicas` 从 0 改为 1。这是消除 RED 告警的最直接措施。 | DBA (David) | **P0** |
| 2 | **获取 VPC 内 REST API 访问**：建立从跳板机或 Lambda 到 OpenSearch VPC endpoint 的访问通道，以便执行集群运维操作和审计。 | DBA + Ops | **P0** |
| 3 | **审计所有 index template**：确保默认模板包含 `"number_of_replicas": 1`，防止新索引继续以0副本创建。 | DBA (David) | **P1** |
| 4 | **升级 dedicated master 实例类型**：t3.small → m5.large 或 c5.large，消除突发性能实例作为 master 的不稳定性。 | DBA + Michael | **P1** |

### 重要 (1-3个月内)

| 序号 | 行动项 | 负责人 | 优先级 |
|---|---|---|---|
| 5 | **升级数据节点实例类型**：m5.large → r5.large 或 r6g.large（Graviton）以提供更大 JVM heap（16GB → ~10GB heap），缓解慢性 JVM 压力。 | DBA + Michael | **P2** |
| 6 | **规划 ES 6.8 → OpenSearch 2.x 升级**：ES 6.8 已 EOL 超过2年，缺少关键的稳定性和安全修复。需要制定分步升级计划（6.8→7.10→OS 1.x→OS 2.x）。 | DBA + Ops + App | **P2** |
| 7 | **启用 AutoTune**：让 AWS 自动优化 JVM 和线程池参数，减少手动调优负担。 | DBA (David) | **P2** |
| 8 | **配置 CloudWatch 原生告警**：补充宙斯告警，设置 ClusterStatus.red≥1(1min) → P1 PagerDuty, JVMMemoryPressure>80%(10min) → Warning, Nodes<7(2min) → Critical。 | DBA (David) | **P2** |

### 长期 (3-6个月)

| 序号 | 行动项 | 负责人 | 优先级 |
|---|---|---|---|
| 9 | **评估 UltraWarm/冷存储分层**：将低频访问的历史日志索引迁至 UltraWarm tier，降低活跃数据量和 JVM 压力。 | DBA | **P3** |
| 10 | **分片策略全面审计和优化**：减少总分片数（当前59个主分片对4个数据节点可能过多），提高单分片大小。 | DBA | **P3** |

---

## 八、附录

### A. 原始数据文件位置

| 文件 | 路径 | 内容 |
|---|---|---|
| 集群健康摘要 | `~/temp/luckycommon-red-20260423-0323/cluster-health.json` | 集群配置、推断的当前状态 |
| CloudWatch 指标 | `~/temp/luckycommon-red-20260423-0323/cloudwatch-metrics.json` | 所有指标汇总（含24小时基线） |
| 分片策略审计 | `~/temp/luckycommon-red-20260423-0323/shard-strategy-audit.txt` | 分片副本分析和建议查询 |
| Domain 配置 | `~/temp/luckycommon-red-20260423-0323/describe-domain.json` | AWS OpenSearch describe-domain 完整输出 |
| Domain 摘要 | `~/temp/luckycommon-red-20260423-0323/describe-domain-summary.json` | 配置摘要 |

### B. 集群配置摘要

```
Engine:           Elasticsearch 6.8 (EOL)
Data Nodes:       4× m5.large.search (2 vCPU, 8 GiB RAM, ~4GB JVM heap each)
Dedicated Master: 3× t3.small.search (2 vCPU burstable, 2 GiB RAM)
Total Nodes:      7 (4 data + 3 master)
EBS:              100 GB gp3 per node (400 GB total)
Zone Awareness:   2 AZ (us-east-1a, us-east-1b)
VPC:              vpc-0dce7ca7770422d33
Shards:           59 primary + 41 replica = 100 total
AutoTune:         DISABLED
Auto Update:      DISABLED
```

### C. JVM Memory Pressure 24小时趋势 (2026-04-19 18:00 → 2026-04-20 18:30 UTC)

```
时间 (UTC)          JVM Max%    备注
───────────────── ──────────  ─────────────────
04-19 18:00       74.6%       基线偏高
04-19 22:30       75.7%       GC 前峰值
04-19 23:00       34.0%       ← Major GC 释放
04-20 00:00       39.5%       GC 后回升开始
04-20 05:00       64.8%       持续爬升
04-20 09:00       75.2%       再次接近峰值
04-20 11:30       42.3%       ← Major GC 释放
04-20 13:30       75.2%       快速爬回
04-20 15:30       75.5%       当天最高
04-20 17:30       50.7%       ← GC 释放
04-20 18:00       64.8%       事件前（又在爬升）
04-20 18:30       74.9%       事件后（继续爬升）
```

**模式**: 典型的 JVM 内存压力锯齿波 — 每 4-8 小时一次 Major GC，压力从 34-42% 爬升至 74-76%，循环反复。m5.large (8GB RAM, ~4GB heap) 对当前工作负载偏小。

### D. 访问限制说明

本次调查未能执行以下 REST API 查询（受 VPC 网络隔离限制）：
- `GET _cluster/health` — 无法直接获取集群实时健康状态
- `GET _cat/indices` — 无法列出索引及其分片配置
- `GET _template` — 无法审计索引模板的默认副本设置
- `GET _cat/shards` — 无法查看分片分配详情
- `GET _snapshot/_all` — 无法验证快照仓库和最近快照状态

建议建立 VPC 内访问通道（SSH tunnel、Lambda 函数或 VPC endpoint policy 调整）以支持后续运维。

### E. 上次事件报告参考

完整的 LCNA-INC-2026-008 报告位于:
`/app/.claude/worktrees/agent-a7176dcd/reports/es-cluster-red-luckycommon-2026-03-08.md`

---

*报告生成时间: 2026-04-23 03:23 UTC*
*调查工具: AWS CLI, CloudWatch MCP Server, mcp-db-gateway*
*调查人: 曾翔宇 (David Zeng) / Claude Code (automated)*
