-- ============================================================================
-- UC-SC-02: Waste Prediction & Reduction — Verification Queries
-- ============================================================================
-- Purpose:  8 verification queries (V1-V8) to validate pipeline output quality,
--           data completeness, and analytical consistency.
-- Usage:    Run against aws-luckyus-dbatest-rw after pipeline execution.
--           All queries return structured result sets for automated checking.
-- Author:   DBA/Infrastructure Team
-- Created:  2026-02-18
-- ============================================================================

USE test;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ V1: Staging Table Completeness                                          ║
-- ║ Verify all 10 staging tables have recent data.                          ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

SELECT 'V1: Staging Table Completeness' AS verification,
       staging.table_name,
       staging.row_count,
       staging.store_count,
       CASE WHEN staging.row_count > 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
    SELECT 'tmp_stock_changes'    AS table_name, COUNT(*) AS row_count,
           COUNT(DISTINCT shop_dept_id) AS store_count FROM test.tmp_stock_changes
    UNION ALL
    SELECT 'tmp_abandon_tasks',    COUNT(*),
           COUNT(DISTINCT dept_id) FROM test.tmp_abandon_tasks
    UNION ALL
    SELECT 'tmp_expiry_prints',    COUNT(*),
           COUNT(DISTINCT dept_id) FROM test.tmp_expiry_prints
    UNION ALL
    SELECT 'tmp_shelf_life_config', COUNT(*),
           0 FROM test.tmp_shelf_life_config
    UNION ALL
    SELECT 'tmp_production',       COUNT(*),
           COUNT(DISTINCT dept_id) FROM test.tmp_production
    UNION ALL
    SELECT 'tmp_commodity',        COUNT(*),
           0 FROM test.tmp_commodity
    UNION ALL
    SELECT 'tmp_predictions',      COUNT(*),
           COUNT(DISTINCT dept_id) FROM test.tmp_predictions
    UNION ALL
    SELECT 'tmp_goods',            COUNT(*),
           0 FROM test.tmp_goods
    UNION ALL
    SELECT 'tmp_stores',           COUNT(*),
           COUNT(DISTINCT dept_id) FROM test.tmp_stores
    UNION ALL
    SELECT 'tmp_formula',          COUNT(*),
           0 FROM test.tmp_formula
) staging
ORDER BY staging.table_name;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ V2: Analytics Table Row Counts & Date Coverage                          ║
-- ║ Verify all 8 analytics tables have data and expected date range.        ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

SELECT 'V2: Analytics Table Coverage' AS verification,
       t.table_name,
       t.row_count,
       t.min_date,
       t.max_date,
       t.distinct_dates,
       t.distinct_stores,
       CASE
           WHEN t.row_count > 0 AND t.distinct_dates > 0 THEN 'PASS'
           ELSE 'FAIL'
       END AS status
FROM (
    SELECT 'waste_daily_detail'   AS table_name, COUNT(*) AS row_count,
           MIN(waste_date)        AS min_date, MAX(waste_date) AS max_date,
           COUNT(DISTINCT waste_date) AS distinct_dates,
           COUNT(DISTINCT shop_dept_id) AS distinct_stores
    FROM test.waste_daily_detail
    UNION ALL
    SELECT 'waste_consumption_daily', COUNT(*),
           MIN(consumption_date),  MAX(consumption_date),
           COUNT(DISTINCT consumption_date),
           COUNT(DISTINCT shop_dept_id)
    FROM test.waste_consumption_daily
    UNION ALL
    SELECT 'waste_shelf_life_config', COUNT(*),
           NULL, NULL, 0,
           0
    FROM test.waste_shelf_life_config
    UNION ALL
    SELECT 'waste_batch_risk_score',  COUNT(*),
           MIN(score_date), MAX(score_date),
           COUNT(DISTINCT score_date),
           COUNT(DISTINCT shop_dept_id)
    FROM test.waste_batch_risk_score
    UNION ALL
    SELECT 'waste_transfer_recommendations', COUNT(*),
           MIN(recommendation_date), MAX(recommendation_date),
           COUNT(DISTINCT recommendation_date),
           COUNT(DISTINCT source_store_id)
    FROM test.waste_transfer_recommendations
    UNION ALL
    SELECT 'waste_summary',           COUNT(*),
           MIN(period_start), MAX(period_end),
           0,
           0
    FROM test.waste_summary
    UNION ALL
    SELECT 'waste_alerts',            COUNT(*),
           MIN(DATE(alert_timestamp)), MAX(DATE(alert_timestamp)),
           COUNT(DISTINCT DATE(alert_timestamp)),
           COUNT(DISTINCT entity_id)
    FROM test.waste_alerts
    UNION ALL
    SELECT 'waste_pipeline_run_log',  COUNT(*),
           MIN(DATE(run_start)), MAX(DATE(run_start)),
           COUNT(DISTINCT DATE(run_start)),
           0
    FROM test.waste_pipeline_run_log
) t
ORDER BY t.table_name;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ V3: Store Coverage — All 10 Manhattan Stores Present                    ║
-- ║ Verify each of the 10 active stores has waste and consumption data.     ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

SELECT 'V3: Store Coverage' AS verification,
       s.dept_id            AS store_id,
       s.shop_name          AS store_name,
       IFNULL(wd.waste_days, 0)  AS waste_days,
       IFNULL(cd.consumption_days, 0) AS consumption_days,
       IFNULL(br.risk_scores, 0) AS risk_score_count,
       CASE
           WHEN IFNULL(cd.consumption_days, 0) > 0 THEN 'PASS'
           ELSE 'FAIL — no consumption data'
       END AS status
FROM test.tmp_stores s
LEFT JOIN (
    SELECT shop_dept_id, COUNT(DISTINCT waste_date) AS waste_days
    FROM test.waste_daily_detail
    GROUP BY shop_dept_id
) wd ON s.dept_id = wd.shop_dept_id
LEFT JOIN (
    SELECT shop_dept_id, COUNT(DISTINCT consumption_date) AS consumption_days
    FROM test.waste_consumption_daily
    GROUP BY shop_dept_id
) cd ON s.dept_id = cd.shop_dept_id
LEFT JOIN (
    SELECT shop_dept_id, COUNT(*) AS risk_scores
    FROM test.waste_batch_risk_score
    GROUP BY shop_dept_id
) br ON s.dept_id = br.shop_dept_id
WHERE s.dept_id IN (1127, 1128, 1140, 1141, 20008, 20010, 20011, 20027, 20031, 20032)
ORDER BY s.dept_id;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ V4: Consumption Feature Quality                                         ║
-- ║ Verify rolling averages are populated and v1_forecast is computed.       ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

SELECT 'V4: Consumption Feature Quality' AS verification,
       consumption_date,
       COUNT(*)                                            AS total_rows,
       -- Rolling average fill rate
       SUM(CASE WHEN consumption_7d_avg IS NOT NULL
                THEN 1 ELSE 0 END)                        AS has_7d_avg,
       ROUND(SUM(CASE WHEN consumption_7d_avg IS NOT NULL THEN 1 ELSE 0 END)
             / COUNT(*) * 100, 1)                          AS pct_7d_avg,
       -- Forecast fill rate
       SUM(CASE WHEN v1_forecast IS NOT NULL
                THEN 1 ELSE 0 END)                        AS has_v1_forecast,
       ROUND(SUM(CASE WHEN v1_forecast IS NOT NULL THEN 1 ELSE 0 END)
             / COUNT(*) * 100, 1)                          AS pct_v1_forecast,
       -- Actual consumption sanity
       ROUND(AVG(actual_consumption), 2)                   AS avg_consumption,
       ROUND(AVG(v1_forecast), 2)                          AS avg_v1_forecast,
       -- Negative values check
       SUM(CASE WHEN actual_consumption < 0 THEN 1 ELSE 0 END) AS negative_consumption,
       SUM(CASE WHEN v1_forecast < 0 THEN 1 ELSE 0 END)   AS negative_forecast,
       CASE
           WHEN SUM(CASE WHEN actual_consumption < 0 THEN 1 ELSE 0 END) = 0
            AND SUM(CASE WHEN v1_forecast < 0 THEN 1 ELSE 0 END) = 0
            AND COUNT(*) > 0
           THEN 'PASS'
           ELSE 'FAIL'
       END AS status
FROM test.waste_consumption_daily
GROUP BY consumption_date
ORDER BY consumption_date DESC
LIMIT 14;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ V5: Forecast Accuracy Assessment (v1 vs Existing vs Baseline)           ║
-- ║ Compare MAPE of v1 forecast against ireplenishment and naive baseline.  ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

SELECT 'V5: Forecast Accuracy' AS verification,
       -- v1 forecast MAPE (our model)
       ROUND(AVG(CASE
           WHEN actual_consumption > 0 AND v1_forecast IS NOT NULL
           THEN ABS(v1_forecast - actual_consumption) / actual_consumption
           ELSE NULL
       END) * 100, 2) AS v1_mape_pct,

       -- Existing ireplenishment MAPE
       ROUND(AVG(CASE
           WHEN actual_consumption > 0 AND predicted_demand IS NOT NULL
           THEN ABS(predicted_demand - actual_consumption) / actual_consumption
           ELSE NULL
       END) * 100, 2) AS existing_mape_pct,

       -- Naive baseline (7-day avg) MAPE
       ROUND(AVG(CASE
           WHEN actual_consumption > 0 AND consumption_7d_avg IS NOT NULL
           THEN ABS(consumption_7d_avg - actual_consumption) / actual_consumption
           ELSE NULL
       END) * 100, 2) AS naive_7d_mape_pct,

       -- Forecast bias (positive = over-forecast)
       ROUND(AVG(CASE
           WHEN actual_consumption > 0 AND v1_forecast IS NOT NULL
           THEN (v1_forecast - actual_consumption) / actual_consumption
           ELSE NULL
       END) * 100, 2) AS v1_bias_pct,

       -- Sample sizes
       COUNT(CASE WHEN v1_forecast IS NOT NULL AND actual_consumption > 0
             THEN 1 END) AS v1_sample_size,
       COUNT(CASE WHEN predicted_demand IS NOT NULL AND actual_consumption > 0
             THEN 1 END) AS existing_sample_size,

       -- Status: v1 should beat or match existing model
       CASE
           WHEN AVG(CASE WHEN actual_consumption > 0 AND v1_forecast IS NOT NULL
                    THEN ABS(v1_forecast - actual_consumption) / actual_consumption END)
                <=
                COALESCE(AVG(CASE WHEN actual_consumption > 0 AND predicted_demand IS NOT NULL
                    THEN ABS(predicted_demand - actual_consumption) / actual_consumption END), 1.0)
           THEN 'PASS — v1 <= existing MAPE'
           ELSE 'WARN — v1 > existing MAPE'
       END AS status
FROM test.waste_consumption_daily
WHERE consumption_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ V6: Risk Score Distribution & Action Coverage                           ║
-- ║ Verify risk tiers are reasonably distributed and actions assigned.      ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

SELECT 'V6: Risk Score Distribution' AS verification,
       score_date,
       COUNT(*)                                                AS total_batches,
       SUM(CASE WHEN risk_tier = 'CRITICAL' THEN 1 ELSE 0 END) AS critical,
       SUM(CASE WHEN risk_tier = 'HIGH'     THEN 1 ELSE 0 END) AS high,
       SUM(CASE WHEN risk_tier = 'MEDIUM'   THEN 1 ELSE 0 END) AS medium,
       SUM(CASE WHEN risk_tier = 'LOW'      THEN 1 ELSE 0 END) AS low,
       ROUND(AVG(risk_score), 2)                                AS avg_score,
       ROUND(MIN(risk_score), 2)                                AS min_score,
       ROUND(MAX(risk_score), 2)                                AS max_score,
       -- Action assignment completeness
       SUM(CASE WHEN recommended_action IS NULL THEN 1 ELSE 0 END) AS missing_action,
       -- Hours remaining sanity (should not be negative for scored batches)
       SUM(CASE WHEN hours_remaining < 0 THEN 1 ELSE 0 END)    AS expired_batches,
       CASE
           WHEN SUM(CASE WHEN recommended_action IS NULL THEN 1 ELSE 0 END) = 0
            AND COUNT(*) > 0
           THEN 'PASS'
           ELSE 'FAIL — missing actions'
       END AS status
FROM test.waste_batch_risk_score
GROUP BY score_date
ORDER BY score_date DESC
LIMIT 7;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ V7: Transfer Recommendation Quality                                     ║
-- ║ Verify transfers have positive net benefit and valid store pairs.        ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

SELECT 'V7: Transfer Recommendation Quality' AS verification,
       recommendation_date,
       COUNT(*)                                                  AS total_recs,
       COUNT(DISTINCT source_store_id)                           AS source_stores,
       COUNT(DISTINCT dest_store_id)                             AS dest_stores,
       COUNT(DISTINCT goods_code)                                AS distinct_skus,
       ROUND(SUM(transfer_qty), 1)                               AS total_transfer_qty,
       ROUND(SUM(net_benefit), 2)                                AS total_net_benefit,
       ROUND(AVG(net_benefit), 2)                                AS avg_net_benefit,
       -- Negative net benefit check (should be 0)
       SUM(CASE WHEN net_benefit < 0 THEN 1 ELSE 0 END)         AS negative_benefit_count,
       -- Self-transfer check (source = dest should be 0)
       SUM(CASE WHEN source_store_id = dest_store_id THEN 1 ELSE 0 END) AS self_transfers,
       -- Minimum hours to expiry (should be >= 8 per SP logic)
       ROUND(MIN(source_hours_to_expiry), 1)                     AS min_hours_to_expiry,
       CASE
           WHEN SUM(CASE WHEN net_benefit < 0 THEN 1 ELSE 0 END) = 0
            AND SUM(CASE WHEN source_store_id = dest_store_id THEN 1 ELSE 0 END) = 0
           THEN 'PASS'
           ELSE 'FAIL'
       END AS status
FROM test.waste_transfer_recommendations
GROUP BY recommendation_date
ORDER BY recommendation_date DESC
LIMIT 7;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ V8: Alert Quality & Pipeline Health                                     ║
-- ║ Verify alerts are reasonable and pipeline runs completed successfully.   ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

-- V8a: Alert distribution
SELECT 'V8a: Alert Distribution' AS verification,
       DATE(alert_timestamp)   AS alert_date,
       alert_type,
       COUNT(*)                AS alert_count,
       COUNT(DISTINCT entity_id) AS affected_entities,
       'INFO' AS status
FROM test.waste_alerts
GROUP BY DATE(alert_timestamp), alert_type
ORDER BY alert_date DESC, alert_type
LIMIT 30;

-- V8b: Pipeline run health
SELECT 'V8b: Pipeline Run Health' AS verification,
       DATE(run_start)       AS run_date,
       step_name,
       status,
       duration_seconds,
       rows_extracted,
       rows_loaded,
       CASE WHEN error_message IS NOT NULL
            THEN LEFT(error_message, 100)
            ELSE NULL
       END                   AS error_preview,
       CASE
           WHEN status IN ('SUCCESS', 'PARTIAL') THEN 'PASS'
           WHEN status = 'RUNNING' THEN 'WARN — still running'
           ELSE 'FAIL'
       END AS health_status
FROM test.waste_pipeline_run_log
WHERE run_start >= DATE_SUB(NOW(), INTERVAL 3 DAY)
ORDER BY run_start DESC, step_name
LIMIT 50;

-- V8c: Summary table dimension coverage
SELECT 'V8c: Summary Dimensions' AS verification,
       period_type,
       dimension_type,
       COUNT(*)              AS row_count,
       MIN(period_start)     AS earliest_period,
       MAX(period_end)       AS latest_period,
       CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM test.waste_summary
GROUP BY period_type, dimension_type
ORDER BY period_type, dimension_type;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ V-SUMMARY: Overall Pipeline Validation                                  ║
-- ║ Single-query health check suitable for automated monitoring.            ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

SELECT 'V-SUMMARY: Pipeline Validation' AS verification,
       -- Staging health
       (SELECT COUNT(*) FROM test.tmp_stock_changes) > 0             AS staging_stock_ok,
       (SELECT COUNT(*) FROM test.tmp_abandon_tasks) > 0             AS staging_disposal_ok,
       (SELECT COUNT(*) FROM test.tmp_stores) >= 10                  AS staging_stores_ok,
       -- Analytics health (check last 7 days)
       (SELECT COUNT(*) FROM test.waste_daily_detail
        WHERE waste_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)) > 0 AS waste_detail_ok,
       (SELECT COUNT(*) FROM test.waste_consumption_daily
        WHERE consumption_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)) > 0
                                                                      AS consumption_ok,
       (SELECT COUNT(*) FROM test.waste_batch_risk_score
        WHERE score_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)) > 0  AS risk_scores_ok,
       -- Forecast health
       (SELECT COUNT(*) FROM test.waste_consumption_daily
        WHERE v1_forecast IS NOT NULL
          AND consumption_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)) > 0
                                                                      AS forecast_ok,
       -- Pipeline run health (last run succeeded)
       (SELECT status FROM test.waste_pipeline_run_log
        WHERE pipeline_name = 'UC-SC-02-waste-prediction'
          AND step_name LIKE 'sp_waste_daily_refresh%'
        ORDER BY run_start DESC LIMIT 1)                              AS last_run_status,
       -- Overall
       CASE
           WHEN (SELECT COUNT(*) FROM test.waste_consumption_daily
                 WHERE consumption_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)) > 0
            AND (SELECT COUNT(*) FROM test.waste_batch_risk_score
                 WHERE score_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)) > 0
           THEN 'PASS — pipeline operational'
           ELSE 'FAIL — pipeline needs attention'
       END AS overall_status;
