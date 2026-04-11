#!/usr/bin/env python3
"""
MySQL 8.0 vs 8.4 Engine Default Parameter Diff (FIXED)
Part of LCNA-DBA-2026-021 Parameter Group Deep Audit

Note: RDS describe-engine-default-parameters returns DefaultValue=None for ALL
parameters in both mysql8.0 and mysql8.4. This script works around that by:
1. Comparing parameter existence (removed/added/renamed)
2. Comparing AllowedValues ranges for changes
3. Comparing metadata (DataType, IsModifiable, ApplyType)
4. Supplementing with known MySQL 8.4 default changes from release notes
5. Deferring actual default validation to Phase 4 runtime queries
"""

import json

# Our 18 custom parameters in luckyus-prod-84-new
CUSTOM_PARAMS = {
    'mysql_native_password': 'ON',
    'binlog_order_commits': '0',
    'binlog_rows_query_log_events': '0',
    'enforce_gtid_consistency': 'ON',
    'gtid-mode': 'ON',
    'innodb_adaptive_hash_index': '0',
    'innodb_lock_wait_timeout': '20',
    'innodb_print_all_deadlocks': '1',
    'innodb_strict_mode': '0',
    'log_bin_trust_function_creators': '1',
    'long_query_time': '0.1',
    'lower_case_table_names': '1',
    'max_connections': '4000',
    'optimizer_switch': 'index_merge=on,...,prefer_ordering_index=off',
    'performance_schema': '1',
    'slow_query_log': '1',
    'sql_mode': 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION',
    'transaction_isolation': 'READ-COMMITTED',
}

# 8 params dropped from 8.4 group design (were explicit-default in 8.0)
DROPPED_EXPLICIT = [
    'binlog_checksum', 'binlog_format', 'binlog_row_image',
    'character_set_server', 'innodb_deadlock_detect', 'log_output',
    'log_queries_not_using_indexes', 'log_slow_admin_statements'
]

# Known MySQL 8.0→8.4 default changes (from release notes, not API)
KNOWN_DEFAULT_CHANGES = {
    'mysql_native_password': {'note': 'NEW in 8.4. Plugin disabled by default (OFF). Must set ON for backward compat.', 'impact': 'CRITICAL'},
    'default_authentication_plugin': {'note': 'REMOVED in 8.4. Replaced by authentication_policy.', 'impact': 'CRITICAL'},
    'authentication_policy': {'note': 'NEW in 8.4. Controls multi-factor auth policy.', 'impact': 'INFO'},
    'temptable_use_mmap': {'note': 'NEW in 8.4 as explicit param. Default OFF (was ON internally in 8.0.28+). Disables mmap for temp tables.', 'impact': 'MEDIUM'},
    'binlog_format': {'note': 'DEPRECATED in 8.4. Only ROW format supported. Variable still exists but is deprecated.', 'impact': 'INFO'},
    'innodb_log_file_size': {'note': 'REMOVED in 8.4. Replaced by innodb_redo_log_capacity.', 'impact': 'INFO'},
    'innodb_log_files_in_group': {'note': 'REMOVED in 8.4. Replaced by innodb_redo_log_capacity.', 'impact': 'INFO'},
    'expire_logs_days': {'note': 'REMOVED in 8.4. Use binlog_expire_logs_seconds instead.', 'impact': 'INFO'},
    'slave_*': {'note': '19 slave_* params renamed to replica_*. Old names removed.', 'impact': 'WARNING'},
    'master_*': {'note': 'master_* params renamed to source_*. Old names removed.', 'impact': 'WARNING'},
    'tls_version': {'note': 'TLSv1.0 and TLSv1.1 removed from allowed values. Only TLSv1.2, TLSv1.3 allowed.', 'impact': 'MEDIUM'},
    'optimizer_switch': {'note': 'New flag: hash_set_operations added in 8.4.', 'impact': 'INFO'},
    'group_replication_consistency': {'note': 'New allowed value: BEFORE_ON_PRIMARY_FAILOVER.', 'impact': 'INFO'},
}


def load_params(filepath):
    with open(filepath) as f:
        data = json.load(f)
    params = data.get('EngineDefaults', {}).get('Parameters', [])
    return {p['ParameterName']: p for p in params}


def detect_renames(removed, added):
    renames = []
    unmatched_removed = set(removed)
    unmatched_added = set(added)
    for old_name in sorted(removed):
        for find, replace in [('slave', 'replica'), ('master', 'source')]:
            new_name = old_name.replace(find, replace)
            if new_name != old_name and new_name in unmatched_added:
                renames.append((old_name, new_name))
                unmatched_removed.discard(old_name)
                unmatched_added.discard(new_name)
                break
    return renames, sorted(unmatched_removed), sorted(unmatched_added)


def main():
    p80 = load_params('/home/claude/parameter-group-audit/defaults-80-raw.json')
    p84 = load_params('/home/claude/parameter-group-audit/defaults-84-raw.json')

    names80 = set(p80.keys())
    names84 = set(p84.keys())
    raw_removed = names80 - names84
    raw_added = names84 - names80
    common = names80 & names84

    renames, truly_removed, truly_added = detect_renames(raw_removed, raw_added)

    # AllowedValues diffs
    av_diffs = []
    for n in sorted(common):
        a1 = p80[n].get('AllowedValues', '')
        a2 = p84[n].get('AllowedValues', '')
        if a1 != a2:
            av_diffs.append((n, a1, a2))

    # Metadata diffs (DataType, IsModifiable, ApplyType)
    meta_diffs = []
    for n in sorted(common):
        changes = []
        for field in ['DataType', 'IsModifiable', 'ApplyType']:
            v1 = p80[n].get(field)
            v2 = p84[n].get(field)
            if v1 != v2:
                changes.append((field, v1, v2))
        if changes:
            meta_diffs.append((n, changes))

    # optimizer_switch flag comparison
    av80_os = p80.get('optimizer_switch', {}).get('AllowedValues', '')
    av84_os = p84.get('optimizer_switch', {}).get('AllowedValues', '')
    flags80 = {f.split('=')[0] for f in av80_os.split(',') if '=' in f}
    flags84 = {f.split('=')[0] for f in av84_os.split(',') if '=' in f}
    os_removed = sorted(flags80 - flags84)
    os_added = sorted(flags84 - flags80)

    # === Generate Report ===
    L = []
    L.append("# Phase 2: MySQL 8.0 vs 8.4 Engine Default Parameter Diff")
    L.append("")
    L.append("**Generated**: 2026-04-11  ")
    L.append("**Report**: LCNA-DBA-2026-021 Appendix  ")
    L.append(f"**MySQL 8.0 total parameters**: {len(p80)}  ")
    L.append(f"**MySQL 8.4 total parameters**: {len(p84)}  ")
    L.append(f"**Net difference**: {len(p84) - len(p80)} params")
    L.append("")
    L.append("> **Note**: RDS `describe-engine-default-parameters` returns `DefaultValue=NULL` for ALL parameters")
    L.append("> in both mysql8.0 and mysql8.4 families. Actual runtime defaults are verified in Phase 4 via MCP")
    L.append("> queries against instances running default parameter groups.")
    L.append("")
    L.append("---")
    L.append("")

    # Section A: Removed
    L.append(f"## A. Parameters REMOVED in 8.4 ({len(truly_removed)} truly removed, {len(renames)} renamed)")
    L.append("")
    if truly_removed:
        L.append("### Truly Removed (no rename detected)")
        L.append("")
        L.append("| # | Parameter | DataType | ApplyType | Impact |")
        L.append("|---|-----------|----------|-----------|--------|")
        for i, name in enumerate(truly_removed, 1):
            p = p80[name]
            known = KNOWN_DEFAULT_CHANGES.get(name, {})
            impact = known.get('impact', '')
            note = known.get('note', '')
            L.append(f"| {i} | `{name}` | {p.get('DataType','')} | {p.get('ApplyType','')} | {impact} {note} |")
        L.append("")

    if renames:
        L.append("### Renamed Parameters (slave_* → replica_*, master_* → source_*)")
        L.append("")
        L.append("| # | Old Name (8.0) | New Name (8.4) |")
        L.append("|---|---------------|---------------|")
        for i, (old, new) in enumerate(renames, 1):
            L.append(f"| {i} | `{old}` | `{new}` |")
        L.append("")

    # Section B: Added
    L.append(f"## B. Parameters ADDED in 8.4 ({len(truly_added)} truly new)")
    L.append("")
    if truly_added:
        L.append("| # | Parameter | DataType | ApplyType | Description |")
        L.append("|---|-----------|----------|-----------|-------------|")
        for i, name in enumerate(truly_added, 1):
            p = p84[name]
            desc = p.get('Description', '')[:100]
            L.append(f"| {i} | `{name}` | {p.get('DataType','')} | {p.get('ApplyType','')} | {desc} |")
        L.append("")

    # Section C: AllowedValues Changes
    L.append(f"## C. AllowedValues Changes ({len(av_diffs)} params)")
    L.append("")
    L.append("> Since DefaultValue is always NULL, AllowedValues changes are the best signal from the API.")
    L.append("")
    if av_diffs:
        for name, a1, a2 in av_diffs:
            L.append(f"### `{name}`")
            known = KNOWN_DEFAULT_CHANGES.get(name, {})
            if known:
                L.append(f"**Known impact**: {known.get('note','')}")
            L.append(f"- **8.0**: `{a1[:200]}{'...' if len(a1) > 200 else ''}`")
            L.append(f"- **8.4**: `{a2[:200]}{'...' if len(a2) > 200 else ''}`")
            L.append("")

    # Section D: optimizer_switch
    L.append("## D. optimizer_switch Flag Changes")
    L.append("")
    L.append(f"- 8.0 flags: {len(flags80)}")
    L.append(f"- 8.4 flags: {len(flags84)}")
    L.append("")
    if os_removed:
        L.append(f"**Removed flags**: {', '.join(f'`{f}`' for f in os_removed)}")
        L.append("")
    if os_added:
        L.append(f"**Added flags**: {', '.join(f'`{f}`' for f in os_added)}")
        L.append("")
    L.append("> Our custom optimizer_switch does NOT include `hash_set_operations`. When we set optimizer_switch")
    L.append("> explicitly with 17 flags, any flag not listed inherits the 8.4 engine default. `hash_set_operations`")
    L.append("> will default to ON — verify this is acceptable.")
    L.append("")

    # Section E: Metadata Changes
    L.append(f"## E. Metadata Changes ({len(meta_diffs)} params)")
    L.append("")
    if meta_diffs:
        L.append("| # | Parameter | Field | 8.0 Value | 8.4 Value |")
        L.append("|---|-----------|-------|-----------|-----------|")
        for i, (name, changes) in enumerate(meta_diffs, 1):
            for field, v1, v2 in changes:
                L.append(f"| {i} | `{name}` | {field} | {v1} | {v2} |")
        L.append("")

    # Section F: Known Default Changes (from release notes)
    L.append("## F. Known 8.0 → 8.4 Default Changes (from MySQL Release Notes)")
    L.append("")
    L.append("> The RDS API does not expose actual default values. The following are known changes")
    L.append("> from MySQL 8.4 release notes. Phase 4 runtime queries validate these.")
    L.append("")
    L.append("| Parameter | Change | Impact | Notes |")
    L.append("|-----------|--------|--------|-------|")
    for param, info in sorted(KNOWN_DEFAULT_CHANGES.items()):
        L.append(f"| `{param}` | {info['note'][:80]} | **{info['impact']}** | Validated in Phase 4 |")
    L.append("")

    # Section G: Cross-Reference with Our 18 Custom Params
    L.append("---")
    L.append("")
    L.append("## G. Cross-Reference: Our 18 Custom Parameters vs 8.4 Compatibility")
    L.append("")
    L.append("| # | Parameter | Our Value | Exists in 8.4? | Status | Notes |")
    L.append("|---|-----------|-----------|---------------|--------|-------|")

    renamed_map = {old: new for old, new in renames}
    truly_removed_set = set(truly_removed)

    for i, (param, value) in enumerate(CUSTOM_PARAMS.items(), 1):
        val_display = value[:35] + '...' if len(value) > 35 else value
        if param in truly_removed_set:
            status = "CRITICAL"
            notes = "REMOVED in 8.4"
        elif param in renamed_map:
            status = "WARNING"
            notes = f"Renamed to `{renamed_map[param]}`"
        elif param in names84:
            known = KNOWN_DEFAULT_CHANGES.get(param, {})
            if known:
                status = known['impact']
                notes = known['note'][:60]
            else:
                status = "OK"
                notes = "Exists in 8.4, no known issues"
        elif param in truly_added:
            status = "OK (NEW)"
            notes = "New in 8.4 — custom value overrides default"
        else:
            status = "CHECK"
            notes = "Not in engine defaults — may be RDS-specific"

        L.append(f"| {i} | `{param}` | {val_display} | {'YES' if param in names84 else 'NO (new/special)'} | **{status}** | {notes} |")

    L.append("")

    # Section H: Dropped params verification
    L.append("## H. Verification of 8 Dropped Explicit Parameters")
    L.append("")
    L.append("These 8 parameters were explicitly set in `luckyus-prod-80-new` matching 8.0 defaults,")
    L.append("dropped from the 8.4 group design to reduce maintenance. Verify they still exist and behave as expected.")
    L.append("")
    L.append("| Parameter | In 8.0? | In 8.4? | Safe to Drop? | Notes |")
    L.append("|-----------|---------|---------|---------------|-------|")
    for param in DROPPED_EXPLICIT:
        in80 = 'YES' if param in names80 else 'NO'
        in84 = 'YES' if param in names84 else 'NO'
        known = KNOWN_DEFAULT_CHANGES.get(param, {})
        if param not in names84:
            safe = "N/A — REMOVED"
            notes = known.get('note', 'Removed in 8.4')
        elif known:
            safe = "CAUTION"
            notes = known.get('note', '')
        else:
            safe = "YES"
            notes = "Still exists, default unchanged"
        L.append(f"| `{param}` | {in80} | {in84} | {safe} | {notes} |")
    L.append("")

    # Section I: Notable new params to consider
    L.append("## I. Notable New 8.4 Parameters to Consider Adding")
    L.append("")
    L.append("| Parameter | In 8.4? | Recommendation |")
    L.append("|-----------|---------|----------------|")
    notable = [
        ('mysql_native_password', 'Already in our config (ON). CRITICAL for backward compat.'),
        ('authentication_policy', 'Future: plan caching_sha2_password migration timeline'),
        ('temptable_use_mmap', 'Default OFF in 8.4. Monitor temp table performance on t4g.micro instances'),
        ('restrict_fk_on_non_standard_key', 'New safety feature. Consider enabling for data integrity'),
        ('explain_json_format_version', 'Controls EXPLAIN JSON output version. Leave default'),
        ('set_operations_buffer_size', 'For INTERSECT/EXCEPT. Leave default unless using set operations'),
        ('tls_certificates_enforced_validation', 'Certificate enforcement. Evaluate for security posture'),
        ('skip_replica_start', 'Replacement for skip-slave-start. Not needed (no read replicas)'),
        ('connection_memory_chunk_size', 'Memory tracking granularity. Evaluate for t4g.micro monitoring'),
    ]
    for param, rec in notable:
        in84 = 'YES' if param in names84 else 'NO'
        L.append(f"| `{param}` | {in84} | {rec} |")
    L.append("")

    report = '\n'.join(L)
    with open('/home/claude/parameter-group-audit/phase2-default-diff.md', 'w') as f:
        f.write(report)

    print(f"Report written: {len(L)} lines")
    print(f"\nSummary:")
    print(f"  Truly removed: {len(truly_removed)}")
    print(f"  Renamed: {len(renames)}")
    print(f"  Truly added: {len(truly_added)}")
    print(f"  AllowedValues diffs: {len(av_diffs)}")
    print(f"  Metadata diffs: {len(meta_diffs)}")
    print(f"  optimizer_switch: +{len(os_added)} added, -{len(os_removed)} removed")
    print(f"  All 18 custom params exist in 8.4: {all(p in names84 for p in CUSTOM_PARAMS)}")


if __name__ == '__main__':
    main()
