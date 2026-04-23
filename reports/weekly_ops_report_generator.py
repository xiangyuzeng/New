#!/usr/bin/env python3
"""
Luckin Coffee North America — Weekly Operations Report Generator
================================================================
LCNA-OPS-2026-022 v1.0 compliant.

Generates a 7-chapter PDF report:
  1. 本周运营概览 (Weekly Overview)
  2. 营收与客流分析 (Revenue & Traffic)
  3. 门店运营排名 (Store Rankings)
  4. 渠道与营销分析 (Channel & Marketing)
  5. 产品与供应链 (Product & Supply Chain)
  6. 本周洞察与预警 (Insights & Alerts)
  7. 下周关注重点 (Next Week Focus)

Usage:
    python3 weekly_ops_report_generator.py                          # current week
    python3 weekly_ops_report_generator.py --week-start 2026-04-06  # specific week
    python3 weekly_ops_report_generator.py --dry-run                # preview data, no PDF
    python3 weekly_ops_report_generator.py --config /path/config.yaml    # custom config

All configuration (per-schema DB hosts, output paths, font) is read from
config.yaml alongside this script (override via --config). ${ENV_VAR} tokens
in the YAML are expanded from the environment — use them for passwords.

Data source: MySQL via pymysql. The three schemas
(luckyus_sales_order / luckyus_iluckyhealth / luckyus_opshop) each live
on a separate RDS instance and are configured per-schema in config.yaml.

No demo / synthetic data path exists — if any required query returns
nothing, the script prints an explicit error and refuses to emit a PDF.

PDF engine: ReportLab with NotoSansSC font.
Brand colors: #0365C0 (primary), #1F4E79 (dark).
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

# Third-party deps — imported up front so missing packages fail before any
# database work is done. Install with:  pip install pymysql pyyaml reportlab
try:
    import yaml
    import pymysql
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, KeepTogether,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
except ImportError as exc:
    missing = exc.name or str(exc)
    sys.stderr.write(
        f"ERROR: required Python package not installed: {missing}\n"
        f"Install all dependencies with:\n"
        f"  pip install pymysql pyyaml reportlab\n"
    )
    sys.exit(2)

import time


def _log(msg: str) -> None:
    """Print a timestamped progress line to stdout (flushed immediately)."""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BRAND_BLUE = (3 / 255, 101 / 255, 192 / 255)       # #0365C0
BRAND_DARK = (31 / 255, 78 / 255, 121 / 255)        # #1F4E79
COLOR_RED = (0.85, 0.15, 0.15)
COLOR_YELLOW = (0.85, 0.65, 0.0)
COLOR_GREEN = (0.2, 0.65, 0.2)
COLOR_GRAY = (0.5, 0.5, 0.5)
BG_RED = (1, 0.92, 0.92)
BG_YELLOW = (1, 0.97, 0.88)
BG_GREEN = (0.92, 0.98, 0.92)
BG_BLUE = (0.92, 0.95, 1.0)

# 3P commission rates
COMMISSION_RATES = {
    8: 0.25,   # Grubhub
    9: 0.25,   # UberEats
    10: 0.25,  # DoorDash
}

CHANNEL_NAMES = {
    1: "POS 到店",
    2: "自有 App",
    3: "小程序",
    8: "Grubhub",
    9: "UberEats",
    10: "DoorDash",
}

CHANNEL_TYPES = {
    1: "1P", 2: "1P", 3: "1P",
    8: "3P", 9: "3P", 10: "3P",
}

SPEND_TIERS = [
    ("$0-3", 0, 3),
    ("$3-5", 3, 5),
    ("$5-8", 5, 8),
    ("$8-15", 8, 15),
    ("$15+", 15, 99999),
]

FREQUENCY_BUCKETS = [
    ("1 次", 1, 1, "一次性客户", "拉新→首单转复购"),
    ("2-3 次", 2, 3, "初期回头客", "复购券巩固习惯"),
    ("4-7 次", 4, 7, "稳定回头客", "会员体系核心"),
    ("8-14 次", 8, 14, "高频忠实客", "VIP 专属权益"),
    ("15+ 次", 15, 99999, "超级用户", "品牌大使候选"),
]

STORE_SCORE_WEIGHTS = {
    "revenue": 0.40,
    "completion": 0.30,
    "ticket": 0.20,
    "speed": 0.10,
}

# Insight rule thresholds
THRESHOLDS = {
    "satisfaction_red": 0.95,       # below this => RED
    "satisfaction_yellow": 0.96,    # below this => YELLOW
    "new_cust_decline_pct": -0.05,  # WoW decline => YELLOW
    "cancel_rate_red": 0.05,        # above 5% => RED
    "make_time_sla_min": 5.0,       # 5 min SLA
    "weekend_gap_yellow": 0.35,     # >35% gap => YELLOW
    "completion_rate_red": 0.93,    # below => RED
}

import re

# Populated by load_config() in main(). None until loaded so that
# accidental early use trips a clear AttributeError.
DB_CONFIGS: Optional[dict] = None
OUTPUT_DIR: Optional[str] = None
FONT_PATH: Optional[str] = None
ACTION_ITEMS_PATH: Optional[str] = None

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

_ENV_VAR_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)(?::-([^}]*))?\}")


def _expand_env(value):
    """Recursively expand ${VAR} / ${VAR:-default} tokens in strings."""
    if isinstance(value, str):
        def sub(m):
            name, default = m.group(1), m.group(2)
            val = os.environ.get(name)
            if val is not None:
                return val
            if default is not None:
                return default
            raise RuntimeError(
                f"Config references environment variable ${{{name}}} but it is not set."
            )
        return _ENV_VAR_RE.sub(sub, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_config(path: str) -> dict:
    """Read YAML config, expand ${ENV_VAR} tokens, populate module-level globals.

    Returns the fully resolved config dict. Raises with a clear message if
    required sections or schemas are missing.
    """
    global DB_CONFIGS, OUTPUT_DIR, FONT_PATH, ACTION_ITEMS_PATH

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            f"Copy {DEFAULT_CONFIG_PATH} and fill in your RDS hosts / credentials."
        )

    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}

    cfg = _expand_env(raw)

    db_section = cfg.get("database")
    if not db_section:
        raise ValueError(f"{path}: missing top-level 'database' section")

    defaults = db_section.get("defaults", {})
    required_schemas = ("luckyus_sales_order", "luckyus_iluckyhealth", "luckyus_opshop")
    resolved = {}
    for schema in required_schemas:
        entry = db_section.get(schema)
        if not entry:
            raise ValueError(
                f"{path}: missing database.{schema} section. "
                f"All three schemas must be configured."
            )
        for key in ("host", "user", "password"):
            if not entry.get(key):
                raise ValueError(
                    f"{path}: database.{schema}.{key} is empty. "
                    f"Set it directly or via ${{ENV_VAR}}."
                )
        resolved[schema] = {
            "host": entry["host"],
            "port": int(entry.get("port", 3306)),
            "user": entry["user"],
            "password": entry["password"],
            "charset": entry.get("charset", defaults.get("charset", "utf8mb4")),
            "connect_timeout": int(entry.get("connect_timeout",
                                             defaults.get("connect_timeout", 10))),
            "read_timeout": int(entry.get("read_timeout",
                                          defaults.get("read_timeout", 30))),
        }

    out_section = cfg.get("output", {})
    DB_CONFIGS = resolved
    OUTPUT_DIR = out_section.get("dir", "/app/reports")
    FONT_PATH = out_section.get("font_path",
                                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    ACTION_ITEMS_PATH = out_section.get("action_items", "action_items.yaml")

    return cfg


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def fmt_int(n: int | float | None) -> str:
    if n is None:
        return "N/A"
    return f"{int(n):,}"


def fmt_money(n: float | Decimal | None) -> str:
    if n is None:
        return "N/A"
    return f"${float(n):,.2f}"


def fmt_pct(n: float | None, decimals: int = 1) -> str:
    if n is None:
        return "N/A"
    return f"{n * 100:.{decimals}f}%"


def fmt_wow(current: float | None, previous: float | None, is_rate: bool = False) -> str:
    """Format WoW change.  is_rate=True uses pp difference."""
    if current is None or previous is None:
        return "N/A"
    if is_rate:
        diff = (current - previous) * 100
        sign = "+" if diff >= 0 else ""
        arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "—")
        return f"{arrow} {sign}{diff:.1f}pp"
    else:
        if previous == 0:
            return "N/A"
        change = (current - previous) / previous
        sign = "+" if change >= 0 else ""
        arrow = "↑" if change > 0 else ("↓" if change < 0 else "—")
        return f"{arrow} {sign}{change * 100:.1f}%"


def wow_arrow_symbol(current, previous, is_rate=False) -> str:
    """Return ▲/▼/— for KPI card display."""
    if current is None or previous is None:
        return "—"
    if is_rate:
        diff = current - previous
    else:
        diff = (current - previous) / previous if previous else 0
    if diff > 0:
        return "▲"
    elif diff < 0:
        return "▼"
    return "—"


def week_bounds(start_date: datetime) -> tuple[datetime, datetime]:
    """Return (Monday 00:00, Sunday 23:59:59) for the week containing start_date."""
    monday = start_date - timedelta(days=start_date.weekday())
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday


def safe_div(a, b, default=0.0):
    if b is None or b == 0:
        return default
    return a / b


# ---------------------------------------------------------------------------
# Database layer
# ---------------------------------------------------------------------------

class DatabaseClient:
    """Thin wrapper around pymysql for read-only queries.

    Accepts a per-schema config mapping {schema_name: pymysql_kwargs} so that
    different schemas can live on different RDS instances.
    """

    def __init__(self, configs: dict):
        self.configs = configs

    def _get_conn(self, database: str):
        if database not in self.configs:
            raise KeyError(
                f"No DB config registered for schema '{database}'. "
                f"Known schemas: {sorted(self.configs)}"
            )
        return pymysql.connect(
            **self.configs[database],
            database=database,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def query(self, database: str, sql: str, params: tuple = ()) -> list[dict]:
        conn = self._get_conn(database)
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Data collection — each function returns a dict of metrics
# ---------------------------------------------------------------------------

class DataCollector:
    """Collects all data for one report week from production databases."""

    # Database names (actual schema names on RDS)
    DB_ORDER = "luckyus_sales_order"
    DB_HEALTH = "luckyus_iluckyhealth"
    DB_SHOP = "luckyus_opshop"

    def __init__(self, db: DatabaseClient, week_start: datetime):
        self.db = db
        self.this_mon, self.this_sun = week_bounds(week_start)
        prev_start = self.this_mon - timedelta(days=7)
        self.prev_mon, self.prev_sun = week_bounds(prev_start)
        # t_order.create_time is stored in UTC; business lives in America/New_York.
        # Every time-filter, DATE(), HOUR(), DAYOFWEEK() uses CONVERT_TZ so
        # week boundaries align with the ET business day (Mon 00:00 – Sun 23:59 ET).

    # ---- helpers ----
    @staticmethod
    def _et(col: str) -> str:
        """Wrap a UTC timestamp column so downstream SQL sees America/New_York time."""
        return f"CONVERT_TZ({col}, 'UTC', 'America/New_York')"

    def _week_filter(self, col: str, which: str = "this") -> str:
        et_col = self._et(col)
        if which == "this":
            return f"{et_col} >= '{self.this_mon:%Y-%m-%d}' AND {et_col} < '{self.this_sun + timedelta(seconds=1):%Y-%m-%d}'"
        else:
            return f"{et_col} >= '{self.prev_mon:%Y-%m-%d}' AND {et_col} < '{self.prev_sun + timedelta(seconds=1):%Y-%m-%d}'"

    def _order_base(self, which: str = "this") -> str:
        """Base WHERE for t_order (exclude test / deleted)."""
        return f"status IN (0, 20, 90) AND {self._week_filter('create_time', which)}"

    # ================================================================
    # Chapter 1: Weekly Overview KPIs
    # ================================================================
    def collect_overview(self) -> dict:
        """9 KPI metrics + WoW."""
        result = {}
        for label, which in [("this", "this"), ("prev", "prev")]:
            wf = self._order_base(which)
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    COUNT(*)                                            AS total_orders,
                    SUM(CASE WHEN status IN (20,90) THEN 1 ELSE 0 END) AS completed_orders,
                    SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END)        AS cancelled_orders,
                    SUM(CASE WHEN status IN (20,90) THEN pay_money ELSE 0 END) AS total_revenue,
                    AVG(CASE WHEN status IN (20,90) THEN pay_money END) AS avg_ticket
                FROM t_order
                WHERE {wf}
            """)
            r = rows[0]
            total = r["total_orders"] or 0
            completed = r["completed_orders"] or 0
            cancelled = r["cancelled_orders"] or 0
            result[f"{label}_total_orders"] = completed  # report counts completed+dispatched
            result[f"{label}_total_revenue"] = float(r["total_revenue"] or 0)
            result[f"{label}_avg_ticket"] = float(r["avg_ticket"] or 0)
            result[f"{label}_completion_rate"] = safe_div(completed, total)
            result[f"{label}_cancel_rate"] = safe_div(cancelled, total)

        # Make time
        for label, which in [("this", "this"), ("prev", "prev")]:
            wf = self._week_filter("o.create_time", which)
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT AVG(TIMESTAMPDIFF(SECOND, m.accept_time, m.finish_time)) / 60.0 AS avg_make_min
                FROM t_order_make m
                JOIN t_order o ON o.id = m.order_id
                WHERE {wf}
                  AND m.accept_time IS NOT NULL AND m.finish_time IS NOT NULL
                  AND m.finish_time > m.accept_time
                  AND TIMESTAMPDIFF(SECOND, m.accept_time, m.finish_time) BETWEEN 10 AND 3600
            """)
            result[f"{label}_avg_make_min"] = float(rows[0]["avg_make_min"] or 0)

        # Satisfaction
        for label, which in [("this", "this"), ("prev", "prev")]:
            wf = self._week_filter("c.create_time", which)
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    COUNT(*) AS total_comments,
                    SUM(CASE WHEN c.level = 1 THEN 1 ELSE 0 END) AS positive
                FROM t_order_comment c
                WHERE {wf}
            """)
            total_c = rows[0]["total_comments"] or 0
            positive = rows[0]["positive"] or 0
            result[f"{label}_satisfaction"] = safe_div(positive, total_c)

        # New customers
        for label, which in [("this", "this"), ("prev", "prev")]:
            wf = self._week_filter("first_order_time", which)
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT COUNT(DISTINCT user_no) AS new_customers
                FROM (
                    SELECT user_no, MIN(create_time) AS first_order_time
                    FROM t_order
                    WHERE status IN (20, 90)
                    GROUP BY user_no
                ) sub
                WHERE {wf}
            """)
            result[f"{label}_new_customers"] = int(rows[0]["new_customers"] or 0)

        # Returning customer rate (30-day window)
        for label, which in [("this", "this"), ("prev", "prev")]:
            if which == "this":
                end_date = self.this_sun
            else:
                end_date = self.prev_sun
            start_30 = end_date - timedelta(days=30)
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    COUNT(DISTINCT user_no) AS total_users,
                    SUM(CASE WHEN order_cnt >= 2 THEN 1 ELSE 0 END) AS returning_users
                FROM (
                    SELECT user_no, COUNT(*) AS order_cnt
                    FROM t_order
                    WHERE status IN (20, 90)
                      AND {self._et('create_time')} >= '{start_30:%Y-%m-%d}'
                      AND {self._et('create_time')} < '{end_date + timedelta(seconds=1):%Y-%m-%d}'
                    GROUP BY user_no
                ) sub
            """)
            total_u = int(rows[0]["total_users"] or 0)
            returning = int(rows[0]["returning_users"] or 0)
            result[f"{label}_return_rate"] = safe_div(returning, total_u)
            if label == "this":
                result["this_total_users_30d"] = total_u
                result["this_returning_users_30d"] = returning

        # Active stores count
        rows = self.db.query(self.DB_ORDER, f"""
            SELECT COUNT(DISTINCT shop_id) AS active_stores
            FROM t_order
            WHERE status IN (20, 90)
              AND {self._week_filter('create_time', 'this')}
        """)
        result["active_stores"] = int(rows[0]["active_stores"] or 0)

        return result

    # ================================================================
    # Chapter 2: Revenue & Traffic
    # ================================================================
    def collect_revenue(self) -> dict:
        result = {}
        for label, which in [("this", "this"), ("prev", "prev")]:
            wf = self._week_filter("create_time", which)
            et_create = self._et("create_time")
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    DATE({et_create}) AS order_date,
                    DAYOFWEEK({et_create}) AS dow,
                    COUNT(*) AS orders,
                    SUM(pay_money) AS revenue,
                    AVG(pay_money) AS avg_ticket
                FROM t_order
                WHERE status IN (20, 90) AND {wf}
                GROUP BY DATE({et_create})
                ORDER BY order_date
            """)
            result[f"{label}_daily"] = [
                {
                    "date": str(r["order_date"]),
                    "dow": r["dow"],
                    "orders": int(r["orders"]),
                    "revenue": float(r["revenue"] or 0),
                    "avg_ticket": float(r["avg_ticket"] or 0),
                }
                for r in rows
            ]

        # Spend tiers
        for label, which in [("this", "this"), ("prev", "prev")]:
            wf = self._week_filter("create_time", which)
            case_parts = []
            for tier_name, lo, hi in SPEND_TIERS:
                if hi == 99999:
                    case_parts.append(f"WHEN pay_money >= {lo} THEN '{tier_name}'")
                else:
                    case_parts.append(f"WHEN pay_money >= {lo} AND pay_money < {hi} THEN '{tier_name}'")
            case_expr = "CASE " + " ".join(case_parts) + " END"
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    {case_expr} AS tier,
                    COUNT(*) AS orders,
                    SUM(pay_money) AS revenue,
                    AVG(pay_money) AS avg_price
                FROM t_order
                WHERE status IN (20, 90) AND {wf}
                GROUP BY tier
                ORDER BY FIELD(tier, '$0-3','$3-5','$5-8','$8-15','$15+')
            """)
            result[f"{label}_tiers"] = [
                {
                    "tier": r["tier"],
                    "orders": int(r["orders"]),
                    "revenue": float(r["revenue"] or 0),
                    "avg_price": float(r["avg_price"] or 0),
                }
                for r in rows
            ]

        # Discount penetration
        for label, which in [("this", "this"), ("prev", "prev")]:
            wf = self._week_filter("create_time", which)
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN total_money > pay_money THEN 1 ELSE 0 END) AS discounted,
                    AVG(CASE WHEN total_money > pay_money THEN total_money - pay_money END) AS avg_discount
                FROM t_order
                WHERE status IN (20, 90) AND {wf}
            """)
            r = rows[0]
            result[f"{label}_discount_rate"] = safe_div(r["discounted"], r["total"])
            result[f"{label}_avg_discount"] = float(r["avg_discount"] or 0)

        return result

    # ================================================================
    # Chapter 3: Store Rankings
    # ================================================================
    def collect_stores(self) -> dict:
        result = {}
        for label, which in [("this", "this"), ("prev", "prev")]:
            wf = self._week_filter("o.create_time", which)
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    o.shop_id,
                    o.shop_name,
                    COUNT(*) AS total_orders,
                    SUM(CASE WHEN o.status IN (20,90) THEN 1 ELSE 0 END) AS completed,
                    SUM(CASE WHEN o.status IN (20,90) THEN o.pay_money ELSE 0 END) AS revenue,
                    AVG(CASE WHEN o.status IN (20,90) THEN o.pay_money END) AS avg_ticket,
                    SUM(CASE WHEN o.status IN (20,90) THEN 1 ELSE 0 END) / COUNT(*) AS completion_rate
                FROM t_order o
                WHERE o.status IN (0, 20, 90) AND {wf}
                GROUP BY o.shop_id, o.shop_name
                ORDER BY revenue DESC
            """)
            stores = []
            for r in rows:
                stores.append({
                    "shop_id": r["shop_id"],
                    "shop_name": r["shop_name"] or f"Store#{r['shop_id']}",
                    "orders": int(r["completed"] or 0),
                    "revenue": float(r["revenue"] or 0),
                    "avg_ticket": float(r["avg_ticket"] or 0),
                    "completion_rate": float(r["completion_rate"] or 0),
                })
            result[f"{label}_stores"] = stores

        # Make time per store
        for label, which in [("this", "this"), ("prev", "prev")]:
            wf = self._week_filter("o.create_time", which)
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    o.shop_id,
                    AVG(TIMESTAMPDIFF(SECOND, m.accept_time, m.finish_time)) / 60.0 AS avg_make_min,
                    SUM(CASE WHEN TIMESTAMPDIFF(SECOND, m.accept_time, m.finish_time) <= 300 THEN 1 ELSE 0 END)
                        / COUNT(*) AS sla_5min_rate
                FROM t_order_make m
                JOIN t_order o ON o.id = m.order_id
                WHERE {wf}
                  AND m.accept_time IS NOT NULL AND m.finish_time IS NOT NULL
                  AND m.finish_time > m.accept_time
                  AND TIMESTAMPDIFF(SECOND, m.accept_time, m.finish_time) BETWEEN 10 AND 3600
                GROUP BY o.shop_id
            """)
            make_map = {}
            for r in rows:
                make_map[r["shop_id"]] = {
                    "avg_make_min": float(r["avg_make_min"] or 0),
                    "sla_5min_rate": float(r["sla_5min_rate"] or 0),
                }
            result[f"{label}_store_make"] = make_map

        # Satisfaction per store
        for label, which in [("this", "this"), ("prev", "prev")]:
            wf = self._week_filter("c.create_time", which)
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    o.shop_id,
                    COUNT(*) AS total_comments,
                    SUM(CASE WHEN c.level = 1 THEN 1 ELSE 0 END) AS positive
                FROM t_order_comment c
                JOIN t_order o ON o.id = c.order_id
                WHERE {wf}
                GROUP BY o.shop_id
            """)
            sat_map = {}
            for r in rows:
                sat_map[r["shop_id"]] = {
                    "satisfaction": safe_div(r["positive"], r["total_comments"]),
                    "comment_count": int(r["total_comments"] or 0),
                }
            result[f"{label}_store_satisfaction"] = sat_map

        return result

    # ================================================================
    # Chapter 4: Channel & Marketing
    # ================================================================
    def collect_channels(self) -> dict:
        result = {}
        for label, which in [("this", "this"), ("prev", "prev")]:
            wf = self._week_filter("create_time", which)
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    channel,
                    COUNT(*) AS orders,
                    SUM(pay_money) AS revenue,
                    AVG(pay_money) AS avg_ticket
                FROM t_order
                WHERE status IN (20, 90) AND {wf}
                GROUP BY channel
                ORDER BY orders DESC
            """)
            result[f"{label}_channels"] = [
                {
                    "channel": int(r["channel"]),
                    "orders": int(r["orders"]),
                    "revenue": float(r["revenue"] or 0),
                    "avg_ticket": float(r["avg_ticket"] or 0),
                }
                for r in rows
            ]

        # Frequency distribution (30-day, 1P only)
        for label, which in [("this", "this"), ("prev", "prev")]:
            if which == "this":
                end_date = self.this_sun
            else:
                end_date = self.prev_sun
            start_30 = end_date - timedelta(days=30)
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT order_cnt, COUNT(*) AS user_count
                FROM (
                    SELECT user_no, COUNT(*) AS order_cnt
                    FROM t_order
                    WHERE status IN (20, 90)
                      AND channel IN (1, 2, 3)
                      AND {self._et('create_time')} >= '{start_30:%Y-%m-%d}'
                      AND {self._et('create_time')} < '{end_date + timedelta(seconds=1):%Y-%m-%d}'
                    GROUP BY user_no
                ) sub
                GROUP BY order_cnt
                ORDER BY order_cnt
            """)
            # Bucket into frequency tiers
            freq_raw = {int(r["order_cnt"]): int(r["user_count"]) for r in rows}
            buckets = []
            for bname, lo, hi, ctype, tip in FREQUENCY_BUCKETS:
                count = sum(v for k, v in freq_raw.items() if lo <= k <= hi)
                buckets.append({"bucket": bname, "users": count, "type": ctype, "tip": tip})
            result[f"{label}_frequency"] = buckets

        # First-order top products (this week only)
        wf = self._week_filter("sub.first_order_time", "this")
        rows = self.db.query(self.DB_ORDER, f"""
            SELECT oi.spu_name, COUNT(*) AS cnt, SUM(oi.pay_money) AS revenue
            FROM t_order_item oi
            JOIN (
                SELECT user_no, MIN(create_time) AS first_order_time, MIN(id) AS first_order_id
                FROM t_order
                WHERE status IN (20, 90) AND channel IN (1,2,3)
                GROUP BY user_no
            ) sub ON oi.order_id = sub.first_order_id
            WHERE {wf}
            GROUP BY oi.spu_name
            ORDER BY cnt DESC
            LIMIT 5
        """)
        result["first_order_products"] = [
            {"name": r["spu_name"], "count": int(r["cnt"]), "revenue": float(r["revenue"] or 0)}
            for r in rows
        ]

        return result

    # ================================================================
    # Chapter 5: Product & Supply Chain
    # ================================================================
    def collect_products(self) -> dict:
        result = {}
        for label, which in [("this", "this"), ("prev", "prev")]:
            wf = self._week_filter("o.create_time", which)
            # Category breakdown
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    oi.one_category_name AS category,
                    COUNT(*) AS item_count,
                    COUNT(DISTINCT oi.spu_name) AS sku_count
                FROM t_order_item oi
                JOIN t_order o ON o.id = oi.order_id
                WHERE o.status IN (20, 90) AND {wf}
                GROUP BY oi.one_category_name
                ORDER BY item_count DESC
            """)
            result[f"{label}_categories"] = [
                {"category": r["category"] or "Other", "count": int(r["item_count"]), "skus": int(r["sku_count"])}
                for r in rows
            ]

            # Top 10 products
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    oi.spu_name,
                    oi.one_category_name AS category,
                    COUNT(*) AS sales,
                    SUM(oi.pay_money) AS revenue
                FROM t_order_item oi
                JOIN t_order o ON o.id = oi.order_id
                WHERE o.status IN (20, 90) AND {wf}
                GROUP BY oi.spu_name, oi.one_category_name
                ORDER BY sales DESC
                LIMIT 10
            """)
            result[f"{label}_top_products"] = [
                {
                    "name": r["spu_name"],
                    "category": r["category"] or "Other",
                    "sales": int(r["sales"]),
                    "revenue": float(r["revenue"] or 0),
                }
                for r in rows
            ]

            # Bottom 5 products
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    oi.spu_name,
                    oi.one_category_name AS category,
                    COUNT(*) AS sales,
                    SUM(oi.pay_money) AS revenue
                FROM t_order_item oi
                JOIN t_order o ON o.id = oi.order_id
                WHERE o.status IN (20, 90) AND {wf}
                GROUP BY oi.spu_name, oi.one_category_name
                ORDER BY sales ASC
                LIMIT 5
            """)
            result[f"{label}_bottom_products"] = [
                {
                    "name": r["spu_name"],
                    "category": r["category"] or "Other",
                    "sales": int(r["sales"]),
                    "revenue": float(r["revenue"] or 0),
                }
                for r in rows
            ]

        # Hourly distribution for top 5 products (this week)
        wf = self._week_filter("o.create_time", "this")
        top5_names = [p["name"] for p in result.get("this_top_products", [])[:5]]
        if top5_names:
            placeholders = ",".join(["%s"] * len(top5_names))
            et_create = self._et("o.create_time")
            rows = self.db.query(self.DB_ORDER, f"""
                SELECT
                    oi.spu_name,
                    HOUR({et_create}) AS hour,
                    COUNT(*) AS cnt
                FROM t_order_item oi
                JOIN t_order o ON o.id = oi.order_id
                WHERE o.status IN (20, 90) AND {wf}
                  AND oi.spu_name IN ({placeholders})
                GROUP BY oi.spu_name, HOUR({et_create})
                ORDER BY oi.spu_name, hour
            """, tuple(top5_names))
            hourly = defaultdict(dict)
            for r in rows:
                hourly[r["spu_name"]][int(r["hour"])] = int(r["cnt"])
            result["hourly_distribution"] = dict(hourly)

        return result

    # ================================================================
    # Collect all
    # ================================================================
    def collect_all(self) -> dict:
        """Run all collectors and merge into one data dict."""
        data = {}
        data["week_start"] = self.this_mon.strftime("%Y-%m-%d")
        data["week_end"] = self.this_sun.strftime("%Y-%m-%d")
        data["prev_week_start"] = self.prev_mon.strftime("%Y-%m-%d")
        data["prev_week_end"] = self.prev_sun.strftime("%Y-%m-%d")
        data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M EST")

        steps = [
            ("overview",  "Ch1 运营概览",  self.collect_overview),
            ("revenue",   "Ch2 营收与客流", self.collect_revenue),
            ("stores",    "Ch3 门店排名",  self.collect_stores),
            ("channels",  "Ch4 渠道与营销", self.collect_channels),
            ("products",  "Ch5 产品与供应链", self.collect_products),
        ]
        for i, (key, label, fn) in enumerate(steps, 1):
            _log(f"[{i}/{len(steps)}] Collecting {label}...")
            t0 = time.monotonic()
            data[key] = fn()
            _log(f"[{i}/{len(steps)}] {label} done in {time.monotonic() - t0:.1f}s")

        return data


# ---------------------------------------------------------------------------
# Insight engine — rule-based AI insights
# ---------------------------------------------------------------------------

class InsightEngine:
    """Generates prioritized insights from collected data."""

    def __init__(self, data: dict):
        self.data = data
        self.insights: list[dict] = []

    def run_all(self) -> list[dict]:
        self._check_satisfaction()
        self._check_new_customer_trend()
        self._check_channel_structure()
        self._check_return_rate()
        self._check_weekend_gap()
        self._check_completion_rate()
        self._check_cancel_rate()
        self._check_make_time()
        self._check_product_concentration()
        # Sort: RED > YELLOW > GREEN
        priority_order = {"RED": 0, "YELLOW": 1, "GREEN": 2}
        self.insights.sort(key=lambda x: priority_order.get(x["priority"], 3))
        return self.insights

    def _add(self, rule_id: str, priority: str, title: str, body: str,
             action: str, audiences: list[str]):
        self.insights.append({
            "rule_id": rule_id,
            "priority": priority,
            "title": title,
            "body": body,
            "action": action,
            "audiences": audiences,
        })

    def _check_satisfaction(self):
        """O-1: Store satisfaction below threshold."""
        stores = self.data.get("stores", {})
        sat_map = stores.get("this_store_satisfaction", {})
        store_list = stores.get("this_stores", [])
        store_names = {s["shop_id"]: s["shop_name"] for s in store_list}

        for shop_id, info in sat_map.items():
            sat = info["satisfaction"]
            name = store_names.get(shop_id, f"Store#{shop_id}")
            comments = info["comment_count"]
            if sat < THRESHOLDS["satisfaction_red"]:
                self._add("O-1", "RED" if sat < THRESHOLDS["satisfaction_red"] else "YELLOW",
                          f"{name} 满意度 {fmt_pct(sat)}",
                          f"{name} 满意度 {fmt_pct(sat)}（{comments} 条评价），低于 {fmt_pct(THRESHOLDS['satisfaction_red'])} 预警线。",
                          "建议运营部安排现场巡检，排查出品质量和服务流程。",
                          ["运营部"])
            elif sat < THRESHOLDS["satisfaction_yellow"]:
                self._add("O-1", "YELLOW",
                          f"{name} 满意度 {fmt_pct(sat)}",
                          f"{name} 满意度 {fmt_pct(sat)}（{comments} 条评价），接近 {fmt_pct(THRESHOLDS['satisfaction_red'])} 预警线。",
                          "建议关注服务速度。",
                          ["运营部"])

    def _check_new_customer_trend(self):
        """M-1: New customer acquisition declining."""
        ov = self.data.get("overview", {})
        this_new = ov.get("this_new_customers", 0)
        prev_new = ov.get("prev_new_customers", 0)
        if prev_new > 0:
            change = (this_new - prev_new) / prev_new
            if change < THRESHOLDS["new_cust_decline_pct"]:
                self._add("M-1", "YELLOW",
                          "新客获取下降",
                          f"新客获取数较上周下降 {abs(change) * 100:.1f}%。当前 30 天独立客户 "
                          f"{fmt_int(ov.get('this_total_users_30d', 0))} 人。",
                          "建议市场部评估拉新活动效果和预算分配。",
                          ["市场部"])

    def _check_channel_structure(self):
        """M-2: Channel structure stability."""
        channels = self.data.get("channels", {})
        this_ch = channels.get("this_channels", [])
        total_orders = sum(c["orders"] for c in this_ch)
        own_orders = sum(c["orders"] for c in this_ch if CHANNEL_TYPES.get(c["channel"]) == "1P")
        own_pct = safe_div(own_orders, total_orders)
        tp_channels = [c for c in this_ch if CHANNEL_TYPES.get(c["channel"]) == "3P"]
        tp_avg = safe_div(sum(c["revenue"] for c in tp_channels), sum(c["orders"] for c in tp_channels)) if tp_channels else 0
        own_avg = safe_div(sum(c["revenue"] for c in this_ch if CHANNEL_TYPES.get(c["channel"]) == "1P"),
                           own_orders) if own_orders else 0

        self._add("M-2", "GREEN",
                  "自有渠道结构稳定",
                  f"自有渠道（App + 小程序 + POS）占比 {fmt_pct(own_pct)}，结构稳定。"
                  f"3P 渠道客单价 {fmt_money(tp_avg)} 远高于自有 {fmt_money(own_avg)}。",
                  "可探索提升 App 客单价策略。",
                  ["市场部"])

    def _check_return_rate(self):
        """M-5: Return rate trend."""
        ov = self.data.get("overview", {})
        this_rr = ov.get("this_return_rate", 0)
        prev_rr = ov.get("prev_return_rate", 0)
        diff_pp = (this_rr - prev_rr) * 100
        total_users = ov.get("this_total_users_30d", 0)
        super_users = 0
        freq = self.data.get("channels", {}).get("this_frequency", [])
        for b in freq:
            if b["bucket"] in ("8-14 次", "15+ 次"):
                super_users += b["users"]
        super_pct = safe_div(super_users, total_users)

        priority = "GREEN" if diff_pp >= 0 else "YELLOW"
        self._add("M-5", priority,
                  f"回头客率 {fmt_pct(this_rr)}",
                  f"回头客率 {fmt_pct(this_rr)}，较上周{'提升' if diff_pp >= 0 else '下降'} {abs(diff_pp):.1f}pp。"
                  f"超级用户（8+次/月）占 {fmt_pct(super_pct)}（{fmt_int(super_users)} 人）。",
                  "建议持续推进会员积分体系建设。",
                  ["产品部"])

    def _check_weekend_gap(self):
        """O-5: Weekend vs weekday gap."""
        rev = self.data.get("revenue", {})
        daily = rev.get("this_daily", [])
        if not daily:
            return
        wd = [d for d in daily if d["dow"] <= 5]
        we = [d for d in daily if d["dow"] > 5]
        wd_avg = safe_div(sum(d["orders"] for d in wd), len(wd)) if wd else 0
        we_avg = safe_div(sum(d["orders"] for d in we), len(we)) if we else 0
        gap = safe_div(wd_avg - we_avg, wd_avg)

        if gap > THRESHOLDS["weekend_gap_yellow"]:
            self._add("O-5", "GREEN",
                      f"周末差距 {fmt_pct(gap)}",
                      f"周末日均订单约 {fmt_int(we_avg)} 单，为工作日 {fmt_int(wd_avg)} 单的 "
                      f"{fmt_pct(1 - gap)}，差距 {fmt_pct(gap)}。",
                      "可考虑周末专属促销或社区活动引流。",
                      ["运营部", "市场部"])

    def _check_completion_rate(self):
        """O-2: Low completion rate."""
        ov = self.data.get("overview", {})
        comp = ov.get("this_completion_rate", 1.0)
        if comp < THRESHOLDS["completion_rate_red"]:
            self._add("O-2", "RED",
                      f"完成率 {fmt_pct(comp)} 偏低",
                      f"本周完成率 {fmt_pct(comp)}，低于 {fmt_pct(THRESHOLDS['completion_rate_red'])} 预警线。",
                      "建议排查取消原因分布，关注缺货和超时取消。",
                      ["运营部"])

    def _check_cancel_rate(self):
        """O-3: High cancel rate."""
        ov = self.data.get("overview", {})
        cancel = ov.get("this_cancel_rate", 0)
        if cancel > THRESHOLDS["cancel_rate_red"]:
            self._add("O-3", "RED",
                      f"取消率 {fmt_pct(cancel)} 过高",
                      f"本周取消率 {fmt_pct(cancel)}，超过 {fmt_pct(THRESHOLDS['cancel_rate_red'])} 阈值。",
                      "建议分析取消原因，重点关注制作超时和用户主动取消。",
                      ["运营部"])

    def _check_make_time(self):
        """O-4: SLA breach on make time."""
        ov = self.data.get("overview", {})
        make = ov.get("this_avg_make_min", 0)
        if make > THRESHOLDS["make_time_sla_min"]:
            self._add("O-4", "RED",
                      f"制作时间 {make:.1f} min 超出 SLA",
                      f"全局平均制作时间 {make:.1f} 分钟，超出 {THRESHOLDS['make_time_sla_min']} 分钟 SLA。",
                      "建议排查高峰时段人力配置。",
                      ["运营部"])

    def _check_product_concentration(self):
        """P-1: Product concentration risk."""
        prods = self.data.get("products", {})
        top = prods.get("this_top_products", [])
        if len(top) >= 3:
            total_sales = sum(p["sales"] for p in top)
            top3_sales = sum(p["sales"] for p in top[:3])
            top3_pct = safe_div(top3_sales, total_sales)
            if top3_pct > 0.45:
                self._add("P-1", "GREEN",
                          f"Top 3 商品占比 {fmt_pct(top3_pct)}",
                          f"Top 3 商品合计占比 {fmt_pct(top3_pct)}，产品集中度较高。",
                          "建议关注季节性变化，适时推新品分散风险。",
                          ["供应链"])


# ---------------------------------------------------------------------------
# Store scoring
# ---------------------------------------------------------------------------

def compute_store_scores(data: dict) -> list[dict]:
    """Compute composite score per store and return sorted list."""
    stores = data.get("stores", {})
    this_stores = stores.get("this_stores", [])
    make_map = stores.get("this_store_make", {})
    sat_map = stores.get("this_store_satisfaction", {})
    prev_stores = {s["shop_id"]: s for s in stores.get("prev_stores", [])}
    prev_make = stores.get("prev_store_make", {})
    prev_sat = stores.get("prev_store_satisfaction", {})

    if not this_stores:
        return []

    # Normalize values for scoring
    revs = [s["revenue"] for s in this_stores]
    comps = [s["completion_rate"] for s in this_stores]
    tickets = [s["avg_ticket"] for s in this_stores]
    speeds = [make_map.get(s["shop_id"], {}).get("avg_make_min", 5) for s in this_stores]

    def norm(val, vals, invert=False):
        mn, mx = min(vals), max(vals)
        if mx == mn:
            return 50
        n = (val - mn) / (mx - mn)
        if invert:
            n = 1 - n
        return n * 100

    scored = []
    for s in this_stores:
        sid = s["shop_id"]
        mk = make_map.get(sid, {})
        st = sat_map.get(sid, {})
        speed = mk.get("avg_make_min", 5)

        score = (
            STORE_SCORE_WEIGHTS["revenue"] * norm(s["revenue"], revs) +
            STORE_SCORE_WEIGHTS["completion"] * norm(s["completion_rate"], comps) +
            STORE_SCORE_WEIGHTS["ticket"] * norm(s["avg_ticket"], tickets) +
            STORE_SCORE_WEIGHTS["speed"] * norm(speed, speeds, invert=True)
        )

        # Prev data
        ps = prev_stores.get(sid, {})
        pm = prev_make.get(sid, {})
        psat = prev_sat.get(sid, {})

        satisfaction = st.get("satisfaction", 0)
        comment_count = st.get("comment_count", 0)

        # Determine status
        if satisfaction < THRESHOLDS["satisfaction_red"]:
            status = "⚠ 关注"
        elif satisfaction >= 0.975 and s["completion_rate"] >= 0.97:
            status = "★ 优秀"
        else:
            status = "✓ 良好"

        scored.append({
            "rank": 0,
            "shop_id": sid,
            "shop_name": s["shop_name"],
            "orders": s["orders"],
            "revenue": s["revenue"],
            "avg_ticket": s["avg_ticket"],
            "completion_rate": s["completion_rate"],
            "avg_make_min": mk.get("avg_make_min", 0),
            "sla_5min_rate": mk.get("sla_5min_rate", 0),
            "satisfaction": satisfaction,
            "comment_count": comment_count,
            "score": round(score, 1),
            "status": status,
            # WoW
            "wow_orders": fmt_wow(s["orders"], ps.get("orders")),
            "wow_revenue": fmt_wow(s["revenue"], ps.get("revenue")),
            "wow_ticket": fmt_wow(s["avg_ticket"], ps.get("avg_ticket")),
            "wow_comp": fmt_wow(s["completion_rate"], ps.get("completion_rate"), is_rate=True),
            "wow_make": fmt_wow(mk.get("avg_make_min"), pm.get("avg_make_min")),
            "wow_sat": fmt_wow(satisfaction, psat.get("satisfaction"), is_rate=True),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    for i, s in enumerate(scored):
        s["rank"] = i + 1

    return scored


# ---------------------------------------------------------------------------
# Action items from insights + manual items
# ---------------------------------------------------------------------------

def generate_action_items(insights: list[dict], generated_date: datetime) -> list[dict]:
    """Generate Ch7 action items from RED/YELLOW insights."""
    items = []
    for ins in insights:
        if ins["priority"] not in ("RED", "YELLOW"):
            # GREEN insights also get follow-up items with longer deadlines
            deadline_days = 14
        elif ins["priority"] == "RED":
            deadline_days = 3
        else:
            deadline_days = 7

        deadline = generated_date + timedelta(days=deadline_days)
        priority_label = {"RED": "🔴 紧急", "YELLOW": "🟡 关注", "GREEN": "🟢 跟进"}[ins["priority"]]

        items.append({
            "priority": ins["priority"],
            "priority_label": priority_label,
            "description": f"{ins['body']} {ins['action']}".strip(),
            "department": " + ".join(ins["audiences"]),
            "deadline": deadline.strftime("%-m/%d"),
            "source": f"AI [{ins['rule_id']}]",
        })

    # Load manual action items if available
    if os.path.exists(ACTION_ITEMS_PATH):
        try:
            with open(ACTION_ITEMS_PATH, "r") as f:
                manual = yaml.safe_load(f)
            if manual and isinstance(manual, list):
                for item in manual:
                    items.append({
                        "priority": item.get("priority", "GREEN"),
                        "priority_label": {"RED": "🔴 紧急", "YELLOW": "🟡 关注", "GREEN": "🟢 跟进"}.get(
                            item.get("priority", "GREEN"), "🟢 跟进"),
                        "description": item.get("description", ""),
                        "department": item.get("department", ""),
                        "deadline": item.get("deadline", ""),
                        "source": "手动",
                    })
        except Exception:
            pass

    return items


# ---------------------------------------------------------------------------
# Text template rendering
# ---------------------------------------------------------------------------

class TextRenderer:
    """Render the Chinese text templates from the spec."""

    def __init__(self, data: dict, insights: list[dict]):
        self.data = data
        self.insights = insights
        self.ov = data.get("overview", {})
        self.rev = data.get("revenue", {})

    def ch1_summary(self) -> str:
        start = self.data["week_start"][5:]  # M/DD
        end = self.data["week_end"][5:]
        ov = self.ov
        wow_comp = fmt_wow(ov["this_completion_rate"], ov["prev_completion_rate"], is_rate=True)
        wow_new = fmt_wow(ov["this_new_customers"], ov["prev_new_customers"])

        top5 = self.insights[:5]
        insight_summary = ""
        for ins in top5:
            if ins["priority"] == "RED":
                insight_summary += ins["title"] + "。"
                break
        if not insight_summary and top5:
            insight_summary = top5[0]["title"] + "。"

        return (
            f"本周（{start}-{end}）{ov['active_stores']} 家门店共完成 {fmt_int(ov['this_total_orders'])} 单，"
            f"营收 {fmt_money(ov['this_total_revenue'])}，客单价 {fmt_money(ov['this_avg_ticket'])}。"
            f"完成率 {fmt_pct(ov['this_completion_rate'])}（{wow_comp}），"
            f"取消率 {fmt_pct(ov['this_cancel_rate'])}。"
            f"新增客户 {fmt_int(ov['this_new_customers'])} 人（{wow_new}），"
            f"回头客占比 {fmt_pct(ov['this_return_rate'])}。{insight_summary}"
        )

    def ch2_summary(self) -> str:
        daily = self.rev.get("this_daily", [])
        if not daily:
            return ""
        total_rev = sum(d["revenue"] for d in daily)
        daily_rev = total_rev / len(daily)
        wd = [d for d in daily if d["dow"] <= 5]
        we = [d for d in daily if d["dow"] > 5]
        wd_rev = sum(d["revenue"] for d in wd) / len(wd) if wd else 0
        we_rev = sum(d["revenue"] for d in we) / len(we) if we else 0
        gap = safe_div(wd_rev - we_rev, wd_rev) * 100

        disc_rate = self.rev.get("this_discount_rate", 0)
        disc_avg = self.rev.get("this_avg_discount", 0)

        tiers = self.rev.get("this_tiers", [])
        mid_tier = next((t for t in tiers if t["tier"] == "$3-5"), None)
        mid_pct = 0
        if mid_tier and daily:
            total_tier_orders = sum(t["orders"] for t in tiers)
            mid_pct = safe_div(mid_tier["orders"], total_tier_orders) * 100

        return (
            f"日均营收 {fmt_money(daily_rev)}（工作日 {fmt_money(wd_rev)}，周末 {fmt_money(we_rev)}，"
            f"差距 {gap:.1f}%）。{disc_rate * 100:.1f}% 订单使用折扣，平均折扣 {fmt_money(disc_avg)}。"
            f"$3-5 为主力消费层（{mid_pct:.0f}%），$15+ 主要来自 3P 平台。"
        )

    def ch4_summary(self) -> str:
        channels = self.data.get("channels", {})
        this_ch = channels.get("this_channels", [])
        total_orders = sum(c["orders"] for c in this_ch)
        own_orders = sum(c["orders"] for c in this_ch if CHANNEL_TYPES.get(c["channel"]) == "1P")
        own_rev = sum(c["revenue"] for c in this_ch if CHANNEL_TYPES.get(c["channel"]) == "1P")
        own_pct = safe_div(own_orders, total_orders) * 100
        tp_channels = [c for c in this_ch if CHANNEL_TYPES.get(c["channel"]) == "3P"]
        tp_pct = 100 - own_pct
        tp_rev = sum(c["revenue"] for c in tp_channels)
        tp_avg = safe_div(tp_rev, sum(c["orders"] for c in tp_channels))
        own_avg = safe_div(own_rev, own_orders)
        ratio = round(safe_div(tp_avg, own_avg), 1) if own_avg else 0
        comm = sum(c["revenue"] * COMMISSION_RATES.get(c["channel"], 0) for c in tp_channels)

        rr = self.ov.get("this_return_rate", 0)
        wow_rr = fmt_wow(self.ov.get("this_return_rate"), self.ov.get("prev_return_rate"), is_rate=True)

        freq = channels.get("this_frequency", [])
        one_time_pct = 0
        total_freq = sum(b["users"] for b in freq)
        if freq and total_freq:
            one_time = next((b for b in freq if b["bucket"] == "1 次"), None)
            if one_time:
                one_time_pct = safe_div(one_time["users"], total_freq) * 100

        return (
            f"自有渠道（App+小程序+POS）占 {own_pct:.1f}%，营收 {fmt_money(own_rev)}（无佣金）。"
            f"3P 渠道占 {tp_pct:.1f}%，客单价 {fmt_money(tp_avg)}（为自有的 {ratio}x），"
            f"估算佣金 {fmt_money(comm)}。复购率 {fmt_pct(rr)}（{wow_rr}），"
            f"{one_time_pct:.1f}% 客户仅消费 1 次 — 首单转复购是最大增长杠杆。"
        )

    def ch5_summary(self) -> str:
        prods = self.data.get("products", {})
        top = prods.get("this_top_products", [])
        cats = prods.get("this_categories", [])

        if not top:
            return ""

        total_sales = sum(p["sales"] for p in top)
        parts = []
        for i, p in enumerate(top[:3]):
            pct = safe_div(p["sales"], total_sales) * 100
            parts.append(f"{p['name']}（{fmt_int(p['sales'])} 杯，占 {pct:.1f}%）")
        top3_sales = sum(p["sales"] for p in top[:3])
        sum_pct = safe_div(top3_sales, total_sales) * 100

        food_cat = next((c for c in cats if "Food" in (c.get("category") or "")), None)
        food_pct = 0
        food_skus = 0
        if food_cat:
            total_cat = sum(c["count"] for c in cats)
            food_pct = safe_div(food_cat["count"], total_cat) * 100
            food_skus = food_cat["skus"]

        return (
            f"Top 3 热销：{'、'.join(parts)}。Top 3 合计占 {sum_pct:.1f}%。"
            f"食品类占 {food_pct:.1f}%（{food_skus} 个 SKU），有扩品空间。"
        )


# ---------------------------------------------------------------------------
# PDF report builder (ReportLab)
# ---------------------------------------------------------------------------

class PDFReportBuilder:
    """Build the weekly ops report PDF using ReportLab."""

    def __init__(self, data: dict, insights: list[dict], store_scores: list[dict],
                 action_items: list[dict], text: TextRenderer):
        self.data = data
        self.insights = insights
        self.stores = store_scores
        self.actions = action_items
        self.text = text

    def build(self, output_path: str):
        # Register Chinese font
        font_registered = False
        font_name = "NotoSansSC"
        font_paths = [
            FONT_PATH,
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/System/Library/Fonts/PingFang.ttc",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, fp))
                    font_registered = True
                    break
                except Exception:
                    continue

        if not font_registered:
            try:
                pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
                font_name = "STSong-Light"
                font_registered = True
            except Exception:
                font_name = "Helvetica"
                print("WARNING: No CJK font found. Chinese characters may not render correctly.")
                print("Install NotoSansCJK or update output.font_path in config.yaml.")

        # Colors
        brand = colors.HexColor("#0365C0")
        dark = colors.HexColor("#1F4E79")
        red = colors.HexColor("#D32F2F")
        yellow = colors.HexColor("#F9A825")
        green = colors.HexColor("#388E3C")
        light_red = colors.HexColor("#FFEBEE")
        light_yellow = colors.HexColor("#FFF8E1")
        light_green = colors.HexColor("#E8F5E9")
        light_blue = colors.HexColor("#E3F2FD")
        bg_header = colors.HexColor("#0365C0")
        bg_alt_row = colors.HexColor("#F5F5F5")

        # Styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            "Title_CN", fontName=font_name, fontSize=22, textColor=dark,
            alignment=TA_CENTER, spaceAfter=4 * mm, leading=28,
        ))
        styles.add(ParagraphStyle(
            "Subtitle_CN", fontName=font_name, fontSize=11, textColor=colors.gray,
            alignment=TA_CENTER, spaceAfter=6 * mm,
        ))
        styles.add(ParagraphStyle(
            "Heading_CN", fontName=font_name, fontSize=14, textColor=brand,
            spaceBefore=6 * mm, spaceAfter=3 * mm, leading=18,
        ))
        styles.add(ParagraphStyle(
            "Body_CN", fontName=font_name, fontSize=9, textColor=colors.black,
            spaceAfter=2 * mm, leading=14,
        ))
        styles.add(ParagraphStyle(
            "Small_CN", fontName=font_name, fontSize=8, textColor=colors.gray,
            spaceAfter=1 * mm, leading=11,
        ))
        styles.add(ParagraphStyle(
            "KPI_Value", fontName=font_name, fontSize=16, textColor=dark,
            alignment=TA_CENTER, leading=20,
        ))
        styles.add(ParagraphStyle(
            "KPI_Label", fontName=font_name, fontSize=8, textColor=colors.gray,
            alignment=TA_CENTER, leading=11,
        ))
        styles.add(ParagraphStyle(
            "KPI_WoW", fontName=font_name, fontSize=8, alignment=TA_CENTER, leading=11,
        ))
        styles.add(ParagraphStyle(
            "TableHeader", fontName=font_name, fontSize=8, textColor=colors.white,
            alignment=TA_CENTER, leading=11,
        ))
        styles.add(ParagraphStyle(
            "TableCell", fontName=font_name, fontSize=8, textColor=colors.black,
            alignment=TA_CENTER, leading=11,
        ))
        styles.add(ParagraphStyle(
            "TableCellLeft", fontName=font_name, fontSize=8, textColor=colors.black,
            alignment=TA_LEFT, leading=11,
        ))
        styles.add(ParagraphStyle(
            "Insight_Body", fontName=font_name, fontSize=9, textColor=colors.black,
            leading=13,
        ))

        # Build document
        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            leftMargin=15 * mm, rightMargin=15 * mm,
            topMargin=15 * mm, bottomMargin=15 * mm,
        )
        story = []
        ov = self.data["overview"]

        # ---- Cover / Title ----
        story.append(Spacer(1, 10 * mm))
        story.append(Paragraph("瑞幸咖啡北美", styles["Title_CN"]))
        story.append(Paragraph("周运营报告  Weekly Operations Report", styles["Title_CN"]))
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(
            f"报告周期：{self.data['week_start']} 至 {self.data['week_end']}<br/>"
            f"{ov['active_stores']} 家活跃门店  |  {fmt_int(ov['this_total_orders'])} 笔订单  |  "
            f"{fmt_money(ov['this_total_revenue'])} 营收",
            styles["Subtitle_CN"]
        ))
        story.append(Paragraph(
            f"生成时间：{self.data['generated_at']}  |  AI 自动生成<br/>"
            "First Ray Holdings USA Inc.  |  内部机密",
            styles["Small_CN"]
        ))
        story.append(Spacer(1, 6 * mm))
        story.append(HRFlowable(width="100%", thickness=1, color=brand))
        story.append(Spacer(1, 4 * mm))

        # ---- Chapter 1: Overview ----
        story.append(Paragraph("一、本周运营概览", styles["Heading_CN"]))

        # KPI Cards (3 rows × 3 columns)
        def kpi_cell(label, value, wow_str):
            return [
                Paragraph(label, styles["KPI_Label"]),
                Paragraph(str(value), styles["KPI_Value"]),
                Paragraph(wow_str, styles["KPI_WoW"]),
            ]

        kpi_data = [
            [
                kpi_cell("总订单量", fmt_int(ov["this_total_orders"]),
                         fmt_wow(ov["this_total_orders"], ov["prev_total_orders"])),
                kpi_cell("总营收", fmt_money(ov["this_total_revenue"]),
                         fmt_wow(ov["this_total_revenue"], ov["prev_total_revenue"])),
                kpi_cell("客单价", fmt_money(ov["this_avg_ticket"]),
                         fmt_wow(ov["this_avg_ticket"], ov["prev_avg_ticket"])),
            ],
            [
                kpi_cell("完成率", fmt_pct(ov["this_completion_rate"]),
                         fmt_wow(ov["this_completion_rate"], ov["prev_completion_rate"], is_rate=True)),
                kpi_cell("取消率", fmt_pct(ov["this_cancel_rate"]),
                         fmt_wow(ov["this_cancel_rate"], ov["prev_cancel_rate"], is_rate=True)),
                kpi_cell("制作时间", f"{ov['this_avg_make_min']:.1f} min",
                         fmt_wow(ov["this_avg_make_min"], ov["prev_avg_make_min"])),
            ],
            [
                kpi_cell("满意度", fmt_pct(ov["this_satisfaction"]),
                         fmt_wow(ov["this_satisfaction"], ov["prev_satisfaction"], is_rate=True)),
                kpi_cell("新客数", fmt_int(ov["this_new_customers"]),
                         fmt_wow(ov["this_new_customers"], ov["prev_new_customers"])),
                kpi_cell("回头客率", fmt_pct(ov["this_return_rate"]),
                         fmt_wow(ov["this_return_rate"], ov["prev_return_rate"], is_rate=True)),
            ],
        ]

        # Flatten KPI cards into table
        col_w = 57 * mm
        for row in kpi_data:
            table_data = []
            for cell_group in row:
                # Each cell_group is [label, value, wow]
                pass
            # Build as a 3-column table where each cell is a mini-table
            cells = []
            for cg in row:
                mini = Table([[cg[0]], [cg[1]], [cg[2]]], colWidths=[col_w])
                mini.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("BACKGROUND", (0, 0), (-1, -1), light_blue),
                    ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ]))
                cells.append(mini)
            row_table = Table([cells], colWidths=[col_w + 2 * mm] * 3)
            row_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(row_table)
            story.append(Spacer(1, 1 * mm))

        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(self.text.ch1_summary(), styles["Body_CN"]))

        # Top 5 insights
        story.append(Paragraph("<b>本周关键洞察</b>", styles["Body_CN"]))
        for ins in self.insights[:5]:
            emoji = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}[ins["priority"]]
            bg = {"RED": light_red, "YELLOW": light_yellow, "GREEN": light_green}[ins["priority"]]
            border_color = {"RED": red, "YELLOW": yellow, "GREEN": green}[ins["priority"]]
            insight_text = f"{emoji} {ins['body']} [{ins['rule_id']}]"
            t = Table(
                [[Paragraph(insight_text, styles["Insight_Body"])]],
                colWidths=[170 * mm],
            )
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ("LINEBEFOREADD", (0, 0), (0, -1), 3, border_color),
            ]))
            story.append(t)
            story.append(Spacer(1, 1 * mm))

        story.append(PageBreak())

        # ---- Chapter 2: Revenue ----
        story.append(Paragraph("二、营收与客流分析", styles["Heading_CN"]))
        story.append(Paragraph("<b>周度趋势</b>", styles["Body_CN"]))

        # Daily table
        daily = self.data["revenue"].get("this_daily", [])
        if daily:
            header = [
                Paragraph("日期", styles["TableHeader"]),
                Paragraph("订单", styles["TableHeader"]),
                Paragraph("营收", styles["TableHeader"]),
                Paragraph("客单价", styles["TableHeader"]),
            ]
            rows_data = [header]
            for d in daily:
                rows_data.append([
                    Paragraph(d["date"], styles["TableCell"]),
                    Paragraph(fmt_int(d["orders"]), styles["TableCell"]),
                    Paragraph(fmt_money(d["revenue"]), styles["TableCell"]),
                    Paragraph(fmt_money(d["avg_ticket"]), styles["TableCell"]),
                ])
            t = Table(rows_data, colWidths=[42 * mm, 30 * mm, 35 * mm, 30 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), bg_header),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_alt_row]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ]))
            story.append(t)
            story.append(Spacer(1, 3 * mm))

        # Spend tiers
        story.append(Paragraph("<b>消费分层</b>", styles["Body_CN"]))
        tiers = self.data["revenue"].get("this_tiers", [])
        if tiers:
            total_tier_orders = sum(t["orders"] for t in tiers)
            total_tier_rev = sum(t["revenue"] for t in tiers)
            header = [
                Paragraph("层级", styles["TableHeader"]),
                Paragraph("订单数", styles["TableHeader"]),
                Paragraph("营收", styles["TableHeader"]),
                Paragraph("层内均价", styles["TableHeader"]),
                Paragraph("订单占比", styles["TableHeader"]),
                Paragraph("营收占比", styles["TableHeader"]),
            ]
            rows_data = [header]
            for t_item in tiers:
                o_pct = safe_div(t_item["orders"], total_tier_orders)
                r_pct = safe_div(t_item["revenue"], total_tier_rev)
                rows_data.append([
                    Paragraph(t_item["tier"], styles["TableCellLeft"]),
                    Paragraph(fmt_int(t_item["orders"]), styles["TableCell"]),
                    Paragraph(fmt_money(t_item["revenue"]), styles["TableCell"]),
                    Paragraph(fmt_money(t_item["avg_price"]), styles["TableCell"]),
                    Paragraph(fmt_pct(o_pct), styles["TableCell"]),
                    Paragraph(fmt_pct(r_pct), styles["TableCell"]),
                ])
            t = Table(rows_data, colWidths=[22 * mm, 25 * mm, 28 * mm, 25 * mm, 25 * mm, 25 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), bg_header),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_alt_row]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ]))
            story.append(t)

        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(self.text.ch2_summary(), styles["Body_CN"]))
        story.append(PageBreak())

        # ---- Chapter 3: Store Rankings ----
        story.append(Paragraph("三、门店运营排名", styles["Heading_CN"]))
        story.append(Paragraph(
            "综合评分 = 营收贡献(40%) + 完成率(30%) + 客单价(20%) + 制作效率(10%)",
            styles["Small_CN"]
        ))

        if self.stores:
            header = [
                Paragraph("#", styles["TableHeader"]),
                Paragraph("门店", styles["TableHeader"]),
                Paragraph("订单", styles["TableHeader"]),
                Paragraph("营收", styles["TableHeader"]),
                Paragraph("客单", styles["TableHeader"]),
                Paragraph("完成率", styles["TableHeader"]),
                Paragraph("制作", styles["TableHeader"]),
                Paragraph("满意度", styles["TableHeader"]),
                Paragraph("评分", styles["TableHeader"]),
                Paragraph("状态", styles["TableHeader"]),
            ]
            rows_data = [header]
            for s in self.stores:
                rows_data.append([
                    Paragraph(str(s["rank"]), styles["TableCell"]),
                    Paragraph(s["shop_name"], styles["TableCellLeft"]),
                    Paragraph(fmt_int(s["orders"]), styles["TableCell"]),
                    Paragraph(fmt_money(s["revenue"]), styles["TableCell"]),
                    Paragraph(fmt_money(s["avg_ticket"]), styles["TableCell"]),
                    Paragraph(fmt_pct(s["completion_rate"]), styles["TableCell"]),
                    Paragraph(f"{s['avg_make_min']:.1f}m", styles["TableCell"]),
                    Paragraph(fmt_pct(s["satisfaction"]), styles["TableCell"]),
                    Paragraph(str(s["score"]), styles["TableCell"]),
                    Paragraph(s["status"], styles["TableCellLeft"]),
                ])
            t = Table(rows_data, colWidths=[
                8 * mm, 32 * mm, 18 * mm, 22 * mm, 16 * mm, 18 * mm, 14 * mm, 18 * mm, 14 * mm, 18 * mm,
            ])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), bg_header),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_alt_row]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), "LEFT"),
                ("ALIGN", (9, 1), (9, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
            ]))
            story.append(t)
            story.append(Spacer(1, 3 * mm))

            # Top 3 / attention text
            top3 = self.stores[:3]
            story.append(Paragraph(
                f"Top 3：{top3[0]['shop_name']}（{top3[0]['score']} 分）、"
                f"{top3[1]['shop_name']}（{top3[1]['score']} 分）、"
                f"{top3[2]['shop_name']}（{top3[2]['score']} 分）。",
                styles["Body_CN"]
            ))
            attention = [s for s in self.stores if "关注" in s["status"]]
            for a in attention:
                story.append(Paragraph(
                    f"需关注：{a['shop_name']} 满意度 {fmt_pct(a['satisfaction'])}（{a['comment_count']} 条评价）。",
                    styles["Body_CN"]
                ))

        story.append(PageBreak())

        # ---- Chapter 4: Channels ----
        story.append(Paragraph("四、渠道与营销分析", styles["Heading_CN"]))
        story.append(Paragraph("<b>渠道表现</b>", styles["Body_CN"]))

        this_ch = self.data.get("channels", {}).get("this_channels", [])
        if this_ch:
            total_orders = sum(c["orders"] for c in this_ch)
            header = [
                Paragraph("渠道", styles["TableHeader"]),
                Paragraph("订单", styles["TableHeader"]),
                Paragraph("营收", styles["TableHeader"]),
                Paragraph("客单价", styles["TableHeader"]),
                Paragraph("占比", styles["TableHeader"]),
                Paragraph("佣金率", styles["TableHeader"]),
                Paragraph("净营收", styles["TableHeader"]),
                Paragraph("类型", styles["TableHeader"]),
            ]
            rows_data = [header]
            for c in this_ch:
                ch_id = c["channel"]
                comm_rate = COMMISSION_RATES.get(ch_id, 0)
                comm = c["revenue"] * comm_rate
                net = c["revenue"] - comm
                pct = safe_div(c["orders"], total_orders)
                rows_data.append([
                    Paragraph(CHANNEL_NAMES.get(ch_id, f"Ch{ch_id}"), styles["TableCellLeft"]),
                    Paragraph(fmt_int(c["orders"]), styles["TableCell"]),
                    Paragraph(fmt_money(c["revenue"]), styles["TableCell"]),
                    Paragraph(fmt_money(c["avg_ticket"]), styles["TableCell"]),
                    Paragraph(fmt_pct(pct), styles["TableCell"]),
                    Paragraph(f"{comm_rate * 100:.0f}%" if comm_rate else "0%", styles["TableCell"]),
                    Paragraph(fmt_money(net), styles["TableCell"]),
                    Paragraph(CHANNEL_TYPES.get(ch_id, "?"), styles["TableCell"]),
                ])
            t = Table(rows_data, colWidths=[
                26 * mm, 20 * mm, 24 * mm, 20 * mm, 16 * mm, 18 * mm, 24 * mm, 14 * mm,
            ])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), bg_header),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_alt_row]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 1), (0, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ]))
            story.append(t)
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(
                "注：3P 渠道通过统一系统账户下单，无法区分新客/回头客。以下客户分析仅含 1P 渠道。",
                styles["Small_CN"]
            ))

        # Frequency table
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("<b>客户复购（30 天窗口 · 仅 1P 渠道）</b>", styles["Body_CN"]))
        freq = self.data.get("channels", {}).get("this_frequency", [])
        if freq:
            total_freq = sum(b["users"] for b in freq)
            header = [
                Paragraph("频次", styles["TableHeader"]),
                Paragraph("客户数", styles["TableHeader"]),
                Paragraph("占比", styles["TableHeader"]),
                Paragraph("客户类型", styles["TableHeader"]),
                Paragraph("营销建议", styles["TableHeader"]),
            ]
            rows_data = [header]
            for b in freq:
                pct = safe_div(b["users"], total_freq)
                rows_data.append([
                    Paragraph(b["bucket"], styles["TableCellLeft"]),
                    Paragraph(fmt_int(b["users"]), styles["TableCell"]),
                    Paragraph(fmt_pct(pct), styles["TableCell"]),
                    Paragraph(b["type"], styles["TableCellLeft"]),
                    Paragraph(b["tip"], styles["TableCellLeft"]),
                ])
            t = Table(rows_data, colWidths=[18 * mm, 22 * mm, 16 * mm, 30 * mm, 50 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), bg_header),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_alt_row]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 1), (0, -1), "LEFT"),
                ("ALIGN", (3, 1), (4, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ]))
            story.append(t)

        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(self.text.ch4_summary(), styles["Body_CN"]))
        story.append(PageBreak())

        # ---- Chapter 5: Products ----
        story.append(Paragraph("五、产品与供应链", styles["Heading_CN"]))

        # Category table
        story.append(Paragraph("<b>品类结构</b>", styles["Body_CN"]))
        cats = self.data.get("products", {}).get("this_categories", [])
        if cats:
            total_cat = sum(c["count"] for c in cats)
            header = [
                Paragraph("品类", styles["TableHeader"]),
                Paragraph("商品数/周", styles["TableHeader"]),
                Paragraph("活跃 SKU", styles["TableHeader"]),
                Paragraph("占比", styles["TableHeader"]),
            ]
            rows_data = [header]
            for c in cats:
                rows_data.append([
                    Paragraph(c["category"], styles["TableCellLeft"]),
                    Paragraph(fmt_int(c["count"]), styles["TableCell"]),
                    Paragraph(str(c["skus"]), styles["TableCell"]),
                    Paragraph(fmt_pct(safe_div(c["count"], total_cat)), styles["TableCell"]),
                ])
            t = Table(rows_data, colWidths=[35 * mm, 30 * mm, 25 * mm, 25 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), bg_header),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_alt_row]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 1), (0, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ]))
            story.append(t)

        # Top 10 products
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("<b>热销 Top 10</b>", styles["Body_CN"]))
        top_prods = self.data.get("products", {}).get("this_top_products", [])
        prev_top = self.data.get("products", {}).get("prev_top_products", [])
        prev_names = [p["name"] for p in prev_top]
        if top_prods:
            total_sales = sum(p["sales"] for p in top_prods)
            header = [
                Paragraph("#", styles["TableHeader"]),
                Paragraph("商品", styles["TableHeader"]),
                Paragraph("销量", styles["TableHeader"]),
                Paragraph("营收", styles["TableHeader"]),
                Paragraph("占比", styles["TableHeader"]),
                Paragraph("品类", styles["TableHeader"]),
            ]
            rows_data = [header]
            for i, p in enumerate(top_prods):
                pct = safe_div(p["sales"], total_sales)
                name = p["name"]
                if name not in prev_names:
                    name += " [NEW]"
                rows_data.append([
                    Paragraph(str(i + 1), styles["TableCell"]),
                    Paragraph(name, styles["TableCellLeft"]),
                    Paragraph(fmt_int(p["sales"]), styles["TableCell"]),
                    Paragraph(fmt_money(p["revenue"]), styles["TableCell"]),
                    Paragraph(fmt_pct(pct), styles["TableCell"]),
                    Paragraph(p["category"], styles["TableCell"]),
                ])
            t = Table(rows_data, colWidths=[8 * mm, 50 * mm, 22 * mm, 25 * mm, 18 * mm, 25 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), bg_header),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_alt_row]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ]))
            story.append(t)

        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(self.text.ch5_summary(), styles["Body_CN"]))
        story.append(PageBreak())

        # ---- Chapter 6: Insights ----
        story.append(Paragraph("六、本周洞察与预警", styles["Heading_CN"]))

        red_insights = [i for i in self.insights if i["priority"] == "RED"]
        yellow_insights = [i for i in self.insights if i["priority"] == "YELLOW"]
        green_insights = [i for i in self.insights if i["priority"] == "GREEN"]

        def render_insight_group(label, ins_list, bg_color, border_clr, emoji):
            story.append(Paragraph(f"<b>{label}（{len(ins_list)} 条）</b>", styles["Body_CN"]))
            if not ins_list:
                story.append(Paragraph(f"本周无{label}项。", styles["Small_CN"]))
            else:
                for ins in ins_list:
                    text = f"{emoji} [{ins['rule_id']}] {ins['body']} {ins['action']}"
                    t = Table(
                        [[Paragraph(text, styles["Insight_Body"])]],
                        colWidths=[170 * mm],
                    )
                    t.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 1 * mm))
            story.append(Spacer(1, 2 * mm))

        render_insight_group("紧急", red_insights, light_red, red, "🔴")
        render_insight_group("关注", yellow_insights, light_yellow, yellow, "🟡")
        render_insight_group("跟进", green_insights, light_green, green, "🟢")

        if not red_insights and not yellow_insights:
            t = Table(
                [[Paragraph("本周各项运营指标均在健康范围内", styles["Body_CN"])]],
                colWidths=[170 * mm],
            )
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), light_blue),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]))
            story.append(t)

        # ---- Chapter 7: Action Items ----
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("七、下周关注重点", styles["Heading_CN"]))

        if self.actions:
            header = [
                Paragraph("优先级", styles["TableHeader"]),
                Paragraph("事项", styles["TableHeader"]),
                Paragraph("责任部门", styles["TableHeader"]),
                Paragraph("截止", styles["TableHeader"]),
                Paragraph("来源", styles["TableHeader"]),
            ]
            rows_data = [header]
            for a in self.actions:
                # Truncate long descriptions
                desc = a["description"]
                if len(desc) > 80:
                    desc = desc[:77] + "..."
                rows_data.append([
                    Paragraph(a["priority_label"], styles["TableCellLeft"]),
                    Paragraph(desc, styles["TableCellLeft"]),
                    Paragraph(a["department"], styles["TableCell"]),
                    Paragraph(a["deadline"], styles["TableCell"]),
                    Paragraph(a["source"], styles["TableCell"]),
                ])
            t = Table(rows_data, colWidths=[20 * mm, 72 * mm, 28 * mm, 18 * mm, 24 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), bg_header),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_alt_row]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 1), (1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ]))
            story.append(t)

        # Footer
        story.append(Spacer(1, 8 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        story.append(Paragraph(
            f"本报告由 AI 自动生成。数据来源：luckyus_sales_order + luckyus_opshop"
            f"（截至 {self.data['week_end']} 00:00 UTC）。如有疑问请联系 DBA 团队。",
            styles["Small_CN"]
        ))
        story.append(Paragraph("— 报告结束 —", styles["Small_CN"]))

        # Build PDF
        doc.build(story)
        print(f"PDF generated: {output_path}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def _check_data_completeness(data: dict) -> list[str]:
    """Return a list of human-readable problems detected in the collected data.

    Checks that each required section exists and contains real numbers.
    Empty DBs or failed queries surface here so a blank PDF is never emitted.
    """
    problems: list[str] = []
    required_sections = ("overview", "revenue", "stores", "channels", "products")
    for name in required_sections:
        section = data.get(name)
        if section is None:
            problems.append(f"section '{name}' is missing (collector returned None)")
            continue
        if isinstance(section, dict) and not section:
            problems.append(f"section '{name}' is empty")

    ov = data.get("overview") or {}
    if not ov.get("this_total_orders"):
        problems.append(
            "overview.this_total_orders is 0 — no completed orders found for the "
            "target week. Verify week range, t_order.status filter, and that the "
            "salesorder RDS is reachable."
        )
    if not ov.get("this_total_revenue"):
        problems.append("overview.this_total_revenue is 0 — no revenue for the week.")

    stores = data.get("stores") or {}
    if not stores.get("this_stores"):
        problems.append(
            "stores.this_stores is empty — no per-store rows returned for the "
            "target week. Verify salesorder RDS reachability, t_order.shop_id/"
            "shop_name populated, and the WHERE status IN (0,20,90) filter."
        )

    return problems


def main():
    parser = argparse.ArgumentParser(description="Luckin Coffee NA Weekly Operations Report Generator")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_PATH,
                        help=f"Path to YAML config file. Default: {DEFAULT_CONFIG_PATH}")
    parser.add_argument("--week-start", type=str, default=None,
                        help="Monday of the report week (YYYY-MM-DD). Default: most recent completed Monday.")
    parser.add_argument("--output", type=str, default=None,
                        help="Output PDF path. Default: <output.dir>/weekly-report-YYYY-WNN.pdf")
    parser.add_argument("--dry-run", action="store_true",
                        help="Collect data and print summary, skip PDF generation.")
    parser.add_argument("--json-out", type=str, default=None,
                        help="Also dump raw data to a JSON file.")
    args = parser.parse_args()

    t_start = time.monotonic()

    # Load YAML config (populates DB_CONFIGS, OUTPUT_DIR, FONT_PATH, ACTION_ITEMS_PATH).
    _log(f"Loading config: {args.config}")
    try:
        load_config(args.config)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    # Determine week
    if args.week_start:
        week_start = datetime.strptime(args.week_start, "%Y-%m-%d")
    else:
        today = datetime.now()
        # Most recent completed week (last Monday)
        days_since_monday = today.weekday()
        if days_since_monday == 0 and today.hour < 9:
            # Monday before 9 AM — report on 2 weeks ago
            week_start = today - timedelta(days=7)
        else:
            week_start = today - timedelta(days=days_since_monday + 7)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    mon, sun = week_bounds(week_start)
    iso_year, iso_week, _ = mon.isocalendar()
    _log(f"Report week: {mon:%Y-%m-%d} (Mon) to {sun:%Y-%m-%d} (Sun) — W{iso_week:02d}")

    # Collect data — always from real databases.
    _log(f"Connecting to {len(DB_CONFIGS)} database schemas: {', '.join(sorted(DB_CONFIGS))}")
    db = DatabaseClient(DB_CONFIGS)
    collector = DataCollector(db, week_start)
    t_collect = time.monotonic()
    try:
        data = collector.collect_all()
    except Exception as e:
        print(f"ERROR: data collection failed: {type(e).__name__}: {e}",
              file=sys.stderr)
        sys.exit(3)
    _log(f"Data collection finished in {time.monotonic() - t_collect:.1f}s")

    problems = _check_data_completeness(data)
    if problems:
        print("\nERROR: required data is missing or empty:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            "\nRefusing to emit a PDF. Fix the data source and rerun.\n"
            "(Use --dry-run --json-out <file> to inspect the partial data.)",
            file=sys.stderr,
        )
        if not args.dry_run:
            sys.exit(4)

    # Run insight engine
    _log("Running insight rules...")
    engine = InsightEngine(data)
    insights = engine.run_all()
    _log(f"Generated {len(insights)} insights: "
         f"{sum(1 for i in insights if i['priority'] == 'RED')} RED, "
         f"{sum(1 for i in insights if i['priority'] == 'YELLOW')} YELLOW, "
         f"{sum(1 for i in insights if i['priority'] == 'GREEN')} GREEN")

    # Compute store scores
    _log("Computing store scores...")
    store_scores = compute_store_scores(data)
    _log(f"Ranked {len(store_scores)} stores")

    # Generate action items (auto + manual)
    generated_date = datetime.now()
    action_items = generate_action_items(insights, generated_date)
    _log(f"Assembled {len(action_items)} action items for next week")

    # Text renderer
    text = TextRenderer(data, insights)

    # Dump JSON if requested
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        _log(f"Data JSON saved: {args.json_out}")

    if args.dry_run:
        print("\n=== DRY RUN: Summary ===")
        ov = data["overview"]
        print(f"  Active stores:    {ov.get('active_stores', 'N/A')}")
        print(f"  Total orders:     {fmt_int(ov.get('this_total_orders'))}")
        print(f"  Total revenue:    {fmt_money(ov.get('this_total_revenue'))}")
        print(f"  Avg ticket:       {fmt_money(ov.get('this_avg_ticket'))}")
        print(f"  Completion rate:  {fmt_pct(ov.get('this_completion_rate'))}")
        print(f"  Cancel rate:      {fmt_pct(ov.get('this_cancel_rate'))}")
        print(f"  Satisfaction:     {fmt_pct(ov.get('this_satisfaction'))}")
        print(f"  New customers:    {fmt_int(ov.get('this_new_customers'))}")
        print(f"  Return rate:      {fmt_pct(ov.get('this_return_rate'))}")
        print(f"\n  Ch1 summary: {text.ch1_summary()}")
        print(f"\n  Insights ({len(insights)}):")
        for ins in insights:
            emoji = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}[ins["priority"]]
            print(f"    {emoji} [{ins['rule_id']}] {ins['title']}")
        print(f"\n  Store rankings ({len(store_scores)}):")
        for s in store_scores[:5]:
            print(f"    #{s['rank']} {s['shop_name']} — {s['score']} pts — {s['status']}")
        print(f"\n  Action items ({len(action_items)}):")
        for a in action_items:
            print(f"    {a['priority_label']} {a['description'][:60]}...")
        return

    # Generate PDF
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(OUTPUT_DIR, f"weekly-report-{iso_year}-W{iso_week:02d}.pdf")

    _log(f"Rendering PDF: {output_path}")
    t_pdf = time.monotonic()
    builder = PDFReportBuilder(data, insights, store_scores, action_items, text)
    builder.build(output_path)
    _log(f"PDF rendered in {time.monotonic() - t_pdf:.1f}s")

    try:
        size_kb = os.path.getsize(output_path) / 1024.0
        size_str = f" ({size_kb:,.0f} KB)"
    except OSError:
        size_str = ""
    _log(f"Done in {time.monotonic() - t_start:.1f}s — report saved to: {output_path}{size_str}")


if __name__ == "__main__":
    main()
