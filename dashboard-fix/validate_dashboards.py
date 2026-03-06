#!/usr/bin/env python3
"""
Phase 3 Validation — LFE Domain Dashboard OpenSearch Fix

Validates that all 17 fixes are correctly applied in the fixed dashboard JSONs.
Can validate against:
  1. Local fixed JSON files (default)
  2. Live Grafana export files (after manual import)

Usage:
  python3 validate_dashboards.py                          # Validate fixed JSONs
  python3 validate_dashboards.py --live SIMPLE DETAILED   # Validate live exports

Exit codes:
  0 = All checks passed
  1 = One or more checks failed
"""
import json, sys, os, argparse

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
INFO = "\033[94m[INFO]\033[0m"

results = {"pass": 0, "fail": 0, "warn": 0}


def check(condition, desc):
    if condition:
        print(f"  {PASS} {desc}")
        results["pass"] += 1
    else:
        print(f"  {FAIL} {desc}")
        results["fail"] += 1
    return condition


def warn(desc):
    print(f"  {WARN} {desc}")
    results["warn"] += 1


def info(desc):
    print(f"  {INFO} {desc}")


def load_dashboard(path):
    """Load dashboard JSON, unwrapping import/API envelope if present."""
    with open(path) as f:
        data = json.load(f)
    if "dashboard" in data and isinstance(data["dashboard"], dict):
        return data["dashboard"]
    return data


def collect_all_panels(panels):
    """Recursively collect all panels including those inside collapsed rows."""
    all_panels = []
    for p in panels:
        all_panels.append(p)
        if p.get("type") == "row" and "panels" in p:
            all_panels.extend(p["panels"])
    return all_panels


def find_panel_by_id(panels, panel_id):
    """Find a panel by its ID across top-level and nested (row) panels."""
    for p in panels:
        if p.get("id") == panel_id:
            return p
        if p.get("type") == "row" and "panels" in p:
            for child in p["panels"]:
                if child.get("id") == panel_id:
                    return child
    return None


def get_interval(panel, agg_idx=0):
    """Get bucketAggs interval value from a panel."""
    try:
        return panel["targets"][0]["bucketAggs"][agg_idx]["settings"].get("interval")
    except (KeyError, IndexError, TypeError):
        return None


def get_terms_size(panel, agg_idx=0):
    """Get bucketAggs terms size value from a panel."""
    try:
        return panel["targets"][0]["bucketAggs"][agg_idx]["settings"].get("size")
    except (KeyError, IndexError, TypeError):
        return None


# ─── Simple Dashboard Validation ────────────────────────────────────────────

def validate_simple(path):
    print(f"\n{'='*60}")
    print(f"Validating 简版 (Simple): {path}")
    print(f"{'='*60}")

    db = load_dashboard(path)
    panels = db.get("panels", [])

    # Basic metadata
    check(db.get("uid") == "vTPcQSI7z", f"UID = vTPcQSI7z (got: {db.get('uid')})")
    info(f"Title: {db.get('title')}")
    info(f"Panel count: {len(panels)}")

    # Fix 1: date_histogram intervals → auto (3 panels)
    print("\n  --- Fix 1: date_histogram interval → auto ---")
    interval_checks = [
        (74, 1, "Panel 74 QPS"),
        (88, 1, "Panel 88 请求量URI占比"),
        (71, 1, "Panel 71 流量"),
    ]
    for pid, agg_idx, desc in interval_checks:
        p = find_panel_by_id(panels, pid)
        if p is None:
            check(False, f"{desc}: panel id={pid} not found")
            continue
        interval = get_interval(p, agg_idx)
        check(
            interval != "1s",
            f"{desc}: interval='{interval}' (must not be '1s')"
        )
        if interval == "auto":
            pass  # ideal
        elif interval and interval != "1s":
            warn(f"{desc}: interval='{interval}' — expected 'auto' but acceptable")

    # Negative check: no remaining 1s intervals anywhere
    print("\n  --- Sweep: no remaining '1s' intervals ---")
    all_panels = collect_all_panels(panels)
    stale = []
    for p in all_panels:
        for t in p.get("targets", []):
            for i, agg in enumerate(t.get("bucketAggs", [])):
                if agg.get("settings", {}).get("interval") == "1s":
                    stale.append(f"panel {p.get('id')} bucketAggs[{i}]")
    check(len(stale) == 0, f"No '1s' intervals remaining ({len(stale)} found: {stale})")


# ─── Detailed Dashboard Validation ──────────────────────────────────────────

def validate_detailed(path):
    print(f"\n{'='*60}")
    print(f"Validating 详版 (Detailed): {path}")
    print(f"{'='*60}")

    db = load_dashboard(path)
    panels = db.get("panels", [])

    # Basic metadata
    check(db.get("uid") == "CoeHpTMHk", f"UID = CoeHpTMHk (got: {db.get('uid')})")
    info(f"Title: {db.get('title')}")
    info(f"Top-level panel count: {len(panels)}")

    all_panels = collect_all_panels(panels)
    info(f"Total panel count (including nested): {len(all_panels)}")

    # Fix 1: Panel 76 panel-level interval removed
    print("\n  --- Fix 1a: Panel 76 panel-level interval removed ---")
    p76 = find_panel_by_id(panels, 76)
    if p76:
        check(
            p76.get("interval") != "1s",
            f"Panel 76: no panel-level interval='1s' (got: {p76.get('interval', '<absent>')})"
        )
    else:
        check(False, "Panel 76 not found")

    # Fix 1b: date_histogram intervals → auto
    print("\n  --- Fix 1b: date_histogram interval → auto ---")
    interval_checks = [
        (76, 0, "Panel 76 QPS"),
        (78, 0, "Panel 78 网络流量"),
        (38, 1, "Panel 38 QPS TOP10 URI"),
        (48, 1, "Panel 48 QPS TOP10 源IP"),
        (50, 1, "Panel 50 流量 TOP10 URI"),
        (49, 1, "Panel 49 流量 TOP10 源IP"),
    ]
    for pid, agg_idx, desc in interval_checks:
        p = find_panel_by_id(panels, pid)
        if p is None:
            check(False, f"{desc}: panel id={pid} not found")
            continue
        interval = get_interval(p, agg_idx)
        check(
            interval != "1s",
            f"{desc}: interval='{interval}' (must not be '1s')"
        )

    # Fix 2: terms aggregation size capped
    print("\n  --- Fix 2: terms size '0' → '20' ---")
    terms_checks = [
        (73, 0, "Panel 73 xff真实IP"),
        (74, 0, "Panel 74 reffer"),
    ]
    for pid, agg_idx, desc in terms_checks:
        p = find_panel_by_id(panels, pid)
        if p is None:
            check(False, f"{desc}: panel id={pid} not found")
            continue
        size = get_terms_size(p, agg_idx)
        check(
            size != "0",
            f"{desc}: terms size='{size}' (must not be '0')"
        )

    # Fix 3: Rows collapsed with children absorbed
    print("\n  --- Fix 3: Rows collapsed with children absorbed ---")
    expected_rows = [
        "QPS、流量分析",
        "响应时间分析",
        "可用性错误分布分析",
        "流量分布",
        "客户端分析",
    ]
    row_panels = [p for p in panels if p.get("type") == "row"]
    info(f"Row panels found: {len(row_panels)}")

    for row_title in expected_rows:
        matching = [r for r in row_panels if row_title in r.get("title", "")]
        if not matching:
            check(False, f"Row '{row_title}': not found")
            continue
        row = matching[0]
        is_collapsed = row.get("collapsed", False)
        has_children = len(row.get("panels", [])) > 0
        check(
            is_collapsed and has_children,
            f"Row '{row_title}': collapsed={is_collapsed}, children={len(row.get('panels', []))}"
        )

    # Verify total absorbed panels
    total_absorbed = sum(len(r.get("panels", [])) for r in row_panels if r.get("collapsed"))
    check(total_absorbed == 25, f"Total absorbed panels: {total_absorbed} (expected 25)")

    # Verify top-level panel count reduced
    check(
        len(panels) <= 15,
        f"Top-level panels ≤ 15: {len(panels)} (was 40 before fix)"
    )

    # Negative check: no remaining 1s intervals anywhere
    print("\n  --- Sweep: no remaining '1s' intervals ---")
    stale = []
    for p in all_panels:
        for t in p.get("targets", []):
            for i, agg in enumerate(t.get("bucketAggs", [])):
                if agg.get("settings", {}).get("interval") == "1s":
                    stale.append(f"panel {p.get('id')} bucketAggs[{i}]")
        if p.get("interval") == "1s":
            stale.append(f"panel {p.get('id')} panel-level")
    check(len(stale) == 0, f"No '1s' intervals remaining ({len(stale)} found: {stale})")

    # Negative check: no unbounded terms
    print("\n  --- Sweep: no unbounded terms (size='0') ---")
    unbounded = []
    for p in all_panels:
        for t in p.get("targets", []):
            for i, agg in enumerate(t.get("bucketAggs", [])):
                if agg.get("type") == "terms" and agg.get("settings", {}).get("size") == "0":
                    unbounded.append(f"panel {p.get('id')} bucketAggs[{i}]")
    check(len(unbounded) == 0, f"No unbounded terms (size='0') remaining ({len(unbounded)} found: {unbounded})")


# ─── Diff Summary ───────────────────────────────────────────────────────────

def diff_summary(raw_path, fixed_path, dtype):
    """Quick structural diff between raw and fixed dashboards."""
    if not os.path.exists(raw_path):
        info(f"Raw backup not found at {raw_path}, skipping diff")
        return

    print(f"\n  --- Diff: raw vs fixed ---")
    raw = load_dashboard(raw_path)
    fixed = load_dashboard(fixed_path)

    raw_panels = collect_all_panels(raw.get("panels", []))
    fixed_panels = collect_all_panels(fixed.get("panels", []))

    info(f"Raw top-level panels:   {len(raw.get('panels', []))}")
    info(f"Fixed top-level panels: {len(fixed.get('panels', []))}")
    info(f"Raw total panels:       {len(raw_panels)}")
    info(f"Fixed total panels:     {len(fixed_panels)}")

    # Count intervals
    raw_1s = sum(
        1 for p in raw_panels
        for t in p.get("targets", [])
        for a in t.get("bucketAggs", [])
        if a.get("settings", {}).get("interval") == "1s"
    )
    fixed_1s = sum(
        1 for p in fixed_panels
        for t in p.get("targets", [])
        for a in t.get("bucketAggs", [])
        if a.get("settings", {}).get("interval") == "1s"
    )
    info(f"'1s' intervals: {raw_1s} → {fixed_1s}")

    if dtype == "detailed":
        raw_collapsed = sum(1 for p in raw.get("panels", []) if p.get("type") == "row" and p.get("collapsed"))
        fixed_collapsed = sum(1 for p in fixed.get("panels", []) if p.get("type") == "row" and p.get("collapsed"))
        info(f"Collapsed rows: {raw_collapsed} → {fixed_collapsed}")


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate LFE dashboard fixes")
    parser.add_argument("--live", nargs=2, metavar=("SIMPLE", "DETAILED"),
                        help="Paths to live-exported simple and detailed JSONs")
    args = parser.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))

    if args.live:
        simple_path, detailed_path = args.live
    else:
        simple_path = os.path.join(base, "simple_fixed.json")
        detailed_path = os.path.join(base, "detailed_fixed.json")

    print("=" * 60)
    print("LFE Dashboard Fix — Phase 3 Validation")
    print("=" * 60)

    if os.path.exists(simple_path):
        validate_simple(simple_path)
        diff_summary(os.path.join(base, "simple_raw.json"), simple_path, "simple")
    else:
        print(f"\n{FAIL} Simple dashboard not found: {simple_path}")
        results["fail"] += 1

    if os.path.exists(detailed_path):
        validate_detailed(detailed_path)
        diff_summary(os.path.join(base, "detailed_raw.json"), detailed_path, "detailed")
    else:
        print(f"\n{FAIL} Detailed dashboard not found: {detailed_path}")
        results["fail"] += 1

    # Manual checks reminder
    print(f"\n{'='*60}")
    print("Manual Checks (cannot be validated programmatically):")
    print("=" * 60)
    print("  [ ] Data source 'Elasticsearch-lfe' min interval set to '5s'")
    print("  [ ] OpenSearch cluster health: green")
    print("  [ ] OpenSearch JVM heap < 75%")
    print("  [ ] Dashboard loads within 5 seconds on 6h time range")

    # Summary
    total = results["pass"] + results["fail"]
    print(f"\n{'='*60}")
    print(f"RESULTS: {results['pass']}/{total} passed, "
          f"{results['fail']} failed, {results['warn']} warnings")
    print("=" * 60)

    if results["fail"] > 0:
        print(f"\n{FAIL} Validation FAILED — review failures above before deploying.")
        sys.exit(1)
    else:
        print(f"\n{PASS} All checks passed — safe to import into Grafana.")
        sys.exit(0)


if __name__ == "__main__":
    main()
