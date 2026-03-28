#!/usr/bin/env python3
"""
Generate 4 CSV files for ConEdison energy consumption analysis.
Combines live database query results with static reference data.
"""
import csv
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 1. STORE MAPPING: ConEd address → internal store
# ============================================================
STORES = [
    {
        "label": "S01", "coned_account": "67291639960", "coned_address": "2799 Broadway",
        "dept_id": 20009, "shop_no": "US00007", "store_name": "108th & Broadway",
        "db_address": "2799 Broadway, New York, NY 10025",
        "lat": 40.802905, "lon": -73.967925,
        "status": "preparing (status=2)", "open_date": None,
        "neighborhood": "Upper West Side / Morningside Heights",
        "match_confidence": "EXACT",
        "scene_type": None,
    },
    {
        "label": "S02", "coned_account": "71595109811", "coned_address": "200 E 21st St",
        "dept_id": 20027, "shop_no": "US00020", "store_name": "21st & 3rd",
        "db_address": "261 3rd Avenue, New York, NY 10010",
        "lat": 40.737333, "lon": -73.983894,
        "status": "active (status=1)", "open_date": "2026-02-06",
        "neighborhood": "Gramercy",
        "match_confidence": "CONFIRMED — ConEd meter at 200 E 21st St, store at 261 3rd Ave (same building, different entrance)",
        "scene_type": "5",
    },
    {
        "label": "S03", "coned_account": "62790930457", "coned_address": "244 8th Ave",
        "dept_id": 20029, "shop_no": "US00022", "store_name": "23rd & 8th",
        "db_address": "244 8th Ave, New York, NY 10011",
        "lat": 40.744798, "lon": -73.998477,
        "status": "preparing (status=2)", "open_date": None,
        "neighborhood": "Chelsea",
        "match_confidence": "EXACT",
        "scene_type": None,
    },
    {
        "label": "S04", "coned_account": "76978209914", "coned_address": "488 Madison Ave",
        "dept_id": 20035, "shop_no": "US00027", "store_name": "52nd & Madison",
        "db_address": "488 Madison Ave, New York, NY 10022",
        "lat": 40.75891, "lon": -73.975197,
        "status": "active (status=1)", "open_date": "2026-02-26",
        "neighborhood": "Midtown / Plaza District",
        "match_confidence": "EXACT",
        "scene_type": "5",
    },
    {
        "label": "S05", "coned_account": "23520686272", "coned_address": "219 Grand St",
        "dept_id": 20032, "shop_no": "US00025", "store_name": "221 Grand",
        "db_address": "221 Grand St, New York, NY 10013",
        "lat": 40.718571, "lon": -73.995919,
        "status": "active (status=1)", "open_date": "2025-12-15",
        "neighborhood": "Chinatown / Little Italy",
        "match_confidence": "NEAR — ConEd 219 vs DB 221 (same building, different entrance numbering)",
        "scene_type": "5",
    },
    {
        "label": "S06", "coned_account": "06543049552", "coned_address": "125 W 31st St",
        "dept_id": 20028, "shop_no": "US00021", "store_name": "128 W 32nd St",
        "db_address": "128 W 32nd St, New York, NY 10001",
        "lat": 40.748921, "lon": -73.990053,
        "status": "preparing (status=2)", "open_date": None,
        "neighborhood": "Koreatown / Herald Square",
        "match_confidence": "CONFIRMED — ConEd meter at 125 W 31st St, store at 128 W 32nd St (adjacent building)",
        "scene_type": None,
    },
    {
        "label": "S07", "coned_account": "11688453528", "coned_address": "184 Thompson St",
        "dept_id": 20016, "shop_no": "US00010", "store_name": "154 Bleecker",
        "db_address": "154 Bleecker St, New York, NY 10012",
        "lat": 40.728185, "lon": -73.999602,
        "status": "under construction (status=2)", "open_date": None,
        "neighborhood": "Greenwich Village",
        "match_confidence": "CONFIRMED — ConEd meter at 184 Thompson St, store at 154 Bleecker St (under construction, ~2 blocks)",
        "scene_type": None,
    },
    {
        "label": "S08", "coned_account": "75509283620", "coned_address": "401 3rd Ave",
        "dept_id": 20026, "shop_no": "US00019", "store_name": "29th & 3rd",
        "db_address": "401 3rd Ave, New York, NY 10016",
        "lat": 40.742275, "lon": -73.980474,
        "status": "preparing (status=2)", "open_date": None,
        "neighborhood": "Kips Bay",
        "match_confidence": "EXACT",
        "scene_type": "5",
    },
    {
        "label": "S09", "coned_account": "21698356041", "coned_address": "352 E 23rd St",
        "dept_id": 20030, "shop_no": "US00023", "store_name": "23rd & 1st",
        "db_address": "352 E 23rd St, New York, NY 10010",
        "lat": 40.736731, "lon": -73.978947,
        "status": "preparing (status=2)", "open_date": None,
        "neighborhood": "Gramercy / Stuyvesant Town",
        "match_confidence": "EXACT",
        "scene_type": "5",
    },
    {
        "label": "S10", "coned_account": "25556485990", "coned_address": "147 3rd Ave",
        "dept_id": 20031, "shop_no": "US00024", "store_name": "15th & 3rd",
        "db_address": "147 3rd Ave, New York, NY 10003",
        "lat": 40.734028, "lon": -73.986224,
        "status": "active (status=1)", "open_date": "2025-12-14",
        "neighborhood": "Gramercy / East Village",
        "match_confidence": "EXACT",
        "scene_type": "5",
    },
    {
        "label": "S11", "coned_account": "84868252416", "coned_address": "102 Fulton St",
        "dept_id": 20010, "shop_no": "US00006", "store_name": "102 Fulton",
        "db_address": "102 Fulton St, New York, NY 10038",
        "lat": 40.709656, "lon": -74.00679,
        "status": "active (status=1)", "open_date": "2025-08-28",
        "neighborhood": "Financial District",
        "match_confidence": "EXACT",
        "scene_type": "5",
    },
    {
        "label": "S12", "coned_account": "38162017628", "coned_address": "555 6th Ave",
        "dept_id": 20019, "shop_no": "US00012", "store_name": "16th & 6th",
        "db_address": "555 6th Ave, New York, NY 10011",
        "lat": 40.738418, "lon": -73.996378,
        "status": "active (status=1)", "open_date": "2026-03-23",
        "neighborhood": "Chelsea / Union Square",
        "match_confidence": "EXACT",
        "scene_type": "5",
    },
]

# ============================================================
# 2. MONTHLY CUP + REVENUE DATA (from t_order + t_order_item)
# ============================================================
# Revenue from t_order (SUM(pay_money)), cups from COUNT(t_order_item rows)
ORDER_DATA = [
    # shop_id, ym, order_count, revenue_usd, operating_days
    (20010, "2025-08", 1950, 7765.90, 4),
    (20010, "2025-09", 12934, 59257.91, 30),
    (20010, "2025-10", 13421, 64572.77, 31),
    (20010, "2025-11", 11140, 52377.37, 30),
    (20010, "2025-12", 9603, 50043.55, 31),
    (20010, "2026-01", 8560, 43805.03, 31),
    (20010, "2026-02", 7729, 40243.14, 27),
    (20010, "2026-03", 9037, 45427.65, 28),
    (20019, "2026-03", 513, 2356.91, 5),
    (20027, "2026-02", 5025, 23324.17, 22),
    (20027, "2026-03", 6027, 29911.14, 28),
    (20031, "2025-12", 2502, 11201.41, 18),
    (20031, "2026-01", 5283, 25210.53, 31),
    (20031, "2026-02", 4500, 23093.97, 27),
    (20031, "2026-03", 4932, 24654.82, 28),
    (20032, "2025-12", 7394, 34753.14, 17),
    (20032, "2026-01", 12330, 61283.48, 31),
    (20032, "2026-02", 9577, 49778.45, 27),
    (20032, "2026-03", 10998, 54731.19, 28),
    (20035, "2026-02", 708, 3101.26, 3),
    (20035, "2026-03", 8073, 38756.56, 28),
]

CUP_DATA = [
    # shop_id, ym, total_cups
    (20010, "2025-08", 2473),
    (20010, "2025-09", 16270),
    (20010, "2025-10", 16944),
    (20010, "2025-11", 14904),
    (20010, "2025-12", 12918),
    (20010, "2026-01", 11483),
    (20010, "2026-02", 10287),
    (20010, "2026-03", 11712),
    (20019, "2026-03", 679),
    (20027, "2026-02", 6600),
    (20027, "2026-03", 7871),
    (20031, "2025-12", 3292),
    (20031, "2026-01", 6893),
    (20031, "2026-02", 5994),
    (20031, "2026-03", 6448),
    (20032, "2025-12", 10426),
    (20032, "2026-01", 17121),
    (20032, "2026-02", 13557),
    (20032, "2026-03", 15004),
    (20035, "2026-02", 959),
    (20035, "2026-03", 10708),
]

# ============================================================
# 3. STAFFING DATA (from t_emp_scheduling)
# ============================================================
STAFF_DATA = [
    # store_id, ym, days_with_staff, avg_daily_staff, avg_daily_hours
    (20009, "2026-03", 7, 7.0, 53.7),
    (20010, "2025-08", 9, 9.6, 72.0),
    (20010, "2025-09", 30, 10.5, 80.4),
    (20010, "2025-10", 31, 13.1, 101.7),
    (20010, "2025-11", 30, 15.1, 116.3),
    (20010, "2025-12", 31, 11.3, 84.3),
    (20010, "2026-01", 31, 11.8, 88.3),
    (20010, "2026-02", 28, 10.2, 77.0),
    (20010, "2026-03", 31, 11.2, 84.5),
    (20019, "2026-03", 13, 8.0, 59.8),
    (20027, "2026-02", 27, 8.9, 65.6),
    (20027, "2026-03", 31, 11.6, 86.3),
    (20031, "2025-12", 22, 9.6, 71.0),
    (20031, "2026-01", 31, 8.4, 61.5),
    (20031, "2026-02", 28, 9.1, 67.2),
    (20031, "2026-03", 31, 9.4, 66.9),
    (20032, "2025-12", 20, 9.8, 71.2),
    (20032, "2026-01", 31, 15.0, 113.1),
    (20032, "2026-02", 28, 12.3, 92.1),
    (20032, "2026-03", 31, 12.3, 92.3),
    (20035, "2026-02", 6, 10.7, 81.7),
    (20035, "2026-03", 30, 9.3, 71.4),
]


def dept_to_store(dept_id):
    """Look up store record by dept_id."""
    for s in STORES:
        if s["dept_id"] == dept_id:
            return s
    return None


def build_order_lookup():
    """Build dict: (shop_id, ym) -> {order_count, revenue_usd, operating_days}"""
    d = {}
    for shop_id, ym, order_count, revenue, op_days in ORDER_DATA:
        d[(shop_id, ym)] = {
            "order_count": order_count,
            "revenue_usd": revenue,
            "operating_days": op_days,
        }
    return d


def build_cup_lookup():
    """Build dict: (shop_id, ym) -> total_cups"""
    d = {}
    for shop_id, ym, cups in CUP_DATA:
        d[(shop_id, ym)] = cups
    return d


def build_staff_lookup():
    """Build dict: (store_id, ym) -> {days, staff, hours}"""
    d = {}
    for store_id, ym, days, staff, hours in STAFF_DATA:
        d[(store_id, ym)] = {
            "days_with_staff": days,
            "avg_daily_staff": staff,
            "avg_daily_hours": hours,
        }
    return d


# ============================================================
# FILE 1: store_info.csv
# ============================================================
def write_store_info():
    path = os.path.join(OUTPUT_DIR, "store_info.csv")
    fields = [
        "store_label", "store_id", "shop_no", "coned_account",
        "address_coned", "address_internal", "store_name_en", "store_name_cn",
        "city", "borough", "neighborhood", "latitude", "longitude",
        "area_sqft", "area_sqm", "store_type", "open_date", "store_status",
        "lease_type", "landlord_electricity", "equipment_notes",
        "match_confidence",
    ]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for s in STORES:
            w.writerow({
                "store_label": s["label"],
                "store_id": s["dept_id"] or "UNMATCHED",
                "shop_no": s["shop_no"] or "UNMATCHED",
                "coned_account": s["coned_account"],
                "address_coned": s["coned_address"],
                "address_internal": s["db_address"],
                "store_name_en": s["store_name"],
                "store_name_cn": "NOT AVAILABLE",
                "city": "New York",
                "borough": "Manhattan",
                "neighborhood": s["neighborhood"],
                "latitude": s["lat"] or "",
                "longitude": s["lon"] or "",
                "area_sqft": "NOT AVAILABLE — collect manually",
                "area_sqm": "NOT AVAILABLE — collect manually",
                "store_type": f"scene_type={s['scene_type']}" if s["scene_type"] else "NOT AVAILABLE — collect manually",
                "open_date": s["open_date"] or "NOT YET OPEN",
                "store_status": s["status"],
                "lease_type": "NOT AVAILABLE — collect manually",
                "landlord_electricity": "NOT AVAILABLE — collect manually",
                "equipment_notes": "NOT AVAILABLE — collect manually",
                "match_confidence": s["match_confidence"],
            })
    print(f"  Wrote {path} — 12 rows")


# ============================================================
# FILE 2: monthly_cups.csv
# ============================================================
def write_monthly_cups():
    path = os.path.join(OUTPUT_DIR, "monthly_cups.csv")
    fields = [
        "store_label", "store_id", "shop_no", "coned_account", "address",
        "year_month", "total_cups", "order_count", "operating_days",
        "daily_avg_cups", "revenue_usd",
    ]
    order_lk = build_order_lookup()
    cup_lk = build_cup_lookup()

    rows = []
    for s in STORES:
        if s["dept_id"] is None:
            continue
        # Find all months with data for this store
        months = sorted(set(
            ym for (sid, ym) in list(order_lk.keys()) + list(cup_lk.keys())
            if sid == s["dept_id"]
        ))
        for ym in months:
            od = order_lk.get((s["dept_id"], ym), {})
            cups = cup_lk.get((s["dept_id"], ym), 0)
            op_days = od.get("operating_days", 0)
            daily_avg = round(cups / op_days, 1) if op_days > 0 else 0
            rows.append({
                "store_label": s["label"],
                "store_id": s["dept_id"],
                "shop_no": s["shop_no"],
                "coned_account": s["coned_account"],
                "address": s["coned_address"],
                "year_month": ym,
                "total_cups": cups,
                "order_count": od.get("order_count", 0),
                "operating_days": op_days,
                "daily_avg_cups": daily_avg,
                "revenue_usd": od.get("revenue_usd", 0),
            })

    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  Wrote {path} — {len(rows)} rows")


# ============================================================
# FILE 3: store_operations.csv
# ============================================================
def write_store_operations():
    path = os.path.join(OUTPUT_DIR, "store_operations.csv")
    fields = [
        "store_label", "store_id", "shop_no", "address", "year_month",
        "days_with_staff", "avg_daily_staff", "avg_daily_scheduled_hours",
        "operating_hours_estimate", "equipment_list", "total_rated_watts",
        "renovation_dates", "temporary_closures",
    ]
    staff_lk = build_staff_lookup()

    rows = []
    for s in STORES:
        if s["dept_id"] is None:
            continue
        months = sorted(set(
            ym for (sid, ym) in staff_lk.keys()
            if sid == s["dept_id"]
        ))
        for ym in months:
            sd = staff_lk.get((s["dept_id"], ym), {})
            # Estimate operating hours: avg_daily_hours / avg_daily_staff ≈ shift length
            staff = sd.get("avg_daily_staff", 0)
            hours = sd.get("avg_daily_hours", 0)
            est_hours = round(hours / staff, 1) if staff > 0 else 0
            rows.append({
                "store_label": s["label"],
                "store_id": s["dept_id"],
                "shop_no": s["shop_no"],
                "address": s["coned_address"],
                "year_month": ym,
                "days_with_staff": sd.get("days_with_staff", 0),
                "avg_daily_staff": staff,
                "avg_daily_scheduled_hours": hours,
                "operating_hours_estimate": f"~{est_hours}h/day (staff-hours / headcount)",
                "equipment_list": "NOT AVAILABLE — collect manually",
                "total_rated_watts": "NOT AVAILABLE — collect manually",
                "renovation_dates": "NOT AVAILABLE — collect manually",
                "temporary_closures": "NOT AVAILABLE — collect manually",
            })

    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  Wrote {path} — {len(rows)} rows")


# ============================================================
# FILE 4: energy_analysis_store_metadata.csv (wide format)
# ============================================================
def write_wide_metadata():
    path = os.path.join(OUTPUT_DIR, "energy_analysis_store_metadata.csv")
    order_lk = build_order_lookup()
    cup_lk = build_cup_lookup()
    staff_lk = build_staff_lookup()

    # Determine all months present
    all_months = sorted(set(
        ym for (_, ym) in list(order_lk.keys()) + list(cup_lk.keys())
    ))

    # Build column headers
    base_fields = [
        "store_label", "shop_no", "coned_account", "address_coned",
        "address_internal", "store_name", "neighborhood", "open_date",
        "store_status", "area_sqft", "match_confidence",
    ]
    cup_fields = [f"cups_{ym.replace('-','_')}" for ym in all_months]
    rev_fields = [f"rev_{ym.replace('-','_')}" for ym in all_months]
    summary_fields = [
        "total_cups_all_months", "total_revenue_all_months",
        "total_operating_days", "avg_daily_cups_all_time",
        "avg_daily_staff_latest",
    ]
    fields = base_fields + cup_fields + rev_fields + summary_fields

    rows = []
    for s in STORES:
        row = {
            "store_label": s["label"],
            "shop_no": s["shop_no"] or "UNMATCHED",
            "coned_account": s["coned_account"],
            "address_coned": s["coned_address"],
            "address_internal": s["db_address"],
            "store_name": s["store_name"],
            "neighborhood": s["neighborhood"],
            "open_date": s["open_date"] or "NOT YET OPEN",
            "store_status": s["status"],
            "area_sqft": "NOT AVAILABLE",
            "match_confidence": s["match_confidence"],
        }

        total_cups = 0
        total_rev = 0
        total_days = 0

        for ym in all_months:
            cups = cup_lk.get((s["dept_id"], ym), 0) if s["dept_id"] else 0
            od = order_lk.get((s["dept_id"], ym), {}) if s["dept_id"] else {}
            rev = od.get("revenue_usd", 0)
            days = od.get("operating_days", 0)

            col_ym = ym.replace("-", "_")
            row[f"cups_{col_ym}"] = cups if cups > 0 else ""
            row[f"rev_{col_ym}"] = rev if rev > 0 else ""

            total_cups += cups
            total_rev += rev
            total_days += days

        row["total_cups_all_months"] = total_cups if total_cups > 0 else ""
        row["total_revenue_all_months"] = round(total_rev, 2) if total_rev > 0 else ""
        row["total_operating_days"] = total_days if total_days > 0 else ""
        row["avg_daily_cups_all_time"] = (
            round(total_cups / total_days, 1) if total_days > 0 else ""
        )

        # Latest staffing
        if s["dept_id"]:
            staff_months = sorted(
                [ym for (sid, ym) in staff_lk if sid == s["dept_id"]]
            )
            if staff_months:
                latest = staff_lk[(s["dept_id"], staff_months[-1])]
                row["avg_daily_staff_latest"] = latest["avg_daily_staff"]
            else:
                row["avg_daily_staff_latest"] = ""
        else:
            row["avg_daily_staff_latest"] = ""

        rows.append(row)

    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  Wrote {path} — {len(rows)} rows, {len(all_months)} months of data")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("Generating ConEdison energy analysis CSVs...\n")
    write_store_info()
    write_monthly_cups()
    write_store_operations()
    write_wide_metadata()
    print("\nDone. All files in:", OUTPUT_DIR)
