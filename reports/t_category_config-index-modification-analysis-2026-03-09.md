# Index Modification Analysis: `luckyus_opshop.t_category_config`

**Date:** 2026-03-09
**Analyst:** David Zeng (DBA)
**Requested By:** 陈海峰
**Host:** `aws-luckyus-opshop-rw.cxwu08m2qypw.us-east-1.rds.amazonaws.com:3306`
**Database/Table:** `luckyus_opshop.t_category_config`

---

## 1. Current Table Stats

| Property | Value |
|----------|-------|
| Engine | InnoDB |
| MySQL Version | 8.0.40 |
| Charset | utf8mb4 / utf8mb4_0900_ai_ci |
| Row Count (exact) | **1,822** |
| Data Size | 0.25 MB |
| Index Size | 0.20 MB |
| Total Size | **0.45 MB** |
| AUTO_INCREMENT | 1,824 |

### Current DDL

```sql
CREATE TABLE `t_category_config` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键id',
  `tenant` varchar(4) NOT NULL COMMENT '租户',
  `name` varchar(200) NOT NULL COMMENT '配置项名称',
  `code` varchar(100) NOT NULL COMMENT '配置项编码',
  `parent_code` varchar(100) DEFAULT NULL COMMENT '父类编码',
  `sort` int NOT NULL COMMENT '排序',
  `tag` varchar(100) DEFAULT NULL COMMENT '标签编码',
  `type` int NOT NULL COMMENT '配置类型',
  `show` tinyint DEFAULT '1' COMMENT '是否显示 0：否，1：是',
  `status` tinyint DEFAULT '0' COMMENT '是否有效 0：无效，1：有效',
  `create_by` bigint DEFAULT NULL,
  `creator_name` varchar(64) DEFAULT NULL,
  `create_time` datetime DEFAULT NULL,
  `modify_by` bigint DEFAULT NULL,
  `modifier_name` varchar(64) DEFAULT NULL,
  `modify_time` datetime DEFAULT NULL,
  `modifier_dept_id` bigint DEFAULT NULL,
  `display_style` varchar(100) DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_code_tenant` (`code`,`tenant`),
  KEY `idx_parent_code` (`parent_code`) USING BTREE,
  KEY `idx_tenant_sort` (`tenant`,`sort`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1824 DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci COMMENT='配置类别'
```

### Current Indexes

| Index Name | Type | Columns | Cardinality |
|------------|------|---------|-------------|
| `PRIMARY` | UNIQUE | `id` | 1,822 |
| `uniq_code_tenant` | UNIQUE | `code`, `tenant` | 1,707 |
| `idx_parent_code` | INDEX | `parent_code` | 28 |
| `idx_tenant_sort` | INDEX | `tenant`, `sort` | tenant=7, sort=247 |

### `type` Column Distribution

| type | row_count | percentage |
|------|-----------|-----------|
| 2 | 1,646 | 90.3% |
| 1 | 148 | 8.1% |
| 10 | 28 | 1.5% |

`type` is `int NOT NULL` — always populated, 3 distinct values across the table.

---

## 2. Data Uniqueness Validation

**Change:** `uniq_code_tenant (code, tenant)` → `uniq_code_tenant_type (code, tenant, type)`

### Check 1 — Duplicate (code, tenant) pairs

```sql
SELECT code, tenant, COUNT(*) AS cnt
FROM luckyus_opshop.t_category_config
GROUP BY code, tenant
HAVING cnt > 1;
```

**Result:** 0 rows — no duplicate (code, tenant) pairs exist.

### Check 2 — Any (code, tenant) paired with multiple type values

```sql
SELECT code, tenant, COUNT(DISTINCT type) AS type_count
FROM luckyus_opshop.t_category_config
GROUP BY code, tenant
HAVING type_count > 1;
```

**Result:** 0 rows — every (code, tenant) combination maps to exactly one `type`.

### Check 3 — Cardinality equivalence

```sql
SELECT
  COUNT(DISTINCT code, tenant)       AS distinct_code_tenant,
  COUNT(DISTINCT code, tenant, type) AS distinct_code_tenant_type
FROM luckyus_opshop.t_category_config;
```

**Result:** both = **1,822** (matches exact row count) — confirming that adding `type` does not change cardinality; the extended key is a strict 1:1 expansion of the current key.

### Uniqueness Validation Verdict: ✅ SAFE

No existing rows violate the proposed new constraint. The ADD INDEX step will succeed without error.

---

## 3. Query Dependency Analysis

Queries hitting `t_category_config` were sampled from `performance_schema.events_statements_summary_by_digest` (last reset window).

### Top Queries by Call Volume

| Rank | Calls | Avg Latency | Query Pattern |
|------|-------|-------------|---------------|
| 1 | 38,342 | ~1ms | `WHERE status=? AND type=? AND tenant=? ORDER BY sort ASC` |
| 2 | 12,050 | ~0.5ms | `WHERE code=? AND tenant=?` |
| 3–25 | < 500 each | — | Various admin/config lookups |

### EXPLAIN Analysis

#### Query 1 — High-volume list query (38,342 calls)

```sql
SELECT * FROM t_category_config
WHERE status = 1 AND type = 2 AND tenant = 'US01'
ORDER BY sort ASC;
```

| key | key_len | rows | Extra |
|-----|---------|------|-------|
| `idx_tenant_sort` | 18 | 247 | Using index condition; Using where |

**Index used: `idx_tenant_sort`** — this query does **NOT** touch `uniq_code_tenant` at all. Modifying or dropping `uniq_code_tenant` has **zero impact** on this query.

#### Query 2 — Point lookup (12,050 calls)

```sql
SELECT * FROM t_category_config
WHERE code = 'CATEGORY_001' AND tenant = 'US01';
```

| key | key_len | rows | Extra |
|-----|---------|------|-------|
| `uniq_code_tenant` | 418 | 1 | — |

**Index used: `uniq_code_tenant` (const table lookup).**

After the modification, `uniq_code_tenant_type (code, tenant, type)` provides a **left-prefix match** on `(code, tenant)`, so this query will use the new index with identical performance — no query changes required.

### Coverage Summary

| Query | Current Index | New Index Coverage | Impact |
|-------|---------------|-------------------|--------|
| `WHERE status+type+tenant ORDER BY sort` | `idx_tenant_sort` | No change | ✅ None |
| `WHERE code=? AND tenant=?` | `uniq_code_tenant` | `uniq_code_tenant_type` (left-prefix) | ✅ None |
| All other queries | Various | No change | ✅ None |

---

## 4. Risk Assessment

| Factor | Assessment | Risk |
|--------|------------|------|
| Table size | 1,822 rows / 0.45 MB | 🟢 Negligible |
| MySQL version | 8.0.40 — supports `ALGORITHM=INPLACE, LOCK=NONE` for ADD/DROP UNIQUE | 🟢 Online DDL |
| Data violations | 0 rows violate new constraint | 🟢 None |
| Query coverage gap | New index covers old index as left-prefix | 🟢 None |
| High-volume query impact | Top query uses `idx_tenant_sort`, unaffected | 🟢 None |
| DDL duration | ~1 second expected for table this size | 🟢 Instant |
| Replication lag risk | Negligible table size | 🟢 Low |
| Two-step window | Between Step 1 and Step 2, both old and new constraints coexist | 🟢 Zero-downtime |

**Overall Risk Rating: 🟢 LOW**

This operation is safe to perform during business hours without a maintenance window.

---

## 5. Final Recommended DDL

Per DBA guidance (陈海峰): add new index first, verify, then drop old — never drop-and-add in one statement to avoid any window without constraint coverage.

### Step 1 — Add New Unique Index

```sql
ALTER TABLE luckyus_opshop.t_category_config
  ADD UNIQUE KEY `uniq_code_tenant_type` (`code`, `tenant`, `type`),
  ALGORITHM=INPLACE, LOCK=NONE;
```

**Expected duration:** < 2 seconds
**Table locks:** None (online DDL)
**Replication:** Replicated automatically to read replicas

### Step 2 — Verify New Index (run before dropping old)

```sql
-- Confirm new index is present and populated
SHOW INDEX FROM luckyus_opshop.t_category_config
WHERE Key_name = 'uniq_code_tenant_type';

-- Re-run uniqueness check on new index
SELECT code, tenant, type, COUNT(*) AS cnt
FROM luckyus_opshop.t_category_config
GROUP BY code, tenant, type
HAVING cnt > 1;
-- Expected: 0 rows
```

### Step 3 — Drop Old Unique Index

```sql
ALTER TABLE luckyus_opshop.t_category_config
  DROP INDEX `uniq_code_tenant`,
  ALGORITHM=INPLACE, LOCK=NONE;
```

**Expected duration:** < 1 second
**Table locks:** None (online DDL)

---

## 6. Rollback Plan

If any step fails or the application behaves unexpectedly after Step 3, rollback is:

```sql
-- Restore original unique index (if dropped)
ALTER TABLE luckyus_opshop.t_category_config
  ADD UNIQUE KEY `uniq_code_tenant` (`code`, `tenant`),
  ALGORITHM=INPLACE, LOCK=NONE;

-- Remove new index (if desired)
ALTER TABLE luckyus_opshop.t_category_config
  DROP INDEX `uniq_code_tenant_type`,
  ALGORITHM=INPLACE, LOCK=NONE;
```

Since no data will be modified, rollback restores the exact original state instantly.

---

## 7. Maintenance Window Recommendation

**Recommendation: Business hours execution is acceptable — no maintenance window needed.**

Justification:
- Table is 0.45 MB with 1,822 rows; DDL completes in < 2 seconds
- `ALGORITHM=INPLACE, LOCK=NONE` means zero table-level locking
- The high-traffic query (38,342 calls, uses `idx_tenant_sort`) is completely unaffected
- The second query (12,050 calls) seamlessly transitions to the new index as a prefix match
- No application code changes are required

Suggested execution time if conservative preference: **weekday 14:00–16:00 EST** (low order activity mid-afternoon).

---

## 8. Execution Checklist

- [ ] Confirm with application team that no schema migration is currently running
- [ ] Run `SHOW PROCESSLIST` on `aws-luckyus-opshop-rw` — confirm no long-running transactions on `t_category_config`
- [ ] Execute **Step 1** (ADD INDEX) — note start/end time
- [ ] Execute **Step 2** verification queries — confirm 0 violations
- [ ] Execute **Step 3** (DROP INDEX) — note start/end time
- [ ] Run `SHOW INDEX FROM luckyus_opshop.t_category_config` — confirm final index set
- [ ] Monitor application error rate for 5 minutes post-execution
- [ ] Record completion in change log

---

*Report generated by DBA automation — Claude Code / mcp-db-gateway / performance_schema analysis*
