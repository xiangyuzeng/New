# Phase 4: Runtime Parameter Verification via MCP

**Generated**: 2026-04-11 (updated with live 8.4 data)  
**8.0 Instance**: aws-luckyus-salesorder-rw (8.0.40, luckyus-prod-80-new-groupconcatmaxlen)  
**8.0 Cross-check**: aws-luckyus-dbatest-rw (8.0.42, luckyus-prod-80-new)  
**8.4 Instance**: aws-luckyus-dba84test (8.4.7, default.mysql8.4)  
**8.4 Cross-check**: aws-luckyus-datalink-84test (8.4.7, default.mysql8.4)

---

## A. Authentication Plugin Status

### A1. 8.0 Production (salesorder-rw)

| Variable | Value |
|----------|-------|
| `authentication_policy` | `*` |
| `default_authentication_plugin` | `mysql_native_password` |

#### User Plugin Distribution (salesorder-rw)

| Plugin | User Count |
|--------|-----------|
| `mysql_native_password` | **27** |
| `caching_sha2_password` | 3 |
| `auth_socket` | 1 |

> **87% mysql_native_password** — confirms the criticality of setting `mysql_native_password=ON` in the 8.4 parameter group.

### A2. 8.4 Test Instance (dba84test)

| Variable | Value |
|----------|-------|
| `authentication_policy` | `*:caching_sha2_password` |
| `mysql_native_password` | **(not loaded — empty result)** |

> In 8.4, `default_authentication_plugin` is **removed**. The `mysql_native_password` plugin is **not loaded by default** — `SHOW VARIABLES LIKE 'mysql_native_password'` returns 0 rows. This confirms the plugin must be explicitly enabled via `mysql_native_password=ON` in the parameter group.

#### User Plugin Distribution (dba84test)

| Plugin | User Count |
|--------|-----------|
| `caching_sha2_password` | **6** |
| `auth_socket` | 1 |
| `mysql_native_password` | **0** |

> On a default 8.4 instance with no custom parameter group, **zero users** use `mysql_native_password`. All new accounts default to `caching_sha2_password`. After applying `mysql_native_password=ON`, existing 8.0-migrated users will retain their plugin.

---

## B. Runtime Parameter Comparison: 8.0 Custom vs 8.4 Defaults (Runtime-Verified)

### Our 18 Custom Parameters

| # | Parameter | 8.0 Runtime (Custom) | 8.4 Runtime Default | Our 8.4 Value | Override Needed? |
|---|-----------|---------------------|---------------------|---------------|-----------------|
| 1 | `mysql_native_password` | N/A (8.0) | **Not loaded (OFF)** | **ON** | **YES** |
| 2 | `binlog_order_commits` | **0** | 1 | **0** | **YES** |
| 3 | `binlog_rows_query_log_events` | **0** | 0 | **0** | No (matches default) |
| 4 | `enforce_gtid_consistency` | **ON** | OFF | **ON** | **YES** |
| 5 | `gtid-mode` | **ON** | OFF_PERMISSIVE | **ON** | **YES** |
| 6 | `innodb_adaptive_hash_index` | **0** | **0 (OFF)** | **0** | No (matches default) ★ |
| 7 | `innodb_lock_wait_timeout` | **20** | 50 | **20** | **YES** |
| 8 | `innodb_print_all_deadlocks` | **1** | 0 (OFF) | **1** | **YES** |
| 9 | `innodb_strict_mode` | **0** | 1 (ON) | **0** | **YES** |
| 10 | `log_bin_trust_function_creators` | **1** | 0 (OFF) | **1** | **YES** |
| 11 | `long_query_time` | **0.1** | 10 | **0.1** | **YES** |
| 12 | `lower_case_table_names` | **1** | 0 | **1** | **YES** |
| 13 | `max_connections` | **4000** | 60 | **4000** | **YES** |
| 14 | `optimizer_switch` | **prefer_ordering_index=off** + 24 others | all defaults (prefer_ordering_index=on) | **same 17 flags** | **YES** |
| 15 | `performance_schema` | **1** | 0 (OFF) | **1** | **YES** |
| 16 | `slow_query_log` | **1** | 0 (OFF) | **1** | **YES** |
| 17 | `sql_mode` | **5 modes (no ONLY_FULL_GROUP_BY)** | **1 mode (NO_ENGINE_SUBSTITUTION only)** | **5 modes** | **YES** |
| 18 | `transaction_isolation` | **READ-COMMITTED** | REPEATABLE-READ | **READ-COMMITTED** | **YES** |

> **Result**: 16 of 18 parameters require explicit override from 8.4 defaults. `binlog_rows_query_log_events` matches the 8.4 default. `mysql_native_password` is a new addition for 8.4.

#### ★ Notable Discovery: `innodb_adaptive_hash_index`

The RDS MySQL 8.4 default for `innodb_adaptive_hash_index` is **0 (OFF)** at runtime — matching our custom override. This differs from MySQL community documentation which lists the default as ON. Our override is now redundant but harmless — keeping it ensures the value remains explicit regardless of future default changes.

#### ★ Notable Discovery: `sql_mode` Radical Simplification

MySQL 8.4 drastically simplifies `sql_mode` from 6 modes (8.0) to just **1 mode**:
- **8.0 default**: `ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION`
- **8.4 runtime default**: `NO_ENGINE_SUBSTITUTION`
- **Our setting**: `STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION` (5 modes, no ONLY_FULL_GROUP_BY)

This means our 8.4 config actually **adds** strictness compared to the 8.4 default, which is the desired behavior for production.

#### ★ Notable Discovery: `gtid_mode` Default

The 8.4 runtime default for `gtid_mode` is `OFF_PERMISSIVE` (not plain `OFF`). This is an RDS-specific default that allows GTID transactions to be received but not generated. Our override to `ON` is required for replication.

### 8 Dropped Explicit Parameters (were in 8.0 group, removed from 8.4 group)

| Parameter | 8.0 Runtime | 8.4 Runtime Default | Safe to Drop? |
|-----------|------------|---------------------|---------------|
| `binlog_checksum` | CRC32 | CRC32 | **YES** — same default |
| `binlog_format` | ROW | ROW (deprecated) | **YES** — ROW is only option in 8.4 |
| `binlog_row_image` | FULL | FULL | **YES** — same default |
| `character_set_server` | utf8mb4 | utf8mb4 | **YES** — same default |
| `innodb_deadlock_detect` | 1 (ON) | 1 (ON) | **YES** — same default |
| `log_output` | FILE | FILE | **YES** — same default |
| `log_queries_not_using_indexes` | 0 (OFF) | 0 (OFF) | **YES** — same default |
| `log_slow_admin_statements` | 0 (OFF) | 0 (OFF) | **YES** — same default |

> **All 8 dropped parameters confirmed safe via runtime verification** — 8.4 defaults match our 8.0 explicit values.

---

## C. Cross-Instance Consistency Checks

### C1. 8.0 Cross-Instance (salesorder-rw vs dbatest-rw)

| Parameter | salesorder-rw | dbatest-rw | Match? |
|-----------|-------------|------------|--------|
| binlog_format | ROW | ROW | YES |
| lower_case_table_names | 1 | 1 | YES |
| transaction_isolation | READ-COMMITTED | READ-COMMITTED | YES |
| temptable_use_mmap | 1 | 1 | YES |
| max_connections | 4000 | 4000 | YES |
| innodb_lock_wait_timeout | 20 | 20 | YES |
| long_query_time | 0.1 | 0.1 | YES |
| innodb_adaptive_hash_index | 0 | 0 | YES |
| innodb_strict_mode | 0 | 0 | YES |
| performance_schema | 1 | 1 | YES |
| slow_query_log | 1 | 1 | YES |
| enforce_gtid_consistency | ON | ON | YES |
| sql_mode | 5 modes | 5 modes | YES |

> **100% consistent** across both 8.0 instances despite different minor versions (8.0.40 vs 8.0.42).

### C2. 8.4 Cross-Instance (dba84test vs datalink-84test)

| Parameter | dba84test | datalink-84test | Match? |
|-----------|-----------|-----------------|--------|
| binlog_format | ROW | ROW | YES |
| lower_case_table_names | 0 | 0 | YES |
| transaction_isolation | REPEATABLE-READ | REPEATABLE-READ | YES |
| temptable_use_mmap | OFF | OFF | YES |
| max_connections | 60 | 60 | YES |
| innodb_lock_wait_timeout | 50 | 50 | YES |
| long_query_time | 10.0 | 10.0 | YES |
| innodb_adaptive_hash_index | 0 | 0 | YES |
| innodb_strict_mode | 1 | 1 | YES |
| innodb_print_all_deadlocks | 0 | 0 | YES |
| performance_schema | 0 | 0 | YES |
| slow_query_log | 0 | 0 | YES |
| enforce_gtid_consistency | OFF | OFF | YES |
| binlog_order_commits | 1 | 1 | YES |
| sql_mode | NO_ENGINE_SUBSTITUTION | NO_ENGINE_SUBSTITUTION | YES |

> **100% consistent** across both 8.4 test instances. Both are on `default.mysql8.4` with no custom parameter group — these values represent ground-truth 8.4 defaults.

---

## D. optimizer_switch Detailed Analysis

### Current 8.0 Runtime (25 flags)

```
index_merge=on, index_merge_union=on, index_merge_sort_union=on,
index_merge_intersection=on, engine_condition_pushdown=on,
index_condition_pushdown=on, mrr=on, mrr_cost_based=on,
block_nested_loop=on, batched_key_access=off, materialization=on,
semijoin=on, loosescan=on, firstmatch=on, duplicateweedout=on,
subquery_materialization_cost_based=on, use_index_extensions=on,
condition_fanout_filter=on, derived_merge=on, use_invisible_indexes=off,
skip_scan=on, hash_join=on, subquery_to_derived=off,
prefer_ordering_index=off, hypergraph_optimizer=off,
derived_condition_pushdown=on
```

### 8.4 Runtime Default (26 flags — from dba84test)

```
index_merge=on, index_merge_union=on, index_merge_sort_union=on,
index_merge_intersection=on, engine_condition_pushdown=on,
index_condition_pushdown=on, mrr=on, mrr_cost_based=on,
block_nested_loop=on, batched_key_access=off, materialization=on,
semijoin=on, loosescan=on, firstmatch=on, duplicateweedout=on,
subquery_materialization_cost_based=on, use_index_extensions=on,
condition_fanout_filter=on, derived_merge=on, use_invisible_indexes=off,
skip_scan=on, hash_join=on, subquery_to_derived=off,
prefer_ordering_index=on, hypergraph_optimizer=off,
derived_condition_pushdown=on, hash_set_operations=on
```

### Our Planned 8.4 optimizer_switch (17 flags explicitly set)

```
index_merge=on, index_merge_union=on, index_merge_sort_union=on,
index_merge_intersection=on, engine_condition_pushdown=on,
index_condition_pushdown=on, mrr=on, mrr_cost_based=on,
block_nested_loop=on, batched_key_access=off, materialization=on,
semijoin=on, loosescan=on, firstmatch=on,
subquery_materialization_cost_based=on, use_index_extensions=on,
prefer_ordering_index=off
```

### Gap Analysis: Flags NOT in our explicit list (will inherit 8.4 defaults)

| Flag | 8.0 Runtime Value | 8.4 Runtime Default | Risk |
|------|-------------------|---------------------|------|
| `duplicateweedout` | on | on | LOW — same |
| `condition_fanout_filter` | on | on | LOW — same |
| `derived_merge` | on | on | LOW — same |
| `use_invisible_indexes` | off | off | LOW — same |
| `skip_scan` | on | on | LOW — same |
| `hash_join` | on | on | LOW — same |
| `subquery_to_derived` | off | off | LOW — same |
| `hypergraph_optimizer` | off | off | LOW — same |
| `derived_condition_pushdown` | on | on | LOW — same |
| **`hash_set_operations`** | N/A (new in 8.4) | **on** | **LOW — new flag, beneficial** |

> **No risk**: All 9 inherited flags maintain their current 8.0 values in 8.4. The new `hash_set_operations=on` flag enables hash-based INTERSECT/EXCEPT operations — a performance improvement with no backward-compat concern.

### Key Difference: `prefer_ordering_index`

| | 8.0 (our config) | 8.4 Default | Our 8.4 Config |
|---|---|---|---|
| `prefer_ordering_index` | **off** | **on** | **off** (explicit override) |

Our explicit override keeps this **off** — this was a deliberate tuning decision to prevent the optimizer from preferring index-based ordering over potentially more efficient query plans.

---

## E. temptable_use_mmap Baseline (Runtime-Verified)

| Instance | Version | temptable_use_mmap | Source |
|----------|---------|-------------------|--------|
| salesorder-rw | 8.0.40 | **ON** | MCP runtime query |
| dbatest-rw | 8.0.42 | **ON** | MCP runtime query |
| dba84test | 8.4.7 | **OFF** | MCP runtime query |
| datalink-84test | 8.4.7 | **OFF** | MCP runtime query |

> **Confirmed via runtime**: MySQL 8.4 defaults `temptable_use_mmap` to **OFF**, meaning temp tables will use InnoDB on-disk instead of memory-mapped files. This could increase disk I/O for large temp tables on `db.t4g.micro` instances (1GB RAM). Monitor `Created_tmp_disk_tables` after upgrade.

---

## F. Recommendations

1. **All 18 custom parameters validated via runtime queries** — all exist in 8.4, override values are correct
2. **All 8 dropped explicit parameters confirmed safe** — 8.4 runtime defaults match our 8.0 values
3. **optimizer_switch gap is safe** — 9 inherited flags keep current values, 1 new flag (`hash_set_operations`) is beneficial
4. **`innodb_adaptive_hash_index` override is now redundant** — 8.4 RDS default is already OFF, but keeping our explicit `0` is harmless and ensures future-proofing
5. **Monitor `temptable_use_mmap=OFF` impact** on temp-table-heavy queries after upgrade, especially on t4g.micro instances
6. **Authentication**: Production fleet has 87% `mysql_native_password` users — the `mysql_native_password=ON` parameter is essential. Plan `caching_sha2_password` migration as Phase 3 (post-upgrade stabilization)
7. **`sql_mode` change is significant** — 8.4 default is just `NO_ENGINE_SUBSTITUTION`. Our 5-mode config adds strictness, which is correct for production
8. **Switch 8.4 test instances to `luckyus-prod-84-new`** after creation — validate parameter group on 8.4 before fleet rollout
