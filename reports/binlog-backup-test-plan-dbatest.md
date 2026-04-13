# MySQL Binlog 实时拉取测试方案 — dbatest-rw

**日期**: 2026-04-13
**作者**: David Zeng (DBA Team)
**目的**: 验证 AWS RDS MySQL 通过 `mysqlbinlog` 工具实时拉取 Binlog 至 EC2 的可行性，为升级回退增量恢复提供能力储备
**实例**: aws-luckyus-dbatest-rw (8.0.45, db.t4g.micro, 20GB)

---

## 1. 背景

MySQL 8.0.40 → 8.0.45 升级过程中，RDS 不支持 minor version 回滚。回退只能通过快照恢复，但快照恢复会丢失升级后的增量数据。

通过 Binlog 实时拉取可以补充增量备份能力：

| 备份层 | 方式 | RPO |
|--------|------|-----|
| 第 1 层 | RDS 自动快照（每日） | 最多丢 24 小时 |
| 第 2 层 | 升级前手动快照 | 丢升级后所有数据 |
| **第 3 层** | **Binlog 实时拉取** | **接近零丢失** |

---

## 2. 环境信息

| 项目 | 值 |
|------|-----|
| 实例 ID | aws-luckyus-dbatest-rw |
| Endpoint | `aws-luckyus-dbatest-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com` |
| 版本 | 8.0.45 |
| 存储 | 20 GB |
| Binlog 格式 | ROW（参数组 `luckyus-prod-80-new` 配置） |
| 可用账号 | `xiangyu.zeng`（已有 REPLICATION SLAVE 权限） |
| 其他 REPL 账号 | `datalink_canal`, `dbms_deploy` |

### 前置条件

- EC2 安全组已放通到 dbatest-rw 的 3306 端口
- EC2 上已安装 `mysqlbinlog` 工具（版本 >= 8.0）
- EC2 上已安装 `mysql` 客户端

---

## 3. 测试步骤

### 步骤 1：配置 Binlog 保留

登录 dbatest-rw MySQL 客户端：

```bash
mysql -h aws-luckyus-dbatest-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com \
      -P 3306 -u xiangyu.zeng -p
```

执行：

```sql
-- 查看当前 binlog 保留配置
CALL mysql.rds_show_configuration;

-- 设置保留 24 小时（测试用，生产建议 72h）
CALL mysql.rds_set_configuration('binlog retention hours', 24);

-- 确认生效
CALL mysql.rds_show_configuration;
```

> 预期结果：`binlog retention hours` 值变为 `24`
>
> 注意：最大可设 168 小时（7 天）。Binlog 会占用实例存储空间，dbatest 有 20GB，测试期间足够。

### 步骤 2：查看当前 Binlog 文件列表

```sql
SHOW BINARY LOGS;
```

记录最后一个文件名，例如 `mysql-bin-changelog.000123`，后续步骤中用到。

### 步骤 3：在 EC2 上创建备份目录

```bash
mkdir -p /data/binlog-backup/dbatest
cd /data/binlog-backup/dbatest
```

### 步骤 4：批量下载测试（单次拉取）

```bash
# 替换 mysql-bin-changelog.000123 为步骤 2 中查到的最后一个文件名
mysqlbinlog \
    --read-from-remote-server \
    --host=aws-luckyus-dbatest-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com \
    --port=3306 \
    --user=xiangyu.zeng \
    --password \
    --raw \
    --result-file=/data/binlog-backup/dbatest/ \
    mysql-bin-changelog.000123
```

验证：

```bash
# 检查文件是否下载成功
ls -lh /data/binlog-backup/dbatest/

# 查看 binlog 内容（可读格式）
mysqlbinlog --verbose /data/binlog-backup/dbatest/mysql-bin-changelog.000123 | head -50
```

> 预期结果：文件大小 > 0，能看到 binlog 事件头信息

### 步骤 5：实时流式拉取测试

```bash
# --stop-never 模式，进程持续运行不退出
mysqlbinlog \
    --read-from-remote-server \
    --host=aws-luckyus-dbatest-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com \
    --port=3306 \
    --user=xiangyu.zeng \
    --password \
    --raw \
    --stop-never \
    --result-file=/data/binlog-backup/dbatest/ \
    mysql-bin-changelog.000123
```

> 预期结果：进程保持运行状态，不退出。后续新产生的 binlog 会自动拉取到本地。

### 步骤 6：制造测试数据验证增量捕获

**另开一个终端**，连接 dbatest 执行写操作：

```sql
-- 创建测试库和表
CREATE DATABASE IF NOT EXISTS binlog_test;
USE binlog_test;

CREATE TABLE test_binlog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    msg VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入测试数据
INSERT INTO test_binlog (msg) VALUES ('hello binlog 1');
INSERT INTO test_binlog (msg) VALUES ('hello binlog 2');
INSERT INTO test_binlog (msg) VALUES ('hello binlog 3');

-- 更新一条
UPDATE test_binlog SET msg = 'updated binlog 1' WHERE id = 1;

-- 删除一条
DELETE FROM test_binlog WHERE id = 2;

-- 确认当前数据
SELECT * FROM test_binlog;
```

> 预期结果：表中剩余 id=1（updated）和 id=3 两条记录

### 步骤 7：验证 Binlog 捕获结果

回到运行 `--stop-never` 的 EC2 终端，**另开窗口**检查：

```bash
# 查看最新拉取的文件
ls -lht /data/binlog-backup/dbatest/

# 解析 binlog，搜索测试数据
mysqlbinlog --verbose /data/binlog-backup/dbatest/mysql-bin-changelog.* \
    | grep -A5 'binlog_test'
```

> 预期结果：能看到 `CREATE TABLE`、`INSERT`、`UPDATE`、`DELETE` 对应的 ROW 事件

### 步骤 8：模拟恢复验证（可选进阶）

```sql
-- 在 dbatest 上删除测试表
DROP TABLE binlog_test.test_binlog;

-- 确认已删除
SELECT * FROM binlog_test.test_binlog;
-- 预期报错: Table doesn't exist
```

用 binlog 回放恢复：

```bash
mysqlbinlog /data/binlog-backup/dbatest/mysql-bin-changelog.* \
    --database=binlog_test \
    | mysql -h aws-luckyus-dbatest-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com \
            -P 3306 -u xiangyu.zeng -p
```

验证恢复结果：

```sql
SELECT * FROM binlog_test.test_binlog;
```

> 预期结果：数据恢复，id=1（msg='updated binlog 1'）和 id=3（msg='hello binlog 3'）

---

## 4. 清理

```bash
# 1. 停止 --stop-never 进程（Ctrl+C）

# 2. 清理 EC2 上的测试文件
rm -rf /data/binlog-backup/dbatest/
```

```sql
-- 3. 清理测试数据库
DROP DATABASE IF EXISTS binlog_test;

-- 4. 恢复 binlog 保留为默认值（可选，如需保留则跳过）
CALL mysql.rds_set_configuration('binlog retention hours', NULL);
```

---

## 5. 验证 Checklist

| # | 验证项 | 预期结果 | 实际结果 | 通过 |
|---|--------|---------|---------|------|
| 1 | `rds_set_configuration` 设置 binlog 保留 | binlog retention hours = 24 | | |
| 2 | `SHOW BINARY LOGS` 列出文件 | 返回 binlog 文件列表 | | |
| 3 | 批量下载单个 binlog 文件 | 文件大小 > 0，可解析 | | |
| 4 | `--stop-never` 流式模式启动 | 进程持续运行不退出 | | |
| 5 | 写入测试数据后检查本地文件 | 新 binlog 自动拉取到本地 | | |
| 6 | 解析 binlog 内容 | 能看到 INSERT/UPDATE/DELETE 事件 | | |
| 7 | Binlog 回放恢复数据（可选） | DROP 后数据成功恢复 | | |

---

## 6. 生产部署建议（测试通过后）

### 6.1 进程管理

`--stop-never` 模式需要常驻进程，建议用 systemd 管理：

```ini
# /etc/systemd/system/binlog-backup@.service
[Unit]
Description=MySQL Binlog Backup for %i
After=network.target

[Service]
Type=simple
User=mysql-backup
ExecStart=/usr/bin/mysqlbinlog \
    --read-from-remote-server \
    --host=%i.cxwu08m2qypw.us-east-1.rds.amazonaws.com \
    --port=3306 \
    --user=repl_backup \
    --password=xxx \
    --raw \
    --stop-never \
    --result-file=/data/binlog-backup/%i/
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

```bash
# 启动
systemctl enable --now binlog-backup@aws-luckyus-salesorder-rw

# 查看状态
systemctl status binlog-backup@aws-luckyus-salesorder-rw
```

### 6.2 Binlog 保留时间建议

| 场景 | 保留时间 | 说明 |
|------|---------|------|
| 升级窗口期间 | 72h | 升级前设置，确认稳定后可调低 |
| 日常增量备份 | 24h | 配合每日快照，覆盖两个快照周期 |
| 不使用 | NULL | 恢复默认，binlog 尽快清除节省空间 |

### 6.3 监控项

| 监控项 | 方法 | 告警条件 |
|--------|------|---------|
| 拉取进程存活 | systemd + CloudWatch Agent | 进程退出时告警 |
| 本地磁盘空间 | `df -h /data/binlog-backup/` | 使用率 > 80% |
| RDS 存储空间 | CloudWatch `FreeStorageSpace` | 因 binlog 保留导致空间下降 |
| Binlog 连续性 | 检查文件编号是否连续 | 编号跳跃说明有缺失 |

### 6.4 优先部署实例（升级相关）

仅需对核心业务实例部署，非所有 62 个：

| 优先级 | 实例 | 原因 |
|--------|------|------|
| P0 | salesorder-rw, salespayment-rw | 订单/支付，数据不可丢失 |
| P0 | framework01-rw, framework02-rw | 核心框架 |
| P1 | salescrm-rw, salesmarketing-rw | CRM/营销 |
| P1 | scm-ordering-rw, scm-shopstock-rw | 供应链核心 |
| P2 | 其余实例 | 快照恢复即可，无需 binlog 备份 |

---

*报告生成工具: Claude Code (Opus 4.6)*
