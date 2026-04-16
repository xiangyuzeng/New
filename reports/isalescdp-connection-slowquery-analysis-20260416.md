# isalescdp 实例连接数 & 慢查询分析报告

- **实例**: aws-luckyus-isalescdp-rw
- **数据库**: luckyus_isales_cdp
- **分析时段**: 2026-04-14 00:00 UTC ~ 2026-04-16 14:00 UTC
- **报告日期**: 2026-04-16
- **分析人**: David Zeng (DBA)

---

## 1. 背景

近两天 isalescdp 实例活跃连接数偏高，需排查是否由慢查询导致。

## 2. 连接数概况

| 指标 | 值 |
|------|-----|
| max_connections | 4,000 |
| 当前总连接数 | 97 (94 Sleep + 1 Query + 1 Binlog Dump + 1 Daemon) |
| 当前最大连接用户 | `icdprealtimeuge_A_o` (56), `icdprealtimeuge_A_w` (38) |
| 两天内最高连接数 (峰值) | **214** (4/16 04:00 UTC) |
| 基线连接数 | 50-70 |

### 连接数趋势 (峰值, Max)

| 时段 (UTC) | 连接数峰值 |
|------------|-----------|
| 4/14 03:54 | 169 |
| 4/14 11:03 | 170 |
| 4/14 12:21 | 159 |
| 4/14 16:54 | 163 |
| 4/14 17:33 | 159 |
| 4/15 03:57 | 201 |
| 4/15 05:54 | 183 |
| 4/15 06:33 | 199 |
| 4/15 15:00 | 188 |
| 4/15 16:57 | 154 |
| 4/15 17:36 | 154 |
| **4/16 04:00** | **214** |

连接数峰值距离 max_connections=4000 还有很大余量，不存在连接耗尽风险。但峰值 200+ 比基线高出 3-4 倍。

## 3. 慢查询分析

### 3.1 慢查询配置

| 参数 | 值 |
|------|-----|
| long_query_time | 0.100000 (100ms) |
| Slow_queries (累计) | 38,338 |

### 3.2 两天内慢查询分布 (共 6,221 条)

| 时段 (UTC) | 慢查询数 | 连接数峰值 | CPU 峰值 |
|------------|---------|-----------|---------|
| **4/16 04:00** | **1,910** | **214** | **86.3%** |
| 4/15 06:00 | 661 | 199 | 85.3% |
| 4/15 17:00 | 626 | 154 | 19.4% |
| 4/14 12:00 | 466 | 170 | 18.5% |
| 4/15 04:00 | 253 | 201 | 84.0% |
| 4/14 17:00 | 250 | 159 | 9.6% |
| 4/15 10:00 | 179 | 111 | 63.5% |
| 4/16 12:00 | 137 | 110 | 11.7% |
| 4/16 13:00 | 118 | 110 | 11.2% |
| 4/14 15:00 | 106 | 152 | 10.7% |

**结论：连接数升高与慢查询强相关。** 慢查询期间写操作排队，连接无法及时释放，导致堆积。

### 3.3 慢查询根因

#### 类型一：每日凌晨批量 DELETE（最大影响）

```sql
-- 用户: isalesmktingadm_A_w
-- 执行时段: 每天 ~04:00-06:00 UTC (00:00-02:00 EST)
-- 影响: CPU 飙升至 80%+，所有并发写入变慢

DELETE FROM t_user_event WHERE id <= 394360093;
-- Query_time: 1.1~1.6s
-- Rows_examined: 5000
-- Lock_time: ~0.000003s
```

每天凌晨的定时清理任务批量删除 `t_user_event` 表中的过期数据。单次删除 5000 行，执行时间 1.1~1.6 秒。该操作触发大量磁盘 I/O，CPU 飙到 80%+，导致同时段所有 INSERT 操作延迟升高、连接堆积。

#### 类型二：高频 INSERT 到 t_user_event_track（持续影响）

```sql
-- 用户: icdprealtimeuge_A_w
-- 执行时段: 全天持续，业务高峰期加剧
-- 来源 IP: 10.238.33.81, 10.238.40.123, 10.238.44.167, 10.238.45.23, 10.238.46.111

INSERT INTO t_user_event_track (user_no, event_type, event_name, ...) VALUES (...);
-- Query_time: 0.4~0.6s
-- Lock_time: ~0.000002s (几乎无锁等待)
-- Rows_examined: 0
```

实时用户行为事件写入，正常时段耗时 0.4-0.6s 超过 0.1s 的慢查询阈值。业务高峰时并发写入密集，多个 INSERT 同时处于执行状态导致连接数升高。

#### 类型三：t_user_state 单行 DELETE

```sql
-- 用户: icdprealtimeuge_A_w
-- 执行时段: 凌晨批量 DELETE 期间

DELETE FROM t_user_state WHERE user_no = '...' AND event_type = 6 AND tenant = 'LKUS';
-- Query_time: 0.4~0.5s
-- Rows_examined: 1
```

单行删除本身不慢，但受凌晨批量 DELETE 的 I/O 压力影响，执行时间被拉长。

## 4. 表碎片分析

| 表名 | 行数 | 数据 (MB) | 索引 (MB) | 碎片空间 (MB) | 碎片率 |
|------|------|----------|----------|-------------|--------|
| t_user_state | 1,104,376 | 258.4 | 88.4 | 10.0 | 2.9% (正常) |
| t_user_event_track | 132,449 | 27.1 | 10.0 | 87.0 | **234.4%** |
| t_user_event | 23,734 | 3.5 | 9.0 | 126.0 | **1005.5%** |

`t_user_event` 实际数据仅 3.5MB 但碎片空间高达 126MB，碎片率超过 1000%。`t_user_event_track` 碎片率也达到 234%。这是频繁 DELETE + INSERT 操作的典型后果，高碎片会：
- 降低顺序写入性能
- 浪费 InnoDB buffer pool 内存
- 增加全表扫描和范围查询的 I/O

## 5. 当前连接分布

| 用户 | 连接数 | 说明 |
|------|--------|------|
| icdprealtimeuge_A_o | 56 | CDP 实时引擎 (只读) |
| icdprealtimeuge_A_w | 38 | CDP 实时引擎 (读写) |
| isalesmktingadm_A_w | 4 | 营销管理后台 (读写) |
| rdsadmin | 2 | RDS 管理进程 |
| datalink_canal | 2 | Canal 数据同步 |
| diagtools | 1 | 诊断工具 |
| event_scheduler | 1 | 事件调度器 |

94 个连接处于 Sleep 状态，当前无活跃慢查询。

## 6. 建议

### 6.1 [高优先级] 优化批量 DELETE 任务

将凌晨的批量 DELETE 改为小批次执行，避免一次性大量删除导致 CPU 飙升：

```sql
-- 建议改为：每次删除 500 行，循环执行，间隔 0.5-1 秒
REPEAT
  DELETE FROM t_user_event WHERE id <= {target_id} LIMIT 500;
  SELECT SLEEP(0.5);
UNTIL ROW_COUNT() = 0
```

或通过应用层控制循环频率。预期效果：消除凌晨 CPU 80%+ 的尖峰，避免写入堆积。

### 6.2 [高优先级] 整理表碎片

在低峰期（UTC 07:00-09:00 / EST 02:00-04:00）执行：

```sql
-- 推荐使用 pt-online-schema-change 避免锁表
-- 或在低峰期直接执行（表较小，影响有限）：
ALTER TABLE t_user_event ENGINE=InnoDB;        -- 回收 ~126MB
ALTER TABLE t_user_event_track ENGINE=InnoDB;   -- 回收 ~87MB
```

### 6.3 [中优先级] 调高慢查询阈值

当前 long_query_time = 0.1s 过低，大量正常业务 INSERT（0.4-0.6s）都被记为慢查询，产生噪音。建议：

```sql
-- 调整为 0.5s 或 1s，聚焦真正异常的查询
SET GLOBAL long_query_time = 1.0;
-- 同步修改 RDS 参数组以持久化
```

### 6.4 [低优先级] 检查连接池配置

`icdprealtimeuge_A_o` 持有 56 个 Sleep 连接，`icdprealtimeuge_A_w` 持有 38 个。建议：
- 确认应用端连接池 maxIdle / minIdle 配置是否合理
- 检查连接池的 idleTimeout 和 maxLifetime 设置
- 排除连接泄露的可能性

## 7. 总结

isalescdp 实例近两天连接数偏高 **确实由慢查询导致**，核心问题是：

1. **每日凌晨批量 DELETE 任务**一次删除大量行，CPU 飙升至 80%+，所有并发写入被拖慢，连接堆积至 200+
2. **t_user_event / t_user_event_track 表碎片严重**（碎片率 234%~1005%），进一步影响写入性能
3. 慢查询阈值 0.1s 过低，正常业务写入也被记为慢查询

优先处理批量 DELETE 优化和表碎片整理，预计可显著降低连接数峰值和 CPU 使用率。
