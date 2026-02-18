-- ============================================================================
-- UC-SC-02: Waste Prediction & Reduction — Consumption Forecast Model v1
-- ============================================================================
-- Stored Procedure: sp_compute_consumption_forecast
-- Purpose:  Generate enhanced consumption forecasts using a weighted blend of
--           historical patterns, rolling averages, and existing ireplenishment
--           predictions.  Apply shelf-life tier safety multipliers to bias
--           short-shelf-life items toward slight under-forecast (waste reduction).
-- Depends:  04_consumption_features.sql must have run for the target date range
--           so that rolling averages and DOW patterns are populated.
-- Model:    v1 — Enhanced Moving Average (rule-based, no ML)
--   forecast = 0.30 * same_dow_4wk_avg
--            + 0.25 * consumption_7d_avg
--            + 0.20 * existing_prediction (ireplenishment vlt_avg_demand)
--            + 0.15 * consumption_14d_avg
--            + 0.10 * consumption_30d_avg
--   Then multiply by shelf-life safety factor:
--     ULTRA_SHORT: 0.95
--     SHORT:       0.97
--     MEDIUM:      1.00
--     LONG:        1.00
-- Idempotency: UPDATE existing rows (features must already be populated).
-- Author:   DBA/Infrastructure Team
-- Created:  2026-02-18
-- ============================================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS test.sp_compute_consumption_forecast$$

CREATE PROCEDURE test.sp_compute_consumption_forecast(
    IN p_start_date DATE,
    IN p_end_date   DATE
)
BEGIN
    DECLARE v_rows_forecast INT DEFAULT 0;
    DECLARE v_rows_accuracy INT DEFAULT 0;

    -- ── Step 1: Compute weighted-blend forecast ─────────────────────────────
    -- Handles NULLs gracefully: if a component is NULL, redistribute its
    -- weight proportionally among non-NULL components via the denominator.

    UPDATE test.waste_consumption_daily cur
    SET cur.v1_forecast = (
        SELECT
            -- Weighted blend with NULL-safe redistribution
            (
                IFNULL(cur.same_dow_4wk_avg,    0) * 0.30
              + IFNULL(cur.consumption_7d_avg,   0) * 0.25
              + IFNULL(cur.predicted_demand,     0) * 0.20
              + IFNULL(cur.consumption_14d_avg,  0) * 0.15
              + IFNULL(cur.consumption_30d_avg,  0) * 0.10
            )
            /
            -- Denominator = sum of weights for non-NULL components
            NULLIF(
                (CASE WHEN cur.same_dow_4wk_avg   IS NOT NULL THEN 0.30 ELSE 0 END)
              + (CASE WHEN cur.consumption_7d_avg  IS NOT NULL THEN 0.25 ELSE 0 END)
              + (CASE WHEN cur.predicted_demand    IS NOT NULL THEN 0.20 ELSE 0 END)
              + (CASE WHEN cur.consumption_14d_avg IS NOT NULL THEN 0.15 ELSE 0 END)
              + (CASE WHEN cur.consumption_30d_avg IS NOT NULL THEN 0.10 ELSE 0 END)
            , 0)
            *
            -- Shelf-life tier safety multiplier
            CASE cur.shelf_life_tier
                WHEN 'ULTRA_SHORT' THEN 0.95
                WHEN 'SHORT'       THEN 0.97
                WHEN 'MEDIUM'      THEN 1.00
                WHEN 'LONG'        THEN 1.00
                ELSE 1.00  -- default if tier not yet populated
            END
    )
    WHERE cur.consumption_date BETWEEN p_start_date AND p_end_date
      -- At least one feature must be non-NULL to produce a forecast
      AND (   cur.same_dow_4wk_avg   IS NOT NULL
           OR cur.consumption_7d_avg  IS NOT NULL
           OR cur.predicted_demand    IS NOT NULL
           OR cur.consumption_14d_avg IS NOT NULL
           OR cur.consumption_30d_avg IS NOT NULL
      );

    SET v_rows_forecast = ROW_COUNT();

    -- ── Step 2: Compute v1 forecast accuracy metrics ────────────────────────

    UPDATE test.waste_consumption_daily cur
    SET cur.v1_forecast_error = cur.v1_forecast - cur.actual_consumption,
        cur.v1_abs_pct_error  = CASE
            WHEN cur.actual_consumption > 0
            THEN ABS(cur.v1_forecast - cur.actual_consumption) / cur.actual_consumption
            ELSE NULL
        END
    WHERE cur.consumption_date BETWEEN p_start_date AND p_end_date
      AND cur.v1_forecast IS NOT NULL;

    SET v_rows_accuracy = ROW_COUNT();

    -- ── Return summary ──────────────────────────────────────────────────────
    SELECT 'sp_compute_consumption_forecast' AS procedure_name,
           p_start_date                     AS date_start,
           p_end_date                       AS date_end,
           v_rows_forecast                  AS rows_with_v1_forecast,
           v_rows_accuracy                  AS rows_with_accuracy_metrics,
           -- Quick accuracy snapshot for the date range
           (SELECT AVG(v1_abs_pct_error)
            FROM test.waste_consumption_daily
            WHERE consumption_date BETWEEN p_start_date AND p_end_date
              AND v1_abs_pct_error IS NOT NULL
              AND actual_consumption > 0
           )                                AS v1_mape,
           (SELECT AVG(abs_pct_error)
            FROM test.waste_consumption_daily
            WHERE consumption_date BETWEEN p_start_date AND p_end_date
              AND abs_pct_error IS NOT NULL
              AND actual_consumption > 0
           )                                AS irep_mape,
           NOW()                            AS completed_at;
END$$

DELIMITER ;
