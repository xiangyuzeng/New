-- ============================================================================
-- UC-SC-02: Waste Prediction & Reduction — Aggregated Waste Summary
-- ============================================================================
-- Stored Procedure: sp_compute_waste_summary
-- Purpose:  Aggregate waste metrics by multiple period types and dimensions
--           into waste_summary for dashboard consumption.
-- Period types:  DAILY, WEEKLY, MONTHLY, ROLLING_7D, ROLLING_30D
-- Dimensions:    OVERALL, STORE, PRODUCT, CATEGORY, SHELF_TIER, DOW, STORAGE_TYPE
-- Depends:  waste_daily_detail, waste_consumption_daily, waste_batch_risk_score,
--           waste_transfer_recommendations
-- Idempotency: DELETE-then-INSERT for the target period.
-- Author:   DBA/Infrastructure Team
-- Created:  2026-02-18
-- ============================================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS test.sp_compute_waste_summary$$

CREATE PROCEDURE test.sp_compute_waste_summary(
    IN p_summary_date DATE
)
BEGIN
    DECLARE v_rows_inserted INT DEFAULT 0;
    DECLARE v_week_start    DATE;
    DECLARE v_week_end      DATE;
    DECLARE v_month_start   DATE;
    DECLARE v_month_end     DATE;
    DECLARE v_roll7_start   DATE;
    DECLARE v_roll30_start  DATE;

    -- Compute period boundaries
    SET v_week_start   = DATE_SUB(p_summary_date, INTERVAL WEEKDAY(p_summary_date) DAY);
    SET v_week_end     = DATE_ADD(v_week_start, INTERVAL 6 DAY);
    SET v_month_start  = DATE_FORMAT(p_summary_date, '%Y-%m-01');
    SET v_month_end    = LAST_DAY(p_summary_date);
    SET v_roll7_start  = DATE_SUB(p_summary_date, INTERVAL 6 DAY);
    SET v_roll30_start = DATE_SUB(p_summary_date, INTERVAL 29 DAY);

    -- ── Clean existing summaries for this date ────────────────────────────────
    DELETE FROM test.waste_summary
    WHERE (period_type = 'DAILY'       AND period_start = p_summary_date)
       OR (period_type = 'WEEKLY'      AND period_start = v_week_start)
       OR (period_type = 'MONTHLY'     AND period_start = v_month_start)
       OR (period_type = 'ROLLING_7D'  AND period_start = v_roll7_start)
       OR (period_type = 'ROLLING_30D' AND period_start = v_roll30_start);

    -- ======================================================================
    -- DAILY summaries
    -- ======================================================================

    -- ── DAILY × OVERALL ──────────────────────────────────────────────────────
    INSERT INTO test.waste_summary (
        period_type, period_start, period_end,
        dimension_type, dimension_value, dimension_name,
        total_waste_qty, total_waste_cost, total_consumption, waste_rate,
        waste_mape, waste_wmape, waste_bias,
        batches_critical, batches_high,
        transfers_recommended, transfers_executed, transfer_savings,
        record_count, sku_count, computed_at
    )
    SELECT
        'DAILY', p_summary_date, p_summary_date,
        'OVERALL', 'ALL', 'All Stores',
        SUM(w.waste_qty_total),
        SUM(w.waste_cost),
        SUM(w.consumption_qty),
        SUM(w.waste_qty_total) / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0),
        -- Forecast accuracy from waste_consumption_daily
        (SELECT AVG(wcd.v1_abs_pct_error)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date = p_summary_date
           AND wcd.v1_abs_pct_error IS NOT NULL AND wcd.actual_consumption > 0),
        (SELECT SUM(ABS(wcd.v1_forecast - wcd.actual_consumption))
                / NULLIF(SUM(wcd.actual_consumption), 0)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date = p_summary_date
           AND wcd.v1_forecast IS NOT NULL AND wcd.actual_consumption > 0),
        (SELECT AVG(wcd.v1_forecast_error)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date = p_summary_date
           AND wcd.v1_forecast_error IS NOT NULL),
        -- Risk distribution
        (SELECT COUNT(*) FROM test.waste_batch_risk_score br
         WHERE br.score_date = p_summary_date AND br.risk_tier = 'CRITICAL'),
        (SELECT COUNT(*) FROM test.waste_batch_risk_score br
         WHERE br.score_date = p_summary_date AND br.risk_tier = 'HIGH'),
        -- Transfer metrics
        (SELECT COUNT(*) FROM test.waste_transfer_recommendations tr
         WHERE tr.recommendation_date = p_summary_date),
        (SELECT COUNT(*) FROM test.waste_transfer_recommendations tr
         WHERE tr.recommendation_date = p_summary_date AND tr.status = 'EXECUTED'),
        (SELECT SUM(tr.net_benefit) FROM test.waste_transfer_recommendations tr
         WHERE tr.recommendation_date = p_summary_date AND tr.status = 'EXECUTED'),
        COUNT(*),
        COUNT(DISTINCT w.goods_code),
        NOW()
    FROM test.waste_daily_detail w
    WHERE w.waste_date = p_summary_date;

    SET v_rows_inserted = v_rows_inserted + ROW_COUNT();

    -- ── DAILY × STORE ────────────────────────────────────────────────────────
    INSERT INTO test.waste_summary (
        period_type, period_start, period_end,
        dimension_type, dimension_value, dimension_name,
        total_waste_qty, total_waste_cost, total_consumption, waste_rate,
        waste_mape, waste_bias,
        batches_critical, batches_high,
        transfers_recommended, transfer_savings,
        record_count, sku_count, computed_at
    )
    SELECT
        'DAILY', p_summary_date, p_summary_date,
        'STORE', CAST(w.shop_dept_id AS CHAR(50)), MAX(w.shop_name),
        SUM(w.waste_qty_total),
        SUM(w.waste_cost),
        SUM(w.consumption_qty),
        SUM(w.waste_qty_total) / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0),
        (SELECT AVG(wcd.v1_abs_pct_error)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date = p_summary_date
           AND wcd.shop_dept_id = w.shop_dept_id
           AND wcd.v1_abs_pct_error IS NOT NULL AND wcd.actual_consumption > 0),
        (SELECT AVG(wcd.v1_forecast_error)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date = p_summary_date
           AND wcd.shop_dept_id = w.shop_dept_id
           AND wcd.v1_forecast_error IS NOT NULL),
        (SELECT COUNT(*) FROM test.waste_batch_risk_score br
         WHERE br.score_date = p_summary_date AND br.shop_dept_id = w.shop_dept_id
           AND br.risk_tier = 'CRITICAL'),
        (SELECT COUNT(*) FROM test.waste_batch_risk_score br
         WHERE br.score_date = p_summary_date AND br.shop_dept_id = w.shop_dept_id
           AND br.risk_tier = 'HIGH'),
        (SELECT COUNT(*) FROM test.waste_transfer_recommendations tr
         WHERE tr.recommendation_date = p_summary_date
           AND tr.source_store_id = w.shop_dept_id),
        (SELECT SUM(tr.net_benefit) FROM test.waste_transfer_recommendations tr
         WHERE tr.recommendation_date = p_summary_date
           AND tr.source_store_id = w.shop_dept_id AND tr.status = 'EXECUTED'),
        COUNT(*),
        COUNT(DISTINCT w.goods_code),
        NOW()
    FROM test.waste_daily_detail w
    WHERE w.waste_date = p_summary_date
    GROUP BY w.shop_dept_id;

    SET v_rows_inserted = v_rows_inserted + ROW_COUNT();

    -- ── DAILY × CATEGORY ─────────────────────────────────────────────────────
    INSERT INTO test.waste_summary (
        period_type, period_start, period_end,
        dimension_type, dimension_value, dimension_name,
        total_waste_qty, total_waste_cost, total_consumption, waste_rate,
        record_count, sku_count, computed_at
    )
    SELECT
        'DAILY', p_summary_date, p_summary_date,
        'CATEGORY', IFNULL(w.large_class_name, 'Unknown'), IFNULL(w.large_class_name, 'Unknown'),
        SUM(w.waste_qty_total),
        SUM(w.waste_cost),
        SUM(w.consumption_qty),
        SUM(w.waste_qty_total) / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0),
        COUNT(*),
        COUNT(DISTINCT w.goods_code),
        NOW()
    FROM test.waste_daily_detail w
    WHERE w.waste_date = p_summary_date
    GROUP BY w.large_class_name;

    SET v_rows_inserted = v_rows_inserted + ROW_COUNT();

    -- ── DAILY × SHELF_TIER ───────────────────────────────────────────────────
    INSERT INTO test.waste_summary (
        period_type, period_start, period_end,
        dimension_type, dimension_value, dimension_name,
        total_waste_qty, total_waste_cost, total_consumption, waste_rate,
        record_count, sku_count, computed_at
    )
    SELECT
        'DAILY', p_summary_date, p_summary_date,
        'SHELF_TIER', IFNULL(w.shelf_life_tier, 'UNKNOWN'), IFNULL(w.shelf_life_tier, 'UNKNOWN'),
        SUM(w.waste_qty_total),
        SUM(w.waste_cost),
        SUM(w.consumption_qty),
        SUM(w.waste_qty_total) / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0),
        COUNT(*),
        COUNT(DISTINCT w.goods_code),
        NOW()
    FROM test.waste_daily_detail w
    WHERE w.waste_date = p_summary_date
    GROUP BY w.shelf_life_tier;

    SET v_rows_inserted = v_rows_inserted + ROW_COUNT();

    -- ── DAILY × DOW ──────────────────────────────────────────────────────────
    INSERT INTO test.waste_summary (
        period_type, period_start, period_end,
        dimension_type, dimension_value, dimension_name,
        total_waste_qty, total_waste_cost, total_consumption, waste_rate,
        record_count, sku_count, computed_at
    )
    SELECT
        'DAILY', p_summary_date, p_summary_date,
        'DOW',
        CAST(DAYOFWEEK(p_summary_date) AS CHAR(10)),
        ELT(DAYOFWEEK(p_summary_date), 'Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'),
        SUM(w.waste_qty_total),
        SUM(w.waste_cost),
        SUM(w.consumption_qty),
        SUM(w.waste_qty_total) / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0),
        COUNT(*),
        COUNT(DISTINCT w.goods_code),
        NOW()
    FROM test.waste_daily_detail w
    WHERE w.waste_date = p_summary_date;

    SET v_rows_inserted = v_rows_inserted + ROW_COUNT();

    -- ======================================================================
    -- ROLLING_7D summaries (OVERALL + STORE)
    -- ======================================================================

    -- ── ROLLING_7D × OVERALL ─────────────────────────────────────────────────
    INSERT INTO test.waste_summary (
        period_type, period_start, period_end,
        dimension_type, dimension_value, dimension_name,
        total_waste_qty, total_waste_cost, total_consumption, waste_rate,
        waste_mape, waste_wmape, waste_bias,
        record_count, sku_count, computed_at
    )
    SELECT
        'ROLLING_7D', v_roll7_start, p_summary_date,
        'OVERALL', 'ALL', 'All Stores (7-Day Rolling)',
        SUM(w.waste_qty_total),
        SUM(w.waste_cost),
        SUM(w.consumption_qty),
        SUM(w.waste_qty_total) / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0),
        (SELECT AVG(wcd.v1_abs_pct_error)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date BETWEEN v_roll7_start AND p_summary_date
           AND wcd.v1_abs_pct_error IS NOT NULL AND wcd.actual_consumption > 0),
        (SELECT SUM(ABS(wcd.v1_forecast - wcd.actual_consumption))
                / NULLIF(SUM(wcd.actual_consumption), 0)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date BETWEEN v_roll7_start AND p_summary_date
           AND wcd.v1_forecast IS NOT NULL AND wcd.actual_consumption > 0),
        (SELECT AVG(wcd.v1_forecast_error)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date BETWEEN v_roll7_start AND p_summary_date
           AND wcd.v1_forecast_error IS NOT NULL),
        COUNT(*),
        COUNT(DISTINCT w.goods_code),
        NOW()
    FROM test.waste_daily_detail w
    WHERE w.waste_date BETWEEN v_roll7_start AND p_summary_date;

    SET v_rows_inserted = v_rows_inserted + ROW_COUNT();

    -- ── ROLLING_7D × STORE ───────────────────────────────────────────────────
    INSERT INTO test.waste_summary (
        period_type, period_start, period_end,
        dimension_type, dimension_value, dimension_name,
        total_waste_qty, total_waste_cost, total_consumption, waste_rate,
        record_count, sku_count, computed_at
    )
    SELECT
        'ROLLING_7D', v_roll7_start, p_summary_date,
        'STORE', CAST(w.shop_dept_id AS CHAR(50)), MAX(w.shop_name),
        SUM(w.waste_qty_total),
        SUM(w.waste_cost),
        SUM(w.consumption_qty),
        SUM(w.waste_qty_total) / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0),
        COUNT(*),
        COUNT(DISTINCT w.goods_code),
        NOW()
    FROM test.waste_daily_detail w
    WHERE w.waste_date BETWEEN v_roll7_start AND p_summary_date
    GROUP BY w.shop_dept_id;

    SET v_rows_inserted = v_rows_inserted + ROW_COUNT();

    -- ======================================================================
    -- ROLLING_30D summaries (OVERALL + STORE)
    -- ======================================================================

    -- ── ROLLING_30D × OVERALL ────────────────────────────────────────────────
    INSERT INTO test.waste_summary (
        period_type, period_start, period_end,
        dimension_type, dimension_value, dimension_name,
        total_waste_qty, total_waste_cost, total_consumption, waste_rate,
        waste_mape, waste_wmape, waste_bias,
        record_count, sku_count, computed_at
    )
    SELECT
        'ROLLING_30D', v_roll30_start, p_summary_date,
        'OVERALL', 'ALL', 'All Stores (30-Day Rolling)',
        SUM(w.waste_qty_total),
        SUM(w.waste_cost),
        SUM(w.consumption_qty),
        SUM(w.waste_qty_total) / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0),
        (SELECT AVG(wcd.v1_abs_pct_error)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date BETWEEN v_roll30_start AND p_summary_date
           AND wcd.v1_abs_pct_error IS NOT NULL AND wcd.actual_consumption > 0),
        (SELECT SUM(ABS(wcd.v1_forecast - wcd.actual_consumption))
                / NULLIF(SUM(wcd.actual_consumption), 0)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date BETWEEN v_roll30_start AND p_summary_date
           AND wcd.v1_forecast IS NOT NULL AND wcd.actual_consumption > 0),
        (SELECT AVG(wcd.v1_forecast_error)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date BETWEEN v_roll30_start AND p_summary_date
           AND wcd.v1_forecast_error IS NOT NULL),
        COUNT(*),
        COUNT(DISTINCT w.goods_code),
        NOW()
    FROM test.waste_daily_detail w
    WHERE w.waste_date BETWEEN v_roll30_start AND p_summary_date;

    SET v_rows_inserted = v_rows_inserted + ROW_COUNT();

    -- ── ROLLING_30D × STORE ──────────────────────────────────────────────────
    INSERT INTO test.waste_summary (
        period_type, period_start, period_end,
        dimension_type, dimension_value, dimension_name,
        total_waste_qty, total_waste_cost, total_consumption, waste_rate,
        record_count, sku_count, computed_at
    )
    SELECT
        'ROLLING_30D', v_roll30_start, p_summary_date,
        'STORE', CAST(w.shop_dept_id AS CHAR(50)), MAX(w.shop_name),
        SUM(w.waste_qty_total),
        SUM(w.waste_cost),
        SUM(w.consumption_qty),
        SUM(w.waste_qty_total) / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0),
        COUNT(*),
        COUNT(DISTINCT w.goods_code),
        NOW()
    FROM test.waste_daily_detail w
    WHERE w.waste_date BETWEEN v_roll30_start AND p_summary_date
    GROUP BY w.shop_dept_id;

    SET v_rows_inserted = v_rows_inserted + ROW_COUNT();

    -- ======================================================================
    -- MONTHLY summary (OVERALL only — run once per day, latest month)
    -- ======================================================================

    INSERT INTO test.waste_summary (
        period_type, period_start, period_end,
        dimension_type, dimension_value, dimension_name,
        total_waste_qty, total_waste_cost, total_consumption, waste_rate,
        waste_mape, waste_wmape, waste_bias,
        batches_critical, batches_high,
        transfers_recommended, transfers_executed, transfer_savings,
        record_count, sku_count, computed_at
    )
    SELECT
        'MONTHLY', v_month_start, v_month_end,
        'OVERALL', DATE_FORMAT(p_summary_date, '%Y-%m'), CONCAT('Month of ', DATE_FORMAT(p_summary_date, '%Y-%m')),
        SUM(w.waste_qty_total),
        SUM(w.waste_cost),
        SUM(w.consumption_qty),
        SUM(w.waste_qty_total) / NULLIF(SUM(w.waste_qty_total) + SUM(IFNULL(w.consumption_qty, 0)), 0),
        (SELECT AVG(wcd.v1_abs_pct_error)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date BETWEEN v_month_start AND p_summary_date
           AND wcd.v1_abs_pct_error IS NOT NULL AND wcd.actual_consumption > 0),
        (SELECT SUM(ABS(wcd.v1_forecast - wcd.actual_consumption))
                / NULLIF(SUM(wcd.actual_consumption), 0)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date BETWEEN v_month_start AND p_summary_date
           AND wcd.v1_forecast IS NOT NULL AND wcd.actual_consumption > 0),
        (SELECT AVG(wcd.v1_forecast_error)
         FROM test.waste_consumption_daily wcd
         WHERE wcd.consumption_date BETWEEN v_month_start AND p_summary_date
           AND wcd.v1_forecast_error IS NOT NULL),
        (SELECT COUNT(*) FROM test.waste_batch_risk_score br
         WHERE br.score_date BETWEEN v_month_start AND p_summary_date
           AND br.risk_tier = 'CRITICAL'),
        (SELECT COUNT(*) FROM test.waste_batch_risk_score br
         WHERE br.score_date BETWEEN v_month_start AND p_summary_date
           AND br.risk_tier = 'HIGH'),
        (SELECT COUNT(*) FROM test.waste_transfer_recommendations tr
         WHERE tr.recommendation_date BETWEEN v_month_start AND p_summary_date),
        (SELECT COUNT(*) FROM test.waste_transfer_recommendations tr
         WHERE tr.recommendation_date BETWEEN v_month_start AND p_summary_date
           AND tr.status = 'EXECUTED'),
        (SELECT SUM(tr.net_benefit) FROM test.waste_transfer_recommendations tr
         WHERE tr.recommendation_date BETWEEN v_month_start AND p_summary_date
           AND tr.status = 'EXECUTED'),
        COUNT(*),
        COUNT(DISTINCT w.goods_code),
        NOW()
    FROM test.waste_daily_detail w
    WHERE w.waste_date BETWEEN v_month_start AND p_summary_date;

    SET v_rows_inserted = v_rows_inserted + ROW_COUNT();

    -- ── Return summary ───────────────────────────────────────────────────────
    SELECT 'sp_compute_waste_summary' AS procedure_name,
           p_summary_date            AS summary_date,
           v_rows_inserted           AS summary_rows_created,
           (SELECT COUNT(*) FROM test.waste_summary
            WHERE period_type = 'DAILY' AND period_start = p_summary_date
           )                         AS daily_summaries,
           (SELECT COUNT(*) FROM test.waste_summary
            WHERE period_type = 'ROLLING_7D' AND period_start = v_roll7_start
           )                         AS rolling_7d_summaries,
           (SELECT COUNT(*) FROM test.waste_summary
            WHERE period_type = 'ROLLING_30D' AND period_start = v_roll30_start
           )                         AS rolling_30d_summaries,
           (SELECT COUNT(*) FROM test.waste_summary
            WHERE period_type = 'MONTHLY' AND period_start = v_month_start
           )                         AS monthly_summaries,
           NOW()                     AS completed_at;
END$$

DELIMITER ;
