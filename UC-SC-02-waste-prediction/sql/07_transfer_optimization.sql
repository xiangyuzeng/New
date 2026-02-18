-- ============================================================================
-- UC-SC-02: Waste Prediction & Reduction — Cross-Store Transfer Optimization
-- ============================================================================
-- Stored Procedure: sp_compute_transfer_recommendations
-- Purpose:  For high-risk batches (CRITICAL/HIGH tier with >8h to expiry),
--           identify neighboring stores with demand deficit and recommend
--           transfers that produce positive net benefit (savings > logistics).
-- Depends:  06_risk_scoring.sql  (batch risk scores must exist for score_date)
--           05_consumption_forecast.sql  (v1_forecast for demand at dest stores)
--           Store distance matrix is hard-coded for 10 Manhattan stores.
-- Idempotency: DELETE-then-INSERT for the target recommendation_date.
-- Author:   DBA/Infrastructure Team
-- Created:  2026-02-18
-- ============================================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS test.sp_compute_transfer_recommendations$$

CREATE PROCEDURE test.sp_compute_transfer_recommendations(
    IN p_recommendation_date DATE
)
BEGIN
    DECLARE v_rows_recs      INT DEFAULT 0;
    DECLARE v_transfer_cost  DECIMAL(10,2) DEFAULT 5.00;  -- $ per trip
    DECLARE v_min_benefit    DECIMAL(10,2) DEFAULT 2.00;  -- minimum net benefit
    DECLARE v_max_distance   DECIMAL(5,2)  DEFAULT 0.50;  -- miles

    -- ── Step 1: Delete existing recommendations for the date (idempotency) ──
    DELETE FROM test.waste_transfer_recommendations
    WHERE recommendation_date = p_recommendation_date;

    -- ── Step 2: Create temporary store distance matrix ──────────────────────
    -- Manhattan stores within 0.5 miles walking distance.
    -- 16 bidirectional pairs from config.py STORE_DISTANCES.

    DROP TEMPORARY TABLE IF EXISTS tmp_store_distances;
    CREATE TEMPORARY TABLE tmp_store_distances (
        source_store_id  BIGINT NOT NULL,
        dest_store_id    BIGINT NOT NULL,
        distance_miles   DECIMAL(5,2) NOT NULL,
        PRIMARY KEY (source_store_id, dest_store_id)
    );

    INSERT INTO tmp_store_distances (source_store_id, dest_store_id, distance_miles) VALUES
        (1127,  1140,  0.40), (1140,  1127,  0.40),
        (1127,  20032, 0.35), (20032, 1127,  0.35),
        (1128,  20008, 0.45), (20008, 1128,  0.45),
        (1140,  20031, 0.30), (20031, 1140,  0.30),
        (1141,  20010, 0.40), (20010, 1141,  0.40),
        (20008, 20010, 0.35), (20010, 20008, 0.35),
        (20011, 20027, 0.45), (20027, 20011, 0.45),
        (20027, 20032, 0.30), (20032, 20027, 0.30);

    -- ── Step 3: Build source candidates (excess at high-risk stores) ────────
    -- Source = stores with CRITICAL/HIGH risk batches AND hours_remaining > 8
    -- (need enough time for the transfer to happen)

    DROP TEMPORARY TABLE IF EXISTS tmp_transfer_sources;
    CREATE TEMPORARY TABLE tmp_transfer_sources (
        shop_dept_id     BIGINT NOT NULL,
        goods_code       VARCHAR(32) NOT NULL,
        batch_id         VARCHAR(64),
        hours_remaining  DECIMAL(8,1),
        risk_score       DECIMAL(5,2),
        risk_tier        VARCHAR(10),
        current_stock_qty DECIMAL(12,2),
        forecast_consumption_24h DECIMAL(12,2),
        excess_qty       DECIMAL(12,2),
        INDEX idx_store_goods (shop_dept_id, goods_code)
    );

    INSERT INTO tmp_transfer_sources (
        shop_dept_id, goods_code, batch_id, hours_remaining,
        risk_score, risk_tier, current_stock_qty,
        forecast_consumption_24h, excess_qty
    )
    SELECT
        br.shop_dept_id,
        br.goods_code,
        br.batch_id,
        br.hours_remaining,
        br.risk_score,
        br.risk_tier,
        IFNULL(br.current_stock_qty, 0),
        IFNULL(br.forecast_consumption_24h, 0),
        -- Excess = stock that won't be consumed before expiry
        GREATEST(0,
            IFNULL(br.current_stock_qty, 0)
            - IFNULL(br.forecast_consumption_24h, 0)
        ) AS excess_qty
    FROM test.waste_batch_risk_score br
    WHERE br.score_date = p_recommendation_date
      AND br.risk_tier IN ('CRITICAL', 'HIGH')
      AND br.hours_remaining > 8
      AND IFNULL(br.current_stock_qty, 0) > IFNULL(br.forecast_consumption_24h, 0);

    -- ── Step 4: Build destination candidates (deficit at nearby stores) ──────
    -- Destination = stores where forecast_consumption > current stock for the SKU

    DROP TEMPORARY TABLE IF EXISTS tmp_transfer_dests;
    CREATE TEMPORARY TABLE tmp_transfer_dests (
        shop_dept_id     BIGINT NOT NULL,
        goods_code       VARCHAR(32) NOT NULL,
        current_stock_qty DECIMAL(12,2),
        forecast_consumption_24h DECIMAL(12,2),
        deficit_qty      DECIMAL(12,2),
        INDEX idx_store_goods (shop_dept_id, goods_code)
    );

    -- Use consumption forecast to estimate demand at potential destinations.
    -- A store has a deficit if its forecasted demand exceeds its stock.
    INSERT INTO tmp_transfer_dests (
        shop_dept_id, goods_code, current_stock_qty,
        forecast_consumption_24h, deficit_qty
    )
    SELECT
        wcd.shop_dept_id,
        wcd.goods_code,
        -- Approximate current stock from recent stock changes
        ABS(IFNULL(stk.net_stock_qty, 0)) AS current_stock_qty,
        IFNULL(wcd.v1_forecast, wcd.consumption_7d_avg) AS forecast_consumption_24h,
        GREATEST(0,
            IFNULL(wcd.v1_forecast, wcd.consumption_7d_avg)
            - ABS(IFNULL(stk.net_stock_qty, 0))
        ) AS deficit_qty
    FROM test.waste_consumption_daily wcd
    LEFT JOIN (
        SELECT sc.shop_dept_id, sc.goods_mid AS goods_code,
               SUM(sc.total_adjust_num) AS net_stock_qty
        FROM test.tmp_stock_changes sc
        WHERE sc.shop_dept_id IN (1127,1128,1140,1141,20008,20010,20011,20027,20031,20032)
          AND DATE(sc.operated_time) >= DATE_SUB(p_recommendation_date, INTERVAL 3 DAY)
        GROUP BY sc.shop_dept_id, sc.goods_mid
    ) stk ON wcd.shop_dept_id = stk.shop_dept_id
          AND wcd.goods_code   = stk.goods_code
    WHERE wcd.consumption_date = p_recommendation_date
      AND wcd.shop_dept_id IN (1127,1128,1140,1141,20008,20010,20011,20027,20031,20032)
      -- Only include if there's actual demand and a deficit
      AND IFNULL(wcd.v1_forecast, wcd.consumption_7d_avg) >
          ABS(IFNULL(stk.net_stock_qty, 0));

    -- ── Step 5: Match sources to destinations via distance matrix ────────────
    -- For each source batch, find the best destination (highest deficit, closest)

    INSERT INTO test.waste_transfer_recommendations (
        recommendation_date,
        source_store_id, dest_store_id,
        goods_code,
        transfer_qty,
        source_excess_qty, dest_deficit_qty,
        source_hours_to_expiry, source_risk_score,
        waste_savings_est, transfer_cost_est, net_benefit,
        status, computed_at
    )
    SELECT
        p_recommendation_date,
        src.shop_dept_id                          AS source_store_id,
        dst.shop_dept_id                          AS dest_store_id,
        src.goods_code,
        -- Transfer qty = MIN(source excess, dest deficit)
        LEAST(src.excess_qty, dst.deficit_qty)    AS transfer_qty,
        src.excess_qty                            AS source_excess_qty,
        dst.deficit_qty                           AS dest_deficit_qty,
        src.hours_remaining                       AS source_hours_to_expiry,
        src.risk_score                            AS source_risk_score,
        -- Waste savings estimate: transfer_qty * assumed unit cost ($1.50 avg)
        ROUND(LEAST(src.excess_qty, dst.deficit_qty) * 1.50, 2)
                                                  AS waste_savings_est,
        v_transfer_cost                           AS transfer_cost_est,
        -- Net benefit = savings - transfer cost
        ROUND(LEAST(src.excess_qty, dst.deficit_qty) * 1.50 - v_transfer_cost, 2)
                                                  AS net_benefit,
        'PENDING'                                 AS status,
        NOW()                                     AS computed_at
    FROM tmp_transfer_sources src
    -- Join to distance matrix to find eligible destinations
    JOIN tmp_store_distances sd
      ON src.shop_dept_id = sd.source_store_id
     AND sd.distance_miles <= v_max_distance
    -- Join to destination candidates on same SKU
    JOIN tmp_transfer_dests dst
      ON sd.dest_store_id = dst.shop_dept_id
     AND src.goods_code   = dst.goods_code
    -- Only recommend if net benefit is positive
    WHERE ROUND(LEAST(src.excess_qty, dst.deficit_qty) * 1.50 - v_transfer_cost, 2)
          >= v_min_benefit
    -- Deduplicate: for each source (store, SKU), pick the best destination
    -- (highest deficit first, then closest)
    AND dst.shop_dept_id = (
        SELECT dst2.shop_dept_id
        FROM tmp_transfer_dests dst2
        JOIN tmp_store_distances sd2
          ON src.shop_dept_id = sd2.source_store_id
         AND dst2.shop_dept_id = sd2.dest_store_id
         AND sd2.distance_miles <= v_max_distance
        WHERE dst2.goods_code = src.goods_code
          AND ROUND(LEAST(src.excess_qty, dst2.deficit_qty) * 1.50 - v_transfer_cost, 2)
              >= v_min_benefit
        ORDER BY dst2.deficit_qty DESC, sd2.distance_miles ASC
        LIMIT 1
    );

    SET v_rows_recs = ROW_COUNT();

    -- ── Step 6: Enrich with store and product names ─────────────────────────

    UPDATE test.waste_transfer_recommendations tr
    LEFT JOIN test.tmp_stores src_s ON tr.source_store_id = src_s.dept_id
    LEFT JOIN test.tmp_stores dst_s ON tr.dest_store_id   = dst_s.dept_id
    LEFT JOIN test.tmp_goods  g    ON tr.goods_code       = g.goods_code
    SET tr.source_store_name = src_s.shop_name,
        tr.dest_store_name   = dst_s.shop_name,
        tr.goods_name        = g.goods_name
    WHERE tr.recommendation_date = p_recommendation_date;

    -- ── Step 7: Update batch risk scores with transfer candidate store ──────

    UPDATE test.waste_batch_risk_score br
    JOIN test.waste_transfer_recommendations tr
      ON  br.score_date    = tr.recommendation_date
      AND br.shop_dept_id  = tr.source_store_id
      AND br.goods_code    = tr.goods_code
    SET br.transfer_candidate_store = tr.dest_store_id
    WHERE br.score_date = p_recommendation_date
      AND tr.status = 'PENDING';

    -- ── Clean up temporary tables ───────────────────────────────────────────
    DROP TEMPORARY TABLE IF EXISTS tmp_store_distances;
    DROP TEMPORARY TABLE IF EXISTS tmp_transfer_sources;
    DROP TEMPORARY TABLE IF EXISTS tmp_transfer_dests;

    -- ── Return summary ─────────────────────────────────────────────────────
    SELECT 'sp_compute_transfer_recommendations' AS procedure_name,
           p_recommendation_date                 AS recommendation_date,
           v_rows_recs                           AS recommendations_generated,
           (SELECT COUNT(DISTINCT source_store_id)
            FROM test.waste_transfer_recommendations
            WHERE recommendation_date = p_recommendation_date
           )                                     AS source_stores_count,
           (SELECT COUNT(DISTINCT dest_store_id)
            FROM test.waste_transfer_recommendations
            WHERE recommendation_date = p_recommendation_date
           )                                     AS dest_stores_count,
           (SELECT COUNT(DISTINCT goods_code)
            FROM test.waste_transfer_recommendations
            WHERE recommendation_date = p_recommendation_date
           )                                     AS distinct_skus,
           (SELECT SUM(transfer_qty)
            FROM test.waste_transfer_recommendations
            WHERE recommendation_date = p_recommendation_date
           )                                     AS total_transfer_qty,
           (SELECT SUM(net_benefit)
            FROM test.waste_transfer_recommendations
            WHERE recommendation_date = p_recommendation_date
           )                                     AS total_net_benefit,
           NOW()                                 AS completed_at;
END$$

DELIMITER ;
