-- ============================================================
-- Marketing Channel Attribution — Validated SQL Queries
-- Generated: 2026-03-19
-- Author: DBA Team (David Zeng)
-- For: Weekly re-runs of channel attribution report (Mai Shi)
-- ============================================================
-- IMPORTANT: All queries are read-only. Never use INSERT/UPDATE/DELETE.
-- Server: aws-luckyus-salescrm-rw (via mcp-db-gateway)
-- ============================================================


-- ============================================================
-- QUERY 1: WEEKLY CHANNEL PIVOT (PRIMARY — for regular reporting)
-- Source: salescrm.t_user
-- Updates weekly: change the WHERE date range each reporting cycle
-- Week boundaries: Sunday–Saturday (Feb 1, 2026 = Sunday)
-- Timezone: UTC (server timezone). For EST, contact DBA to adjust.
-- ============================================================

SELECT
    CASE
        WHEN create_time < '2026-02-08' THEN 'W1 Feb 1-7'
        WHEN create_time < '2026-02-15' THEN 'W2 Feb 8-14'
        WHEN create_time < '2026-02-22' THEN 'W3 Feb 15-21'
        WHEN create_time < '2026-03-01' THEN 'W4 Feb 22-28'
        WHEN create_time < '2026-03-08' THEN 'W1 Mar 1-7'
        WHEN create_time < '2026-03-15' THEN 'W2 Mar 8-14'
        WHEN create_time < '2026-03-22' THEN 'W3 Mar 15-21'  -- extend as weeks pass
        -- Add new weeks here:
        -- WHEN create_time < '2026-03-29' THEN 'W4 Mar 22-28'
        ELSE 'Uncategorized'
    END AS week_label,
    CASE
        WHEN origin = 6 THEN 'iOS应用商店'
        WHEN origin = 5 THEN '安卓应用商店'
        WHEN origin = 4 THEN 'H5/Web及其他'
        ELSE CONCAT('Unknown(', origin, ')')
    END AS channel_label,
    COUNT(*) AS new_registrations
FROM luckyus_sales_crm.t_user
WHERE tenant = 'LKUS'
  AND create_time >= '2026-02-01'          -- ← adjust start date as needed
  AND create_time < '2026-03-22'           -- ← adjust end date (exclusive) each week
GROUP BY week_label, channel_label
ORDER BY week_label, channel_label;


-- ============================================================
-- QUERY 2: DAILY CHANNEL BREAKDOWN (for spot-checking)
-- Use this to verify specific days or investigate anomalies
-- ============================================================

SELECT
    DATE(create_time)                      AS registration_date,
    CASE
        WHEN origin = 6 THEN 'iOS应用商店'
        WHEN origin = 5 THEN '安卓应用商店'
        WHEN origin = 4 THEN 'H5/Web及其他'
        ELSE CONCAT('Unknown(', origin, ')')
    END AS channel_label,
    COUNT(*)                               AS new_registrations
FROM luckyus_sales_crm.t_user
WHERE tenant = 'LKUS'
  AND create_time >= '2026-02-01'
  AND create_time < '2026-03-20'
GROUP BY registration_date, channel_label
ORDER BY registration_date, channel_label;


-- ============================================================
-- QUERY 3: CHANNEL DISTRIBUTION SUMMARY (full period)
-- Use for percentage breakdown
-- ============================================================

SELECT
    CASE
        WHEN origin = 6 THEN 'iOS应用商店'
        WHEN origin = 5 THEN '安卓应用商店'
        WHEN origin = 4 THEN 'H5/Web及其他'
        ELSE CONCAT('Unknown(', origin, ')')
    END AS channel_label,
    origin                                 AS origin_code,
    COUNT(*)                               AS total_users,
    ROUND(COUNT(*) * 100.0 /
        SUM(COUNT(*)) OVER(), 1)           AS pct_share
FROM luckyus_sales_crm.t_user
WHERE tenant = 'LKUS'
  AND create_time >= '2026-02-01'
  AND create_time < '2026-03-20'
GROUP BY channel_label, origin_code
ORDER BY total_users DESC;


-- ============================================================
-- QUERY 4: WEEKLY TOTALS CONTROL CHECK
-- Use to verify that channel rows sum to the total
-- ============================================================

SELECT
    CASE
        WHEN create_time < '2026-02-08' THEN 'W1 Feb 1-7'
        WHEN create_time < '2026-02-15' THEN 'W2 Feb 8-14'
        WHEN create_time < '2026-02-22' THEN 'W3 Feb 15-21'
        WHEN create_time < '2026-03-01' THEN 'W4 Feb 22-28'
        WHEN create_time < '2026-03-08' THEN 'W1 Mar 1-7'
        WHEN create_time < '2026-03-15' THEN 'W2 Mar 8-14'
        ELSE                                  'W3 Mar 15-19'
    END AS week_label,
    SUM(CASE WHEN origin = 6 THEN 1 ELSE 0 END) AS ios_app_store,
    SUM(CASE WHEN origin = 5 THEN 1 ELSE 0 END) AS android_play,
    SUM(CASE WHEN origin = 4 THEN 1 ELSE 0 END) AS h5_web_other,
    COUNT(*)                                       AS total
FROM luckyus_sales_crm.t_user
WHERE tenant = 'LKUS'
  AND create_time >= '2026-02-01'
  AND create_time < '2026-03-20'
GROUP BY week_label
ORDER BY week_label;


-- ============================================================
-- QUERY 5: CDP FIRST-DAY LOGIN CHANNEL BREAKDOWN (Mar 19+ only)
-- Source: isalescdp.t_user_event_track
-- Note: CDP went live 2026-03-19. Only use for Mar 19 onwards.
-- Server: aws-luckyus-isalescdp-rw
-- ============================================================

SELECT
    DATE(event_time)                       AS local_dt,
    channel,
    p_os,
    CASE
        WHEN channel = 'App Store'         THEN 'iOS应用商店'
        WHEN channel IN ('google play', 'GGLMAP') THEN '安卓/GooglePlay'
        WHEN channel = 'referral'          THEN '好友拉新(H5)'
        WHEN channel = 'nochannel'         THEN '无追踪/直接(H5)'
        ELSE CONCAT('其他:', channel)
    END AS channel_label,
    COUNT(DISTINCT user_no)                AS distinct_new_users
FROM luckyus_isales_cdp.t_user_event_track
WHERE tenant = 'LKUS'
  AND p_is_first_day = 'true'              -- string 'true', not boolean
  AND DATE(event_time) >= '2026-03-19'     -- CDP go-live date; do not query before this
  AND event_type IN (
      '$page.user$model.0$content.0$action.login',   -- iOS/Android native app login
      '$page.h5user$model.0$content.0$action.login'  -- H5/web login
  )
GROUP BY local_dt, channel, p_os, channel_label
ORDER BY local_dt, channel, p_os;


-- ============================================================
-- QUERY 6: ORIGIN CODE VALIDATION (run if origin codes change)
-- Cross-validate origin codes against CDP channel data
-- Requires: run QUERY 6a on isalescdp server, collect user_nos,
--           then run QUERY 6b on salescrm server with those user_nos
-- ============================================================

-- QUERY 6a: Get user_nos with known CDP channels (run on isalescdp server)
-- SELECT user_no, channel, p_os
-- FROM luckyus_isales_cdp.t_user_event_track
-- WHERE tenant = 'LKUS'
--   AND p_is_first_day = 'true'
--   AND DATE(event_time) = '2026-03-19'   -- ← use latest date with CDP data
--   AND event_type IN (
--       '$page.user$model.0$content.0$action.login',
--       '$page.h5user$model.0$content.0$action.login'
--   )
-- GROUP BY user_no, channel, p_os LIMIT 50;

-- QUERY 6b: Look up origin codes for those user_nos (run on salescrm server)
-- SELECT user_no, origin
-- FROM luckyus_sales_crm.t_user
-- WHERE tenant = 'LKUS'
--   AND user_no IN ( /* paste user_nos from QUERY 6a here */ );

-- Expected decode (validated 2026-03-19):
--   origin 6 = iOS / App Store
--   origin 5 = Android / Google Play
--   origin 4 = H5/Web (referral, nochannel, Google Maps H5, offline QR scan)


-- ============================================================
-- QUERY 7: REFERRAL REGISTRATION COUNT (using invitation records)
-- Approximates referral-originated registrations within origin=4
-- Run on salescrm server
-- ============================================================

SELECT
    CASE
        WHEN u.create_time < '2026-02-08' THEN 'W1 Feb 1-7'
        WHEN u.create_time < '2026-02-15' THEN 'W2 Feb 8-14'
        WHEN u.create_time < '2026-02-22' THEN 'W3 Feb 15-21'
        WHEN u.create_time < '2026-03-01' THEN 'W4 Feb 22-28'
        WHEN u.create_time < '2026-03-08' THEN 'W1 Mar 1-7'
        WHEN u.create_time < '2026-03-15' THEN 'W2 Mar 8-14'
        ELSE                                    'W3 Mar 15-19'
    END AS week_label,
    COUNT(DISTINCT ua.user_no) AS referral_users
FROM luckyus_sales_crm.t_user u
JOIN luckyus_sales_crm.t_user_attribute ua ON u.user_no = ua.user_no AND u.tenant = ua.tenant
WHERE u.tenant = 'LKUS'
  AND u.create_time >= '2026-02-01' AND u.create_time < '2026-03-20'
  AND ua.inviter_code IS NOT NULL AND ua.inviter_code != ''
GROUP BY week_label
ORDER BY week_label;

-- NOTE: This query approximates referral registrations by checking if the user
-- has an inviter_code in t_user_attribute. If inviter_code is populated,
-- the user was referred by an existing member.
-- This is a SUBSET of origin=4 (H5) users.
-- Run and compare referral_users vs total origin=4 users to estimate referral share.


-- ============================================================
-- QUERY 8: WEEKLY PIVOT TEMPLATE FOR FUTURE PERIODS
-- Update date boundaries each week to extend the report
-- ============================================================

-- Template: add new weeks by extending the CASE WHEN block
-- Example for week of Mar 22-28:
-- WHEN create_time >= '2026-03-22' AND create_time < '2026-03-29' THEN 'W4 Mar 22-28'

-- Example for running the full pivot for any custom date range:
SELECT
    CONCAT(
        YEAR(create_time), '-W',
        LPAD(WEEK(create_time, 0), 2, '0')  -- mode 0 = Sunday start
    ) AS us_week,
    MIN(DATE(create_time))                   AS week_start_date,
    SUM(CASE WHEN origin = 6 THEN 1 ELSE 0 END) AS ios_app_store,
    SUM(CASE WHEN origin = 5 THEN 1 ELSE 0 END) AS android_play,
    SUM(CASE WHEN origin = 4 THEN 1 ELSE 0 END) AS h5_web_other,
    COUNT(*)                                     AS total_registrations
FROM luckyus_sales_crm.t_user
WHERE tenant = 'LKUS'
  AND create_time >= '2026-01-01'          -- ← adjust as needed
  AND create_time < '2026-04-01'           -- ← adjust end date
GROUP BY us_week
ORDER BY us_week;
