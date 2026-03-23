# QR Code Touchpoint Breakdown — Instrumentation Specification

**Date:** 2026-03-23
**Author:** David Zeng (DBA/Infrastructure Team)
**Status:** No placement-level data exists today. This document specifies the instrumentation needed.

---

## 1. Current State

All in-store QR codes point to the same H5 URL with **no placement parameter**. Whether a user scans an A-frame on the sidewalk, a counter card, a table tent, or a door poster, the resulting registration event is identical:

```
Current QR URL:  https://h5.luckincoffee.us/scan?shop_id=xxx
CDP channel:     nochannel
Placement:       UNKNOWN
```

Result: We can estimate **total** QR scan registrations (~6,230, 16.6% of all registrations) but cannot determine which physical placement drives downloads.

---

## 2. Instrumentation Specification

### 2a. URL Parameter Design

Each QR placement gets a unique `src` parameter appended to the existing H5 URL:

```
https://h5.luckincoffee.us/scan?shop_id={shop_id}&src={placement_code}
```

| Placement Code | Physical Location | Description |
|---------------|-------------------|-------------|
| `aframe` | Sidewalk A-frame sign | Standing sign outside store entrance |
| `counter` | Checkout counter card | Card/stand at POS/ordering counter |
| `table` | Table tent / table sticker | QR placed on customer seating tables |
| `door` | Door/window decal | Glass door or window-facing QR sticker |
| `receipt` | Receipt / bag sticker | QR on printed receipt or takeout bag |
| `poster` | Wall poster | In-store wall-mounted promotional poster |
| `standee` | Floor standee | Free-standing display inside store |
| `other` | Other / miscellaneous | Catch-all for unlisted placements |

### 2b. Complete URL Format

```
https://h5.luckincoffee.us/scan?shop_id={shop_id}&src={placement_code}
```

**Examples:**
| Store | Placement | QR URL |
|-------|-----------|--------|
| Store #001 (Herald Sq) | A-frame | `https://h5.luckincoffee.us/scan?shop_id=001&src=aframe` |
| Store #001 (Herald Sq) | Counter | `https://h5.luckincoffee.us/scan?shop_id=001&src=counter` |
| Store #003 (Times Sq) | Door | `https://h5.luckincoffee.us/scan?shop_id=003&src=door` |
| JFK Kiosk | Counter | `https://h5.luckincoffee.us/scan?shop_id=jfk01&src=counter` |

### 2c. QR Code Generation Requirements

- **One unique QR code per placement per store.** 11 stores × ~4 placements = ~44 QR codes minimum.
- Each QR code encodes the full URL including both `shop_id` and `src` parameters.
- QR codes should be generated at sufficient error correction level (Level M or higher) for reliable scanning in varied lighting conditions.
- Print size: minimum 3cm × 3cm for table/counter, 8cm × 8cm for A-frame/poster.

---

## 3. Data Flow After Instrumentation

```
User scans QR  →  H5 page loads with ?src=aframe&shop_id=001
               →  Sensors Data SDK captures page URL parameters
               →  Event stored with:
                     event_name: $pageview (or scan-specific event)
                     shop_id: "001"
                     src: "aframe"
                     p_is_first_day: "true" / "false"
               →  Flows to:
                     - MySQL t_user_event_track (if configured)
                     - S3 → Redshift (full event stream)
```

### Required Product/Engineering Changes

1. **H5 page**: Parse `src` URL parameter and pass to Sensors Data SDK as a custom property
2. **Sensors Data SDK**: Add `qr_placement` property to the page load event schema
3. **CDP event track**: Include `qr_placement` in `t_user_event_track` for MySQL-accessible reporting
4. **QR code management**: Product team generates and tracks unique QR codes per placement per store

---

## 4. Implementation Timeline (Estimated)

| Phase | Tasks | Duration | Owner |
|-------|-------|----------|-------|
| 1. Design | Finalize placement codes, URL format, SDK property name | 1 week | 王姣 (Product) + DBA |
| 2. H5 Development | Parse `src` parameter, pass to Sensors Data SDK | 1 week | Engineering |
| 3. QR Generation | Generate ~44 unique QR codes (11 stores × 4 placements) | 1 week | Marketing + Product |
| 4. Store Rollout | Print and deploy QR codes to all 11 locations | 1-2 weeks | Operations |
| 5. Validation | Verify events flowing to CDP and/or Redshift | 1 week | DBA + Data Analyst |
| **Total** | | **4-6 weeks** | |

---

## 5. What We Can Do Now: Store-Level QR Distribution

While we cannot break down by touchpoint, we can estimate QR scan registrations by **store** using the first-order store as a proxy. Users who register via QR scan typically place their first order at the same store where they scanned.

### Recommended Query

```sql
-- First-order store distribution for QR-estimated users (H5 non-referral, 0-15 min)
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
```

This would show which stores generate the most QR scan registrations, informing placement optimization even before touchpoint-level tracking is deployed.

---

## 6. Future Reporting Query (Post-Instrumentation)

Once `src` parameters are deployed and flowing to CDP/Redshift:

```sql
-- QR touchpoint breakdown (run on Redshift or CDP)
SELECT
    DATE_TRUNC('week', event_time) AS week,
    src AS qr_placement,
    shop_id,
    COUNT(DISTINCT user_id) AS new_registrations
FROM events
WHERE event_name = '$pageview'
  AND p_is_first_day = 'true'
  AND src IS NOT NULL
  AND event_time >= '2026-02-01'
GROUP BY 1, 2, 3
ORDER BY 1, 4 DESC;
```
