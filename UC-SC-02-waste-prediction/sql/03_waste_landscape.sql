-- ============================================================================
-- UC-SC-02: Waste Prediction & Reduction — Waste Landscape Computation
-- ============================================================================
-- Stored Procedure: sp_compute_waste_landscape
-- Purpose:  Compute daily waste detail from disposal records, enrich with
--           shelf-life config, consumption data, and master data.
-- Depends:  02_create_analytics_schema.sql (tables must exist)
--           Python orchestrator must have loaded staging tables first:
--             tmp_abandon_tasks, tmp_expiry_prints, tmp_shelf_life_config,
--             tmp_goods, tmp_stores, tmp_stock_changes
-- Idempotency: DELETE-then-INSERT for the target date range.
-- Author:   DBA/Infrastructure Team
-- Created:  2026-02-18
-- ============================================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS test.sp_compute_waste_landscape$$

CREATE PROCEDURE test.sp_compute_waste_landscape(
    IN p_start_date DATE,
    IN p_end_date   DATE
)
BEGIN
    DECLARE v_rows_shelf   INT DEFAULT 0;
    DECLARE v_rows_waste   INT DEFAULT 0;
    DECLARE v_rows_enrich  INT DEFAULT 0;

    -- ── Step 1: Sync shelf-life config to analytics table ──────────────────
    -- Idempotent: REPLACE INTO handles upsert by unique index on goods_code.

    REPLACE INTO test.waste_shelf_life_config (
        goods_code, goods_name, large_class_name,
        open_expiry_hours, container_expiry_hours, thaw_expiry_hours,
        min_expiry_hours, shelf_life_tier, is_active, synced_at
    )
    SELECT
        sc.spec_mid                                     AS goods_code,
        COALESCE(g.goods_name, sc.goods_name)           AS goods_name,
        g.large_class_name,
        -- Convert to hours: time_unit 1=days(*24), 2=hours
        CASE WHEN sc.open_time_unit = 1
             THEN sc.open_time_data * 24
             ELSE sc.open_time_data END                 AS open_expiry_hours,
        CASE WHEN sc.container_time_unit = 1
             THEN sc.container_time_data * 24
             ELSE sc.container_time_data END             AS container_expiry_hours,
        CASE WHEN sc.thaw_time_unit = 1
             THEN sc.thaw_time_data * 24
             ELSE sc.thaw_time_data END                  AS thaw_expiry_hours,
        -- min_expiry_hours = MIN of non-null converted values
        LEAST(
            COALESCE(CASE WHEN sc.open_time_unit = 1
                          THEN sc.open_time_data * 24
                          ELSE sc.open_time_data END, 999999),
            COALESCE(CASE WHEN sc.container_time_unit = 1
                          THEN sc.container_time_data * 24
                          ELSE sc.container_time_data END, 999999),
            COALESCE(CASE WHEN sc.thaw_time_unit = 1
                          THEN sc.thaw_time_data * 24
                          ELSE sc.thaw_time_data END, 999999)
        )                                                AS min_expiry_hours,
        -- Tier classification
        CASE
            WHEN LEAST(
                    COALESCE(CASE WHEN sc.open_time_unit = 1 THEN sc.open_time_data * 24 ELSE sc.open_time_data END, 999999),
                    COALESCE(CASE WHEN sc.container_time_unit = 1 THEN sc.container_time_data * 24 ELSE sc.container_time_data END, 999999),
                    COALESCE(CASE WHEN sc.thaw_time_unit = 1 THEN sc.thaw_time_data * 24 ELSE sc.thaw_time_data END, 999999)
                 ) < 24    THEN 'ULTRA_SHORT'
            WHEN LEAST(
                    COALESCE(CASE WHEN sc.open_time_unit = 1 THEN sc.open_time_data * 24 ELSE sc.open_time_data END, 999999),
                    COALESCE(CASE WHEN sc.container_time_unit = 1 THEN sc.container_time_data * 24 ELSE sc.container_time_data END, 999999),
                    COALESCE(CASE WHEN sc.thaw_time_unit = 1 THEN sc.thaw_time_data * 24 ELSE sc.thaw_time_data END, 999999)
                 ) < 72    THEN 'SHORT'
            WHEN LEAST(
                    COALESCE(CASE WHEN sc.open_time_unit = 1 THEN sc.open_time_data * 24 ELSE sc.open_time_data END, 999999),
                    COALESCE(CASE WHEN sc.container_time_unit = 1 THEN sc.container_time_data * 24 ELSE sc.container_time_data END, 999999),
                    COALESCE(CASE WHEN sc.thaw_time_unit = 1 THEN sc.thaw_time_data * 24 ELSE sc.thaw_time_data END, 999999)
                 ) <= 336  THEN 'MEDIUM'
            ELSE 'LONG'
        END                                              AS shelf_life_tier,
        1                                                AS is_active,
        NOW()                                            AS synced_at
    FROM test.tmp_shelf_life_config sc
    LEFT JOIN test.tmp_goods g ON sc.spec_mid = g.goods_code
    WHERE sc.is_deleted = 0;

    SET v_rows_shelf = ROW_COUNT();

    -- ── Step 2: Delete existing waste detail for date range (idempotency) ──
    DELETE FROM test.waste_daily_detail
    WHERE waste_date BETWEEN p_start_date AND p_end_date;

    -- ── Step 3: Insert daily waste from disposal/abandon tasks ─────────────
    INSERT INTO test.waste_daily_detail (
        waste_date, shop_dept_id, goods_code,
        waste_qty_normal, waste_qty_frozen, waste_qty_refrigerated,
        waste_qty_total, storage_type,
        abandon_task_ids, computed_at
    )
    SELECT
        DATE(a.abandoned_date)                           AS waste_date,
        a.dept_id                                        AS shop_dept_id,
        a.spec_mid                                       AS goods_code,
        SUM(IFNULL(a.abandon_amount_normal, 0))          AS waste_qty_normal,
        SUM(IFNULL(a.abandon_amount_frozen, 0))          AS waste_qty_frozen,
        SUM(IFNULL(a.abandon_amount_refrigerated, 0))    AS waste_qty_refrigerated,
        SUM(IFNULL(a.abandon_amount_normal, 0)
          + IFNULL(a.abandon_amount_frozen, 0)
          + IFNULL(a.abandon_amount_refrigerated, 0))    AS waste_qty_total,
        -- Dominant storage type
        CASE
            WHEN SUM(IFNULL(a.abandon_amount_frozen, 0)) >=
                 GREATEST(SUM(IFNULL(a.abandon_amount_normal, 0)),
                          SUM(IFNULL(a.abandon_amount_refrigerated, 0)))
                 THEN 'FROZEN'
            WHEN SUM(IFNULL(a.abandon_amount_refrigerated, 0)) >=
                 SUM(IFNULL(a.abandon_amount_normal, 0))
                 THEN 'REFRIGERATED'
            ELSE 'NORMAL'
        END                                              AS storage_type,
        GROUP_CONCAT(DISTINCT a.id ORDER BY a.id SEPARATOR ',') AS abandon_task_ids,
        NOW()                                            AS computed_at
    FROM test.tmp_abandon_tasks a
    WHERE a.dept_id IN (1127,1128,1140,1141,20008,20010,20011,20027,20031,20032)
      AND DATE(a.abandoned_date) BETWEEN p_start_date AND p_end_date
    GROUP BY DATE(a.abandoned_date), a.dept_id, a.spec_mid
    HAVING waste_qty_total > 0;

    SET v_rows_waste = ROW_COUNT();

    -- ── Step 4: Enrich with expiry label counts ────────────────────────────
    UPDATE test.waste_daily_detail w
    JOIN (
        SELECT DATE(e.print_time) AS print_date,
               e.dept_id,
               e.spec_mid,
               COUNT(*)           AS label_count
        FROM test.tmp_expiry_prints e
        WHERE e.dept_id IN (1127,1128,1140,1141,20008,20010,20011,20027,20031,20032)
          AND DATE(e.print_time) BETWEEN p_start_date AND p_end_date
        GROUP BY DATE(e.print_time), e.dept_id, e.spec_mid
    ) ep ON w.waste_date    = ep.print_date
         AND w.shop_dept_id = ep.dept_id
         AND w.goods_code   = ep.spec_mid
    SET w.expiry_print_count = ep.label_count
    WHERE w.waste_date BETWEEN p_start_date AND p_end_date;

    -- ── Step 5: Enrich with consumption data and compute waste_pct ─────────
    UPDATE test.waste_daily_detail w
    JOIN test.waste_consumption_daily c
      ON  w.waste_date    = c.consumption_date
      AND w.shop_dept_id  = c.shop_dept_id
      AND w.goods_code    = c.goods_code
    SET w.consumption_qty = c.actual_consumption,
        w.waste_pct = CASE
            WHEN (c.actual_consumption + w.waste_qty_total) > 0
            THEN w.waste_qty_total / (c.actual_consumption + w.waste_qty_total)
            ELSE NULL
        END
    WHERE w.waste_date BETWEEN p_start_date AND p_end_date;

    -- ── Step 6: Enrich with shelf-life tier from config ────────────────────
    UPDATE test.waste_daily_detail w
    JOIN test.waste_shelf_life_config slc
      ON w.goods_code = slc.goods_code
    SET w.shelf_life_tier  = slc.shelf_life_tier,
        w.shelf_life_hours = slc.min_expiry_hours
    WHERE w.waste_date BETWEEN p_start_date AND p_end_date;

    -- ── Step 7: Enrich with product and store names from master data ───────
    UPDATE test.waste_daily_detail w
    LEFT JOIN test.tmp_goods g   ON w.goods_code   = g.goods_code
    LEFT JOIN test.tmp_stores s  ON w.shop_dept_id = s.dept_id
    SET w.goods_name       = g.goods_name,
        w.large_class_name = g.large_class_name,
        w.shop_name        = s.shop_name
    WHERE w.waste_date BETWEEN p_start_date AND p_end_date;

    SET v_rows_enrich = ROW_COUNT();

    -- ── Return summary ─────────────────────────────────────────────────────
    SELECT 'sp_compute_waste_landscape' AS procedure_name,
           p_start_date                AS date_start,
           p_end_date                  AS date_end,
           v_rows_shelf                AS shelf_life_configs_synced,
           v_rows_waste                AS waste_detail_rows_inserted,
           v_rows_enrich               AS rows_enriched_with_names,
           NOW()                       AS completed_at;
END$$

DELIMITER ;
