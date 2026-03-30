# Marketing Traffic & Registration Analysis Report

**Report Date:** 2026-03-19
**Prepared by:** DBA/Infrastructure Team (David Zeng)
**Data Sources:** isalescdp CDP event tracking, salescrm user registration
**Coverage:** Feb 1 – Mar 19, 2026 (registrations) | Oct 2025 – Mar 19, 2026 (CDP events)

---

## 1. Executive Summary

| KPI | Value | Notes |
|-----|-------|-------|
| Total Registrations (Feb 1 – Mar 18) | **33,767** | Excludes Mar 19 partial day |
| Feb Average Daily Registrations | **647/day** | 18,125 over 28 days |
| Mar Average Daily Registrations | **869/day** | 15,642 over 18 full days (+34% vs Feb) |
| Peak Registration Day | **Mar 8: 1,245** | Sustained high Mar 7–11 |
| CDP Go-Live | **2026-03-19** | 3,371 events on first full day |
| Top Acquisition Channel | **App Store (83.1%)** | iOS dominates user acquisition |
| Platform Split | **87.1% iOS / 12.7% Android / 0.2% H5** | |
| Push Campaign Events | **3** | Tracking just enabled; not yet statistically significant |

**Key Takeaway:** March 2026 shows a strong 34% uplift in daily registrations vs. February, driven by marketing campaigns in the Mar 7–11 and Mar 14 windows. The CDP event tracking system went live on March 19, providing the first full-scale behavioral data. Early indicators confirm iOS/App Store as the dominant acquisition channel.

---

## 2. User Registration Trend

### 2.1 Monthly Summary

| Period | Days | Total Registrations | Daily Avg | Peak Day |
|--------|------|--------------------|-----------|----|
| Feb 2026 | 28 | 18,125 | 647 | Feb 21: 937 |
| Mar 1–18 2026 | 18 | 15,642 | 869 | Mar 8: 1,245 |
| **Combined** | **46** | **33,767** | **734** | |

**Month-over-month trend:** +34% daily average increase from February to March.

### 2.2 Notable Registration Events

**February spikes:**
- **Feb 14 (Valentine's Day): 923** — Likely driven by a Valentine's Day promotion. +43% above Feb average.
- **Feb 21: 937** — Campaign effect (possibly Lunar New Year period activity).
- **Feb 26–28: 967 / 835 / 1,035** — End-of-month push, possibly driven by February app store featured placement or coupon campaign.

**February anomaly:**
- **Feb 22: 365 and Feb 23: 66** — Sharp two-day drop. Feb 23 is only 10% of surrounding days' average. This likely indicates a tracking/ingestion issue, not a genuine traffic collapse. Recommend verifying with ops team whether a registration pipeline issue occurred around this date.

**March acceleration:**
- **Mar 7–8: 1,165 / 1,245** — Strongest consecutive two-day period in the dataset. +91% above Feb average.
- **Mar 10–11: 1,021 / 1,022** — Sustained high engagement.
- **Mar 14: 1,076** — Mid-month campaign activity.
- **Mar 7–14 average: 1,005/day** — Week-long elevated period suggesting a sustained campaign or external media coverage.

**Current week (Mar 15–18):**
- Averaging ~788/day — cooling from the peak week but still above Feb baseline. Healthy normalized trend.

### 2.3 Week-by-Week Breakdown

| Week | Dates | Total | Daily Avg | Notable |
|------|-------|-------|-----------|---------|
| W1 Feb | Feb 1–7 | 4,160 | 594 | Baseline |
| W2 Feb | Feb 8–14 | 4,492 | 642 | Valentine's spike |
| W3 Feb | Feb 15–21 | 5,303 | 758 | Feb 21 spike |
| W4 Feb | Feb 22–28 | 4,170 | 596 | Feb 23 anomaly |
| W1 Mar | Mar 1–7 | 5,621 | 803 | Ramp-up begins |
| W2 Mar | Mar 8–14 | 7,075 | 1,011 | **Peak week** |
| W3 Mar | Mar 15–18 | 3,150 | 788 | Normalizing |

---

## 3. Channel Attribution Analysis

### 3.1 Channel Distribution

| Channel | Total Events | Distinct Users | Events/User | Interpretation |
|---------|-------------|----------------|-------------|----------------|
| **App Store** | 3,052 | 125 | 24.4 | Primary iOS acquisition; high engagement depth |
| **Google Play** | 440 | 31 | 14.2 | Android acquisition; growing |
| **No Channel** | 176 | 94 | 1.9 | H5/Web sessions; low depth, high breadth |
| **Referral** | 3 | 1 | 3.0 | Word-of-mouth; minimal but emerging |

### 3.2 Key Insights

**App Store dominance:** The App Store accounts for 83.1% of all tracked events and 79.1% of distinct users. App Store users generate 24.4 events per user vs. 14.2 for Google Play — indicating iOS users have significantly higher session depth and app engagement.

**Google Play growth potential:** At 12.0% event share with only 31 users, Android users show healthy engagement (14.2 events/user) but represent an underpenetrated market. Given NYC demographics (~30%+ Android), there is headroom for Android acquisition growth.

**No-channel (H5/Web):** 176 events across 94 users = 1.9 events/user. These are primarily `$pageview` and `$WebStay` events from the web interface. High user count (94) but very low engagement depth — most H5 visitors do not convert to app sessions. This represents a conversion opportunity: H5 → App download CTA optimization could improve acquisition efficiency.

**Referral channel:** Only 3 events, 1 user at this stage. The referral program is either newly launched, not widely tracked, or underperforming. Recommend investigating referral attribution setup.

---

## 4. Platform Mix Analysis

### 4.1 Platform Share

| Platform | Events | Share | Avg Events/User |
|----------|--------|-------|-----------------|
| iOS App (Platform 1) | ~3,196 | 87.1% | ~25.6 |
| Android App (Platform 2) | ~468 | 12.7% | ~15.1 |
| H5/Web (Platform 3) | ~7 | 0.2% | ~1.4 |

### 4.2 OS Version Context

All iOS events arrive via App Store channel; all Android events via Google Play. The H5 platform registers almost no events relative to app platforms — confirming Luckin USA is fundamentally an app-first product with minimal web engagement.

### 4.3 Platform Implications

- **iOS-first optimization is correct:** The 87% iOS share validates investing in iOS-specific features (Apple Pay, iOS push notifications, App Store optimization).
- **Android gap:** 12.7% Android share in a market where Android users represent ~30–40% of smartphone users suggests either (a) lower Android conversion from awareness to install, or (b) Android app experience gaps. Benchmark: If Android share reached 25%, that would add ~100 additional DAU based on current user counts.
- **H5 is entry-only:** H5 serves as a discovery surface (0.2% events) but drives minimal engagement. Users who enter via H5 need a frictionless app download prompt.

---

## 5. Event Type Analysis

### 5.1 Event Volume Breakdown

| Category | Events | Share | Interpretation |
|----------|--------|-------|----------------|
| App Screen (page_start/end, $AppViewScreen) | 2,941 | 80.1% | Core navigation activity |
| App Lifecycle ($AppStart/End/Passive) | 528 | 14.4% | Session boundaries |
| Web/H5 ($pageview, $WebStay) | 177 | 4.8% | Web traffic |
| Login (app + h5) | 22 | 0.6% | Authentication events |
| Push | 3 | 0.1% | Notification tracking (just enabled) |

### 5.2 App Engagement Quality

**Screen view symmetry:** page_start (977) ≈ page_end (767) ≈ $AppViewScreen (981). The ~21% drop from page_start to page_end suggests some sessions exit without completing a page view cycle — normal for navigation patterns.

**Session start/end ratio:** $AppStart (240) vs. $AppEnd (285). More ends than starts in this window may indicate app backgrounding behaviors being counted differently on iOS vs. the start event.

**Login events:** 20 app logins + 2 H5 logins tracked = 22 total. These represent new session authentications. Low relative to total users (22 logins / 158 users = ~14%) is expected if most users maintain persistent sessions.

### 5.3 User Engagement Depth

- App Store iOS users: avg ~24 events/user → **High engagement** (multiple screens, sessions)
- Google Play Android: avg ~14 events/user → **Moderate engagement**
- No Channel H5: avg ~1.9 events/user → **Bounce-heavy**

The 12x engagement gap between App and H5 users reinforces the app-first strategy.

---

## 6. CDP Go-Live Analysis (2026-03-19)

### 6.1 CDP System Launch

The CDP event tracking system (`t_user_event_track`) registered:
- **Oct 2025 – Mar 18, 2026:** 300 total events (26 unique days of data; QA/test traffic)
- **Mar 19, 2026 (today):** **3,371 events** in a single day

This 1,124× jump confirms March 19 as the CDP production go-live date. Today's data represents the first valid production behavioral dataset.

### 6.2 First-Day Behavioral Profile (Mar 19)

**Top events on go-live day:**

| Event | Count | Distinct Users |
|-------|-------|----------------|
| $AppViewScreen | 939 | ~130 |
| page_start | 935 | ~129 |
| page_end | 863 | ~113 |
| $AppEnd | 225 | ~126 |
| $AppStart | 218 | ~126 |
| $pageview (H5) | 150 | ~91 |
| login events | 20 | ~17 |
| push events | 3 | 3 |

**Active users on CDP go-live day:** ~159 distinct users tracked.

This represents a sample of active users — the full daily active user population is larger; the CDP SDK may still be rolling out to all app versions.

### 6.3 Push Campaign Events (Mar 19)

| Funnel Stage | Event | Count |
|-------------|-------|-------|
| Notification shown | push_show_bw | 1 |
| Notification clicked | push_click_ck | 1 |
| App opened from push | push_start_app | 1 |

**Funnel:** 100% click-through rate and 100% open rate — but sample size is 1. These events indicate the push notification tracking pipeline is correctly wired end-to-end. As push volume scales, this funnel will provide meaningful CTR and conversion metrics.

**Note on "Mar 18 spike":** The previous analysis session flagged a potential Mar 18 event. Actual Mar 18 data shows only 60 events (pre-launch testing). The significant activity began on Mar 19 with the CDP go-live.

---

## 7. Data Gaps & Limitations

| Gap | Description | Impact | Recommendation |
|-----|-------------|--------|----------------|
| CDP go-live recency | All meaningful event data is from Mar 19 only | Cannot establish behavioral trends; no baseline | Re-run analysis in 7–14 days for trend analysis |
| t_user_event_track row count | Estimated 258K rows (info_schema) vs. actual 3,671 | Previous count was MySQL InnoDB estimate (often ~10x off); actual is 3,671 | Use COUNT(*) not info_schema for row counts |
| Feb 22–23 registration anomaly | 365 → 66 registrations (89% drop in 2 days) | Potential data quality issue | Verify with upstream registration system logs |
| H5 channel attribution | 94 distinct users in "nochannel" bucket | H5 users not attributed to a source | Implement UTM parameter tracking for H5 |
| Push campaign data | Only 3 push events (1 per event type) | No statistically valid CTR/open rate | Collect 7+ days of push data |
| Referral tracking | 3 events total | Cannot measure referral program effectiveness | Verify referral SDK integration |
| No order/purchase events | CDP tracks navigation only; no conversion events | Cannot compute registration→order funnel | Add purchase event to CDP schema |
| t_user_event table | Separate 84K-row table not analyzed in this report | May contain additional behavioral data | Explore schema in next session |

---

## 8. Recommendations

### Immediate (This Week)

1. **Monitor CDP data quality:** With go-live today (Mar 19), establish a daily check on event ingestion volume. Alert if daily events drop below 500 (would indicate SDK instrumentation gap).

2. **Fix Feb 22–23 registration anomaly:** Investigate the 89% registration drop on Feb 22–23. If it's a data pipeline issue, back-fill or annotate the data. If genuine, identify the cause (app store review period? server issue?).

3. **Expand push tracking sample:** The push funnel (push_show_bw → push_click_ck → push_start_app) is correctly wired. Measure CTR after first 1,000 push notifications sent.

### Short-Term (2–4 Weeks)

4. **H5-to-App conversion CTA:** With 94 "nochannel" H5 users and only 1.9 events/user, add an in-page app download banner for H5 sessions. Target: convert 20% of H5 visitors to app installs (would add ~19 new app users per day at current volume).

5. **Android acquisition push:** With 87% iOS vs. 12% Android in a market where Android is ~30% of devices, run a targeted Google Play Store optimization campaign. A/B test the Play Store listing description and screenshots.

6. **Valentine's Day / event-driven campaigns:** Feb 14 showed a 43% uplift. Mar 7–8 showed 91% uplift. Identify what campaigns drove these and document them as reusable playbooks.

7. **Add purchase/order events to CDP:** Currently only navigation events are tracked. Adding `order_placed`, `checkout_started`, and `menu_viewed` events to the CDP schema will enable full funnel analysis from registration → first order.

### Strategic (Next Quarter)

8. **Referral program instrumentation:** With referral showing 0.1% of events, investigate whether the referral program is correctly attributed in the CDP. Referral/word-of-mouth should be a high-value channel for a social coffee brand.

9. **Cohort analysis readiness:** Once 30+ days of CDP data are available, build cohort retention analysis: what % of users registered in Week X are still active in Week X+2?

10. **Registration vs. DAU gap analysis:** Current CDP shows ~159 active users/day on go-live. With 277K registered users, this implies very low activation. Analyze the registration-to-active funnel: How many of 33K+ registrations since Feb 1 are generating app sessions?

---

*Report generated from live production data. CDP events data as of 2026-03-19 reflects first-day go-live figures only. Re-run this analysis after 7 days for trend-based insights.*
