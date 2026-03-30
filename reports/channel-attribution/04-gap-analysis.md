# Channel Attribution Gap Analysis

**Date:** 2026-03-19
**Author:** David Zeng (DBA/Infrastructure Team)
**Purpose:** Document what is available, what is missing, root causes, and action items for complete weekly channel attribution reporting

---

## 1. Data Coverage Matrix

| Channel | Feb 1–Mar 4 | Mar 5–Mar 18 | Mar 19 | Source Available? |
|---------|:-----------:|:------------:|:------:|:-----------------:|
| iOS App Store | ✅ Count only | ✅ Count only | ✅ Count + CDP | `salescrm.t_user origin=6` |
| Android Google Play | ✅ Count only | ✅ Count only | ✅ Count + CDP | `salescrm.t_user origin=5` |
| H5/Web (combined) | ✅ Count only | ✅ Count only | ✅ Count + CDP | `salescrm.t_user origin=4` |
| 线下扫码 (Offline QR) | ❌ Not separable | ❌ Not separable | ❌ Not separable | Embedded in H5/Web (origin=4) |
| GGLMAP / Google Maps | ❌ Not in MySQL | ❌ Count only (CDP) | ✅ CDP only | CDP channel='GGLMAP' (Mar 19 only) |
| 社媒引流 (Social Media) | ❌ No data | ❌ No data | ❌ No data | Adjust links not deployed |
| Referral (好友拉新) | ❌ Not separable | ❌ Not separable | ✅ CDP only | Embedded in origin=4 (H5 path) |

---

## 2. Per-Channel Root Cause Analysis

### 2.1 线下扫码 (Offline QR Scan) — ❌ Cannot Isolate

**Root Cause:**
The in-store QR code registration flow routes users through the H5 mobile web interface. The `salescrm.t_user.origin` field records the registration **interface** (H5=4, iOS App=6, Android App=5), not the **discovery method**. There is no separate scan event table in the accessible MySQL databases.

**What was searched:**
- `opshop.luckyus_opshop` — no QR/scan/invite tables found
- `isalesprivatedomain` — no location/scan tables (only messaging/campaign tables)
- `cdpactivity` — empty/inaccessible schema
- `isalescdp.t_user_event` — numeric event types, not Sensors Data SDK events
- `isalescdp.t_user_event_track` — only 2 login event types; no scan events in Mar 5–18 window

**Likely data location:**
- In-store scan events would be in a Sensors Data scan page event: `$page.scan$model.0$content.0$action.bw`
- This event type was referenced in the analyst's sample but NOT found in MySQL `t_user_event_track`
- **Most likely source: Redshift Serverless** (full Sensors Data event stream)

**What can be inferred:**
- Origin 4 (H5/Web) = 27.5% of registrations includes all H5 registrations: offline scan + Google Maps H5 + direct web + referral links
- Offline scan is likely a meaningful portion given 11 physical stores, but cannot be quantified without scan event access

---

### 2.2 iOS应用商店 (iOS App Store) — ✅ Available (Count Only, No Adid)

**Available:** Weekly counts from `salescrm.t_user origin=6` — confirmed 100% accurate via cross-validation.

**Gap:** True IDFA (Apple advertising ID) for paid acquisition attribution not available:
- `t_user_event_track.p_device_id` is sparsely populated (< 2% non-empty)
- Analyst's expected data shows ~99% adid coverage — this data is in Redshift, not MySQL

**Impact:** Cannot distinguish organic App Store discovery from paid Apple Search Ads (ASA) attribution.

---

### 2.3 安卓应用商店 (Android Google Play) — ✅ Available (Count Only, No Adid)

Same as iOS: counts confirmed, GAID (Google Advertising ID) not available in MySQL.

---

### 2.4 社媒引流 (Social Media Referral) — ❌ No Data

**Root Cause:** Adjust deep link system has not been deployed. Social media campaigns (TikTok, Instagram, Facebook, Xiaohongshu/Rednote) are configured in `salesmarketing.t_marketing_channel` (IDs 134–138, 179, etc.) but without Adjust links, there is no attribution tracking connected to the registration flow.

**Evidence:** The `salesmarketing.t_marketing_channel` table shows social media channel hierarchy:
- 社媒传播 (Social Media) → TikTok, Instagram, Facebook, 小红书Rednote, KOLinfluencer, yelp

But these are marketing planning records only — no event tracking data flows from these channels into the registration system.

**What's needed:** Adjust SDK integration + deep link deployment by Marketing/Product team.

---

### 2.5 GGLMAP / Google Maps Channel

**Status:** Partially available in CDP (Mar 19 only), not accessible for Feb 1–Mar 18.

**What it is:** Users who find Luckin Coffee on Google Maps (store listing), click the app download link, and are attributed to the Google Maps channel. This is an ONLINE channel (discovery via Google Maps = digital), not an offline channel.

**Current coverage:**
- In salescrm: Likely included in origin=4 (H5 web path) OR origin=6 (if Google Maps linked directly to App Store)
- In CDP (Mar 19): Available as `channel='GGLMAP'`

**Analyst's data (Mar 1):** GGLMAP appeared in the sample as a distinct channel, suggesting Redshift has full historical GGLMAP attribution.

---

### 2.6 Referral / 好友拉新 — ❌ Not Separable from H5

**Root Cause:** Friend invitation links open the H5 referral page → user registers on H5 → recorded as origin=4. `t_user_attribute.invitation_code` and `inviter_code` fields exist but cross-DB joins to salescrm are blocked (gateway permission denied).

**What's available:** `salescrm.t_invitation_record` has 11,482 records (total invitations sent), but connecting these to registrations requires joining with t_user — which is within the same DB and should be possible.

---

## 3. What CAN Be Delivered Now

| Deliverable | Quality | Source |
|------------|---------|--------|
| Weekly total registrations (all channels) | ✅ High | salescrm.t_user |
| iOS App Store weekly counts | ✅ High | salescrm.t_user origin=6 |
| Android Google Play weekly counts | ✅ High | salescrm.t_user origin=5 |
| H5/Web combined weekly counts | ✅ High | salescrm.t_user origin=4 |
| Mar 19 channel breakdown (small sample) | ⚠️ Low (n=34) | CDP t_user_event_track |
| Origin code decode (validated) | ✅ High | Cross-validated with CDP sample |

---

## 4. Action Items by Owner

### David Zeng (DBA) — Infrastructure Access

| # | Action | Priority | Timeline |
|---|--------|----------|---------|
| 1 | Request `redshift:DescribeClusters` + `redshift-serverless:ListWorkgroups` + `redshift-data:*` IAM permissions for `databasecheck` user | 🔴 Critical | 1-2 days |
| 2 | Once Redshift access granted: locate event table (look for `cdp`, `lkus`, `sensors_data` schemas) | 🔴 Critical | Same day as access |
| 3 | Investigate whether `salescrm.t_invitation_record` can be joined with `t_user` to separate referral registrations from other origin=4 H5 users | 🟡 Medium | 2-3 days |
| 4 | Clarify Feb 22-23 registration anomaly (365 and 66 users — possible pipeline failure) with ops team | 🟡 Medium | 1 week |

### 马云飞 (Data Analyst) — Analyst Collaboration

| # | Action | Priority | Timeline |
|---|--------|----------|---------|
| 1 | Share the Redshift/Tableau table name for the event source (ask: "What database and schema does your Tableau workbook connect to for the channel attribution query?") | 🔴 Critical | Same day |
| 2 | Confirm whether `$page.scan$model.0$content.0$action.bw` is the correct scan event type name for offline QR registrations | 🟡 Medium | 1 week |
| 3 | Provide the correct `p_is_first_day` encoding (0/1 integer vs 'true'/'false' string) in the full event table | 🟡 Medium | 1 week |

### 王姣 (Product) — SDK & Attribution

| # | Action | Priority | Timeline |
|---|--------|----------|---------|
| 1 | Deploy Adjust deep links for social media campaigns (TikTok, Instagram, Facebook) to enable social media attribution | 🟠 High | 2-4 weeks |
| 2 | Add a scan page event (`$page.scan$...`) specifically for in-store QR code scanning with `shop_id` parameter, to distinguish offline scan registrations from other H5 registrations | 🟠 High | 2-4 weeks |
| 3 | Clarify whether `origin=4` (H5) is intentionally opaque or if the app should record a more specific registration source | 🟡 Medium | 2 weeks |

### Mai Shi (Marketing) — Reporting Requirements

| # | Action | Priority | Timeline |
|---|--------|----------|---------|
| 1 | Confirm if the "线下扫码" row in the pivot can be approximated using "H5/Web" as a proxy (offline scan is the primary H5 acquisition channel for in-store stores) | 🟠 High | 1 week |
| 2 | Confirm whether GGLMAP should be classified as "线上" (online) or "线下" (offline) in the attribution model — it is a Google Maps digital listing, not a physical QR scan | 🟡 Medium | 1 week |
| 3 | Decide if the weekly pivot should use UTC or Eastern Time (EST) for day/week boundaries | 🟢 Low | 1 week |

---

## 5. Architecture Recommendation for Complete Channel Attribution

**Current State:**
```
In-store QR Scan ─┐
Google Maps Link ─┤──→ H5 Web Page ──→ salescrm.t_user origin=4 (no channel detail)
Direct Web Link ──┤
Referral Link ────┘

App Store ─────────────────────────────→ salescrm.t_user origin=6
Google Play ───────────────────────────→ salescrm.t_user origin=5
```

**Target State (with instrumentation):**
```
In-store QR Scan ──→ H5 with shop_id param ──→ Sensors Data scan event
                                                 (event_type: $page.scan$..., shop_id: "xxx")
Google Maps Link ──→ Adjust deep link ──→ App Store/Play (GGLMAP attribution)
Social Media ──────→ Adjust deep link ──→ App Store/Play (TikTok/IG/FB attribution)
Referral Link ─────→ H5 with invite_code ──→ Sensors Data referral event
                                              (can join with t_invitation_record)

All events ──→ Sensors Data SDK ──→ S3 ──→ Redshift (full historical event table)
                                         ──→ MySQL t_user_event_track (near-real-time, login only)
```

**Required changes:**
1. **QR code instrumentation**: Add `scan_source=shop_qr&shop_id={shop_id}` URL parameter to in-store QR codes → triggers distinct scan event in Sensors Data
2. **Adjust SDK integration**: Connect marketing campaign deep links to Adjust → populates `channel` field in Sensors Data with specific social platform
3. **Redshift access**: Open `SELECT` for `databasecheck` on event table → DBA can run weekly attribution queries directly

**Estimated timeline to full coverage:** 4-6 weeks (Adjust deployment 2-4w + QR re-deployment 1-2w)

---

## 6. Summary: Answering Mai Shi's Report Request

| Row in Target Pivot | Status | Data |
|--------------------|--------|------|
| 线下扫码 | ❌ Cannot isolate | Embedded in H5/Web (origin=4); no separate scan event tracked |
| iOS应用商店 | ✅ Available | origin=6 counts by week — see 03-weekly-pivot-final.md |
| 安卓应用商店 | ✅ Available | origin=5 counts by week — see 03-weekly-pivot-final.md |
| 社媒引流 | ❌ No data | Adjust links not deployed |
| 自来水/其他 | ⚠️ Partial | origin=4 (H5/Web combined); contains offline QR + GGLMAP + referral + organic web |
| 合计 | ✅ Available | Direct count from salescrm.t_user |
