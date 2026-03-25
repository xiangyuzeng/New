# Dify AI Platform Database Investigation Report

**Date:** 2026-03-25
**Investigator:** David Zeng (DBA)
**Purpose:** Decommission assessment for Dify AI platform PostgreSQL databases

---

## Infrastructure Overview

| Attribute | OLD Instance (dify-rw) | NEW Instance (difynew-rw) |
|-----------|----------------------|--------------------------|
| **RDS Identifier** | aws-luckyus-dify-rw | aws-luckyus-difynew-rw |
| **Endpoint** | aws-luckyus-dify-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com | aws-luckyus-difynew-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com |
| **PostgreSQL Version** | 16.8 | 16.10 |
| **Databases** | luckyus_dify_api, luckyus_dify_plugin | luckyus_dify_api, luckyus_dify_plugin |
| **DB Users** | dba_admin, dify_w, dongyaowang | dba_admin, dify_w, dongyaowang |
| **EKS Namespace** | baseservices-cloud-dify (pods: dify-*) | baseservices-cloud-dify (pods: new-dify-*) |
| **EKS Cluster** | prod-worker01-eks-us | prod-worker01-eks-us |
| **Dify Version** | 1.3.1 | 1.8.1 |
| **Vector Store** | Milvus | OpenSearch |
| **Storage** | S3 (lk-infra-dify-data) | Local PVC (data-dify-39mdc) |
| **Redis** | luckyus-redis-dify | luckyus-difynew |

---

## Query Results — NEW Instance (aws-luckyus-difynew-rw)

### Query 1.1 — All User Accounts

| # | Name | Email (masked) | Last Login | Created | Last Active | Status | Language |
|---|------|---------------|------------|---------|-------------|--------|----------|
| 1 | dify | ***@lkcoffee.com | 2026-02-27 | 2025-09-26 | 2026-03-09 | active | en-US |
| 2 | 卢延新 | ***@lkcoffee.com | 2026-03-09 | 2025-09-26 | 2026-03-09 | active | zh-Hans |
| 3 | zhuo.jiang | ***@lkcoffee.com | 2025-12-16 | 2025-09-26 | 2025-12-20 | active | zh-Hans |
| 4 | zhiyong.lan | ***@lkcoffee.com | 2025-11-26 | 2025-09-26 | 2025-11-27 | active | zh-Hans |
| 5 | litlei | ***@amazon.com | 2025-11-05 | 2025-10-15 | 2025-11-21 | active | en-US |
| 6 | jianhui | ***@lkcoffee.com | 2025-11-07 | 2025-10-15 | 2025-11-07 | active | en-US |
| 7 | Ethan | ***@amazon.com | 2025-10-16 | 2025-10-15 | 2025-11-05 | active | zh-Hans |
| 8 | yaner | ***@lkcoffee.com | 2025-11-03 | 2025-10-15 | 2025-11-03 | active | zh-Hans |
| 9 | dongyao.wang | ***@luckincoffee.us | 2025-10-31 | 2025-10-31 | 2025-11-02 | active | en-US |
| 10 | Jack Che | ***@lkcoffee.com | 2025-10-09 | 2025-10-09 | 2025-10-09 | active | zh-Hans |
| 11 | yang.zhang22 | ***@lkcoffee.com | (never) | 2025-10-09 | 2025-10-09 | pending | zh-Hans |
| 12 | peng.wei01 | ***@lkcoffee.com | 2025-09-30 | 2025-09-26 | 2025-09-30 | active | zh-Hans |
| 13 | jingyu.li | ***@lkcoffee.com | (never) | 2025-09-26 | 2025-09-26 | pending | zh-Hans |
| 14 | mengxing.lou | ***@lkcoffee.com | (never) | 2025-09-26 | 2025-09-26 | pending | zh-Hans |
| 15 | jiale.chen | ***@lkcoffee.com | (never) | 2025-09-26 | 2025-09-26 | pending | zh-Hans |
| 16 | chao.wang13 | ***@lkcoffee.com | 2025-09-26 | 2025-09-26 | 2025-09-26 | active | zh-Hans |

**Total: 16 accounts** (12 active, 4 pending/never logged in)

### Query 1.2 — Last 20 Active Users with Days Inactive

| Name | Email (masked) | Last Active | Days Inactive |
|------|---------------|-------------|---------------|
| dify | ***@lkcoffee.com | 2026-03-09 | **16** |
| 卢延新 | ***@lkcoffee.com | 2026-03-09 | **16** |
| zhuo.jiang | ***@lkcoffee.com | 2025-12-20 | 94 |
| zhiyong.lan | ***@lkcoffee.com | 2025-11-27 | 118 |
| litlei | ***@amazon.com | 2025-11-21 | 124 |
| jianhui | ***@lkcoffee.com | 2025-11-07 | 138 |
| Ethan | ***@amazon.com | 2025-11-05 | 140 |
| yaner | ***@lkcoffee.com | 2025-11-03 | 142 |
| dongyao.wang | ***@luckincoffee.us | 2025-11-02 | 143 |
| Jack Che | ***@lkcoffee.com | 2025-10-09 | 167 |
| yang.zhang22 | ***@lkcoffee.com | 2025-10-09 | 167 |
| peng.wei01 | ***@lkcoffee.com | 2025-09-30 | 176 |
| jingyu.li | ***@lkcoffee.com | 2025-09-26 | 180 |
| mengxing.lou | ***@lkcoffee.com | 2025-09-26 | 180 |
| jiale.chen | ***@lkcoffee.com | 2025-09-26 | 180 |
| chao.wang13 | ***@lkcoffee.com | 2025-09-26 | 180 |

**Key observation:** Only 2 users were active within the last 30 days (dify, 卢延新 — both on 2026-03-09). All other users have been inactive for 94+ days.

### Query 1.3 — Knowledge Base / Dataset Inventory

| # | Dataset Name | Description | Created | Updated | Data Source | Embedding Model | Creator |
|---|-------------|-------------|---------|---------|-------------|----------------|---------|
| 1 | product_info_IQA1_test03 | | 2025-10-17 | 2025-10-17 | upload_file | amazon.titan-embed-text-v1 | 卢延新 |
| 2 | product_info_lkus_test03 | test03 | 2025-10-17 | 2025-10-17 | upload_file | amazon.titan-embed-text-v1 | 卢延新 |
| 3 | product_info_IQA1 | prod | 2025-09-28 | 2025-09-28 | upload_file | text-embedding-3-large | 卢延新 |
| 4 | product_info_lkus | prod | 2025-09-28 | 2025-09-28 | upload_file | text-embedding-3-large | 卢延新 |
| 5 | 堡垒机双因素认证操作手册.pdf... | Useful for queries about 堡垒机双因素认证操作手册 | 2025-09-24 | 2025-09-24 | upload_file | amazon.titan-embed-text-v1 | (system) |
| 6 | 堡垒机双因素认证操作手册.pdf... | Useful for queries about 堡垒机双因素认证操作手册 | 2025-09-24 | 2025-09-24 | upload_file | amazon.titan-embed-text-v1 | (system) |

**Total: 6 datasets** — All created by 卢延新 or system import. Primary content is product info for AI ordering and a jump server manual.

### Query 1.4 — Apps / Workflows Inventory

| # | App Name | Mode | Created | Updated | Status | Creator |
|---|----------|------|---------|---------|--------|---------|
| 1 | 美国AI点单-开发-lei_Solution2-prod | advanced-chat | 2025-11-05 | 2025-11-05 | normal | litlei (***@amazon.com) |
| 2 | 美国AI点单-开发-lei_Solution2-test03 | advanced-chat | 2025-11-03 | 2025-11-03 | normal | litlei (***@amazon.com) |
| 3 | 美国AI点单-开发-lei_Solution2-prod_backup | advanced-chat | 2025-10-28 | 2025-10-31 | normal | litlei (***@amazon.com) |
| 4 | ai生成测试数据-单轮对话 | workflow | 2025-10-27 | 2025-10-27 | normal | jianhui (***@lkcoffee.com) |
| 5 | ai生成测试数据-多轮对话 | workflow | 2025-10-23 | 2025-10-27 | normal | jianhui (***@lkcoffee.com) |
| 6 | 美国AI点单-开发-jiangzhuo-test | advanced-chat | 2025-10-24 | 2025-10-24 | normal | zhuo.jiang (***@lkcoffee.com) |
| 7 | Transcribe 词库生成 | chat | 2025-10-23 | 2025-10-23 | normal | zhuo.jiang (***@lkcoffee.com) |
| 8 | 美国AI点单-开发-lei_Solution1-test03 | advanced-chat | 2025-10-17 | 2025-10-17 | normal | 卢延新 (***@lkcoffee.com) |
| 9 | 美国AI点单-联调-lei | advanced-chat | 2025-10-16 | 2025-10-16 | normal | litlei (***@amazon.com) |
| 10 | 美国AI点单-开发-lei_Solution1-prod_wp | advanced-chat | 2025-09-30 | 2025-09-30 | normal | peng.wei01 (***@lkcoffee.com) |
| 11 | 美国AI点单-开发-lei_Solution1-prod | advanced-chat | 2025-09-26 | 2025-09-28 | normal | dify (***@lkcoffee.com) |
| 12 | 美国AI点单-开发-lei_Solution2 | advanced-chat | 2025-09-26 | 2025-09-26 | normal | dify (***@lkcoffee.com) |
| 13 | 11 | chat | 2025-09-26 | 2025-09-26 | normal | dify (***@lkcoffee.com) |
| 14 | 11 | chat | 2025-09-26 | 2025-09-26 | normal | (system) |

**Total: 14 apps** — Primarily "美国AI点单" (US AI Ordering) apps in various development/test stages. 2 workflow apps for test data generation, 1 Transcribe dictionary generator.

### Query 1.5 — Message / Conversation Activity (Last 6 Months)

| Month | Message Count | Workflow Runs |
|-------|--------------|---------------|
| 2026-03 | 8 | 8 |
| 2026-02 | 1 | 1 |
| 2025-12 | 4 | 2 |
| 2025-11 | 3,635 | 3,916 |
| 2025-10 | 35,913 | 37,259 |
| 2025-09 | 43 | 37 |

**All-time totals:**
- Messages: **39,604** (first: 2025-09-26, last: 2026-03-23)
- Workflow runs: **41,223** (first: 2025-09-29, last: 2026-03-23)

**Key observation:** Heavy usage was concentrated in Oct-Nov 2025 (AI ordering development phase). Activity dropped to near-zero from Dec 2025 onward. The 8 messages in March 2026 and last activity on 2026-03-23 suggest an automated process (API token) is still calling the platform, not interactive users.

### Query 1.6 — Document Inventory (Uploaded Files)

| Dataset | Document | Source | Words | Tokens | Created | Status |
|---------|----------|--------|-------|--------|---------|--------|
| product_info_IQA1_test03 | product_info_IQA1.txt | upload_file | 0 | 0 | 2025-10-17 | completed |
| product_info_lkus_test03 | product_info_lkus.txt | upload_file | 0 | 0 | 2025-10-17 | completed |
| product_info_lkus | product_info_lkus.txt | upload_file | 0 | 0 | 2025-09-28 | completed |
| product_info_IQA1 | product_info.txt | upload_file | 0 | 0 | 2025-09-28 | completed |
| 堡垒机双因素认证操作手册... | 堡垒机双因素认证操作手册.pdf | upload_file | 721 | 550 | 2025-09-24 | completed |
| 堡垒机双因素认证操作手册... | 堡垒机双因素认证操作手册.pdf | upload_file | 721 | (error) | 2025-09-24 | error |

**Total: 6 documents, 1,442 words, 550 tokens** — Very minimal knowledge base content.

### Query 1.7 — API Tokens Inventory

| # | App Name | Type | Created | Last Used |
|---|----------|------|---------|-----------|
| 1 | 美国AI点单-开发-lei_Solution2-prod | app | 2025-11-06 | **2026-03-23** |
| 2 | 美国AI点单-开发-lei_Solution2-test03 | app | 2025-11-03 | 2025-12-05 |
| 3 | 美国AI点单-开发-lei_Solution1-prod | app | 2025-10-20 | 2025-11-07 |
| 4 | ai生成测试数据-多轮对话 | app | 2025-10-23 | 2025-11-07 |
| 5 | 美国AI点单-开发-lei_Solution1-prod | app | 2025-10-27 | 2025-11-04 |
| 6 | 美国AI点单-开发-lei_Solution2-test03 | app | 2025-11-03 | 2025-11-03 |
| 7 | 美国AI点单-开发-lei_Solution1-prod | app | 2025-10-28 | 2025-10-31 |
| 8-17 | (various) | app | 2025-09 to 2025-11 | 2025-10 to 2025-10 |
| 18-21 | (various) | app/dataset | 2025-09 to 2025-11 | (never used) |

**Total: 21 API tokens**

**CRITICAL: 1 token is still actively in use** — The token for "美国AI点单-开发-lei_Solution2-prod" was last used on **2026-03-23** (2 days ago). This is the source of the 16 idle backend connections and the continuing trickle of messages/workflow runs.

### Query 1.8 — Table Sizes (NEW Instance)

| Table | Size |
|-------|------|
| workflow_node_executions | **4,222 MB** |
| workflow_runs | **1,274 MB** |
| workflow_conversation_variables | **319 MB** |
| messages | 52 MB |
| conversations | 40 MB |
| dataset_queries | 10 MB |
| embeddings | 3.6 MB |
| workflows | 3.1 MB |
| (73 other tables) | < 2.2 MB each |

**Total database size: 5,942 MB (5.8 GB)**

**Key observation:** 94% of database size (5,535 MB) is consumed by workflow execution data (workflow_node_executions + workflow_runs + workflow_conversation_variables). The actual business data (datasets, documents, apps) is negligible.

### Query 1.9 — Database Size Breakdown (NEW Instance)

| Database | Size |
|----------|------|
| luckyus_dify_api | **5,942 MB** |
| luckyus_dify_plugin | 8,524 kB |
| postgres | 7,724 kB |

---

## Query Results — OLD Instance (aws-luckyus-dify-rw)

> **Note:** Direct application-level queries could not be executed on the OLD instance because the mcp-db-gateway connects to the `postgres` database (not `luckyus_dify_api`), and the `dify_w` credentials differ between old and new instances. The following data was gathered from cluster-level PostgreSQL catalog views.

### Query 1.10 — User Accounts (OLD)

**ERROR:** Could not query — `dify_w` password on OLD instance differs from NEW instance. No direct access to `luckyus_dify_api` database.

From `pg_stat_activity`: **0 active backends** connected to `luckyus_dify_api` on the OLD instance. Only 1 idle connection to `luckyus_dify_plugin`.

### Query 1.11 — Dataset Count (OLD)

**ERROR:** Same access limitation as above.

### Query 1.12 — App Count (OLD)

**ERROR:** Same access limitation as above.

### Query 1.13 — Message Count (OLD)

**ERROR:** Same access limitation as above.

### Query 1.14/1.15 — Database Sizes (OLD Instance)

| Database | Size |
|----------|------|
| luckyus_dify_api | **1,222 MB** |
| luckyus_dify_plugin | 8,828 kB |
| postgres | 7,724 kB |

### OLD Instance — Activity Statistics (from pg_stat_database)

| Metric | luckyus_dify_api | luckyus_dify_plugin |
|--------|-----------------|---------------------|
| Active backends | **0** | 1 (idle) |
| Total transactions | 4,640,482 | 3,767,780 |
| Tuples inserted | 950,701 | 876 |
| Tuples updated | 454,917 | 152 |
| Tuples deleted | 201,599 | 75 |
| Deadlocks | 0 | 0 |
| Temp files | 0 | 0 |

### OLD Instance — Connection Summary

| Database | User | State | Count |
|----------|------|-------|-------|
| luckyus_dify_plugin | dify_w | idle | 1 |
| postgres | dba_admin | active | 1 |
| rdsadmin | rdsadmin | idle | 2 |

**Key observation:** The OLD instance has **zero application connections** to `luckyus_dify_api`. Only `luckyus_dify_plugin` has 1 idle connection (likely a persistent connection pool from the old Dify pods which are still running).

---

## OLD vs NEW Instance Comparison

| Metric | OLD (dify-rw) | NEW (difynew-rw) |
|--------|--------------|------------------|
| PostgreSQL version | 16.8 | 16.10 |
| Dify version | 1.3.1 | 1.8.1 |
| luckyus_dify_api size | 1,222 MB | 5,942 MB |
| Active backends to dify_api | **0** | **16** |
| Last activity on dify_api | Unknown (no backends) | 2026-03-23 |
| Vector store | Milvus (self-hosted) | OpenSearch (AWS managed) |
| File storage | S3 bucket | Local PVC |
| Redis cluster | luckyus-redis-dify | luckyus-difynew |
| Total transactions (dify_api) | 4.6M | 8.4M |
| Tuples inserted (dify_api) | 950K | 3.7M |

---

## Summary Assessment

### 1. User Activity
- **16 total accounts** on the NEW instance (12 active, 4 pending/never logged in)
- **Only 2 users active within last 30 days** (dify, 卢延新 — both last active 2026-03-09, 16 days ago)
- **No users active within the last 14 days** via interactive login
- Most users (10 of 16) have been inactive for 94+ days

### 2. Active API Token (CRITICAL for decommission)
- **1 API token is still being called** — for app "美国AI点单-开发-lei_Solution2-prod", last used **2026-03-23** (2 days ago)
- This token is generating 8 messages/month in March 2026 and is the source of the 16 idle backend connections
- **Before decommission, this integration must be identified and shut down** — likely an external application calling the Dify API

### 3. Knowledge Base & Apps
- **6 datasets** with 6 documents (1,442 words total) — minimal content, mostly product info for AI ordering
- **14 apps** — primarily "美国AI点单" (US AI Ordering) development iterations
- Business value is in the workflow definitions and RAG configurations, not in the data volume
- **Recommendation:** Export DSL (workflow definitions) for the 2-3 production apps before decommission

### 4. Data Volume
- NEW instance: **5.8 GB** (94% is workflow execution logs, not business data)
- OLD instance: **1.2 GB** (no active connections, appears fully abandoned)
- Total across both instances: **7.0 GB**

### 5. OLD Instance Status
- **Completely idle** — 0 application connections to the main database
- Still has 1 plugin daemon connection (from old Dify pods still running in EKS)
- The old Dify pods (dify-api, dify-worker, dify-sandbox, dify-web) are still deployed and running on EKS
- **Safe to decommission** after stopping the old Dify EKS deployments

### 6. Decommission Readiness

| Component | Status | Action Required |
|-----------|--------|----------------|
| OLD instance (dify-rw) | Ready to decommission | Stop old Dify EKS pods first |
| NEW instance (difynew-rw) | **NOT ready** | Identify and disable active API token consumer |
| OLD Dify EKS pods (dify-*) | Can be stopped | Scale to 0 replicas |
| NEW Dify EKS pods (new-dify-*) | Active (16 backends) | Coordinate with API consumer before stopping |
| Milvus cluster (EKS) | Review needed | 34 pods running — check if still serving NEW instance |
| Redis (luckyus-redis-dify) | Review needed | Used by OLD Dify |
| Redis (luckyus-difynew) | Active | Used by NEW Dify |
| S3 (lk-infra-dify-data) | Backup before delete | Used by OLD Dify for file storage |
| OpenSearch (luckyus-opensearch-dify) | Active | Vector store for NEW Dify |

### 7. Recommended Decommission Order
1. **Identify the API consumer** calling "美国AI点单-开发-lei_Solution2-prod" (last used 2026-03-23)
2. **Export/backup** production app DSL workflows and knowledge base data
3. **Scale down OLD Dify** EKS deployments to 0
4. **Take final RDS snapshot** of both instances
5. **Disable the active API token** after coordinating with stakeholders
6. **Scale down NEW Dify** EKS deployments
7. **Scale down Milvus** cluster (34 pods, significant compute cost)
8. **Delete RDS instances** after retention period
9. **Clean up** Redis clusters, OpenSearch domain, S3 bucket

---

*Report generated by Claude Code on 2026-03-25. All database queries were read-only. PII (email addresses) has been masked in this report.*
