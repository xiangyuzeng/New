#!/usr/bin/env python3
"""
Fix LFE domain monitoring dashboards to resolve OpenSearch bucket explosion.

Fixes:
  1. date_histogram interval "1s" → "auto" (prevents bucket explosion)
  2. terms aggregation size "0" → "20" (caps cardinality)
  3. Row panels collapsed=true with children absorbed (reduces initial query load)
  4. Panel-level interval property removed where hardcoded to "1s"

Usage:
  python3 fix_dashboards.py --all              # Fix both dashboards
  python3 fix_dashboards.py INPUT OUTPUT TYPE   # Fix single (TYPE: simple|detailed)
"""
import json, sys, os, copy

def fix_interval(panel, agg_idx, desc, changes):
    """Fix a bucketAggs interval from '1s' to 'auto'."""
    try:
        agg = panel["targets"][0]["bucketAggs"][agg_idx]
        old = agg["settings"].get("interval")
        if old == "1s":
            agg["settings"]["interval"] = "auto"
            changes.append(f"  [FIX] {desc}: interval '1s' → 'auto'")
        else:
            changes.append(f"  [OK]  {desc}: interval='{old}'")
    except (KeyError, IndexError) as e:
        changes.append(f"  [ERR] {desc}: {e}")

def fix_simple(dashboard):
    """Fix 简版 (vTPcQSI7z) — 3 interval fixes."""
    panels = dashboard["panels"]
    changes = []
    for pi, ai, desc in [
        (1, 1, "Panel 74 QPS"),
        (6, 1, "Panel 88 请求量URI占比"),
        (7, 1, "Panel 71 流量"),
    ]:
        fix_interval(panels[pi], ai, desc, changes)
    return changes

def fix_detailed(dashboard):
    """Fix 详版 (CoeHpTMHk) — intervals + terms.size + row collapse."""
    panels = dashboard["panels"]
    changes = []

    # --- Interval fixes ---
    # Panel 76 (idx 1): panel-level interval
    if panels[1].get("interval") == "1s":
        del panels[1]["interval"]
        changes.append("  [FIX] Panel 76 QPS: removed panel-level interval='1s'")

    # Panels with date_histogram at bucketAggs[0]
    for pi, desc in [(1, "Panel 76 QPS"), (2, "Panel 78 网络流量")]:
        fix_interval(panels[pi], 0, desc, changes)

    # Panels with date_histogram at bucketAggs[1]
    for pi, desc in [
        (11, "Panel 38 QPS TOP10 URI"),
        (12, "Panel 48 QPS TOP10 源IP"),
        (13, "Panel 50 流量 TOP10 URI"),
        (14, "Panel 49 流量 TOP10 源IP"),
    ]:
        fix_interval(panels[pi], 1, desc, changes)

    # --- Terms size fixes ---
    for pi, desc in [(36, "Panel 73 xff真实IP"), (39, "Panel 74 reffer")]:
        try:
            agg = panels[pi]["targets"][0]["bucketAggs"][0]
            old = agg["settings"].get("size")
            if old == "0":
                agg["settings"]["size"] = "20"
                changes.append(f"  [FIX] {desc}: terms size '0' → '20'")
            else:
                changes.append(f"  [OK]  {desc}: terms size='{old}'")
        except (KeyError, IndexError) as e:
            changes.append(f"  [ERR] {desc}: {e}")

    # --- Row collapse (highest index first to preserve lower indices) ---
    row_defs = [
        (32, 33, 40, "客户端分析"),
        (28, 29, 32, "流量分布"),
        (20, 21, 28, "可用性错误分布分析"),
        (15, 16, 20, "响应时间分析"),
        (10, 11, 15, "QPS、流量分析"),
    ]
    for ri, cs, ce, desc in row_defs:
        row = panels[ri]
        if row.get("type") != "row":
            changes.append(f"  [WARN] idx {ri} not a row, skip")
            continue
        children = panels[cs:ce]
        row["panels"] = children
        row["collapsed"] = True
        del panels[cs:ce]
        changes.append(f"  [FIX] Row '{desc}' (idx {ri}): collapsed, absorbed {len(children)} panels")

    return changes

def wrap_import(dashboard, folder_id=27):
    d = copy.deepcopy(dashboard)
    d.pop("id", None)
    d.pop("version", None)
    return {"dashboard": d, "folderId": folder_id, "overwrite": True}

def process(input_path, output_path, dtype):
    with open(input_path) as f:
        data = json.load(f)
    # Extract dashboard from API response wrapper
    if "dashboard" in data and "meta" in data:
        dashboard = data["dashboard"]
    elif "dashboard" in data and isinstance(data["dashboard"], dict):
        dashboard = data["dashboard"]
    else:
        dashboard = data

    title = dashboard.get("title", "?")
    uid = dashboard.get("uid", "?")
    n = len(dashboard.get("panels", []))
    print(f"\n{'='*60}")
    print(f"Dashboard: {title}")
    print(f"UID: {uid}, Version: {dashboard.get('version')}, Panels: {n}")
    print(f"{'='*60}")

    if dtype == "simple":
        changes = fix_simple(dashboard)
    elif dtype == "detailed":
        changes = fix_detailed(dashboard)
    else:
        print(f"Unknown type: {dtype}"); return

    print(f"\nChanges ({len(changes)}):")
    for c in changes:
        print(c)

    import_data = wrap_import(dashboard)
    with open(output_path, 'w') as f:
        json.dump(import_data, f, indent=2, ensure_ascii=False)

    final_n = len(dashboard.get("panels", []))
    print(f"\nSaved: {output_path}")
    print(f"Panel count: {n} → {final_n}")

def main():
    d = os.path.dirname(os.path.abspath(__file__))
    if len(sys.argv) >= 4:
        process(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        for raw, fixed, dt in [
            ("simple_raw.json", "simple_fixed.json", "simple"),
            ("detailed_raw.json", "detailed_fixed.json", "detailed"),
        ]:
            rp, fp = os.path.join(d, raw), os.path.join(d, fixed)
            if os.path.exists(rp):
                process(rp, fp, dt)
            else:
                print(f"[SKIP] {rp} not found")

    print("\n" + "="*60)
    print("IMPORT INSTRUCTIONS:")
    print("="*60)
    print("""
Option A — Grafana UI Import:
  1. Go to Grafana → Dashboards → Import
  2. Upload the *_fixed.json file
  3. It will overwrite the existing dashboard (same UID)

Option B — API Import (requires write-capable token):
  curl -X POST 'https://GRAFANA_URL/api/dashboards/db' \\
    -H 'Authorization: Bearer YOUR_TOKEN' \\
    -H 'Content-Type: application/json' \\
    -d @simple_fixed.json

  curl -X POST 'https://GRAFANA_URL/api/dashboards/db' \\
    -H 'Authorization: Bearer YOUR_TOKEN' \\
    -H 'Content-Type: application/json' \\
    -d @detailed_fixed.json

ADDITIONAL: Set datasource min interval:
  Grafana → Configuration → Data Sources → Elasticsearch-lfe
  → Min time interval → set to '5s' → Save & Test
""")

if __name__ == "__main__":
    main()
