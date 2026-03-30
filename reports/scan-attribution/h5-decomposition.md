# H5/Web (origin=4) Decomposition — Feb 1 to Mar 19, 2026

**Total origin=4 users:** 9,281
**Period:** 2026-02-01 to 2026-03-19
**Author:** David Zeng (DBA/Infrastructure)
**Date:** 2026-03-19

---

## What origin=4 Contains

All users who registered through the H5 mobile web interface, regardless of how they found Luckin:

```
origin=4 (H5/Web) = 9,281 users
├── 好友拉新 (Referral / Friend Invitation) ──── 2,471 ✅ confirmed
├── GGLMAP (Google Maps H5)  ────────────────── ~490  ⚠️ estimated
├── 线下扫码 (Offline QR Scan) ─────────────── unknown ❌
└── Direct H5 (no channel / nochannel) ──────── unknown ❌
     [QR scan and direct web both appear as 'nochannel' in CDP]
```

---

## Sub-Segment Detail

### 1. 好友拉新 (Referral) — 2,471 users (26.6%) ✅

**How confirmed:** JOIN between `salescrm.t_invitation_record.invitee_user_no` and `salescrm.t_user` filtered to `origin=4`.

**What it means:** User received a friend's invitation link, clicked it, opened the H5 page, and registered. The referral URL carries an invitation code that creates an `t_invitation_record` entry.

**Weekly detail:**

| Week | Referral Count |
|------|---------------|
| W1 Feb | 355 |
| W2 Feb | 348 |
| W3 Feb | 333 |
| W4 Feb | 320 |
| W1 Mar | 426 |
| W2 Mar | 468 |
| W3 Mar | 221 |
| **Total** | **2,471** |

---

### 2. GGLMAP (Google Maps) — ~490 users (5.3%) ⚠️

**How estimated:** On Mar 19, 2 of 20 H5 login events in CDP carried `channel='GGLMAP901'` (10%).
Proportional correction applied: full-period referral is 26.6% but Mar 19 sample shows 50%, implying sample overweights referral by ~1.88×. Adjusted GGLMAP share: 10% / 1.88 ≈ 5.3%.

**What it means:** User found Luckin on Google Maps, tapped the link in the business listing, which loaded the H5 web ordering page. They registered there. Google Maps attribution is passed as `GGLMAP901` channel code.

**Classification note:** GGLMAP is an **online channel** (digital discovery), not an offline channel. It should appear in the "online/其他线上" row in the marketing report, not as "线下扫码."

**Range:** 400–900 users. Very uncertain — only n=20 Mar 19 sample available.

---

### 3. 线下扫码 (Offline QR Scan) — UNKNOWN ❌

**What it is:** User scans a QR code displayed in-store (on the counter, wall, packaging) → lands on H5 page → registers.

**Why unknown:**
- Current in-store QR codes have **no UTM parameters** → land as `channel='nochannel'` in CDP
- The Sensors Data scan event (`$page.scan$...`) exists in the H5 page flow — confirmed by CDP `p_title="scan"` and `p_referrer_title="scan"` page views — but:
  - These events are browsing events, not registration events
  - They include both new and returning users
  - The scan page visit count ≠ scan-sourced registrations

**Evidence scan page exists:**
```
CDP $pageview events Mar 19:
  p_title="scan" + p_referrer_title=""  →  3 pageviews
  p_title="home" + p_referrer_title="scan"  →  3 pageviews
All carried channel='nochannel'
```

**Where the data lives:** Redshift Serverless (Sensors Data full event stream). The authoritative count would come from:
```sql
SELECT DATE_TRUNC('week', event_time) AS week,
       COUNT(DISTINCT login_id) AS qr_scan_registrants
FROM <sensors_data_schema>.events
WHERE event_name LIKE '$page.scan%'
  AND p_is_first_day = 'true'
  AND event_time >= '2026-02-01'
GROUP BY 1 ORDER BY 1;
```
(Table name and schema TBD — need confirmation from 马云飞 or Redshift IAM access.)

---

### 4. Direct H5 / Nochannel — UNKNOWN ❌

Users who accessed the H5 web ordering page directly (typed URL, bookmarked link, unannotated shared link) and registered. These also land as `channel='nochannel'` — indistinguishable from QR scan in MySQL.

---

## Decomposition Summary

| Sub-Channel | Count | % of H5 | % of Total | Confidence |
|------------|-------|---------|-----------|-----------|
| 好友拉新 (Referral) | 2,471 | 26.6% | 7.3% | ✅ High |
| GGLMAP | ~490 | ~5.3% | ~1.4% | ⚠️ Low |
| 线下扫码 (QR Scan) | unknown | unknown | unknown | ❌ |
| Direct H5 / nochannel | unknown | unknown | unknown | ❌ |
| **H5 Total** | **9,281** | **100%** | **27.5%** | ✅ |

> Rows 1–2 sum to ~2,961. The remaining ~6,320 are split between QR scan and direct H5 in an unknown ratio.
> Per the plan verification requirement: Referral (2,471) + GGLMAP (~490) + QR+Direct (6,320) = **9,281** ✅

---

## Action Required to Resolve Unknown

| Priority | Action | Owner | Unlocks |
|---------|--------|-------|---------|
| 🔴 Critical | Request `redshift-serverless:ListWorkgroups` + `redshift-data:*` IAM permissions for `databasecheck` user | Michael (CTO) | Direct Sensors Data query for scan events |
| 🔴 Critical | Ask 马云飞: "What Redshift database/schema does your Tableau workbook use for channel attribution?" | David / 马云飞 | Can query Redshift once access is granted |
| 🟠 High | Add `?source=shop_qr&shop_id={id}` to all in-store QR code URLs | 王姣 (Product) | Future: QR scan becomes directly countable without Redshift |

---

## Notes for Marketing Report

If the marketing team needs a value for "线下扫码" before Redshift access is obtained:

**Conservative proxy:** Use "non-referral H5" = 6,810 as the upper bound for QR scan + GGLMAP + direct web.
**Best estimate for QR scan only:** 3,500–5,000 (assumes 50-75% of non-referral, non-GGLMAP H5 came from in-store QR).
**Label clearly as estimate** with note: "Pending Redshift Sensors Data access for authoritative count."
