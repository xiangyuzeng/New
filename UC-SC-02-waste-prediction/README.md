# UC-SC-02: Waste Prediction & Reduction

## Overview
Waste prediction and reduction system for 11 Manhattan Luckin Coffee stores, targeting 2-3% COGS reduction (~$44K-$66K/year) by reducing waste from 5-8% to 2-4% of COGS.

## Architecture
- **Pattern**: Replicates UC-SC-01 — MySQL-based ETL pipeline
- **Sources**: 8 databases (scm-shopstock, opqualitycontrol, opproduction, ireplenishment, pub-dm, opshop, scm-commodity, sales-order)
- **Target**: `aws-luckyus-dbatest-rw` → schema `test`
- **Visualization**: Grafana Waste Command Center dashboard
- **Orchestration**: Python + stored procedures

## Directory Structure
```
UC-SC-02-waste-prediction/
├── README.md
├── docs/
│   ├── data_dictionary.md
│   └── architecture.md
├── sql/
│   ├── 01_schema_discovery.sql        # Source table documentation
│   ├── 02_create_analytics_schema.sql # DDL for 8 analytics tables
│   ├── 03_waste_landscape.sql         # SP: waste detail computation
│   ├── 04_consumption_features.sql    # SP: feature engineering
│   ├── 05_consumption_forecast.sql    # SP: forecast model v1
│   ├── 06_risk_scoring.sql            # SP: batch risk scores
│   ├── 07_transfer_optimization.sql   # SP: cross-store transfers
│   ├── 08_waste_alerts.sql            # SP: alert threshold checks
│   ├── 09_waste_summary.sql           # SP: aggregate summaries
│   └── 10_daily_refresh.sql           # Master SP + MySQL EVENT
├── orchestrator/
│   ├── run_waste_pipeline.py          # Main Python orchestrator
│   ├── config.py                      # Store config, distances, thresholds
│   └── .env.example                   # DB connection env vars
├── dashboards/
│   ├── waste_command_center.json      # Grafana dashboard JSON
│   └── WasteCommandCenter.jsx         # React/Recharts component
└── tests/
    ├── test_pipeline.py               # Pipeline unit tests
    └── verification_queries.sql       # V1-V8 verification queries
```

## Quick Start
```bash
# 1. Create analytics tables
mysql -h aws-luckyus-dbatest-rw < sql/02_create_analytics_schema.sql

# 2. Configure environment
cp orchestrator/.env.example orchestrator/.env
# Edit .env with actual credentials

# 3. Run initial backfill (90 days)
python orchestrator/run_waste_pipeline.py --start-date 2025-11-20 --end-date 2026-02-17

# 4. Run daily pipeline
python orchestrator/run_waste_pipeline.py --date 2026-02-17

# 5. Import Grafana dashboard
# Import dashboards/waste_command_center.json into Grafana
```

## CLI Usage
```bash
python run_waste_pipeline.py --date 2026-02-17              # Single date
python run_waste_pipeline.py --start-date 2026-02-01 --end-date 2026-02-17  # Range
python run_waste_pipeline.py --setup                         # Create tables only
python run_waste_pipeline.py --dry-run                       # Validate without writing
python run_waste_pipeline.py --step extract_disposal          # Single step
```

## Pipeline Steps (15)
1. `extract_stock_changes` — scm-shopstock → tmp_stock_changes
2. `extract_disposal` — opqualitycontrol → tmp_abandon_tasks
3. `extract_expiry_labels` — opqualitycontrol → tmp_expiry_prints
4. `extract_shelf_life_config` — opqualitycontrol → tmp_shelf_life_config
5. `extract_production` — opproduction → tmp_production, tmp_commodity
6. `extract_predictions` — ireplenishment → tmp_predictions
7. `extract_master_data` — pub-dm, opshop, scm-commodity → tmp_goods, tmp_stores, tmp_formula
8. `call_sp_consumption_daily` — Compute daily consumption
9. `call_sp_consumption_features` — Build forecasting features
10. `call_sp_consumption_forecast` — Run forecast model v1
11. `call_sp_waste_landscape` — Compute waste detail
12. `call_sp_risk_scoring` — Batch risk scores
13. `call_sp_transfer_recs` — Transfer recommendations
14. `call_sp_waste_summary` — Aggregate summaries
15. `call_sp_waste_alerts` — Check alert thresholds

## Success Criteria
| Metric | Baseline | Target |
|--------|----------|--------|
| Waste rate (% of COGS) | 5-8% | 2-4% |
| Consumption forecast MAPE | 37.8% | <25% |
| Waste cost reduction (monthly) | $0 | $3.7K-$5.5K/mo |
| CRITICAL batch alerts actioned | N/A | >90% within 2h |
| Transfer recommendations | 0 | >5/week executed |
| Dashboard data freshness | N/A | <2h lag |
