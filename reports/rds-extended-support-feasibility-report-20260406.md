# RDS Extended Support 可行性调查报告

**调查日期**: 2026-04-06
**调查人**: 曾翔宇 (David Zeng) — Senior DBA / Infrastructure Engineer
**审阅人**: 沙文强
**AWS 账户**: 257394478466 (us-east-1)
**背景**: 沙文强 2026-04-04 内部 wiki 指出 "All AWS RDS Extended Support is currently NOT enabled, and cannot be modified." — 本报告通过 AWS CLI 和官方文档验证此结论，并评估选项D (Extended Support) 的可行性。

---

## 一、实例 Extended Support 注册状态

### 1.1 全量查询结果

通过 `aws rds describe-db-instances` 查询全部 61 个 MySQL RDS 实例的 `EngineLifecycleSupport` 字段：

| # | 实例标识 | 版本 | 实例类型 | vCPU | Extended Support 状态 | 自动小版本升级 |
|---|---------|------|---------|------|---------------------|-------------|
| 1 | `aws-luckyus-cdpactivity-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 2 | `aws-luckyus-dbatest-rw` | 8.0.42 | db.t4g.micro | 2 | 已禁用 | 否 |
| 3 | `aws-luckyus-devops-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 4 | `aws-luckyus-fichargecontrol-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 5 | `aws-luckyus-fitax-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 6 | `aws-luckyus-framework01-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 7 | `aws-luckyus-framework02-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 8 | `aws-luckyus-iadmin-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 9 | `aws-luckyus-ibillingcentersrv-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 10 | `aws-luckyus-ibizconfigcenter-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 11 | `aws-luckyus-icyberdata-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 12 | `aws-luckyus-iehr-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 13 | `aws-luckyus-ifiaccounting-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 14 | `aws-luckyus-igers-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 15 | `aws-luckyus-ijumpserver-jumpserver-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 16 | `aws-luckyus-ilsopdevopsdata-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 17 | `aws-luckyus-iluckyams-rw` | 8.0.44 | db.t4g.micro | 2 | 已禁用 | 是 |
| 18 | `aws-luckyus-iluckyauthapi-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 19 | `aws-luckyus-iluckydorisops-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 20 | `aws-luckyus-iluckyhealth-rw` | 8.0.40 | db.t3.small | 2 | 已禁用 | 否 |
| 21 | `aws-luckyus-iluckymedia-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 22 | `aws-luckyus-iopenadmin-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 23 | `aws-luckyus-iopenlinker-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 24 | `aws-luckyus-iopenservice-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 25 | `aws-luckyus-iopocp-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 26 | `aws-luckyus-iopshopexpand-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 27 | `aws-luckyus-iotplatform-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 28 | `aws-luckyus-ipermission-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 29 | `aws-luckyus-ireplenishment-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 30 | `aws-luckyus-iriskcontrolservice-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 31 | `aws-luckyus-isalescdp-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 32 | `aws-luckyus-isalesdatamarketing-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 33 | `aws-luckyus-isalesmembermarketing-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 34 | `aws-luckyus-isalesprivatedomain-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 35 | `aws-luckyus-iunifiedreconcile-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 36 | `aws-luckyus-iworkflowmidlayer-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 37 | `aws-luckyus-ldas-rw` | 8.0.40 | db.t4g.large | 2 | 已禁用 | 否 |
| 38 | `aws-luckyus-ldas01-rw` | 8.0.41 | db.t4g.large | 2 | 已禁用 | 否 |
| 39 | `aws-luckyus-mfranchise-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 40 | `aws-luckyus-opempefficiency-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 41 | `aws-luckyus-oplog-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 42 | `aws-luckyus-opproduction-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 43 | `aws-luckyus-opqualitycontrol-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 44 | `aws-luckyus-opshop-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 45 | `aws-luckyus-opshopsale-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 46 | `aws-luckyus-pubdm-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 47 | `aws-luckyus-salescrm-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 48 | `aws-luckyus-salesmarketing-rw` | 8.0.40 | db.t4g.xlarge | 4 | 已禁用 | 否 |
| 49 | `aws-luckyus-salesorder-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 50 | `aws-luckyus-salespayment-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 51 | `aws-luckyus-scm-asset-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 52 | `aws-luckyus-scm-openapi-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 53 | `aws-luckyus-scm-ordering-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 54 | `aws-luckyus-scm-plan-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 55 | `aws-luckyus-scm-purchase-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 56 | `aws-luckyus-scm-shopstock-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 57 | `aws-luckyus-scm-wds-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 58 | `aws-luckyus-scm-wmssimulate-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 59 | `aws-luckyus-scmcommodity-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |
| 60 | `aws-luckyus-scmsrm-rw` | 8.0.40 | db.t4g.micro | 2 | 已禁用 | 否 |
| 61 | `aws-luckyus-upush-rw` | 8.0.40 | db.t4g.medium | 2 | 已禁用 | 否 |

### 1.2 汇总统计

| 项目 | 数量 |
|------|------|
| MySQL 实例总数 | 61 |
| Extended Support **已启用** | **0** |
| Extended Support **已禁用** | **61 (100%)** |
| 总 vCPU 数 | 124 |

**版本分布**:
| 版本 | 数量 |
|------|------|
| 8.0.40 | 58 |
| 8.0.41 | 1 |
| 8.0.42 | 1 |
| 8.0.44 | 1 |

**实例类型分布**:
| 实例类型 | 数量 | 单实例 vCPU |
|---------|------|-----------|
| db.t4g.micro | 40 | 2 |
| db.t4g.medium | 17 | 2 |
| db.t4g.large | 2 | 2 |
| db.t4g.xlarge | 1 | 4 |
| db.t3.small | 1 | 2 |

---

## 二、关键发现

### 2.1 EngineLifecycleSupport 字段确认存在

所有 61 个实例均返回 `EngineLifecycleSupport` 字段，值为：

```
"EngineLifecycleSupport": "open-source-rds-extended-support-disabled"
```

验证方式 — 对 5 个不同类型的代表性实例执行详细查询：

```bash
aws rds describe-db-instances --db-instance-identifier <ID> --region us-east-1 \
  --query 'DBInstances[0].{Id:DBInstanceIdentifier,EngineLifecycleSupport:EngineLifecycleSupport}'
```

| 实例 | 版本 | 类型 | EngineLifecycleSupport |
|------|------|------|----------------------|
| aws-luckyus-dbatest-rw | 8.0.42 | db.t4g.micro | `open-source-rds-extended-support-disabled` |
| aws-luckyus-devops-rw | 8.0.40 | db.t4g.medium | `open-source-rds-extended-support-disabled` |
| aws-luckyus-ldas01-rw | 8.0.41 | db.t4g.large | `open-source-rds-extended-support-disabled` |
| aws-luckyus-salesmarketing-rw | 8.0.40 | db.t4g.xlarge | `open-source-rds-extended-support-disabled` |
| aws-luckyus-iluckyams-rw | 8.0.44 | db.t4g.micro | `open-source-rds-extended-support-disabled` |

**结论**: 所有实例均未启用 Extended Support。

### 2.2 EngineLifecycleSupport 无法在现有实例上修改

**证据 1 — ModifyDBInstance API 不包含此参数**

查阅 AWS 官方 API 文档 ([ModifyDBInstance](https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_ModifyDBInstance.html))，`ModifyDBInstance` 的可修改参数列表中 **不包含** `EngineLifecycleSupport`。该参数仅在以下 API 中可设置：
- `CreateDBInstance` (创建时)
- `RestoreDBInstanceFromDBSnapshot` (从快照恢复时)
- `RestoreDBInstanceToPointInTime` (时间点恢复时)

**证据 2 — DescribeValidDBInstanceModifications 无此字段**

```bash
aws rds describe-valid-db-instance-modifications \
  --db-instance-identifier aws-luckyus-dbatest-rw --region us-east-1
```

返回结果仅包含存储相关的可修改选项（StorageType, StorageSize, ProvisionedIops），**无 EngineLifecycleSupport 相关内容**。

**证据 3 — AWS 官方文档明确说明**

> 来源: [Creating a DB instance with RDS Extended Support](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/extended-support-creating-db-instance.html)
>
> EngineLifecycleSupport 仅在 **创建** 或 **恢复** 实例时可设置。

**结论**: 沙文强的判断完全正确 — Extended Support 当前未启用，且**无法通过修改现有实例来启用**。

### 2.3 Extended Support 禁用后的 AWS 行为（核心问题）

根据 AWS 官方文档 ([extended-support-creating-db-instance.html](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/extended-support-creating-db-instance.html))：

| Extended Support 状态 | 标准支持结束后的行为 |
|----------------------|-------------------|
| **已启用** (`open-source-rds-extended-support`) | AWS 收取 Extended Support 费用，实例继续运行当前版本 |
| **已禁用** (`open-source-rds-extended-support-disabled`) | **AWS 将自动升级实例到受支持的引擎版本。此升级将在标准支持结束日期当天或之后不久执行。** |

> 原文: "Amazon RDS upgrades your DB instance or Multi-AZ DB cluster to a supported engine version. This upgrade takes place on or shortly after the RDS end of standard support date."

补充说明 ([extended-support-overview.html](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/extended-support-overview.html)):

> "After the RDS end of standard support date, if you didn't disable RDS Extended Support during the creation or restoration of your DB instances, then Amazon RDS will automatically enroll them in RDS Extended Support."

**这意味着**: 只有在创建/恢复时**没有主动禁用**的实例，才会被自动注册到 Extended Support。我们的实例在创建时被设置为 `disabled`（可能是创建时的默认值或明确设置），因此**不会被自动注册，而是会被强制升级**。

### 2.4 强制升级的目标版本

当前可用的升级路径：

```
8.0.40 → 8.0.41, 8.0.42, 8.0.43, 8.0.44, 8.0.45, 8.4.3, 8.4.4, 8.4.5, 8.4.6, 8.4.7, 8.4.8
8.0.45 → 8.4.3, 8.4.4, 8.4.5, 8.4.6, 8.4.7, 8.4.8
```

AWS 文档指出强制升级会升到**受支持的引擎版本 (supported engine version)**。MySQL 8.0 标准支持结束后，8.0.x 系列将不再是"受支持版本"，因此 AWS 大概率会将实例直接升级到 **MySQL 8.4.x**（当前最新: 8.4.8）。

### 2.4.1 小版本支持截止日期（重要补充）

根据 AWS 官方版本日历，各小版本的标准支持截止日期**不同于**大版本的 July 31, 2026：

| 小版本 | 实例数 | 小版本标准支持截止 | 距今天数 |
|--------|-------|-------------------|---------|
| **8.0.40** | **58** | **2026-05-31** | **55天** |
| **8.0.41** | **1** | **2026-05-31** | **55天** |
| 8.0.42 | 1 | 2026-07-31 | 116天 |
| 8.0.44 | 1 | 2026-07-31 | 116天 |

**关键影响**: 59/61 实例 (96.7%) 运行的小版本将在 **2026-05-31** 停止接收安全补丁，比大版本 ES 强制升级日期 (2026-07-31) 早**两个月**。这意味着：
- 如果不执行小版本升级 (Option B)，从 2026-06-01 到 2026-07-31 将有**两个月的安全补丁空窗期**
- 这使得 Option B（升级到 8.0.45）的紧迫性从 "7月底前" 提前到 **"5月底前"**
- 注意: ES 强制升级行为仍然由大版本日期 (July 31, 2026) 触发，小版本截止日期不影响 ES 行为

### 2.5 AWS Health 事件（无法访问）

```bash
aws health describe-events --filter '{"eventTypeCategories":["scheduledChange"],"services":["RDS"]}'
# ERROR: AccessDeniedException — IAM user databasecheck 无 health:DescribeEvents 权限
```

建议向 Michael 申请 `health:DescribeEvents` 权限，以获取 AWS 关于 MySQL 8.0 EOL 的具体通知内容和时间表。

---

## 三、选项D可行性结论

### 结论: 有条件可行 (CONDITIONAL) — 但不建议

**当前状态下不可行**。所有 61 个实例的 Extended Support 均为 `disabled`，且**无法直接修改**。

**如果仍要启用 Extended Support**，唯一的途径是：

1. 对每个实例创建手动快照
2. 从快照恢复为新实例，并在恢复时指定 `--engine-lifecycle-support open-source-rds-extended-support`
3. 将应用连接切换到新实例（新的 endpoint）
4. 删除旧实例

**这等同于重建全部 61 个实例**，涉及：
- 61 次快照 + 恢复操作
- 61 个实例的 endpoint 变更
- 所有应用连接字符串更新
- DNS/服务发现配置更新
- 参数组、安全组、标签等重新配置
- 预计停机时间：每实例 30-60 分钟（含验证）
- 总工作量：约 2-3 周（含测试验证）

**即使成功启用，Extended Support 成本估算**：

| 期间 | vCPU/小时费率 | 月成本 | 年成本 |
|------|------------|--------|--------|
| 第1年 (2026-08 ~ 2027-07) | $0.10 | $9,052 | $108,624 |
| 第2年 (2027-08 ~ 2028-07) | $0.10 | $9,052 | $108,624 |
| 第3年 (2028-08 ~ 2029-07) | $0.20 | $18,104 | $217,248 |
| **3年总计** | | | **$434,496** |

> 计算公式: 124 vCPU × $0.10/vCPU/hr × 730 hr/month = $9,052/月 (第1-2年)
> 应用 EDP 31% 折扣后: 124 × $0.10 × 730 × 0.69 = **$6,246/月** (第1-2年), **$12,492/月** (第3年)
> EDP 折扣后3年总计: **~$299,802**

---

## 四、与其他选项的对比建议

| 维度 | 选项B: 小版本升级 (→8.0.45) | 选项C: 大版本升级 (→8.4.8 LTS) | 选项D: Extended Support |
|------|------------------------|--------------------------|----------------------|
| **升级难度** | 低 — ~30秒停机 | 中 — ~10分钟 + 故障切换 | 高 — 61个实例重建 |
| **风险** | 极低 | 中 — 需认证插件迁移 | 低（重建后）|
| **费用** | $0 | $0 | $300K~$434K (3年) |
| **解决期限** | 临时 — 仍在8.0 EOL范围内 | 永久 — 8.4 LTS 标准支持至2029+ | 临时 — 延后3年 |
| **工作量** | 1-2周 | 3-5周 | 2-3周（重建）+ 持续费用 |
| **不操作的后果** | 8.0.40/41: 2026-05-31 起无安全补丁；2026-07-31 后全部被强制升级到8.4.x | N/A | 无法启用 — 被强制升级 |

### 建议方案（下周二会议讨论）

**推荐: 选项 B → C 分阶段升级**

1. **立即执行选项B** (2周内，**5月31日前必须完成**): 将全部 61 个实例从 8.0.40/41/42/44 升级到 **8.0.45**
   - 风险极低，停机约30秒/实例
   - **紧迫原因**: 59/61 实例的小版本 (8.0.40/41) 将于 2026-05-31 停止安全补丁
   - 确保所有实例处于 8.0 系列最新版本
   - 为选项C做好准备

2. **随后执行选项C** (4周内): 从 8.0.45 升级到 **8.4.8 LTS**
   - 分 8 批次按业务风险递进
   - 提前完成 `mysql_native_password` → `caching_sha2_password` 认证迁移
   - 使用 Blue/Green 部署实现零停机

3. **不建议选项D**:
   - 需要重建全部实例，工作量与直接升级相当
   - 3年额外成本 $300K-$434K
   - 仅延后问题，最终仍需升级
   - 不如把同样的精力投入到一步到位的 8.4.8 升级

### 不操作的风险

如果我们什么都不做：
- **2026-07-31 后**，AWS 将在其选择的时间**不受控制地**将全部 61 个实例强制升级到 MySQL 8.4.x
- 升级时间由 AWS 决定，无法预期
- 可能导致应用兼容性问题（特别是 `mysql_native_password` 认证插件在 8.4 中被移除）
- 可能在业务高峰期发生
- **这是最差的选择**

---

## 五、原始 CLI 输出摘要

### 5.1 全量实例 Extended Support 状态查询

```bash
aws rds describe-db-instances \
  --query 'DBInstances[?Engine==`mysql`].[DBInstanceIdentifier,EngineVersion,DBInstanceClass,EngineLifecycleSupport,AutoMinorVersionUpgrade]' \
  --output json --region us-east-1
```

**结果**: 61个实例全部返回 `"open-source-rds-extended-support-disabled"`。已启用: 0，已禁用: 61。

### 5.2 代表性实例详细查询示例

```bash
aws rds describe-db-instances --db-instance-identifier aws-luckyus-dbatest-rw --region us-east-1 \
  --query 'DBInstances[0].{Id:DBInstanceIdentifier,Version:EngineVersion,Class:DBInstanceClass,
           AutoMinorUpgrade:AutoMinorVersionUpgrade,EngineLifecycleSupport:EngineLifecycleSupport}'
```

```json
{
    "Id": "aws-luckyus-dbatest-rw",
    "Version": "8.0.42",
    "Class": "db.t4g.micro",
    "AutoMinorUpgrade": false,
    "EngineLifecycleSupport": "open-source-rds-extended-support-disabled"
}
```

### 5.3 引擎版本升级路径查询

```bash
aws rds describe-db-engine-versions --engine mysql --engine-version 8.0.40 --region us-east-1 \
  --query 'DBEngineVersions[0].ValidUpgradeTarget[*].EngineVersion'
```

```json
["8.0.41", "8.0.42", "8.0.43", "8.0.44", "8.0.45", "8.4.3", "8.4.4", "8.4.5", "8.4.6", "8.4.7", "8.4.8"]
```

### 5.4 可用 MySQL 8.4 版本

```
8.4.3  — available
8.4.4  — available
8.4.5  — available
8.4.6  — available
8.4.7  — available
8.4.8  — available
```

### 5.5 ModifyDBInstance API 验证

通过 `DescribeValidDBInstanceModifications` 查询可修改项，返回结果仅包含存储相关参数（StorageType, StorageSize, ProvisionedIops 等），**不包含 EngineLifecycleSupport**。

AWS API 文档确认 `ModifyDBInstance` 的参数列表中**无 EngineLifecycleSupport 选项**。

### 5.6 快照可用性

最近的自动快照（2026-04-06）：

```
rds:aws-luckyus-iluckyhealth-rw-2026-04-06-09-34   | 8.0.40 | available
rds:aws-luckyus-scm-openapi-rw-2026-04-06-09-42    | 8.0.40 | available
rds:aws-luckyus-scm-plan-rw-2026-04-06-10-14       | 8.0.40 | available
rds:aws-luckyus-framework01-rw-2026-04-06-10-23    | 8.0.40 | available
rds:aws-luckyus-oplog-rw-2026-04-06-10-27          | 8.0.40 | available
```

自动快照每日创建中，如需执行快照恢复方案（选项D），快照数据是可用的。

---

## 六、AWS 官方文档引用

| 文档 | URL | 关键信息 |
|------|-----|---------|
| Extended Support 概述 | [extended-support-overview.html](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/extended-support-overview.html) | 未禁用ES的实例会自动注册；已禁用的不会 |
| 创建实例与ES | [extended-support-creating-db-instance.html](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/extended-support-creating-db-instance.html) | ES禁用 → 强制升级；ES启用 → 收费 |
| ES费用说明 | [extended-support-charges.html](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/extended-support-charges.html) | 避免费用的方式：禁用ES + 升级 |
| 责任说明 | [extended-support-responsibilities.html](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/extended-support-responsibilities.html) | ES到期后不升级 → AWS可能删除实例（保留数据） |
| ModifyDBInstance API | [API_ModifyDBInstance.html](https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_ModifyDBInstance.html) | 可修改参数中无 EngineLifecycleSupport |

---

**报告结束**

*本报告基于 2026-04-06 的 AWS CLI 查询结果和 AWS 官方文档。建议在下周二会议前转发给相关决策人员审阅。*
