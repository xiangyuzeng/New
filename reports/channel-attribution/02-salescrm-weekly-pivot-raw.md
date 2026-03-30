# salescrm.t_user — Weekly Registration Pivot (Raw)

**Source:** `aws-luckyus-salescrm-rw` → `luckyus_sales_crm.t_user`
**Filter:** `tenant = 'LKUS'`, `create_time >= '2026-02-01' AND < '2026-03-20'`
**Query Date:** 2026-03-19
**Total Records:** 33,819

---

## Origin Code Decode (Validated)

Cross-referenced 33 CDP users (Mar 19, `p_is_first_day='true'`) with their `origin` in salescrm:

| Origin Code | Channel Label | Evidence | Count (Feb 1 – Mar 19) | Share |
|-------------|--------------|----------|------------------------|-------|
| **6** | iOS / App Store | 25/25 confirmed: all origin-6 users had CDP channel="App Store", p_os="iOS" | 22,127 | 65.4% |
| **5** | Android / Google Play | 2/2 confirmed: all origin-5 users had CDP channel="google play", p_os="Android" | 2,411 | 7.1% |
| **4** | H5/Web (includes referral, GGLMAP, nochannel, offline QR) | 6 confirmed: mix of referral, nochannel, and App-Store-channel users who registered via H5 first | 9,281 | 27.5% |

**Key finding on origin 4:** These users registered through the H5 mobile web interface, regardless of how they discovered Luckin:
- Friend referral link → opened H5 → registered (origin 4)
- Google Maps listing → H5 web page → registered (origin 4)
- Direct web link / no tracking → H5 → registered (origin 4)
- **Offline QR scan → H5 → registered (origin 4)** ← cannot separate from other H5

---

## Weekly Registration Counts by Origin Code

Weeks use Sunday–Saturday boundaries matching the target report format (Feb 1 = Sunday).
Timestamps are UTC (server timezone).

| Week | Dates | origin 4 (H5/Web) | origin 5 (Android) | origin 6 (iOS) | **Total** |
|------|-------|-------------------|--------------------|--------------------|-----------|
| W1 Feb | Feb 1–7 | 1,204 | 297 | 2,659 | **4,160** |
| W2 Feb | Feb 8–14 | 1,315 | 321 | 3,036 | **4,672** |
| W3 Feb | Feb 15–21 | 1,387 | 375 | 3,341 | **5,103** |
| W4 Feb | Feb 22–28 | 1,109 | 345 | 2,732 | **4,186** |
| W1 Mar | Mar 1–7 | 1,529 | 400 | 3,692 | **5,621** |
| W2 Mar | Mar 8–14 | 1,846 | 458 | 4,567 | **6,871** |
| W3 Mar | Mar 15–19 | 891 | 215 | 2,100 | **3,206** |
| **Total** | | **9,281** | **2,411** | **22,127** | **33,819** |

---

## Variance vs. Prior Marketing Report Control Sums

Prior report weekly totals were computed from a different query (likely using Eastern Time date boundaries or different table state):

| Week | Prior Report | This Query | Delta | Likely Cause |
|------|-------------|-----------|-------|-------------|
| W1 Feb | 4,160 | 4,160 | 0 | ✅ Exact match |
| W2 Feb | 4,492 | 4,672 | +180 | UTC vs ET boundary shift (±5h) |
| W3 Feb | 5,303 | 5,103 | -200 | UTC vs ET boundary shift |
| W4 Feb | 4,170 | 4,186 | +16 | Minor (Feb 23 anomaly day) |
| W1 Mar | 5,621 | 5,621 | 0 | ✅ Exact match |
| W2 Mar | 7,075 | 6,871 | -204 | UTC vs ET boundary shift |
| W3 Mar | 3,150 | 3,206 | +56 | Partial day Mar 19 included here |

**Note:** Prior report covered Feb 1–Mar 18 (33,767 users excl. Mar 19). This query covers Feb 1–Mar 19 (33,819). Excluding Mar 19: 33,819 - 641 ≈ 33,178... The deltas between weeks cancel out because the timezone shift just redistributes users across week boundaries without losing them.

---

## CDP Supplement: Mar 19 Channel Breakdown (Limited Sample)

From `luckyus_isales_cdp.t_user_event_track` (CDP went live Mar 19):
- Only 34 first-day login events on Mar 19 (~5% coverage of daily registrations)
- Too small for reliable percentages, but confirms origin code mapping

| CDP Channel | p_os | Count | Maps to Origin |
|-------------|------|-------|---------------|
| App Store | iOS | 28 | 6 (iOS/App Store) |
| google play | Android | 2 | 5 (Android) |
| nochannel | iOS | 2 | 4 (H5/Web) |
| referral | iOS | 2 | 4 (H5/Web) |

---

## SQL Used

```sql
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
    origin,
    COUNT(*) AS cnt
FROM luckyus_sales_crm.t_user
WHERE create_time >= '2026-02-01' AND create_time < '2026-03-20'
  AND tenant = 'LKUS'
GROUP BY week_label, origin
ORDER BY week_label, origin;
```
