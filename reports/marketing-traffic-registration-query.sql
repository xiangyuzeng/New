-- ============================================================
-- Marketing Traffic & Registration Data Extraction
-- Generated: 2026-03-19
-- Author: DBA Team (David Zeng)
-- ============================================================
-- This file contains two SQL sections:
--   Section 1: Working query (available now) against t_user_event_track
--   Section 2: Full template query (for analyst) with all 7 events + adid
-- ============================================================


-- ============================================================
-- SECTION 1: WORKING QUERY (Available Now)
-- Source: aws-luckyus-isalescdp-rw
-- Table:  luckyus_isales_cdp.t_user_event_track
-- Events: 2 login events (app + h5); ~260K rows from 2026-03-05 onward
-- Notes:
--   - p_device_id is used as adid PROXY (sparse — most rows = 0 distinct)
--   - user_no maps to login_id concept
--   - p_is_first_day is a string: 'true' / 'false'
--   - platform: 1=iOS App, 2=Android App, 3=H5/WeChat
--   - Replace the date filter for other days; earliest reliable date is 2026-03-05
-- Validated: Returns 16 rows for 2026-03-18 (App Store iOS, google play, GGLMAP, etc.)
-- ============================================================

SELECT
    DATE(event_time)              AS local_dt,
    channel,
    p_os,
    p_is_first_day,
    platform,
    event_type                    AS event,
    COUNT(1)                      AS total_count,
    COUNT(DISTINCT p_device_id)   AS distinct_adid,      -- proxy for adid; mostly 0 (field sparsely populated)
    COUNT(DISTINCT user_no)       AS distinct_login_id
FROM luckyus_isales_cdp.t_user_event_track
WHERE tenant = 'LKUS'
  AND DATE(event_time) = '2026-03-18'          -- ← change date as needed (YYYY-MM-DD)
  AND event_type IN (
      '$page.user$model.0$content.0$action.login',       -- App native login
      '$page.h5user$model.0$content.0$action.login'      -- H5/WeChat login
  )
GROUP BY
    local_dt,
    channel,
    p_os,
    p_is_first_day,
    platform,
    event_type
ORDER BY
    local_dt,
    channel,
    p_os,
    p_is_first_day,
    platform,
    event_type;


-- ============================================================
-- SECTION 1b: DATE RANGE VARIANT
-- Use this to pull multiple days at once (max ~14 days recommended for performance)
-- ============================================================

SELECT
    DATE(event_time)              AS local_dt,
    channel,
    p_os,
    p_is_first_day,
    platform,
    event_type                    AS event,
    COUNT(1)                      AS total_count,
    COUNT(DISTINCT p_device_id)   AS distinct_adid,
    COUNT(DISTINCT user_no)       AS distinct_login_id
FROM luckyus_isales_cdp.t_user_event_track
WHERE tenant = 'LKUS'
  AND DATE(event_time) BETWEEN '2026-03-10' AND '2026-03-18'   -- ← adjust range
  AND event_type IN (
      '$page.user$model.0$content.0$action.login',
      '$page.h5user$model.0$content.0$action.login'
  )
GROUP BY
    local_dt,
    channel,
    p_os,
    p_is_first_day,
    platform,
    event_type
ORDER BY
    local_dt,
    channel,
    p_os,
    p_is_first_day,
    platform,
    event_type;


-- ============================================================
-- SECTION 1c: FIRST-TIME REGISTRATIONS ONLY
-- Filter p_is_first_day = 'true' to isolate new user registration events
-- ============================================================

SELECT
    DATE(event_time)              AS local_dt,
    channel,
    p_os,
    platform,
    event_type                    AS event,
    COUNT(1)                      AS total_count,
    COUNT(DISTINCT p_device_id)   AS distinct_adid,
    COUNT(DISTINCT user_no)       AS distinct_login_id
FROM luckyus_isales_cdp.t_user_event_track
WHERE tenant = 'LKUS'
  AND DATE(event_time) = '2026-03-18'
  AND p_is_first_day = 'true'                              -- ← new users only
  AND event_type IN (
      '$page.user$model.0$content.0$action.login',
      '$page.h5user$model.0$content.0$action.login'
  )
GROUP BY
    local_dt,
    channel,
    p_os,
    platform,
    event_type
ORDER BY
    local_dt,
    channel,
    p_os,
    platform,
    event_type;


-- ============================================================
-- SECTION 2: FULL TEMPLATE QUERY (For Analyst — Needs Redshift/True Source)
-- ============================================================
-- Purpose: Template matching the analyst's expected output format exactly.
--   Includes all 7 event types, true adid field, login_id field.
--   Replace {schema}.{event_table} with the actual Redshift/Sensors Data table.
--
-- Expected event types (from analyst sample):
--   action.bw   — browse (traffic/impression)
--   action.ck   — click
--   action.login — login/registration
--   scan page events (3 variants)
--   (+ others TBD)
--
-- Expected output columns (analyst sample 2026-03-01):
--   local_dt | channel | p_os | p_is_first_day | platform | event
--   | total_count | distinct_adid | distinct_login_id
--
-- Analyst sample validation values:
--   App Store + iOS + p_is_first_day=0 + platform=1 + action.bw
--     → total_count=206, distinct_adid=80, distinct_login_id=1
--   App Store + iOS + p_is_first_day=1 + platform=1 + action.login
--     → total_count=643, distinct_adid=637, distinct_login_id=640
-- ============================================================

SELECT
    DATE(event_time)              AS local_dt,        -- or: TO_DATE(event_time) in Redshift
    channel,
    p_os,
    p_is_first_day,                                   -- numeric in source? 0/1 vs 'true'/'false'
    platform,
    event_type                    AS event,            -- or: event_name depending on schema
    COUNT(1)                      AS total_count,
    COUNT(DISTINCT adid)          AS distinct_adid,   -- TRUE adid field (IDFA/GAID)
    COUNT(DISTINCT login_id)      AS distinct_login_id -- TRUE login_id field (user identifier)
FROM {schema}.{event_table}                           -- ← REPLACE with actual table
WHERE 1=1
  -- AND tenant = 'LKUS'                              -- uncomment if multi-tenant table
  AND DATE(event_time) = '2026-03-01'                -- ← analyst's validation date
  AND event_type IN (
      -- Traffic/browse events
      '$page.user$model.login$content.0$action.bw',
      '$page.user$model.login$content.0$action.ck',
      -- Registration/login events
      '$page.user$model.login$content.0$action.login',
      -- H5 variants
      '$page.h5user$model.login$content.0$action.bw',
      '$page.h5user$model.login$content.0$action.ck',
      '$page.h5user$model.login$content.0$action.login',
      -- Scan page event(s) — confirm exact names with analyst
      '$page.scan$model.0$content.0$action.bw'
      -- Add additional events as confirmed
  )
GROUP BY
    local_dt,
    channel,
    p_os,
    p_is_first_day,
    platform,
    event_type
ORDER BY
    local_dt,
    channel,
    p_os,
    p_is_first_day,
    platform,
    event_type;


-- ============================================================
-- SECTION 3: DIAGNOSTIC QUERIES
-- Use these to understand data availability and field distributions
-- ============================================================

-- 3a: Check available event types in t_user_event_track
SELECT event_type, COUNT(*) AS cnt
FROM luckyus_isales_cdp.t_user_event_track
WHERE tenant = 'LKUS'
  AND DATE(event_time) >= '2026-03-10'
GROUP BY event_type
ORDER BY cnt DESC
LIMIT 30;

-- 3b: Check p_device_id (adid proxy) population rate
SELECT
    COUNT(*) AS total_rows,
    COUNT(NULLIF(p_device_id, ''))  AS rows_with_device_id,
    ROUND(COUNT(NULLIF(p_device_id, '')) * 100.0 / COUNT(*), 1) AS device_id_pct
FROM luckyus_isales_cdp.t_user_event_track
WHERE tenant = 'LKUS'
  AND DATE(event_time) = '2026-03-18';

-- 3c: Data availability by date (confirm earliest date with data)
SELECT DATE(event_time) AS dt, COUNT(*) AS row_count
FROM luckyus_isales_cdp.t_user_event_track
WHERE tenant = 'LKUS'
GROUP BY DATE(event_time)
ORDER BY dt DESC
LIMIT 20;

-- 3d: Channel distribution for today
SELECT channel, COUNT(*) AS cnt
FROM luckyus_isales_cdp.t_user_event_track
WHERE tenant = 'LKUS'
  AND DATE(event_time) = '2026-03-18'
GROUP BY channel
ORDER BY cnt DESC
LIMIT 20;
