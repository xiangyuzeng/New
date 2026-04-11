# MySQL 8.4 Parameter Group Deep Audit — Summary Report

**Document ID**: LCNA-DBA-2026-021 Appendix  
**Date**: 2026-04-11 (updated with live 8.4 runtime verification)  
**Author**: David Zeng (DBA)  
**Status**: AUDIT COMPLETE — ALL PHASES VERIFIED

---

## 1. Executive Summary

This audit validates the design of 2 new MySQL 8.4 parameter groups for the Luckin Coffee NA RDS fleet upgrade (8.0 → 8.4). All data was collected via AWS CLI API calls and MCP database queries against live production and test instances.

### Key Findings

| Metric | Value |
|--------|-------|
| MySQL 8.0 engine parameters | 553 |
| MySQL 8.4 engine parameters | 536 |
| Parameters removed in 8.4 | 29 (truly removed) |
| Parameters renamed in 8.4 | 19 (slave_* → replica_*) |
| Parameters added in 8.4 | 12 (truly new) |
| AllowedValues changes | 5 (including tls_version, optimizer_switch) |
| **Our 18 custom params — all exist in 8.4** | **YES (18/18)** |
| **Breaking changes to our params** | **NONE** |
| Fleet instances audited | 63 |
| Instances in-sync | 62 (1 pending-reboot: dbatest-rw) |
| 8.4 runtime defaults verified | **YES (dba84test + datalink-84test)** |
| 8.4 parameter groups created | **NOT YET** |

### Verdict

**The `luckyus-prod-84-new` parameter group design is validated and ready for creation.** All 18 custom parameters exist in MySQL 8.4, no breaking changes affect our configuration, all 8 dropped explicit parameters have unchanged defaults in 8.4, and all values have been verified against live 8.4 runtime data.

---

## 2. Parameter Group Current State (Phase 1)

### Existing Parameter Groups (3 × MySQL 8.0)

| Parameter Group | Custom Params | Instances | Status |
|----------------|--------------|-----------|--------|
| `luckyus-prod-80-new` | 25 (17 custom + 8 explicit-default) | 56 | Active |
| `luckyus-prod` | 23 (missing 2 vs -80-new) | 2 (devops, ldas) | Active (legacy) |
| `luckyus-prod-80-new-groupconcatmaxlen` | 26 (25 + group_concat_max_len) | 1 (salesorder) | Active |

### Planned Parameter Groups (2 × MySQL 8.4)

| Parameter Group | Custom Params | Target Instances | Status |
|----------------|--------------|-----------------|--------|
| `luckyus-prod-84-new` | 18 | 62 (all except salesorder) | **NOT CREATED** |
| `luckyus-prod-84-new-groupconcatmaxlen` | 19 (18 + group_concat_max_len) | 1 (salesorder) | **NOT CREATED** |

### Design Change: 8.0 → 8.4 Parameter Group

| Change | Details |
|--------|---------|
| Params added | +1: `mysql_native_password=ON` (8.4 disables plugin by default) |
| Params dropped | -8: explicit-default locks removed (binlog_checksum, binlog_format, binlog_row_image, character_set_server, innodb_deadlock_detect, log_output, log_queries_not_using_indexes, log_slow_admin_statements) |
| Net change | 25 → 18 custom params (cleaner, less maintenance) |

---

## 3. 8.0 → 8.4 Default Changes (Phase 2)

### RDS API Limitation

The RDS `describe-engine-default-parameters` API returns `DefaultValue=NULL` for **all** parameters in both mysql8.0 and mysql8.4 families. Actual defaults were verified via runtime queries on `dba84test` and `datalink-84test` (Phase 4).

### Critical Changes Affecting Our Fleet

| Change | Parameter | Impact | Our Mitigation |
|--------|-----------|--------|---------------|
| Plugin disabled | `mysql_native_password` | 87% of prod users use this plugin | Set `mysql_native_password=ON` in PG |
| Param removed | `default_authentication_plugin` | Was set to mysql_native_password in 8.0 | Replaced by `mysql_native_password=ON` |
| Deprecated | `binlog_format` | ROW-only in 8.4 | Already ROW; dropped from explicit PG |
| New default | `temptable_use_mmap` | **OFF in 8.4** (was ON in 8.0) — runtime verified | Monitor temp table I/O post-upgrade |
| TLS tightened | `tls_version` | TLSv1.0/1.1 removed | Already using TLSv1.2+ |
| New optimizer flag | `hash_set_operations` | Added in 8.4 (default ON) — runtime verified | Inherits default — no action needed |
| sql_mode simplified | `sql_mode` | **8.4 default: only NO_ENGINE_SUBSTITUTION** (was 6 modes in 8.0) | Our 5-mode config adds strictness — correct |
| AHI default changed | `innodb_adaptive_hash_index` | **OFF in RDS 8.4** (differs from community docs) | Our override (0) now matches default — harmless |

### Renamed Parameters (19 total)

All `slave_*` → `replica_*` and `master_*` → `source_*` renames. None of these are in our custom parameter group, so **no impact** on our configuration. Application-level code using `SHOW SLAVE STATUS` is affected (tracked separately in LCNA-DBA-2026-021 deprecated SQL audit).

### Truly Removed Parameters (29 total)

Includes `default_authentication_plugin`, `expire_logs_days`, `innodb_log_file_size`, `innodb_log_files_in_group`, `relay_log_info_repository`, `master_info_repository`, and others. **None of these are in our custom parameter group.**

---

## 4. Confirmation Matrix: 18 Custom Parameters vs 8.4 (Runtime-Verified)

| # | Parameter | Our Value | In 8.4? | 8.4 Default (Runtime) | Override Needed? | Validated? |
|---|-----------|-----------|---------|----------------------|-----------------|-----------|
| 1 | `mysql_native_password` | ON | YES (new) | Not loaded (OFF) | **YES** | Runtime (8.4) |
| 2 | `binlog_order_commits` | 0 | YES | 1 | **YES** | Runtime (8.4) |
| 3 | `binlog_rows_query_log_events` | 0 | YES | 0 | No (matches) | Runtime (8.4) |
| 4 | `enforce_gtid_consistency` | ON | YES | OFF | **YES** | Runtime (8.4) |
| 5 | `gtid-mode` | ON | YES | OFF_PERMISSIVE | **YES** | Runtime (8.4) |
| 6 | `innodb_adaptive_hash_index` | 0 | YES | **0 (OFF)** ★ | No (matches) ★ | Runtime (8.4) |
| 7 | `innodb_lock_wait_timeout` | 20 | YES | 50 | **YES** | Runtime (8.4) |
| 8 | `innodb_print_all_deadlocks` | 1 | YES | 0 | **YES** | Runtime (8.4) |
| 9 | `innodb_strict_mode` | 0 | YES | 1 | **YES** | Runtime (8.4) |
| 10 | `log_bin_trust_function_creators` | 1 | YES | 0 | **YES** | Runtime (8.4) |
| 11 | `long_query_time` | 0.1 | YES | 10 | **YES** | Runtime (8.4) |
| 12 | `lower_case_table_names` | 1 | YES | 0 | **YES** | Runtime (8.4) |
| 13 | `max_connections` | 4000 | YES | 60 | **YES** | Runtime (8.4) |
| 14 | `optimizer_switch` | prefer_ordering_index=off + 16 others | YES | all defaults (prefer_ordering_index=on) | **YES** | Runtime (8.4) |
| 15 | `performance_schema` | 1 | YES | 0 | **YES** | Runtime (8.4) |
| 16 | `slow_query_log` | 1 | YES | 0 | **YES** | Runtime (8.4) |
| 17 | `sql_mode` | 5 modes (no ONLY_FULL_GROUP_BY) | YES | NO_ENGINE_SUBSTITUTION only ★ | **YES** | Runtime (8.4) |
| 18 | `transaction_isolation` | READ-COMMITTED | YES | REPEATABLE-READ | **YES** | Runtime (8.4) |

**Result: 18/18 parameters validated against live 8.4 runtime. 16/18 require explicit override (★ `innodb_adaptive_hash_index` now matches 8.4 default). All exist in MySQL 8.4.**

### ★ Notable Runtime Discoveries

1. **`innodb_adaptive_hash_index` = 0 (OFF)** in RDS MySQL 8.4 default — differs from community docs (listed as ON). Our override is now redundant but harmless.
2. **`sql_mode` = `NO_ENGINE_SUBSTITUTION` only** — 8.4 radically simplified from 6 modes to 1. Our 5-mode config adds strictness, which is correct for production.
3. **`gtid_mode` = `OFF_PERMISSIVE`** — RDS-specific default (not plain OFF). Allows receiving GTID transactions.
4. **`max_connections` = 60** on default 8.4 (t4g.micro formula-based). Our override to 4000 is essential.
5. **`authentication_policy` = `*:caching_sha2_password`** — more specific than 8.0's `*`.

---

## 5. Instance Mapping Summary (Phase 3)

| Parameter Group | Count | Status |
|----------------|-------|--------|
| luckyus-prod-80-new | 56 | All in-sync except dbatest-rw (pending-reboot) |
| luckyus-prod | 2 | devops-rw, ldas-rw — legacy, safe to consolidate |
| luckyus-prod-80-new-groupconcatmaxlen | 1 | salesorder-rw — in-sync |
| default.mysql8.4 | 2 | dba84test, datalink-84test — test instances (runtime-verified) |

### Anomalies

| Flag | Instance | Issue | Action |
|------|----------|-------|--------|
| pending-reboot | dbatest-rw | Parameter changes pending | Reboot (test instance, low risk) |
| Legacy PG | devops-rw, ldas-rw | Missing 2 params | Auto-resolved when migrating to -84-new |
| Default PG | dba84test, datalink-84test | On default.mysql8.4 | Switch to luckyus-prod-84-new after creation |
| Version drift | iluckyams-rw (8.0.44) | auto_minor_upgrade=true | No impact on upgrade plan |

---

## 6. Runtime Verification Results (Phase 4)

### 8.0 Production Verification

- **Instances queried**: salesorder-rw (8.0.40), dbatest-rw (8.0.42)
- **Cross-instance consistency**: 100% — all parameters match between instances
- **Authentication plugins**: 27 mysql_native_password, 3 caching_sha2_password, 1 auth_socket
- **optimizer_switch**: 25 flags active, all at expected values

### 8.4 Test Instance Verification

- **Instances queried**: dba84test (8.4.7), datalink-84test (8.4.7)
- **Cross-instance consistency**: 100% — all parameters match between both 8.4 instances
- **Both on `default.mysql8.4`** — runtime values represent ground-truth 8.4 defaults
- **Authentication plugins (8.4 default)**: 6 caching_sha2_password, 1 auth_socket, 0 mysql_native_password
- **optimizer_switch**: 26 flags (25 from 8.0 + `hash_set_operations=on`)
- **temptable_use_mmap**: OFF (confirmed)
- **sql_mode**: `NO_ENGINE_SUBSTITUTION` only (1 mode vs 8.0's 6)

---

## 7. New 8.4 Parameters to Consider

| Parameter | 8.4 Runtime Default | Recommendation | Priority |
|-----------|---------------------|----------------|----------|
| `mysql_native_password` | Not loaded (OFF) | **Already in our config (ON)** | DONE |
| `authentication_policy` | `*:caching_sha2_password` | Plan caching_sha2_password migration timeline | LOW (post-upgrade) |
| `temptable_use_mmap` | OFF (runtime confirmed) | Monitor temp table I/O on t4g.micro after upgrade | MEDIUM |
| `restrict_fk_on_non_standard_key` | ON | Good safety default — leave as-is | LOW |
| `hash_set_operations` (optimizer_switch) | ON (runtime confirmed) | Beneficial — inherits default via our partial optimizer_switch | NONE |
| `connection_memory_chunk_size` | N/A (not in RDS) | Not available in RDS params | N/A |

---

## 8. Risk Items Requiring Further Testing

| Risk | Severity | Description | Mitigation |
|------|----------|-------------|------------|
| `temptable_use_mmap=OFF` | MEDIUM | 8.4 disables mmap for temp tables by default (runtime confirmed). Could increase disk I/O on memory-constrained t4g.micro instances (40 instances, 1GB RAM). | Monitor `Created_tmp_disk_tables` metric post-upgrade. Consider adding explicit `temptable_use_mmap=ON` if regression detected. |
| `optimizer_switch` partial set | LOW | Our config sets 17 of 26 flags explicitly. 9 flags + 1 new flag inherit 8.4 defaults. | Verified all inherited flags match current 8.0 runtime values via live queries. No risk. |
| `authentication_policy` | LOW | New auth policy framework in 8.4: `*:caching_sha2_password`. Currently permissive for first factor. | No immediate action. Plan caching_sha2_password migration as separate project. |
| `dbatest-rw` pending-reboot | LOW | Has unapplied parameter changes. | Reboot during next maintenance window. |

---

## 9. Recommendations

### Immediate Actions (Before Upgrade)

1. **Create parameter groups**: Run the creation scripts from `/app/reports/mysql-8.4-parameter-group-config.md` Section 4.1 and 4.2
2. **Switch 8.4 test instances to `luckyus-prod-84-new`**: Validate parameter group on 8.4 before fleet rollout (script in Section 4.4)
3. **Reboot dbatest-rw**: Clear pending-reboot status

### Post-Creation Verification

4. Run verification script (Section 4.3 of parameter-group-config.md) to confirm 18 params in luckyus-prod-84-new
5. Query dba84test via MCP after applying custom PG — verify all 18 params applied correctly
6. Run test queries on dba84test to validate application compatibility

### Post-Upgrade Monitoring

7. Monitor `Created_tmp_disk_tables` for temptable_use_mmap impact
8. Monitor `Slow_queries` rate during first 48 hours
9. Verify `mysql_native_password` plugin is active on all upgraded instances
10. Validate `sql_mode` includes all 5 expected modes on each upgraded instance

---

## 10. Audit Files

| File | Phase | Description |
|------|-------|-------------|
| `phase1-current-state.txt` | 1 | Raw parameter dumps from 5 groups (3 exist, 2 NOT CREATED) |
| `defaults-80-raw.json` | 2 | Full mysql8.0 engine defaults (553 params) |
| `defaults-84-raw.json` | 2 | Full mysql8.4 engine defaults (536 params) |
| `diff_defaults.py` | 2 | Python comparison script |
| `phase2-default-diff.md` | 2 | Detailed diff: removed/added/renamed/AllowedValues/metadata |
| `phase3-instance-mapping.md` | 3 | All 63 instances mapped to parameter groups |
| `phase3-instances-raw.txt` | 3 | Raw AWS CLI output |
| `phase4-runtime-check.md` | 4 | Runtime parameter verification (8.0 prod + **8.4 test — live verified**) |
| `SUMMARY.md` | 5 | This document |

---

*End of MySQL 8.4 Parameter Group Deep Audit — LCNA-DBA-2026-021*
