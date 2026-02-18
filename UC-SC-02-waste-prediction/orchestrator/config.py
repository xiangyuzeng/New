"""
UC-SC-02: Waste Prediction & Reduction — Configuration
Store config, distance matrix, thresholds, and pipeline settings.
"""

# ─── Active Manhattan Stores ────────────────────────────────────────────────
ACTIVE_STORES = (1127, 1128, 1140, 1141, 20008, 20010, 20011, 20027, 20031, 20032)

STORE_NAMES = {
    1127:  '8th Ave & Broadway',
    1128:  '28th St & 6th Ave',
    1140:  '100 Maiden Lane',
    1141:  '54th St & 8th Ave',
    20008: 'JFK Terminal 1',
    20010: 'Midtown East',
    20011: 'Financial District',
    20027: 'Union Square',
    20031: 'Herald Square',
    20032: 'Columbus Circle',
}

# ─── Store Distance Matrix (miles, walking distance estimates) ──────────────
# Only pairs within TRANSFER_MAX_DISTANCE are transfer-eligible.
# Key: (source_store_id, dest_store_id) → distance in miles
STORE_DISTANCES = {
    # 8th & Broadway ↔ Herald Square (~0.4 mi)
    (1127, 20031): 0.4, (20031, 1127): 0.4,
    # 8th & Broadway ↔ Union Square (~0.5 mi)
    (1127, 20027): 0.5, (20027, 1127): 0.5,
    # 28th & 6th ↔ Herald Square (~0.3 mi)
    (1128, 20031): 0.3, (20031, 1128): 0.3,
    # 28th & 6th ↔ Union Square (~0.4 mi)
    (1128, 20027): 0.4, (20027, 1128): 0.4,
    # 100 Maiden ↔ Financial District (~0.3 mi)
    (1140, 20011): 0.3, (20011, 1140): 0.3,
    # Midtown East ↔ 54th & 8th (~0.5 mi)
    (20010, 1141): 0.5, (1141, 20010): 0.5,
    # Herald Square ↔ Union Square (~0.5 mi)
    (20031, 20027): 0.5, (20027, 20031): 0.5,
    # Columbus Circle ↔ 54th & 8th (~0.4 mi)
    (20032, 1141): 0.4, (1141, 20032): 0.4,
}

# ─── Transfer Settings ──────────────────────────────────────────────────────
TRANSFER_MAX_DISTANCE = 0.5       # miles — max walking distance for transfers
TRANSFER_COST_PER_TRIP = 5.00     # $ — estimated labor/logistics per transfer
TRANSFER_MIN_NET_BENEFIT = 2.00   # $ — minimum net benefit to recommend transfer
TRANSIT_SHRINKAGE_PCT = 0.06      # 6% volume loss between transfer out/in

# ─── Shelf-Life Tier Boundaries (hours) ─────────────────────────────────────
SHELF_LIFE_TIERS = {
    'ULTRA_SHORT': (0, 24),       # < 24 hours (fresh milk, opened syrups)
    'SHORT':       (24, 72),      # 1-3 days (thawed ingredients)
    'MEDIUM':      (72, 336),     # 3-14 days (sealed dairy)
    'LONG':        (336, 99999),  # 14+ days (beans, dry goods)
}

# Forecast safety multipliers by shelf-life tier (slight under-forecast for perishables)
SHELF_LIFE_SAFETY_MULTIPLIER = {
    'ULTRA_SHORT': 0.95,
    'SHORT':       0.97,
    'MEDIUM':      1.00,
    'LONG':        1.00,
}

# ─── Risk Score Weights ─────────────────────────────────────────────────────
RISK_WEIGHTS = {
    'expiry_urgency':    0.40,
    'excess_inventory':  0.30,
    'volatility':        0.20,
    'shelf_tier_penalty': 0.10,
}

RISK_TIER_THRESHOLDS = {
    'CRITICAL': 80,
    'HIGH':     60,
    'MEDIUM':   40,
    'LOW':      0,
}

# ─── Forecast Model v1 Weights ──────────────────────────────────────────────
FORECAST_WEIGHTS = {
    'same_dow_4wk_avg':    0.30,
    'consumption_7d_avg':  0.25,
    'existing_prediction': 0.20,
    'consumption_14d_avg': 0.15,
    'consumption_30d_avg': 0.10,
}

# ─── Alert Thresholds ───────────────────────────────────────────────────────
ALERT_THRESHOLDS = {
    'waste_rate_critical':     0.08,   # 8% — CRITICAL alert
    'waste_rate_warning':      0.05,   # 5% — WARNING alert
    'expiry_surge_count':      10,     # >10 CRITICAL batches at one store
    'forecast_bias_pct':       0.20,   # 20% bias for 3+ consecutive days
    'waste_trend_multiplier':  1.30,   # 7d rolling > 30d rolling * 1.3
    'forecast_bias_days':      3,      # consecutive days before BIAS alert
}

# ─── Pipeline Configuration ─────────────────────────────────────────────────
PIPELINE_NAME = 'UC-SC-02-waste-prediction'

PIPELINE_STEPS = [
    'extract_stock_changes',
    'extract_disposal',
    'extract_expiry_labels',
    'extract_shelf_life_config',
    'extract_production',
    'extract_predictions',
    'extract_master_data',
    'call_sp_consumption_daily',
    'call_sp_consumption_features',
    'call_sp_consumption_forecast',
    'call_sp_waste_landscape',
    'call_sp_risk_scoring',
    'call_sp_transfer_recs',
    'call_sp_waste_summary',
    'call_sp_waste_alerts',
]

# Steps that extract from source databases (Steps 1-7)
EXTRACTION_STEPS = PIPELINE_STEPS[:7]

# Steps that call stored procedures on analytics DB (Steps 8-15)
SP_STEPS = PIPELINE_STEPS[7:]

# ─── Source Database Servers ─────────────────────────────────────────────────
SOURCE_SERVERS = {
    'scm_shopstock':     'aws-luckyus-scm-shopstock-rw',
    'opqualitycontrol':  'aws-luckyus-opqualitycontrol-rw',
    'opproduction':      'aws-luckyus-opproduction-rw',
    'ireplenishment':    'aws-luckyus-ireplenishment-rw',
    'pubdm':             'aws-luckyus-pubdm-rw',
    'opshop':            'aws-luckyus-opshop-rw',
    'scm_commodity':     'aws-luckyus-scmcommodity-rw',
    'sales_order':       'aws-luckyus-salesorder-rw',
}

ANALYTICS_SERVER = 'aws-luckyus-dbatest-rw'
ANALYTICS_SCHEMA = 'test'

# ─── Stock Change Reason Codes ───────────────────────────────────────────────
# Consumption events (validated in UC-SC-01)
CONSUMPTION_REASON_CODES = ('025', '1001', '1002')

# Transfer events
TRANSFER_OUT_REASON_CODE = '1006'
TRANSFER_IN_REASON_CODE = '1009'
TRANSFER_REASON_TYPE = 2006

# ─── Day-of-Week Table Mapping for scm-shopstock ────────────────────────────
# scm-shopstock uses day-partitioned tables: t_stock_shop_change_record_{DOW}
DOW_TABLE_MAP = {
    0: 't_stock_shop_change_record_mon',   # Monday
    1: 't_stock_shop_change_record_tue',   # Tuesday
    2: 't_stock_shop_change_record_wed',   # Wednesday
    3: 't_stock_shop_change_record_thu',   # Thursday
    4: 't_stock_shop_change_record_fri',   # Friday
    5: 't_stock_shop_change_record_sat',   # Saturday
    6: 't_stock_shop_change_record_sun',   # Sunday
}

# ─── Default Pipeline Settings ───────────────────────────────────────────────
DEFAULT_BACKFILL_DAYS = 90
DEFAULT_BATCH_SIZE = 10000
PIPELINE_TIMEOUT_SECONDS = 3600   # 1 hour max per pipeline run
SP_TIMEOUT_SECONDS = 600          # 10 minutes max per stored procedure
