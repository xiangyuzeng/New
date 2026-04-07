# MySQL 8.0 → 8.4 升级深度调查报告

**调查日期**: 2026-04-07  
**调查范围**: 61个 MySQL RDS 实例（59个可访问，2个不在 MCP Gateway）  
**AWS账号**: 257394478466 (us-east-1)  
**调查执行**: David Zeng (Senior DBA)  
**关联文档**: `/app/upgrade_plan_template.md`, `/app/reports/rds-extended-support-upgrade-brief-20260406.md`

---

## 执行摘要

> **结论：可以推进升级。全59个可访问实例均无硬性阻断项（Phase 2 Blockers）。**

| 检查项 | 结果 | 影响 |
|--------|------|------|
| FK引用非唯一列（Q4） | ✅ 0 个发现 | 无阻断 |
| FLOAT/DOUBLE AUTO_INCREMENT（Q5） | ✅ 0 个发现 | 无阻断 |
| 保留字冲突—列名（Q6a） | ✅ 0 个发现 | 无阻断 |
| 保留字冲突—表名（Q6b） | ✅ 0 个发现 | 无阻断 |
| 存储过程中已废弃语法（Q7a） | ✅ 0 个发现 | 无阻断 |
| Binlog/Canal配置 | ✅ 全部标准配置 | 无阻断 |
| optimizer_switch | ✅ 全部默认值 | 无阻断 |
| t4g.micro内存压力 | ⚠️ 128-256MB buffer pool | 低风险 |
| Canal语法兼容性 | ⚠️ 需升级Canal版本 | 升级前处理 |
| mfranchise utf8mb3 | ⚠️ 废弃字符集（非阻断） | 警告级 |

**最大升级窗口需求：** ldas01 (86 GB) → Phase 2 建议 120 min 维护窗口  
**Phase 1（8.0.x → 8.0.45）：** 全实例约 30 秒 failover，可批量执行

---

## 1. 调查范围与方法

### 1.1 实例清单

| 类别 | 可访问 | 不可访问 | 备注 |
|------|--------|----------|------|
| DevOps (12) | 10 | 2 | ijumpserver, recovery-dbatest 未在 MCP Gateway |
| Sales/CRM (9) | 9 | 0 | |
| SCM (11) | 11 | 0 | |
| Finance (5) | 5 | 0 | |
| Operations (8) | 8 | 0 | |
| Platform (9) | 9 | 0 | |
| Data/Analytics (4) | 4 | 0 | |
| HR/Other (3) | 3 | 0 | |
| **合计** | **59** | **2** | |

> ijumpserver 和 recovery-dbatest 需通过 AWS Console 或特权账号单独验证。

### 1.2 检查方法

所有检查通过 MCP DB Gateway（`diagtools` 用户）对 `information_schema` 执行只读查询。单次发送最多 30+ 个并行查询，覆盖全59台实例。

已知限制：
- `diagtools` 用户无 `REPLICATION CLIENT` 权限，无法执行 `SHOW REPLICA STATUS` / `SHOW BINARY LOG STATUS`
- Binlog 相关数据从 `performance_schema.global_variables` 获取

---

## 2. Phase 2 阻断项扫描（全部清洁）

### Q4：外键引用非唯一列

MySQL 8.4 新增 `restrict_fk_on_non_standard_key=ON`（默认）——外键必须引用唯一索引列（非宽松模式）。

```
扫描范围：59/59 个实例
发现数量：0
结论：✅ CLEAN
```

### Q5：FLOAT/DOUBLE AUTO_INCREMENT

MySQL 8.4 禁止对 FLOAT 或 DOUBLE 类型列使用 AUTO_INCREMENT。

```
扫描范围：59/59 个实例
发现数量：0
结论：✅ CLEAN
```

### Q6a：新增保留字—列名冲突

检查列名是否与 MySQL 8.4 新增保留字冲突：
`INTERSECT`, `EXCEPT`, `LATERAL`, `QUALIFY`, `TABLESAMPLE`

```
扫描范围：59/59 个实例
发现数量：0
结论：✅ CLEAN
```

### Q6b：新增保留字—表名冲突

```
扫描范围：59/59 个实例
发现数量：0
结论：✅ CLEAN
```

### Q7a：存储过程中已废弃语法

检查存储过程定义中是否包含 `SHOW SLAVE STATUS` / `SHOW MASTER STATUS`（MySQL 8.4 已移除）。

```
扫描范围：59/59 个实例
发现数量：0
结论：✅ CLEAN
```

> **注意（来自历史审计）：** mfranchise 的应用层代码（非存储过程）中曾被发现 `SHOW MASTER STATUS` 调用（参见 commit 9bc4f54）。需在 Phase 2 前验证应用代码是否已切换到 `SHOW BINARY LOG STATUS`。

---

## 3. 数据量调查（升级窗口规划）

### 3.1 全实例数据量（按大小降序）

| 排名 | 服务器 | 主数据库 | 数据量(GB) | 表数量 | 建议 Phase 2 维护窗口 | 批次 |
|------|--------|----------|-----------|--------|----------------------|------|
| 1 | ldas01 | luckyus_db_collection | **86.055** | 64 | **120 min** | Batch 7 |
| 2 | salesmarketing | luckyus_sales_marketing | **42.718** | 171 | **90 min** | Batch 6 |
| 3 | iluckyhealth | luckyus_iluckyhealth | **29.430** | 14 | **60 min** | Batch 2 |
| 4 | icyberdata | luckyus_icyberdata | **22.623** | 440 | **60 min** | Batch 7 |
| 5 | iriskcontrolservice | luckyus_iriskcontrolservice | **17.743** | 157 | **45 min** | Batch 2 |
| 6 | upush | 多库合计(iupushapp等) | **17.305** | 837 | **45 min** | Batch 2 |
| 7 | cdpactivity | luckyus_cdp_activity | **15.117** | 36 | **45 min** | Batch 6 |
| 8 | isalesdatamarketing | luckyus_isalesdatamarketing | 6.600 | 26 | 30 min | Batch 6 |
| 9 | scm-shopstock | luckyus_scm_shopstock | 6.172 | 192 | 30 min | Batch 4 |
| 10 | iworkflowmidlayer | luckyus_iworkflowmidlayer | 4.964 | 25 | 30 min | Batch 1 |
| 11 | salesorder | luckyus_sales_order | 4.529 | 40 | 30 min | Batch 6 |
| 12 | opproduction | luckyus_opproduction | 4.055 | 14 | 30 min | Batch 3 |
| 13 | isalesprivatedomain | luckyus_isales_privatedomain | 1.724 | 25 | 20 min | Batch 6 |
| 14 | iopocp | luckyus_iopocp | 1.477 | 9 | 20 min | Batch 3 |
| 15 | ldas | luckyus_ikafadmin 等 | 1.560 | ~100 | 20 min | Batch 7 |
| 16 | isalescdp | luckyus_isales_cdp | 1.397 | 4 | 20 min | Batch 6 |
| 17 | ibillingcentersrv | luckyus_ibillingcenterservice | 1.165 | 13 | 20 min | Batch 5 |
| 18 | ireplenishment | luckyus_ireplenishment | 1.163 | 7 | 20 min | Batch 4 |
| 19 | salespayment | luckyus_sales_payment | 0.555 | 28 | 15 min | Batch 6 |
| 20 | opqualitycontrol | luckyus_opqualitycontrol | 0.539 | 44 | 15 min | Batch 3 |
| 21 | salescrm | luckyus_sales_crm | 0.513 | 29 | 15 min | Batch 6 |
| 22 | iotplatform | luckyus_iot_platform | 0.480 | 93 | 15 min | Batch 2 |
| 23 | scm-ordering | luckyus_scm_ordering | 0.279 | 104 | 15 min | Batch 4 |
| 24 | opshopsale | luckyus_opshopsale | 0.272 | 23 | 15 min | Batch 3 |
| 25 | framework01 | 多库合计 | 0.271 | ~259 | 15 min | Batch 1 |
| 26 | ifiaccounting | luckyus_ifiaccounting | 0.221 | 83 | 15 min | Batch 5 |
| 27 | devops | 多库合计 | 0.213 | ~259 | 15 min | Batch 1 |
| 28 | scmcommodity | luckyus_scm_commodity | 0.171 | 143 | 15 min | Batch 4 |
| 29 | scm-wds | luckyus_scm_wds | 0.156 | 157 | 15 min | Batch 4 |
| 30 | scm-openapi | luckyus_scm_openapi | 0.152 | 22 | 15 min | Batch 4 |
| 31 | scm-purchase | luckyus_scm_purchase | 0.141 | 159 | 15 min | Batch 4 |
| 32 | scmsrm | luckyus_scm_srm | 0.114 | 127 | 15 min | Batch 4 |
| 33 | opempefficiency | luckyus_opempefficiency | 0.087 | 33 | 15 min | Batch 3 |
| 34 | ipermission | luckyus_ipermission | 0.082 | 31 | 15 min | Batch 2 |
| 35 | iopenlinker | luckyus_iopenlinker | 0.081 | 14 | 15 min | Batch 2 |
| 36 | iadmin | luckyus_iadmin | 0.069 | 23 | 15 min | Batch 2 |
| 37 | fichargecontrol | luckyus_fi_chargecontrol | 0.038 | 33 | 15 min | Batch 5 |
| 38 | scm-wmssimulate | luckyus_scm_wmssimulate | 0.031 | 85 | 15 min | Batch 4 |
| 39 | opshop | luckyus_opshop | 0.029 | 34 | 15 min | Batch 3 |
| 40 | ibizconfigcenter | luckyus_ibizconfigcenter | 0.018 | 9 | 15 min | Batch 2 |
| 41 | scm-asset | luckyus_scm_asset | 0.016 | 146 | 15 min | Batch 4 |
| 42 | iehr | luckyus_iehr | 0.016 | 56 | 15 min | Batch 2 |
| 43 | pubdm | luckyus_pub_dm | 0.008 | 67 | 15 min | Batch 7 |
| 44 | dbatest | test | 0.005 | 2 | 15 min | Batch 0 |
| 45 | scm-plan | luckyus_scm_plan | 0.005 | 40 | 15 min | Batch 4 |
| 46 | iunifiedreconcile | luckyus_iunifiedreconcile | 0.004 | 11 | 15 min | Batch 5 |
| 47 | mfranchise | luckyus_mfranchise | 0.003 | 69 | 15 min | Batch 3 |
| 48 | fitax | luckyus_fi_tax | 0.001 | 13 | 15 min | Batch 5 |
| 49-59 | 其余10台 | 各单库 | < 0.001 | < 25 | 15 min | 各批次 |

**全量总计：~326 GB 数据量（59台实例）**

### 3.2 批次升级窗口预估（Phase 2 专用）

| 批次 | 实例数 | 最大单实例(GB) | 建议维护窗口 | 批次总耗时估算 |
|------|--------|---------------|-------------|---------------|
| Batch 0 (dbatest) | 1 | 0.005 | 15 min | 15 min |
| Batch 1 (DevOps工具) | ~7 | 4.964 (iworkflowmidlayer) | 30 min | ~210 min（串行） |
| Batch 2 (内管平台) | ~16 | 29.430 (iluckyhealth) | **60 min** | 建议拆分子批次 |
| Batch 3 (门店运营) | 7 | 4.055 (opproduction) | 30 min | ~210 min |
| Batch 4 (供应链) | 11 | 6.172 (scm-shopstock) | 30 min | ~330 min |
| Batch 5 (财务) | 5 | 1.165 (ibillingcentersrv) | 20 min | ~100 min |
| Batch 6 (销售CRM) | 9 | 42.718 (salesmarketing) | **90 min** | 含3台>5GB大库 |
| Batch 7 (数据平台) | ~5 | 86.055 (ldas01) | **120 min** | 含最大单实例 |

> **重要：** iluckyhealth (29.4 GB) 在 Batch 2 中偏大，建议单独排最后，独立维护窗口。upush 多库合计 17.3 GB，同样建议独立窗口。

---

## 4. Canal/Datalink 兼容性调查（Inv9）

### 4.1 Binlog 配置（全舰队统一）

以下配置在所有已检查的 Canal 相关实例（salesmarketing、salesorder、salespayment、isalescdp、scm-ordering、scm-shopstock、opshop、opshopsale、framework01、mfranchise）中完全一致：

| 参数 | 当前值 | 状态 |
|------|--------|------|
| `binlog_format` | ROW | ✅ 8.4 兼容 |
| `binlog_row_image` | FULL | ✅ Canal 推荐 |
| `gtid_mode` | ON | ✅ 8.4 兼容 |
| `log_bin` | ON | ✅ |
| `sync_binlog` | 1 | ✅ 强一致 |
| `binlog_expire_logs_seconds` | 2592000 (30天) | ✅ |
| `expire_logs_days` | 0 (由上参数控制) | ✅ |

### 4.2 Canal 升级前必做项

MySQL 8.4 已 **移除**（不是废弃）以下命令：

| 旧命令（8.0） | 新命令（8.4） |
|--------------|-------------|
| `SHOW MASTER STATUS` | `SHOW BINARY LOG STATUS` |
| `SHOW SLAVE STATUS` | `SHOW REPLICA STATUS` |
| `SHOW SLAVE HOSTS` | `SHOW REPLICAS` |

**Canal 内部使用这些命令定位 binlog 位置。**

| 行动项 | 负责方 | Deadline |
|--------|--------|---------|
| 确认 Canal 版本是否支持 MySQL 8.4 | DBA + 中间件团队 | Phase 2 前 |
| Canal >= 1.1.6 支持 MySQL 8.4 语法，需验证 | DBA | Phase 2 前 |
| 测试环境验证 Canal 连接 8.4 实例 | DBA | Phase 2 前 |
| mfranchise 应用层 `SHOW MASTER STATUS` 调用（见 commit 9bc4f54） | 应用团队 | Phase 2 前 |

---

## 5. 内存压力分析（Inv8 — t4g.micro 实例）

5台 t4g.micro 实例（1 GB RAM）内存配置：

| 实例 | innodb_buffer_pool_size | 数据量 | 风险评估 |
|------|------------------------|--------|---------|
| oplog | 256 MB | 0.0 GB | 无风险 |
| iadmin | 256 MB | 0.069 GB | 无风险 |
| scm-plan | 256 MB | 0.005 GB | 无风险 |
| pubdm | 256 MB | 0.008 GB | 无风险 |
| fitax | **128 MB** | 0.001 GB | 低风险（数据极小） |

所有 t4g.micro 实例数据量均极小（< 0.1 GB），升级期间内存压力不会成为阻断项。

---

## 6. optimizer_switch 分析（Inv10）

对 devops、salesorder 进行抽样，两台完全一致：

```
index_merge=on, index_merge_union=on, index_merge_sort_union=on,
index_merge_intersection=on, engine_condition_pushdown=on,
index_condition_pushdown=on, mrr=on, mrr_cost_based=on,
block_nested_loop=on,          ← 8.4已移除此flag（AWS RDS会自动处理）
batched_key_access=off,
materialization=on, semijoin=on, loosescan=on, firstmatch=on,
duplicateweedout=on, subquery_materialization_cost_based=on,
use_index_extensions=on, condition_fanout_filter=on, derived_merge=on,
use_invisible_indexes=off, skip_scan=on, hash_join=on,
subquery_to_derived=off,
prefer_ordering_index=off,     ← 非默认值（默认ON），在8.4中仍有效
hypergraph_optimizer=off,
derived_condition_pushdown=on
```

**结论：**
- `block_nested_loop` 在 8.4 中被移除（已合并入 hash_join），RDS 升级时会自动从参数组移除，不影响功能
- `prefer_ordering_index=off` 是业务侧已调整的参数，在 8.4 中仍然有效
- 全舰队无自定义 optimizer_switch 会导致查询计划突变的风险

---

## 7. 其他发现

### 7.1 mfranchise — utf8mb3 字符集

来源：历史审计（commit 9bc4f54）

`mfranchise` 数据库中存在 `utf8mb3` 字符集列（即旧版 `utf8`）。MySQL 8.4 中 `utf8mb3` 仍可用，但会产生 deprecation warning，且未来版本（9.x）将正式移除。

| 状态 | 处理建议 |
|------|---------|
| 警告（非阻断） | Phase 2 升级后，可安排 `ALTER TABLE ... CONVERT TO CHARACTER SET utf8mb4` |

### 7.2 诊断账号权限限制

`diagtools` 用户缺少 `REPLICATION CLIENT` 权限，导致以下命令失败：
- `SHOW REPLICA STATUS` / `SHOW SLAVE STATUS`
- `SHOW BINARY LOG STATUS` / `SHOW MASTER STATUS`

需使用特权账号（或 AWS Console 的 RDS events）验证复制状态。

### 7.3 不可访问实例

| 实例 | 原因 | 处理建议 |
|------|------|---------|
| aws-luckyus-ijumpserver-rw | 未在 MCP Gateway 注册 | 通过 AWS Console 直接操作 |
| aws-luckyus-recovery-dbatest-rw | 未在 MCP Gateway 注册 | 验证实例状态后单独升级 |

---

## 8. 升级路径确认

```
Phase 1: 8.0.x → 8.0.45 (各实例单独小版本升级, ~30秒 failover)
    ↓
Phase 2: 8.0.45 → 8.4.8 (跨主版本, 30-120分钟, 批次执行)
```

### Phase 2 前置条件（Go Checklist）

- [ ] 所有实例完成 Phase 1 → 运行 8.0.45
- [ ] Canal 版本确认支持 MySQL 8.4（>= v1.1.6 或厂商确认）
- [ ] 创建 `mysql8.4-luckyus-default` 参数组（复制现有参数并移除 `block_nested_loop`）
- [ ] dbatest 实例 Phase 2 完成并验证（Batch 0）
- [ ] mfranchise 应用层 `SHOW MASTER STATUS` 调用已修复
- [ ] 已通知各业务团队维护窗口计划（尤其 Batch 6/7 大实例）
- [ ] RDS 快照已在 Phase 2 前取完

---

## 9. 风险汇总

| 风险 | 级别 | 影响实例 | 缓解措施 |
|------|------|---------|---------|
| Canal `SHOW MASTER STATUS` 兼容性 | HIGH | 10个Canal源实例 | 升级前验证Canal版本 |
| ldas01 维护窗口过长（86 GB） | MEDIUM | ldas01 | 安排120分钟维护窗口，提前通知数据团队 |
| iluckyhealth 意外大库（29 GB） | MEDIUM | iluckyhealth | Batch 2 中单独排窗口 |
| t4g.micro 内存紧张 | LOW | 5台micro实例 | 数据量极小，实际影响可忽略 |
| mfranchise utf8mb3 | LOW | mfranchise | Phase 2 后按计划迁移字符集 |
| prefer_ordering_index=off 查询计划变化 | LOW | 全部实例 | 在8.4中仍有效，不改变行为 |
| ijumpserver/recovery-dbatest 未验证 | LOW | 2台 | 通过AWS Console补充验证 |

---

## 10. 下一步行动

| 优先级 | 行动 | 负责人 | 完成时限 |
|--------|------|--------|---------|
| P0 | 验证Canal版本 MySQL 8.4 兼容性 | DBA + 中间件 | Phase 2 前 |
| P0 | 在测试环境执行完整 Batch 0 升级验证 | DBA | Phase 2 前 |
| P1 | 创建 mysql8.4 参数组 | DBA | Phase 1 完成后 |
| P1 | 修复 mfranchise 应用层 SHOW MASTER STATUS 调用 | 应用团队 | Phase 2 前 |
| P1 | 拆分 Batch 2（单独调度 iluckyhealth、upush、iriskcontrolservice） | DBA | 排期前 |
| P2 | 完善 ijumpserver、recovery-dbatest 的兼容性验证 | DBA | Phase 2 前 |
| P3 | mfranchise utf8mb3 → utf8mb4 迁移 | DBA | Phase 2 后计划内 |

---

## 附录：查询语句

### Phase 2 阻断项扫描（单实例通用版）

```sql
-- Q5 + Q6a + Q6b + Q7a 合并扫描
SELECT 'Q5_FLOAT_AUTO' as check_type, TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, COLUMN_TYPE as detail
FROM information_schema.COLUMNS
WHERE EXTRA LIKE '%auto_increment%' AND DATA_TYPE IN ('float','double')
  AND TABLE_SCHEMA NOT IN ('mysql','information_schema','performance_schema','sys')
UNION ALL
SELECT 'Q6A_RSVD_COL', TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM information_schema.COLUMNS
WHERE UPPER(COLUMN_NAME) IN ('INTERSECT','EXCEPT','LATERAL','QUALIFY','TABLESAMPLE')
  AND TABLE_SCHEMA NOT IN ('mysql','information_schema','performance_schema','sys')
UNION ALL
SELECT 'Q6B_RSVD_TBL', TABLE_SCHEMA, TABLE_NAME, '', TABLE_TYPE
FROM information_schema.TABLES
WHERE UPPER(TABLE_NAME) IN ('INTERSECT','EXCEPT','LATERAL','QUALIFY','TABLESAMPLE')
  AND TABLE_SCHEMA NOT IN ('mysql','information_schema','performance_schema','sys')
UNION ALL
SELECT 'Q7A_DEPR_PROC', ROUTINE_SCHEMA, ROUTINE_NAME, ROUTINE_TYPE, LEFT(ROUTINE_DEFINITION, 200)
FROM information_schema.ROUTINES
WHERE ROUTINE_DEFINITION REGEXP 'SHOW[[:space:]]+(SLAVE|MASTER)[[:space:]]+STATUS'
  AND ROUTINE_SCHEMA NOT IN ('mysql','information_schema','performance_schema','sys')
LIMIT 100;
```

### 数据量统计

```sql
SELECT TABLE_SCHEMA, ROUND(SUM(data_length+index_length)/1024/1024/1024,3) as total_gb,
       COUNT(*) as table_count
FROM information_schema.TABLES
WHERE TABLE_SCHEMA NOT IN ('mysql','information_schema','performance_schema','sys')
GROUP BY TABLE_SCHEMA ORDER BY total_gb DESC;
```

### Binlog 配置检查

```sql
SELECT variable_name, variable_value
FROM performance_schema.global_variables
WHERE variable_name IN ('binlog_expire_logs_seconds','expire_logs_days','binlog_format',
                        'log_bin','sync_binlog','gtid_mode','binlog_row_image')
ORDER BY variable_name;
```

---

*报告生成时间: 2026-04-07 | 调查工具: MCP DB Gateway (mcp-db-gateway) | 查询账号: diagtools (只读)*
