#!/usr/bin/env python3
"""
RDS Performance Baseline Report Generator
Luckin Coffee North America — DBA Infrastructure Team

Pulls CloudWatch metrics for all RDS instances in a region, computes statistics,
evaluates RAG (Red/Amber/Green) thresholds, and outputs a markdown baseline report.

Usage:
    python baseline_rds.py --region us-east-1 --period 30 --format markdown
    python baseline_rds.py --cluster-filter "aws-luckyus-*" --verbose
    python baseline_rds.py --profile databasecheck --format both
"""

import argparse
import datetime
import fnmatch
import json
import logging
import os
import statistics
import sys
import time

import boto3
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Instance class → total memory (GB)
# ---------------------------------------------------------------------------
INSTANCE_MEMORY_GB = {
    # R5 family
    "db.r5.large": 16, "db.r5.xlarge": 32, "db.r5.2xlarge": 64,
    "db.r5.4xlarge": 128, "db.r5.8xlarge": 256, "db.r5.12xlarge": 384,
    "db.r5.16xlarge": 512, "db.r5.24xlarge": 768,
    # R6g family (Graviton)
    "db.r6g.large": 16, "db.r6g.xlarge": 32, "db.r6g.2xlarge": 64,
    "db.r6g.4xlarge": 128, "db.r6g.8xlarge": 256, "db.r6g.12xlarge": 384,
    "db.r6g.16xlarge": 512,
    # R6i family
    "db.r6i.large": 16, "db.r6i.xlarge": 32, "db.r6i.2xlarge": 64,
    "db.r6i.4xlarge": 128, "db.r6i.8xlarge": 256,
    # R7g family
    "db.r7g.large": 16, "db.r7g.xlarge": 32, "db.r7g.2xlarge": 64,
    "db.r7g.4xlarge": 128, "db.r7g.8xlarge": 256,
    # T3 family
    "db.t3.micro": 1, "db.t3.small": 2, "db.t3.medium": 4,
    "db.t3.large": 8, "db.t3.xlarge": 16, "db.t3.2xlarge": 32,
    # T4g family (Graviton)
    "db.t4g.micro": 1, "db.t4g.small": 2, "db.t4g.medium": 4,
    "db.t4g.large": 8, "db.t4g.xlarge": 16, "db.t4g.2xlarge": 32,
    # M5 family
    "db.m5.large": 8, "db.m5.xlarge": 16, "db.m5.2xlarge": 32,
    "db.m5.4xlarge": 64, "db.m5.8xlarge": 128, "db.m5.12xlarge": 192,
    "db.m5.16xlarge": 256, "db.m5.24xlarge": 384,
    # M6g family (Graviton)
    "db.m6g.large": 8, "db.m6g.xlarge": 16, "db.m6g.2xlarge": 32,
    "db.m6g.4xlarge": 64, "db.m6g.8xlarge": 128,
    # M6i family
    "db.m6i.large": 8, "db.m6i.xlarge": 16, "db.m6i.2xlarge": 32,
    "db.m6i.4xlarge": 64, "db.m6i.8xlarge": 128,
    # M7g family
    "db.m7g.large": 8, "db.m7g.xlarge": 16, "db.m7g.2xlarge": 32,
    "db.m7g.4xlarge": 64, "db.m7g.8xlarge": 128,
}

# ---------------------------------------------------------------------------
# RAG thresholds
# ---------------------------------------------------------------------------
RAG_THRESHOLDS = {
    "CPUUtilization":       {"green": 60,   "amber": 80,   "higher_is_worse": True},
    "FreeableMemory_pct":   {"green": 30,   "amber": 15,   "higher_is_worse": False},
    "FreeStorageSpace_pct": {"green": 40,   "amber": 20,   "higher_is_worse": False},
    "ReadIOPS":             {"green": None,  "amber": None,  "higher_is_worse": True},
    "WriteIOPS":            {"green": None,  "amber": None,  "higher_is_worse": True},
    "ReadLatency_ms":       {"green": 5,    "amber": 20,   "higher_is_worse": True},
    "WriteLatency_ms":      {"green": 5,    "amber": 20,   "higher_is_worse": True},
    "DatabaseConnections":  {"green": None,  "amber": None,  "higher_is_worse": True},
    "ReplicaLag":           {"green": 1,    "amber": 10,   "higher_is_worse": True},
    "SwapUsage_mb":         {"green": 64,   "amber": 256,  "higher_is_worse": True},
}

# Metrics to collect from CloudWatch (in order)
METRICS = [
    {"name": "CPUUtilization",     "display": "CPU Utilization",   "unit": "%",     "convert": None},
    {"name": "FreeableMemory",     "display": "Freeable Memory",   "unit": "%",     "convert": "memory_pct"},
    {"name": "FreeStorageSpace",   "display": "Free Storage",      "unit": "%",     "convert": "storage_pct"},
    {"name": "ReadIOPS",           "display": "Read IOPS",         "unit": "iops",  "convert": None},
    {"name": "WriteIOPS",          "display": "Write IOPS",        "unit": "iops",  "convert": None},
    {"name": "ReadLatency",        "display": "Read Latency",      "unit": "ms",    "convert": "sec_to_ms"},
    {"name": "WriteLatency",       "display": "Write Latency",     "unit": "ms",    "convert": "sec_to_ms"},
    {"name": "DatabaseConnections","display": "Connections",        "unit": "count", "convert": None},
    {"name": "ReplicaLag",         "display": "Replica Lag",       "unit": "sec",   "convert": None},
    {"name": "SwapUsage",          "display": "Swap Usage",        "unit": "MB",    "convert": "bytes_to_mb"},
]

log = logging.getLogger("baseline_rds")


# ===================================================================
# RAG evaluation
# ===================================================================

def rag(value, green_threshold, amber_threshold, higher_is_worse):
    """Return RAG emoji given a value and thresholds."""
    if green_threshold is None:
        return "🔵"
    if higher_is_worse:
        if value <= green_threshold:
            return "🟢"
        elif value <= amber_threshold:
            return "🟡"
        else:
            return "🔴"
    else:
        if value >= green_threshold:
            return "🟢"
        elif value >= amber_threshold:
            return "🟡"
        else:
            return "🔴"


def rag_text(value, green_threshold, amber_threshold, higher_is_worse):
    """Return RAG as text string for JSON output."""
    if green_threshold is None:
        return "info"
    if higher_is_worse:
        if value <= green_threshold:
            return "green"
        elif value <= amber_threshold:
            return "amber"
        else:
            return "red"
    else:
        if value >= green_threshold:
            return "green"
        elif value >= amber_threshold:
            return "amber"
        else:
            return "red"


def threshold_display(metric_key):
    """Format threshold for display in table."""
    t = RAG_THRESHOLDS.get(metric_key)
    if not t or t["green"] is None:
        return "—"
    if t["higher_is_worse"]:
        return f"G:≤{t['green']} A:≤{t['amber']}"
    else:
        return f"G:≥{t['green']} A:≥{t['amber']}"


# ===================================================================
# Statistics helpers
# ===================================================================

def compute_stats(values):
    """Compute avg, min, max, p95 from a list of floats."""
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    return {
        "avg": statistics.mean(sorted_vals),
        "min": sorted_vals[0],
        "max": sorted_vals[-1],
        "p95": sorted_vals[int(n * 0.95)] if n > 1 else sorted_vals[0],
        "datapoints": n,
    }


def fmt(value, unit, precision=1):
    """Format a numeric value for display."""
    if value is None:
        return "—"
    if unit == "%":
        return f"{value:.{precision}f}%"
    elif unit == "ms":
        return f"{value:.{precision}f} ms"
    elif unit == "MB":
        return f"{value:.{precision}f} MB"
    elif unit == "sec":
        return f"{value:.{precision}f}s"
    elif unit == "iops":
        return f"{value:,.0f}"
    elif unit == "count":
        return f"{value:,.0f}"
    elif unit == "GB":
        return f"{value:.2f} GB"
    else:
        return f"{value:.{precision}f}"


# ===================================================================
# AWS discovery
# ===================================================================

def discover_instances(rds_client, filters):
    """Discover all RDS instances via describe_db_instances with pagination."""
    instances = []
    paginator = rds_client.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for db in page["DBInstances"]:
            inst_id = db["DBInstanceIdentifier"]
            # Apply filter patterns
            if filters:
                if not any(fnmatch.fnmatch(inst_id, pat) for pat in filters):
                    log.debug(f"  Skipped {inst_id} (no filter match)")
                    continue
            is_replica = bool(db.get("ReadReplicaSourceDBInstanceIdentifier"))
            instances.append({
                "instance_id": inst_id,
                "instance_class": db.get("DBInstanceClass", "unknown"),
                "engine": db.get("Engine", "unknown"),
                "engine_version": db.get("EngineVersion", ""),
                "allocated_storage_gb": db.get("AllocatedStorage", 0),
                "storage_type": db.get("StorageType", ""),
                "iops": db.get("Iops"),
                "cluster_id": db.get("DBClusterIdentifier"),
                "multi_az": db.get("MultiAZ", False),
                "is_replica": is_replica,
                "replica_source": db.get("ReadReplicaSourceDBInstanceIdentifier"),
                "status": db.get("DBInstanceStatus", "unknown"),
            })
            log.debug(f"  Found: {inst_id} ({db.get('DBInstanceClass')}, {db.get('Engine')})")
    return instances


def discover_clusters(rds_client):
    """Discover Aurora clusters for reference."""
    clusters = {}
    try:
        paginator = rds_client.get_paginator("describe_db_clusters")
        for page in paginator.paginate():
            for cl in page["DBClusters"]:
                clusters[cl["DBClusterIdentifier"]] = {
                    "engine": cl.get("Engine"),
                    "engine_version": cl.get("EngineVersion"),
                    "members": [m["DBInstanceIdentifier"] for m in cl.get("DBClusterMembers", [])],
                }
    except ClientError as e:
        log.warning(f"Could not list DB clusters: {e}")
    return clusters


# ===================================================================
# CloudWatch metric collection
# ===================================================================

def collect_metrics(cw_client, instance, start_time, end_time, period_seconds):
    """Collect all 10 metrics for a single RDS instance."""
    inst_id = instance["instance_id"]
    inst_class = instance["instance_class"]
    allocated_gb = instance["allocated_storage_gb"]
    total_mem_gb = INSTANCE_MEMORY_GB.get(inst_class)
    results = {}

    for metric_def in METRICS:
        metric_name = metric_def["name"]
        convert = metric_def["convert"]
        display_unit = metric_def["unit"]

        # Skip ReplicaLag for non-replicas
        if metric_name == "ReplicaLag" and not instance["is_replica"]:
            results[metric_name] = {
                "stats": None, "unit": display_unit,
                "rag_key": metric_name, "skip_reason": "primary",
            }
            continue

        try:
            resp = cw_client.get_metric_statistics(
                Namespace="AWS/RDS",
                MetricName=metric_name,
                Dimensions=[{"Name": "DBInstanceIdentifier", "Value": inst_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period_seconds,
                Statistics=["Average", "Maximum", "Minimum"],
            )
        except ClientError as e:
            log.warning(f"  CloudWatch error for {inst_id}/{metric_name}: {e}")
            results[metric_name] = {
                "stats": None, "unit": display_unit,
                "rag_key": metric_name, "skip_reason": "error",
            }
            continue

        datapoints = resp.get("Datapoints", [])
        if not datapoints:
            results[metric_name] = {
                "stats": None, "unit": display_unit,
                "rag_key": metric_name, "skip_reason": "no_data",
            }
            continue

        # Extract average values for stats (use Average statistic)
        avg_values = [dp["Average"] for dp in datapoints if "Average" in dp]
        max_values = [dp["Maximum"] for dp in datapoints if "Maximum" in dp]

        # Apply conversions
        rag_key = metric_name
        actual_unit = display_unit

        if convert == "memory_pct" and total_mem_gb:
            total_bytes = total_mem_gb * 1024 * 1024 * 1024
            avg_values = [(v / total_bytes) * 100 for v in avg_values]
            max_values = [(v / total_bytes) * 100 for v in max_values]
            rag_key = "FreeableMemory_pct"
            actual_unit = "%"
        elif convert == "memory_pct" and not total_mem_gb:
            # No memory lookup — convert to GB instead
            avg_values = [v / (1024 ** 3) for v in avg_values]
            max_values = [v / (1024 ** 3) for v in max_values]
            rag_key = "FreeableMemory_pct"
            actual_unit = "GB"
        elif convert == "storage_pct" and allocated_gb > 0:
            total_bytes = allocated_gb * 1024 * 1024 * 1024
            avg_values = [(v / total_bytes) * 100 for v in avg_values]
            max_values = [(v / total_bytes) * 100 for v in max_values]
            rag_key = "FreeStorageSpace_pct"
            actual_unit = "%"
        elif convert == "sec_to_ms":
            avg_values = [v * 1000 for v in avg_values]
            max_values = [v * 1000 for v in max_values]
            rag_key = f"{metric_name}_ms"
            actual_unit = "ms"
        elif convert == "bytes_to_mb":
            avg_values = [v / (1024 * 1024) for v in avg_values]
            max_values = [v / (1024 * 1024) for v in max_values]
            rag_key = "SwapUsage_mb"
            actual_unit = "MB"

        stats = compute_stats(avg_values)
        max_stats = compute_stats(max_values)
        if stats and max_stats:
            stats["abs_max"] = max_stats["max"]

        # Note if memory shown as raw GB
        note = None
        if convert == "memory_pct" and not total_mem_gb:
            note = f"Instance class {inst_class} not in lookup; showing raw GB"

        results[metric_name] = {
            "stats": stats,
            "unit": actual_unit,
            "rag_key": rag_key,
            "note": note,
        }

    return results


# ===================================================================
# RAG evaluation for an instance
# ===================================================================

def evaluate_rag(metrics_data):
    """Evaluate RAG status for all metrics of one instance. Returns per-metric RAG."""
    rag_results = {}
    for metric_name, mdata in metrics_data.items():
        stats = mdata.get("stats")
        rag_key = mdata.get("rag_key", metric_name)
        threshold = RAG_THRESHOLDS.get(rag_key)

        if not stats or not threshold:
            rag_results[metric_name] = {"avg": "—", "p95": "—", "overall": "—",
                                        "avg_text": "skip", "p95_text": "skip", "overall_text": "skip"}
            continue

        g = threshold["green"]
        a = threshold["amber"]
        hw = threshold["higher_is_worse"]

        rag_avg = rag(stats["avg"], g, a, hw)
        rag_p95 = rag(stats["p95"], g, a, hw)
        rag_avg_t = rag_text(stats["avg"], g, a, hw)
        rag_p95_t = rag_text(stats["p95"], g, a, hw)

        # Overall = worst of avg and p95
        priority = {"🔴": 3, "🟡": 2, "🟢": 1, "🔵": 0}
        priority_t = {"red": 3, "amber": 2, "green": 1, "info": 0}
        overall = rag_avg if priority.get(rag_avg, 0) >= priority.get(rag_p95, 0) else rag_p95
        overall_t = rag_avg_t if priority_t.get(rag_avg_t, 0) >= priority_t.get(rag_p95_t, 0) else rag_p95_t

        rag_results[metric_name] = {
            "avg": rag_avg, "p95": rag_p95, "overall": overall,
            "avg_text": rag_avg_t, "p95_text": rag_p95_t, "overall_text": overall_t,
        }
    return rag_results


# ===================================================================
# Report generation — Markdown
# ===================================================================

def generate_markdown(all_data, metadata, output_path):
    """Generate the full markdown baseline report."""
    lines = []
    w = lines.append  # shorthand

    w("# RDS Performance Baseline Report")
    w(f"**Period:** {metadata['period_start']} to {metadata['period_end']} "
      f"({metadata['period_days']} days) | **Region:** {metadata['region']} | "
      f"**Account:** {metadata['account_id']}")
    w(f"**Generated:** {metadata['generated_at']}")
    w("")
    w("---")
    w("")

    # --- Summary counts ---
    summary = {"🟢": 0, "🟡": 0, "🔴": 0, "🔵": 0}
    alerts = []

    for inst_data in all_data:
        for metric_name, rdata in inst_data["rag"].items():
            emoji = rdata.get("overall", "—")
            if emoji in summary:
                summary[emoji] += 1
            if emoji == "🔴":
                stats = inst_data["metrics"].get(metric_name, {}).get("stats")
                if stats:
                    mdef = next((m for m in METRICS if m["name"] == metric_name), None)
                    unit = inst_data["metrics"][metric_name].get("unit", "")
                    alerts.append(
                        f"- 🔴 `{inst_data['instance']['instance_id']}`: "
                        f"{mdef['display'] if mdef else metric_name} "
                        f"avg {fmt(stats['avg'], unit)}, p95 {fmt(stats['p95'], unit)}"
                    )
            elif emoji == "🟡":
                stats = inst_data["metrics"].get(metric_name, {}).get("stats")
                if stats:
                    mdef = next((m for m in METRICS if m["name"] == metric_name), None)
                    unit = inst_data["metrics"][metric_name].get("unit", "")
                    alerts.append(
                        f"- 🟡 `{inst_data['instance']['instance_id']}`: "
                        f"{mdef['display'] if mdef else metric_name} "
                        f"avg {fmt(stats['avg'], unit)}, p95 {fmt(stats['p95'], unit)}"
                    )

    n_primary = sum(1 for d in all_data if not d["instance"]["is_replica"])
    n_replica = sum(1 for d in all_data if d["instance"]["is_replica"])

    w("## Summary")
    w("")
    w("| Metric | 🟢 Green | 🟡 Amber | 🔴 Red | 🔵 Info |")
    w("|--------|----------|----------|--------|---------|")
    w(f"| Count  | {summary['🟢']}       | {summary['🟡']}       | "
      f"{summary['🔴']}      | {summary['🔵']}      |")
    w("")
    w(f"**Instances Scanned:** {len(all_data)} ({n_primary} primary, {n_replica} replica)")
    w("")

    if alerts:
        w("### Alerts")
        w("")
        # Sort: red first, then amber
        red_alerts = [a for a in alerts if a.startswith("- 🔴")]
        amber_alerts = [a for a in alerts if a.startswith("- 🟡")]
        for a in red_alerts:
            w(a)
        for a in amber_alerts:
            w(a)
        w("")

    w("---")
    w("")

    # --- Per-instance detail ---
    for inst_data in all_data:
        inst = inst_data["instance"]
        inst_id = inst["instance_id"]
        engine_str = f"{inst['engine']} {inst['engine_version']}"
        storage_str = f"{inst['allocated_storage_gb']} GB {inst['storage_type']}"
        if inst.get("iops"):
            storage_str += f" ({inst['iops']} IOPS)"
        multi_az = "Yes" if inst["multi_az"] else "No"
        role = "Replica" if inst["is_replica"] else "Primary"
        if inst.get("cluster_id"):
            role += f" (Cluster: {inst['cluster_id']})"

        w(f"## Instance Detail: {inst_id}")
        w("")
        w(f"**Type:** {inst['instance_class']} | **Engine:** {engine_str} | "
          f"**Storage:** {storage_str} | **Multi-AZ:** {multi_az} | **Role:** {role}")
        w("")
        w("| # | Metric | Avg | P95 | Max | RAG | Threshold |")
        w("|---|--------|-----|-----|-----|-----|-----------|")

        for idx, mdef in enumerate(METRICS, 1):
            metric_name = mdef["name"]
            mdata = inst_data["metrics"].get(metric_name, {})
            stats = mdata.get("stats")
            unit = mdata.get("unit", mdef["unit"])
            rag_key = mdata.get("rag_key", metric_name)
            rdata = inst_data["rag"].get(metric_name, {})
            skip = mdata.get("skip_reason")

            if skip == "primary":
                w(f"| {idx} | {mdef['display']} | — | — | — | — | (primary) |")
                continue
            if skip or not stats:
                w(f"| {idx} | {mdef['display']} | N/A | N/A | N/A | — | — |")
                continue

            avg_s = fmt(stats["avg"], unit)
            p95_s = fmt(stats["p95"], unit)
            max_s = fmt(stats.get("abs_max", stats["max"]), unit)
            overall_rag = rdata.get("overall", "—")
            thresh = threshold_display(rag_key)

            w(f"| {idx} | {mdef['display']} | {avg_s} | {p95_s} | {max_s} | {overall_rag} | {thresh} |")

        # Notes
        notes = [mdata.get("note") for mdata in inst_data["metrics"].values() if mdata.get("note")]
        if notes:
            w("")
            for note in notes:
                w(f"> ⚠️ {note}")
        w("")
        w("---")
        w("")

    # --- Full grid ---
    w("## Full Grid (All Instances × Key Metrics)")
    w("")
    w("| Instance | CPU Avg | CPU RAG | Mem Free % | Mem RAG | Storage Free % | "
      "Storage RAG | Read Lat ms | Write Lat ms | Replica Lag |")
    w("|----------|---------|---------|------------|---------|----------------|"
      "-------------|-------------|--------------|-------------|")

    for inst_data in all_data:
        inst_id = inst_data["instance"]["instance_id"]

        def _val(metric_name, stat_key="avg"):
            mdata = inst_data["metrics"].get(metric_name, {})
            stats = mdata.get("stats")
            if not stats:
                return "—"
            unit = mdata.get("unit", "")
            return fmt(stats[stat_key], unit)

        def _rag(metric_name):
            rdata = inst_data["rag"].get(metric_name, {})
            return rdata.get("overall", "—")

        replica_lag = _val("ReplicaLag")
        if inst_data["metrics"].get("ReplicaLag", {}).get("skip_reason") == "primary":
            replica_lag = "—"
        else:
            rl_rag = _rag("ReplicaLag")
            if replica_lag != "—":
                replica_lag = f"{replica_lag} {rl_rag}"

        w(f"| {inst_id} | {_val('CPUUtilization')} | {_rag('CPUUtilization')} | "
          f"{_val('FreeableMemory')} | {_rag('FreeableMemory')} | "
          f"{_val('FreeStorageSpace')} | {_rag('FreeStorageSpace')} | "
          f"{_val('ReadLatency')} | {_val('WriteLatency')} | {replica_lag} |")

    w("")

    # Write file
    report = "\n".join(lines) + "\n"
    with open(output_path, "w") as f:
        f.write(report)
    return output_path


# ===================================================================
# Report generation — JSON
# ===================================================================

def generate_json(all_data, metadata, output_path):
    """Generate JSON baseline report."""
    summary = {"green": 0, "amber": 0, "red": 0, "info": 0}
    for inst_data in all_data:
        for rdata in inst_data["rag"].values():
            t = rdata.get("overall_text", "skip")
            if t in summary:
                summary[t] += 1

    instances_json = []
    for inst_data in all_data:
        inst = inst_data["instance"]
        metrics_json = {}
        for mdef in METRICS:
            mn = mdef["name"]
            mdata = inst_data["metrics"].get(mn, {})
            stats = mdata.get("stats")
            rdata = inst_data["rag"].get(mn, {})
            if stats:
                metrics_json[mn] = {
                    "avg": round(stats["avg"], 3),
                    "p95": round(stats["p95"], 3),
                    "max": round(stats.get("abs_max", stats["max"]), 3),
                    "min": round(stats["min"], 3),
                    "rag_avg": rdata.get("avg_text", "skip"),
                    "rag_p95": rdata.get("p95_text", "skip"),
                    "rag_overall": rdata.get("overall_text", "skip"),
                    "unit": mdata.get("unit", mdef["unit"]),
                    "datapoints": stats["datapoints"],
                }
                if mdata.get("note"):
                    metrics_json[mn]["note"] = mdata["note"]
            else:
                skip = mdata.get("skip_reason", "no_data")
                metrics_json[mn] = {"status": "skipped", "reason": skip}

        instances_json.append({
            "instance_id": inst["instance_id"],
            "instance_class": inst["instance_class"],
            "engine": f"{inst['engine']} {inst['engine_version']}",
            "allocated_storage_gb": inst["allocated_storage_gb"],
            "storage_type": inst["storage_type"],
            "multi_az": inst["multi_az"],
            "is_replica": inst["is_replica"],
            "cluster_id": inst.get("cluster_id"),
            "metrics": metrics_json,
        })

    output = {
        "metadata": metadata,
        "summary": summary,
        "instances": instances_json,
        "thresholds": {k: {kk: vv for kk, vv in v.items()} for k, v in RAG_THRESHOLDS.items()},
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    return output_path


# ===================================================================
# Main
# ===================================================================

def parse_args():
    p = argparse.ArgumentParser(
        description="RDS Performance Baseline Report Generator — Luckin Coffee NA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python baseline_rds.py
  python baseline_rds.py --period 7 --format both --verbose
  python baseline_rds.py --cluster-filter "aws-luckyus-*" --output-dir /app/reports
  python baseline_rds.py --profile databasecheck --region us-east-1
        """,
    )
    p.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    p.add_argument("--profile", default=None, help="AWS CLI profile name")
    p.add_argument("--period", type=int, default=30, help="Lookback period in days (default: 30)")
    p.add_argument("--cluster-filter", default=None,
                   help="Comma-separated name patterns to include (supports wildcards, e.g. 'prod-*,aws-luckyus-*')")
    p.add_argument("--output-dir", default="./reports", help="Output directory (default: ./reports)")
    p.add_argument("--format", choices=["markdown", "json", "both"], default="markdown",
                   help="Output format (default: markdown)")
    p.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return p.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # --- AWS session ---
    session_kwargs = {"region_name": args.region}
    if args.profile:
        session_kwargs["profile_name"] = args.profile
    session = boto3.Session(**session_kwargs)
    rds_client = session.client("rds")
    cw_client = session.client("cloudwatch")
    sts_client = session.client("sts")

    # Get account ID
    try:
        account_id = sts_client.get_caller_identity()["Account"]
    except ClientError:
        account_id = "unknown"
    log.info(f"Account: {account_id} | Region: {args.region}")

    # --- Time window ---
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=args.period)
    period_seconds = 300 if args.period <= 7 else 900

    log.info(f"Period: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')} "
             f"({args.period} days, {period_seconds}s granularity)")

    # --- Filters ---
    filters = None
    if args.cluster_filter:
        filters = [f.strip() for f in args.cluster_filter.split(",")]
        log.info(f"Filters: {filters}")

    # --- Step 1: Discover ---
    log.info("Step 1: Discovering RDS instances...")
    instances = discover_instances(rds_client, filters)
    clusters = discover_clusters(rds_client)
    if not instances:
        log.error("No RDS instances found matching criteria. Exiting.")
        sys.exit(1)
    log.info(f"  Found {len(instances)} instances "
             f"({sum(1 for i in instances if not i['is_replica'])} primary, "
             f"{sum(1 for i in instances if i['is_replica'])} replica)")

    # --- Step 2 & 3: Collect metrics + compute stats ---
    log.info("Step 2-3: Collecting CloudWatch metrics and computing statistics...")
    all_data = []
    for idx, inst in enumerate(instances, 1):
        inst_id = inst["instance_id"]
        log.info(f"  [{idx}/{len(instances)}] Collecting metrics for {inst_id}...")
        try:
            metrics = collect_metrics(cw_client, inst, start_time, end_time, period_seconds)
            rag_results = evaluate_rag(metrics)
            all_data.append({
                "instance": inst,
                "metrics": metrics,
                "rag": rag_results,
            })
        except Exception as e:
            log.error(f"  Failed to collect metrics for {inst_id}: {e}")
            all_data.append({
                "instance": inst,
                "metrics": {},
                "rag": {},
            })

    # --- Metadata ---
    metadata = {
        "service": "rds",
        "region": args.region,
        "account_id": account_id,
        "period_start": start_time.strftime("%Y-%m-%d"),
        "period_end": end_time.strftime("%Y-%m-%d"),
        "period_days": args.period,
        "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "instances_scanned": len(all_data),
        "granularity_seconds": period_seconds,
    }

    # --- Step 5-6: Generate reports ---
    os.makedirs(args.output_dir, exist_ok=True)
    date_str = end_time.strftime("%Y-%m-%d")

    outputs = []
    if args.format in ("markdown", "both"):
        md_path = os.path.join(args.output_dir, f"rds-baseline-{date_str}.md")
        log.info(f"Step 5: Generating markdown report → {md_path}")
        generate_markdown(all_data, metadata, md_path)
        outputs.append(md_path)

    if args.format in ("json", "both"):
        json_path = os.path.join(args.output_dir, f"rds-baseline-{date_str}.json")
        log.info(f"Step 6: Generating JSON report → {json_path}")
        generate_json(all_data, metadata, json_path)
        outputs.append(json_path)

    # --- Done ---
    total_red = sum(1 for d in all_data for r in d["rag"].values() if r.get("overall") == "🔴")
    total_amber = sum(1 for d in all_data for r in d["rag"].values() if r.get("overall") == "🟡")
    log.info(f"Done! {len(all_data)} instances scanned. {total_red} RED, {total_amber} AMBER alerts.")
    for o in outputs:
        log.info(f"  Output: {o}")

    # Exit code: 2 if any RED, 1 if any AMBER, 0 if all green
    if total_red > 0:
        sys.exit(2)
    elif total_amber > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
