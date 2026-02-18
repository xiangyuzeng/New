-- ============================================================================
-- UC-SC-02: Waste Prediction & Reduction — Batch-Level Risk Scoring
-- ============================================================================
-- Stored Procedure: sp_compute_batch_risk_scores
-- Purpose:  Score each active batch (store × SKU with expiry tracking) on a
--           0-100 risk scale combining expiry urgency, excess inventory,
--           demand volatility, and shelf-life tier penalty.  Assign risk tiers
--           and recommended actions (HOLD / PROMOTE / TRANSFER / DISCOUNT / DISPOSE).
-- Depends:  04_consumption_features.sql  (rolling averages, stddev)
--           05_consumption_forecast.sql  (v1_forecast for forward-looking demand)
--           03_waste_landscape.sql       (shelf-life config)
--           Python orchestrator must have loaded:
--             tmp_expiry_prints (batch-level expiry timestamps)
--             tmp_stock_changes (for current on-hand estimation)
-- Idempotency: DELETE-then-INSERT for the target score_date.
-- Author:   DBA/Infrastructure Team
-- Created:  2026-02-18
-- ============================================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS test.sp_compute_batch_risk_scores$$

CREATE PROCEDURE test.sp_compute_batch_risk_scores(
    IN p_score_date DATE
)
BEGIN
    DECLARE v_rows_scored  INT DEFAULT 0;
    DECLARE v_rows_action  INT DEFAULT 0;

    -- ── Step 1: Delete existing scores for the date (idempotency) ────────────
    DELETE FROM test.waste_batch_risk_score
    WHERE score_date = p_score_date;

    -- ── Step 2: Insert base batch records from expiry print log ──────────────
    -- Each (store, SKU, batch) with an expiry timestamp becomes a scorable row.
    -- We use the latest expiry print per (store, SKU, collection_code) as batch.

    INSERT INTO test.waste_batch_risk_score (
        score_date, shop_dept_id, goods_code,
        batch_id, expiry_time,
        hours_remaining,
        computed_at
    )
    SELECT
        p_score_date                                       AS score_date,
        ep.dept_id                                         AS shop_dept_id,
        ep.spec_mid                                        AS goods_code,
        ep.collection_code                                 AS batch_id,
        ep.expire_time                                     AS expiry_time,
        TIMESTAMPDIFF(SECOND, NOW(), ep.expire_time) / 3600.0 AS hours_remaining,
        NOW()                                              AS computed_at
    FROM (
        -- Deduplicate: latest print per (store, SKU, collection_code)
        SELECT dept_id, spec_mid, collection_code, expire_time,
               ROW_NUMBER() OVER (
                   PARTITION BY dept_id, spec_mid, collection_code
                   ORDER BY print_time DESC
               ) AS rn
        FROM test.tmp_expiry_prints
        WHERE dept_id IN (1127,1128,1140,1141,20008,20010,20011,20027,20031,20032)
          AND expire_time >= NOW()  -- only future-expiring batches
    ) ep
    WHERE ep.rn = 1;

    SET v_rows_scored = ROW_COUNT();

    -- ── Step 3: Enrich with current stock estimate ───────────────────────────
    -- Approximate current on-hand = most recent day's net stock movement.
    -- This is a simplification; full inventory snapshot would be more accurate.

    UPDATE test.waste_batch_risk_score br
    LEFT JOIN (
        SELECT sc.shop_dept_id, sc.goods_mid AS goods_code,
               SUM(sc.total_adjust_num) AS net_stock_qty
        FROM test.tmp_stock_changes sc
        WHERE sc.shop_dept_id IN (1127,1128,1140,1141,20008,20010,20011,20027,20031,20032)
          AND DATE(sc.operated_time) >= DATE_SUB(p_score_date, INTERVAL 3 DAY)
        GROUP BY sc.shop_dept_id, sc.goods_mid
    ) stk ON br.shop_dept_id = stk.shop_dept_id
          AND br.goods_code   = stk.goods_code
    SET br.current_stock_qty = ABS(IFNULL(stk.net_stock_qty, 0))
    WHERE br.score_date = p_score_date;

    -- ── Step 4: Enrich with forecast consumption (24h and 48h) ───────────────
    -- Use v1_forecast from waste_consumption_daily as the daily rate,
    -- then scale to 24h and 48h windows.

    UPDATE test.waste_batch_risk_score br
    LEFT JOIN test.waste_consumption_daily wcd
      ON  br.shop_dept_id    = wcd.shop_dept_id
      AND br.goods_code      = wcd.goods_code
      AND wcd.consumption_date = p_score_date
    SET br.forecast_consumption_24h = IFNULL(wcd.v1_forecast, wcd.consumption_7d_avg),
        br.forecast_consumption_48h = IFNULL(wcd.v1_forecast, wcd.consumption_7d_avg) * 2
    WHERE br.score_date = p_score_date;

    -- ── Step 5: Compute 4-component risk score ───────────────────────────────
    -- risk_score = 40% * expiry_urgency
    --            + 30% * excess_inventory
    --            + 20% * volatility
    --            + 10% * shelf_tier_penalty

    UPDATE test.waste_batch_risk_score br
    LEFT JOIN test.waste_consumption_daily wcd
      ON  br.shop_dept_id    = wcd.shop_dept_id
      AND br.goods_code      = wcd.goods_code
      AND wcd.consumption_date = p_score_date
    LEFT JOIN test.waste_shelf_life_config slc
      ON br.goods_code = slc.goods_code
    SET br.risk_score = ROUND(
        100.0 * (
            -- Component 1: Expiry urgency (40% weight)
            0.40 * (
                CASE
                    WHEN br.hours_remaining <= 4  THEN 1.0
                    WHEN br.hours_remaining <= 8  THEN 0.8
                    WHEN br.hours_remaining <= 24 THEN 0.5
                    WHEN br.hours_remaining <= 48 THEN 0.3
                    ELSE 0.1
                END
            )
            -- Component 2: Excess inventory (30% weight)
            -- Higher when stock exceeds forecast consumption before expiry
          + 0.30 * LEAST(1.0,
                GREATEST(0,
                    (IFNULL(br.current_stock_qty, 0)
                     - CASE
                         WHEN br.hours_remaining <= 24
                         THEN IFNULL(br.forecast_consumption_24h, 0)
                         ELSE IFNULL(br.forecast_consumption_48h, 0)
                       END
                    )
                    / NULLIF(br.current_stock_qty, 0)
                )
            )
            -- Component 3: Demand volatility (20% weight)
            -- Higher coefficient of variation = less predictable demand
          + 0.20 * LEAST(1.0,
                IFNULL(wcd.consumption_7d_stddev, 0)
                / NULLIF(IFNULL(wcd.consumption_7d_avg, 0), 0)
            )
            -- Component 4: Shelf-life tier penalty (10% weight)
          + 0.10 * (
                CASE IFNULL(slc.shelf_life_tier, 'LONG')
                    WHEN 'ULTRA_SHORT' THEN 1.0
                    WHEN 'SHORT'       THEN 0.6
                    WHEN 'MEDIUM'      THEN 0.3
                    WHEN 'LONG'        THEN 0.1
                    ELSE 0.1
                END
            )
        )
    , 2)
    WHERE br.score_date = p_score_date;

    -- ── Step 6: Assign risk tier ─────────────────────────────────────────────

    UPDATE test.waste_batch_risk_score
    SET risk_tier = CASE
        WHEN risk_score >= 80 THEN 'CRITICAL'
        WHEN risk_score >= 60 THEN 'HIGH'
        WHEN risk_score >= 40 THEN 'MEDIUM'
        ELSE 'LOW'
    END
    WHERE score_date = p_score_date;

    -- ── Step 7: Assign recommended action ────────────────────────────────────

    UPDATE test.waste_batch_risk_score
    SET recommended_action = CASE
        -- CRITICAL risk with very little time: dispose immediately
        WHEN risk_tier = 'CRITICAL' AND hours_remaining < 4
            THEN 'DISPOSE'
        -- CRITICAL risk but time for transfer: try cross-store transfer
        WHEN risk_tier = 'CRITICAL' AND hours_remaining >= 4
            THEN 'TRANSFER'
        -- HIGH risk: promote usage (prioritize in production/sales)
        WHEN risk_tier = 'HIGH'
            THEN 'PROMOTE'
        -- MEDIUM risk: discount to accelerate sell-through
        WHEN risk_tier = 'MEDIUM' AND hours_remaining < 24
            THEN 'DISCOUNT'
        -- Default: hold and monitor
        ELSE 'HOLD'
    END
    WHERE score_date = p_score_date;

    SET v_rows_action = ROW_COUNT();

    -- ── Return summary ──────────────────────────────────────────────────────
    SELECT 'sp_compute_batch_risk_scores' AS procedure_name,
           p_score_date                  AS score_date,
           v_rows_scored                 AS batches_scored,
           v_rows_action                 AS batches_with_action,
           (SELECT COUNT(*) FROM test.waste_batch_risk_score
            WHERE score_date = p_score_date AND risk_tier = 'CRITICAL'
           )                             AS critical_count,
           (SELECT COUNT(*) FROM test.waste_batch_risk_score
            WHERE score_date = p_score_date AND risk_tier = 'HIGH'
           )                             AS high_count,
           (SELECT COUNT(*) FROM test.waste_batch_risk_score
            WHERE score_date = p_score_date AND risk_tier = 'MEDIUM'
           )                             AS medium_count,
           (SELECT COUNT(*) FROM test.waste_batch_risk_score
            WHERE score_date = p_score_date AND risk_tier = 'LOW'
           )                             AS low_count,
           (SELECT AVG(risk_score) FROM test.waste_batch_risk_score
            WHERE score_date = p_score_date
           )                             AS avg_risk_score,
           NOW()                         AS completed_at;
END$$

DELIMITER ;
