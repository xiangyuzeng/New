# Dify 下线操作手册 — 访问与凭据
## Decommission Operator Runbook: Access & Credentials

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Author** | 曾翔宇 (David Zeng), DBA/Infrastructure |
| **Operator IAM** | `databasecheck` (AWS 257394478466, us-east-1) |
| **Related** | [Decommission Plan (2026-03-24)](/app/reports/dify-system-decommission-plan-2026-03-24.md) |
| **Related** | [Technical Report (2026-03-25)](/app/reports/dify-decommission-technical-report-2026-03-25.md) |

---

## Table of Contents

1. [AWS CLI 访问 (IAM Permissions Audit)](#1-aws-cli-访问-iam-permissions-audit)
2. [EKS / MCP 访问 (Kubernetes Access)](#2-eks--mcp-访问-kubernetes-access)
3. [RDS 连接信息 (PostgreSQL Connection)](#3-rds-连接信息-postgresql-connection)
4. [Redis 连接信息 (Redis Connection)](#4-redis-连接信息-redis-connection)
5. [OpenSearch 访问 (OpenSearch Access)](#5-opensearch-访问-opensearch-access)
6. [EC2 访问方式 (EC2 Access Methods)](#6-ec2-访问方式-ec2-access-methods)
7. [S3 访问 (S3 Bucket Access)](#7-s3-访问-s3-bucket-access)
8. [DNS 与网络 (DNS & Network)](#8-dns-与网络-dns--network)
9. [凭据清单 (Credential Inventory)](#9-凭据清单-credential-inventory)
10. [权限缺口矩阵 (Permission Gap Matrix)](#10-权限缺口矩阵-permission-gap-matrix)
11. [MCP 命令映射 (kubectl → MCP Translation)](#11-mcp-命令映射-kubectl--mcp-translation)
12. [操作环境配置 (Environment Setup Guide)](#12-操作环境配置-environment-setup-guide)

---

## 1. AWS CLI 访问 (IAM Permissions Audit)

### 1.1 Current Identity

| Field | Value |
|-------|-------|
| **IAM User** | `databasecheck` |
| **User ARN** | `arn:aws:iam::257394478466:user/databasecheck` |
| **User ID** | `AIDATX3PIBWBHOR7ZX46M` |
| **Account** | `257394478466` |
| **Region** | `us-east-1` |
| **Created** | 2025-09-29 |
| **Console URL** | `https://257394478466.signin.aws.amazon.com/console` |

### 1.2 IAM Self-Inspection

IAM self-inspection is **fully denied** for `databasecheck`:

| Action | Status |
|--------|--------|
| `iam:ListAttachedUserPolicies` | **DENIED** |
| `iam:ListUserPolicies` | **DENIED** |
| `iam:ListGroupsForUser` | **DENIED** |
| `iam:ListAccountAliases` | **DENIED** |

> Cannot determine which policies/groups grant access. Must coordinate with AWS admin to audit.

### 1.3 Service Permission Matrix

| Service | Action | Permission | Status | Notes |
|---------|--------|-----------|--------|-------|
| **RDS** | Describe instances | `rds:DescribeDBInstances` | **GRANTED** | Both dify instances accessible |
| **RDS** | Describe snapshots | `rds:DescribeDBSnapshots` | **GRANTED** | Can list existing snapshots |
| **RDS** | Create snapshot | `rds:CreateDBSnapshot` | **UNTESTED** | No dry-run available; test day-of |
| **RDS** | Delete instance | `rds:DeleteDBInstance` | **UNTESTED** | No dry-run available |
| **ElastiCache** | Describe groups | `elasticache:DescribeReplicationGroups` | **GRANTED** | Both clusters accessible |
| **ElastiCache** | Create snapshot | `elasticache:CreateSnapshot` | **UNTESTED** | No dry-run available |
| **ElastiCache** | Delete group | `elasticache:DeleteReplicationGroup` | **UNTESTED** | No dry-run available |
| **OpenSearch** | Describe domain | `es:DescribeDomain` | **GRANTED** | Full domain details accessible |
| **OpenSearch** | Delete domain | `es:DeleteDomain` | **UNTESTED** | No dry-run available |
| **EC2** | Describe instances | `ec2:DescribeInstances` | **GRANTED** | Both instances accessible |
| **EC2** | Stop instances | `ec2:StopInstances` | **DENIED** | dry-run confirmed UnauthorizedOperation |
| **EC2** | Terminate instances | `ec2:TerminateInstances` | **DENIED** | dry-run confirmed UnauthorizedOperation |
| **EC2** | Delete ENI | `ec2:DeleteNetworkInterface` | **DENIED** | dry-run confirmed UnauthorizedOperation |
| **EC2** | Describe SGs | `ec2:DescribeSecurityGroups` | **GRANTED** | |
| **EC2** | Describe key pairs | `ec2:DescribeKeyPairs` | **GRANTED** | 5 key pairs visible |
| **EC2** | Describe ENIs | `ec2:DescribeNetworkInterfaces` | **GRANTED** | 4 orphaned ENIs confirmed |
| **ELBv2** | Describe LBs | `elasticloadbalancing:DescribeLoadBalancers` | **GRANTED** | NLB visible |
| **ELBv2** | Delete LB | `elasticloadbalancing:DeleteLoadBalancer` | **UNTESTED** | |
| **S3** | Head bucket | `s3:HeadBucket` | **DENIED** | 403 Forbidden on all 3 buckets |
| **S3** | List objects | `s3:ListBucket` | **DENIED** | |
| **S3** | Get versioning | `s3:GetBucketVersioning` | **GRANTED** | All disabled |
| **S3** | Get tagging | `s3:GetBucketTagging` | **GRANTED** | All tagged `team=inf` |
| **S3** | Delete bucket/objects | `s3:DeleteBucket` / `s3:DeleteObject` | **UNTESTED** | Likely denied |
| **Route53** | List hosted zones | `route53:ListHostedZones` | **DENIED** | |
| **Route53** | Change records | `route53:ChangeResourceRecordSets` | **DENIED** | Cannot manage DNS |
| **SSM** | Describe instances | `ssm:DescribeInstanceInformation` | **DENIED** | |
| **ECR** | Describe repos | `ecr:DescribeRepositories` | **DENIED** | |
| **Secrets Manager** | List secrets | `secretsmanager:ListSecrets` | **DENIED** | |
| **KMS** | Describe key | `kms:DescribeKey` | **DENIED** | |
| **EFS** | Describe filesystems | `elasticfilesystem:DescribeFileSystems` | **DENIED** | |

### 1.4 Available SSH Key Pairs

| Key Pair Name | Notes |
|---------------|-------|
| `sre_aws2573` | Used by both Dify EC2 instances |
| `lk-tech-yw-sysop` | |
| `security-david` | |
| `eksprod` | EKS-related |
| `network` | |

---

## 2. EKS / MCP 访问 (Kubernetes Access)

### 2.1 Access Method

**kubectl and helm are NOT installed** on the operator workstation. All Kubernetes operations go through MCP:

| Tool | Status | MCP Server | Endpoint |
|------|--------|------------|----------|
| kubectl | **NOT INSTALLED** | eks-server (stdio) | Via Claude Code |
| helm | **NOT INSTALLED** | N/A — no Helm MCP tool | Must request access |
| EKS API | via MCP | eks-server | `prod-worker01-eks-us` cluster |

**To set up kubeconfig (if kubectl is installed later):**
```bash
aws eks update-kubeconfig --name prod-worker01-eks-us --region us-east-1 --alias prod-worker01-eks-us
```

### 2.2 RBAC Permissions

| Resource | Operation | Status | Notes |
|----------|-----------|--------|-------|
| Deployments | read/list | **GRANTED** | 19 deployments visible |
| StatefulSets | read/list | **GRANTED** | 6 statefulsets visible |
| Services | read/list | **GRANTED** | 25 services visible |
| ConfigMaps | read/list | **GRANTED** | 13 configmaps visible |
| Ingresses | read/list | **GRANTED** | 2 ingresses visible |
| PVCs | read/list | **GRANTED** | 13 PVCs visible |
| **Secrets** | list | **DENIED** | 403 — requires RBAC update |
| **Pod logs** | get | **DENIED** | Requires `--allow-sensitive-data-access` on eks-server |
| Deployments | patch/delete | **UNTESTED** | Requires `--allow-write` on eks-server |

### 2.3 Namespace Resource Inventory

**Namespace:** `baseservices-cloud-dify`

**19 Deployments:**

| # | Name | Manager | Release | Created |
|---|------|---------|---------|---------|
| 1 | dify-api | Helm | dify (v1.3.1) | 2025-05-21 |
| 2 | dify-web | Helm | dify (v1.3.1) | 2025-05-21 |
| 3 | dify-worker | Helm | dify (v1.3.1) | 2025-05-21 |
| 4 | dify-sandbox | Helm | dify (v1.3.1) | 2025-05-21 |
| 5 | dify-plugin-daemon | Helm | dify (v1.3.1) | 2025-05-26 |
| 6 | **new-dify-api** | kubectl | v1.8.1 | 2025-09-30 |
| 7 | **new-dify-web** | kubectl | v1.8.1 | 2025-09-24 |
| 8 | **new-dify-worker** | kubectl | v1.8.1 | 2025-09-26 |
| 9 | **new-dify-sandbox** | kubectl | v0.2.12 | 2025-09-23 |
| 10 | **new-dify-plugin-daemon** | kubectl | v0.2.0 | 2025-09-30 |
| 11-19 | milvus-* (9 deployments) | Helm | milvus v2.2.13 | 2025-05-20 |

**6 StatefulSets (all Helm/milvus):** milvus-etcd, milvus-pulsar-bookie, milvus-pulsar-broker, milvus-pulsar-proxy, milvus-pulsar-recovery, milvus-pulsar-zookeeper

**2 Ingresses:**

| Name | Host | Paths | Manager |
|------|------|-------|---------|
| new-dify-ingress | `dify-console.luckincoffee.us` | `/console`, `/api`, `/v1` → new-dify-api:5001; `/` → new-dify-web:3000 | kubectl |
| milvus-attu | — | — | Helm |

**13 ConfigMaps:** dify-api, dify-plugin-daemon, dify-proxy, dify-sandbox, dify-web, dify-worker, kube-root-ca.crt, milvus, milvus-pulsar-bookie, milvus-pulsar-broker, milvus-pulsar-proxy, milvus-pulsar-recovery, milvus-pulsar-zookeeper

**13 PVCs:**

| # | Name | Provisioner | Notes |
|---|------|-------------|-------|
| 1 | data-dify-39mdc | **efs.csi.aws.com** | Shared by new-dify-api, worker, plugin-daemon (10Gi EFS) |
| 2-4 | data-milvus-etcd-{0,1,2} | ebs.csi.aws.com | etcd data |
| 5-7 | milvus-pulsar-bookie-journal-*-{0,1,2} | ebs.csi.aws.com | Pulsar journal |
| 8-10 | milvus-pulsar-bookie-ledgers-*-{0,1,2} | ebs.csi.aws.com | Pulsar ledgers |
| 11-13 | milvus-pulsar-zookeeper-data-*-{0,1,2} | ebs.csi.aws.com | ZK data |

**25 Services:** 5 old-dify, 5 new-dify, 14 milvus, 1 hello-world (test)

**Secrets:** DENIED (403 Forbidden — RBAC restriction)

### 2.4 Helm Releases

| Release | Chart | Version | Resources Managed |
|---------|-------|---------|-------------------|
| `dify` | dify-0.0.1 | 1.3.1 | 5 Deployments, 5 Services, 6 ConfigMaps |
| `milvus` | milvus-4.0.31 | 2.2.13 | 9 Deployments, 6 StatefulSets, 14 Services, 6 ConfigMaps |

> **Note:** `helm uninstall` requires Helm CLI access. No MCP equivalent exists. See Section 11 for workaround.

---

## 3. RDS 连接信息 (PostgreSQL Connection)

### 3.1 Instance Details

| Property | OLD: aws-luckyus-dify-rw | NEW: aws-luckyus-difynew-rw |
|----------|--------------------------|------------------------------|
| **Endpoint** | `aws-luckyus-dify-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com` | `aws-luckyus-difynew-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com` |
| **Internal IP** | 10.238.4.223 | 10.238.4.142 |
| **Port** | 5432 | 5432 |
| **Engine** | PostgreSQL 16.8 | PostgreSQL 16.10 |
| **Class** | db.r5.xlarge | db.r5.xlarge |
| **Storage** | 20 GB gp3 | 20 GB gp3 |
| **Multi-AZ** | Yes | Yes |
| **Security Group** | sg-0deaa7cf7437e39c7 (sg_public_prod) | sg-0deaa7cf7437e39c7 (sg_public_prod) |
| **Subnet Group** | rds-group (shared by 64+ instances — **DO NOT DELETE**) | rds-group |

### 3.2 Connection Methods

**Method 1: MCP Gateway (primary — verified)**
```
Tool: mcp__mcp-db-gateway__postgres_query
```

| Instance | MCP Server Name | Connects As | Default DB | Status |
|----------|-----------------|-------------|------------|--------|
| NEW (difynew) | `aws-luckyus-difynew-rw` | `dba_admin` | `postgres` | **CONNECTED** |
| OLD (dify) | `aws-luckyus-dify-rw` | `dba_admin` | `postgres` | **CONNECTED** |

> **Limitation:** MCP gateway connects to `postgres` database by default. Use `\connect luckyus_dify_api` or cross-database queries for app data.

**Method 2: Direct psql (requires psql installation)**
```bash
# NEW instance — use app credentials from Section 9, Credential #1
psql "host=aws-luckyus-difynew-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com \
      port=5432 dbname=luckyus_dify_api user=dify_w sslmode=require"

# OLD instance — known password mismatch for dify_w user
# Use dba_admin via MCP gateway instead
```

### 3.3 Application Credentials (from EKS Deployment Env Vars)

| Env Var | Value Format | Used By |
|---------|-------------|---------|
| `DB_USERNAME` | `dify_w` | new-dify-api, worker, plugin-daemon |
| `DB_PASSWORD` | 10-char alphanumeric (see Credential #1) | new-dify-api, worker, plugin-daemon |
| `DB_HOST` | `aws-luckyus-difynew-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com` | all |
| `DB_PORT` | `5432` | all |
| `DB_DATABASE` | `luckyus_dify_api` (api/worker), `luckyus_dify_plugin` (plugin-daemon) | varies |
| `DB_SSL_MODE` | `require` | plugin-daemon, worker |

---

## 4. Redis 连接信息 (Redis Connection)

### 4.1 Cluster Details

| Property | OLD: luckyus-redis-dify | NEW: luckyus-difynew |
|----------|------------------------|----------------------|
| **Primary Endpoint** | `master.luckyus-redis-dify.vyllrs.use1.cache.amazonaws.com:6379` | `master.luckyus-difynew.vyllrs.use1.cache.amazonaws.com:6379` |
| **Reader Endpoint** | `replica.luckyus-redis-dify.vyllrs.use1.cache.amazonaws.com:6379` | `replica.luckyus-difynew.vyllrs.use1.cache.amazonaws.com:6379` |
| **Node Type** | cache.m6g.large | cache.t4g.micro |
| **Engine** | Redis 7.0.7 | Redis 6.0.5 |
| **Auth Token** | Enabled | Enabled |
| **TLS** | Required | Required |
| **At-Rest Encryption** | Enabled | Enabled |
| **Auto Failover** | Enabled | Enabled |
| **Status** | available | available |
| **Uptime** | 310 days | — |

### 4.2 Connection Methods

**Method 1: MCP Gateway**

| Cluster | MCP Server Name | Status |
|---------|-----------------|--------|
| OLD (luckyus-redis-dify) | `luckyus-redis-dify` | **CONNECTED** (PONG verified) |
| NEW (luckyus-difynew) | — | **NOT IN GATEWAY** |

> **CRITICAL GAP:** The NEW Redis cluster `luckyus-difynew` is **not registered** in mcp-db-gateway. It cannot be accessed via MCP.
> - **Option A:** Add `luckyus-difynew` entry to mcp-db-gateway config (requires gateway admin)
> - **Option B:** Use redis-cli from within VPC (bastion host or VPN)
> - **Impact:** Cannot perform pre-decommission data verification on NEW cluster via MCP

**Method 2: Direct redis-cli (requires redis-cli + TLS)**
```bash
# OLD cluster
redis-cli -h master.luckyus-redis-dify.vyllrs.use1.cache.amazonaws.com \
          -p 6379 --tls -a '<SEE CREDENTIAL #2>' PING

# NEW cluster
redis-cli -h master.luckyus-difynew.vyllrs.use1.cache.amazonaws.com \
          -p 6379 --tls -a '<SEE CREDENTIAL #2>' PING
```

### 4.3 Application Credentials (from EKS Deployment Env Vars)

| Env Var | Value Format | Used By |
|---------|-------------|---------|
| `REDIS_HOST` | `master.luckyus-difynew.vyllrs.use1.cache.amazonaws.com` | new-dify-api, worker, plugin-daemon |
| `REDIS_PORT` | `6379` | all |
| `REDIS_PASSWORD` | 18-char alphanumeric (see Credential #2) | new-dify-api, worker, plugin-daemon |
| `REDIS_USE_SSL` | `true` | all |
| `CELERY_BROKER_URL` | `rediss://:****@master.luckyus-difynew...:6379/1` | new-dify-api, worker |

---

## 5. OpenSearch 访问 (OpenSearch Access)

### 5.1 Domain Details

| Property | Value |
|----------|-------|
| **Domain** | `luckyus-opensearch-dify` |
| **Engine** | OpenSearch 2.15 |
| **VPC Endpoint** | `vpc-luckyus-opensearch-dify-476fgzupv2mhhiacjpc4ac53ea.us-east-1.es.amazonaws.com` |
| **Data Nodes** | 2x r6g.large.search |
| **Dedicated Masters** | 3x m7g.large.search |
| **VPC** | vpc-0dce7ca7770422d33 |
| **Subnets** | subnet-01608eef3ea13c7d3 (us-east-1a), subnet-0acd412a7bc5ebc55 (us-east-1b) |
| **Security Group** | sg-0deaa7cf7437e39c7 (sg_public_prod) — **shared, DO NOT DELETE** |
| **Advanced Security** | Enabled (Internal User DB) |
| **Zone Awareness** | 2 AZs |

### 5.2 Connection Method

VPC-restricted endpoint. Accessible only from within VPC (EKS pods, EC2 instances, VPN).

```bash
# From within VPC (e.g., bastion host or EKS pod):
curl -u 'luckyus_dify_rw:<SEE CREDENTIAL #4>' \
     'https://vpc-luckyus-opensearch-dify-476fgzupv2mhhiacjpc4ac53ea.us-east-1.es.amazonaws.com/'
```

### 5.3 Application Credentials (from EKS Deployment Env Vars)

| Env Var | Value Format | Used By |
|---------|-------------|---------|
| `OPENSEARCH_HOST` | `https://vpc-luckyus-opensearch-dify-...es.amazonaws.com` (api) or without `https://` (worker) | new-dify-api, worker |
| `OPENSEARCH_PORT` | `443` | new-dify-api, worker |
| `OPENSEARCH_USER` | `luckyus_dify_rw` | new-dify-api, worker |
| `OPENSEARCH_PASSWORD` | 16-char with special characters (see Credential #4) | new-dify-api, worker |
| `OPENSEARCH_SECURE` | `true` | new-dify-api, worker |
| `VECTOR_STORE` | `opensearch` | new-dify-api, worker |

---

## 6. EC2 访问方式 (EC2 Access Methods)

### 6.1 Instance Details

| Property | isredify01 | iluckydifyjump01 |
|----------|------------|------------------|
| **Instance ID** | i-06e7301a6e3f28df4 | i-02d4ea4bbab7fd574 |
| **Full Name** | isredify01-prod-usa-aws | iluckydifyjump01-prod-usa-aws |
| **Type** | c6i.large | c6i.large |
| **State** | running | running |
| **Private IP** | 10.238.3.201 | 10.238.3.92 |
| **Public IP** | None | None |
| **Key Pair** | `sre_aws2573` | `sre_aws2573` |
| **Security Group** | sg-0deaa7cf7437e39c7 (sg_public_prod) | sg-0deaa7cf7437e39c7 (sg_public_prod) |
| **IAM Profile** | **None** | **None** |
| **Subnet** | subnet-0828db1b483e7e580 | subnet-0828db1b483e7e580 |
| **Purpose** | Standalone Redis server | Dify bastion/jump host |

### 6.2 Access Methods

| Method | Status | Notes |
|--------|--------|-------|
| **SSM Session Manager** | **NOT AVAILABLE** | No IAM instance profile → no SSM agent |
| **SSH** | **Requires** `sre_aws2573` key + VPN/bastion | No public IP; must be within VPC |
| **AWS Console** | Read-only (describe only) | Cannot stop/terminate with databasecheck |

> **Note:** `iluckydifyjump01` IS the bastion host for Dify. Since it has no public IP, you need VPN or another bastion to reach it. Coordinate with Ops team for direct access.

### 6.3 EC2 Operation Permissions

| Operation | Status |
|-----------|--------|
| Stop instances | **DENIED** (dry-run confirmed) |
| Terminate instances | **DENIED** (dry-run confirmed) |
| Describe instances | **GRANTED** |

> **Action required:** Request `ec2:StopInstances` and `ec2:TerminateInstances`, or delegate to Ops (王东尧).

---

## 7. S3 访问 (S3 Bucket Access)

### 7.1 Bucket Details

| Bucket | Tag | Versioning | Est. Size |
|--------|-----|------------|-----------|
| `lk-infra-dify` | team=inf | Disabled | ~50 MB |
| `lk-infra-dify-data` | team=inf | Disabled | ~20 MB |
| `lk-infra-dify-plugindaemon` | team=inf | Disabled | ~3 MB |

### 7.2 Permissions

| Operation | Status |
|-----------|--------|
| `s3:HeadBucket` | **DENIED** (403) |
| `s3:ListBucket` | **DENIED** |
| `s3:GetBucketVersioning` | **GRANTED** (all disabled) |
| `s3:GetBucketTagging` | **GRANTED** (all team=inf) |
| `s3:GetBucketPolicy` | **DENIED** |
| `s3:GetBucketEncryption` | **DENIED** |
| `s3:DeleteBucket` / `s3:DeleteObject` | **UNTESTED** (likely denied) |

> **Note:** Application uses `STORAGE_TYPE=local` (EFS PVC), so these buckets may contain only legacy/migration data. Delegate S3 deletion to Ops team.

---

## 8. DNS 与网络 (DNS & Network)

### 8.1 DNS Record

| Record | Type | Target | Status |
|--------|------|--------|--------|
| `dify-console.luckincoffee.us` | TBD | Points to NGINX Ingress | **Route53 access DENIED** |

> Cannot verify or modify DNS records. Delegate to 王东尧/李昆.

### 8.2 Network Load Balancer

| Property | Value |
|----------|-------|
| **Name** | `inf-milvus-service` |
| **ARN** | `arn:aws:elasticloadbalancing:us-east-1:257394478466:loadbalancer/net/inf-milvus-service/83c26a421d630082` |
| **DNS** | `inf-milvus-service-83c26a421d630082.elb.us-east-1.amazonaws.com` |
| **Type** | NLB (network), internal |
| **State** | active |
| **VPC** | vpc-0dce7ca7770422d33 |

> Created by Helm via `service.beta.kubernetes.io/aws-load-balancer-*` annotations on `milvus` Service. Will be auto-cleaned when the Service is deleted, or manually via ELBv2 API.

### 8.3 Orphaned ENIs

| ENI ID | Status | Description | Private IP | AZ |
|--------|--------|-------------|------------|-----|
| eni-0f2adc1cdec3cab8a | available | ES luckyus-opensearch-dify | 10.238.4.154 | us-east-1a |
| eni-0d7735e22a081705c | available | ES luckyus-opensearch-dify | 10.238.4.167 | us-east-1a |
| eni-0d623c6205c24d3a7 | available | ES luckyus-opensearch-dify | 10.238.9.89 | us-east-1b |
| eni-0ba40d95964577c62 | available | ES luckyus-opensearch-dify | 10.238.9.137 | us-east-1b |

All 4 ENIs are detached (`available`). `ec2:DeleteNetworkInterface` is **DENIED** for `databasecheck`.

---

## 9. 凭据清单 (Credential Inventory)

All credentials below were found as **plaintext in `kubectl.kubernetes.io/last-applied-configuration` annotations** on new-dify-* deployments. Values are masked per security policy.

### 9.1 Credentials Requiring Post-Decommission Rotation

| # | Credential | Env Var | Format | Used By | Connects To | Rotation |
|---|-----------|---------|--------|---------|-------------|----------|
| 1 | **PostgreSQL password** | `DB_PASSWORD` | 10-char alphanumeric | api, worker, plugin-daemon | RDS difynew-rw (user: `dify_w`) | **YES** |
| 2 | **Redis auth token** | `REDIS_PASSWORD` | 18-char alphanumeric | api, worker, plugin-daemon | ElastiCache luckyus-difynew | **YES** |
| 3 | **Dify SECRET_KEY** | `SECRET_KEY` | 48-char, `sk-` prefix | api, worker | Dify internal auth | No (system deleted) |
| 4 | **OpenSearch password** | `OPENSEARCH_PASSWORD` | 16-char with special chars | api, worker | OpenSearch (user: `luckyus_dify_rw`) | **YES** |
| 5 | **SMTP password** | `SMTP_PASSWORD` | 16-char with special chars | api, worker | WorkMail (`dify@luckincoffee.us`) | **YES** — shared service survives decommission |
| 6 | **Plugin daemon key** | `PLUGIN_DAEMON_KEY` | 58-char base64 | api, plugin-daemon | Internal plugin auth | No (system deleted) |
| 7 | **Inner API key** | `DIFY_INNER_API_KEY` | Same as SECRET_KEY (#3) | plugin-daemon | Internal API auth | No (system deleted) |
| 8 | **Sandbox API key** | `CODE_EXECUTION_API_KEY` | Static string | api | Code sandbox | No (system deleted) |

### 9.2 Credential Locations

| Location | Type | Access |
|----------|------|--------|
| new-dify-api Deployment annotation | Plaintext `last-applied-configuration` | EKS read (GRANTED) |
| new-dify-worker Deployment annotation | Plaintext `last-applied-configuration` | EKS read (GRANTED) |
| new-dify-plugin-daemon Deployment annotation | Plaintext `last-applied-configuration` | EKS read (GRANTED) |
| K8s Secrets in namespace | Unknown contents | EKS Secrets (DENIED — 403) |
| Old dify Helm release secrets | Contains old Helm values | Helm CLI required |
| MCP gateway config | `dba_admin` credentials for both RDS | Gateway admin only |

> **WARNING:** Credentials #1, #2, #4, #5 are hardcoded in plaintext in Kubernetes annotations visible to anyone with Deployment read access. Credential #5 (SMTP) connects to a shared WorkMail service that survives the decommission — this MUST be rotated.

---

## 10. 权限缺口矩阵 (Permission Gap Matrix)

### 10.1 Permissions Needed by Decommission Phase

| Phase | Action | Required Permission | Status | Owner |
|-------|--------|---------------------|--------|-------|
| **1** | Scale new-dify pods to 0 | eks-server `--allow-write` | **NEEDS FLAG** | Ops (王东尧) |
| **1** | Delete ingress new-dify-ingress | eks-server `--allow-write` | **NEEDS FLAG** | Ops |
| **2** | `helm uninstall dify` | Helm CLI | **NO MCP TOOL** | Ops |
| **2** | `helm uninstall milvus` | Helm CLI | **NO MCP TOOL** | Ops |
| **2** | Create RDS snapshot (dify-rw) | `rds:CreateDBSnapshot` | **UNTESTED** | DBA (曾翔宇) |
| **2** | Delete RDS dify-rw | `rds:DeleteDBInstance` | **UNTESTED** | DBA |
| **3** | Delete new-dify-* deployments/svc/pvc | eks-server `--allow-write` | **NEEDS FLAG** | Ops |
| **4** | Delete Milvus resources | Helm or eks-server write | **NEEDS FLAG** | Ops |
| **5** | Create ElastiCache snapshots | `elasticache:CreateSnapshot` | **UNTESTED** | DBA |
| **5** | Delete ElastiCache clusters | `elasticache:DeleteReplicationGroup` | **UNTESTED** | DBA |
| **5** | Create RDS snapshot (difynew-rw) | `rds:CreateDBSnapshot` | **UNTESTED** | DBA |
| **5** | Delete RDS difynew-rw | `rds:DeleteDBInstance` | **UNTESTED** | DBA |
| **5** | Delete OpenSearch domain | `es:DeleteDomain` | **UNTESTED** | Ops |
| **6** | Stop EC2 instances | `ec2:StopInstances` | **DENIED** | Ops |
| **6** | Terminate EC2 instances | `ec2:TerminateInstances` | **DENIED** | Ops |
| **6** | Empty + Delete S3 buckets | `s3:DeleteObject`, `s3:DeleteBucket` | **DENIED** | Ops |
| **7** | Delete namespace | eks-server `--allow-write` | **NEEDS FLAG** | Ops |
| **7** | Delete orphaned ENIs | `ec2:DeleteNetworkInterface` | **DENIED** | Ops |
| **7** | Delete DNS record | `route53:ChangeResourceRecordSets` | **DENIED** | Ops |
| **7** | Remove MCP gateway entries | Gateway admin | **AVAILABLE** | DBA |
| **7** | Rotate credentials | Various | **AVAILABLE** | DBA + Ops |

### 10.2 Escalation Requests Summary

| # | Request | Permissions Needed | Request To | Priority |
|---|---------|-------------------|-----------|----------|
| 1 | **EKS write access** | Enable `--allow-write` on eks-server MCP | EKS admin / 李昆 | HIGH |
| 2 | **Helm CLI** | Install helm on operator workstation or bastion | Ops / 王东尧 | HIGH |
| 3 | **EC2 mutate** | `ec2:StopInstances`, `ec2:TerminateInstances`, `ec2:DeleteNetworkInterface` | AWS admin | MEDIUM |
| 4 | **S3 full access** | `s3:ListBucket`, `s3:DeleteObject`, `s3:DeleteBucket` for lk-infra-dify* | AWS admin | MEDIUM |
| 5 | **Route53 access** | `route53:ListHostedZones`, `route53:ChangeResourceRecordSets` | AWS admin | MEDIUM |
| 6 | **RDS/ElastiCache mutate** | Test `rds:CreateDBSnapshot`, `elasticache:CreateSnapshot` day-of | AWS admin (if denied) | LOW — test first |
| 7 | **EKS Secrets** | RBAC update for Secrets list/get in namespace | EKS admin | LOW |

---

## 11. MCP 命令映射 (kubectl → MCP Translation)

### 11.1 kubectl → eks-server MCP

| Original Command | MCP Tool | Key Parameters |
|-----------------|----------|----------------|
| `kubectl scale deployment X --replicas=0` | `manage_k8s_resource` | `operation="patch", kind="Deployment", api_version="apps/v1", name="X", namespace="baseservices-cloud-dify", body={"spec":{"replicas":0}}` |
| `kubectl delete ingress X` | `manage_k8s_resource` | `operation="delete", kind="Ingress", api_version="networking.k8s.io/v1", name="X"` |
| `kubectl delete deployment X` | `manage_k8s_resource` | `operation="delete", kind="Deployment", api_version="apps/v1", name="X"` |
| `kubectl delete service X` | `manage_k8s_resource` | `operation="delete", kind="Service", api_version="v1", name="X"` |
| `kubectl delete pvc X` | `manage_k8s_resource` | `operation="delete", kind="PersistentVolumeClaim", api_version="v1", name="X"` |
| `kubectl delete statefulset X` | `manage_k8s_resource` | `operation="delete", kind="StatefulSet", api_version="apps/v1", name="X"` |
| `kubectl delete configmap X` | `manage_k8s_resource` | `operation="delete", kind="ConfigMap", api_version="v1", name="X"` |
| `kubectl delete namespace X` | `manage_k8s_resource` | `operation="delete", kind="Namespace", api_version="v1", name="X"` |
| `kubectl get pods -n X` | `list_k8s_resources` | `kind="Pod", api_version="v1", namespace="X"` |
| `kubectl get deployment X -o json` | `manage_k8s_resource` | `operation="read", kind="Deployment", api_version="apps/v1", name="X"` |

### 11.2 helm uninstall Workaround

No Helm MCP tool exists. Replace with sequential resource deletion:

**`helm uninstall dify`** — delete in order:
1. Deployments: dify-api, dify-web, dify-worker, dify-sandbox, dify-plugin-daemon
2. Services: dify-api, dify-web, dify-sandbox, dify-plugin-daemon
3. ConfigMaps: dify-api, dify-web, dify-worker, dify-sandbox, dify-plugin-daemon, dify-proxy

**`helm uninstall milvus`** — delete in order:
1. Deployments: milvus-proxy, milvus-querynode, milvus-querycoord, milvus-indexnode, milvus-indexcoord, milvus-datanode, milvus-datacoord, milvus-rootcoord, milvus-attu
2. StatefulSets: milvus-pulsar-proxy, milvus-pulsar-broker, milvus-pulsar-bookie, milvus-pulsar-recovery, milvus-pulsar-zookeeper, milvus-etcd
3. Services: all 14 milvus-* services
4. ConfigMaps: milvus, milvus-pulsar-bookie, milvus-pulsar-broker, milvus-pulsar-proxy, milvus-pulsar-recovery, milvus-pulsar-zookeeper
5. PVCs: 12 milvus-* PVCs
6. Ingress: milvus-attu

> **Alternative:** Get temporary helm access on bastion (10.238.3.92) and run helm uninstall directly.

### 11.3 AWS CLI Commands (Available Directly)

```bash
# Phase 2/5: Create RDS snapshots
aws rds create-db-snapshot --db-instance-identifier aws-luckyus-dify-rw \
  --db-snapshot-identifier dify-rw-final-20260325 --region us-east-1

aws rds create-db-snapshot --db-instance-identifier aws-luckyus-difynew-rw \
  --db-snapshot-identifier difynew-rw-final-20260325 --region us-east-1

# Phase 5: Create ElastiCache snapshots
aws elasticache create-snapshot --replication-group-id luckyus-redis-dify \
  --snapshot-name redis-dify-final-20260325 --region us-east-1

aws elasticache create-snapshot --replication-group-id luckyus-difynew \
  --snapshot-name redis-difynew-final-20260325 --region us-east-1

# Phase 2: Delete OLD RDS (with final snapshot)
aws rds delete-db-instance --db-instance-identifier aws-luckyus-dify-rw \
  --final-db-snapshot-identifier dify-rw-decommission-final --region us-east-1

# Phase 5: Delete NEW RDS (with final snapshot)
aws rds delete-db-instance --db-instance-identifier aws-luckyus-difynew-rw \
  --final-db-snapshot-identifier difynew-rw-decommission-final --region us-east-1

# Phase 5: Delete ElastiCache
aws elasticache delete-replication-group --replication-group-id luckyus-redis-dify \
  --final-snapshot-identifier redis-dify-decommission-final --region us-east-1

aws elasticache delete-replication-group --replication-group-id luckyus-difynew \
  --final-snapshot-identifier redis-difynew-decommission-final --region us-east-1

# Phase 5: Delete OpenSearch
aws opensearch delete-domain --domain-name luckyus-opensearch-dify --region us-east-1

# Phase 6: EC2 (DENIED — delegate to Ops)
# aws ec2 stop-instances --instance-ids i-06e7301a6e3f28df4 i-02d4ea4bbab7fd574 --region us-east-1
# aws ec2 terminate-instances --instance-ids i-06e7301a6e3f28df4 i-02d4ea4bbab7fd574 --region us-east-1

# Phase 6: S3 (DENIED — delegate to Ops)
# aws s3 rm s3://lk-infra-dify --recursive && aws s3 rb s3://lk-infra-dify
# aws s3 rm s3://lk-infra-dify-data --recursive && aws s3 rb s3://lk-infra-dify-data
# aws s3 rm s3://lk-infra-dify-plugindaemon --recursive && aws s3 rb s3://lk-infra-dify-plugindaemon

# Phase 7: ENIs (DENIED — delegate to Ops)
# aws ec2 delete-network-interface --network-interface-id eni-0d623c6205c24d3a7 --region us-east-1
# aws ec2 delete-network-interface --network-interface-id eni-0ba40d95964577c62 --region us-east-1
# aws ec2 delete-network-interface --network-interface-id eni-0d7735e22a081705c --region us-east-1
# aws ec2 delete-network-interface --network-interface-id eni-0f2adc1cdec3cab8a --region us-east-1

# Post-decommission verification
aws rds describe-db-instances --query "DBInstances[?contains(DBInstanceIdentifier,'dify')]" --region us-east-1
aws elasticache describe-replication-groups --query "ReplicationGroups[?contains(ReplicationGroupId,'dify')]" --region us-east-1
aws opensearch list-domain-names --query "DomainNames[?contains(DomainName,'dify')]" --region us-east-1
aws ec2 describe-instances --filters "Name=tag:Name,Values=*dify*" --query "Reservations[].Instances[?State.Name!='terminated']" --region us-east-1
```

---

## 12. 操作环境配置 (Environment Setup Guide)

### 12.1 Pre-Requisites Check

```bash
# 1. Verify AWS CLI
aws --version  # Expected: aws-cli/2.x.x

# 2. Verify identity
aws sts get-caller-identity --region us-east-1  # Expected: Account 257394478466

# 3. Test core read permissions
aws rds describe-db-instances --db-instance-identifier aws-luckyus-dify-rw \
  --query 'DBInstances[0].DBInstanceIdentifier' --region us-east-1
aws elasticache describe-replication-groups --replication-group-id luckyus-redis-dify \
  --query 'ReplicationGroups[0].ReplicationGroupId' --region us-east-1
aws opensearch describe-domain --domain-name luckyus-opensearch-dify \
  --query 'DomainStatus.DomainName' --region us-east-1

# 4. CRITICAL: Test snapshot creation (do this BEFORE execution day)
aws rds create-db-snapshot --db-instance-identifier aws-luckyus-dify-rw \
  --db-snapshot-identifier test-perm-check-$(date +%s) --region us-east-1
# If succeeds: delete the test snapshot immediately
# If fails: escalate to AWS admin for rds:CreateDBSnapshot
```

### 12.2 MCP Server Connectivity

| Server | Test Method | Expected |
|--------|-----------|----------|
| mcp-db-gateway (PG) | `postgres_query(server="aws-luckyus-difynew-rw", sql="SELECT 1")` | `{"rows":[{"?column?":1}]}` |
| mcp-db-gateway (Redis) | `redis_command(server="luckyus-redis-dify", command="PING")` | `{"result":true}` |
| eks-server | `list_k8s_resources(cluster="prod-worker01-eks-us", kind="Namespace", api_version="v1")` | Namespace list |
| grafana-lucky | `search_dashboards(query="dify")` | Dashboard results |

### 12.3 Tool Availability

| Tool | Status | Install Command |
|------|--------|----------------|
| AWS CLI v2 | **Installed** | — |
| kubectl | Not installed | Install then: `aws eks update-kubeconfig --name prod-worker01-eks-us --region us-east-1` |
| helm | Not installed | `curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 \| bash` |
| psql | Not installed | `sudo yum install -y postgresql15` |
| redis-cli | Not installed | `sudo yum install -y redis6` |

### 12.4 MCP Gateway Cleanup (Phase 7)

Remove these entries from mcp-db-gateway after decommission:

| Entry Type | Server Name | Action |
|------------|-------------|--------|
| PostgreSQL | `aws-luckyus-dify-rw` | Remove |
| PostgreSQL | `aws-luckyus-difynew-rw` | Remove |
| Redis | `luckyus-redis-dify` | Remove |

> `luckyus-difynew` was never in gateway — no removal needed.

Gateway endpoint: `http://10.238.3.43:8080/sse`

### 12.5 Day-of Execution Checklist

- [ ] All escalation requests approved (Section 10.2)
- [ ] Active API token resolved (contact litlei)
- [ ] All 16 users notified
- [ ] Snapshot creation permission verified
- [ ] Communication sent to 王东尧 and 李昆
- [ ] Rollback plan reviewed
- [ ] This runbook accessible during execution

---

## Appendix A: Shared Resources — DO NOT DELETE

| Resource | ID | Shared By | Impact If Deleted |
|----------|----|-----------|-------------------|
| Security Group | sg-0deaa7cf7437e39c7 (`sg_public_prod`) | 623+ ENIs, all RDS, OpenSearch, EC2 | **CATASTROPHIC** |
| RDS Subnet Group | `rds-group` | 64+ RDS instances | **CATASTROPHIC** |
| VPC | vpc-0dce7ca7770422d33 | Entire infrastructure | **CATASTROPHIC** |
| KMS Key | 0d74cdfc-57ba-4d94-8947-2249228352f1 | OpenSearch encryption | Safe after OpenSearch deletion |

## Appendix B: EFS Dependency

PVC `data-dify-39mdc` uses EFS (`efs.csi.aws.com`). After namespace deletion, the underlying EFS access point may remain orphaned. EFS access is DENIED for `databasecheck` — coordinate with Ops to clean up.

---

*Runbook generated 2026-03-25 by Claude Code for 曾翔宇 (David Zeng)*
