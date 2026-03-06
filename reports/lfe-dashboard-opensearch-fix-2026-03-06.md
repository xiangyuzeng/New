# LFE Domain Monitoring Dashboard Fix — OpenSearch Bucket Explosion

**Date**: 2026-03-06
**Author**: David Zeng (曾翔宇), Senior DBA
**Status**: Phase 2 Complete — Awaiting Manual Import
**Severity**: High — Causes OpenSearch cluster instability

---

## Executive Summary

Two Grafana dashboards monitoring the LFE (Luckin Front-End) domain were identified as the root cause of recurring OpenSearch cluster instability. Hardcoded `1s` intervals in `date_histogram` aggregations cause **bucket explosion** when users select time ranges longer than 1 hour — a 6-hour window generates 21,600 buckets per panel, multiplied by terms cardinality, producing 600K+ data points per dashboard load.

**17 fixes** were applied across both dashboards via an automated script. Fixed JSON files are ready for import.

---

## Affected Dashboards

| Property | 简版 (Simple) | 详版 (Detailed) |
|----------|---------------|-----------------|
| **UID** | `vTPcQSI7z` | `CoeHpTMHk` |
| **Title** | 【LUCKY】LFE域名简版 | LFE域名详版 |
| **Dashboard ID** | 28 | 29 |
| **Version** | 10 | 17 |
| **Panels (before)** | 8 | 40 |
| **Panels (after)** | 8 | 15 (25 absorbed into collapsed rows) |
| **Folder** | 【域名指标监控】(id:27, uid:`EqR9fVTHk`) | Same |
| **Data Source** | Elasticsearch-lfe (uid:`d0qWL4oNk`) | Same |
| **Index Pattern** | `ufenginx-*` | Same |

---

## Root Cause Analysis

### Problem: Bucket Explosion

The `date_histogram` aggregation in multiple panels used a hardcoded `fixed_interval: "1s"`. This means:

| Time Range | Buckets per Panel | With 10 terms | Total Data Points |
|------------|-------------------|---------------|-------------------|
| 15 min | 900 | 9,000 | Acceptable |
| 1 hour | 3,600 | 36,000 | Heavy |
| 6 hours | 21,600 | 216,000 | **Overload** |
| 24 hours | 86,400 | 864,000 | **Cluster crash** |

When multiple users open dashboards with 6h+ ranges, OpenSearch receives millions of bucket requests simultaneously, causing:
- JVM heap exhaustion
- Circuit breaker trips
- Cluster-wide slow queries and timeouts
- Impact on other services sharing the same OpenSearch cluster

### Secondary Issues

1. **Unbounded terms aggregation** (`size: "0"`): Two panels in 详版 request unlimited cardinality for high-cardinality fields (`xff` IP addresses, `referrer` URLs), amplifying bucket explosion.

2. **All rows expanded by default**: 详版 has 5 row groups containing 25 panels — all fire queries on page load even when collapsed sections aren't visible.

---

## Fixes Applied (17 Total)

### Fix 1: date_histogram interval `1s` → `auto` (10 panels)

Grafana's `auto` interval adapts to the selected time range and panel pixel width, typically resolving to:
- 15m range → ~1s interval (same as before)
- 1h range → ~5s interval
- 6h range → ~30s interval
- 24h range → ~2m interval

This prevents bucket explosion while preserving detail at short time ranges.

**简版 — 3 panels fixed:**

| Panel ID | Panel Title | Aggregation Path |
|----------|-------------|------------------|
| 74 | QPS | `bucketAggs[1].settings.interval` |
| 88 | 请求量URI占比 | `bucketAggs[1].settings.interval` |
| 71 | 流量 | `bucketAggs[1].settings.interval` |

**详版 — 7 panels fixed (including 1 panel-level interval removal):**

| Panel ID | Panel Title | Fix Applied |
|----------|-------------|-------------|
| 76 | QPS | Removed panel-level `interval="1s"` property AND `bucketAggs[0].settings.interval` → `auto` |
| 78 | 网络流量 | `bucketAggs[0].settings.interval` → `auto` |
| 38 | QPS TOP10 URI | `bucketAggs[1].settings.interval` → `auto` |
| 48 | QPS TOP10 源IP | `bucketAggs[1].settings.interval` → `auto` |
| 50 | 流量 TOP10 URI | `bucketAggs[1].settings.interval` → `auto` |
| 49 | 流量 TOP10 源IP | `bucketAggs[1].settings.interval` → `auto` |

### Fix 2: terms aggregation size `0` → `20` (2 panels)

Caps cardinality to top 20 results, preventing unbounded term bucket expansion.

| Panel ID | Panel Title | Field |
|----------|-------------|-------|
| 73 | xff真实IP | `bucketAggs[0].settings.size` |
| 74 | reffer | `bucketAggs[0].settings.size` |

### Fix 3: Row Collapse (5 rows, 25 panels absorbed)

All 5 row groups in 详版 set to `collapsed: true` with child panels absorbed into the row's nested `panels[]` array. This means child panels only fire queries when the user explicitly expands a row.

| Row Title | Panels Absorbed |
|-----------|----------------|
| QPS、流量分析 | 4 |
| 响应时间分析 | 4 |
| 可用性错误分布分析 | 7 |
| 流量分布 | 3 |
| 客户端分析 | 7 |
| **Total** | **25** |

**Impact**: Initial page load drops from 40 panel queries to 15 (top-level panels + collapsed rows). Users expand rows on demand.

### Fix 4: Data Source Min Interval (Manual)

**Requires manual action** — cannot be applied via dashboard JSON.

Set `Elasticsearch-lfe` data source minimum interval to `5s`:
1. Grafana → Configuration → Data Sources → Elasticsearch-lfe
2. Set "Min time interval" to `5s`
3. Save & Test

This provides a safety net: even if any panel still uses `1s`, the data source enforces a floor of `5s`.

---

## Expected Impact

### Before Fix (worst case: 6h time range)

| Metric | Simple | Detailed | Combined |
|--------|--------|----------|----------|
| Panels querying | 8 | 40 | 48 |
| Buckets per panel | 21,600 | 21,600 | — |
| Terms cardinality | 10-unlimited | 10-unlimited | — |
| Est. data points | ~200K | ~600K+ | ~800K+ |

### After Fix (6h time range)

| Metric | Simple | Detailed | Combined |
|--------|--------|----------|----------|
| Panels querying on load | 8 | 15 | 23 |
| Buckets per panel (~30s auto) | ~720 | ~720 | — |
| Terms cardinality | 10 (capped) | 10-20 (capped) | — |
| Est. data points | ~7K | ~15K | ~22K |

**Reduction: ~97% fewer data points on initial load.**

---

## File Inventory

| File | Size | Purpose |
|------|------|---------|
| `/home/claude/dashboard-fix/simple_raw.json` | 21,343 B | Original backup — DO NOT MODIFY |
| `/home/claude/dashboard-fix/detailed_raw.json` | 135,824 B | Original backup — DO NOT MODIFY |
| `/home/claude/dashboard-fix/simple_fixed.json` | 46,303 B | Import-ready fixed 简版 |
| `/home/claude/dashboard-fix/detailed_fixed.json` | 147,241 B | Import-ready fixed 详版 |
| `/home/claude/dashboard-fix/fix_dashboards.py` | 6,460 B | Fix script (rerunnable) |

All fixed JSONs are wrapped in Grafana import format:
```json
{"dashboard": {...}, "folderId": 27, "overwrite": true}
```

---

## Import Instructions

### Option A — Grafana UI Import (Recommended)

1. Go to Grafana → Dashboards → Import
2. Upload `simple_fixed.json`
3. It will overwrite the existing dashboard (same UID: `vTPcQSI7z`)
4. Repeat with `detailed_fixed.json` (UID: `CoeHpTMHk`)

### Option B — API Import (requires write-capable token)

```bash
# Simple dashboard
curl -X POST 'https://GRAFANA_URL/api/dashboards/db' \
  -H 'Authorization: Bearer YOUR_WRITE_TOKEN' \
  -H 'Content-Type: application/json' \
  -d @/home/claude/dashboard-fix/simple_fixed.json

# Detailed dashboard
curl -X POST 'https://GRAFANA_URL/api/dashboards/db' \
  -H 'Authorization: Bearer YOUR_WRITE_TOKEN' \
  -H 'Content-Type: application/json' \
  -d @/home/claude/dashboard-fix/detailed_fixed.json
```

**Note**: The current `grafana-lucky` MCP token returns 403 on write operations. A token with Editor or Admin role is required.

### Post-Import: Data Source Min Interval

Grafana → Configuration → Data Sources → Elasticsearch-lfe → Min time interval → `5s` → Save & Test

---

## Phase 3: Validation Checklist

After importing, run the validation script (`/home/claude/dashboard-fix/validate_dashboards.py`) to confirm:

- [ ] All `date_histogram` intervals are `auto` (not `1s`)
- [ ] All `terms` aggregation sizes are ≤ 20 (not `0`)
- [ ] All rows in 详版 are collapsed with children absorbed
- [ ] Panel-level interval removed from Panel 76
- [ ] Data source min interval set to `5s`
- [ ] OpenSearch cluster health: green, JVM heap < 75%
- [ ] Dashboard loads within 5 seconds on 6h time range

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Dashboard looks different after fix | Low | `auto` interval produces same visual at short ranges; collapsed rows are user-expandable |
| Fix breaks existing saved views | Very Low | Only interval resolution changed; no queries/metrics altered |
| Need to rollback | Low | Raw backups preserved at `/home/claude/dashboard-fix/*_raw.json` |
| Data source min interval too aggressive | Low | `5s` is conservative; can adjust to `1s` if needed |

---

## Timeline

| Date | Phase | Status |
|------|-------|--------|
| 2026-03-05 | Phase 1: Investigation | Complete |
| 2026-03-06 | Phase 2: Fix script + JSON generation | Complete |
| 2026-03-06 | Phase 2: Manual import | **Pending** |
| TBD | Phase 3: Validation | Blocked on import |
