-- ============================================================================
-- UC-SC-02: Waste Prediction & Reduction — Master Daily Refresh
-- ============================================================================
-- Stored Procedure: sp_waste_daily_refresh
-- Purpose:  Orchestrate the full stored-procedure chain in the correct order.
--           Designed to be called by the Python orchestrator AFTER extraction
--           steps have loaded staging tables, or by the MySQL EVENT scheduler
--           for lightweight (SP-only) daily refresh.
-- Order:
--   1. sp_build_consumption_features   (date range)
--   2. sp_compute_waste_landscape      (date range)
--   3. sp_compute_consumption_forecast (date range)
--   4. sp_compute_batch_risk_scores    (single date)
--   5. sp_compute_transfer_recommendations (single date)
--   6. sp_compute_waste_summary        (single date)
--   7. sp_check_waste_alerts           (single date)
-- Idempotency: Each sub-SP is individually idempotent (DELETE+INSERT or dedup).
-- Author:   DBA/Infrastructure Team
-- Created:  2026-02-18
-- ============================================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS test.sp_waste_daily_refresh$$

CREATE PROCEDURE test.sp_waste_daily_refresh(
    IN p_target_date DATE
)
BEGIN
    DECLARE v_run_id       VARCHAR(12);
    DECLARE v_start_ts     DATETIME;
    DECLARE v_step_start   DATETIME;
    DECLARE v_step_name    VARCHAR(64);
    DECLARE v_error_msg    TEXT DEFAULT NULL;
    DECLARE v_steps_ok     INT DEFAULT 0;
    DECLARE v_steps_failed INT DEFAULT 0;

    SET v_run_id   = LEFT(UUID(), 12);
    SET v_start_ts = NOW();

    -- Log pipeline start
    INSERT INTO test.waste_pipeline_run_log (
        run_id, pipeline_name, step_name, run_start,
        data_date_start, data_date_end, status, triggered_by
    ) VALUES (
        v_run_id, 'UC-SC-02-waste-prediction', 'sp_waste_daily_refresh',
        v_start_ts, p_target_date, p_target_date, 'RUNNING', 'mysql_event'
    );

    -- ── Step 1: Build consumption features ──────────────────────────────────
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_error_msg = MESSAGE_TEXT;
            SET v_steps_failed = v_steps_failed + 1;
            INSERT INTO test.waste_pipeline_run_log (
                run_id, pipeline_name, step_name, run_start, run_end,
                data_date_start, data_date_end, status, error_message, triggered_by
            ) VALUES (
                v_run_id, 'UC-SC-02-waste-prediction', 'sp_build_consumption_features',
                v_step_start, NOW(), p_target_date, p_target_date,
                'FAILED', LEFT(v_error_msg, 500), 'sp_waste_daily_refresh'
            );
        END;

        SET v_step_start = NOW();
        CALL test.sp_build_consumption_features(p_target_date, p_target_date);
        SET v_steps_ok = v_steps_ok + 1;

        INSERT INTO test.waste_pipeline_run_log (
            run_id, pipeline_name, step_name, run_start, run_end,
            duration_seconds, data_date_start, data_date_end, status, triggered_by
        ) VALUES (
            v_run_id, 'UC-SC-02-waste-prediction', 'sp_build_consumption_features',
            v_step_start, NOW(), TIMESTAMPDIFF(SECOND, v_step_start, NOW()),
            p_target_date, p_target_date, 'SUCCESS', 'sp_waste_daily_refresh'
        );
    END;

    -- ── Step 2: Compute waste landscape ─────────────────────────────────────
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_error_msg = MESSAGE_TEXT;
            SET v_steps_failed = v_steps_failed + 1;
            INSERT INTO test.waste_pipeline_run_log (
                run_id, pipeline_name, step_name, run_start, run_end,
                data_date_start, data_date_end, status, error_message, triggered_by
            ) VALUES (
                v_run_id, 'UC-SC-02-waste-prediction', 'sp_compute_waste_landscape',
                v_step_start, NOW(), p_target_date, p_target_date,
                'FAILED', LEFT(v_error_msg, 500), 'sp_waste_daily_refresh'
            );
        END;

        SET v_step_start = NOW();
        CALL test.sp_compute_waste_landscape(p_target_date, p_target_date);
        SET v_steps_ok = v_steps_ok + 1;

        INSERT INTO test.waste_pipeline_run_log (
            run_id, pipeline_name, step_name, run_start, run_end,
            duration_seconds, data_date_start, data_date_end, status, triggered_by
        ) VALUES (
            v_run_id, 'UC-SC-02-waste-prediction', 'sp_compute_waste_landscape',
            v_step_start, NOW(), TIMESTAMPDIFF(SECOND, v_step_start, NOW()),
            p_target_date, p_target_date, 'SUCCESS', 'sp_waste_daily_refresh'
        );
    END;

    -- ── Step 3: Compute consumption forecast ────────────────────────────────
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_error_msg = MESSAGE_TEXT;
            SET v_steps_failed = v_steps_failed + 1;
            INSERT INTO test.waste_pipeline_run_log (
                run_id, pipeline_name, step_name, run_start, run_end,
                data_date_start, data_date_end, status, error_message, triggered_by
            ) VALUES (
                v_run_id, 'UC-SC-02-waste-prediction', 'sp_compute_consumption_forecast',
                v_step_start, NOW(), p_target_date, p_target_date,
                'FAILED', LEFT(v_error_msg, 500), 'sp_waste_daily_refresh'
            );
        END;

        SET v_step_start = NOW();
        CALL test.sp_compute_consumption_forecast(p_target_date, p_target_date);
        SET v_steps_ok = v_steps_ok + 1;

        INSERT INTO test.waste_pipeline_run_log (
            run_id, pipeline_name, step_name, run_start, run_end,
            duration_seconds, data_date_start, data_date_end, status, triggered_by
        ) VALUES (
            v_run_id, 'UC-SC-02-waste-prediction', 'sp_compute_consumption_forecast',
            v_step_start, NOW(), TIMESTAMPDIFF(SECOND, v_step_start, NOW()),
            p_target_date, p_target_date, 'SUCCESS', 'sp_waste_daily_refresh'
        );
    END;

    -- ── Step 4: Compute batch risk scores ───────────────────────────────────
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_error_msg = MESSAGE_TEXT;
            SET v_steps_failed = v_steps_failed + 1;
            INSERT INTO test.waste_pipeline_run_log (
                run_id, pipeline_name, step_name, run_start, run_end,
                data_date_start, data_date_end, status, error_message, triggered_by
            ) VALUES (
                v_run_id, 'UC-SC-02-waste-prediction', 'sp_compute_batch_risk_scores',
                v_step_start, NOW(), p_target_date, p_target_date,
                'FAILED', LEFT(v_error_msg, 500), 'sp_waste_daily_refresh'
            );
        END;

        SET v_step_start = NOW();
        CALL test.sp_compute_batch_risk_scores(p_target_date);
        SET v_steps_ok = v_steps_ok + 1;

        INSERT INTO test.waste_pipeline_run_log (
            run_id, pipeline_name, step_name, run_start, run_end,
            duration_seconds, data_date_start, data_date_end, status, triggered_by
        ) VALUES (
            v_run_id, 'UC-SC-02-waste-prediction', 'sp_compute_batch_risk_scores',
            v_step_start, NOW(), TIMESTAMPDIFF(SECOND, v_step_start, NOW()),
            p_target_date, p_target_date, 'SUCCESS', 'sp_waste_daily_refresh'
        );
    END;

    -- ── Step 5: Compute transfer recommendations ────────────────────────────
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_error_msg = MESSAGE_TEXT;
            SET v_steps_failed = v_steps_failed + 1;
            INSERT INTO test.waste_pipeline_run_log (
                run_id, pipeline_name, step_name, run_start, run_end,
                data_date_start, data_date_end, status, error_message, triggered_by
            ) VALUES (
                v_run_id, 'UC-SC-02-waste-prediction', 'sp_compute_transfer_recommendations',
                v_step_start, NOW(), p_target_date, p_target_date,
                'FAILED', LEFT(v_error_msg, 500), 'sp_waste_daily_refresh'
            );
        END;

        SET v_step_start = NOW();
        CALL test.sp_compute_transfer_recommendations(p_target_date);
        SET v_steps_ok = v_steps_ok + 1;

        INSERT INTO test.waste_pipeline_run_log (
            run_id, pipeline_name, step_name, run_start, run_end,
            duration_seconds, data_date_start, data_date_end, status, triggered_by
        ) VALUES (
            v_run_id, 'UC-SC-02-waste-prediction', 'sp_compute_transfer_recommendations',
            v_step_start, NOW(), TIMESTAMPDIFF(SECOND, v_step_start, NOW()),
            p_target_date, p_target_date, 'SUCCESS', 'sp_waste_daily_refresh'
        );
    END;

    -- ── Step 6: Compute waste summary ───────────────────────────────────────
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_error_msg = MESSAGE_TEXT;
            SET v_steps_failed = v_steps_failed + 1;
            INSERT INTO test.waste_pipeline_run_log (
                run_id, pipeline_name, step_name, run_start, run_end,
                data_date_start, data_date_end, status, error_message, triggered_by
            ) VALUES (
                v_run_id, 'UC-SC-02-waste-prediction', 'sp_compute_waste_summary',
                v_step_start, NOW(), p_target_date, p_target_date,
                'FAILED', LEFT(v_error_msg, 500), 'sp_waste_daily_refresh'
            );
        END;

        SET v_step_start = NOW();
        CALL test.sp_compute_waste_summary(p_target_date);
        SET v_steps_ok = v_steps_ok + 1;

        INSERT INTO test.waste_pipeline_run_log (
            run_id, pipeline_name, step_name, run_start, run_end,
            duration_seconds, data_date_start, data_date_end, status, triggered_by
        ) VALUES (
            v_run_id, 'UC-SC-02-waste-prediction', 'sp_compute_waste_summary',
            v_step_start, NOW(), TIMESTAMPDIFF(SECOND, v_step_start, NOW()),
            p_target_date, p_target_date, 'SUCCESS', 'sp_waste_daily_refresh'
        );
    END;

    -- ── Step 7: Check waste alerts ──────────────────────────────────────────
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_error_msg = MESSAGE_TEXT;
            SET v_steps_failed = v_steps_failed + 1;
            INSERT INTO test.waste_pipeline_run_log (
                run_id, pipeline_name, step_name, run_start, run_end,
                data_date_start, data_date_end, status, error_message, triggered_by
            ) VALUES (
                v_run_id, 'UC-SC-02-waste-prediction', 'sp_check_waste_alerts',
                v_step_start, NOW(), p_target_date, p_target_date,
                'FAILED', LEFT(v_error_msg, 500), 'sp_waste_daily_refresh'
            );
        END;

        SET v_step_start = NOW();
        CALL test.sp_check_waste_alerts(p_target_date);
        SET v_steps_ok = v_steps_ok + 1;

        INSERT INTO test.waste_pipeline_run_log (
            run_id, pipeline_name, step_name, run_start, run_end,
            duration_seconds, data_date_start, data_date_end, status, triggered_by
        ) VALUES (
            v_run_id, 'UC-SC-02-waste-prediction', 'sp_check_waste_alerts',
            v_step_start, NOW(), TIMESTAMPDIFF(SECOND, v_step_start, NOW()),
            p_target_date, p_target_date, 'SUCCESS', 'sp_waste_daily_refresh'
        );
    END;

    -- ── Update master run log entry ─────────────────────────────────────────
    UPDATE test.waste_pipeline_run_log
    SET run_end          = NOW(),
        duration_seconds = TIMESTAMPDIFF(SECOND, v_start_ts, NOW()),
        status           = CASE
                               WHEN v_steps_failed = 0 THEN 'SUCCESS'
                               WHEN v_steps_ok > 0     THEN 'PARTIAL'
                               ELSE 'FAILED'
                           END,
        error_message    = CASE
                               WHEN v_steps_failed > 0
                               THEN CONCAT(v_steps_failed, ' of 7 steps failed')
                               ELSE NULL
                           END
    WHERE run_id       = v_run_id
      AND step_name    = 'sp_waste_daily_refresh';

    -- ── Return summary ──────────────────────────────────────────────────────
    SELECT 'sp_waste_daily_refresh' AS procedure_name,
           v_run_id                AS run_id,
           p_target_date           AS target_date,
           v_steps_ok              AS steps_succeeded,
           v_steps_failed          AS steps_failed,
           CASE WHEN v_steps_failed = 0 THEN 'SUCCESS'
                WHEN v_steps_ok > 0     THEN 'PARTIAL'
                ELSE 'FAILED'
           END                     AS overall_status,
           TIMESTAMPDIFF(SECOND, v_start_ts, NOW()) AS total_seconds,
           NOW()                   AS completed_at;
END$$

DELIMITER ;


-- ============================================================================
-- MySQL EVENT: Daily auto-refresh at 06:00 UTC (01:00 EST)
-- ============================================================================
-- Prerequisites:
--   SET GLOBAL event_scheduler = ON;
--   GRANT EVENT ON test.* TO 'your_user'@'%';
-- ============================================================================

DELIMITER $$

DROP EVENT IF EXISTS test.evt_waste_daily_refresh$$

CREATE EVENT test.evt_waste_daily_refresh
    ON SCHEDULE EVERY 1 DAY
    STARTS CONCAT(CURDATE() + INTERVAL 1 DAY, ' 06:00:00')
    ON COMPLETION PRESERVE
    ENABLE
    COMMENT 'UC-SC-02: Daily waste prediction refresh — runs all 7 SPs for yesterday'
DO
BEGIN
    -- Process yesterday's data (allows source systems to finalize)
    CALL test.sp_waste_daily_refresh(DATE_SUB(CURDATE(), INTERVAL 1 DAY));
END$$

DELIMITER ;
