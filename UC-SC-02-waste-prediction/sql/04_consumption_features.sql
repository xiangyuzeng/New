-- ============================================================================
-- UC-SC-02: Waste Prediction & Reduction — Consumption Feature Engineering
-- ============================================================================
-- Stored Procedure: sp_build_consumption_features
-- Purpose:  Extract daily consumption from staging stock changes, compute
--           rolling averages, DOW patterns, trend indicators, and join with
--           existing ireplenishment predictions for error tracking.
-- Depends:  02_create_analytics_schema.sql (tables must exist)
--           Python orchestrator must have loaded staging tables first:
--             tmp_stock_changes, tmp_predictions, tmp_goods
--           waste_shelf_life_config must be populated (03_waste_landscape.sql)
-- Idempotency: DELETE-then-INSERT for the target date range.
-- Author:   DBA/Infrastructure Team
-- Created:  2026-02-18
-- ============================================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS test.sp_build_consumption_features$$

CREATE PROCEDURE test.sp_build_consumption_features(
    IN p_start_date DATE,
    IN p_end_date   DATE
)
BEGIN
    DECLARE v_rows_base    INT DEFAULT 0;
    DECLARE v_rows_rolling INT DEFAULT 0;
    DECLARE v_rows_pred    INT DEFAULT 0;

    -- ── Step 1: Delete existing rows for date range (idempotency) ─────────
    DELETE FROM test.waste_consumption_daily
    WHERE consumption_date BETWEEN p_start_date AND p_end_date;

    -- ── Step 2: Insert base daily consumption from stock changes ──────────
    -- Consumption = reason_code IN ('025','1001','1002') AND total_adjust_num < 0
    -- Quantity = SUM(ABS(total_adjust_num))

    INSERT INTO test.waste_consumption_daily (
        consumption_date, shop_dept_id, goods_code,
        actual_consumption, day_of_week, is_weekend,
        computed_at
    )
    SELECT
        DATE(sc.operated_time)                          AS consumption_date,
        sc.shop_dept_id,
        sc.goods_mid                                    AS goods_code,
        SUM(ABS(sc.total_adjust_num))                   AS actual_consumption,
        DAYOFWEEK(DATE(sc.operated_time))                AS day_of_week,
        CASE WHEN DAYOFWEEK(DATE(sc.operated_time)) IN (1, 7)
             THEN 1 ELSE 0 END                          AS is_weekend,
        NOW()                                           AS computed_at
    FROM test.tmp_stock_changes sc
    WHERE sc.reason_code IN ('025', '1001', '1002')
      AND sc.total_adjust_num < 0
      AND sc.shop_dept_id IN (1127,1128,1140,1141,20008,20010,20011,20027,20031,20032)
      AND DATE(sc.operated_time) BETWEEN p_start_date AND p_end_date
    GROUP BY DATE(sc.operated_time), sc.shop_dept_id, sc.goods_mid
    HAVING actual_consumption > 0;

    SET v_rows_base = ROW_COUNT();

    -- ── Step 3: Compute rolling averages (7d, 14d, 30d) ──────────────────
    -- Uses self-join against the full waste_consumption_daily history table.
    -- We need historical data beyond p_start_date for lookback windows.

    UPDATE test.waste_consumption_daily cur
    LEFT JOIN (
        SELECT
            h.shop_dept_id,
            h.goods_code,
            h.consumption_date,
            -- 7-day rolling average
            (SELECT AVG(h2.actual_consumption)
             FROM test.waste_consumption_daily h2
             WHERE h2.shop_dept_id = h.shop_dept_id
               AND h2.goods_code   = h.goods_code
               AND h2.consumption_date BETWEEN DATE_SUB(h.consumption_date, INTERVAL 7 DAY)
                                             AND DATE_SUB(h.consumption_date, INTERVAL 1 DAY)
            ) AS avg_7d,
            -- 7-day rolling std dev
            (SELECT STDDEV_SAMP(h2.actual_consumption)
             FROM test.waste_consumption_daily h2
             WHERE h2.shop_dept_id = h.shop_dept_id
               AND h2.goods_code   = h.goods_code
               AND h2.consumption_date BETWEEN DATE_SUB(h.consumption_date, INTERVAL 7 DAY)
                                             AND DATE_SUB(h.consumption_date, INTERVAL 1 DAY)
            ) AS stddev_7d,
            -- 14-day rolling average
            (SELECT AVG(h2.actual_consumption)
             FROM test.waste_consumption_daily h2
             WHERE h2.shop_dept_id = h.shop_dept_id
               AND h2.goods_code   = h.goods_code
               AND h2.consumption_date BETWEEN DATE_SUB(h.consumption_date, INTERVAL 14 DAY)
                                             AND DATE_SUB(h.consumption_date, INTERVAL 1 DAY)
            ) AS avg_14d,
            -- 30-day rolling average
            (SELECT AVG(h2.actual_consumption)
             FROM test.waste_consumption_daily h2
             WHERE h2.shop_dept_id = h.shop_dept_id
               AND h2.goods_code   = h.goods_code
               AND h2.consumption_date BETWEEN DATE_SUB(h.consumption_date, INTERVAL 30 DAY)
                                             AND DATE_SUB(h.consumption_date, INTERVAL 1 DAY)
            ) AS avg_30d,
            -- Same day-of-week average over last 4 weeks
            (SELECT AVG(h2.actual_consumption)
             FROM test.waste_consumption_daily h2
             WHERE h2.shop_dept_id = h.shop_dept_id
               AND h2.goods_code   = h.goods_code
               AND DAYOFWEEK(h2.consumption_date) = DAYOFWEEK(h.consumption_date)
               AND h2.consumption_date BETWEEN DATE_SUB(h.consumption_date, INTERVAL 28 DAY)
                                             AND DATE_SUB(h.consumption_date, INTERVAL 1 DAY)
            ) AS same_dow_4wk
        FROM test.waste_consumption_daily h
        WHERE h.consumption_date BETWEEN p_start_date AND p_end_date
    ) feat ON cur.shop_dept_id    = feat.shop_dept_id
          AND cur.goods_code      = feat.goods_code
          AND cur.consumption_date = feat.consumption_date
    SET cur.consumption_7d_avg    = feat.avg_7d,
        cur.consumption_7d_stddev = feat.stddev_7d,
        cur.consumption_14d_avg   = feat.avg_14d,
        cur.consumption_30d_avg   = feat.avg_30d,
        cur.same_dow_4wk_avg      = feat.same_dow_4wk,
        -- Trend indicator: (7d - 14d) / 14d
        cur.consumption_trend_7d  = CASE
            WHEN feat.avg_14d > 0
            THEN (IFNULL(feat.avg_7d, 0) - feat.avg_14d) / feat.avg_14d
            ELSE NULL
        END
    WHERE cur.consumption_date BETWEEN p_start_date AND p_end_date;

    SET v_rows_rolling = ROW_COUNT();

    -- ── Step 4: Join with existing ireplenishment predictions ─────────────
    UPDATE test.waste_consumption_daily cur
    JOIN test.tmp_predictions p
      ON  cur.shop_dept_id    = p.dept_id
      AND cur.goods_code      = p.goods_code
      AND cur.consumption_date = p.forecast_date
    SET cur.predicted_demand    = p.vlt_avg_demand,
        cur.predicted_order_qty = p.order_num,
        cur.forecast_error      = p.vlt_avg_demand - cur.actual_consumption,
        cur.abs_pct_error       = CASE
            WHEN cur.actual_consumption > 0
            THEN ABS(p.vlt_avg_demand - cur.actual_consumption) / cur.actual_consumption
            ELSE NULL
        END
    WHERE cur.consumption_date BETWEEN p_start_date AND p_end_date;

    SET v_rows_pred = ROW_COUNT();

    -- ── Step 5: Enrich with shelf-life tier ───────────────────────────────
    UPDATE test.waste_consumption_daily cur
    JOIN test.waste_shelf_life_config slc
      ON cur.goods_code = slc.goods_code
    SET cur.shelf_life_tier = slc.shelf_life_tier
    WHERE cur.consumption_date BETWEEN p_start_date AND p_end_date;

    -- ── Return summary ───────────────────────────────────────────────────
    SELECT 'sp_build_consumption_features' AS procedure_name,
           p_start_date                   AS date_start,
           p_end_date                     AS date_end,
           v_rows_base                    AS base_consumption_rows,
           v_rows_rolling                 AS rows_with_rolling_features,
           v_rows_pred                    AS rows_matched_predictions,
           NOW()                          AS completed_at;
END$$

DELIMITER ;
