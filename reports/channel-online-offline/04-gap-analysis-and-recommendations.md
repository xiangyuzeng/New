# Updated Gap Analysis and Recommendations

**Date:** 2026-03-23
**Author:** David Zeng (DBA/Infrastructure Team)
**Supersedes:** `/app/reports/channel-attribution/04-gap-analysis.md` (2026-03-19)

---

## 1. What's Now Resolved

| Gap (from Mar 19) | Status Mar 19 | Status Mar 23 | How Resolved |
|-------------------|--------------|--------------|--------------|
| QR scan count | ❌ Cannot isolate | ✅ **Estimated: ~6,230 (16.6%)** | Timing proxy via `t_user_profile.first_pay_time` + mixing model |
| Online vs offline split | ❌ Not possible | ✅ **Online 83.4% / Offline 16.6%** | QR scan estimate enables full classification |
| Referral separation | ⚠️ Partial (same-DB join needed) | ✅ **2,712 confirmed** | `t_invitation_record` JOIN with `t_user` (extended to Mar 22) |
| H5 decomposition | ❌ 4 unknown segments | ✅ **All 4 segments estimated** | Referral (confirmed) + QR (timing proxy) + GGLMAP (CDP sample) + Direct (residual) |
| Weekly consistency | ❓ Unverified | ✅ **90-94% stable across 8 weeks** | Weekly timing rate validation |

---

## 2. What Remains Unresolved

### 2.1 GGLMAP Confidence — LOW

**Problem:** GGLMAP (Google Maps H5) estimate (~545, 5.3% of H5) is based on a single-day CDP sample (n=20 on Mar 19). The actual share could range from 2% to 10%.

**Impact:** Affects the split between GGLMAP and Direct H5, but does NOT affect the QR scan estimate (both are "non-referral H5" and handled by the mixing model residual).

**Resolution path:**
- Wait for CDP to accumulate 2+ weeks of data (by Apr 2)
- Query CDP for GGLMAP share with larger sample
- Or: obtain Redshift access for historical GGLMAP channel data

### 2.2 Social Media Attribution — NO DATA

**Problem:** Adjust deep links have not been deployed. Social media campaigns (TikTok, Instagram, Facebook, Xiaohongshu/Rednote) cannot be attributed.

**Impact:** Any registrations driven by social media are counted as iOS/Android (if user downloads via app store link) or H5 (if user clicks a web link). Cannot measure social media ROI.

**Resolution path:** Adjust SDK integration + deep link deployment (2-4 week project).

### 2.3 QR Touchpoint Breakdown — NOT INSTRUMENTED

**Problem:** All in-store QR codes use the same URL. Cannot determine which physical placement (A-frame, counter, table, etc.) drives registrations.

**Impact:** Cannot optimize in-store QR placement strategy.

**Resolution path:** See `03-qr-touchpoint-breakdown.md` for instrumentation specification. Estimated 4-6 weeks.

### 2.4 Redshift / Glue Access — BLOCKED

**Problem:** IAM user `databasecheck` lacks permissions for Redshift Serverless and Glue Data Catalog.

**Impact:** Cannot run authoritative Sensors Data queries. The timing proxy workaround reduces urgency but Redshift access would:
- Confirm QR scan estimate against actual scan events
- Provide GGLMAP historical data (removing the low-confidence CDP sample dependency)
- Enable paid vs organic App Store/Play attribution (via IDFA/GAID)

**Resolution path:** IAM permission request pending Michael (CTO) approval.

### 2.5 Paid vs Organic App Store/Play — NOT SEPARABLE

**Problem:** iOS (origin=6) and Android (origin=5) counts are totals. Cannot separate organic App Store discovery from paid Apple Search Ads or Google Ads-driven installs.

**Impact:** Cannot measure paid acquisition ROI for app store campaigns.

**Resolution path:** Requires Redshift access for IDFA/GAID advertising ID data, or Adjust integration.

---

## 3. Updated Data Coverage Matrix

| Channel | Feb 1 – Mar 18 | Mar 19 – Mar 22 | Mar 23+ (projected) |
|---------|:--------------:|:----------------:|:-------------------:|
| iOS App Store | ✅ Count | ✅ Count + CDP | ✅ Count + CDP |
| Android Google Play | ✅ Count | ✅ Count + CDP | ✅ Count + CDP |
| Referral (friend invite) | ✅ Confirmed | ✅ Confirmed | ✅ Confirmed |
| **In-store QR Scan** | **✅ Estimated (timing proxy)** | **✅ Estimated** | **✅ Estimated** |
| GGLMAP / Google Maps | ⚠️ Low-confidence | ⚠️ Low-confidence | ⚠️ Improving (CDP accumulating) |
| Social Media | ❌ No data | ❌ No data | ❌ Requires Adjust |
| Paid vs Organic App | ❌ Not separable | ❌ Not separable | ❌ Requires Redshift |

---

## 4. Action Items by Owner

### David Zeng (DBA) — Infrastructure

| # | Action | Priority | Status | Timeline |
|---|--------|----------|--------|----------|
| 1 | ~~Investigate timing proxy for QR estimation~~ | — | ✅ **DONE** | — |
| 2 | ~~Extend date range to Mar 22~~ | — | ✅ **DONE** | — |
| 3 | Request Redshift/Glue IAM permissions (escalate to Michael) | 🟠 High | Pending | 1-2 weeks |
| 4 | Re-query CDP GGLMAP share after 2 weeks accumulation (~Apr 2) | 🟡 Medium | Scheduled | Apr 2 |
| 5 | Query first-order store distribution for QR scan users (per-store breakdown) | 🟢 Low | Optional | As needed |
| 6 | Set up weekly automated pivot refresh (extend query dates each Monday) | 🟡 Medium | Not started | 1 day |

### 马云飞 (Data Analyst)

| # | Action | Priority | Status | Timeline |
|---|--------|----------|--------|----------|
| 1 | Share Redshift table name for Sensors Data events | 🟠 High | Pending | Async |
| 2 | Validate timing proxy results against Tableau data (if possible) | 🟡 Medium | Not started | 1 week |
| 3 | Confirm scan event type name (`$page.scan$...`) | 🟡 Medium | Pending | 1 week |

### 王姣 (Product)

| # | Action | Priority | Status | Timeline |
|---|--------|----------|--------|----------|
| 1 | Implement QR touchpoint instrumentation (see `03-qr-touchpoint-breakdown.md`) | 🟠 High | Not started | 4-6 weeks |
| 2 | Deploy Adjust deep links for social media campaigns | 🟠 High | Not started | 2-4 weeks |
| 3 | Add `src` URL parameter parsing to H5 page + Sensors Data SDK | 🟠 High | Not started | 2 weeks |

### Mai Shi (Marketing)

| # | Action | Priority | Status | Timeline |
|---|--------|----------|--------|----------|
| 1 | ~~Confirm online/offline classification needs~~ | — | ✅ **Delivered** | — |
| 2 | Review QR touchpoint instrumentation spec; confirm placement list | 🟠 High | Pending review | 1 week |
| 3 | Decide social media attribution priority (Adjust deployment) | 🟡 Medium | Not started | 2 weeks |
| 4 | Confirm timezone preference for weekly boundaries (UTC vs EST) | 🟢 Low | Pending | 1 week |

---

## 5. Recommended Next Steps (Priority Order)

1. **Share this report with Mai Shi** — the online/offline split with timing proxy methodology answers the primary question
2. **Schedule CDP re-check for Apr 2** — 2 weeks of CDP data will significantly improve GGLMAP confidence
3. **Escalate Redshift IAM request** — unblocks authoritative validation and future attribution work
4. **Kick off QR touchpoint instrumentation** — the spec is ready; needs Product team commitment
5. **Evaluate Adjust SDK priority** — social media attribution is a separate workstream
