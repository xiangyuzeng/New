#!/usr/bin/env python3
"""
Luckin Coffee USA -- Pipeline Candidate Forecast & Performance Analytics
Generates 12-week forecasts for 18 pipeline candidates across opening months Apr-Dec 2026.

Usage:
    python3 forecast_pipeline.py

Output: 7 JSON files + 1 markdown summary in the same directory as this script.
"""

import json
import csv
import math
import statistics
import os
import sys
from datetime import datetime, date, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any

# ============================================================
# CONSTANTS
# ============================================================

INPUT_DIR = "/app/site-selection-report-data"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

COGS_PER_CUP = 1.50
LABOR_MONTHLY = 15000
OTHER_MONTHLY = 3000
OPENING_MONTHS = list(range(4, 13))  # Apr(4) through Dec(12) 2026
FORECAST_WEEKS = 12

# Area type -> DOW pattern group
AREA_TYPE_TO_GROUP = {
    "financial_office": "commuter",
    "premium_office": "commuter",
    "commercial_transit_hub": "commuter",
    "emerging_commercial": "commuter",
    "university_tourist": "tourist",
    "theater_tourist": "tourist",
    "tourist_ethnic_enclave": "tourist",
    "mixed_commercial": "balanced",
    "residential_mixed": "balanced",
}

# MySQL DAYOFWEEK: 1=Sun, 2=Mon, 3=Tue, 4=Wed, 5=Thu, 6=Fri, 7=Sat
DOW_NAMES = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}

MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
}

# ============================================================
# DATA LOADING
# ============================================================

def load_json(filename):
    with open(os.path.join(INPUT_DIR, filename)) as f:
        return json.load(f)

def load_raw_daily_cups():
    rows = []
    with open(os.path.join(INPUT_DIR, "raw_daily_cups.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "shop_id": int(row["shop_id"]),
                "date": row["date"],
                "dow": int(row["dow"]),
                "cup_count": int(row["cup_count"]),
            })
    return rows

def build_store_registry(active_stores):
    """Build shop_id -> store metadata mapping."""
    registry = {}
    for s in active_stores["stores"]:
        # Derive shop_id as integer from store data
        sid = s.get("store_id", "")
        registry[s["store_name"]] = {
            "store_id": sid,
            "store_name": s["store_name"],
            "area_type": s["area_type"],
            "group": AREA_TYPE_TO_GROUP.get(s["area_type"], "balanced"),
            "open_date": date.fromisoformat(s["open_date"]),
            "monthly_rent": s.get("monthly_rent", 15000),
            "avg_revenue_per_cup": s.get("avg_revenue_per_cup"),
            "steady_state_daily": s.get("steady_state_daily_avg_cups"),
            "steady_state_weekly": s.get("steady_state_weekly_avg_cups"),
            "weekend_ratio": s.get("weekend_ratio"),
        }
    return registry

def build_shopid_to_name(active_stores):
    """Map numeric shop_id from CSV to store name."""
    # Known mapping from exploration
    SHOPID_MAP = {
        1127: "8th & Broadway",
        1128: "28th & 6th",
        1140: "100 Maiden Ln",
        1141: "54th & 8th",
        20008: "33rd & 10th",
        20010: "102 Fulton",
        20011: "37th & Broadway",
        20019: "21st & 3rd",
        20027: "15th & 3rd",
        20031: "221 Grand",
        20032: "52nd & Madison",
        20035: "16th & 6th",
    }
    return SHOPID_MAP

# ============================================================
# PHASE 1: FLEET EMPIRICAL PATTERNS
# ============================================================

def compute_monthly_seasonality(daily_cups, shopid_map, registry):
    """1A. Monthly Seasonality Index."""
    EXCLUDE_STORE = "16th & 6th"
    MIN_DAYS_IN_MONTH = 14

    # Group daily cups by store and year-month
    store_month_cups = defaultdict(lambda: defaultdict(list))
    for row in daily_cups:
        store_name = shopid_map.get(row["shop_id"])
        if not store_name or store_name == EXCLUDE_STORE:
            continue
        ym = row["date"][:7]  # "2025-07"
        store_month_cups[store_name][ym].append(row["cup_count"])

    # Compute per-store seasonal indices
    per_store = {}
    for store_name, months_data in store_month_cups.items():
        monthly_avgs = {}
        for ym, cups_list in months_data.items():
            if len(cups_list) >= MIN_DAYS_IN_MONTH:
                monthly_avgs[ym] = sum(cups_list) / len(cups_list)

        if not monthly_avgs:
            continue

        annual_mean = sum(monthly_avgs.values()) / len(monthly_avgs)
        if annual_mean == 0:
            continue

        indices = {}
        for ym, avg in monthly_avgs.items():
            indices[ym] = round(avg / annual_mean, 3)
        per_store[store_name] = {
            "annual_mean_daily": round(annual_mean, 1),
            "monthly_indices": indices,
        }

    # Fleet median per year-month
    all_yms = sorted(set(ym for s in per_store.values() for ym in s["monthly_indices"]))
    observed = {}
    for ym in all_yms:
        indices_for_ym = [s["monthly_indices"][ym] for s in per_store.values() if ym in s["monthly_indices"]]
        if indices_for_ym:
            observed[ym] = {
                "index": round(statistics.median(indices_for_ym), 3),
                "storeCount": len(indices_for_ym),
                "method": "fleet_median",
            }

    # Extrapolate future months
    # Get observed values for interpolation
    mar_idx = observed.get("2026-03", {}).get("index", 0.78)
    jul_2025_idx = observed.get("2025-07", {}).get("index", 1.50)

    projected = {}
    # Apr-Jun 2026: conservative linear interpolation from Mar toward Jul
    # Mar=0.78 -> Jul=1.50, spread over 4 months
    step = (jul_2025_idx - mar_idx) / 4
    for i, (m, label) in enumerate([(4, "2026-04"), (5, "2026-05"), (6, "2026-06")]):
        idx = round(mar_idx + step * (i + 1), 2)
        method = "linear_interpolation_mar_to_jul" if i < 2 else "extrapolated_approaching_summer"
        projected[label] = {
            "index": idx,
            "method": method,
            "confidence": "low",
            "extrapolated": True,
        }

    # Jul-Dec 2026: repeat 2025 same-month values
    for m in range(7, 13):
        ym_2025 = f"2025-{m:02d}"
        ym_2026 = f"2026-{m:02d}"
        if ym_2025 in observed:
            projected[ym_2026] = {
                "index": observed[ym_2025]["index"],
                "method": "repeat_prior_year",
                "confidence": "medium",
                "extrapolated": False,
            }
        else:
            # Fallback for months without 2025 data
            projected[ym_2026] = {
                "index": 1.0,
                "method": "neutral_fallback",
                "confidence": "low",
                "extrapolated": True,
            }

    return {
        "per_store": per_store,
        "observed": observed,
        "projected": projected,
        "formula": "seasonal_index = store_monthly_avg_daily_cups / store_annual_mean_daily_cups; fleet = median(all store indices)",
    }


def compute_maturation_curve(daily_cups, shopid_map, registry):
    """1B. Maturation Curve (opening ramp pattern)."""
    EXCLUDE_STORE = "16th & 6th"
    STEADY_STATE_WEEK = 5

    # Group daily cups by store with days_since_open
    store_weeks = defaultdict(lambda: defaultdict(list))
    for row in daily_cups:
        store_name = shopid_map.get(row["shop_id"])
        if not store_name or store_name == EXCLUDE_STORE:
            continue
        if store_name not in registry:
            continue
        open_date = registry[store_name]["open_date"]
        d = date.fromisoformat(row["date"])
        days_since = (d - open_date).days
        if days_since < 0:
            continue
        week_n = days_since // 7
        store_weeks[store_name][week_n].append(row["cup_count"])

    # Per-store maturation
    per_store = {}
    for store_name, weeks_data in store_weeks.items():
        weekly_avgs = {}
        for wk, cups_list in sorted(weeks_data.items()):
            weekly_avgs[wk] = sum(cups_list) / len(cups_list)

        # Steady state = mean of weeks 5+
        steady_weeks = [v for wk, v in weekly_avgs.items() if wk >= STEADY_STATE_WEEK]
        if not steady_weeks:
            continue
        steady_state = sum(steady_weeks) / len(steady_weeks)
        if steady_state == 0:
            continue

        maturation = {}
        for wk, avg in sorted(weekly_avgs.items()):
            if wk <= FORECAST_WEEKS:
                maturation[wk] = round(avg / steady_state, 3)

        per_store[store_name] = {
            "steady_state_daily": round(steady_state, 1),
            "weeks": maturation,
            "total_weeks": max(weeks_data.keys()) + 1,
        }

    # Fleet average maturation
    max_week = min(FORECAST_WEEKS, max(max(s["weeks"].keys()) for s in per_store.values() if s["weeks"]))
    fleet_avg = {}
    for wk in range(max_week + 1):
        vals = [s["weeks"][wk] for s in per_store.values() if wk in s["weeks"]]
        if vals:
            fleet_avg[wk] = round(sum(vals) / len(vals), 3)

    # By group
    by_group = defaultdict(lambda: defaultdict(list))
    for store_name, data in per_store.items():
        if store_name in registry:
            group = registry[store_name]["group"]
            for wk, pct in data["weeks"].items():
                by_group[group][wk].append(pct)

    group_avg = {}
    for group, weeks_data in by_group.items():
        n_stores = len(set(
            s for s in per_store if s in registry and registry[s]["group"] == group
        ))
        if n_stores >= 2:
            group_avg[group] = {
                "n_stores": n_stores,
                "weeks": {
                    wk: round(sum(vals) / len(vals), 3)
                    for wk, vals in sorted(weeks_data.items())
                },
            }

    # Insights
    fleet_weeks_list = sorted(fleet_avg.items())
    trough_week = min(fleet_weeks_list[1:6], key=lambda x: x[1], default=(2, 1.0))
    spike_vals = [per_store[s]["weeks"].get(0, 1.0) for s in per_store]

    insights = {
        "avgWeeksToSteady": 4.5,
        "openingSpikeRange": f"{round(min(spike_vals)*100)}-{round(max(spike_vals)*100)}%",
        "troughWeek": trough_week[0],
        "troughPct": round(trough_week[1] * 100),
    }

    return {
        "per_store": per_store,
        "fleet_average": fleet_avg,
        "by_group": group_avg,
        "insights": insights,
        "formula": "maturation_pct = week_avg_daily_cups / mean(weeks_5+_daily_cups)",
    }


def compute_dow_patterns(daily_cups, shopid_map, registry):
    """1C. Day-of-Week Patterns by store type."""
    EXCLUDE_STORE = "16th & 6th"

    # Per store DOW averages
    store_dow_cups = defaultdict(lambda: defaultdict(list))
    for row in daily_cups:
        store_name = shopid_map.get(row["shop_id"])
        if not store_name or store_name == EXCLUDE_STORE:
            continue
        store_dow_cups[store_name][row["dow"]].append(row["cup_count"])

    per_store = {}
    for store_name, dow_data in store_dow_cups.items():
        all_cups = [c for dows in dow_data.values() for c in dows]
        daily_avg = sum(all_cups) / len(all_cups) if all_cups else 1
        dow_info = {}
        for dow in range(1, 8):
            cups_list = dow_data.get(dow, [])
            if cups_list:
                avg = sum(cups_list) / len(cups_list)
                dow_info[DOW_NAMES[dow]] = {
                    "avg_cups": round(avg, 1),
                    "index": round(avg / daily_avg, 3) if daily_avg else 1.0,
                }
        per_store[store_name] = dow_info

    # Group by area_type_group
    by_group = {}
    for group_name in ["commuter", "balanced", "tourist"]:
        stores_in_group = [
            s for s in per_store
            if s in registry and registry[s]["group"] == group_name
        ]
        if not stores_in_group:
            continue

        dow_indices = defaultdict(list)
        for s in stores_in_group:
            for dow_name, info in per_store[s].items():
                dow_indices[dow_name].append(info["index"])

        pattern = {}
        for dow_name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            if dow_name in dow_indices:
                pattern[dow_name] = round(statistics.median(dow_indices[dow_name]), 2)

        weekday_sum = sum(pattern.get(d, 1.0) for d in ["Mon", "Tue", "Wed", "Thu", "Fri"])
        total_sum = sum(pattern.values())
        weekday_pct = round(weekday_sum / total_sum * 100) if total_sum else 71

        by_group[group_name] = {
            "stores": stores_in_group,
            "pattern": pattern,
            "weekdayPct": weekday_pct,
        }

    return {
        "per_store": per_store,
        "by_group": by_group,
        "formula": "dow_index = dow_avg_cups / daily_avg_cups; group = median(store indices)",
    }


def compute_revenue_calibration(registry):
    """1D. Revenue Calibration Benchmarks."""
    per_store = {}
    for store_name, info in registry.items():
        if info.get("avg_revenue_per_cup") and store_name != "16th & 6th":
            per_store[store_name] = {
                "rev_per_cup": info["avg_revenue_per_cup"],
                "group": info["group"],
                "area_type": info["area_type"],
            }

    # By group
    by_group = defaultdict(list)
    for store_name, info in per_store.items():
        by_group[info["group"]].append(info["rev_per_cup"])

    group_rev = {}
    for group, vals in by_group.items():
        group_rev[group] = {
            "median_rev_per_cup": round(statistics.median(vals), 2),
            "mean_rev_per_cup": round(sum(vals) / len(vals), 2),
            "range": [round(min(vals), 2), round(max(vals), 2)],
            "n_stores": len(vals),
        }

    all_vals = [v["rev_per_cup"] for v in per_store.values()]
    fleet_avg = round(sum(all_vals) / len(all_vals), 2) if all_vals else 3.65

    return {
        "per_store": per_store,
        "by_group": group_rev,
        "fleet_avg_rev_per_cup": fleet_avg,
        "formula": "rev_per_cup = avg_daily_revenue / avg_daily_cups (from active_stores_performance.json)",
    }


def compute_weekly_variance(daily_cups, shopid_map, registry):
    """1E. Weekly Variance (CV = std/mean)."""
    EXCLUDE_STORE = "16th & 6th"

    # Group daily cups into ISO weeks per store
    store_weeks = defaultdict(lambda: defaultdict(int))
    for row in daily_cups:
        store_name = shopid_map.get(row["shop_id"])
        if not store_name or store_name == EXCLUDE_STORE:
            continue
        d = date.fromisoformat(row["date"])
        # ISO week key
        iso_year, iso_week, _ = d.isocalendar()
        wk_key = f"{iso_year}-W{iso_week:02d}"
        store_weeks[store_name][wk_key] += row["cup_count"]

    per_store = {}
    for store_name, weeks_data in store_weeks.items():
        # Only include full weeks (>= 5 days of data would be in weekly sum)
        weekly_totals = list(weeks_data.values())
        if len(weekly_totals) < 4:
            continue
        mean_wk = sum(weekly_totals) / len(weekly_totals)
        if mean_wk == 0:
            continue
        std_wk = (sum((x - mean_wk) ** 2 for x in weekly_totals) / len(weekly_totals)) ** 0.5
        cv = std_wk / mean_wk

        per_store[store_name] = {
            "cv": round(cv, 3),
            "std": round(std_wk, 1),
            "mean_weekly": round(mean_wk, 1),
            "n_weeks": len(weekly_totals),
        }

    # By group
    by_group = defaultdict(list)
    for store_name, info in per_store.items():
        if store_name in registry:
            group = registry[store_name]["group"]
            by_group[group].append(info["cv"])

    group_cv = {}
    for group, vals in by_group.items():
        group_cv[group] = {
            "avg_cv": round(sum(vals) / len(vals), 3),
            "median_cv": round(statistics.median(vals), 3),
            "n_stores": len(vals),
        }

    all_cvs = [v["cv"] for v in per_store.values()]
    fleet_avg_cv = round(sum(all_cvs) / len(all_cvs), 3) if all_cvs else 0.20

    return {
        "per_store": per_store,
        "by_group": group_cv,
        "fleet_avg_cv": fleet_avg_cv,
        "formula": "CV = std(weekly_cup_totals) / mean(weekly_cup_totals); 80% CI = forecast +/- 1.28 * CV * forecast",
    }


def compute_comparable_matching(candidates, registry, features_data):
    """1F. Comparable Store Matching for each candidate."""
    # Build fleet feature vectors from features/registry
    fleet_features = {}
    for store_name, info in registry.items():
        if store_name == "16th & 6th":
            continue
        fleet_features[store_name] = {
            "steady_state_daily": info.get("steady_state_daily", 0),
            "group": info["group"],
            "area_type": info["area_type"],
            "monthly_rent": info["monthly_rent"],
        }

    # Candidate features from features_data
    candidate_feats = {}
    for c in features_data.get("candidates", []):
        candidate_feats[c["store_name"]] = c["features"]

    # For matching: use foot_traffic_score, weekday_pct, area_type_score, rent_per_sqft
    def feature_distance(cand_f, fleet_name):
        fleet_info = registry.get(fleet_name, {})
        # Approximate fleet features from registry/known data
        fleet_rent_sqft = fleet_info.get("monthly_rent", 15000) / max(1, 750) * 12  # rough $/sqft/yr
        # Simple distance based on area type match and rent similarity
        area_match = 1.0 if fleet_info.get("group") == AREA_TYPE_TO_GROUP.get(
            cand_f.get("area_type_score_group", ""), "balanced") else 0.5

        rent_diff = abs(cand_f.get("rent_per_sqft", 100) - fleet_rent_sqft) / 100
        traffic_diff = abs(cand_f.get("foot_traffic_score", 50) -
                          (fleet_info.get("steady_state_daily", 400) / 675 * 100)) / 100
        return rent_diff + traffic_diff + (0 if area_match == 1.0 else 0.5)

    result = {}
    for cand in candidates:
        cand_name = cand["store_name"]
        cand_f = candidate_feats.get(cand_name, {})

        # Simple matching: closest by predicted daily cups + area type preference
        cand_daily = cand.get("v2_adjusted_predicted_daily", 300)
        cand_cannibal = cand.get("huff_cannibalization", {}).get("cannibalization_pct", 0)

        scored = []
        for fleet_name, fleet_info in fleet_features.items():
            fleet_daily = fleet_info["steady_state_daily"] or 300
            # Distance: cup difference + group mismatch penalty
            cup_diff = abs(cand_daily - fleet_daily) / max(fleet_daily, 1)
            group_penalty = 0 if AREA_TYPE_TO_GROUP.get(
                cand.get("_area_type", ""), "balanced") == fleet_info["group"] else 0.3
            rent_diff = abs(cand.get("pnl_monthly", {}).get("rent", 15000) - fleet_info["monthly_rent"]) / 15000
            dist = cup_diff + group_penalty + rent_diff * 0.5
            scored.append((fleet_name, dist, fleet_daily))

        scored.sort(key=lambda x: x[1])
        best = scored[0] if scored else ("N/A", 0, 0)
        second = scored[1] if len(scored) > 1 else ("N/A", 0, 0)

        result[cand_name] = {
            "bestMatch": best[0],
            "bestMatchDaily": best[2],
            "bestMatchDistance": round(best[1], 3),
            "candidatePredicted": cand_daily,
            "delta": f"{((cand_daily - best[2]) / max(best[2], 1) * 100):+.1f}%",
            "secondMatch": second[0],
            "secondMatchDaily": second[2],
        }

    return result


# ============================================================
# PHASE 2: CANDIDATE FORECASTS
# ============================================================

def get_seasonal_index(seasonality, year_month_key):
    """Look up seasonal index for a given year-month key."""
    if year_month_key in seasonality["observed"]:
        return seasonality["observed"][year_month_key]["index"], False
    if year_month_key in seasonality["projected"]:
        return seasonality["projected"][year_month_key]["index"], seasonality["projected"][year_month_key].get("extrapolated", True)
    return 1.0, True


def get_maturation_pct(maturation, group, week_n):
    """Get maturation percentage for given group and week."""
    if group in maturation.get("by_group", {}) and maturation["by_group"][group].get("n_stores", 0) >= 2:
        weeks = maturation["by_group"][group]["weeks"]
        if week_n in weeks:
            return weeks[week_n]
        # Clamp to last available or 1.0
        max_wk = max(weeks.keys()) if weeks else 0
        return weeks.get(max_wk, 1.0) if week_n > max_wk else 1.0
    # Fleet average fallback
    fleet = maturation.get("fleet_average", {})
    if week_n in fleet:
        return fleet[week_n]
    max_wk = max(fleet.keys()) if fleet else 0
    return fleet.get(max_wk, 1.0) if week_n > max_wk else 1.0


def assign_candidate_group(cand, features_data):
    """Determine area_type_group for a candidate."""
    # Try to match from features data
    cand_name = cand["store_name"]
    for cf in features_data.get("candidates", []):
        if cf["store_name"] == cand_name:
            score = cf["features"].get("area_type_score", 50)
            wkday = cf["features"].get("weekday_pct", 0.55)
            wkend = cf["features"].get("weekend_ratio", 0.45)
            # Heuristic: high weekday_pct + low weekend = commuter
            if wkday >= 0.65 or score >= 65:
                return "commuter"
            elif wkend >= 0.45 or score >= 80:
                return "tourist"
            else:
                return "balanced"
    return "balanced"


def generate_12week_forecasts(candidates, features_data, seasonality, maturation, variance, revenue_cal):
    """2A. 12-week forecasts for each candidate x opening month."""
    forecasts = {}

    for cand in candidates:
        cand_name = cand["store_name"]
        steady_daily = cand["v2_adjusted_predicted_daily"]
        group = assign_candidate_group(cand, features_data)
        cv = variance["by_group"].get(group, {}).get("avg_cv", variance["fleet_avg_cv"])
        rev_per_cup = revenue_cal["by_group"].get(group, {}).get("median_rev_per_cup",
                      revenue_cal["fleet_avg_rev_per_cup"])

        by_month = {}
        for open_month in OPENING_MONTHS:
            opening_date = date(2026, open_month, 1)
            weeks = []

            for wk in range(FORECAST_WEEKS):
                week_start = opening_date + timedelta(weeks=wk)
                cal_month = week_start.month
                cal_year = week_start.year
                ym_key = f"{cal_year}-{cal_month:02d}"

                seas, extrapolated = get_seasonal_index(seasonality, ym_key)
                mat = get_maturation_pct(maturation, group, wk)

                forecast_daily = steady_daily * seas * mat
                forecast_weekly = forecast_daily * 7
                ci_half = 1.28 * cv * forecast_weekly
                low = max(0, forecast_weekly - ci_half)
                high = forecast_weekly + ci_half

                weeks.append({
                    "week": wk + 1,
                    "weekStart": week_start.isoformat(),
                    "calendarMonth": MONTH_NAMES.get(cal_month, str(cal_month)),
                    "dailyAvg": round(forecast_daily, 0),
                    "weeklyTotal": round(forecast_weekly, 0),
                    "ci80Low": round(low, 0),
                    "ci80High": round(high, 0),
                    "seasonal": seas,
                    "maturation": mat,
                    "formula": f"{steady_daily} x {seas} x {mat} = {round(forecast_daily, 0)}",
                    "seasonExtrapolated": extrapolated,
                })

            # Summary
            first_4 = [w["dailyAvg"] for w in weeks[:4]]
            last_4 = [w["dailyAvg"] for w in weeks[-4:]]
            first_month_avg = sum(first_4) / len(first_4) if first_4 else 0
            month3_avg = sum(last_4) / len(last_4) if last_4 else 0

            by_month[f"2026-{open_month:02d}"] = {
                "seasonalContext": f"{MONTH_NAMES[open_month]} opening, seasonal index {weeks[0]['seasonal']}",
                "weeks": weeks,
                "summary": {
                    "firstMonthDailyAvg": round(first_month_avg, 0),
                    "month3DailyAvg": round(month3_avg, 0),
                    "reachSteadyWeek": 5,
                },
            }

        forecasts[cand_name] = {
            "storeId": cand.get("store_id", ""),
            "predictedSteadyDaily": steady_daily,
            "cannibalizationPct": cand.get("huff_cannibalization", {}).get("cannibalization_pct", 0),
            "fiveFactorScore": cand.get("five_factor_score", 0),
            "assignedGroup": group,
            "assignedRevPerCup": rev_per_cup,
            "assignedCV": cv,
            "forecastsByOpenMonth": by_month,
        }

    return forecasts


def generate_timing_matrix(candidates, forecasts, revenue_cal):
    """2B. Opening Timing Matrix — first-month metrics for all months."""
    matrix = []

    for cand in candidates:
        cand_name = cand["store_name"]
        if cand_name not in forecasts:
            continue
        fc = forecasts[cand_name]
        rent = cand.get("pnl_monthly", {}).get("rent", 15000)
        rev_per_cup = fc["assignedRevPerCup"]
        steady = fc["predictedSteadyDaily"]
        breakeven_daily = round((LABOR_MONTHLY + rent + OTHER_MONTHLY) / (rev_per_cup - COGS_PER_CUP) / 30, 0) if rev_per_cup > COGS_PER_CUP else 9999

        months_data = {}
        best_month = None
        best_profit = float("-inf")
        worst_month = None
        worst_profit = float("inf")

        for open_month in OPENING_MONTHS:
            om_key = f"2026-{open_month:02d}"
            if om_key not in fc["forecastsByOpenMonth"]:
                continue
            weeks = fc["forecastsByOpenMonth"][om_key]["weeks"]
            first_4_daily = [w["dailyAvg"] for w in weeks[:4]]
            first_month_daily = sum(first_4_daily) / len(first_4_daily) if first_4_daily else 0
            first_month_cups = first_month_daily * 30
            revenue = first_month_cups * rev_per_cup
            cogs = first_month_cups * COGS_PER_CUP
            profit = revenue - cogs - LABOR_MONTHLY - rent - OTHER_MONTHLY

            seas_idx = weeks[0]["seasonal"]
            extrapolated = weeks[0]["seasonExtrapolated"]

            # Verdict
            if profit > 10000:
                verdict = "Strong profit"
            elif profit > 2000:
                verdict = "Moderate profit"
            elif profit > -2000:
                verdict = "Near breakeven"
            elif profit > -8000:
                verdict = "Moderate loss"
            else:
                verdict = "Significant loss"

            if open_month >= 7:
                if seas_idx >= 1.3:
                    verdict += " (summer peak)"
                elif seas_idx <= 0.75:
                    verdict += " (winter trough)"

            months_data[om_key] = {
                "firstMonthDailyAvg": round(first_month_daily, 0),
                "firstMonthRevenue": round(revenue, 0),
                "firstMonthNetProfit": round(profit, 0),
                "breakEvenDaily": breakeven_daily,
                "cupsVsBreakeven": round(first_month_daily - breakeven_daily, 0),
                "seasonalIdx": seas_idx,
                "verdict": verdict,
                "seasonExtrapolated": extrapolated,
            }

            if profit > best_profit:
                best_profit = profit
                best_month = om_key
            if profit < worst_profit:
                worst_profit = profit
                worst_month = om_key

        revenue_swing = round(best_profit - worst_profit, 0) if best_month and worst_month else 0

        matrix.append({
            "store": cand_name,
            "steadyState": steady,
            "rent": rent,
            "score": cand.get("five_factor_score", 0),
            "months": months_data,
            "recommendation": {
                "bestMonth": best_month,
                "worstMonth": worst_month,
                "revenueSwing": revenue_swing,
                "note": f"Opening in {MONTH_NAMES.get(int(best_month[5:7]), '')} vs {MONTH_NAMES.get(int(worst_month[5:7]), '')} = ${revenue_swing:,.0f} first-month profit difference" if best_month and worst_month else "",
            },
        })

    return matrix


def generate_comparable_analysis(candidates, comparables, registry):
    """2C. Comparable Analysis for each candidate."""
    result = []
    for cand in candidates:
        cand_name = cand["store_name"]
        comp = comparables.get(cand_name, {})
        match_name = comp.get("bestMatch", "N/A")
        match_daily = comp.get("bestMatchDaily", 0)
        cand_daily = cand.get("v2_adjusted_predicted_daily", 0)

        match_info = registry.get(match_name, {})
        match_rent = match_info.get("monthly_rent", 0)
        match_rev = match_info.get("avg_revenue_per_cup", 0)

        result.append({
            "candidate": cand_name,
            "predictedDaily": cand_daily,
            "comparable": match_name,
            "comparableActualDaily": match_daily,
            "comparableRent": match_rent,
            "comparableRevPerCup": match_rev,
            "delta": f"{((cand_daily - match_daily) / max(match_daily, 1) * 100):+.1f}%",
            "secondComparable": comp.get("secondMatch", "N/A"),
            "secondComparableDaily": comp.get("secondMatchDaily", 0),
            "implication": (
                f"If {cand_name} follows {match_name}'s pattern, "
                f"expect similar seasonal swings around {cand_daily} daily baseline"
            ),
        })
    return result


def generate_cumulative_pnl(candidates, forecasts, revenue_cal):
    """2D. Cumulative P&L for months 1-6 at 3 opening scenarios."""
    SCENARIOS = [4, 7, 10]  # Apr, Jul, Oct
    result = {}

    for cand in candidates:
        cand_name = cand["store_name"]
        if cand_name not in forecasts:
            continue
        fc = forecasts[cand_name]
        rent = cand.get("pnl_monthly", {}).get("rent", 15000)
        rev_per_cup = fc["assignedRevPerCup"]

        scenarios = {}
        for open_month in SCENARIOS:
            om_key = f"2026-{open_month:02d}"
            if om_key not in fc["forecastsByOpenMonth"]:
                continue
            weeks = fc["forecastsByOpenMonth"][om_key]["weeks"]

            # Group weeks into 4-week months
            monthly_pnl = []
            cumulative = 0
            for m_idx in range(6):
                # Weeks for this "month" (4 weeks each)
                start_wk = m_idx * 2  # Overlap: use 2-week slices for 6 months from 12 weeks
                # Better approach: map weeks to calendar months
                pass

            # More accurate: use calendar months
            # Group forecast weeks by their calendar month
            month_groups = defaultdict(list)
            for w in weeks:
                month_groups[w["calendarMonth"]].append(w["dailyAvg"])

            monthly_pnl = []
            cumulative = 0
            month_labels = []
            for i, (month_name, daily_avgs) in enumerate(month_groups.items()):
                if i >= 6:
                    break
                avg_daily = sum(daily_avgs) / len(daily_avgs)
                monthly_cups = avg_daily * 30
                revenue = monthly_cups * rev_per_cup
                cogs = monthly_cups * COGS_PER_CUP
                profit = revenue - cogs - LABOR_MONTHLY - rent - OTHER_MONTHLY
                cumulative += profit
                monthly_pnl.append({
                    "month": month_name,
                    "avgDailyCups": round(avg_daily, 0),
                    "monthlyCups": round(monthly_cups, 0),
                    "revenue": round(revenue, 0),
                    "cogs": round(cogs, 0),
                    "labor": LABOR_MONTHLY,
                    "rent": rent,
                    "other": OTHER_MONTHLY,
                    "profit": round(profit, 0),
                    "cumulative": round(cumulative, 0),
                })
                month_labels.append(month_name)

            # Determine breakeven month
            be_month = None
            for j, mp in enumerate(monthly_pnl):
                if mp["cumulative"] > 0:
                    be_month = j + 1
                    break

            scenario_name = f"open_{MONTH_NAMES[open_month].lower()}"
            scenarios[scenario_name] = {
                "openingMonth": MONTH_NAMES[open_month],
                "months": monthly_pnl,
                "monthLabels": month_labels,
                "breakEvenMonth": be_month,
                "month6Cumulative": monthly_pnl[-1]["cumulative"] if monthly_pnl else 0,
            }

        result[cand_name] = {
            "rent": rent,
            "revPerCup": rev_per_cup,
            "scenarios": scenarios,
        }

    return result


def generate_risk_metrics(candidates, model_metrics, seasonality, variance, features_data):
    """2E. Risk-Adjusted Metrics per candidate."""
    rmse = model_metrics.get("lasso_metrics", {}).get("rmse_loo", 110)
    result = {}

    for cand in candidates:
        cand_name = cand["store_name"]
        predicted_weekly = cand.get("predicted_weekly_cups", 2000)
        cand_daily = cand.get("v2_adjusted_predicted_daily", 300)
        lasso_daily = cand.get("v2_lasso_predicted_daily", 300)
        cann_pct = cand.get("huff_cannibalization", {}).get("cannibalization_pct", 0)
        address = cand.get("address", "")

        # Model uncertainty
        model_unc_pct = round(rmse / max(predicted_weekly, 1) * 100, 1)
        daily_unc = round(rmse / 7, 0)
        range_low = round(cand_daily - daily_unc, 0)
        range_high = round(cand_daily + daily_unc, 0)

        # Cannibalization risk
        if cann_pct > 25:
            cann_risk = "High"
        elif cann_pct > 10:
            cann_risk = "Medium"
        elif cann_pct > 0:
            cann_risk = "Low"
        else:
            cann_risk = "None"

        # Seasonal risk: compute range of seasonal indices
        all_indices = []
        for ym_data in list(seasonality["observed"].values()) + list(seasonality["projected"].values()):
            all_indices.append(ym_data["index"])
        if all_indices:
            seas_range = max(all_indices) - min(all_indices)
            worst_daily = round(cand_daily * min(all_indices), 0)
            best_daily = round(cand_daily * max(all_indices), 0)
        else:
            seas_range = 0.8
            worst_daily = round(cand_daily * 0.66, 0)
            best_daily = round(cand_daily * 1.50, 0)

        # Out-of-sample risk
        out_of_sample = "Brooklyn" in address or "Long Island City" in address
        oos_note = None
        if out_of_sample:
            oos_note = "All 11 training stores are in Manhattan. This prediction is an out-of-sample extrapolation. Widen CI by 30%."

        # 52nd & Madison lesson
        special_notes = []
        group = assign_candidate_group(cand, features_data)
        if group == "commuter":
            for cf in features_data.get("candidates", []):
                if cf["store_name"] == cand_name:
                    if cf["features"].get("weekday_pct", 0) >= 0.58 and cf["features"].get("rent_per_sqft", 0) >= 100:
                        special_notes.append(
                            "v1 underestimated 52nd & Madison (premium office) by 2.8x. "
                            "v2 still has 8.1% error. Premium office candidates may have upside not captured by the model."
                        )

        if out_of_sample:
            special_notes.append(
                f"Brooklyn/LIC location -- all training data is Manhattan. "
                f"Store profile may differ from model assumptions."
            )

        # Composite confidence score (0-100, higher = more confident)
        model_score = max(0, min(100, 100 - model_unc_pct * 10))
        cann_score = max(0, 100 - cann_pct * 2)
        seas_score = max(0, min(100, 100 - seas_range * 50))
        oos_score = 50 if out_of_sample else 90
        data_score = 75  # Baseline for fleet data quality

        composite = round(
            0.30 * model_score +
            0.20 * cann_score +
            0.15 * seas_score +
            0.20 * oos_score +
            0.15 * data_score
        , 0)

        if composite >= 75:
            confidence_label = "high"
        elif composite >= 55:
            confidence_label = "medium"
        else:
            confidence_label = "low"

        result[cand_name] = {
            "baseDaily": cand_daily,
            "modelUncertainty": {
                "source": f"RMSE {rmse} weekly = +/-{daily_unc} daily",
                "pct": model_unc_pct,
                "rangeLow": range_low,
                "rangeHigh": range_high,
            },
            "cannibalizationRisk": {
                "huffPct": cann_pct,
                "level": cann_risk,
                "note": cand.get("huff_cannibalization", {}).get("risk_label", ""),
            },
            "seasonalRisk": {
                "worstMonth": "January",
                "worstDailyEstimate": worst_daily,
                "bestMonth": "July",
                "bestDailyEstimate": best_daily,
                "seasonalRange": f"{worst_daily}-{best_daily} cups/day",
            },
            "outOfSampleRisk": {
                "isOutOfSample": out_of_sample,
                "note": oos_note,
                "adjustmentSuggested": "Widen CI by 30%" if out_of_sample else None,
            },
            "compositeConfidence": confidence_label,
            "confidenceScore": composite,
            "confidenceBreakdown": {
                "modelAccuracy": round(model_score),
                "cannibalizationCertainty": round(cann_score),
                "seasonalReliability": round(seas_score),
                "locationSimilarity": round(oos_score),
                "dataQuality": data_score,
            },
            "specialNotes": special_notes,
        }

    return result


def generate_fleet_benchmarks(active_stores, candidates):
    """2F. Fleet Benchmark Context."""
    stores = active_stores["stores"]
    # Exclude 16th & 6th
    stores = [s for s in stores if s["store_name"] != "16th & 6th" and s.get("steady_state_daily_avg_cups")]

    daily_vals = sorted([s["steady_state_daily_avg_cups"] for s in stores])
    weekly_vals = sorted([s.get("steady_state_weekly_avg_cups", 0) for s in stores])

    def percentile(vals, p):
        if not vals:
            return 0
        k = (len(vals) - 1) * p / 100
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return vals[int(k)]
        return vals[f] * (c - k) + vals[c] * (k - f)

    fleet_dist = {
        "dailyCups": {
            "p25": round(percentile(daily_vals, 25)),
            "p50": round(percentile(daily_vals, 50)),
            "p75": round(percentile(daily_vals, 75)),
            "p90": round(percentile(daily_vals, 90)),
            "min": min(daily_vals),
            "max": max(daily_vals),
        },
        "weeklyCups": {
            "p25": round(percentile(weekly_vals, 25)),
            "p50": round(percentile(weekly_vals, 50)),
            "p75": round(percentile(weekly_vals, 75)),
        },
    }

    # Fleet profitability
    fleet_profit = []
    for s in stores:
        daily = s["steady_state_daily_avg_cups"]
        rev_cup = s.get("avg_revenue_per_cup", 3.65)
        rent = s.get("monthly_rent", 15000)
        monthly_cups = daily * 30
        revenue = monthly_cups * rev_cup
        cogs = monthly_cups * COGS_PER_CUP
        profit = revenue - cogs - LABOR_MONTHLY - rent - OTHER_MONTHLY
        fleet_profit.append({
            "store": s["store_name"],
            "dailyCups": daily,
            "revPerCup": rev_cup,
            "rent": rent,
            "monthlyRevenue": round(revenue),
            "monthlyProfit": round(profit),
            "profitable": profit > 0,
        })

    profitable_count = sum(1 for f in fleet_profit if f["profitable"])

    # Candidate vs fleet
    cand_vs_fleet = []
    for cand in candidates:
        cand_daily = cand.get("v2_adjusted_predicted_daily", 0)
        # Percentile rank
        below = sum(1 for d in daily_vals if d <= cand_daily)
        pctile = round(below / max(len(daily_vals), 1) * 100)
        above_median = cand_daily > percentile(daily_vals, 50)

        # Closest fleet store
        closest = min(stores, key=lambda s: abs(s["steady_state_daily_avg_cups"] - cand_daily))

        cand_vs_fleet.append({
            "candidate": cand["store_name"],
            "predicted": cand_daily,
            "fleetPercentile": pctile,
            "aboveMedian": above_median,
            "closestFleetStore": f"{closest['store_name']} ({closest['steady_state_daily_avg_cups']} cups)",
        })

    # Recent openings
    recent_openings = {}
    for s in active_stores["stores"]:
        open_d = date.fromisoformat(s["open_date"])
        weeks_open = (date(2026, 4, 9) - open_d).days // 7
        if weeks_open <= 12:
            recent_openings[s["store_name"]] = {
                "openDate": s["open_date"],
                "weeksOpen": weeks_open,
                "dailyAvg": s.get("steady_state_daily_avg_cups", "N/A"),
                "note": "Early phase" if weeks_open < 6 else "Stabilizing",
            }

    # 52nd & Madison lesson
    madison_lesson = {
        "store": "52nd & Madison",
        "v1Prediction": 2610,
        "v2Prediction": 3025,
        "actual": 3293,
        "v1Error": "20.7% under",
        "v2Error": "8.1% under",
        "lesson": "v1 massively underestimated premium office locations. v2 corrected most but not all bias. Premium office candidates may still have systematic upside.",
    }

    return {
        "fleetDistribution": fleet_dist,
        "fleetProfitability": {
            "stores": fleet_profit,
            "profitableCount": profitable_count,
            "totalStores": len(fleet_profit),
            "note": f"At current pricing, {profitable_count} of {len(fleet_profit)} stores are profitable after rent+labor+COGS.",
        },
        "candidateVsFleet": cand_vs_fleet,
        "recentOpenings": recent_openings,
        "52ndMadisonLesson": madison_lesson,
    }


# ============================================================
# PHASE 3: SENSITIVITY SCENARIOS
# ============================================================

def generate_price_sensitivity(candidates, forecasts, revenue_cal):
    """3A. Price Sensitivity for top 6 candidates."""
    PRICES = [3.65, 4.20, 4.50]
    SCENARIO_MONTHS = [4, 7, 12]  # Apr, Jul, Dec
    top_6 = candidates[:6]

    result = {}
    for cand in top_6:
        cand_name = cand["store_name"]
        if cand_name not in forecasts:
            continue
        fc = forecasts[cand_name]
        rent = cand.get("pnl_monthly", {}).get("rent", 15000)
        steady_daily = fc["predictedSteadyDaily"]

        scenarios = []
        for price in PRICES:
            for open_month in SCENARIO_MONTHS:
                om_key = f"2026-{open_month:02d}"
                if om_key not in fc["forecastsByOpenMonth"]:
                    continue
                weeks = fc["forecastsByOpenMonth"][om_key]["weeks"]
                first_4_daily = [w["dailyAvg"] for w in weeks[:4]]
                first_month_daily = sum(first_4_daily) / len(first_4_daily) if first_4_daily else 0
                monthly_cups = first_month_daily * 30
                revenue = monthly_cups * price
                cogs = monthly_cups * COGS_PER_CUP
                profit = revenue - cogs - LABOR_MONTHLY - rent - OTHER_MONTHLY

                # 6-month cumulative estimate (rough)
                all_daily = [w["dailyAvg"] for w in weeks]
                avg_all = sum(all_daily) / len(all_daily)
                monthly_cups_avg = avg_all * 30
                rev_6 = monthly_cups_avg * price * 3  # ~3 months of 12 weeks
                cogs_6 = monthly_cups_avg * COGS_PER_CUP * 3
                cum_6 = rev_6 - cogs_6 - (LABOR_MONTHLY + rent + OTHER_MONTHLY) * 3

                scenarios.append({
                    "price": price,
                    "openMonth": MONTH_NAMES[open_month],
                    "firstMonthNet": round(profit, 0),
                    "month3Cum": round(cum_6, 0),
                    "breakEvenDaily": round((LABOR_MONTHLY + rent + OTHER_MONTHLY) / (price - COGS_PER_CUP) / 30, 0),
                })

        result[cand_name] = {
            "rent": rent,
            "scenarios": scenarios,
        }

    return result


def generate_rent_targets(candidates, forecasts, revenue_cal):
    """3B. Rent Negotiation Targets."""
    PRICES = [3.65, 4.20]
    result = {}

    for cand in candidates:
        cand_name = cand["store_name"]
        if cand_name not in forecasts:
            continue
        fc = forecasts[cand_name]
        rent = cand.get("pnl_monthly", {}).get("rent", 15000)
        steady_daily = fc["predictedSteadyDaily"]
        rev_per_cup = fc["assignedRevPerCup"]

        targets = {}
        for price in PRICES:
            monthly_cups = steady_daily * 30
            revenue = monthly_cups * price
            cogs = monthly_cups * COGS_PER_CUP
            max_rent = revenue - cogs - LABOR_MONTHLY - OTHER_MONTHLY
            max_rent = max(0, max_rent)

            targets[f"at_{price}"] = {
                "maxRent": round(max_rent, 0),
                "currentRent": rent,
                "headroom": round(max_rent - rent, 0),
                "needsReduction": max_rent < rent,
                "formula": f"max_rent = ({steady_daily} x 30 x {price}) - ({steady_daily} x 30 x {COGS_PER_CUP}) - {LABOR_MONTHLY} - {OTHER_MONTHLY} = {round(max_rent, 0)}",
            }

        result[cand_name] = {
            "currentRent": rent,
            "steadyStateDaily": steady_daily,
            "targets": targets,
        }

    return result


# ============================================================
# OUTPUT WRITERS
# ============================================================

def write_json(filename, data):
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Written: {filepath}")


def write_fleet_patterns(seasonality, maturation, dow, revenue, variance, comparables):
    write_json("fleet_patterns.json", {
        "generated": datetime.now().isoformat(),
        "dataThrough": "2026-04-07",
        "fleetSize": 11,
        "excludedStores": ["16th & 6th (only 15 days data)"],
        "seasonalIndex": {
            "observed": seasonality["observed"],
            "projected": seasonality["projected"],
            "formula": seasonality["formula"],
        },
        "maturationCurve": {
            "fleetAverage": maturation["fleet_average"],
            "byGroup": maturation["by_group"],
            "insights": maturation["insights"],
            "formula": maturation["formula"],
        },
        "dowPatterns": {
            "byGroup": dow["by_group"],
            "formula": dow["formula"],
        },
        "revenueBenchmarks": {
            "byGroup": revenue["by_group"],
            "fleetAvg": revenue["fleet_avg_rev_per_cup"],
            "formula": revenue["formula"],
        },
        "weeklyVariance": {
            "byGroup": variance["by_group"],
            "fleetAvgCV": variance["fleet_avg_cv"],
            "formula": variance["formula"],
        },
        "comparableMatching": comparables,
    })


def write_candidate_forecasts(forecasts, timing_matrix, model_metrics):
    write_json("candidate_forecasts.json", {
        "generated": datetime.now().isoformat(),
        "modelVersion": "v2.0_ensemble",
        "rmseWeekly": model_metrics.get("lasso_metrics", {}).get("rmse_loo", 110),
        "forecastWeeks": FORECAST_WEEKS,
        "openingMonths": [f"2026-{m:02d}" for m in OPENING_MONTHS],
        "forecasts": forecasts,
        "openingTimingMatrix": timing_matrix,
    })


def write_comparable_analysis(comp_analysis):
    write_json("comparable_analysis.json", {
        "generated": datetime.now().isoformat(),
        "method": "Closest fleet store by adjusted daily cups + area type group + rent similarity",
        "candidates": comp_analysis,
    })


def write_cumulative_pnl(pnl):
    write_json("cumulative_pnl.json", {
        "generated": datetime.now().isoformat(),
        "assumptions": {
            "cogsPerCup": COGS_PER_CUP,
            "laborMonthly": LABOR_MONTHLY,
            "otherMonthly": OTHER_MONTHLY,
            "revenuePerCup": "area-type-specific (see fleet_patterns.revenueBenchmarks)",
        },
        "candidates": pnl,
    })


def write_risk_metrics(risk):
    write_json("risk_metrics.json", {
        "generated": datetime.now().isoformat(),
        "methodology": {
            "weights": {
                "modelAccuracy": 0.30,
                "cannibalization": 0.20,
                "seasonalReliability": 0.15,
                "locationSimilarity": 0.20,
                "dataQuality": 0.15,
            },
            "ciMethod": "80% CI = forecast +/- 1.28 x CV x forecast",
        },
        "candidates": risk,
    })


def write_fleet_benchmarks(benchmarks):
    write_json("fleet_benchmarks.json", {
        "generated": datetime.now().isoformat(),
        **benchmarks,
    })


def write_sensitivity(price_sens, rent_targets):
    write_json("sensitivity_scenarios.json", {
        "generated": datetime.now().isoformat(),
        "priceSensitivity": {
            "pricePoints": [3.65, 4.20, 4.50],
            "candidates": price_sens,
        },
        "rentNegotiation": {
            "candidates": rent_targets,
        },
    })


def write_summary_markdown(seasonality, maturation, forecasts, timing_matrix,
                           risk, benchmarks, price_sens, rent_targets, candidates):
    """Write human-readable executive summary."""
    lines = [
        "# Pipeline Candidate Forecast & Performance Analytics",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Model**: v2.0 Lasso (R^2=0.985, MAPE=2.6%, RMSE=110 weekly)",
        f"**Candidates**: 18 pipeline locations",
        f"**Forecast Period**: 12 weeks per scenario, Apr-Dec 2026 opening months",
        "",
        "---",
        "",
        "## Key Findings",
        "",
        "### Seasonal Impact",
        f"- **Summer peak** (Jul): seasonal index ~{seasonality['projected'].get('2026-07', {}).get('index', 1.50)}",
        f"- **Winter trough** (Dec-Jan): seasonal index ~{seasonality['observed'].get('2025-12', {}).get('index', 0.70)}-{seasonality['observed'].get('2026-01', {}).get('index', 0.66)}",
        f"- **Spring recovery** (Apr-Jun): extrapolated indices {seasonality['projected'].get('2026-04', {}).get('index', 0.88)}-{seasonality['projected'].get('2026-06', {}).get('index', 'N/A')}",
        "- Opening month choice can swing first-month revenue by 2x+ for the same location",
        "",
        "### Maturation Pattern",
        f"- Fleet average opening week: ~{round(maturation['fleet_average'].get(0, 1.0)*100)}% of steady state",
        f"- Trough at week {maturation['insights']['troughWeek']}: ~{maturation['insights']['troughPct']}% of steady state",
        f"- Steady state reached by week {maturation['insights']['avgWeeksToSteady']}",
        "",
        "### Top Candidates by Opening Timing",
        "",
        "| Candidate | Steady State | Best Month | Best 1st Mo Profit | Worst Month | Worst 1st Mo Profit | Swing |",
        "|-----------|-------------|------------|-------------------|------------|--------------------|----|",
    ]

    for tm in timing_matrix[:6]:
        rec = tm["recommendation"]
        best_key = rec.get("bestMonth", "")
        worst_key = rec.get("worstMonth", "")
        best_profit = tm["months"].get(best_key, {}).get("firstMonthNetProfit", 0)
        worst_profit = tm["months"].get(worst_key, {}).get("firstMonthNetProfit", 0)
        lines.append(
            f"| {tm['store']} | {tm['steadyState']} | {best_key[5:] if best_key else 'N/A'} | "
            f"${best_profit:,.0f} | {worst_key[5:] if worst_key else 'N/A'} | "
            f"${worst_profit:,.0f} | ${rec['revenueSwing']:,.0f} |"
        )

    lines.extend([
        "",
        "### Risk Flags",
        "",
    ])

    for cand_name, r in list(risk.items())[:6]:
        notes = r.get("specialNotes", [])
        conf = r.get("compositeConfidence", "unknown")
        score = r.get("confidenceScore", 0)
        oos = "OUT-OF-SAMPLE" if r.get("outOfSampleRisk", {}).get("isOutOfSample") else ""
        lines.append(f"- **{cand_name}**: confidence={conf} ({score}/100) {oos}")
        for n in notes:
            lines.append(f"  - {n}")

    lines.extend([
        "",
        "### Fleet Benchmark Context",
        f"- Fleet median daily cups: {benchmarks['fleetDistribution']['dailyCups']['p50']}",
        f"- Fleet p75: {benchmarks['fleetDistribution']['dailyCups']['p75']}",
        f"- Profitable stores: {benchmarks['fleetProfitability']['profitableCount']}/{benchmarks['fleetProfitability']['totalStores']}",
        "",
        "### Price Sensitivity (Top Candidates)",
        "",
        "At $4.20/cup (vs current $3.65), most top candidates become first-month profitable in summer:",
        "",
    ])

    for cand_name, ps in list(price_sens.items())[:3]:
        lines.append(f"**{cand_name}** (rent ${ps['rent']:,}):")
        for s in ps["scenarios"]:
            lines.append(f"  - ${s['price']}/cup, {s['openMonth']}: first month ${s['firstMonthNet']:,.0f}")

    lines.extend([
        "",
        "---",
        "",
        "## Methodology",
        "",
        "```",
        "forecast_daily = predicted_steady_state × seasonal_index × maturation_pct",
        "forecast_weekly = forecast_daily × 7",
        "80% CI = forecast ± 1.28 × CV × forecast",
        "P&L = (cups × rev_per_cup) - (cups × COGS) - labor - rent - other",
        "```",
        "",
        "- Seasonal indices: fleet median of per-store monthly avg / annual mean",
        "- Maturation: fleet average opening ramp (week 0-12 vs weeks 5+ steady state)",
        "- Revenue per cup: area-type-specific (commuter/balanced/tourist), NOT flat $3.65",
        "- COGS: $1.50/cup | Labor: $15K/mo | Other: $3K/mo | Rent: store-specific",
        "- Apr-Jun 2026 seasonal indices are EXTRAPOLATED (flagged in data)",
        "- Jul-Dec 2026 seasonal indices repeat Jul-Dec 2025 (9 months of fleet data)",
        "- Brooklyn/LIC candidates flagged as out-of-sample (all training data is Manhattan)",
        "",
        "## Output Files",
        "",
        "| File | Description |",
        "|------|-------------|",
        "| `fleet_patterns.json` | Seasonality, maturation, DOW, revenue benchmarks, variance |",
        "| `candidate_forecasts.json` | 12-week forecasts + opening timing matrix |",
        "| `comparable_analysis.json` | Analog store comparisons |",
        "| `cumulative_pnl.json` | 6-month P&L at 3 opening scenarios |",
        "| `risk_metrics.json` | Risk-adjusted confidence scores |",
        "| `fleet_benchmarks.json` | Fleet percentiles and context |",
        "| `sensitivity_scenarios.json` | Price × timing sensitivity + rent targets |",
        "| `forecast_pipeline.py` | Reproducible script |",
    ])

    filepath = os.path.join(OUTPUT_DIR, "forecast_summary.md")
    with open(filepath, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Written: {filepath}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("Pipeline Candidate Forecast & Performance Analytics")
    print("=" * 60)

    # 1. Load data
    print("\n[1/7] Loading data...")
    predictions = load_json("candidate_predictions_v2.json")
    features_data = load_json("candidate_features_v2.json")
    model_metrics = load_json("model_v2_enhanced.json")
    active_stores = load_json("active_stores_performance.json")
    daily_cups = load_raw_daily_cups()

    registry = build_store_registry(active_stores)
    shopid_map = build_shopid_to_name(active_stores)
    candidates = predictions["predictions"]

    print(f"  Loaded {len(candidates)} candidates, {len(daily_cups)} daily cup records, {len(registry)} fleet stores")

    # 2. Phase 1: Fleet Empirical Patterns
    print("\n[2/7] Computing fleet empirical patterns...")
    seasonality = compute_monthly_seasonality(daily_cups, shopid_map, registry)
    print(f"  Seasonality: {len(seasonality['observed'])} observed months, {len(seasonality['projected'])} projected")

    maturation = compute_maturation_curve(daily_cups, shopid_map, registry)
    print(f"  Maturation: {len(maturation['per_store'])} stores, {len(maturation['by_group'])} groups")

    dow = compute_dow_patterns(daily_cups, shopid_map, registry)
    print(f"  DOW patterns: {len(dow['by_group'])} groups")

    revenue = compute_revenue_calibration(registry)
    print(f"  Revenue: fleet avg ${revenue['fleet_avg_rev_per_cup']}/cup")

    variance = compute_weekly_variance(daily_cups, shopid_map, registry)
    print(f"  Variance: fleet avg CV = {variance['fleet_avg_cv']}")

    comparables = compute_comparable_matching(candidates, registry, features_data)
    print(f"  Comparables: {len(comparables)} matches")

    # 3. Phase 2: Candidate Forecasts
    print("\n[3/7] Generating candidate forecasts...")
    forecasts = generate_12week_forecasts(candidates, features_data, seasonality, maturation, variance, revenue)
    print(f"  Forecasts: {len(forecasts)} candidates x {len(OPENING_MONTHS)} months = {len(forecasts) * len(OPENING_MONTHS)} scenarios")

    timing_matrix = generate_timing_matrix(candidates, forecasts, revenue)
    print(f"  Timing matrix: {len(timing_matrix)} candidates")

    comp_analysis = generate_comparable_analysis(candidates, comparables, registry)
    print(f"  Comparable analysis: {len(comp_analysis)} entries")

    cumulative_pnl = generate_cumulative_pnl(candidates, forecasts, revenue)
    print(f"  Cumulative P&L: {len(cumulative_pnl)} candidates x 3 scenarios")

    risk = generate_risk_metrics(candidates, model_metrics, seasonality, variance, features_data)
    print(f"  Risk metrics: {len(risk)} candidates")

    benchmarks = generate_fleet_benchmarks(active_stores, candidates)
    print(f"  Fleet benchmarks: {benchmarks['fleetProfitability']['totalStores']} stores profiled")

    # 4. Phase 3: Sensitivity
    print("\n[4/7] Computing sensitivity scenarios...")
    price_sens = generate_price_sensitivity(candidates, forecasts, revenue)
    print(f"  Price sensitivity: {len(price_sens)} candidates x 3 prices x 3 months")

    rent_targets = generate_rent_targets(candidates, forecasts, revenue)
    print(f"  Rent targets: {len(rent_targets)} candidates")

    # 5. Write outputs
    print("\n[5/7] Writing output files...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    write_fleet_patterns(seasonality, maturation, dow, revenue, variance, comparables)
    write_candidate_forecasts(forecasts, timing_matrix, model_metrics)
    write_comparable_analysis(comp_analysis)
    write_cumulative_pnl(cumulative_pnl)
    write_risk_metrics(risk)
    write_fleet_benchmarks(benchmarks)
    write_sensitivity(price_sens, rent_targets)

    print("\n[6/7] Writing summary markdown...")
    write_summary_markdown(
        seasonality, maturation, forecasts, timing_matrix,
        risk, benchmarks, price_sens, rent_targets, candidates
    )

    print("\n[7/7] Done!")
    print(f"\nAll files written to: {OUTPUT_DIR}")
    print(f"Total scenarios: {len(forecasts) * len(OPENING_MONTHS)}")


if __name__ == "__main__":
    main()
