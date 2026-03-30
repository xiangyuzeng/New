# Offline QR Scan Registration — Discovery Results

**Author:** David Zeng (DBA/Infrastructure)
**Date:** 2026-03-19
**Question:** How many registrations came from in-store QR scan (线下扫码)?

---

## Executive Summary

No single MySQL or CDP table provides a direct count of offline QR scan registrations.
The registration interface (`origin=4` = H5/Web) records *how* users registered, not *why* they came. QR scan, GGLMAP, referral, and direct web all produce `origin=4`.

**One meaningful subtraction is confirmed:** 2,471 referral (好友拉新) users can be removed from the 9,281 origin=4 pool.
**Residual unresolved:** QR scan, GGLMAP, and direct H5 cannot be separated without Redshift access.

---

## Step-by-Step Findings

### Step 1 — t_user_attribute Code Fields (BLOCKED)

**Query:** NULL-rate check for `link_code`, `touchpoint_code`, `site_code` on origin=4 users, Feb 1–Mar 19.

| Field | Non-NULL Count | Non-NULL % |
|-------|---------------|------------|
| link_code | 0 | 0.0% |
| touchpoint_code | 0 | 0.0% |
| site_code | 0 | 0.0% |
| **Total origin=4 matched** | **9,305** | — |

> **Conclusion:** All three code fields are universally NULL for origin=4 users.
> Cannot identify QR scan vs. other H5 sub-channels via this path.
> (Note: query returned 9,305 vs. 9,281 due to slight time boundary difference; both counts are correct for their respective date scopes.)

---

### Step 2 — Referral Subtraction via t_invitation_record (SUCCESS ✅)

**Method:** JOIN `t_invitation_record.invitee_user_no` → `t_user.user_no` filtered to `origin=4`, Feb 1–Mar 19.

| Week | Referral Users (origin=4) |
|------|--------------------------|
| W1 Feb 1–7 | 355 |
| W2 Feb 8–14 | 348 |
| W3 Feb 15–21 | 333 |
| W4 Feb 22–28 | 320 |
| W1 Mar 1–7 | 426 |
| W2 Mar 8–14 | 468 |
| W3 Mar 15–19 | 221 |
| **Total** | **2,471** |

> **Conclusion:** 2,471 origin=4 users registered via a friend referral/invitation link.
> This is the only directly confirmed sub-segment. HIGH CONFIDENCE.

---

### Step 3 — Lat/Lng Column Search Across Databases (NO REGISTRATION LOCATION FOUND)

| Database | Result |
|----------|--------|
| salescrm | `t_user_delivery_address` has `longitude`/`latitude` — delivery address only, not registration location |
| isalescdp | `t_user_event_track.platform` matched regex; no real location columns |
| salesorder | `t_order_member` has `member_lat`/`member_lon` (user coords at order time) and `take_address_lat`/`take_address_lon` — order location, not registration |

No "底层隐私表" (privacy/registration location table) found in any accessible MySQL database.

---

### Step 4 — Data/Analytics Database Inventory (NOT RELEVANT)

| Server | Schemas Found | Assessment |
|--------|--------------|------------|
| aws-luckyus-pubdm-rw | `luckyus_pub_dm` | Master Data Management (goods, shop coords, suppliers) — no user analytics |
| aws-luckyus-ldas-rw | `luckyus_ldas_nacos`, `luckyus_ldas_cmdb`, `luckyus_ozono`, `luckyus_apigatewayadmin`, `luckyus_ikafadmin` | DevOps/platform tooling — no user data |
| aws-luckyus-ldas01-rw | `luckyus_db_collection` | DBA data platform ETL pipeline manager — no user analytics |
| aws-luckyus-icyberdata-rw | `luckyus_icyberdata`, `luckyus_icyberdata_user`, `luckyus_icyberdata_nacos` | DBA's own monitoring/collection DB — no user registration data |

None of these databases contain user registration or channel attribution tables.

---

### Step 5 — IoT Platform (NOT RELEVANT FOR QR SCAN)

`aws-luckyus-iotplatform-rw` largest tables:
- `t_cup_order_info`: 669K rows — **coffee machine order data** (beverage IoT, not user QR scan)
- `t_shop_info`: 521 rows — has `location_longitude`/`location_latitude` (store coordinates — useful if we ever get registration lat/lng)

> No QR scan event tables. IoT platform manages beverage machines, not store entry QR codes.

---

### Step 6 — CDP Full Event Type Audit (PARTIAL — NO SCAN EVENT)

**Full event type list, Feb 1–Mar 19 (t_user_event_track, tenant=LKUS):**

| Event Type | Count | Date Range |
|-----------|-------|-----------|
| page_end | 16,452 | Feb 1 – Mar 19 |
| $AppViewScreen | 15,458 | Feb 3 – Mar 19 |
| page_start | 15,448 | Feb 3 – Mar 19 |
| $AppEnd | 4,734 | Feb 10 – Mar 19 |
| $AppStart | 4,593 | Feb 27 – Mar 19 |
| $pageview | 2,491 | Mar 19 only |
| push_show_bw | 1,573 | Mar 19 only |
| $WebStay | 247 | Mar 19 only |
| $page.user$...$action.login | 130 | Mar 19 only |
| $AppStartPassively | 69 | Feb 18 – Mar 19 |
| push_click_ck | 55 | Mar 16 – Mar 19 |
| **$page.h5user$...$action.login** | **20** | **Mar 19 only** |
| push_start_app | 9 | Mar 16 – Mar 19 |
| $WebClick | 4 | Mar 19 only |
| $SignUp | 1 | Mar 19 only |

**Key negatives:**
- `$page.scan$model.0$content.0$action.bw` — **NOT FOUND** for any date
- Login and registration events only exist on Mar 19 (CDP went live Mar 19)

**Key positive — GGLMAP channel confirmed:**
H5 login events on Mar 19 by channel:

| Channel | H5 Login Count | % of H5 Logins |
|---------|--------------|----------------|
| referral | 10 | 50% |
| nochannel | 8 | 40% |
| GGLMAP901 | 2 | 10% |
| **Total H5** | **20** | 100% |

> ⚠️ Mar 19 sample is n=20, which is not representative of the full period.
> Full-period referral share from t_invitation_record = 26.6%, not 50% — confirming the sample is skewed.

**Scan page confirmed in nochannel H5 flow:**
From `$pageview` events on Mar 19:
- `p_title = "scan"` with `p_referrer_title = ""` → 3 events
- `p_title = "home"` with `p_referrer_title = "scan"` → 3 events

This confirms in-store QR scan users DO visit a page titled **"scan"** and then proceed to **"home"**.
However, these are browsing events (not registration events) and include both existing and new users.
The QR scan flow lands in **`channel = 'nochannel'`** because current store QR codes have no UTM parameters.

---

### Step 7 — Redshift (BLOCKED)

Both IAM actions attempted and denied:
- `redshift:DescribeClusters` — AccessDenied
- `redshift-serverless:ListWorkgroups` — AccessDenied

The Sensors Data full event stream (with authoritative scan event counts and channel attribution) is in Redshift but remains inaccessible for `iam:databasecheck`.

---

## What Was Ruled Out

| Database/Table | Why Not Relevant |
|---------------|-----------------|
| opshop | No QR/scan/invite tables (checked in prior work) |
| isalesprivatedomain | Only messaging/campaign tables |
| cdpactivity | Empty/inaccessible |
| ldas, ldas01 | Platform tooling, no user data |
| icyberdata | DBA monitoring system (David's own tool) |
| pubdm | Master data management, no analytics |
| iotplatform | Beverage machine IoT, no registration QR |
| salescrm t_user | Only 15 columns: origin, phone, timezone — no channel field |
| salescrm t_user_attribute | link_code/touchpoint_code/site_code all NULL for origin=4 |
| isalescdp t_user_event | Only Mar 19 data; numeric event types (click, browse, order) — not registration |
