#!/usr/bin/env python3
"""
Luckin Coffee USA — Supplementary Analytics for Dashboard v2.0
Computes 8 new datasets from local CSV + metadata + DB query results.
"""

import csv
import json
import math
import statistics
import sys
from datetime import datetime, timedelta, date
from collections import defaultdict

# Import from existing pipeline
sys.path.insert(0, '/app/site-selection-report-data')
from process_all_phases import SHOP_ID_MAP, REVENUE_DATA, haversine

# ============================================================================
# CONSTANTS
# ============================================================================

CSV_PATH = "/app/site-selection-report-data/raw_daily_cups.csv"
PERF_PATH = "/app/site-selection-report-data/active_stores_performance.json"
OUTPUT_DIR = "/home/claude/dashboard-supplementary"

DOW_NAMES = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}
REVENUE_PER_CUP = 3.65

# DB query results (from t_order WHERE status >= 20, queried 2026-04-09)
ORDER_DATA = {
    1127:  {"total_orders": 166557, "avg_order_value": 4.50, "total_revenue": 749537.35, "days_span": 283},
    1128:  {"total_orders": 106826, "avg_order_value": 4.80, "total_revenue": 512531.20, "days_span": 283},
    1140:  {"total_orders": 45718,  "avg_order_value": 4.81, "total_revenue": 219714.01, "days_span": 212},
    1141:  {"total_orders": 71671,  "avg_order_value": 5.25, "total_revenue": 376028.39, "days_span": 228},
    20008: {"total_orders": 29189,  "avg_order_value": 4.83, "total_revenue": 140977.75, "days_span": 129},
    20010: {"total_orders": 78349,  "avg_order_value": 4.90, "total_revenue": 384198.81, "days_span": 224},
    20011: {"total_orders": 48469,  "avg_order_value": 4.83, "total_revenue": 234030.64, "days_span": 140},
    20019: {"total_orders": 2348,   "avg_order_value": 4.82, "total_revenue": 11322.72,  "days_span": 17},
    20027: {"total_orders": 12263,  "avg_order_value": 4.84, "total_revenue": 59398.42,  "days_span": 62},
    20031: {"total_orders": 19742,  "avg_order_value": 4.93, "total_revenue": 97307.79,  "days_span": 116},
    20032: {"total_orders": 42672,  "avg_order_value": 4.99, "total_revenue": 213094.25, "days_span": 108},
    20035: {"total_orders": 13102,  "avg_order_value": 4.88, "total_revenue": 63970.77,  "days_span": 42},
}

# GL-verified rents from store_lease_data.csv (confidence=HIGH only)
GL_VERIFIED_RENTS = {
    "US00006": 16000,   # 102 Fulton — 7 months consistent entries
    "US00020": 18000,   # 21st & 3rd
    "US00012": 10125,   # 16th & 6th — vs $17K in SHOP_ID_MAP
    "US00025": 13000,   # 221 Grand — rent portion only
    "US00027": 19360,   # 52nd & Madison — vs $22K in SHOP_ID_MAP
}

# Cannibalization pairs: (new_store_dept_id, affected_store_dept_id, description)
CANNIBALIZATION_PAIRS = [
    (20008, 1128,  "33rd & 10th opened Dec 1 → 28th & 6th"),
    (20027, 20031, "21st & 3rd opened Feb 6 → 15th & 3rd"),
    (20035, 20011, "52nd & Madison opened Feb 26 → 37th & Broadway"),
    (20019, 1127,  "16th & 6th opened Mar 23 → 8th & Broadway"),
    (20019, 20031, "16th & 6th opened Mar 23 → 15th & 3rd"),
]


# ============================================================================
# DATA LOADING
# ============================================================================

def load_csv():
    """Load raw_daily_cups.csv into dict: {dept_id: [(date, dow, cups), ...]}"""
    data = defaultdict(list)
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dept_id = int(row['shop_id'])
            dt = datetime.strptime(row['date'], '%Y-%m-%d').date()
            dow = int(row['dow'])
            cups = int(row['cup_count'])
            data[dept_id].append((dt, dow, cups))
    # Sort by date
    for dept_id in data:
        data[dept_id].sort(key=lambda x: x[0])
    return data


def load_performance():
    """Load active_stores_performance.json"""
    with open(PERF_PATH, 'r') as f:
        return json.load(f)


def dept_to_shop(dept_id):
    """Map dept_id to shop_no (e.g., 1127 → 'US00001')"""
    if dept_id in SHOP_ID_MAP:
        return SHOP_ID_MAP[dept_id]['shop_no']
    return f"UNKNOWN_{dept_id}"


def dept_to_name(dept_id):
    """Map dept_id to store name"""
    if dept_id in SHOP_ID_MAP:
        return SHOP_ID_MAP[dept_id]['name']
    return f"Unknown ({dept_id})"


def get_open_date(dept_id):
    """Get opening date for a store"""
    if dept_id in SHOP_ID_MAP:
        return datetime.strptime(SHOP_ID_MAP[dept_id]['open_date'], '%Y-%m-%d').date()
    return None


# ============================================================================
# DATASET 1: WEEKLY TIME SERIES
# ============================================================================

def compute_weekly_time_series(daily_data):
    """Aggregate daily cups into weekly totals per store."""
    result = {}
    fleet_weekly = defaultdict(lambda: {"cups": 0, "stores": 0})

    for dept_id, days in daily_data.items():
        shop_no = dept_to_shop(dept_id)
        name = dept_to_name(dept_id)

        # Group by ISO week
        weeks = defaultdict(lambda: {"cups": 0, "days": 0})
        for dt, dow, cups in days:
            iso = dt.isocalendar()
            week_key = f"{iso[0]}-W{iso[1]:02d}"
            # Also store the Monday of this week for sorting
            monday = dt - timedelta(days=dt.weekday())
            weeks[week_key]["cups"] += cups
            weeks[week_key]["days"] += 1
            weeks[week_key]["monday"] = monday.isoformat()

        # Build sorted list, exclude partial weeks < 5 days
        week_list = []
        for wk, info in sorted(weeks.items()):
            if info["days"] >= 5:
                week_list.append({
                    "week": wk,
                    "weekStart": info["monday"],
                    "cups": info["cups"],
                    "days": info["days"],
                    "avgDaily": round(info["cups"] / info["days"], 1)
                })
                # Add to fleet totals
                fleet_weekly[wk]["cups"] += info["cups"]
                fleet_weekly[wk]["stores"] += 1

        result[shop_no] = {"name": name, "weeks": week_list}

    # Fleet totals
    fleet_list = []
    for wk in sorted(fleet_weekly.keys()):
        fw = fleet_weekly[wk]
        fleet_list.append({
            "week": wk,
            "totalCups": fw["cups"],
            "storeCount": fw["stores"],
            "avgPerStore": round(fw["cups"] / fw["stores"], 1)
        })

    all_dates = [d[0] for days in daily_data.values() for d in days]
    return {
        "perStore": result,
        "fleetWeekly": fleet_list,
        "metadata": {
            "totalWeeks": len(fleet_list),
            "dateRange": [min(all_dates).isoformat(), max(all_dates).isoformat()],
            "csvRows": sum(len(d) for d in daily_data.values())
        }
    }


# ============================================================================
# DATASET 2: MONTHLY SEASONALITY
# ============================================================================

def compute_monthly_seasonality(daily_data):
    """Aggregate into monthly averages, compute seasonal index."""
    result = {}
    fleet_monthly = defaultdict(lambda: {"total_cups": 0, "total_days": 0, "stores": set()})

    for dept_id, days in daily_data.items():
        shop_no = dept_to_shop(dept_id)
        name = dept_to_name(dept_id)
        open_dt = get_open_date(dept_id)

        # Group by month, skip first partial month after opening
        months = defaultdict(lambda: {"cups": 0, "days": 0})
        for dt, dow, cups in days:
            # Skip the opening month (noisy)
            if open_dt and dt.year == open_dt.year and dt.month == open_dt.month and open_dt.day > 1:
                continue
            month_key = f"{dt.year}-{dt.month:02d}"
            months[month_key]["cups"] += cups
            months[month_key]["days"] += 1

        # Only include stores with 3+ complete months
        complete_months = [k for k, v in months.items() if v["days"] >= 20]
        if len(complete_months) < 3:
            continue

        month_list = []
        for mk in sorted(months.keys()):
            info = months[mk]
            if info["days"] >= 15:  # Include months with at least 15 days
                avg = round(info["cups"] / info["days"], 1)
                month_list.append({
                    "month": mk,
                    "avgDaily": avg,
                    "days": info["days"]
                })
                fleet_monthly[mk]["total_cups"] += info["cups"]
                fleet_monthly[mk]["total_days"] += info["days"]
                fleet_monthly[mk]["stores"].add(shop_no)

        result[shop_no] = {"name": name, "months": month_list}

    # Fleet average by month
    fleet_list = []
    overall_avg = 0
    month_avgs = {}
    for mk in sorted(fleet_monthly.keys()):
        fm = fleet_monthly[mk]
        avg = round(fm["total_cups"] / fm["total_days"], 1)
        month_avgs[mk] = avg
        fleet_list.append({
            "month": mk,
            "avgDaily": avg,
            "storeCount": len(fm["stores"]),
            "totalDays": fm["total_days"]
        })

    # Seasonal index (month avg / overall avg)
    if month_avgs:
        overall_avg = statistics.mean(month_avgs.values())
        seasonal_index = {mk: round(v / overall_avg, 3) for mk, v in month_avgs.items()}
    else:
        seasonal_index = {}

    return {
        "perStore": result,
        "fleetAvgByMonth": fleet_list,
        "seasonalIndex": seasonal_index,
        "overallFleetAvgDaily": round(overall_avg, 1) if overall_avg else 0,
        "qualifyingStores": len(result)
    }


# ============================================================================
# DATASET 3: STORE MATURATION CURVES
# ============================================================================

def compute_maturation_curves(daily_data):
    """Calculate weekly avg cups relative to opening, normalize to steady state."""
    result = {}
    fleet_weeks = defaultdict(lambda: {"cups": [], "stores": 0})

    for dept_id, days in daily_data.items():
        shop_no = dept_to_shop(dept_id)
        name = dept_to_name(dept_id)
        open_dt = get_open_date(dept_id)
        if not open_dt:
            continue

        # Assign each day to a relative week number
        week_data = defaultdict(list)
        for dt, dow, cups in days:
            days_since = (dt - open_dt).days
            if days_since < 0:
                continue
            week_num = days_since // 7
            week_data[week_num].append(cups)

        # Compute steady state (weeks 5+ average)
        steady_days = []
        for wn, cup_list in week_data.items():
            if wn >= 4:  # week 4+ (28+ days)
                steady_days.extend(cup_list)
        steady_state = round(statistics.mean(steady_days), 1) if steady_days else None

        if not steady_state or steady_state == 0:
            continue

        # Build curve
        curve = []
        for wn in sorted(week_data.keys()):
            cup_list = week_data[wn]
            if len(cup_list) >= 5:  # Only full-ish weeks
                avg = statistics.mean(cup_list)
                pct = round(avg / steady_state * 100, 1)
                curve.append({
                    "week": wn,
                    "avgDaily": round(avg, 1),
                    "pctOfSteady": pct,
                    "days": len(cup_list)
                })
                fleet_weeks[wn]["cups"].append(avg)
                fleet_weeks[wn]["stores"] += 1

        result[shop_no] = {
            "name": name,
            "steadyStateAvg": steady_state,
            "totalWeeks": len(curve),
            "curve": curve
        }

    # Fleet average curve
    fleet_curve = []
    # Compute fleet steady state for normalization
    fleet_steady_vals = []
    for wn, info in fleet_weeks.items():
        if wn >= 4:
            fleet_steady_vals.extend(info["cups"])
    fleet_steady = statistics.mean(fleet_steady_vals) if fleet_steady_vals else 1

    for wn in sorted(fleet_weeks.keys()):
        info = fleet_weeks[wn]
        avg = statistics.mean(info["cups"])
        fleet_curve.append({
            "week": wn,
            "avgDaily": round(avg, 1),
            "pctOfSteady": round(avg / fleet_steady * 100, 1),
            "storeCount": info["stores"]
        })

    return {
        "perStore": result,
        "fleetAverageCurve": fleet_curve,
        "fleetSteadyStateAvg": round(fleet_steady, 1)
    }


# ============================================================================
# DATASET 4: CANNIBALIZATION EVIDENCE
# ============================================================================

def compute_cannibalization_evidence(daily_data):
    """Compare affected store's cups before vs after a nearby store opened."""
    pairs_result = []

    # Build lookup: dept_id → {date: cups}
    cups_by_date = {}
    for dept_id, days in daily_data.items():
        cups_by_date[dept_id] = {dt: cups for dt, dow, cups in days}

    # Fleet daily average (all stores combined) for market adjustment
    all_dates = sorted(set(dt for days in daily_data.values() for dt, _, _ in days))
    fleet_daily = {}
    for dt_val in all_dates:
        day_cups = []
        for dept_id, lookup in cups_by_date.items():
            if dt_val in lookup:
                day_cups.append(lookup[dt_val])
        fleet_daily[dt_val] = statistics.mean(day_cups) if day_cups else 0

    for new_dept, affected_dept, description in CANNIBALIZATION_PAIRS:
        new_name = dept_to_name(new_dept)
        affected_name = dept_to_name(affected_dept)
        new_open = get_open_date(new_dept)
        affected_open = get_open_date(affected_dept)

        if not new_open or affected_dept not in cups_by_date:
            continue

        # Distance between stores
        new_info = SHOP_ID_MAP[new_dept]
        aff_info = SHOP_ID_MAP[affected_dept]
        dist = haversine(new_info['lat'], new_info['lon'], aff_info['lat'], aff_info['lon'])

        # Before period: 28 days before new store opened
        before_start = new_open - timedelta(days=28)
        before_end = new_open - timedelta(days=1)

        # After period: 28 days after new store opened
        after_start = new_open
        after_end = new_open + timedelta(days=27)

        # Check affected store was already open during before period
        if affected_open and before_start < affected_open:
            # Adjust before_start to affected store opening + 7 days (skip opening noise)
            before_start = affected_open + timedelta(days=7)
            if before_start >= before_end:
                pairs_result.append({
                    "newStore": new_name,
                    "affectedStore": affected_name,
                    "distanceMiles": round(dist, 2),
                    "openDate": new_open.isoformat(),
                    "verdict": "Insufficient pre-opening data for affected store",
                    "skipped": True
                })
                continue

        # Collect cups for affected store in before/after windows
        affected_lookup = cups_by_date[affected_dept]
        before_cups = []
        after_cups = []
        fleet_before = []
        fleet_after = []

        for d in range((before_end - before_start).days + 1):
            dt_val = before_start + timedelta(days=d)
            if dt_val in affected_lookup:
                before_cups.append(affected_lookup[dt_val])
            if dt_val in fleet_daily:
                # Fleet avg excluding new and affected store
                day_cups_excl = []
                for did, lk in cups_by_date.items():
                    if did != new_dept and did != affected_dept and dt_val in lk:
                        day_cups_excl.append(lk[dt_val])
                if day_cups_excl:
                    fleet_before.append(statistics.mean(day_cups_excl))

        for d in range((after_end - after_start).days + 1):
            dt_val = after_start + timedelta(days=d)
            if dt_val in affected_lookup:
                after_cups.append(affected_lookup[dt_val])
            day_cups_excl = []
            for did, lk in cups_by_date.items():
                if did != new_dept and did != affected_dept and dt_val in lk:
                    day_cups_excl.append(lk[dt_val])
            if day_cups_excl:
                fleet_after.append(statistics.mean(day_cups_excl))

        if len(before_cups) < 14 or len(after_cups) < 14:
            pairs_result.append({
                "newStore": new_name,
                "affectedStore": affected_name,
                "distanceMiles": round(dist, 2),
                "openDate": new_open.isoformat(),
                "beforeDays": len(before_cups),
                "afterDays": len(after_cups),
                "verdict": f"Insufficient data (need 14+ days, got {len(before_cups)} before / {len(after_cups)} after)",
                "skipped": True
            })
            continue

        before_avg = statistics.mean(before_cups)
        after_avg = statistics.mean(after_cups)
        raw_change = (after_avg - before_avg) / before_avg * 100

        # Market adjustment
        fleet_before_avg = statistics.mean(fleet_before) if fleet_before else before_avg
        fleet_after_avg = statistics.mean(fleet_after) if fleet_after else after_avg
        market_change = (fleet_after_avg - fleet_before_avg) / fleet_before_avg * 100
        adjusted_change = raw_change - market_change

        # Huff model prediction: overlap = max(0, 1 - dist/1.0), diversion = overlap * weekly * 0.15
        huff_overlap = max(0, 1 - dist / 1.0)
        affected_weekly = before_avg * 7
        huff_diverted_weekly = huff_overlap * affected_weekly * 0.15
        huff_diverted_daily = huff_diverted_weekly / 7
        huff_predicted_pct = -huff_diverted_daily / before_avg * 100 if before_avg > 0 else 0

        pairs_result.append({
            "newStore": new_name,
            "affectedStore": affected_name,
            "distanceMiles": round(dist, 2),
            "openDate": new_open.isoformat(),
            "beforePeriod": {"start": before_start.isoformat(), "end": before_end.isoformat(),
                             "avgDailyCups": round(before_avg, 1), "days": len(before_cups)},
            "afterPeriod": {"start": after_start.isoformat(), "end": after_end.isoformat(),
                            "avgDailyCups": round(after_avg, 1), "days": len(after_cups)},
            "rawChangePct": round(raw_change, 1),
            "marketChangePct": round(market_change, 1),
            "marketAdjustedChangePct": round(adjusted_change, 1),
            "huffPredictedChangePct": round(huff_predicted_pct, 1),
            "huffOverlapPct": round(huff_overlap * 100, 1),
            "actualDiversionDaily": round(before_avg - after_avg, 1) if after_avg < before_avg else 0,
            "huffPredictedDiversionDaily": round(huff_diverted_daily, 1),
            "verdict": _cannibalization_verdict(raw_change, adjusted_change, huff_predicted_pct, dist),
            "skipped": False
        })

    # Summary
    valid = [p for p in pairs_result if not p.get("skipped")]
    return {
        "pairs": pairs_result,
        "summary": {
            "totalPairsAnalyzed": len(valid),
            "pairsSkipped": len(pairs_result) - len(valid),
            "avgRawChangePct": round(statistics.mean([p["rawChangePct"] for p in valid]), 1) if valid else None,
            "avgAdjustedChangePct": round(statistics.mean([p["marketAdjustedChangePct"] for p in valid]), 1) if valid else None,
        }
    }


def _cannibalization_verdict(raw_change, adjusted, huff_predicted, dist):
    """Generate a human-readable verdict."""
    if adjusted > -2:
        return f"No significant cannibalization detected (market-adjusted change: {adjusted:+.1f}%)"
    elif abs(adjusted) < abs(huff_predicted) * 0.5:
        return f"Huff model overestimated impact — actual {adjusted:+.1f}% vs predicted {huff_predicted:+.1f}%"
    elif abs(adjusted) > abs(huff_predicted) * 1.5:
        return f"Huff model underestimated impact — actual {adjusted:+.1f}% vs predicted {huff_predicted:+.1f}%"
    else:
        return f"Huff model reasonably accurate — actual {adjusted:+.1f}% vs predicted {huff_predicted:+.1f}%"


# ============================================================================
# DATASET 5: DAY OF WEEK HEATMAP
# ============================================================================

def compute_dow_heatmap(daily_data):
    """Average cups per day of week per store (steady-state only)."""
    result = {}
    fleet_dow = defaultdict(list)

    for dept_id, days in daily_data.items():
        shop_no = dept_to_shop(dept_id)
        name = dept_to_name(dept_id)
        open_dt = get_open_date(dept_id)

        # Filter to steady-state days (28+ days after opening)
        steady_days = []
        for dt, dow, cups in days:
            if open_dt and (dt - open_dt).days >= 28:
                steady_days.append((dow, cups))

        if len(steady_days) < 28:
            continue

        # Group by DOW
        dow_cups = defaultdict(list)
        for dow, cups in steady_days:
            dow_cups[dow].append(cups)

        # Compute averages
        overall_avg = statistics.mean([c for _, c in steady_days])
        dow_data = {}
        weekday_cups = []
        weekend_cups = []
        for dow_num in range(1, 8):
            if dow_num in dow_cups:
                avg = round(statistics.mean(dow_cups[dow_num]), 1)
                idx = round(avg / overall_avg, 3) if overall_avg > 0 else 1.0
                dow_data[DOW_NAMES[dow_num]] = {"avgCups": avg, "index": idx, "sampleDays": len(dow_cups[dow_num])}
                fleet_dow[dow_num].append(avg)

                # Weekday vs weekend classification
                if dow_num in (1, 7):  # Sun=1, Sat=7
                    weekend_cups.append(avg)
                else:
                    weekday_cups.append(avg)

        weekday_avg = statistics.mean(weekday_cups) if weekday_cups else 0
        weekend_avg = statistics.mean(weekend_cups) if weekend_cups else 0

        # Pattern classification
        if weekend_avg > 0 and weekday_avg / weekend_avg > 1.3:
            pattern = "commuter"
        elif weekday_avg > 0 and weekend_avg / weekday_avg > 1.1:
            pattern = "tourist/residential"
        else:
            pattern = "balanced"

        peak_day = max(dow_data.items(), key=lambda x: x[1]["avgCups"])[0]
        trough_day = min(dow_data.items(), key=lambda x: x[1]["avgCups"])[0]

        result[shop_no] = {
            "name": name,
            "pattern": pattern,
            "dow": dow_data,
            "peakDay": peak_day,
            "troughDay": trough_day,
            "weekdayAvg": round(weekday_avg, 1),
            "weekendAvg": round(weekend_avg, 1),
            "volatility": round(statistics.stdev([v["avgCups"] for v in dow_data.values()]) / overall_avg, 3) if len(dow_data) > 1 else 0
        }

    # Fleet average
    fleet_avg = {}
    for dow_num in range(1, 8):
        if dow_num in fleet_dow:
            fleet_avg[DOW_NAMES[dow_num]] = round(statistics.mean(fleet_dow[dow_num]), 1)

    return {
        "perStore": result,
        "fleetAverage": fleet_avg
    }


# ============================================================================
# DATASET 6: REVENUE COMPOSITION
# ============================================================================

def compute_revenue_composition(daily_data):
    """Combine order-level DB data with cups data for revenue analysis."""
    result = {}

    for dept_id, order_info in ORDER_DATA.items():
        shop_no = dept_to_shop(dept_id)
        name = dept_to_name(dept_id)
        rev_data = REVENUE_DATA.get(shop_no, {})

        days_span = order_info["days_span"]
        if days_span <= 0:
            continue

        daily_orders = round(order_info["total_orders"] / days_span, 1)
        daily_revenue = rev_data.get("avg_daily_revenue", order_info["total_revenue"] / days_span)
        daily_cups = rev_data.get("avg_daily_items", 0)

        # From active_stores_performance.json
        # cups from performance data
        perf_cups = 0
        for dept, info in SHOP_ID_MAP.items():
            if info["shop_no"] == shop_no:
                # Use the known steady-state cups
                break

        cups_per_order = round(daily_cups / daily_orders, 2) if daily_orders > 0 else 0
        revenue_per_cup = round(daily_revenue / daily_cups, 2) if daily_cups > 0 else 0
        revenue_per_order = order_info["avg_order_value"]

        result[shop_no] = {
            "name": name,
            "avgDailyOrders": daily_orders,
            "avgDailyCups": round(daily_cups, 1),
            "cupsPerOrder": cups_per_order,
            "avgOrderValue": round(revenue_per_order, 2),
            "avgRevenuePerCup": revenue_per_cup,
            "dailyRevenue": round(daily_revenue, 2),
            "itemsVsCupsDelta": f"REVENUE_DATA items ({round(daily_cups)}) includes non-cup items"
        }

    # Fleet summary
    all_cpo = [v["cupsPerOrder"] for v in result.values() if v["cupsPerOrder"] > 0]
    all_aov = [v["avgOrderValue"] for v in result.values()]
    all_rpc = [v["avgRevenuePerCup"] for v in result.values() if v["avgRevenuePerCup"] > 0]

    return {
        "perStore": result,
        "fleetSummary": {
            "avgCupsPerOrder": round(statistics.mean(all_cpo), 2) if all_cpo else 0,
            "avgOrderValue": round(statistics.mean(all_aov), 2) if all_aov else 0,
            "avgRevenuePerCup": round(statistics.mean(all_rpc), 2) if all_rpc else 0,
            "note": "Revenue per cup ($3.23-$3.54 from items) differs from per-order ($4.50-$5.25) because orders contain multiple items"
        }
    }


# ============================================================================
# DATASET 7: RENT EFFICIENCY
# ============================================================================

def compute_rent_efficiency(perf_data):
    """Calculate rent efficiency metrics per store."""
    stores = perf_data.get("stores", [])
    result = []
    discrepancies = []

    for store in stores:
        shop_no = store["store_id"]
        name = store["store_name"]

        # Get rent — prefer GL-verified where available
        model_rent = store.get("monthly_rent", 0)
        gl_rent = GL_VERIFIED_RENTS.get(shop_no)
        rent = gl_rent if gl_rent else model_rent
        rent_source = "GL-verified" if gl_rent else "model estimate"

        if gl_rent and model_rent and abs(gl_rent - model_rent) / model_rent > 0.05:
            discrepancies.append({
                "store": name,
                "storeId": shop_no,
                "modelRent": model_rent,
                "glVerifiedRent": gl_rent,
                "deltaPct": round((gl_rent - model_rent) / model_rent * 100, 1)
            })

        sqft = store.get("sqft", 0)
        daily_cups = store.get("steady_state_daily_avg_cups", store.get("opening_avg_daily_cups", 0))
        daily_revenue = store.get("avg_daily_revenue", 0)
        monthly_revenue = daily_revenue * 30

        if rent <= 0 or daily_cups <= 0:
            continue

        cups_per_1k = round(daily_cups / (rent / 1000), 1)
        rev_per_sqft = round(monthly_revenue / sqft, 1) if sqft > 0 else 0
        rent_pct = round(rent / monthly_revenue * 100, 1) if monthly_revenue > 0 else 999

        # P&L metrics
        cogs_monthly = daily_cups * 1.50 * 30
        labor = 15000
        other = 3000
        net_profit = monthly_revenue - cogs_monthly - rent - labor - other
        profit_per_sqft = round(net_profit / sqft, 1) if sqft > 0 else 0

        result.append({
            "name": name,
            "storeId": shop_no,
            "monthlyRent": rent,
            "rentSource": rent_source,
            "sqft": sqft,
            "dailyCups": daily_cups,
            "cupsPerThousandRent": cups_per_1k,
            "revenuePerSqftMonthly": rev_per_sqft,
            "rentAsPctOfRevenue": rent_pct,
            "monthlyRevenue": round(monthly_revenue, 0),
            "monthlyNetProfit": round(net_profit, 0),
            "profitPerSqft": profit_per_sqft
        })

    # Sort by cups_per_1k_rent descending
    result.sort(key=lambda x: x["cupsPerThousandRent"], reverse=True)

    # Add ranks
    for i, r in enumerate(result):
        r["efficiencyRank"] = i + 1

    return {
        "stores": result,
        "rankings": {
            "byCupsPerRent": [r["name"] for r in sorted(result, key=lambda x: x["cupsPerThousandRent"], reverse=True)],
            "byRevenuePerSqft": [r["name"] for r in sorted(result, key=lambda x: x["revenuePerSqftMonthly"], reverse=True)],
            "byLowestRentBurden": [r["name"] for r in sorted(result, key=lambda x: x["rentAsPctOfRevenue"])]
        },
        "rentDiscrepancies": discrepancies
    }


# ============================================================================
# DATASET 8: OPENING COHORT ANALYSIS
# ============================================================================

def compute_cohort_analysis(perf_data):
    """Group stores by opening quarter and compare performance."""
    stores = perf_data.get("stores", [])

    # Define cohorts
    cohorts = {
        "Q3-2025 (Jun-Aug)": {"start": date(2025, 6, 1), "end": date(2025, 8, 31)},
        "Q4-2025 (Sep-Nov)": {"start": date(2025, 9, 1), "end": date(2025, 11, 30)},
        "Q1-2026 (Dec-Feb)": {"start": date(2025, 12, 1), "end": date(2026, 2, 28)},
        "Q2-2026 (Mar-May)": {"start": date(2026, 3, 1), "end": date(2026, 5, 31)},
    }

    cohort_stores = {c: [] for c in cohorts}

    for store in stores:
        open_dt = datetime.strptime(store["open_date"], "%Y-%m-%d").date()
        for cohort_name, period in cohorts.items():
            if period["start"] <= open_dt <= period["end"]:
                cohort_stores[cohort_name].append(store)
                break

    result = []
    for cohort_name, cstores in cohort_stores.items():
        if not cstores:
            continue

        names = [s["store_name"] for s in cstores]
        steady = [s for s in cstores if s.get("steady_state_reached")]

        daily_cups = [s["steady_state_daily_avg_cups"] for s in steady] if steady else [s.get("opening_avg_daily_cups", 0) for s in cstores]
        rents = [s.get("monthly_rent", 0) for s in cstores if s.get("monthly_rent", 0) > 0]
        rev_per_cup = [s.get("avg_revenue_per_cup", 0) for s in steady] if steady else []
        trend_slopes = [s.get("trend_slope_pct", 0) for s in steady] if steady else []
        weeks = [s.get("total_weeks_of_data", 0) for s in cstores]

        top = max(steady, key=lambda s: s.get("steady_state_daily_avg_cups", 0)) if steady else cstores[0]

        cohort_entry = {
            "cohort": cohort_name,
            "stores": names,
            "count": len(cstores),
            "steadyStateCount": len(steady),
            "avgDailyCups": round(statistics.mean(daily_cups), 1) if daily_cups else 0,
            "medianDailyCups": round(statistics.median(daily_cups), 1) if daily_cups else 0,
            "avgRent": round(statistics.mean(rents)) if rents else 0,
            "avgRevPerCup": round(statistics.mean(rev_per_cup), 2) if rev_per_cup else 0,
            "avgTrendSlopePct": round(statistics.mean(trend_slopes), 1) if trend_slopes else 0,
            "weeksOfData": f"{min(weeks)}-{max(weeks)}" if weeks else "0",
            "topPerformer": f"{top['store_name']} ({top.get('steady_state_daily_avg_cups', top.get('opening_avg_daily_cups', 'N/A'))})",
            "maturityNote": "Fully mature (28+ weeks)" if min(weeks) >= 28 else f"Mixed maturity ({min(weeks)}-{max(weeks)} weeks)"
        }
        result.append(cohort_entry)

    # Cross-cohort insights
    if len(result) >= 2:
        first = result[0]
        last = [r for r in result if r["steadyStateCount"] > 0][-1] if any(r["steadyStateCount"] > 0 for r in result) else result[-1]
        trend = "improving" if last["avgDailyCups"] > first["avgDailyCups"] else "declining"
    else:
        trend = "insufficient data"

    return {
        "cohorts": result,
        "crossCohortInsight": {
            "performanceTrend": trend,
            "caveat": "Newer cohorts have less data and may still be ramping up. Q1-2026 includes winter months which depress averages."
        }
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("Loading data...")
    daily_data = load_csv()
    perf_data = load_performance()

    print(f"  CSV: {sum(len(d) for d in daily_data.values())} daily records across {len(daily_data)} stores")

    print("\n1/8: Computing weekly time series...")
    weekly = compute_weekly_time_series(daily_data)
    print(f"  → {weekly['metadata']['totalWeeks']} weeks, {len(weekly['perStore'])} stores")

    print("2/8: Computing monthly seasonality...")
    seasonality = compute_monthly_seasonality(daily_data)
    print(f"  → {seasonality['qualifyingStores']} qualifying stores, {len(seasonality['fleetAvgByMonth'])} months")

    print("3/8: Computing store maturation curves...")
    maturation = compute_maturation_curves(daily_data)
    print(f"  → {len(maturation['perStore'])} stores with curves")

    print("4/8: Computing cannibalization evidence...")
    cannibalization = compute_cannibalization_evidence(daily_data)
    valid = len([p for p in cannibalization['pairs'] if not p.get('skipped')])
    print(f"  → {valid} valid pairs analyzed, {len(cannibalization['pairs']) - valid} skipped")

    print("5/8: Computing day-of-week heatmap...")
    dow = compute_dow_heatmap(daily_data)
    print(f"  → {len(dow['perStore'])} stores")

    print("6/8: Computing revenue composition...")
    revenue = compute_revenue_composition(daily_data)
    print(f"  → {len(revenue['perStore'])} stores")

    print("7/8: Computing rent efficiency...")
    rent = compute_rent_efficiency(perf_data)
    print(f"  → {len(rent['stores'])} stores ranked, {len(rent['rentDiscrepancies'])} rent discrepancies found")

    print("8/8: Computing opening cohort analysis...")
    cohort = compute_cohort_analysis(perf_data)
    print(f"  → {len(cohort['cohorts'])} cohorts")

    # Assemble output
    output = {
        "metadata": {
            "generatedAt": datetime.now().strftime("%Y-%m-%d"),
            "purpose": "Supplementary analytics for dashboard v2.0 — does NOT overlap with existing data",
            "dataThrough": weekly["metadata"]["dateRange"][1],
            "csvRows": weekly["metadata"]["csvRows"],
            "storeCount": len(daily_data)
        },
        "weeklyTimeSeries": weekly,
        "monthlySeasonality": seasonality,
        "maturationCurves": maturation,
        "cannibalizationEvidence": cannibalization,
        "dowHeatmap": dow,
        "revenueComposition": revenue,
        "rentEfficiency": rent,
        "cohortAnalysis": cohort
    }

    output_path = f"{OUTPUT_DIR}/supplementary_data.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n✓ Output saved to {output_path}")
    print(f"  File size: {len(json.dumps(output, default=str)):,} bytes")

    return output


if __name__ == "__main__":
    main()
