# UC-SC-02: Waste Prediction & Reduction — Data Dictionary

## Overview

18 tables in schema `test` on `aws-luckyus-dbatest-rw`:
- **8 analytics tables** — persistent output of stored procedures
- **10 staging tables** — temporary, populated by Python orchestrator each run

---

## Analytics Tables

### 1. `waste_daily_detail`

Row-level waste tracking per (date, store, SKU). Primary output of `sp_compute_waste_landscape`.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment |
| `waste_date` | DATE | Waste event date |
| `shop_dept_id` | BIGINT | Store ID (FK to tmp_stores.dept_id) |
| `shop_name` | VARCHAR(100) | Denormalized store name |
| `goods_code` | VARCHAR(32) | Goods code (GS-level) |
| `goods_name` | VARCHAR(200) | Denormalized goods name |
| `large_class_name` | VARCHAR(100) | Product category |
| `shelf_life_tier` | ENUM | ULTRA_SHORT / SHORT / MEDIUM / LONG |
| `shelf_life_hours` | INT | Shelf life in hours |
| `storage_type` | ENUM | NORMAL / FROZEN / REFRIGERATED |
| `waste_qty_normal` | DECIMAL(12,2) | Room-temperature waste qty |
| `waste_qty_frozen` | DECIMAL(12,2) | Frozen waste qty |
| `waste_qty_refrigerated` | DECIMAL(12,2) | Refrigerated waste qty |
| `waste_qty_total` | DECIMAL(12,2) | Sum of all waste |
| `unit_cost` | DECIMAL(10,4) | Estimated unit cost ($) |
| `waste_cost` | DECIMAL(12,2) | waste_qty_total × unit_cost |
| `consumption_qty` | DECIMAL(12,2) | Same-day consumption (for waste rate) |
| `waste_pct` | DECIMAL(10,4) | waste / (consumption + waste) |
| `abandon_task_ids` | TEXT | Source disposal task IDs |
| `expiry_print_count` | INT | Expiry labels printed that day |
| `computed_at` | DATETIME | Computation timestamp |

**Indexes**: (waste_date, shop_dept_id), (waste_date, goods_code), (shop_dept_id, goods_code), (waste_date), (shelf_life_tier)

---

### 2. `waste_consumption_daily`

Daily consumption actuals and forecast features per (date, store, SKU). Foundation for forecasting model.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment |
| `consumption_date` | DATE | Consumption date |
| `shop_dept_id` | BIGINT | Store ID |
| `goods_code` | VARCHAR(32) | Goods code |
| `actual_consumption` | DECIMAL(12,2) | Actual consumed qty (from stock changes where reason_code IN 025,1001,1002 AND adjust < 0) |
| `day_of_week` | TINYINT | 1=Mon through 7=Sun |
| `is_weekend` | BOOLEAN | Weekend flag |
| `consumption_7d_avg` | DECIMAL(12,2) | 7-day rolling average |
| `consumption_7d_stddev` | DECIMAL(12,2) | 7-day rolling std deviation |
| `consumption_14d_avg` | DECIMAL(12,2) | 14-day rolling average |
| `consumption_30d_avg` | DECIMAL(12,2) | 30-day rolling average |
| `same_dow_4wk_avg` | DECIMAL(12,2) | Same day-of-week 4-week average |
| `consumption_trend_7d` | DECIMAL(10,4) | (7d_avg - 14d_avg) / 14d_avg |
| `predicted_demand` | DECIMAL(12,2) | ireplenishment algorithm prediction |
| `predicted_order_qty` | DECIMAL(12,2) | ireplenishment order suggestion |
| `forecast_error` | DECIMAL(12,2) | predicted - actual |
| `abs_pct_error` | DECIMAL(10,4) | Absolute percentage error |
| `v1_forecast` | DECIMAL(12,2) | Forecast model v1 output |
| `v1_forecast_error` | DECIMAL(12,2) | v1 forecast - actual |
| `v1_abs_pct_error` | DECIMAL(10,4) | v1 absolute percentage error |
| `computed_at` | DATETIME | Computation timestamp |

**Unique index**: (consumption_date, shop_dept_id, goods_code)

**Forecast Model v1 Formula**:
```
v1_forecast = (0.30 × same_dow_4wk_avg
             + 0.25 × consumption_7d_avg
             + 0.20 × predicted_demand
             + 0.15 × consumption_14d_avg
             + 0.10 × consumption_30d_avg)
             × shelf_life_safety_multiplier
```

Safety multipliers: ULTRA_SHORT=0.95, SHORT=0.97, MEDIUM=1.00, LONG=1.00

---

### 3. `waste_shelf_life_config`

Materialized shelf-life configuration per SKU. Updated by `sp_compute_waste_landscape`.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment |
| `goods_code` | VARCHAR(32) UNIQUE | Goods code |
| `goods_name` | VARCHAR(200) | Product name |
| `large_class_name` | VARCHAR(100) | Category |
| `open_expiry_hours` | INT | Open-package expiry (hours) |
| `container_expiry_hours` | INT | Container storage expiry (hours) |
| `thaw_expiry_hours` | INT | Thaw/unfreeze expiry (hours) |
| `min_expiry_hours` | INT | Shortest applicable expiry |
| `shelf_life_tier` | ENUM | Tier classification |
| `is_active` | BOOLEAN | Active flag |
| `synced_at` | DATETIME | Last sync time |

**Tier boundaries**: ULTRA_SHORT: <24h, SHORT: 24-72h, MEDIUM: 72-336h, LONG: >336h

---

### 4. `waste_batch_risk_score`

Per-batch expiry risk scoring. Computed by `sp_compute_batch_risk_scores`.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment |
| `score_date` | DATE | Score computation date |
| `shop_dept_id` | BIGINT | Store ID |
| `goods_code` | VARCHAR(32) | Goods code |
| `batch_id` | VARCHAR(64) | Batch/collection code |
| `receipt_time` | DATETIME | Receipt timestamp |
| `expiry_time` | DATETIME | Expiry timestamp |
| `hours_remaining` | DECIMAL(8,1) | Hours until expiry |
| `current_stock_qty` | DECIMAL(12,2) | Estimated on-hand qty |
| `forecast_consumption_24h` | DECIMAL(12,2) | Forecasted next-24h consumption |
| `forecast_consumption_48h` | DECIMAL(12,2) | Forecasted next-48h consumption |
| `expiry_urgency_score` | DECIMAL(5,2) | Component 1 (0-1) |
| `excess_inventory_score` | DECIMAL(5,2) | Component 2 (0-1) |
| `volatility_score` | DECIMAL(5,2) | Component 3 (0-1) |
| `shelf_tier_penalty_score` | DECIMAL(5,2) | Component 4 (0-1) |
| `risk_score` | DECIMAL(5,2) | Final score 0-100 |
| `risk_tier` | ENUM | LOW / MEDIUM / HIGH / CRITICAL |
| `recommended_action` | ENUM | HOLD / PROMOTE / TRANSFER / DISCOUNT / DISPOSE |
| `transfer_candidate_store` | BIGINT | Suggested transfer destination |
| `computed_at` | DATETIME | Computation timestamp |

**Risk Score Formula**:
```
risk_score = 100 × (0.40 × expiry_urgency
                   + 0.30 × excess_inventory
                   + 0.20 × volatility
                   + 0.10 × shelf_tier_penalty)
```

| Tier | Score Range |
|------|-------------|
| CRITICAL | ≥ 80 |
| HIGH | 60–79 |
| MEDIUM | 40–59 |
| LOW | < 40 |

**Action Assignment Logic**:
| Condition | Action |
|-----------|--------|
| CRITICAL + hours < 4 | DISPOSE |
| CRITICAL + hours ≥ 4 | TRANSFER |
| HIGH | PROMOTE |
| MEDIUM + hours < 24 | DISCOUNT |
| Default | HOLD |

---

### 5. `waste_transfer_recommendations`

Cross-store transfer optimization. Computed by `sp_compute_transfer_recommendations`.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment |
| `recommendation_date` | DATE | Recommendation date |
| `source_store_id` | BIGINT | Source store (excess) |
| `source_store_name` | VARCHAR(100) | Source store name |
| `dest_store_id` | BIGINT | Destination store (deficit) |
| `dest_store_name` | VARCHAR(100) | Destination store name |
| `goods_code` | VARCHAR(32) | Goods code |
| `goods_name` | VARCHAR(200) | Product name |
| `transfer_qty` | DECIMAL(12,2) | Recommended qty = MIN(excess, deficit) |
| `source_excess_qty` | DECIMAL(12,2) | Stock - forecast at source |
| `dest_deficit_qty` | DECIMAL(12,2) | Forecast - stock at destination |
| `source_hours_to_expiry` | DECIMAL(8,1) | Hours remaining at source (min 8) |
| `source_risk_score` | DECIMAL(5,2) | Source batch risk score |
| `waste_savings_est` | DECIMAL(10,2) | transfer_qty × $1.50 |
| `transfer_cost_est` | DECIMAL(10,2) | $5.00 per trip |
| `net_benefit` | DECIMAL(10,2) | savings − cost (min $2.00) |
| `status` | ENUM | PENDING / APPROVED / EXECUTED / EXPIRED / CANCELLED |
| `computed_at` | DATETIME | Computation timestamp |

**Constraints**: Max distance 0.5 miles, min net benefit $2.00, min 8h to expiry.

---

### 6. `waste_summary`

Aggregated waste metrics by period and dimension. Computed by `sp_compute_waste_summary`.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment |
| `period_type` | ENUM | DAILY / WEEKLY / MONTHLY / ROLLING_7D / ROLLING_30D |
| `period_start` | DATE | Period start date |
| `period_end` | DATE | Period end date |
| `dimension_type` | ENUM | OVERALL / STORE / PRODUCT / CATEGORY / SHELF_TIER / DOW / STORAGE_TYPE |
| `dimension_value` | VARCHAR(100) | Dimension key |
| `dimension_name` | VARCHAR(200) | Dimension display name |
| `total_waste_qty` | DECIMAL(14,2) | Aggregated waste qty |
| `total_waste_cost` | DECIMAL(14,2) | Aggregated waste cost ($) |
| `total_consumption` | DECIMAL(14,2) | Aggregated consumption |
| `waste_rate` | DECIMAL(10,4) | waste / (consumption + waste) |
| `waste_mape` | DECIMAL(10,4) | Consumption forecast MAPE |
| `waste_wmape` | DECIMAL(10,4) | Weighted MAPE |
| `waste_bias` | DECIMAL(12,4) | Forecast bias (+ = over-forecast) |
| `batches_critical` | INT | CRITICAL risk batch count |
| `batches_high` | INT | HIGH risk batch count |
| `transfers_recommended` | INT | Transfer recommendations |
| `transfers_executed` | INT | Executed transfers |
| `transfer_savings` | DECIMAL(12,2) | Transfer savings ($) |
| `record_count` | INT | Source detail record count |
| `sku_count` | INT | Distinct SKU count |
| `computed_at` | DATETIME | Computation timestamp |

---

### 7. `waste_alerts`

Threshold-based alerting for waste anomalies. Computed by `sp_check_waste_alerts`.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment |
| `alert_timestamp` | DATETIME | Alert creation time |
| `alert_date` | DATE | Alert date |
| `alert_type` | ENUM | CRITICAL / WARNING / BIAS / COVERAGE / TREND / EXPIRY_SURGE |
| `entity_type` | ENUM | STORE / PRODUCT / CATEGORY / BATCH / SYSTEM |
| `entity_id` | VARCHAR(50) | Entity identifier |
| `entity_name` | VARCHAR(200) | Entity display name |
| `metric_name` | VARCHAR(50) | Metric that breached threshold |
| `metric_value` | DECIMAL(10,4) | Current metric value |
| `threshold_value` | DECIMAL(10,4) | Threshold breached |
| `baseline_value` | DECIMAL(10,4) | Historical baseline |
| `description` | TEXT | Human-readable description |
| `recommended_action` | TEXT | Suggested remediation |
| `is_acknowledged` | BOOLEAN | Acknowledgement flag |
| `acknowledged_by` | VARCHAR(100) | Who acknowledged |
| `acknowledged_at` | DATETIME | Ack timestamp |

**Alert Rules**:

| # | Type | Condition | Threshold |
|---|------|-----------|-----------|
| 1 | CRITICAL | Store daily waste rate | > 8% |
| 2 | WARNING | Store daily waste rate | > 5% (≤ 8%) |
| 3 | CRITICAL | CRITICAL risk batches at store | > 10 |
| 4 | BIAS | Forecast bias 3+ consecutive days | > 20% |
| 5 | TREND | 7d rolling waste vs 30d rolling | > 30% increase |

---

### 8. `waste_pipeline_run_log`

ETL pipeline execution tracking.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment |
| `run_id` | VARCHAR(64) | Pipeline run UUID |
| `pipeline_name` | VARCHAR(100) | Pipeline identifier |
| `step_name` | VARCHAR(100) | Step name |
| `run_start` | DATETIME | Execution start |
| `run_end` | DATETIME | Execution end |
| `duration_seconds` | INT | Elapsed seconds |
| `data_date_start` | DATE | Data range start |
| `data_date_end` | DATE | Data range end |
| `status` | ENUM | RUNNING / SUCCESS / FAILED / PARTIAL / SKIPPED |
| `rows_extracted` | INT | Extraction count |
| `rows_transformed` | INT | Transformation count |
| `rows_loaded` | INT | Load count |
| `rows_errored` | INT | Error count |
| `target_table` | VARCHAR(100) | Target table name |
| `error_message` | TEXT | Error summary |
| `error_detail` | TEXT | Full error detail |
| `triggered_by` | VARCHAR(100) | Trigger source |
| `host_name` | VARCHAR(100) | Execution host |
| `config_snapshot` | JSON | Config at run time |

**Unique index**: (run_id, step_name) — enables ON DUPLICATE KEY UPDATE

---

## Staging Tables

All staging tables are truncated and reloaded each pipeline run. Prefix: `tmp_`.

### `tmp_stock_changes`
**Source**: `scm-shopstock.t_stock_shop_change_record_{dow}`

| Column | Source Column | Description |
|--------|--------------|-------------|
| `shop_dept_id` | shop_dept_id | Store ID |
| `goods_mid` | goods_mid | Goods code (mid-level) |
| `reason_code` | reason_code | Stock change reason (025=consumption, 1001/1002=production use) |
| `total_adjust_num` | total_adjust_num | Qty adjustment (negative=consumption) |
| `operated_time` | operated_time | Operation timestamp |

### `tmp_abandon_tasks`
**Source**: `opqualitycontrol.t_goods_abandon_task_form`

| Column | Description |
|--------|-------------|
| `dept_id` | Store ID |
| `spec_mid` | Goods code |
| `abandoned_date` | Disposal date |
| `abandon_amount_normal` | Room-temp waste qty |
| `abandon_amount_frozen` | Frozen waste qty |
| `abandon_amount_refrigerated` | Refrigerated waste qty |
| `task_status` | 3=completed |

### `tmp_expiry_prints`
**Source**: `opqualitycontrol.t_expiry_print_log`

| Column | Description |
|--------|-------------|
| `dept_id` | Store ID |
| `spec_mid` | Goods code |
| `expire_time` | Expiry timestamp |
| `print_time` | Label print time |
| `collection_code` | Batch ID |

### `tmp_shelf_life_config`
**Source**: `opqualitycontrol.t_goods_expiry_config`

| Column | Description |
|--------|-------------|
| `spec_mid` | Goods code |
| `open_time_data` / `open_time_unit` | Open-package expiry |
| `container_time_data` / `container_time_unit` | Container storage expiry |
| `thaw_time_data` / `thaw_time_unit` | Thaw expiry |

### `tmp_production`
**Source**: `opproduction.t_production`

| Column | Description |
|--------|-------------|
| `dept_id` | Store ID |
| `product_status` | Production status |
| `order_create_time` | Order creation time |
| `order_complete_time` | Completion time |

### `tmp_commodity`
**Source**: `opproduction.t_production_commodity_detail`

| Column | Description |
|--------|-------------|
| `production_id` | FK to tmp_production |
| `spu_code` | SPU code (recipe level) |
| `goods_code` | Goods code (ingredient level) |
| `use_amount` | Qty used in production |

### `tmp_predictions`
**Source**: `ireplenishment.t_goods_vlt_day_forecast`

| Column | Description |
|--------|-------------|
| `dept_id` | Store ID |
| `goods_code` | Goods code |
| `forecast_date` | Forecast target date |
| `vlt_avg_demand` | Algorithm demand prediction |
| `order_num` | Suggested order qty |

### `tmp_goods`
**Source**: `pubdm.t_mdm_goods`

| Column | Description |
|--------|-------------|
| `goods_code` | Goods code |
| `goods_name` | Product name |
| `large_class_name` | Category name |

### `tmp_stores`
**Source**: `opshop.t_shop_info`

| Column | Description |
|--------|-------------|
| `dept_id` | Store ID |
| `shop_name` | Store name |
| `shop_code` | Store code |
| `province` / `city` | Location |

### `tmp_formula`
**Source**: `scmcommodity.t_formula_spu`

| Column | Description |
|--------|-------------|
| `spu_code` | Recipe SPU code |
| `goods_code` | Ingredient goods code |
| `dosage` | Ingredient dosage |

---

## Key Relationships

```
tmp_stock_changes ──→ waste_consumption_daily ──→ waste_consumption_daily (v1_forecast)
tmp_abandon_tasks ──→ waste_daily_detail
tmp_expiry_prints ──→ waste_batch_risk_score
tmp_shelf_life_config ──→ waste_shelf_life_config
tmp_predictions ──→ waste_consumption_daily (predicted_demand)
tmp_goods ──→ denormalization across all tables
tmp_stores ──→ denormalization across all tables

waste_consumption_daily ──→ waste_batch_risk_score (forecast_consumption_24h/48h)
waste_batch_risk_score ──→ waste_transfer_recommendations (source batches)
waste_daily_detail ──→ waste_summary (aggregation)
waste_daily_detail ──→ waste_alerts (threshold checks)
waste_batch_risk_score ──→ waste_alerts (expiry surge)
waste_consumption_daily ──→ waste_alerts (forecast bias)
```

---

## Reason Code Reference

| Code | Type | Meaning |
|------|------|---------|
| 025 | Consumption | Direct sales consumption |
| 1001 | Consumption | Production use (recipe ingredient) |
| 1002 | Consumption | Production use (auxiliary) |
| 1006 | Transfer | Transfer out |
| 1009 | Transfer | Transfer in |
| 2006 | Transfer | Transfer reason_type |
