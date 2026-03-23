-- ============================================================
-- Channel Attribution: Online vs Offline Breakdown
-- Validated SQL Queries
-- Generated: 2026-03-23
-- Author: DBA Team (David Zeng)
-- For: Online/offline channel attribution report (Mai Shi)
-- ============================================================
-- IMPORTANT: All queries are read-only. Never use INSERT/UPDATE/DELETE.
-- Server: aws-luckyus-salescrm-rw (via mcp-db-gateway)
-- ============================================================


-- ============================================================
-- QUERY 1: WEEKLY REGISTRATION PIVOT (Feb 1 – Mar 22)
-- Source: salescrm.t_user
-- Week boundaries: Sunday–Saturday, UTC timezone
-- ============================================================

SELECT
    CASE
        WHEN create_time < '2026-02-08' THEN 'W1 Feb 1-7'
        WHEN create_time < '2026-02-15' THEN 'W2 Feb 8-14'
        WHEN create_time < '2026-02-22' THEN 'W3 Feb 15-21'
        WHEN create_time < '2026-03-01' THEN 'W4 Feb 22-28'
        WHEN create_time < '2026-03-08' THEN 'W1 Mar 1-7'
        WHEN create_time < '2026-03-15' THEN 'W2 Mar 8-14'
        WHEN create_time < '2026-03-22' THEN 'W3 Mar 15-21'
        WHEN create_time < '2026-03-29' THEN 'W4 Mar 22-28'
        ELSE 'Uncategorized'
    END AS week_label,
    SUM(CASE WHEN origin = 6 THEN 1 ELSE 0 END) AS ios_app_store,
    SUM(CASE WHEN origin = 5 THEN 1 ELSE 0 END) AS android_play,
    SUM(CASE WHEN origin = 4 THEN 1 ELSE 0 END) AS h5_web_other,
    COUNT(*) AS total
FROM luckyus_sales_crm.t_user
WHERE tenant = 'LKUS'
  AND create_time >= '2026-02-01'
  AND create_time < '2026-03-23'
GROUP BY week_label
ORDER BY week_label;


-- ============================================================
-- QUERY 2: REFERRAL SUBTRACTION (origin=4 with inviter)
-- Identifies referral users within H5 by JOIN to t_invitation_record
-- ============================================================

SELECT
    CASE
        WHEN u.create_time < '2026-02-08' THEN 'W1 Feb 1-7'
        WHEN u.create_time < '2026-02-15' THEN 'W2 Feb 8-14'
        WHEN u.create_time < '2026-02-22' THEN 'W3 Feb 15-21'
        WHEN u.create_time < '2026-03-01' THEN 'W4 Feb 22-28'
        WHEN u.create_time < '2026-03-08' THEN 'W1 Mar 1-7'
        WHEN u.create_time < '2026-03-15' THEN 'W2 Mar 8-14'
        WHEN u.create_time < '2026-03-22' THEN 'W3 Mar 15-21'
        WHEN u.create_time < '2026-03-29' THEN 'W4 Mar 22-28'
        ELSE 'Uncategorized'
    END AS week_label,
    COUNT(DISTINCT ir.invitee_user_no) AS referral_users
FROM luckyus_sales_crm.t_user u
JOIN luckyus_sales_crm.t_invitation_record ir
    ON u.user_no = ir.invitee_user_no AND u.tenant = ir.tenant
WHERE u.tenant = 'LKUS'
  AND u.origin = 4
  AND u.create_time >= '2026-02-01'
  AND u.create_time < '2026-03-23'
GROUP BY week_label
ORDER BY week_label;


-- ============================================================
-- QUERY 3: TIMING PROXY — Registration-to-first-order by segment
-- The KEY query for online/offline estimation
-- Uses t_user_profile.first_pay_time (same DB, no cross-server join)
-- ============================================================

SELECT
    CASE
        WHEN u.origin = 4 AND ir.invitee_user_no IS NOT NULL THEN 'H5 referral'
        WHEN u.origin = 4 THEN 'H5 non-referral'
        WHEN u.origin = 6 THEN 'iOS'
        WHEN u.origin = 5 THEN 'Android'
        ELSE 'Other'
    END AS segment,
    CASE
        WHEN p.first_pay_time IS NULL THEN 'No order'
        WHEN TIMESTAMPDIFF(MINUTE, u.create_time, p.first_pay_time) <= 15 THEN '0-15 min'
        WHEN TIMESTAMPDIFF(MINUTE, u.create_time, p.first_pay_time) <= 30 THEN '16-30 min'
        WHEN TIMESTAMPDIFF(MINUTE, u.create_time, p.first_pay_time) <= 60 THEN '31-60 min'
        WHEN TIMESTAMPDIFF(MINUTE, u.create_time, p.first_pay_time) <= 120 THEN '1-2 hr'
        WHEN TIMESTAMPDIFF(HOUR, u.create_time, p.first_pay_time) <= 24 THEN '2-24 hr'
        ELSE '24+ hr'
    END AS time_bucket,
    COUNT(*) AS user_count
FROM luckyus_sales_crm.t_user u
LEFT JOIN luckyus_sales_crm.t_user_profile p
    ON u.user_no = p.user_no AND u.tenant = p.tenant
LEFT JOIN luckyus_sales_crm.t_invitation_record ir
    ON u.user_no = ir.invitee_user_no AND u.tenant = ir.tenant
WHERE u.tenant = 'LKUS'
  AND u.create_time >= '2026-02-01'
  AND u.create_time < '2026-03-23'
GROUP BY segment, time_bucket
ORDER BY segment, time_bucket;


-- ============================================================
-- QUERY 4: WEEKLY TIMING BREAKDOWN (H5 non-referral only)
-- Validates consistency of 0-15 min rate across weeks
-- ============================================================

SELECT
    CASE
        WHEN u.create_time < '2026-02-08' THEN 'W1 Feb 1-7'
        WHEN u.create_time < '2026-02-15' THEN 'W2 Feb 8-14'
        WHEN u.create_time < '2026-02-22' THEN 'W3 Feb 15-21'
        WHEN u.create_time < '2026-03-01' THEN 'W4 Feb 22-28'
        WHEN u.create_time < '2026-03-08' THEN 'W1 Mar 1-7'
        WHEN u.create_time < '2026-03-15' THEN 'W2 Mar 8-14'
        WHEN u.create_time < '2026-03-22' THEN 'W3 Mar 15-21'
        WHEN u.create_time < '2026-03-29' THEN 'W4 Mar 22-28'
        ELSE 'Uncategorized'
    END AS week_label,
    SUM(CASE
        WHEN p.first_pay_time IS NOT NULL
         AND TIMESTAMPDIFF(MINUTE, u.create_time, p.first_pay_time) <= 15
        THEN 1 ELSE 0
    END) AS within_15min,
    COUNT(*) AS total,
    ROUND(
        SUM(CASE
            WHEN p.first_pay_time IS NOT NULL
             AND TIMESTAMPDIFF(MINUTE, u.create_time, p.first_pay_time) <= 15
            THEN 1 ELSE 0
        END) * 100.0 / COUNT(*), 1
    ) AS pct_15min
FROM luckyus_sales_crm.t_user u
LEFT JOIN luckyus_sales_crm.t_user_profile p
    ON u.user_no = p.user_no AND u.tenant = p.tenant
LEFT JOIN luckyus_sales_crm.t_invitation_record ir
    ON u.user_no = ir.invitee_user_no AND u.tenant = ir.tenant
WHERE u.tenant = 'LKUS'
  AND u.origin = 4
  AND ir.invitee_user_no IS NULL     -- non-referral only
  AND u.create_time >= '2026-02-01'
  AND u.create_time < '2026-03-23'
GROUP BY week_label
ORDER BY week_label;


-- ============================================================
-- QUERY 5: CDP CHANNEL BREAKDOWN (Mar 19+ only)
-- Source: isalescdp.t_user_event_track
-- Server: aws-luckyus-isalescdp-rw
-- ============================================================

SELECT
    DATE(event_time)                       AS local_dt,
    channel,
    p_os,
    CASE
        WHEN channel = 'App Store'         THEN 'iOS App Store'
        WHEN channel IN ('google play', 'GGLMAP') THEN 'Android/GooglePlay'
        WHEN channel LIKE 'GGLMAP%'        THEN 'Google Maps H5'
        WHEN channel = 'referral'          THEN 'Referral (H5)'
        WHEN channel = 'nochannel'         THEN 'No tracking / Direct (H5)'
        ELSE CONCAT('Other: ', channel)
    END AS channel_label,
    COUNT(DISTINCT user_no)                AS distinct_new_users
FROM luckyus_isales_cdp.t_user_event_track
WHERE tenant = 'LKUS'
  AND p_is_first_day = 'true'
  AND DATE(event_time) >= '2026-03-19'
  AND event_type IN (
      '$page.user$model.0$content.0$action.login',
      '$page.h5user$model.0$content.0$action.login'
  )
GROUP BY local_dt, channel, p_os, channel_label
ORDER BY local_dt, channel, p_os;


-- ============================================================
-- QUERY 6: ORIGIN VALUE VALIDATION
-- Confirms which origin codes exist in the date range
-- ============================================================

SELECT
    origin,
    COUNT(*) AS user_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM luckyus_sales_crm.t_user
WHERE tenant = 'LKUS'
  AND create_time >= '2026-02-01'
  AND create_time < '2026-03-23'
GROUP BY origin
ORDER BY user_count DESC;


-- ============================================================
-- QUERY 7: t_user_profile SCHEMA DISCOVERY
-- Confirms available columns for timing proxy
-- Server: aws-luckyus-salescrm-rw
-- ============================================================

SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'luckyus_sales_crm'
  AND TABLE_NAME = 't_user_profile'
ORDER BY ORDINAL_POSITION
LIMIT 50;


-- ============================================================
-- QUERY 8: CHANNEL DISTRIBUTION SUMMARY (full period)
-- For percentage breakdown reporting
-- ============================================================

SELECT
    CASE
        WHEN origin = 6 THEN 'iOS App Store'
        WHEN origin = 5 THEN 'Android Google Play'
        WHEN origin = 4 THEN 'H5/Web (all sub-channels)'
        ELSE CONCAT('Unknown(', origin, ')')
    END AS channel_label,
    origin AS origin_code,
    COUNT(*) AS total_users,
    ROUND(COUNT(*) * 100.0 /
        SUM(COUNT(*)) OVER(), 1) AS pct_share
FROM luckyus_sales_crm.t_user
WHERE tenant = 'LKUS'
  AND create_time >= '2026-02-01'
  AND create_time < '2026-03-23'
GROUP BY channel_label, origin_code
ORDER BY total_users DESC;


-- ============================================================
-- QUERY 9: STORE-LEVEL QR SCAN DISTRIBUTION (optional)
-- Shows which stores generate the most QR scan registrations
-- Uses first-order store as proxy for scan location
-- ============================================================

SELECT
    p.first_order_shop_id AS shop_id,
    COUNT(*) AS qr_est_users
FROM luckyus_sales_crm.t_user u
JOIN luckyus_sales_crm.t_user_profile p
    ON u.user_no = p.user_no AND u.tenant = p.tenant
LEFT JOIN luckyus_sales_crm.t_invitation_record ir
    ON u.user_no = ir.invitee_user_no AND u.tenant = ir.tenant
WHERE u.tenant = 'LKUS'
  AND u.origin = 4
  AND u.create_time >= '2026-02-01'
  AND u.create_time < '2026-03-23'
  AND ir.invitee_user_no IS NULL          -- exclude referral
  AND p.first_pay_time IS NOT NULL
  AND TIMESTAMPDIFF(MINUTE, u.create_time, p.first_pay_time) <= 15
GROUP BY p.first_order_shop_id
ORDER BY qr_est_users DESC
LIMIT 20;


-- ============================================================
-- QUERY 10: WEEKLY PIVOT TEMPLATE (auto week labels via WEEK())
-- Use for extending the report to future periods
-- ============================================================

SELECT
    CONCAT(
        YEAR(create_time), '-W',
        LPAD(WEEK(create_time, 0), 2, '0')
    ) AS us_week,
    MIN(DATE(create_time)) AS week_start_date,
    SUM(CASE WHEN origin = 6 THEN 1 ELSE 0 END) AS ios_app_store,
    SUM(CASE WHEN origin = 5 THEN 1 ELSE 0 END) AS android_play,
    SUM(CASE WHEN origin = 4 THEN 1 ELSE 0 END) AS h5_web_other,
    COUNT(*) AS total_registrations
FROM luckyus_sales_crm.t_user
WHERE tenant = 'LKUS'
  AND create_time >= '2026-02-01'
  AND create_time < '2026-03-29'
GROUP BY us_week
ORDER BY us_week;
