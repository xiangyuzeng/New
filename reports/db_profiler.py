#!/usr/bin/env python3
"""
Database Profiler — Schema discovery and data distribution analysis.

Validates requirements document LCNA-OPS-2026-021-v2 against actual production data.
Connects via pipeline/config/settings.py (AWS Secrets Manager + RDS discovery).

Usage:
    cd /app/luckin-ops-dashboard
    python investigation/db_profiler.py

Output:
    investigation/findings.json   — structured results
    investigation/findings.md     — human-readable report
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pymysql
import pymysql.cursors

from config.settings import BUSINESS_DB, HEALTH_DB, OPSHOP_DB

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("db_profiler")

OUTPUT_DIR = Path(__file__).resolve().parent

_VALID_ORDER = """status IN (20, 90) AND refund_status != 5
  AND shop_number LIKE 'US%%' AND shop_number != 'US00000'"""


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def connect(dsn: dict) -> pymysql.Connection:
    return pymysql.connect(
        host=dsn["host"],
        port=dsn["port"],
        user=dsn["user"],
        password=dsn["password"],
        database=dsn.get("database", ""),
        connect_timeout=10,
        read_timeout=60,
        cursorclass=pymysql.cursors.DictCursor,
    )


def safe_query(cur, sql, params=None, label="query"):
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    except Exception as exc:
        logger.error("%s failed: %s", label, exc)
        return []


# ---------------------------------------------------------------------------
# Schema discovery
# ---------------------------------------------------------------------------

DESCRIBE_QUERIES = {
    "t_order": ("BUSINESS", "DESCRIBE luckyus_sales_order.t_order"),
    "t_order_item": ("BUSINESS", "DESCRIBE luckyus_sales_order.t_order_item"),
    "t_order_make": ("BUSINESS", "DESCRIBE luckyus_sales_order.t_order_make"),
    "t_order_comment": ("BUSINESS", "DESCRIBE luckyus_sales_order.t_order_comment"),
    "t_collect_order_tenant_inter": ("HEALTH", "DESCRIBE luckyus_iluckyhealth.t_collect_order_tenant_inter"),
    "t_collect_shop_inter": ("HEALTH", "DESCRIBE luckyus_iluckyhealth.t_collect_shop_inter"),
    "t_shop_info": ("OPSHOP", "DESCRIBE luckyus_opshop.t_shop_info"),
}


def run_describes(connections: dict) -> dict:
    results = {}
    for table, (db_key, sql) in DESCRIBE_QUERIES.items():
        conn = connections.get(db_key)
        if not conn:
            logger.warning("Skipping DESCRIBE %s — %s not connected", table, db_key)
            continue
        with conn.cursor() as cur:
            rows = safe_query(cur, sql, label=f"DESCRIBE {table}")
            results[table] = {
                "columns": rows,
                "column_count": len(rows),
                "column_names": [r["Field"] for r in rows],
            }
            logger.info("DESCRIBE %s: %d columns", table, len(rows))
    return results


def answer_critical_questions(schema: dict) -> dict:
    t_order_cols = set(schema.get("t_order", {}).get("column_names", []))
    t_order_item_cols = set(schema.get("t_order_item", {}).get("column_names", []))
    t_order_make_cols = set(schema.get("t_order_make", {}).get("column_names", []))
    t_order_comment_cols = set(schema.get("t_order_comment", {}).get("column_names", []))
    t_shop_info_cols = set(schema.get("t_shop_info", {}).get("column_names", []))

    return {
        "Q1_comment_has_order_id": "order_id" in t_order_comment_cols,
        "Q2_order_has_cancel_reason": "cancel_reason" in t_order_cols or "cancel_type" in t_order_cols,
        "Q3_order_item_extras": sorted(
            t_order_item_cols - {"id", "tenant", "order_id", "spu_name", "one_category_name", "pay_money", "create_time", "modify_time", "version"}
        ),
        "Q4_order_has_discount_cols": {
            "total_money": "total_money" in t_order_cols,
            "payable_money": "payable_money" in t_order_cols,
            "coupon_id": "coupon_id" in t_order_cols,
        },
        "Q5_order_make_extras": {
            "make_id": "make_id" in t_order_make_cols,
            "make_name": "make_name" in t_order_make_cols,
            "dispatch_time": "dispatch_time" in t_order_make_cols,
            "expect_time": "expect_time" in t_order_make_cols,
        },
        "Q6_shop_info_geo": {
            "longitude": "location_longitude" in t_shop_info_cols,
            "latitude": "location_latitude" in t_shop_info_cols,
            "set_up_time": "set_up_time" in t_shop_info_cols,
            "operation_area": "operation_area" in t_shop_info_cols,
        },
    }


# ---------------------------------------------------------------------------
# Distribution queries
# ---------------------------------------------------------------------------

def run_distributions(connections: dict, schema: dict) -> dict:
    biz = connections.get("BUSINESS")
    health = connections.get("HEALTH")
    opshop = connections.get("OPSHOP")
    results = {}
    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

    if biz:
        with biz.cursor() as cur:
            # 3A: Channel distribution
            results["3A_channel"] = safe_query(cur, f"""
                SELECT channel, COUNT(*) AS orders, ROUND(SUM(pay_money),2) AS revenue,
                       ROUND(AVG(pay_money),2) AS avg_ticket, COUNT(DISTINCT user_no) AS unique_customers
                FROM luckyus_sales_order.t_order
                WHERE create_time >= %s AND {_VALID_ORDER}
                GROUP BY channel ORDER BY orders DESC
            """, (week_ago,), "3A_channel")

            # 3B: Refund status
            results["3B_refund_status"] = safe_query(cur, f"""
                SELECT refund_status, COUNT(*) AS order_count
                FROM luckyus_sales_order.t_order
                WHERE create_time >= %s AND shop_number LIKE 'US%%' AND shop_number != 'US00000'
                GROUP BY refund_status ORDER BY order_count DESC
            """, (week_ago,), "3B_refund_status")

            # 3C: Order status
            results["3C_order_status"] = safe_query(cur, f"""
                SELECT status, COUNT(*) AS order_count
                FROM luckyus_sales_order.t_order
                WHERE create_time >= %s AND shop_number LIKE 'US%%' AND shop_number != 'US00000'
                GROUP BY status ORDER BY order_count DESC
            """, (week_ago,), "3C_order_status")

            # 3D: Product categories
            results["3D_product_category"] = safe_query(cur, f"""
                SELECT oi.one_category_name, COUNT(*) AS item_count,
                       COUNT(DISTINCT oi.spu_name) AS unique_products
                FROM luckyus_sales_order.t_order_item oi
                JOIN luckyus_sales_order.t_order o ON oi.order_id = o.id
                WHERE o.create_time >= %s AND o.status IN (20,90) AND o.refund_status != 5
                  AND o.shop_number LIKE 'US%%' AND o.shop_number != 'US00000'
                GROUP BY oi.one_category_name ORDER BY item_count DESC
            """, (week_ago,), "3D_product_category")

            # 3E: Repeat behavior (30 days)
            results["3E_repeat_behavior"] = safe_query(cur, f"""
                SELECT order_bucket, COUNT(*) AS customer_count FROM (
                  SELECT user_no, CASE
                    WHEN COUNT(*) = 1 THEN '1_time'
                    WHEN COUNT(*) BETWEEN 2 AND 3 THEN '2_3_times'
                    WHEN COUNT(*) BETWEEN 4 AND 7 THEN '4_7_times'
                    WHEN COUNT(*) BETWEEN 8 AND 14 THEN '8_14_times'
                    ELSE '15_plus' END AS order_bucket
                  FROM luckyus_sales_order.t_order
                  WHERE create_time >= %s AND {_VALID_ORDER}
                    AND user_no IS NOT NULL AND user_no != ''
                  GROUP BY user_no
                ) bucketed GROUP BY order_bucket
            """, (month_ago,), "3E_repeat_behavior")

            # 3F: Spend tiers
            results["3F_spend_tier"] = safe_query(cur, f"""
                SELECT CASE
                    WHEN pay_money < 3 THEN 'tier_0_3'
                    WHEN pay_money < 5 THEN 'tier_3_5'
                    WHEN pay_money < 8 THEN 'tier_5_8'
                    ELSE 'tier_8_plus' END AS spend_tier,
                  COUNT(*) AS order_count, ROUND(SUM(pay_money),2) AS total_revenue,
                  ROUND(AVG(pay_money),2) AS avg_in_tier
                FROM luckyus_sales_order.t_order
                WHERE create_time >= %s AND {_VALID_ORDER}
                GROUP BY spend_tier ORDER BY spend_tier
            """, (week_ago,), "3F_spend_tier")

            # 3G: Review volume
            results["3G_review_volume"] = safe_query(cur, """
                SELECT COUNT(*) AS total_reviews,
                       SUM(CASE WHEN level = 1 THEN 1 ELSE 0 END) AS satisfied,
                       SUM(CASE WHEN level = 2 THEN 1 ELSE 0 END) AS unsatisfied,
                       COUNT(DISTINCT level) AS distinct_levels
                FROM luckyus_sales_order.t_order_comment
                WHERE create_time >= %s
            """, (week_ago,), "3G_review_volume")

            # 3H: Prep time
            results["3H_prep_time"] = safe_query(cur, """
                SELECT COUNT(*) AS total_orders,
                  ROUND(AVG(TIMESTAMPDIFF(SECOND, accept_time, finish_time))/60, 1) AS avg_min,
                  ROUND(MIN(TIMESTAMPDIFF(SECOND, accept_time, finish_time))/60, 1) AS min_min,
                  ROUND(MAX(TIMESTAMPDIFF(SECOND, accept_time, finish_time))/60, 1) AS max_min,
                  SUM(CASE WHEN TIMESTAMPDIFF(SECOND, accept_time, finish_time) <= 180 THEN 1 ELSE 0 END) AS within_3min,
                  SUM(CASE WHEN TIMESTAMPDIFF(SECOND, accept_time, finish_time) <= 300 THEN 1 ELSE 0 END) AS within_5min,
                  SUM(CASE WHEN accept_time IS NULL OR finish_time IS NULL THEN 1 ELSE 0 END) AS null_timestamps
                FROM luckyus_sales_order.t_order_make
                WHERE create_time >= %s
            """, (week_ago,), "3H_prep_time")

            # 3I: User coverage
            results["3I_user_coverage"] = safe_query(cur, f"""
                SELECT COUNT(DISTINCT user_no) AS total_users,
                       SUM(CASE WHEN user_no IS NULL OR user_no = '' THEN 1 ELSE 0 END) AS null_user_orders,
                       COUNT(*) AS total_orders
                FROM luckyus_sales_order.t_order
                WHERE create_time >= %s AND {_VALID_ORDER}
            """, (week_ago,), "3I_user_coverage")

            # 3J: Per-store satisfaction (only if order_id confirmed)
            cq = answer_critical_questions(schema)
            if cq.get("Q1_comment_has_order_id"):
                results["3J_per_store_satisfaction"] = safe_query(cur, f"""
                    SELECT o.shop_name, COUNT(*) AS reviews,
                           ROUND(SUM(CASE WHEN c.level=1 THEN 1 ELSE 0 END)/COUNT(*)*100,1) AS sat_pct
                    FROM luckyus_sales_order.t_order_comment c
                    JOIN luckyus_sales_order.t_order o ON c.order_id = o.id
                    WHERE c.create_time >= %s
                      AND o.status IN (20,90) AND o.shop_number LIKE 'US%%' AND o.shop_number != 'US00000'
                    GROUP BY o.shop_name ORDER BY reviews DESC
                """, (week_ago,), "3J_per_store_satisfaction")

            # 3K: Historical depth
            results["3K_historical_depth"] = safe_query(cur, """
                SELECT MIN(create_time) AS earliest_order, MAX(create_time) AS latest_order,
                       COUNT(*) AS total_orders,
                       DATEDIFF(MAX(create_time), MIN(create_time)) AS days_span
                FROM luckyus_sales_order.t_order
                WHERE shop_number LIKE 'US%%' AND shop_number != 'US00000'
            """, label="3K_historical_depth")

    if health:
        with health.cursor() as cur:
            results["health_metrics"] = safe_query(cur, """
                SELECT metric_name, COUNT(*) AS cnt
                FROM luckyus_iluckyhealth.t_collect_order_tenant_inter
                WHERE metric_value_comment = 'LKUS' AND create_time >= %s
                GROUP BY metric_name ORDER BY cnt DESC LIMIT 20
            """, (week_ago,), "health_metrics")

    if opshop:
        with opshop.cursor() as cur:
            results["shop_status"] = safe_query(cur, """
                SELECT status, COUNT(*) AS cnt FROM luckyus_opshop.t_shop_info
                WHERE shop_no LIKE 'US%%' AND shop_no != 'US00000' AND shop_no NOT LIKE 'US999%%'
                GROUP BY status
            """, label="shop_status")

    return results


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_findings_json(schema, questions, distributions, output_path):
    data = {
        "meta": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "generator": "investigation/db_profiler.py",
            "requirements_doc": "LCNA-OPS-2026-021-v2",
        },
        "schema_discovery": schema,
        "critical_questions": questions,
        "distributions": distributions,
    }
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, cls=DecimalEncoder)
    logger.info("Wrote %s", output_path)


def write_findings_md(schema, questions, distributions, output_path):
    lines = [
        "# Database Investigation Report — LCNA-OPS-2026-021-v2",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Method**: db_profiler.py via pipeline/config/settings.py",
        "",
        "## Schema Discovery",
        "",
    ]
    for table, info in schema.items():
        lines.append(f"### {table} ({info['column_count']} columns)")
        lines.append("")
        lines.append("| Column | Type | Nullable | Key |")
        lines.append("|--------|------|----------|-----|")
        for col in info.get("columns", []):
            lines.append(f"| {col['Field']} | {col['Type']} | {col['Null']} | {col.get('Key', '')} |")
        lines.append("")

    lines.append("## Critical Questions")
    lines.append("")
    for key, val in questions.items():
        lines.append(f"- **{key}**: `{val}`")
    lines.append("")

    lines.append("## Distribution Results")
    lines.append("")
    for query_id, rows in distributions.items():
        lines.append(f"### {query_id}")
        lines.append(f"```json")
        lines.append(json.dumps(rows, indent=2, cls=DecimalEncoder, default=str)[:2000])
        lines.append("```")
        lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    logger.info("Wrote %s", output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 60)
    logger.info("Database Profiler — LCNA-OPS-2026-021-v2 Validation")
    logger.info("=" * 60)

    connections = {}
    try:
        if BUSINESS_DB:
            connections["BUSINESS"] = connect(BUSINESS_DB)
            logger.info("Connected to BUSINESS_DB (salesorder)")
        else:
            logger.warning("BUSINESS_DB not configured (set BUSINESS_DB_INSTANCE env var)")

        if HEALTH_DB:
            connections["HEALTH"] = connect(HEALTH_DB)
            logger.info("Connected to HEALTH_DB (iluckyhealth)")
        else:
            logger.warning("HEALTH_DB not configured (set HEALTH_DB_INSTANCE env var)")

        if OPSHOP_DB:
            connections["OPSHOP"] = connect(OPSHOP_DB)
            logger.info("Connected to OPSHOP_DB (opshop)")
        else:
            logger.warning("OPSHOP_DB not configured (set OPSHOP_DB_INSTANCE env var)")

        if not connections:
            logger.error("No database connections available. Exiting.")
            return 1

        # Phase 1: Schema discovery
        logger.info("Phase 1: Schema discovery...")
        schema = run_describes(connections)
        questions = answer_critical_questions(schema)
        logger.info("Critical questions answered: %s", json.dumps(questions, indent=2))

        # Phase 2: Distribution profiling
        logger.info("Phase 2: Distribution profiling...")
        distributions = run_distributions(connections, schema)

        # Phase 3: Write outputs
        logger.info("Phase 3: Writing outputs...")
        write_findings_json(schema, questions, distributions, OUTPUT_DIR / "findings.json")
        write_findings_md(schema, questions, distributions, OUTPUT_DIR / "findings.md")

        logger.info("Done. Check investigation/findings.json and investigation/findings.md")
        return 0

    finally:
        for name, conn in connections.items():
            try:
                conn.close()
                logger.info("Closed %s connection", name)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
