# Phase 2: MySQL 8.0 vs 8.4 Engine Default Parameter Diff

**Generated**: 2026-04-11  
**Report**: LCNA-DBA-2026-021 Appendix  
**MySQL 8.0 total parameters**: 553  
**MySQL 8.4 total parameters**: 536  
**Net difference**: -17 params

> **Note**: RDS `describe-engine-default-parameters` returns `DefaultValue=NULL` for ALL parameters
> in both mysql8.0 and mysql8.4 families. Actual runtime defaults are verified in Phase 4 via MCP
> queries against instances running default parameter groups.

---

## A. Parameters REMOVED in 8.4 (29 truly removed, 19 renamed)

### Truly Removed (no rename detected)

| # | Parameter | DataType | ApplyType | Impact |
|---|-----------|----------|-----------|--------|
| 1 | `avoid_temporal_upgrade` | boolean | dynamic |   |
| 2 | `binlog_transaction_dependency_tracking` | list | dynamic |   |
| 3 | `character-set-client-handshake` | boolean | static |   |
| 4 | `collation_database` | string | dynamic |   |
| 5 | `core-file` | boolean | static |   |
| 6 | `default_authentication_plugin` | string | static | CRITICAL REMOVED in 8.4. Replaced by authentication_policy. |
| 7 | `expire_logs_days` | integer | dynamic | INFO REMOVED in 8.4. Use binlog_expire_logs_seconds instead. |
| 8 | `gtid_mode` | string | dynamic |   |
| 9 | `innodb_doublewrite_batch_size` | integer | dynamic |   |
| 10 | `innodb_log_file_size` | integer | static | INFO REMOVED in 8.4. Replaced by innodb_redo_log_capacity. |
| 11 | `innodb_log_files_in_group` | integer | static | INFO REMOVED in 8.4. Replaced by innodb_redo_log_capacity. |
| 12 | `log_bin_use_v1_row_events` | boolean | static |   |
| 13 | `master-info-repository` | string | static |   |
| 14 | `master_info_repository` | string | dynamic |   |
| 15 | `new` | string | dynamic |   |
| 16 | `old-style-user-limits` | boolean | static |   |
| 17 | `relay_log_info_file` | string | static |   |
| 18 | `relay_log_info_repository` | string | static |   |
| 19 | `rpl_semi_sync_master_wait_for_slave_count` | integer | dynamic |   |
| 20 | `rpl_semi_sync_master_wait_point` | string | dynamic |   |
| 21 | `show_old_temporals` | boolean | dynamic |   |
| 22 | `skip-character-set-client-handshake` | boolean | static |   |
| 23 | `skip-slave-start` | boolean | static |   |
| 24 | `slave_allow_batching` | boolean | dynamic |   |
| 25 | `slave_rows_search_algorithms` | list | dynamic |   |
| 26 | `ssl_fips_mode` | string | dynamic |   |
| 27 | `sync_master_info` | integer | dynamic |   |
| 28 | `sync_relay_log_info` | integer | dynamic |   |
| 29 | `transaction_write_set_extraction` | string | dynamic |   |

### Renamed Parameters (slave_* → replica_*, master_* → source_*)

| # | Old Name (8.0) | New Name (8.4) |
|---|---------------|---------------|
| 1 | `init_slave` | `init_replica` |
| 2 | `log_slave_updates` | `log_replica_updates` |
| 3 | `log_slow_slave_statements` | `log_slow_replica_statements` |
| 4 | `master_verify_checksum` | `source_verify_checksum` |
| 5 | `rpl_stop_slave_timeout` | `rpl_stop_replica_timeout` |
| 6 | `slave_checkpoint_group` | `replica_checkpoint_group` |
| 7 | `slave_checkpoint_period` | `replica_checkpoint_period` |
| 8 | `slave_compressed_protocol` | `replica_compressed_protocol` |
| 9 | `slave_exec_mode` | `replica_exec_mode` |
| 10 | `slave_load_tmpdir` | `replica_load_tmpdir` |
| 11 | `slave_net_timeout` | `replica_net_timeout` |
| 12 | `slave_parallel_type` | `replica_parallel_type` |
| 13 | `slave_parallel_workers` | `replica_parallel_workers` |
| 14 | `slave_pending_jobs_size_max` | `replica_pending_jobs_size_max` |
| 15 | `slave_preserve_commit_order` | `replica_preserve_commit_order` |
| 16 | `slave_sql_verify_checksum` | `replica_sql_verify_checksum` |
| 17 | `slave_transaction_retries` | `replica_transaction_retries` |
| 18 | `slave_type_conversions` | `replica_type_conversions` |
| 19 | `sql_slave_skip_counter` | `sql_replica_skip_counter` |

## B. Parameters ADDED in 8.4 (12 truly new)

| # | Parameter | DataType | ApplyType | Description |
|---|-----------|----------|-----------|-------------|
| 1 | `authentication_policy` | string | dynamic | This parameter controls the default authentication plugin used to authenticate users. We recommend t |
| 2 | `connection_memory_chunk_size` | integer | dynamic | Set the chunking size for updates to the global memory usage counter Global_connection_memory. |
| 3 | `core_file` | boolean | static | Write a core file if mysqld dies. |
| 4 | `explain_json_format_version` | integer | dynamic | Determines the version of the JSON output format used by EXPLAIN FORMAT=JSON statements. |
| 5 | `group_replication_exit_state_action` | string | dynamic | Configures how Group Replication behaves when this server instance leaves the group unintentionally. |
| 6 | `innodb_numa_interleave` | boolean | static | Enables the NUMA interleave memory policy for allocation of the InnoDB buffer pool. |
| 7 | `mysql_native_password` | string | static | Enables the mysql_native_password authentication plugin. |
| 8 | `restrict_fk_on_non_standard_key` | boolean | dynamic | Disallow the creation of foreign keys referencing non-unique key or partial key. |
| 9 | `set_operations_buffer_size` | integer | dynamic | Sets the buffer size for INTERSECT and EXCEPT operations that use hash tables when the hash_set_oper |
| 10 | `skip_replica_start` | boolean | static | Tells the replica server not to start the replication threads when the server starts. |
| 11 | `temptable_use_mmap` | boolean | dynamic | Defines whether the TempTable storage engine allocates space for internal in-memory temporary tables |
| 12 | `tls_certificates_enforced_validation` | boolean | static | Controls whether certificate validation is enforced at startup. Discovery of an invalid certificate  |

## C. AllowedValues Changes (5 params)

> Since DefaultValue is always NULL, AllowedValues changes are the best signal from the API.

### `group_replication_consistency`
**Known impact**: New allowed value: BEFORE_ON_PRIMARY_FAILOVER.
- **8.0**: `EVENTUAL,BEFORE,AFTER,BEFORE_AND_AFTER`
- **8.4**: `EVENTUAL,BEFORE_ON_PRIMARY_FAILOVER,BEFORE,AFTER,BEFORE_AND_AFTER`

### `optimizer_switch`
**Known impact**: New flag: hash_set_operations added in 8.4.
- **8.0**: `default,batched_key_access=off,batched_key_access=on,block_nested_loop=off,block_nested_loop=on,condition_fanout_filter=off,condition_fanout_filter=on,derived_condition_pushdown=off,derived_condition_...`
- **8.4**: `default,batched_key_access=off,batched_key_access=on,block_nested_loop=off,block_nested_loop=on,condition_fanout_filter=off,condition_fanout_filter=on,derived_condition_pushdown=off,derived_condition_...`

### `ssl_cipher`
- **8.0**: `ECDHE-RSA-AES256-GCM-SHA384,ECDHE-RSA-AES128-GCM-SHA256,ECDHE-RSA-AES256-SHA384,ECDHE-RSA-AES128-SHA256,ECDHE-RSA-AES256-SHA,ECDHE-RSA-AES128-SHA,AES256-GCM-SHA384,AES128-GCM-SHA256,AES256-SHA,AES128-...`
- **8.4**: `ECDHE-RSA-AES128-GCM-SHA256,ECDHE-RSA-AES256-GCM-SHA384,ECDHE-RSA-CHACHA20-POLY1305,ECDHE-ECDSA-AES128-GCM-SHA256,ECDHE-ECDSA-AES256-GCM-SHA384,ECDHE-ECDSA-CHACHA20-POLY1305`

### `tls_ciphersuites`
- **8.0**: `TLS_AES_128_GCM_SHA256,TLS_AES_256_GCM_SHA384,TLS_CHACHA20_POLY1305_SHA256,TLS_AES_128_CCM_SHA256,TLS_AES_128_CCM_8_SHA256`
- **8.4**: `TLS_AES_128_GCM_SHA256,TLS_AES_256_GCM_SHA384,TLS_CHACHA20_POLY1305_SHA256`

### `tls_version`
**Known impact**: TLSv1.0 and TLSv1.1 removed from allowed values. Only TLSv1.2, TLSv1.3 allowed.
- **8.0**: `TLSv1,TLSv1.1,TLSv1.2,TLSv1.3`
- **8.4**: `TLSv1.2,TLSv1.3`

## D. optimizer_switch Flag Changes

- 8.0 flags: 25
- 8.4 flags: 26

**Added flags**: `hash_set_operations`

> Our custom optimizer_switch does NOT include `hash_set_operations`. When we set optimizer_switch
> explicitly with 17 flags, any flag not listed inherits the 8.4 engine default. `hash_set_operations`
> will default to ON — verify this is acceptable.

## E. Metadata Changes (2 params)

| # | Parameter | Field | 8.0 Value | 8.4 Value |
|---|-----------|-------|-----------|-----------|
| 1 | `innodb_flush_method` | IsModifiable | True | False |
| 2 | `temptable_max_mmap` | ApplyType | static | dynamic |

## F. Known 8.0 → 8.4 Default Changes (from MySQL Release Notes)

> The RDS API does not expose actual default values. The following are known changes
> from MySQL 8.4 release notes. Phase 4 runtime queries validate these.

| Parameter | Change | Impact | Notes |
|-----------|--------|--------|-------|
| `authentication_policy` | NEW in 8.4. Controls multi-factor auth policy. | **INFO** | Validated in Phase 4 |
| `binlog_format` | DEPRECATED in 8.4. Only ROW format supported. Variable still exists but is depre | **INFO** | Validated in Phase 4 |
| `default_authentication_plugin` | REMOVED in 8.4. Replaced by authentication_policy. | **CRITICAL** | Validated in Phase 4 |
| `expire_logs_days` | REMOVED in 8.4. Use binlog_expire_logs_seconds instead. | **INFO** | Validated in Phase 4 |
| `group_replication_consistency` | New allowed value: BEFORE_ON_PRIMARY_FAILOVER. | **INFO** | Validated in Phase 4 |
| `innodb_log_file_size` | REMOVED in 8.4. Replaced by innodb_redo_log_capacity. | **INFO** | Validated in Phase 4 |
| `innodb_log_files_in_group` | REMOVED in 8.4. Replaced by innodb_redo_log_capacity. | **INFO** | Validated in Phase 4 |
| `master_*` | master_* params renamed to source_*. Old names removed. | **WARNING** | Validated in Phase 4 |
| `mysql_native_password` | NEW in 8.4. Plugin disabled by default (OFF). Must set ON for backward compat. | **CRITICAL** | Validated in Phase 4 |
| `optimizer_switch` | New flag: hash_set_operations added in 8.4. | **INFO** | Validated in Phase 4 |
| `slave_*` | 19 slave_* params renamed to replica_*. Old names removed. | **WARNING** | Validated in Phase 4 |
| `temptable_use_mmap` | NEW in 8.4 as explicit param. Default OFF (was ON internally in 8.0.28+). Disabl | **MEDIUM** | Validated in Phase 4 |
| `tls_version` | TLSv1.0 and TLSv1.1 removed from allowed values. Only TLSv1.2, TLSv1.3 allowed. | **MEDIUM** | Validated in Phase 4 |

---

## G. Cross-Reference: Our 18 Custom Parameters vs 8.4 Compatibility

| # | Parameter | Our Value | Exists in 8.4? | Status | Notes |
|---|-----------|-----------|---------------|--------|-------|
| 1 | `mysql_native_password` | ON | YES | **CRITICAL** | NEW in 8.4. Plugin disabled by default (OFF). Must set ON fo |
| 2 | `binlog_order_commits` | 0 | YES | **OK** | Exists in 8.4, no known issues |
| 3 | `binlog_rows_query_log_events` | 0 | YES | **OK** | Exists in 8.4, no known issues |
| 4 | `enforce_gtid_consistency` | ON | YES | **OK** | Exists in 8.4, no known issues |
| 5 | `gtid-mode` | ON | YES | **OK** | Exists in 8.4, no known issues |
| 6 | `innodb_adaptive_hash_index` | 0 | YES | **OK** | Exists in 8.4, no known issues |
| 7 | `innodb_lock_wait_timeout` | 20 | YES | **OK** | Exists in 8.4, no known issues |
| 8 | `innodb_print_all_deadlocks` | 1 | YES | **OK** | Exists in 8.4, no known issues |
| 9 | `innodb_strict_mode` | 0 | YES | **OK** | Exists in 8.4, no known issues |
| 10 | `log_bin_trust_function_creators` | 1 | YES | **OK** | Exists in 8.4, no known issues |
| 11 | `long_query_time` | 0.1 | YES | **OK** | Exists in 8.4, no known issues |
| 12 | `lower_case_table_names` | 1 | YES | **OK** | Exists in 8.4, no known issues |
| 13 | `max_connections` | 4000 | YES | **OK** | Exists in 8.4, no known issues |
| 14 | `optimizer_switch` | index_merge=on,...,prefer_ordering_... | YES | **INFO** | New flag: hash_set_operations added in 8.4. |
| 15 | `performance_schema` | 1 | YES | **OK** | Exists in 8.4, no known issues |
| 16 | `slow_query_log` | 1 | YES | **OK** | Exists in 8.4, no known issues |
| 17 | `sql_mode` | STRICT_TRANS_TABLES,NO_ZERO_IN_DATE... | YES | **OK** | Exists in 8.4, no known issues |
| 18 | `transaction_isolation` | READ-COMMITTED | YES | **OK** | Exists in 8.4, no known issues |

## H. Verification of 8 Dropped Explicit Parameters

These 8 parameters were explicitly set in `luckyus-prod-80-new` matching 8.0 defaults,
dropped from the 8.4 group design to reduce maintenance. Verify they still exist and behave as expected.

| Parameter | In 8.0? | In 8.4? | Safe to Drop? | Notes |
|-----------|---------|---------|---------------|-------|
| `binlog_checksum` | YES | YES | YES | Still exists, default unchanged |
| `binlog_format` | YES | YES | CAUTION | DEPRECATED in 8.4. Only ROW format supported. Variable still exists but is deprecated. |
| `binlog_row_image` | YES | YES | YES | Still exists, default unchanged |
| `character_set_server` | YES | YES | YES | Still exists, default unchanged |
| `innodb_deadlock_detect` | YES | YES | YES | Still exists, default unchanged |
| `log_output` | YES | YES | YES | Still exists, default unchanged |
| `log_queries_not_using_indexes` | YES | YES | YES | Still exists, default unchanged |
| `log_slow_admin_statements` | YES | YES | YES | Still exists, default unchanged |

## I. Notable New 8.4 Parameters to Consider Adding

| Parameter | In 8.4? | Recommendation |
|-----------|---------|----------------|
| `mysql_native_password` | YES | Already in our config (ON). CRITICAL for backward compat. |
| `authentication_policy` | YES | Future: plan caching_sha2_password migration timeline |
| `temptable_use_mmap` | YES | Default OFF in 8.4. Monitor temp table performance on t4g.micro instances |
| `restrict_fk_on_non_standard_key` | YES | New safety feature. Consider enabling for data integrity |
| `explain_json_format_version` | YES | Controls EXPLAIN JSON output version. Leave default |
| `set_operations_buffer_size` | YES | For INTERSECT/EXCEPT. Leave default unless using set operations |
| `tls_certificates_enforced_validation` | YES | Certificate enforcement. Evaluate for security posture |
| `skip_replica_start` | YES | Replacement for skip-slave-start. Not needed (no read replicas) |
| `connection_memory_chunk_size` | YES | Memory tracking granularity. Evaluate for t4g.micro monitoring |
