# AWS IAM 权限申请表

| 项目 | 内容 |
|------|------|
| **申请人** | 曾翔宇 (David Zeng) |
| **职位** | Senior DBA / Infrastructure Engineer |
| **申请日期** | 2026-04-03 |
| **AWS Account** | 257394478466 |
| **Region** | us-east-1 |
| **申请用户名** | _(待填写)_ |
| **访问方式** | Console + Programmatic (Access Key) |
| **权限级别** | 只读（Read-Only） |

---

## 权限清单

### 一、核心数据库服务

| # | AWS 服务 | 权限 (Policy) | 申请目的 |
|---|---------|---------------|----------|
| 1 | RDS | AmazonRDSReadOnlyAccess | 查看 62 个 MySQL 和 3 个 PostgreSQL 实例的状态、事件、慢查询日志 |
| 2 | RDS Performance Insights | pi:Get*, pi:List*, pi:Describe* | 数据库性能分析，定位慢查询和等待事件 |
| 3 | ElastiCache | AmazonElastiCacheReadOnlyAccess | 查看 78 个 Redis 集群的节点状态、内存使用、参数配置 |
| 4 | DocumentDB | AmazonDocDBReadOnlyAccess | 查看 4 个 DocumentDB 实例的集群健康和事件 |
| 5 | OpenSearch | AmazonOpenSearchServiceReadOnlyAccess | 查看 2 个 OpenSearch 集群的域状态和索引健康 |
| 6 | Redshift Serverless | AmazonRedshiftReadOnlyAccess | 查看数据仓库工作组，执行分析查询 |

### 二、计算与容器

| # | AWS 服务 | 权限 (Policy) | 申请目的 |
|---|---------|---------------|----------|
| 7 | EC2 | AmazonEC2ReadOnlyAccess | 查看 233 个实例状态、安全组、VPC 网络配置 |
| 8 | EKS | AmazonEKSReadOnlyAccess | 查看 3 个 K8s 集群状态，排查 exporter Pod 异常 |
| 9 | ECR | AmazonEC2ContainerRegistryReadOnly | 查看容器镜像版本信息 |

### 三、数据处理与分析

| # | AWS 服务 | 权限 (Policy) | 申请目的 |
|---|---------|---------------|----------|
| 10 | S3 | AmazonS3ReadOnlyAccess | 查看数据湖文件、Glue ETL 脚本、数据库备份 |
| 11 | Glue | glue:Get*, glue:List*, glue:BatchGet* | 查看 Data Catalog、ETL 作业运行状态、Crawler 配置 |
| 12 | Athena | AmazonAthenaReadOnlyAccess | 执行 Cost & Usage Report 查询和数据分析 |
| 13 | MSK (Kafka) | AmazonMSKReadOnlyAccess | 查看 2 个 Kafka 集群的健康状态和 308 个 topic 配置 |
| 14 | EMR | AmazonEMRReadOnlyAccessPolicy_v2 | 查看数据处理集群状态 |

### 四、监控与运维

| # | AWS 服务 | 权限 (Policy) | 申请目的 |
|---|---------|---------------|----------|
| 15 | CloudWatch | CloudWatchReadOnlyAccess | 查看 100+ 日志组的指标、日志、告警（日常最高频使用） |
| 16 | SNS | AmazonSNSReadOnlyAccess | 查看告警通知渠道配置 |
| 17 | EventBridge | AmazonEventBridgeReadOnlyAccess | 查看事件规则和定时任务配置 |
| 18 | SSM Parameter Store | AmazonSSMReadOnlyAccess | 查看应用配置参数 |
| 19 | CloudFormation | AWSCloudFormationReadOnlyAccess | 查看 EKS 基础设施堆栈状态 |

### 五、安全与密钥

| # | AWS 服务 | 权限 (Policy) | 申请目的 |
|---|---------|---------------|----------|
| 20 | Secrets Manager | secretsmanager:Get*, List*, Describe* | 查看数据库连接密钥、API Key 等配置信息 |
| 21 | IAM (查看) | iam:Get*, iam:List* (只读) | 查看角色和策略配置，排查权限问题 |

### 六、成本与计费

| # | AWS 服务 | 权限 (Policy) | 申请目的 |
|---|---------|---------------|----------|
| 22 | Cost Explorer / Budgets | AWSBillingReadOnlyAccess | 月度费用分析和预算监控（当前月支出约 $49,645） |
| 23 | Compute Optimizer | ComputeOptimizerReadOnlyAccess | 获取 EC2/Lambda 资源优化建议 |
| 24 | Cost Optimization Hub | cost-optimization-hub:Get*, List* | 查看统一成本优化建议 |
| 25 | Pricing API | pricing:Get*, Describe*, List* | 查询 AWS 服务价格用于成本估算 |

---

## 权限汇总

| 类别 | 服务数量 | 权限级别 |
|------|---------|----------|
| 核心数据库 | 6 | 只读 |
| 计算与容器 | 3 | 只读 |
| 数据处理与分析 | 5 | 只读 |
| 监控与运维 | 5 | 只读 |
| 安全与密钥 | 2 | 只读 |
| 成本与计费 | 4 | 只读 |
| **合计** | **25 项** | **全部只读** |

---

## 安全措施

- 全部权限为 **只读**，无法对生产环境执行任何写操作
- 建议启用 **MFA（多因素认证）**
- 建议定期轮换 Access Key（每 90 天）
- 如不需要查看密钥明文，可去除 Secrets Manager 的 `GetSecretValue` 权限

---

| | 签署 |
|---|------|
| **申请人** | __________________ |
| **审批人** | __________________ |
| **审批日期** | __________________ |
