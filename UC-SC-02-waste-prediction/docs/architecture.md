# UC-SC-02: Waste Prediction & Reduction — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     UC-SC-02 Pipeline Architecture                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────┐     ┌─────────────────┐     ┌───────────────────┐│
│  │   Source Databases    │     │   Orchestrator   │     │  Analytics DB     ││
│  │   (8 MySQL servers)  │────▶│   (Python CLI)   │────▶│  (dbatest/test)   ││
│  └──────────────────────┘     └────────┬────────┘     └───────┬───────────┘│
│                                        │                      │             │
│                                        │              ┌───────▼───────────┐│
│                                        │              │ 7 Stored Procs    ││
│                                        └─────────────▶│ (SQL transforms)  ││
│                                                       └───────┬───────────┘│
│                                                               │             │
│                                              ┌────────────────▼────────────┐│
│                                              │  Grafana Dashboard          ││
│                                              │  Waste Command Center       ││
│                                              └─────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Phase 1: Extraction (Python Orchestrator → Staging Tables)

```
┌─────────────────────┐    ┌────────────────────────────────┐
│ scm-shopstock       │───▶│ tmp_stock_changes               │
│ (DOW-partitioned)   │    │ (consumption, transfers)        │
└─────────────────────┘    └────────────────────────────────┘

┌─────────────────────┐    ┌────────────────────────────────┐
│ opqualitycontrol    │───▶│ tmp_abandon_tasks               │
│                     │───▶│ tmp_expiry_prints               │
│                     │───▶│ tmp_shelf_life_config            │
└─────────────────────┘    └────────────────────────────────┘

┌─────────────────────┐    ┌────────────────────────────────┐
│ opproduction        │───▶│ tmp_production + tmp_commodity   │
└─────────────────────┘    └────────────────────────────────┘

┌─────────────────────┐    ┌────────────────────────────────┐
│ ireplenishment      │───▶│ tmp_predictions                 │
└─────────────────────┘    └────────────────────────────────┘

┌─────────────────────┐    ┌────────────────────────────────┐
│ pubdm + opshop +    │───▶│ tmp_goods + tmp_stores +        │
│ scmcommodity        │    │ tmp_formula                     │
└─────────────────────┘    └────────────────────────────────┘
```

### Phase 2: Transformation (Stored Procedures → Analytics Tables)

```
Step 1: sp_build_consumption_features
  tmp_stock_changes + tmp_predictions ──▶ waste_consumption_daily
  (consumption extraction, rolling averages, DOW patterns, prediction join)

Step 2: sp_compute_waste_landscape
  tmp_abandon_tasks + tmp_expiry_prints + tmp_shelf_life_config ──▶
  waste_daily_detail + waste_shelf_life_config

Step 3: sp_compute_consumption_forecast
  waste_consumption_daily (self-update) ──▶ v1_forecast, v1_forecast_error

Step 4: sp_compute_batch_risk_scores
  tmp_expiry_prints + waste_consumption_daily ──▶ waste_batch_risk_score

Step 5: sp_compute_transfer_recommendations
  waste_batch_risk_score + waste_consumption_daily ──▶ waste_transfer_recommendations

Step 6: sp_compute_waste_summary
  waste_daily_detail + waste_consumption_daily + waste_batch_risk_score ──▶ waste_summary

Step 7: sp_check_waste_alerts
  waste_daily_detail + waste_batch_risk_score + waste_consumption_daily ──▶ waste_alerts
```

## Execution Modes

### 1. Python Orchestrator (Full Pipeline)

```bash
# Daily run — all 15 steps (7 extraction + 8 SP calls)
python run_waste_pipeline.py --date 2026-02-17

# Backfill — range processing with chunked SP calls
python run_waste_pipeline.py --start-date 2025-11-20 --end-date 2026-02-17
```

The orchestrator:
1. Connects to 8 source databases via PyMySQL
2. Extracts data into 10 staging tables (TRUNCATE + INSERT)
3. Calls 7 stored procedures in dependency order
4. Logs each step to `waste_pipeline_run_log`

### 2. MySQL Event (SP-Only Daily Refresh)

```sql
-- Runs daily at 06:00 UTC (01:00 EST)
-- Calls sp_waste_daily_refresh(yesterday)
-- Assumes staging tables already populated
CREATE EVENT test.evt_waste_daily_refresh
    ON SCHEDULE EVERY 1 DAY STARTS '... 06:00:00'
```

### 3. Manual SP Execution

```sql
-- Run individual SPs for debugging
CALL test.sp_build_consumption_features('2026-02-17', '2026-02-17');
CALL test.sp_compute_waste_landscape('2026-02-17', '2026-02-17');
CALL test.sp_compute_consumption_forecast('2026-02-17', '2026-02-17');
CALL test.sp_compute_batch_risk_scores('2026-02-17');
CALL test.sp_compute_transfer_recommendations('2026-02-17');
CALL test.sp_compute_waste_summary('2026-02-17');
CALL test.sp_check_waste_alerts('2026-02-17');

-- Or call the master SP
CALL test.sp_waste_daily_refresh('2026-02-17');
```

## Stored Procedure Signatures

| SP | Parameters | Type |
|----|-----------|------|
| `sp_build_consumption_features` | (p_start_date DATE, p_end_date DATE) | Range |
| `sp_compute_waste_landscape` | (p_start_date DATE, p_end_date DATE) | Range |
| `sp_compute_consumption_forecast` | (p_start_date DATE, p_end_date DATE) | Range |
| `sp_compute_batch_risk_scores` | (p_score_date DATE) | Single |
| `sp_compute_transfer_recommendations` | (p_recommendation_date DATE) | Single |
| `sp_compute_waste_summary` | (p_summary_date DATE) | Single |
| `sp_check_waste_alerts` | (p_alert_date DATE) | Single |
| `sp_waste_daily_refresh` | (p_target_date DATE) | Master |

## Idempotency

All SPs are idempotent via DELETE-then-INSERT (or REPLACE INTO) for the target date:

| SP | Strategy |
|----|----------|
| sp_build_consumption_features | DELETE FROM waste_consumption_daily WHERE date BETWEEN start AND end |
| sp_compute_waste_landscape | DELETE FROM waste_daily_detail WHERE date BETWEEN start AND end |
| sp_compute_consumption_forecast | UPDATE existing rows (no new inserts) |
| sp_compute_batch_risk_scores | DELETE FROM waste_batch_risk_score WHERE score_date = date |
| sp_compute_transfer_recommendations | DELETE FROM waste_transfer_recommendations WHERE date = date |
| sp_compute_waste_summary | DELETE FROM waste_summary WHERE period includes date |
| sp_check_waste_alerts | Dedup check: NOT EXISTS for same type+entity+date |

## Source Database Inventory

| Server | Database | Key Tables | Data |
|--------|----------|------------|------|
| aws-luckyus-scm-shopstock-rw | scm-shopstock | t_stock_shop_change_record_{dow} | Stock movements (DOW-partitioned) |
| aws-luckyus-opqualitycontrol-rw | opqualitycontrol | t_goods_abandon_task_form, t_expiry_print_log, t_goods_expiry_config | Disposal, expiry labels, shelf-life config |
| aws-luckyus-opproduction-rw | opproduction | t_production, t_production_commodity_detail | Production orders + ingredients |
| aws-luckyus-ireplenishment-rw | ireplenishment | t_goods_vlt_day_forecast | Demand predictions |
| aws-luckyus-pubdm-rw | pubdm | t_mdm_goods | Product master data |
| aws-luckyus-opshop-rw | opshop | t_shop_info | Store master data |
| aws-luckyus-scmcommodity-rw | scmcommodity | t_formula_spu | BOM/recipes |
| aws-luckyus-salesorder-rw | salesorder | (future: order data) | Sales context |

**Analytics target**: aws-luckyus-dbatest-rw → schema `test`

## 10 Active Manhattan Stores

| Store ID | Name |
|----------|------|
| 1127 | 8th Ave & Broadway |
| 1128 | 28th St & 6th Ave |
| 1140 | 100 Maiden Lane |
| 1141 | 54th St & 8th Ave |
| 20008 | JFK Terminal 1 |
| 20010 | Midtown East |
| 20011 | Financial District |
| 20027 | Union Square |
| 20031 | Herald Square |
| 20032 | Columbus Circle |

## Transfer Distance Matrix

8 bidirectional pairs (16 directional entries) within 0.5 miles:

```
8th & Broadway ↔ Herald Square     (0.4 mi)
8th & Broadway ↔ Union Square      (0.5 mi)
28th & 6th    ↔ Herald Square      (0.3 mi)
28th & 6th    ↔ Union Square       (0.4 mi)
100 Maiden    ↔ Financial District (0.3 mi)
Midtown East  ↔ 54th & 8th        (0.5 mi)
Herald Square ↔ Union Square       (0.5 mi)
Columbus Circ ↔ 54th & 8th        (0.4 mi)
```

## Forecast Model v1

**Type**: Enhanced Moving Average (rule-based, no ML)

**Inputs**:
- `same_dow_4wk_avg` — Same day-of-week average over past 4 weeks (weight: 0.30)
- `consumption_7d_avg` — 7-day rolling average (weight: 0.25)
- `predicted_demand` — ireplenishment algorithm output (weight: 0.20)
- `consumption_14d_avg` — 14-day rolling average (weight: 0.15)
- `consumption_30d_avg` — 30-day rolling average (weight: 0.10)

**NULL handling**: If a component is NULL, its weight is redistributed proportionally to non-NULL components.

**Safety multipliers** (reduce forecast for perishables to avoid over-ordering):
- ULTRA_SHORT (<24h): × 0.95
- SHORT (24-72h): × 0.97
- MEDIUM (3-14d): × 1.00
- LONG (14d+): × 1.00

**Target MAPE**: <25% (baseline: 37.8%)

## Risk Scoring Model

**4-component weighted score (0-100)**:

| Component | Weight | Description | Scoring |
|-----------|--------|-------------|---------|
| Expiry urgency | 0.40 | Time to expiry | ≤4h=1.0, ≤8h=0.8, ≤24h=0.5, ≤48h=0.3, else=0.1 |
| Excess inventory | 0.30 | Stock vs forecast | (stock - forecast) / stock, capped [0,1] |
| Demand volatility | 0.20 | CV of demand | stddev / avg, capped at 1.0 |
| Shelf-life penalty | 0.10 | Perishability | ULTRA_SHORT=1.0, SHORT=0.6, MEDIUM=0.3, LONG=0.1 |

## Alert System

5 rules evaluated by `sp_check_waste_alerts`:

| Rule | Type | Condition | Action |
|------|------|-----------|--------|
| 1 | CRITICAL | Store waste rate > 8% | Emergency review |
| 2 | WARNING | Store waste rate 5-8% | Review expiry schedule |
| 3 | CRITICAL | >10 CRITICAL batches at store | Emergency transfers/discounts |
| 4 | BIAS | Forecast bias >20% for 3+ days | Investigate forecast inputs |
| 5 | TREND | 7d waste > 30d waste × 1.3 | Root cause analysis |

Deduplication: Each alert type+entity+date combination fires at most once.

## Monitoring & Observability

### Pipeline Health
- `waste_pipeline_run_log` tracks every step with status, duration, row counts
- Master SP reports SUCCESS/PARTIAL/FAILED with step breakdown
- Verification queries (tests/verification_queries.sql) validate output quality

### Dashboard
- Grafana Waste Command Center with 12 panels
- Data source: MySQL → `aws-luckyus-dbatest-rw` schema `test`
- Refresh: auto 5-minute, manual available
- Key metrics: waste rate trend, risk distribution, forecast accuracy, alerts, transfers

### Success Criteria

| Metric | Baseline | Target |
|--------|----------|--------|
| Waste rate (% of COGS) | 5-8% | 2-4% |
| Consumption forecast MAPE | 37.8% | <25% |
| Monthly waste cost reduction | $0 | $3.7K-$5.5K |
| CRITICAL alerts actioned within 2h | N/A | >90% |
| Transfer recommendations executed | 0 | >5/week |
| Dashboard data freshness | N/A | <2h lag |

## Dependencies

### Python
- `pymysql` — MySQL connections
- `python-dotenv` — Environment variable loading
- Standard library: `argparse`, `datetime`, `logging`, `uuid`, `os`

### MySQL
- MySQL 8.0+ (for CTEs, window functions, JSON type)
- `event_scheduler = ON` for daily auto-refresh
- EVENT privilege on `test` schema

### Infrastructure
- Network access from orchestrator host to all 8 source DB servers + analytics server
- Grafana with MySQL data source pointing to `aws-luckyus-dbatest-rw`
