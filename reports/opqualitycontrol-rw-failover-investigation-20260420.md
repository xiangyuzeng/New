# opqualitycontrol-rw 告警调查报告

**日期**: 2026-04-20
**实例**: aws-luckyus-opqualitycontrol-rw
**事件**: OOM 导致 Multi-AZ Failover

---

## 告警原因：OOM 导致 Multi-AZ Failover

RDS 事件链（UTC 时间）：

| 时间 | 事件 |
|------|------|
| 13:30:30 | Multi-AZ failover **开始** |
| 13:30:56 | DB instance **重启** |
| 13:31:14 | **"The RDS Multi-AZ primary instance is busy and unresponsive"** |
| 13:33:36 | **"A database workload is causing the system to run critically low on memory"**，RDS 自动将 innodb_buffer_pool_size 设为 128MB |

## 根因分析

**实例严重资源不足**：

| 指标 | 值 | 问题 |
|------|------|------|
| 实例规格 | **db.t4g.micro** (1 vCPU / 1GB RAM) | 极小规格 |
| Swap 使用 | **~800MB**（接近 RAM 大小）| 严重 swap thrashing |
| 可用内存 | 80-100MB (仅 ~10% RAM) | 长期内存压力 |
| Buffer Pool | 128MB (数据集 585MB) | 命中率不足，大量磁盘 I/O |
| max_connections | **4000** | 对 1GB 实例来说过高 |
| 今日慢查询 | **5,427 条** (阈值 100ms) | 大量 I/O 导致 |

**触发 Failover 的关键慢查询** — `t_expiry_print_log` 上的窗口函数查询：

```sql
SELECT ... FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY dept_id, print_type, 
    stock_goods_spec_code, collection_code ORDER BY expire_time DESC) AS rn 
  FROM t_expiry_print_log 
  WHERE dept_id IN (500+ 个值...)  -- 巨大 IN 列表
  AND expire_time >= '2026-03-21' AND confirm_time IS NULL
) tmp WHERE rn = 1;
```

- 该表 19.4 万行 / 152MB，带窗口函数 + 500+ dept_id IN 子句
- 执行时间 1.16-1.35 秒，每分钟执行一次
- 在 1GB 实例上频繁执行这种查询 → swap thrashing → 主节点无响应 → failover

## 现状

实例已通过 failover 恢复，当前运行正常，但 **根本问题未解决** — 下次还会发生。

## 建议

| 优先级 | 操作 | 预期效果 |
|--------|------|----------|
| **P0** | 升级到 **db.t4g.small** (2GB) 或 **db.t4g.medium** (4GB) | 消除内存压力，buffer pool 可覆盖全部数据集 |
| **P0** | 降低 `max_connections` 从 4000 到 **200** | 减少内存预留，防止 OOM |
| **P1** | 优化 `t_expiry_print_log` 查询 — 将大 IN 子句改为 JOIN 或分批查询 | 降低单次查询内存消耗 |
| **P2** | 调整 `long_query_time` 从 0.1s 到 1s | 减少慢查询日志量 |

升级到 db.t4g.small 的成本估算：On-Demand $0.032/h × 730h × 0.69(EDP) = **~$16.12/月**（当前 micro 约 $8/月），增加不到 $8 即可根本解决问题。
