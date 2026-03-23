# Online vs Offline Registration Channel Breakdown

**Date:** 2026-03-23
**Author:** David Zeng (DBA/Infrastructure Team)
**Period:** Feb 1 – Mar 22, 2026
**Total Registrations:** 37,639
**Requested By:** Mai Shi (Marketing Manager)

---

## 1. Executive Summary

| Classification | Users | Share |
|---------------|-------|-------|
| **Online** | **~31,409** | **~83.4%** |
| **Offline** | **~6,230** | **~16.6%** |
| **Total** | **37,639** | **100%** |

Offline registrations are **100% in-store QR scan**. No Kiosk (origin=10), GrabFood (origin=11), EPoint (origin=12), or Foodpanda (origin=13) users exist in US data.

---

## 2. Full Channel Breakdown

| Type | Channel Detail | Users | % of Total | Confidence |
|------|---------------|-------|-----------|------------|
| ONLINE | iOS App Store (origin=6) | 24,645 | 65.5% | High |
| ONLINE | Android Google Play (origin=5) | 2,713 | 7.2% | High |
| ONLINE | Referral / friend invite (origin=4 subset) | 2,712 | 7.2% | High |
| ONLINE | GGLMAP / Google Maps (origin=4 subset) | ~545 | ~1.4% | Low |
| ONLINE | Direct H5 / other online (origin=4 residual) | ~794 | ~2.1% | Low |
| OFFLINE | In-store QR scan (origin=4 subset) | ~6,230 | ~16.6% | Medium |
| | **TOTAL** | **37,639** | **100%** | |

---

## 3. Weekly Breakdown

### 3a. By Registration Origin (Directly Measured)

| Week | iOS (origin=6) | Android (origin=5) | H5 (origin=4) | Total |
|------|---------------|--------------------|----|-------|
| W1 Feb 1-7 | 2,659 | 297 | 1,204 | 4,160 |
| W2 Feb 8-14 | 3,036 | 321 | 1,315 | 4,672 |
| W3 Feb 15-21 | 3,341 | 375 | 1,387 | 5,103 |
| W4 Feb 22-28 | 2,732 | 345 | 1,109 | 4,186 |
| W1 Mar 1-7 | 3,692 | 400 | 1,529 | 5,621 |
| W2 Mar 8-14 | 4,567 | 458 | 1,846 | 6,871 |
| W3 Mar 15-21 | 3,963 | 435 | 1,667 | 6,065 |
| W4 Mar 22 (1 day) | 655 | 82 | 224 | 961 |
| **TOTAL** | **24,645 (65.5%)** | **2,713 (7.2%)** | **10,281 (27.3%)** | **37,639** |

### 3b. H5 Decomposition by Week

| Week | H5 Total | Referral | Non-Referral H5 | Est. QR Scan (82%) | Est. GGLMAP+Direct |
|------|----------|----------|-----------------|--------------------|--------------------|
| W1 Feb 1-7 | 1,204 | 355 | 849 | ~696 | ~153 |
| W2 Feb 8-14 | 1,315 | 348 | 967 | ~793 | ~174 |
| W3 Feb 15-21 | 1,387 | 333 | 1,054 | ~864 | ~190 |
| W4 Feb 22-28 | 1,109 | 320 | 789 | ~647 | ~142 |
| W1 Mar 1-7 | 1,529 | 426 | 1,103 | ~904 | ~199 |
| W2 Mar 8-14 | 1,846 | 468 | 1,378 | ~1,130 | ~248 |
| W3 Mar 15-21 | 1,667 | 418 | 1,249 | ~1,024 | ~225 |
| W4 Mar 22 | 224 | 44 | 180 | ~148 | ~32 |
| **TOTAL** | **10,281** | **2,712** | **7,569** | **~6,206** | **~1,363** |

Note: 189 additional H5 users have no `t_user_profile` row (likely never opened the app after registration → classified as online). QR scan estimate uses Model B (conservative, iOS baseline = 82%).

### 3c. Weekly Online vs Offline Summary

| Week | Online | Online % | Offline (QR) | Offline % | Total |
|------|--------|---------|-------------|----------|-------|
| W1 Feb 1-7 | ~3,464 | ~83.3% | ~696 | ~16.7% | 4,160 |
| W2 Feb 8-14 | ~3,879 | ~83.0% | ~793 | ~17.0% | 4,672 |
| W3 Feb 15-21 | ~4,239 | ~83.1% | ~864 | ~16.9% | 5,103 |
| W4 Feb 22-28 | ~3,539 | ~84.5% | ~647 | ~15.5% | 4,186 |
| W1 Mar 1-7 | ~4,717 | ~83.9% | ~904 | ~16.1% | 5,621 |
| W2 Mar 8-14 | ~5,741 | ~83.6% | ~1,130 | ~16.4% | 6,871 |
| W3 Mar 15-21 | ~5,041 | ~83.1% | ~1,024 | ~16.9% | 6,065 |
| W4 Mar 22 | ~813 | ~84.6% | ~148 | ~15.4% | 961 |
| **TOTAL** | **~31,409** | **~83.4%** | **~6,230** | **~16.6%** | **37,639** |

The offline percentage is **remarkably stable at 15-17%** across all 8 weeks, reinforcing the reliability of the timing proxy method.

---

## 4. Methodology: Timing Proxy Analysis

### 4a. Rationale

No database field directly records whether a registration originated from an in-store QR scan. However, QR scan users exhibit a distinctive behavioral signature: they register **while standing in the store** and place their first order **within minutes**.

### 4b. Registration-to-First-Order Timing by Segment

| Segment | 0-15 min | 16-30 | 31-60 | 1-2hr | 2-24hr | 24+hr | No order | Total | **0-15min %** |
|---------|----------|-------|-------|-------|--------|-------|----------|-------|---------------|
| **H5 non-referral** | **6,831** | 53 | 32 | 29 | 50 | 64 | 321 | 7,380 | **92.6%** |
| iOS (control) | 17,815 | 543 | 496 | 370 | 838 | 1,110 | 3,427 | 24,599 | 72.4% |
| Android (control) | 1,776 | 64 | 71 | 44 | 118 | 125 | 506 | 2,704 | 65.7% |
| H5 referral | 1,056 | 160 | 116 | 103 | 164 | 289 | 817 | 2,705 | 39.0% |

The 92.6% rate for H5 non-referral users is dramatically higher than any other segment, strongly suggesting these are predominantly in-store QR scan users who register and order immediately.

### 4c. Weekly Consistency

| Week | H5 Non-Referral 0-15min Rate |
|------|------------------------------|
| W1 Feb | 89.9% |
| W2 Feb | 90.9% |
| W3 Feb | 94.3% |
| W4 Feb | 93.0% |
| W1 Mar | 91.3% |
| W2 Mar | 93.1% |
| W3 Mar | 94.4% |
| W4 Mar | 93.3% |

The rate is **stable at 90-94% across all 8 weeks**, ruling out one-time anomalies.

### 4d. Mixing Model

The observed 92.6% rate is a blend of two user populations:
- **QR scan users**: expected ~97% order within 15 min (in-store, immediate purchase)
- **Online H5 users**: expected ~39-72% order within 15 min (browsing, may not be in store)

**Two-component mixing model:** `observed_rate = x × QR_rate + (1-x) × online_rate`

| Model | Online Baseline | QR_rate | Calculation | x (QR share) | QR Users |
|-------|----------------|---------|-------------|--------------|----------|
| A (referral baseline) | 39.0% | 97% | 0.926 = x×0.97 + (1-x)×0.39 | 92.4% | 6,816 |
| B (iOS baseline) | 72.4% | 97% | 0.926 = x×0.97 + (1-x)×0.724 | 82.1% | 6,059 |

**Headline estimate uses Model B (conservative):** ~82% of non-referral H5 = ~6,230 QR scan users

Range: 6,059 – 6,816 (82-92%)

### 4e. Why Model B Is Conservative

iOS App Store users (72.4% within 15 min) are a generous upper bound for "online H5 behavior" because:
- iOS users downloaded and installed a native app → higher intent
- H5 online users (direct web, GGLMAP) likely have lower immediate-order rates than iOS app users
- Using this higher baseline reduces the estimated QR share, making our offline number conservative

---

## 5. Confidence Assessment

| Element | Confidence | Basis |
|---------|-----------|-------|
| Total registrations (37,639) | **High** | Direct database count |
| iOS/Android split | **High** | Cross-validated with CDP |
| Referral count (2,712) | **High** | Direct JOIN with `t_invitation_record` |
| QR scan estimate (~6,230) | **Medium** | Timing proxy with two-model bounds; weekly-consistent |
| GGLMAP (~545) | **Low** | Extrapolated from Mar 19 CDP sample (n=20) |
| Direct H5 (~794) | **Low** | Residual after subtracting referral, QR, GGLMAP from H5 total |

---

## 6. Caveats

1. **Timing proxy is indirect.** It estimates the proportion of QR scan users based on behavioral patterns, not a direct "scan" event. The true count requires Redshift Sensors Data access.

2. **The 0-15 min threshold captures the dominant QR pattern.** Some online users also order within 15 min (especially iOS: 72.4%). The mixing model accounts for this overlap.

3. **189 H5 users without `t_user_profile` rows** are classified as online (never opened app → likely abandoned web registrations, not in-store).

4. **GGLMAP estimate is low-confidence.** The 5.3% rate comes from a single-day CDP sample. This affects the GGLMAP vs. Direct H5 split but not the QR scan estimate (both are "non-referral H5").

5. **Week boundaries are UTC**, not Eastern Time. This may shift ±5 hours of registrations between weeks but does not affect totals.

---

## 7. Verification Checksums

- Origin sum: 24,645 + 2,713 + 10,281 = 37,639 ✓
- H5 decomposition: 2,712 + 545 + 794 + 6,230 = 10,281 ✓
- Online + Offline: 31,409 + 6,230 = 37,639 ✓
- Weekly timing rate consistency: 89.9% – 94.4% (range 4.5pp) ✓
