# Marketing Traffic & Registration — Field Documentation

**Date**: 2026-03-19
**Author**: DBA Team (David Zeng)
**Purpose**: Document the field mapping between the analyst's expected output and what's available in MySQL, identify gaps, and provide next steps to access the complete dataset.

---

## 1. Analyst's Expected Output Format

The marketing analyst provided a sample output (date: 2026-03-01) with the following structure:

| Column | Sample Values |
|--------|--------------|
| `local_dt` | 2026-03-01 |
| `channel` | App Store, google play, referral, GGLMAP, nochannel |
| `p_os` | iOS, Android |
| `p_is_first_day` | 0, 1 |
| `platform` | 1 (iOS App), 2 (Android App), 3 (H5/WeChat) |
| `event` | action.bw, action.ck, action.login, scan page variants |
| `total_count` | integer (e.g., 206, 643) |
| `distinct_adid` | integer — unique advertising IDs (IDFA/GAID) |
| `distinct_login_id` | integer — unique registered user IDs |

### Analyst Validation Rows (2026-03-01)

| channel | p_os | p_is_first_day | platform | event | total_count | distinct_adid | distinct_login_id |
|---------|------|---------------|----------|-------|-------------|---------------|-------------------|
| App Store | iOS | 0 | 1 | action.bw | 206 | 80 | 1 |
| App Store | iOS | 1 | 1 | action.login | 643 | 637 | 640 |

---

## 2. Discovered MySQL Source: `t_user_event_track`

**Server**: `aws-luckyus-isalescdp-rw`
**Database**: `luckyus_isales_cdp`
**Table**: `t_user_event_track`
**Rows**: ~260K (LKUS tenant)
**Earliest data**: ~2026-03-05

### Column Mapping

| Expected Field | MySQL Column | Match Status | Notes |
|----------------|-------------|--------------|-------|
| `local_dt` | `DATE(event_time)` | ✅ Derivable | `event_time` is DATETIME |
| `channel` | `channel` | ✅ Exact match | Same values: App Store, google play, GGLMAP, referral, nochannel |
| `p_os` | `p_os` | ✅ Exact match | Values: iOS, Android |
| `p_is_first_day` | `p_is_first_day` | ⚠️ Type mismatch | MySQL stores string `'true'`/`'false'`; analyst shows `0`/`1` |
| `platform` | `platform` | ✅ Exact match | Values: 1 (iOS App), 2 (Android App), 3 (H5/WeChat) |
| `event` | `event_type` | ❌ Format differs | See Section 3 |
| `adid` | `p_device_id` | ❌ Not true adid | See Section 4 |
| `login_id` | `user_no` | ⚠️ Different name | Functionally equivalent user identifier |

### Available Events in MySQL (Validated)

| event_type value | Analyst equivalent |
|------------------|-------------------|
| `$page.user$model.0$content.0$action.login` | action.login (App) |
| `$page.h5user$model.0$content.0$action.login` | action.login (H5/WeChat) |

---

## 3. Critical Gap: Missing Event Types

The analyst's sample includes 7+ event types. **Only 2 login events exist in `t_user_event_track`.**

### Expected Events (from analyst) — NOT found in MySQL

| Expected event | Description | Status |
|----------------|-------------|--------|
| `action.bw` | Browse/impression (traffic metric) | ❌ Not in MySQL |
| `action.ck` | Click event | ❌ Not in MySQL |
| `action.login` | Login/registration | ✅ Present (different name format) |
| Scan page events | Scan/QR page views | ❌ Not in MySQL |

### Event Name Format Mismatch

MySQL event names use format: `$page.{page}$model.0$content.0$action.{type}`
Analyst's events use format: `$page.{page}$model.{model}$content.0$action.{type}`

The `model` segment differs: MySQL has `0`; analyst's data has `login`, `bw`, `ck`, etc. This may indicate:
- Different SDK version or event instrumentation layer
- Different data source (Redshift vs. MySQL)
- Events may be pre-aggregated or transformed in the analyst's source

---

## 4. Critical Gap: No True `adid` Field

**adid** = Advertising ID (IDFA for iOS, GAID for Android) — used for attribution tracking.

| Field | MySQL Column | Issue |
|-------|-------------|-------|
| True adid (IDFA/GAID) | **Not found** in any explored table | No advertising ID field exists in MySQL |
| Proxy: `p_device_id` | Exists in `t_user_event_track` | Sparsely populated — most rows return `distinct_adid = 0` |

**Evidence from validation (2026-03-18)**:
- App Store + iOS + action.login → `distinct_adid = 2` out of 111 events (1.8% population)
- google play + Android + action.login → `distinct_adid = 0`

The analyst's sample shows `distinct_adid = 637` for 643 events — indicating near-complete adid coverage. This level of coverage does not exist in MySQL.

---

## 5. Critical Gap: No Pre-March-5 Data

- Analyst's validation date is **2026-03-01**
- MySQL table `t_user_event_track` has **no data before ~2026-03-05**
- The query cannot be validated against the analyst's exact reference rows

---

## 6. Likely True Data Source

Based on the gaps above, the analyst's complete dataset is almost certainly in **Redshift Serverless** (not MySQL):

| Evidence | Detail |
|----------|--------|
| "Tables already exist in Tableau" | Tableau typically connects to Redshift for analytical queries |
| adid coverage near 100% | Requires full Sensors Data SDK event stream, typically stored in Redshift |
| action.bw / action.ck events present | Raw clickstream events are loaded into Redshift via S3/Glue pipeline |
| Pre-March-5 data available | Redshift has historical data; MySQL table appears recently created |

**Recommended table location**: Redshift Serverless workspace
**Access needed**: Redshift read credentials for IAM user `databasecheck`
(Currently blocked: `databasecheck` lacks `redshift:DescribeClusters` permission)

---

## 7. Current Working Query Summary

The file `marketing-traffic-registration-query.sql` contains:

| Section | Description | Status |
|---------|-------------|--------|
| **Section 1** | Single-day login query vs. `t_user_event_track` | ✅ Validated — returns 16 rows for 2026-03-18 |
| **Section 1b** | Date-range variant | ✅ Ready to use |
| **Section 1c** | New users only (p_is_first_day = 'true') | ✅ Ready to use |
| **Section 2** | Full template with all 7 events (needs true source table) | 🔲 Placeholder — requires Redshift access |
| **Section 3** | Diagnostic queries for data exploration | ✅ Ready to use |

---

## 8. Next Steps to Get Complete Dataset

### Option A: Redshift Access (Recommended — 1-2 days)
1. Request Redshift `SELECT` permission for IAM user `databasecheck`
2. Request `redshift:DescribeClusters` / `redshift:GetClusterCredentials` IAM permissions
3. Once connected: run `SHOW TABLES` in Redshift to find the event table
4. Map columns to confirm `adid`, `login_id`, and all 7 event names
5. Replace `{schema}.{event_table}` in Section 2 with actual table name

### Option B: Ask Analyst for Table/Column Names (Same day)
Ask the analyst: "What table and database does your Tableau workbook connect to for this query?"
This bypasses all investigation and gives the exact table name.

### Option C: Check Glue Data Catalog (Self-serve)
Use `manage_aws_glue_databases` to list Glue catalog databases — may reveal the S3/Redshift event table schema.

### Option D: Use MySQL Login Data for Partial Analysis
The current working query (Section 1) covers registration events only (action.login).
It **cannot** provide:
- Traffic/attribution metrics (action.bw, action.ck)
- True adid-based attribution
- Pre-March-5 historical data

---

## 9. Schema Reference: `t_user_event_track`

```sql
-- Verified columns (2026-03-19)
event_time      DATETIME        -- event timestamp (UTC)
tenant          VARCHAR         -- always filter: WHERE tenant = 'LKUS'
channel         VARCHAR         -- acquisition channel (App Store, google play, etc.)
p_os            VARCHAR         -- operating system (iOS, Android)
p_is_first_day  VARCHAR         -- 'true' if user's first day, 'false' otherwise
platform        VARCHAR         -- 1=iOS App, 2=Android App, 3=H5/WeChat
event_type      VARCHAR         -- event name in Sensors Data format
p_device_id     VARCHAR         -- device identifier (sparse; NOT true IDFA/GAID)
user_no         VARCHAR         -- user identifier (maps to login_id concept)
```

---

## 10. Contact & Ownership

- **Query author**: David Zeng (DBA Team)
- **Data owner (MySQL)**: CDP Engineering / isalescdp service
- **Data owner (Redshift)**: Data Platform Team
- **Analyst contact**: Marketing Analytics (provided sample output)
- **Tableau workbook**: Marketing team (for Redshift table name — see Option B above)
