-- ============================================================================
-- UC-SC-02: Waste Prediction & Reduction — Alert Threshold Checks
-- ============================================================================
-- Stored Procedure: sp_check_waste_alerts
-- Purpose:  Evaluate 5 alert rules against current waste metrics and insert
--           new alerts into waste_alerts for any breached thresholds.
-- Rules:
--   1. CRITICAL  — Store daily waste_rate > 8%
--   2. WARNING   — Store daily waste_rate > 5%
--   3. CRITICAL  — Expiry surge: >10 CRITICAL batches at single store
--   4. BIAS      — Forecast bias > 20% for 3+ consecutive days
--   5. TREND     — 7d rolling waste > 30d rolling waste * 1.3
-- Depends:  waste_daily_detail, waste_batch_risk_score, waste_consumption_daily
-- Idempotency: Only inserts NEW alerts (checks for duplicates by type+entity+date).
-- Author:   DBA/Infrastructure Team
-- Created:  2026-02-18
-- ============================================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS test.sp_check_waste_alerts$$

CREATE PROCEDURE test.sp_check_waste_alerts(
    IN p_alert_date DATE
)
BEGIN
    DECLARE v_alerts_created INT DEFAULT 0;

    -- ── Alert 1: CRITICAL — Store daily waste rate > 8% ───────────────────
    INSERT INTO test.waste_alerts (
        alert_timestamp, alert_type, entity_type, entity_id, entity_name,
        metric_name, metric_value, threshold_value, baseline_value,
        description, recommended_action
    )
    SELECT
        NOW()                                AS alert_timestamp,
        'CRITICAL'                           AS alert_type,
        'STORE'                              AS entity_type,
        CAST(w.shop_dept_id AS CHAR(50))     AS entity_id,
        MAX(w.shop_name)                     AS entity_name,
        'daily_waste_rate'                   AS metric_name,
        ROUND(SUM(w.waste_qty_total)
              / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0), 4)
                                             AS metric_value,
        0.0800                               AS threshold_value,
        NULL                                 AS baseline_value,
        CONCAT('Store ', MAX(w.shop_name),
               ' (', w.shop_dept_id, ') waste rate ',
               ROUND(SUM(w.waste_qty_total)
                     / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0) * 100, 1),
               '% exceeds CRITICAL threshold of 8%')
                                             AS description,
        'Immediate review: check expiring batches, consider emergency transfers or discounts'
                                             AS recommended_action
    FROM test.waste_daily_detail w
    WHERE w.waste_date = p_alert_date
    GROUP BY w.shop_dept_id
    HAVING SUM(w.waste_qty_total)
           / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0) > 0.08
    -- Deduplicate: skip if same alert already exists for today
    AND NOT EXISTS (
        SELECT 1 FROM test.waste_alerts a
        WHERE a.alert_type   = 'CRITICAL'
          AND a.entity_type  = 'STORE'
          AND a.entity_id    = CAST(w.shop_dept_id AS CHAR(50))
          AND a.metric_name  = 'daily_waste_rate'
          AND DATE(a.alert_timestamp) = p_alert_date
    );

    SET v_alerts_created = v_alerts_created + ROW_COUNT();

    -- ── Alert 2: WARNING — Store daily waste rate > 5% (but ≤ 8%) ────────
    INSERT INTO test.waste_alerts (
        alert_timestamp, alert_type, entity_type, entity_id, entity_name,
        metric_name, metric_value, threshold_value, baseline_value,
        description, recommended_action
    )
    SELECT
        NOW()                                AS alert_timestamp,
        'WARNING'                            AS alert_type,
        'STORE'                              AS entity_type,
        CAST(w.shop_dept_id AS CHAR(50))     AS entity_id,
        MAX(w.shop_name)                     AS entity_name,
        'daily_waste_rate'                   AS metric_name,
        ROUND(SUM(w.waste_qty_total)
              / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0), 4)
                                             AS metric_value,
        0.0500                               AS threshold_value,
        NULL                                 AS baseline_value,
        CONCAT('Store ', MAX(w.shop_name),
               ' (', w.shop_dept_id, ') waste rate ',
               ROUND(SUM(w.waste_qty_total)
                     / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0) * 100, 1),
               '% exceeds WARNING threshold of 5%')
                                             AS description,
        'Review batch expiry schedule and adjust production planning'
                                             AS recommended_action
    FROM test.waste_daily_detail w
    WHERE w.waste_date = p_alert_date
    GROUP BY w.shop_dept_id
    HAVING SUM(w.waste_qty_total)
           / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0)
           BETWEEN 0.05 AND 0.08
    AND NOT EXISTS (
        SELECT 1 FROM test.waste_alerts a
        WHERE a.alert_type   = 'WARNING'
          AND a.entity_type  = 'STORE'
          AND a.entity_id    = CAST(w.shop_dept_id AS CHAR(50))
          AND a.metric_name  = 'daily_waste_rate'
          AND DATE(a.alert_timestamp) = p_alert_date
    );

    SET v_alerts_created = v_alerts_created + ROW_COUNT();

    -- ── Alert 3: CRITICAL — Expiry surge: >10 CRITICAL batches at store ──
    INSERT INTO test.waste_alerts (
        alert_timestamp, alert_type, entity_type, entity_id, entity_name,
        metric_name, metric_value, threshold_value, baseline_value,
        description, recommended_action
    )
    SELECT
        NOW()                                AS alert_timestamp,
        'CRITICAL'                           AS alert_type,
        'STORE'                              AS entity_type,
        CAST(br.shop_dept_id AS CHAR(50))    AS entity_id,
        (SELECT s.shop_name FROM test.tmp_stores s
         WHERE s.dept_id = br.shop_dept_id LIMIT 1)
                                             AS entity_name,
        'critical_batch_count'               AS metric_name,
        COUNT(*)                             AS metric_value,
        10.0000                              AS threshold_value,
        NULL                                 AS baseline_value,
        CONCAT('Store ', br.shop_dept_id,
               ' has ', COUNT(*), ' CRITICAL risk batches (threshold: 10)')
                                             AS description,
        'Emergency: prioritize immediate consumption, transfers, or discounts for all CRITICAL batches'
                                             AS recommended_action
    FROM test.waste_batch_risk_score br
    WHERE br.score_date = p_alert_date
      AND br.risk_tier  = 'CRITICAL'
    GROUP BY br.shop_dept_id
    HAVING COUNT(*) > 10
    AND NOT EXISTS (
        SELECT 1 FROM test.waste_alerts a
        WHERE a.alert_type   = 'CRITICAL'
          AND a.entity_type  = 'STORE'
          AND a.entity_id    = CAST(br.shop_dept_id AS CHAR(50))
          AND a.metric_name  = 'critical_batch_count'
          AND DATE(a.alert_timestamp) = p_alert_date
    );

    SET v_alerts_created = v_alerts_created + ROW_COUNT();

    -- ── Alert 4: BIAS — Forecast bias > 20% for 3+ consecutive days ──────
    -- Over-forecasting leads to over-ordering → waste.
    -- Check per-store average bias over last 3 days.

    INSERT INTO test.waste_alerts (
        alert_timestamp, alert_type, entity_type, entity_id, entity_name,
        metric_name, metric_value, threshold_value, baseline_value,
        description, recommended_action
    )
    SELECT
        NOW()                                AS alert_timestamp,
        'BIAS'                               AS alert_type,
        'STORE'                              AS entity_type,
        CAST(bias_check.shop_dept_id AS CHAR(50)) AS entity_id,
        (SELECT s.shop_name FROM test.tmp_stores s
         WHERE s.dept_id = bias_check.shop_dept_id LIMIT 1)
                                             AS entity_name,
        'forecast_bias_3d'                   AS metric_name,
        bias_check.avg_bias                  AS metric_value,
        0.2000                               AS threshold_value,
        NULL                                 AS baseline_value,
        CONCAT('Store ', bias_check.shop_dept_id,
               ' forecast bias ', ROUND(bias_check.avg_bias * 100, 1),
               '% over last 3 days (threshold: 20%)')
                                             AS description,
        'Investigate forecast model inputs; check for demand pattern change or data quality issues'
                                             AS recommended_action
    FROM (
        SELECT
            wcd.shop_dept_id,
            -- Average signed bias over last 3 days
            AVG(
                (IFNULL(wcd.v1_forecast, wcd.predicted_demand) - wcd.actual_consumption)
                / NULLIF(wcd.actual_consumption, 0)
            ) AS avg_bias,
            -- Count days with data
            COUNT(*) AS days_with_data,
            -- Count days where bias > 20%
            SUM(CASE
                WHEN (IFNULL(wcd.v1_forecast, wcd.predicted_demand) - wcd.actual_consumption)
                     / NULLIF(wcd.actual_consumption, 0) > 0.20
                THEN 1 ELSE 0
            END) AS days_above_threshold
        FROM test.waste_consumption_daily wcd
        WHERE wcd.consumption_date BETWEEN DATE_SUB(p_alert_date, INTERVAL 2 DAY) AND p_alert_date
          AND wcd.actual_consumption > 0
          AND (wcd.v1_forecast IS NOT NULL OR wcd.predicted_demand IS NOT NULL)
        GROUP BY wcd.shop_dept_id
        HAVING days_with_data >= 3 AND days_above_threshold >= 3
    ) bias_check
    WHERE NOT EXISTS (
        SELECT 1 FROM test.waste_alerts a
        WHERE a.alert_type   = 'BIAS'
          AND a.entity_type  = 'STORE'
          AND a.entity_id    = CAST(bias_check.shop_dept_id AS CHAR(50))
          AND a.metric_name  = 'forecast_bias_3d'
          AND DATE(a.alert_timestamp) = p_alert_date
    );

    SET v_alerts_created = v_alerts_created + ROW_COUNT();

    -- ── Alert 5: TREND — 7d rolling waste > 30d rolling waste * 1.3 ──────
    -- Detects accelerating waste patterns at the store level.

    INSERT INTO test.waste_alerts (
        alert_timestamp, alert_type, entity_type, entity_id, entity_name,
        metric_name, metric_value, threshold_value, baseline_value,
        description, recommended_action
    )
    SELECT
        NOW()                                AS alert_timestamp,
        'TREND'                              AS alert_type,
        'STORE'                              AS entity_type,
        CAST(trend.shop_dept_id AS CHAR(50)) AS entity_id,
        (SELECT s.shop_name FROM test.tmp_stores s
         WHERE s.dept_id = trend.shop_dept_id LIMIT 1)
                                             AS entity_name,
        'waste_trend_7d_vs_30d'              AS metric_name,
        ROUND(trend.waste_7d_avg, 2)         AS metric_value,
        ROUND(trend.waste_30d_avg * 1.3, 2)  AS threshold_value,
        ROUND(trend.waste_30d_avg, 2)        AS baseline_value,
        CONCAT('Store ', trend.shop_dept_id,
               ' 7-day avg waste (', ROUND(trend.waste_7d_avg, 1),
               ') exceeds 30-day avg (', ROUND(trend.waste_30d_avg, 1),
               ') by >30%')
                                             AS description,
        'Investigate root cause of waste increase; review ordering patterns and shelf-life management'
                                             AS recommended_action
    FROM (
        SELECT
            shop_dept_id,
            (SELECT AVG(w2.waste_qty_total)
             FROM test.waste_daily_detail w2
             WHERE w2.shop_dept_id = w.shop_dept_id
               AND w2.waste_date BETWEEN DATE_SUB(p_alert_date, INTERVAL 6 DAY) AND p_alert_date
            ) AS waste_7d_avg,
            (SELECT AVG(w2.waste_qty_total)
             FROM test.waste_daily_detail w2
             WHERE w2.shop_dept_id = w.shop_dept_id
               AND w2.waste_date BETWEEN DATE_SUB(p_alert_date, INTERVAL 29 DAY) AND p_alert_date
            ) AS waste_30d_avg
        FROM test.waste_daily_detail w
        WHERE w.waste_date = p_alert_date
        GROUP BY w.shop_dept_id
    ) trend
    WHERE trend.waste_30d_avg > 0
      AND trend.waste_7d_avg > trend.waste_30d_avg * 1.3
      AND NOT EXISTS (
          SELECT 1 FROM test.waste_alerts a
          WHERE a.alert_type   = 'TREND'
            AND a.entity_type  = 'STORE'
            AND a.entity_id    = CAST(trend.shop_dept_id AS CHAR(50))
            AND a.metric_name  = 'waste_trend_7d_vs_30d'
            AND DATE(a.alert_timestamp) = p_alert_date
      );

    SET v_alerts_created = v_alerts_created + ROW_COUNT();

    -- ── Return summary ────────────────────────────────────────────────────
    SELECT 'sp_check_waste_alerts'  AS procedure_name,
           p_alert_date             AS alert_date,
           v_alerts_created         AS new_alerts_created,
           (SELECT COUNT(*) FROM test.waste_alerts
            WHERE DATE(alert_timestamp) = p_alert_date AND alert_type = 'CRITICAL'
           )                        AS critical_alerts_today,
           (SELECT COUNT(*) FROM test.waste_alerts
            WHERE DATE(alert_timestamp) = p_alert_date AND alert_type = 'WARNING'
           )                        AS warning_alerts_today,
           (SELECT COUNT(*) FROM test.waste_alerts
            WHERE DATE(alert_timestamp) = p_alert_date AND alert_type = 'BIAS'
           )                        AS bias_alerts_today,
           (SELECT COUNT(*) FROM test.waste_alerts
            WHERE DATE(alert_timestamp) = p_alert_date AND alert_type = 'TREND'
           )                        AS trend_alerts_today,
           (SELECT COUNT(*) FROM test.waste_alerts
            WHERE is_acknowledged = FALSE
           )                        AS total_unacknowledged,
           NOW()                    AS completed_at;
END$$

DELIMITER ;
