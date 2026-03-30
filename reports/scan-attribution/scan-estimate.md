# Offline QR Scan Registrations — Estimate

**Date:** 2026-03-19
**Period:** Feb 1 – Mar 19, 2026 (7 weeks)
**Author:** David Zeng (DBA/Infrastructure)
**Confidence:** MEDIUM-LOW (inferred, not direct count)

---

## Baseline

| Metric | Value | Source |
|--------|-------|--------|
| Total registrations (Feb 1–Mar 19) | 33,819 | salescrm.t_user |
| iOS App Store (origin=6) | 22,127 | Direct count ✅ |
| Android Google Play (origin=5) | 2,411 | Direct count ✅ |
| H5/Web combined (origin=4) | 9,281 | Direct count ✅ |

The 9,281 H5/Web users are the pool from which offline QR scan must be extracted.

---

## Confirmed Subtraction

### Referral (好友拉新) — HIGH CONFIDENCE

**Method:** Direct JOIN between `t_invitation_record` and `t_user` within `luckyus_sales_crm`.

| Week | origin=4 Total | Referral Users | Non-Referral H5 |
|------|---------------|----------------|-----------------|
| W1 Feb 1–7 | 1,204 | 355 | 849 |
| W2 Feb 8–14 | 1,315 | 348 | 967 |
| W3 Feb 15–21 | 1,387 | 333 | 1,054 |
| W4 Feb 22–28 | 1,109 | 320 | 789 |
| W1 Mar 1–7 | 1,529 | 426 | 1,103 |
| W2 Mar 8–14 | 1,846 | 468 | 1,378 |
| W3 Mar 15–19 | 891 | 221 | 670 |
| **Total** | **9,281** | **2,471 (26.6%)** | **6,810 (73.4%)** |

> 2,471 origin=4 users came through a friend invitation link. These are NOT offline QR scan.

---

## GGLMAP Estimate — LOW CONFIDENCE

**Source:** CDP `t_user_event_track` Mar 19 only (n=20 H5 logins).

On Mar 19, 2 out of 20 H5 login events carried `channel = 'GGLMAP901'` = **10%**.

However, the same Mar 19 sample shows 50% referral share vs. the confirmed full-period 26.6%, indicating the sample is skewed. Applying a proportional correction:

- Full-period referral share: 26.6%
- Mar 19 referral share: 50.0%
- Correction factor: 26.6% / 50.0% = **0.532**
- Adjusted GGLMAP share: 10% × 0.532 ≈ **5.3%**
- GGLMAP estimate: 9,281 × 5.3% ≈ **~490 users**
- Plausible range: **~400–900 users** (high uncertainty)

---

## QR Scan + Direct H5 Estimate — LOW CONFIDENCE

After removing referral and GGLMAP:

| Component | Count | Confidence |
|-----------|-------|-----------|
| Total origin=4 | 9,281 | ✅ High |
| − Referral | −2,471 | ✅ High |
| − GGLMAP (est.) | −490 (range: −400 to −900) | ⚠️ Low |
| **= QR Scan + Direct H5** | **~6,320** (range: 5,981–6,410) | ⚠️ Low |

Within this residual (~6,320), **no data source distinguishes** QR scan from direct H5 web access:
- Both land as `channel = 'nochannel'` in CDP
- Both register through the H5 interface (`origin=4`)
- The QR scan "scan" page exists (confirmed in CDP pageview data) but is visited by both new and existing users

**Key evidence that QR scan is a significant fraction of the residual:**
1. Luckin has 11 physical stores in Manhattan — in-store QR is the primary acquisition mechanism at the counter
2. CDP data shows the "scan" page exists in the H5 flow (p_title="scan" → p_referrer="scan" pattern confirmed)
3. For a coffee chain with 500-600 daily orders/store, in-store QR is likely the dominant H5 acquisition path

**Working assumption (for planning purposes only):**
If 70-80% of the non-referral, non-GGLMAP H5 users came via QR scan:
- QR scan estimate: ~4,420–5,050 users
- Direct H5 (no QR): ~1,270–1,900 users

> ⚠️ This working assumption has NO data backing. It is a planning proxy only.
> **The authoritative answer requires Redshift access.** See action items below.

---

## Summary Estimate Table

| Channel | Count | Confidence |
|---------|-------|-----------|
| iOS App Store | 22,127 | ✅ High — direct count |
| Android Google Play | 2,411 | ✅ High — direct count |
| 好友拉新 (Referral H5) | 2,471 | ✅ High — confirmed join |
| GGLMAP (Google Maps H5) | ~490 | ⚠️ Low — Mar 19 sample n=20 |
| 线下扫码 + Direct H5 | ~6,320 | ⚠️ Low — residual after subtraction |
| **Total** | **33,819** | ✅ Verified |

---

## To Get the Real Answer

| Action | Owner | Unblocks |
|--------|-------|----------|
| Grant `redshift-serverless:ListWorkgroups` + `redshift-data:ExecuteStatement` + `redshift-data:GetStatementResult` to IAM user `databasecheck` | Michael (CTO / AWS admin) | Authoritative scan event count from Sensors Data |
| Ask 马云飞 (data analyst) for Redshift schema/table name | 马云飞 | Can query even before IAM fix if analyst runs it |
| Add `shop_id` UTM parameter to in-store QR codes | Product (王姣) | Future weeks: QR scan becomes directly countable in CDP |
