# Channel Attribution — Data Access Discovery Report

**Date:** 2026-03-23
**Author:** David Zeng (DBA/Infrastructure Team)
**Period Under Analysis:** Feb 1 – Mar 22, 2026 (37,639 registrations)
**Purpose:** Document all data source investigations, accessibility results, and the key breakthrough enabling online/offline estimation

---

## 1. Investigation Summary

10 discovery attempts were made across 7 databases, 2 data warehouse services, and 1 CDP platform. The key breakthrough came from discovering `t_user_profile` in the salescrm database, which contains `first_pay_time` in the same server as `t_user`, enabling a timing proxy analysis without cross-server joins.

| # | Investigation Target | Server/Service | Result | Actionable? |
|---|---------------------|----------------|--------|-------------|
| 1.1 | Origin value enumeration | salescrm | Only origin 4, 5, 6 exist. No 10/11/12/13 (Kiosk/GrabFood/EPoint/Foodpanda = 0 users) | Yes |
| 1.2 | `t_user_event` table (84K rows) | isalescdp | Schema: tinyint `event_type`, no channel/source columns. Dead end. | No |
| 1.3 | CDP expansion Mar 19-23 | isalescdp | Mar 23: 4,841 events / 162 users (CDP activated). First-day logins: 15 iOS, 1 Android, 1 H5 nochannel. No GGLMAP. No scan pageviews. | Partially |
| 1.4 | `salesmarketing` DB | salesmarketing | Coupon/promotion tables only. No attribution mapping. | No |
| 1.5 | `isalesdatamarketing` DB | isalesdatamarketing | A/B experiment bucketing only. No channel data. | No |
| 1.6 | Redshift Serverless | redshift | AccessDenied — IAM `databasecheck` user lacks permissions | No |
| 1.7 | Glue Data Catalog | glue | AccessDenied — same IAM issue | No |
| 1.8 | `salesorder.t_order` | salesorder | Has `pay_time`, `shop_id`, `user_no`. Different server from salescrm. | Unnecessary |
| B1 | **`t_user_profile` schema** | **salescrm** | **Has `first_pay_time`, `first_order_time`, `first_login_origin`, `get_platform`. Same DB as `t_user`!** | **Yes — KEY** |
| B2 | `first_login_origin` field | salescrm | ALL NULL for origin=4 users. Dead end for direct classification. | No |
| B3 | `get_platform` field | salescrm | 6,038 = value 2 (iOS), 4,047 = NULL. Most H5 users are on iOS Safari. | Informational |

---

## 2. Database/Table Accessibility Matrix

| Database | Server | Tables Queried | Access | Useful for Attribution? |
|----------|--------|---------------|--------|------------------------|
| `luckyus_sales_crm` | aws-luckyus-salescrm-rw | `t_user`, `t_user_attribute`, `t_invitation_record`, **`t_user_profile`** | Read ✅ | **Yes — primary source + timing proxy** |
| `luckyus_isales_cdp` | aws-luckyus-isalescdp-rw | `t_user_event`, `t_user_event_track` | Read ✅ | Partial (Mar 19+ only) |
| `luckyus_sales_marketing` | aws-luckyus-salesmarketing-rw | `t_marketing_channel`, coupon tables | Read ✅ | No (planning data only) |
| `luckyus_isales_data_marketing` | aws-luckyus-isalesdatamarketing-rw | A/B experiment tables | Read ✅ | No |
| `luckyus_sales_order` | aws-luckyus-salesorder-rw | `t_order` | Read ✅ | Unnecessary (profile has timing) |
| Redshift Serverless | AWS Redshift Data API | — | ❌ AccessDenied | Would unlock full Sensors Data |
| Glue Data Catalog | AWS Glue API | — | ❌ AccessDenied | Would reveal Redshift schema |

---

## 3. The Key Breakthrough: `t_user_profile`

### Discovery

While searching for ways to link registration to first-order behavior without cross-server joins, the `t_user_profile` table was discovered in the same `luckyus_sales_crm` database as `t_user`.

### Schema (relevant columns)

| Column | Type | Population | Notes |
|--------|------|-----------|-------|
| `user_no` | varchar | 100% | Join key to `t_user` |
| `first_pay_time` | datetime | ~96% of paying users | First completed payment timestamp |
| `first_order_time` | datetime | ~96% of ordering users | First order placement timestamp |
| `first_login_origin` | int | ALL NULL for origin=4 | Dead end |
| `get_platform` | int | ~60% populated | 2 = iOS; mostly NULL for H5 |

### Why This Matters

With `first_pay_time` available in the same database as `create_time` (registration timestamp), we can compute **registration-to-first-order timing** for every user segment. This timing pattern turns out to be the key differentiator between in-store QR scan registrations (order within minutes) and online registrations (order hours/days later or never).

---

## 4. Comparison to Prior Investigation

| Aspect | Prior (Mar 19) | Updated (Mar 23) |
|--------|---------------|------------------|
| Period | Feb 1 – Mar 19 (33,819 users) | Feb 1 – Mar 22 (37,639 users) |
| QR scan estimate | "Unknown ❌" | **~6,230 (16.6%) via timing proxy** |
| Referral count | 2,471 | 2,712 (+241 from extended date range) |
| GGLMAP estimate | ~490 (5.3% of H5) | ~545 (5.3% of H5, proportionally scaled) |
| Method | CDP sample only (n=34) | Timing proxy with 37K+ users, validated weekly |
| Confidence | Low (cannot isolate) | Medium (model-based, weekly-consistent) |
| Data source | salescrm.t_user only | salescrm.t_user + t_user_profile (same server) |

---

## 5. Data Sources Still Blocked

| Source | Blocked By | Impact | Escalation |
|--------|-----------|--------|------------|
| Redshift Serverless | IAM `databasecheck` lacks `redshift-serverless:ListWorkgroups`, `redshift-data:*` | Cannot query full Sensors Data event stream directly | Pending Michael (CTO) approval |
| Glue Data Catalog | Same IAM permissions gap | Cannot discover Redshift schema/table names | Same IAM request |

These remain the primary blockers for authoritative scan event counting vs. the timing proxy approach.
