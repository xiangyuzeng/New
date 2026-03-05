#!/usr/bin/env python3
"""
CloudWatch Log Retention Audit Tool — Luckin Coffee North America (LCNA)

Discovers CloudWatch log groups with no/indefinite retention, categorizes them,
estimates storage costs, generates reports, and optionally applies retention policies.

Minimum IAM Permissions Required:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:PutRetentionPolicy",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}

Usage:
    python audit_cw_logs.py                          # Dry-run report only
    python audit_cw_logs.py --apply                  # Apply with confirmation
    python audit_cw_logs.py --apply --yes             # Apply without confirmation (cron)
    python audit_cw_logs.py --format both --min-stored-mb 10
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError, BotoCoreError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STORAGE_COST_PER_GB_MONTH = 0.033  # USD per GB stored per month
EXCESSIVE_RETENTION_DAYS = 90      # Flag groups with retention > this value

CATEGORY_RULES: list[tuple[str, callable]] = []  # populated in _build_category_rules()

DEFAULT_RETENTION_MAP = {
    "RDS SlowQuery":    30,
    "RDS Error":        30,
    "RDS General":      14,
    "RDS Audit":        90,
    "Lambda":           7,
    "API Gateway":      30,
    "Internet Monitor": 7,
    "VPC Flow Logs":    30,
    "ECS / Container":  30,
    "ElastiCache":      30,
    "CloudTrail":       90,
    "EC2 / Application":30,
    "Other":            30,
}

logger = logging.getLogger("cw-audit")

# ---------------------------------------------------------------------------
# Categorisation
# ---------------------------------------------------------------------------

def categorize(name: str) -> str:
    """Classify a log group name into a category."""
    n = name.lower()

    if "/aws/rds/" in n:
        if "slowquery" in n:
            return "RDS SlowQuery"
        if "error" in n:
            return "RDS Error"
        if "general" in n:
            return "RDS General"
        if "audit" in n:
            return "RDS Audit"
        return "RDS General"  # fallback for other /aws/rds/ patterns

    if "/aws/lambda/" in n:
        return "Lambda"

    if "/aws/apigateway/" in n or "api-gateway-execution-logs" in n:
        return "API Gateway"

    if "internetmonitor" in n:
        return "Internet Monitor"

    if "/aws/vpc/flowlogs" in n or "vpcflowlogs" in n:
        return "VPC Flow Logs"

    if "/ecs/" in n or "/aws/ecs/" in n:
        return "ECS / Container"

    if "/aws/elasticache/" in n:
        return "ElastiCache"

    if "aws-cloudtrail-logs" in n or "/aws/cloudtrail/" in n or "cloudtrail" in n:
        return "CloudTrail"

    if "/ec2/" in n:
        return "EC2 / Application"

    return "Other"


def retention_for_category(category: str, default_days: int) -> int:
    """Return the recommended retention for a category."""
    return DEFAULT_RETENTION_MAP.get(category, default_days)


# ---------------------------------------------------------------------------
# AWS helpers
# ---------------------------------------------------------------------------

def get_session(region: str, profile: str | None) -> boto3.Session:
    kwargs: dict[str, Any] = {"region_name": region}
    if profile:
        kwargs["profile_name"] = profile
    return boto3.Session(**kwargs)


def get_account_id(session: boto3.Session) -> str:
    try:
        return session.client("sts").get_caller_identity()["Account"]
    except (ClientError, BotoCoreError) as exc:
        logger.warning("Could not determine account ID: %s", exc)
        return "unknown"


def discover_log_groups(
    client,
    min_stored_bytes: int = 0,
    category_filter: set[str] | None = None,
) -> list[dict]:
    """Paginate through all log groups and return those needing remediation."""
    flagged: list[dict] = []
    total_scanned = 0
    access_errors: list[str] = []

    paginator = client.get_paginator("describe_log_groups")
    try:
        for page in paginator.paginate():
            for lg in page.get("logGroups", []):
                total_scanned += 1
                retention = lg.get("retentionInDays")  # None = Never Expire

                # Flag if no retention or excessively long
                if retention is not None and retention <= EXCESSIVE_RETENTION_DAYS:
                    continue

                stored_bytes = lg.get("storedBytes", 0)
                if stored_bytes < min_stored_bytes:
                    continue

                name = lg["logGroupName"]
                cat = categorize(name)

                if category_filter and cat not in category_filter:
                    continue

                creation_ms = lg.get("creationTime", 0)
                creation_dt = datetime.fromtimestamp(creation_ms / 1000, tz=timezone.utc) if creation_ms else None
                now = datetime.now(timezone.utc)
                age_days = (now - creation_dt).days if creation_dt else 0

                stored_gb = round(stored_bytes / (1024 ** 3), 2)
                monthly_cost = round(stored_gb * STORAGE_COST_PER_GB_MONTH, 4)

                # Estimate growth rate: stored_gb / age_in_months
                age_months = max(age_days / 30.44, 1)
                growth_gb_per_month = stored_gb / age_months
                # If we apply 30-day retention, we keep ~1 month of data
                projected_stored_30d = round(growth_gb_per_month, 2)
                projected_cost_30d = round(projected_stored_30d * STORAGE_COST_PER_GB_MONTH, 4)
                savings = round(max(monthly_cost - projected_cost_30d, 0), 4)

                flagged.append({
                    "logGroupName": name,
                    "arn": lg.get("arn", ""),
                    "storedBytes": stored_bytes,
                    "storedGB": stored_gb,
                    "creationTime": creation_dt.isoformat() if creation_dt else "unknown",
                    "ageDays": age_days,
                    "retentionInDays": retention if retention else "Never Expire",
                    "category": cat,
                    "monthlyCost": monthly_cost,
                    "growthGBPerMonth": round(growth_gb_per_month, 2),
                    "projectedCost30d": projected_cost_30d,
                    "estimatedSavings": savings,
                })
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "AccessDeniedException":
            logger.error("AccessDeniedException listing log groups: %s", exc)
            access_errors.append("describe_log_groups: AccessDenied")
        else:
            raise

    return flagged, total_scanned, access_errors


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _fmt_usd(val: float) -> str:
    return f"${val:,.2f}"


def _fmt_gb(val: float) -> str:
    return f"{val:,.2f}"


def generate_markdown_report(
    flagged: list[dict],
    total_scanned: int,
    account_id: str,
    region: str,
    apply_mode: bool,
    access_errors: list[str],
    remediation_results: list[dict] | None = None,
) -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    total_gb = sum(g["storedGB"] for g in flagged)
    total_cost = sum(g["monthlyCost"] for g in flagged)
    total_savings = sum(g["estimatedSavings"] for g in flagged)

    # Group by category
    by_cat: dict[str, list[dict]] = {}
    for g in flagged:
        by_cat.setdefault(g["category"], []).append(g)

    lines: list[str] = []
    a = lines.append

    a(f"# CloudWatch Log Retention Audit Report")
    a(f"**Date:** {now_str} | **Account:** {account_id} | **Region:** {region}")
    a("")

    # -- Executive Summary --
    a("## Executive Summary")
    a(f"- **Total Log Groups Scanned:** {total_scanned}")
    a(f"- **Flagged (No/Excessive Retention):** {len(flagged)}")
    a(f"- **Total Stored Data:** {_fmt_gb(total_gb)} GB")
    a(f"- **Current Monthly Storage Cost:** {_fmt_usd(total_cost)}")
    a(f"- **Estimated Monthly Savings (with retention):** {_fmt_usd(total_savings)}")
    a(f"- **Estimated Annual Savings:** {_fmt_usd(total_savings * 12)}")
    if access_errors:
        a(f"- **Access Errors:** {len(access_errors)} — some groups could not be inspected")
    a("")

    # -- Breakdown by Category --
    a("## Breakdown by Category")
    a("")
    for cat in sorted(by_cat.keys()):
        groups = sorted(by_cat[cat], key=lambda g: g["storedBytes"], reverse=True)
        cat_gb = sum(g["storedGB"] for g in groups)
        cat_cost = sum(g["monthlyCost"] for g in groups)
        a(f"### {cat} ({len(groups)} groups, {_fmt_gb(cat_gb)} GB, {_fmt_usd(cat_cost)}/mo)")
        a("")
        a("| Log Group | Stored GB | Age (days) | Retention | Monthly Cost |")
        a("|-----------|-----------|------------|-----------|--------------|")
        for g in groups:
            name = g["logGroupName"]
            # Truncate very long names for readability
            if len(name) > 70:
                name = name[:67] + "..."
            a(f"| {name} | {_fmt_gb(g['storedGB'])} | {g['ageDays']} | {g['retentionInDays']} | {_fmt_usd(g['monthlyCost'])} |")
        a("")

    # -- Top 20 Offenders --
    a("## Top 20 Offenders by Storage")
    a("")
    top20 = sorted(flagged, key=lambda g: g["storedBytes"], reverse=True)[:20]
    a("| # | Log Group | Category | Stored GB | Monthly Cost | Est. Savings |")
    a("|---|-----------|----------|-----------|--------------|--------------|")
    for i, g in enumerate(top20, 1):
        name = g["logGroupName"]
        if len(name) > 60:
            name = name[:57] + "..."
        a(f"| {i} | {name} | {g['category']} | {_fmt_gb(g['storedGB'])} | {_fmt_usd(g['monthlyCost'])} | {_fmt_usd(g['estimatedSavings'])} |")
    a("")

    # -- Recommended Retention Policies --
    a("## Recommended Retention Policies")
    a("")
    a("| Category | Retention (days) | Rationale |")
    a("|----------|-----------------|-----------|")
    rationale = {
        "RDS SlowQuery":     "30 days sufficient for performance investigation cycles",
        "RDS Error":         "30 days covers typical incident investigation window",
        "RDS General":       "14 days for general log review; high volume, low retention value",
        "RDS Audit":         "90 days for compliance and security audit requirements",
        "Lambda":            "7 days — high-volume debug logs, rarely needed beyond a week",
        "API Gateway":       "30 days for API troubleshooting",
        "Internet Monitor":  "7 days — metrics data, quickly stale",
        "VPC Flow Logs":     "30 days for network security investigation",
        "ECS / Container":   "30 days for container troubleshooting",
        "ElastiCache":       "30 days for cache performance analysis",
        "CloudTrail":        "90 days for compliance and security audit trail",
        "EC2 / Application": "30 days for application debugging",
        "Other":             "30 days default — review individually if needed",
    }
    for cat in sorted(DEFAULT_RETENTION_MAP.keys()):
        days = DEFAULT_RETENTION_MAP[cat]
        r = rationale.get(cat, "")
        a(f"| {cat} | {days} | {r} |")
    a("")

    # -- Remediation Status --
    a("## Remediation Status")
    a("")
    if not apply_mode:
        a("- **Mode:** DRY RUN (use `--apply` to remediate)")
        a("- No changes were made to any log groups.")
    else:
        if remediation_results:
            success = sum(1 for r in remediation_results if r["status"] == "success")
            failed = sum(1 for r in remediation_results if r["status"] == "failed")
            a(f"- **Mode:** APPLY")
            a(f"- **Success:** {success} log groups updated")
            a(f"- **Failed:** {failed} log groups could not be updated")
            if failed:
                a("")
                a("### Failed Remediations")
                a("| Log Group | Error |")
                a("|-----------|-------|")
                for r in remediation_results:
                    if r["status"] == "failed":
                        a(f"| {r['logGroupName']} | {r['error']} |")
        else:
            a("- **Mode:** APPLY (no groups required remediation)")
    a("")

    if access_errors:
        a("## Access Errors")
        a("")
        for err in access_errors:
            a(f"- {err}")
        a("")

    # -- Footer --
    a("---")
    a(f"*Generated by `audit_cw_logs.py` on {now_str}*")

    return "\n".join(lines)


def generate_json_report(
    flagged: list[dict],
    total_scanned: int,
    account_id: str,
    region: str,
    apply_mode: bool,
    access_errors: list[str],
    remediation_results: list[dict] | None = None,
) -> str:
    total_gb = sum(g["storedGB"] for g in flagged)
    total_cost = sum(g["monthlyCost"] for g in flagged)
    total_savings = sum(g["estimatedSavings"] for g in flagged)

    report = {
        "reportDate": datetime.now(timezone.utc).isoformat(),
        "accountId": account_id,
        "region": region,
        "totalScanned": total_scanned,
        "totalFlagged": len(flagged),
        "totalStoredGB": round(total_gb, 2),
        "currentMonthlyCost": round(total_cost, 2),
        "estimatedMonthlySavings": round(total_savings, 2),
        "estimatedAnnualSavings": round(total_savings * 12, 2),
        "mode": "apply" if apply_mode else "dry-run",
        "accessErrors": access_errors,
        "logGroups": flagged,
        "remediationResults": remediation_results or [],
    }
    return json.dumps(report, indent=2, default=str)


# ---------------------------------------------------------------------------
# Remediation
# ---------------------------------------------------------------------------

def apply_retention_policies(
    client,
    flagged: list[dict],
    default_days: int,
) -> list[dict]:
    """Apply retention policies. Returns list of {logGroupName, retentionDays, status, error}."""
    results = []
    for g in flagged:
        cat = g["category"]
        days = retention_for_category(cat, default_days)
        name = g["logGroupName"]
        try:
            client.put_retention_policy(logGroupName=name, retentionInDays=days)
            logger.info("Applied %d-day retention to %s", days, name)
            results.append({"logGroupName": name, "retentionDays": days, "status": "success", "error": None})
        except ClientError as exc:
            err_msg = exc.response["Error"].get("Message", str(exc))
            logger.error("Failed to set retention on %s: %s", name, err_msg)
            results.append({"logGroupName": name, "retentionDays": days, "status": "failed", "error": err_msg})
        except BotoCoreError as exc:
            logger.error("Failed to set retention on %s: %s", name, exc)
            results.append({"logGroupName": name, "retentionDays": days, "status": "failed", "error": str(exc)})
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CloudWatch Log Retention Audit & Remediation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Dry-run markdown report
  %(prog)s --apply                            # Apply with confirmation prompt
  %(prog)s --apply --yes --format both        # Cron-safe: apply + both formats
  %(prog)s --min-stored-mb 100 --category-filter "RDS SlowQuery,Lambda"
        """,
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--profile", default=None, help="AWS CLI profile name")
    parser.add_argument("--apply", action="store_true", help="Apply retention policies (default: dry-run)")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--retention", type=int, default=30, help="Default retention in days (default: 30)")
    parser.add_argument("--output-dir", default="./reports", help="Output directory (default: ./reports)")
    parser.add_argument("--min-stored-mb", type=float, default=0, help="Minimum stored MB to flag (default: 0)")
    parser.add_argument("--format", choices=["markdown", "json", "both"], default="markdown", help="Output format")
    parser.add_argument("--category-filter", default=None, help="Comma-separated categories to include")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # Logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("Starting CloudWatch Log Retention Audit")
    logger.info("Region: %s | Apply: %s | Default retention: %d days",
                args.region, args.apply, args.retention)

    # Parse category filter
    category_filter: set[str] | None = None
    if args.category_filter:
        category_filter = {c.strip() for c in args.category_filter.split(",")}
        logger.info("Category filter: %s", category_filter)

    min_stored_bytes = int(args.min_stored_mb * 1024 * 1024)

    # AWS session
    try:
        session = get_session(args.region, args.profile)
        client = session.client("logs")
        account_id = get_account_id(session)
    except Exception as exc:
        logger.critical("Failed to initialize AWS session: %s", exc)
        return 2

    logger.info("Account: %s", account_id)

    # Step 1 & 2: Discover and categorize
    try:
        flagged, total_scanned, access_errors = discover_log_groups(
            client, min_stored_bytes, category_filter
        )
    except Exception as exc:
        logger.critical("Failed to discover log groups: %s", exc)
        return 2

    logger.info("Scanned %d log groups, flagged %d", total_scanned, len(flagged))

    if not flagged:
        logger.info("No log groups require remediation. Generating report anyway.")

    # Step 5: Apply (if requested)
    remediation_results = None
    if args.apply and flagged:
        # Build summary for confirmation
        by_cat_summary: dict[str, int] = {}
        for g in flagged:
            cat = g["category"]
            by_cat_summary[cat] = by_cat_summary.get(cat, 0) + 1

        print("\n=== Retention Policy Changes ===")
        print(f"{'Category':<25} {'Count':>6} {'Retention (days)':>16}")
        print("-" * 50)
        for cat in sorted(by_cat_summary.keys()):
            days = retention_for_category(cat, args.retention)
            print(f"{cat:<25} {by_cat_summary[cat]:>6} {days:>16}")
        print(f"\nTotal: {len(flagged)} log groups will be updated.\n")

        if not args.yes:
            answer = input("Proceed? [y/N]: ").strip().lower()
            if answer != "y":
                logger.info("User cancelled remediation.")
                print("Cancelled. Generating report in dry-run mode.")
                args.apply = False

    if args.apply and flagged:
        logger.info("Applying retention policies...")
        remediation_results = apply_retention_policies(client, flagged, args.retention)
        success_count = sum(1 for r in remediation_results if r["status"] == "success")
        fail_count = sum(1 for r in remediation_results if r["status"] == "failed")
        logger.info("Remediation complete: %d success, %d failed", success_count, fail_count)

    # Step 4: Generate report
    os.makedirs(args.output_dir, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base_name = f"cloudwatch-log-retention-report-{date_str}"
    outputs: list[str] = []

    if args.format in ("markdown", "both"):
        md = generate_markdown_report(
            flagged, total_scanned, account_id, args.region,
            args.apply, access_errors, remediation_results,
        )
        md_path = os.path.join(args.output_dir, f"{base_name}.md")
        with open(md_path, "w") as f:
            f.write(md)
        outputs.append(md_path)
        logger.info("Markdown report: %s", md_path)

    if args.format in ("json", "both"):
        js = generate_json_report(
            flagged, total_scanned, account_id, args.region,
            args.apply, access_errors, remediation_results,
        )
        json_path = os.path.join(args.output_dir, f"{base_name}.json")
        with open(json_path, "w") as f:
            f.write(js)
        outputs.append(json_path)
        logger.info("JSON report: %s", json_path)

    # Summary to stdout
    total_gb = sum(g["storedGB"] for g in flagged)
    total_cost = sum(g["monthlyCost"] for g in flagged)
    total_savings = sum(g["estimatedSavings"] for g in flagged)

    print(f"\n{'='*60}")
    print(f"CloudWatch Log Retention Audit — {date_str}")
    print(f"{'='*60}")
    print(f"  Scanned:          {total_scanned} log groups")
    print(f"  Flagged:          {len(flagged)}")
    print(f"  Total stored:     {total_gb:,.2f} GB")
    print(f"  Monthly cost:     ${total_cost:,.2f}")
    print(f"  Est. savings/mo:  ${total_savings:,.2f}")
    print(f"  Est. savings/yr:  ${total_savings * 12:,.2f}")
    print(f"  Mode:             {'APPLY' if args.apply else 'DRY RUN'}")
    for p in outputs:
        print(f"  Report:           {p}")
    print(f"{'='*60}\n")

    # Exit code
    if remediation_results:
        if any(r["status"] == "failed" for r in remediation_results):
            return 1
    if access_errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
