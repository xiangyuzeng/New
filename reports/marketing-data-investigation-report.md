# Marketing Data Requirements — Feasibility Investigation Report

**Report Date:** 2026-03-19
**Prepared by:** DBA/Infrastructure Team (David Zeng)
**Scope:** Full investigation of 13 dashboard metric tables requested by Maishi's US Marketing team
**Data Sources:** 9 MySQL databases queried across salesorder, salescrm, salesmarketing, salespayment, scmcommodity, isalescdp, isalesdatamarketing, isalesmembermarketing, upush

---

## Executive Summary

| Status | Count | Dashboard Tables |
|--------|-------|-----------------|
| ✅ Fully Available | 7 | Orders, Revenue, Users, Coupons, SPU, Stores, Repeat Purchase |
| ⚠️ Partial — Gaps | 4 | Channel Attribution, Push Performance, User Segments, MAU |
| ❌ Not in MySQL | 1 | App Traffic (action.bw / action.ck) — lives in Redshift |
| 🔧 Needs Build | 1 | Marketing Campaign ROI — needs join across 3 tables |

**Bottom line:** Core transactional metrics (orders, revenue, coupons, products, users) are fully available in MySQL with clean, production-grade schemas. The main gap is behavioral/traffic data (clickstream, app opens), which resides in Redshift Serverless. Push notification send-side data exists but open/click tracking is only partially available.

---

## Part 1: Schema Map — Confirmed Tables & Row Counts

### Database Naming (Actual vs. Expected)

| Service Name | Server | Actual Schema Name |
|-------------|--------|--------------------|
| salesorder | aws-luckyus-salesorder-rw | `luckyus_sales_order` |
| salescrm | aws-luckyus-salescrm-rw | `luckyus_sales_crm` |
| salesmarketing | aws-luckyus-salesmarketing-rw | `luckyus_sales_marketing` |
| salespayment | aws-luckyus-salespayment-rw | `luckyus_sales_payment` |
| scmcommodity | aws-luckyus-scmcommodity-rw | `luckyus_scm_commodity` |
| isalescdp | aws-luckyus-isalescdp-rw | `luckyus_isales_cdp` |
| isalesdatamarketing | aws-luckyus-isalesdatamarketing-rw | `luckyus_isalesdatamarketing` |
| isalesmembermarketing | aws-luckyus-isalesmembermarketing-rw | `luckyus_isalesmembermarketing` |
| upush | aws-luckyus-upush-rw | Multiple schemas (see §1.8) |

### 1.1 Orders Database (`luckyus_sales_order`)

| Table | Rows (est.) | Size | Purpose |
|-------|-------------|------|---------|
| `t_order_oper_history` | 2,974,860 | 488 MB | Order state change log |
| `t_finance_history` | 1,154,762 | 450 MB | Financial ledger |
| **`t_order_item`** | **737,076** | **1,293 MB** | **Line items (SPU-level)** |
| `t_order_promotion_detail` | 715,139 | 137 MB | Promotion applied per order |
| **`t_order`** | **626,084** | **201 MB** | **Main order header** |
| `t_order_pay` | 593,553 | 68 MB | Payment records |
| `t_order_member` | 581,245 | 116 MB | Member order snapshot |
| **`t_order_amount`** | **577,508** | **296 MB** | **Detailed revenue breakdown** |
| `t_order_store_fact` | 82,554 | 19 MB | Pre-aggregated store facts |
| `t_order_stat_fact` | 24,828 | 5 MB | Daily order statistics |
| `t_order_item_stat_fact` | 24,674 | 5 MB | Daily item statistics |
| `t_finance_refund` | 15,727 | 7 MB | Refund records |

**Actual data range (LKUS tenant):** 2025-05-09 to 2026-03-19
**Total completed orders:** 551,810 (status=90) + 7,477 delivery + 3,727 virtual
**Distinct users who ordered:** 171,628
**Distinct shops in orders:** 15

### 1.2 CRM / Users Database (`luckyus_sales_crm`)

| Table | Rows (est.) | Purpose |
|-------|-------------|---------|
| `t_user_history` | 585,115 | User change log |
| `t_user_config` | 342,889 | User preferences |
| **`t_user`** | **300,690** | **User registration master** |
| `t_user_attribute` | 272,539 | Extended user attributes |
| `t_user_grant` | 220,752 | Permission/benefit grants |
| **`t_user_profile`** | **209,593** | **Pre-computed user metrics** |
| `t_device_manager` | 175,780 | Device registry |
| `t_invitation_record` | 11,482 | Referral/invite tracking |

### 1.3 Marketing / Coupons Database (`luckyus_sales_marketing`)

| Table | Rows (est.) | Purpose |
|-------|-------------|---------|
| **`t_coupon_record_expired`** | **35,273,943** | **Historical redeemed/expired coupons** |
| `t_user_group_label` | 5,208,985 | User segment tags |
| **`t_coupon_record`** | **3,361,590** | **Active coupon wallet** |
| `t_market_activity_partake` | 619,074 | Campaign participation log |
| `t_coupon_template` | 1,803 | Coupon type definitions |
| `t_contact_user_group` | 419 | User group definitions |
| `t_coupon_proposal` | 248 | Coupon scheme master |

### 1.4 Payment Database (`luckyus_sales_payment`)

| Table | Rows (est.) | Purpose |
|-------|-------------|---------|
| `t_channel_fee` | 591,743 | Payment processor fees |
| **`t_trade`** | **575,919** | **Payment transactions** |
| `t_user_channel` | 182,037 | User payment method |
| `t_refund` | 14,792 | Refund transactions |

### 1.5 Product Catalog (`luckyus_scm_commodity`)

| Table | Rows (est.) | Purpose |
|-------|-------------|---------|
| `t_formula_spu` | 32,834 | SPU recipe formulas |
| `t_commodity_category` | 196 | Product category hierarchy |
| **`t_commodity_base_info`** | **146** | **SPU master (US products)** |
| `t_commodity_sale_info` | 143 | Sale price configuration |
| **`t_shop_info`** | **534** | **Store dimension** |

### 1.6 CDP (`luckyus_isales_cdp`)

| Table | Rows (est.) | Purpose |
|-------|-------------|---------|
| `t_realtime_user_group_log` | 3,933,321 | Real-time segment assignment |
| `t_user_state` | 1,256,325 | User lifecycle state |
| `t_user_event_track` | 258,242 | Behavioral events (go-live 2026-03-19) |
| `t_user_event` | 84,124 | User events (alt format) |

### 1.7 Data Marketing (`luckyus_isalesdatamarketing`)

| Table | Rows (est.) | Purpose |
|-------|-------------|---------|
| `_t_user_traffic_distribution_new` | 6,734,736 | A/B test traffic buckets |
| `t_user_hit_experiment_record` | 6,528,029 | Experiment assignment records |
| `t_experiment` | 85 | Experiment definitions |

> **Note:** This database is an **A/B testing framework**, not a user segmentation tool for marketing reporting. It tracks experiment group assignments.

### 1.8 Member Marketing (`luckyus_isalesmembermarketing`)

> **All 24 tables are EMPTY.** Member marketing (levels, medals, points, benefits) has not been deployed in the US market. No data available.

### 1.9 Push/Messaging (`upush` — multiple schemas)

| Schema | Key Tables | Purpose |
|--------|-----------|---------|
| `luckyus_iupushsms` | `sms_sent_bulk_lucky` (1.42M), `sms_bulk_deliver_record_lucky` (2.98M), `sms_receipt_*` (32 shards, ~4M total) | SMS send & delivery |
| `luckyus_iupushapp` | `msg_center_*` (32 shards, ~9M total), `t_msg_statistics` (1,034) | In-app message inbox |
| `luckyus_iupushaid` | `t_shorturl_access_record_*` (~155K), `t_short_url_map_*` (~52K) | Short URL click tracking |
| `luckyus_iupushusercenter` | `t_lucky_member` (276,175) | Push service user registry |

---

## Part 2: Business Logic Evidence — Open Questions Resolved

### 2A: Revenue Field Mapping — 应收 / 实收 / 实付

**Confirmed from actual data sample (10 orders):**

| Concept | Column | Table | Definition |
|---------|--------|-------|-----------|
| **应收** (Receivable/List Price) | `total_money` / `order_origin_money` | `t_order` / `t_order_amount` | Full catalog price before ANY discount |
| **实收** (Actual Revenue) | `order_payable_money` | `t_order_amount` | After all discounts, what should be collected |
| **实付** (Customer Paid) | `pay_money` / `order_actually_money` | `t_order` / `t_order_amount` | Amount customer actually paid (card charged) |
| **订单收入** (Net Income) | `order_income` | `t_order_amount` | Net revenue recorded (= 实收 in most cases) |

**DBA Recommendation:** Use `order_income` for financial reporting (净收入). Use `total_money` for GMV/应收. For marketing dashboards showing "how much discount was given": `total_money - pay_money`.

**Evidence:** Sample order: `total_money=6.45`, `payable_money=0.01`, `pay_money=0.01`
→ New user with $1.99 coupon, leaving $0.01 due (system minimum charge). Discount = $6.44.
Another order: `total_money=40.25`, `payable_money=8.05`, `pay_money=8.05` → Multi-item order, bundle pricing applied.

### 2B: Daypart Histogram — Past 30 Days (Eastern Time)

**Data evidence (status=90, completed orders, last 30 days):**

| Hour (ET) | Orders | % of Day | Daypart |
|-----------|--------|----------|---------|
| 6am | 1,874 | 2.1% | Pre-AM |
| 7am | 7,379 | 8.3% | **AM Rush** |
| **8am** | **11,575** | **13.0%** | **PEAK — AM Rush** |
| 9am | 10,539 | 11.8% | AM Rush |
| 10am | 8,522 | 9.6% | AM Rush |
| 11am | 7,852 | 8.8% | Lunch |
| 12pm | 8,859 | 9.9% | **Lunch Peak** |
| 1pm | 8,867 | 9.9% | **Lunch Peak** |
| 2pm | 7,346 | 8.3% | Afternoon |
| 3pm | 6,040 | 6.8% | Afternoon |
| 4pm | 4,488 | 5.0% | PM |
| 5pm | 3,324 | 3.7% | PM |
| 6pm | 1,967 | 2.2% | Evening |
| 7pm+ | 1,023 | 1.1% | Late |

**DBA Recommendation:** Natural breakpoints support 4 dayparts:
- **AM (6–10am):** 39.8% of orders — morning commuter peak
- **Lunch (11am–2pm):** 36.9% of orders — lunch break peak
- **PM (3–6pm):** 17.5% of orders — afternoon slowdown
- **Evening (7pm+):** 1.1% of orders — minimal

No orders before 6am ET or after 8pm ET (stores close ~7pm).

### 2C: Order Status Enum

| Status Code | Count | Meaning |
|-------------|-------|---------|
| 0 | 23,569 | 未完成/初始化 (pending/failed — exclude from revenue) |
| 10 | 2 | 已新建 (rare intermediate state) |
| 20 | 26 | 已支付 (paid, not yet completed — very few) |
| **90** | **562,014** | **已完成 (completed — use this for all revenue metrics)** |

> **Critical:** Always filter `WHERE status = 90` for revenue and sales metrics. Status 0 are abandoned/failed orders and must be excluded.

### 2D: Order Type / Virtual Order Filter

| order_type | order_category | Count | Meaning |
|------------|----------------|-------|---------|
| 1 | 1 | 551,810 | 现制商品 自取 (fresh-made, pickup) |
| 2 | 1 | 7,477 | 现制商品 配送 (fresh-made, delivery) |
| 3 | 2 | 3,727 | 虚拟订单/礼品券 (virtual/gift) |

**虚拟订单 filter:** `WHERE order_category = 2` (excludes gift/virtual orders from cup count metrics).
**现制饮品 (fresh-made beverages):** `spu_mode = 0` in `t_order_item` (vs `spu_mode = 1` for pre-packaged food).

### 2E: New User Coupon Offers — $0.99 and $1.99

**Confirmed from `t_coupon_record`:**

| Denomination | Discount Type | Count Issued | Count Used | Use Rate | Context |
|-------------|---------------|-------------|------------|----------|---------|
| $1.99 | 3=商品兑换券 | 227,530 | 166,027 | 73% | **Primary new user offer** — free product up to $1.99 |
| $1.99 | 2=代金券 | 38,225 | 38,225 | 100% | $1.99 cash discount (fully used campaigns) |
| $0.99 | 3=商品兑换券 | 3,508 | 3,508 | 100% | $0.99 product offer (limited campaign) |
| $2.99 | 3=商品兑换券 | 166,596 | 15,795 | 9% | Newer offer, lower redemption |

**Key insight:** The $1.99 商品兑换券 is the primary acquisition tool (227K+ issued). Activity names confirm: "新客券包" (new user coupon package), "新客补券循环" (new user coupon replenishment loop), and win-back campaigns ("沉默召回").

**`member_status` field** in `t_coupon_record` confirms new-user attribution:
- `1` = 新注册 (newly registered) — the new user coupon
- `2` = 有效 (existing active user)
- `3` = 无效 (invalid user)

### 2F: Top SPU Rankings — Cups vs Orders (Past 7 Days)

| Rank | SPU Name | Category | spu_mode | Cups | Orders | Cups/Order |
|------|----------|----------|----------|------|--------|-----------|
| 1 | Iced Coconut Latte | Fresh ground coffee | 0=fresh | 2,470 | 2,289 | 1.08 |
| 2 | Iced Kyoto Matcha Latte | Matcha | 0=fresh | 2,099 | 1,979 | 1.06 |
| 3 | Latte | Classic drinks | 0=fresh | 1,992 | 1,898 | 1.05 |
| 4 | Sausage Egg & Cheese Croissant | Food | **1=packaged** | 1,583 | 1,516 | 1.04 |
| 5 | Iced Latte | Classic drinks | 0=fresh | 1,553 | 1,490 | 1.04 |
| 6 | Drip Coffee | Classic drinks | 0=fresh | 1,396 | 1,312 | 1.06 |
| 7 | Cold Brew | Cold Brew | 0=fresh | 1,148 | 1,082 | 1.06 |
| 8 | Coconut Latte | Fresh ground coffee | 0=fresh | 940 | 865 | 1.09 |

**Finding:** Rankings by cups and by orders are nearly identical (Cups/Order ≈ 1.05–1.09). Most orders include exactly 1 drink. Cup-count ranking = order-count ranking for this dataset. The only non-drink in top 10 is the Croissant (packaged food, `spu_mode=1`).

**現制飲品 filter:** `WHERE spu_mode = 0` — all fresh-made items (drinks + any fresh food).

### 2G: User Registration & First Order Data

**`t_user` columns confirmed:**
- `create_time` = registration timestamp ✅
- `origin` = registration channel (6=App Store iOS, 4=Google Play Android, 5=H5/WeChat)
- `tenant` = always filter `WHERE tenant = 'LKUS'`

**`t_user_profile` — pre-computed metrics (gold mine):**

| Column | Content |
|--------|---------|
| `first_login_time` | First app login timestamp |
| `first_order_time` | First order placement timestamp |
| `first_pay_time` | First successful payment timestamp |
| `last_order_time` | Most recent order timestamp |
| `finish_order` | Total completed order count |
| `total_consumption` | Cumulative spend (decimal) |
| `is_send_coupon` | Whether new user coupon was issued (0/1) |
| `not_available_new_user_coupon` | New user coupon eligibility flag |
| `student_verified` | Student verification status |

> This table enables cohort analysis, retention analysis, and first-order conversion tracking **without expensive self-joins on the orders table**.

### 2H: Store Dimension

**15 real retail stores active in order data** (status=1 in `t_shop_info`, internal=0):

| Store No | Name | Opening Date |
|----------|------|-------------|
| US00001 | 8th & Broadway | 2025-06-30 |
| US00002 | 28th & 6th | 2025-06-30 |
| US00003 | 100 Maiden Ln | 2025-09-09 |
| US00004 | 37th & Broadway | 2025-11-20 |
| US00005 | 54th & 8th | 2025-08-24 |
| US00006 | 102 Fulton | 2025-08-28 |
| US00007 | 108th & Broadway | (no date) |
| US00008 | 33rd & 10th | 2025-12-01 |
| US00009 | 48th & 3rd | (no date) |
| US00010 | 154 Bleecker | (no date) |
| US00011 | 180 Varick | (no date) |
| US00012 | 16th & 6th | (no date) |
| US00013 | Grand Central Terminal | (no date) |
| US00014 | 25 Park Row | (no date) |
| US00024 | 15th & 3rd | 2025-12-14 |

> Internal test kitchens: US00000 (NJ Test Kitchen), US99999, US99998 — filter `WHERE internal = 0` or `WHERE shop_no NOT IN ('US00000','US99999','US99998')`.

---

## Part 3: Dashboard Metric Feasibility Matrix

### 表1: Daily Order Volume & Revenue (日订单量/营收)

| Metric | Source Table | Column | Status |
|--------|-------------|--------|--------|
| Daily order count | `t_order` | `COUNT(*)` WHERE `status=90, tenant='LKUS'` | ✅ |
| GMV (应收) | `t_order` | `SUM(total_money)` | ✅ |
| Net revenue (实收) | `t_order_amount` | `SUM(order_actually_money)` | ✅ |
| Order income | `t_order_amount` | `SUM(order_income)` | ✅ |
| Cup count | `t_order_item` | `SUM(sku_num)` WHERE `gift_flag=0` | ✅ |
| AOV (average order value) | Derived | `SUM(pay_money)/COUNT(*)` | ✅ |
| Pickup vs delivery split | `t_order` | `GROUP BY order_type` | ✅ |
| Exclude virtual orders | `t_order` | `WHERE order_category=1` | ✅ |

**Verdict: ✅ Fully available. Filter template:**
```sql
SELECT DATE(CONVERT_TZ(pay_time,'+00:00','-05:00')) as local_date,
       shop_name, COUNT(*) as orders, SUM(pay_money) as revenue
FROM luckyus_sales_order.t_order
WHERE tenant='LKUS' AND status=90 AND order_category=1
GROUP BY local_date, shop_id, shop_name;
```

---

### 表2: User Registration Trends (用户注册)

| Metric | Source Table | Column | Status |
|--------|-------------|--------|--------|
| Daily new registrations | `t_user` | `COUNT(*) GROUP BY DATE(create_time)` | ✅ |
| Registration channel | `t_user` | `origin` (6=iOS, 4=Android, 5=H5) | ✅ |
| Total registered users | `t_user` | `COUNT(*)` WHERE `status=1` | ✅ |
| New user coupon issued | `t_user_profile` | `is_send_coupon` | ✅ |

**Verdict: ✅ Fully available.**
**Gap:** Channel labels need enum mapping (6→App Store, 4→Google Play, 5→H5). Confirm mapping with app dev team.

---

### 表3: Coupon Redemption Analysis (券核销)

| Metric | Source Table | Column | Status |
|--------|-------------|--------|--------|
| Coupons issued by type | `t_coupon_record` | `COUNT(*) GROUP BY coupon_type, coupon_denomination` | ✅ |
| Coupons used | `t_coupon_record` | `WHERE use_status=1` | ✅ |
| Redemption rate | Derived | `used/issued` | ✅ |
| New user coupons | `t_coupon_record` | `WHERE member_status=1` | ✅ |
| Coupon face value | `t_coupon_record` | `coupon_denomination` | ✅ |
| Campaign attribution | `t_coupon_record` | `activity_name, proposal_name` | ✅ |
| Coupon discount amount | `t_order_amount` | `commodity_coupon_deduct_money` | ✅ |
| Order linked to coupon | `t_coupon_record` | `order_no` → join to `t_order` | ✅ |

**Verdict: ✅ Fully available.**
**Note:** Active coupons in `t_coupon_record` (3.36M); expired/used coupons in `t_coupon_record_expired` (35.27M). For historical analysis, query both tables with UNION.

---

### 表4: SPU Sales Volume (商品销售)

| Metric | Source Table | Column | Status |
|--------|-------------|--------|--------|
| Cups sold by SPU | `t_order_item` | `SUM(sku_num)` GROUP BY `spu_code, spu_name` | ✅ |
| Revenue by SPU | `t_order_item` | `SUM(pay_money)` | ✅ |
| 现制饮品 only | `t_order_item` | `WHERE spu_mode=0` | ✅ |
| 小食 (food) only | `t_order_item` | `WHERE spu_mode=1` | ✅ |
| Category breakdown | `t_order_item` | `one_category_name, two_category_name` | ✅ |
| Exclude gifts | `t_order_item` | `WHERE gift_flag=0` | ✅ |

**Verdict: ✅ Fully available.**
**Note:** `spu_mode=0` = fresh-made (现制), `spu_mode=1` = pre-packaged (外购). Category is denormalized in the order item — no join to catalog needed for reporting.

---

### 表5: Daypart Analysis (时段分析)

| Metric | Source Table | Status |
|--------|-------------|--------|
| Orders by hour (ET) | `t_order` + `CONVERT_TZ(pay_time,'+00:00','-05:00')` | ✅ |
| Revenue by daypart | Derived from above | ✅ |
| Store-level daypart | Add `GROUP BY shop_id, shop_name` | ✅ |

**Daypart definition (DBA recommendation based on data):**
- AM Rush: 6:00–10:59 ET (peak at 8am, 39.8% of orders)
- Lunch: 11:00–14:59 ET (peak at 12–1pm, 36.9%)
- PM: 15:00–18:59 ET (declining, 17.5%)
- Evening: 19:00+ ET (<2%)

**Verdict: ✅ Fully available.**
**Timezone note:** All timestamps stored in UTC. Always convert: `CONVERT_TZ(pay_time, '+00:00', '-05:00')` for ET (or `-04:00` during EDT summer).

---

### 表6: Repeat Purchase / Retention (复购分析)

| Metric | Source Table | Column | Status |
|--------|-------------|--------|--------|
| User order count | `t_user_profile` | `finish_order` | ✅ |
| First order date | `t_user_profile` | `first_pay_time` | ✅ |
| Last order date | `t_user_profile` | `last_order_time` | ✅ |
| Days since last order | Derived | `DATEDIFF(NOW(), last_order_time)` | ✅ |
| Cohort repeat rate | `t_order` + `t_user_profile` | Join on `user_no` | ✅ |
| 7-day retention | Derived | Orders within 7 days of first order | ✅ |
| 30-day retention | Derived | Orders within 30 days of first order | ✅ |

**Verdict: ✅ Fully available.** `t_user_profile` is a pre-computed summary table that makes cohort analysis highly efficient.

**Sample cohort query:**
```sql
SELECT DATE(first_pay_time) as cohort_date,
       COUNT(*) as cohort_size,
       SUM(CASE WHEN finish_order >= 2 THEN 1 ELSE 0 END) as repeat_buyers,
       AVG(finish_order) as avg_orders
FROM luckyus_sales_crm.t_user_profile
WHERE tenant='LKUS' AND first_pay_time IS NOT NULL
GROUP BY DATE(first_pay_time)
ORDER BY cohort_date;
```

---

### 表7: MAU / Active Users (月活跃用户)

| Metric | Source Table | Status |
|--------|-------------|--------|
| Monthly ordering users (order-based MAU) | `t_order` GROUP BY month, `user_no` | ✅ |
| Monthly registered users (new) | `t_user` GROUP BY month, `create_time` | ✅ |
| App session MAU | `t_user_event_track` (CDP) | ⚠️ Only from 2026-03-19 |

**Verdict: ⚠️ Partial.**
- **Order-based MAU** (users who placed ≥1 order per month) is **fully available** in `t_order`.
- **App session MAU** (users who opened app regardless of ordering) requires CDP event data, only available from 2026-03-19. For historical MAU, use order-based definition.
- **DBA Recommendation:** Define MAU = distinct `user_no` with `status=90` order in the calendar month. This is the most reliable metric available. Document the definition clearly.

---

### 表8: Product Category Mix (商品品类)

| Metric | Source Table | Status |
|--------|-------------|--------|
| Drinks vs food split | `t_order_item.spu_mode` (0=drink, 1=food) | ✅ |
| Category hierarchy (L1/L2) | `t_order_item.one_category_name, two_category_name` | ✅ |
| Active SKU count | `t_commodity_base_info` (146 rows) | ✅ |
| SPU category master | `t_commodity_category` (196 rows, using `mid`, `name`, `parent_mid`, `level`) | ✅ |

**Product hierarchy confirmed (from order data):**
- **Drink > Fresh ground coffee** (Coconut Latte, Velvet Latte, Tiramisu Latte, etc.)
- **Drink > Matcha** (Kyoto Matcha Latte family)
- **Drink > Classic drinks** (Latte, Iced Latte, Americano, Drip Coffee)
- **Drink > Cold Brew**
- **Food** (Sausage Egg & Cheese Croissant — packaged, spu_mode=1)

**Verdict: ✅ Fully available.** Category is denormalized in `t_order_item`, no catalog join required.

---

### 表9: New User Conversion Funnel (新用户转化)

| Metric | Source Table | Status |
|--------|-------------|--------|
| Registration → First order gap | `t_user_profile.create_time` vs `first_pay_time` | ✅ |
| New user coupon issued | `t_user_profile.is_send_coupon` | ✅ |
| New user coupon redemption | `t_coupon_record WHERE member_status=1 AND use_status=1` | ✅ |
| Registration → coupon use rate | JOIN `t_user` + `t_coupon_record` | ✅ |
| Day-0 conversion rate | `DATEDIFF(first_pay_time, u.create_time) = 0` | ✅ |

**Verdict: ✅ Fully available.**
**Key stat:** 265,755 new user coupons issued ($1.99); 204,252 redeemed (76.8% conversion).

---

### 表10: Channel Attribution (渠道归因)

| Metric | Source Table | Status |
|--------|-------------|--------|
| Registration by channel | `t_user.origin` | ⚠️ Enum needs mapping |
| Orders by acquisition channel | JOIN `t_user` + `t_order` on `user_no` | ✅ |
| App install attribution | CDP event data / Adjust SDK | ❌ Not in MySQL |
| Cost per acquisition (CPA) | Ad spend data | ❌ Not in any DB |
| ROAS | Ad spend vs revenue | ❌ External (Meta/Google Ads) |

**Verdict: ⚠️ Partial.**
- **Available:** Registration counts by channel (App Store / Play Store / H5), orders attributed back to acquisition channel via user join.
- **Gap:** App install count (pre-registration), ad spend, impression data — all live in Meta Ads Manager / Google Ads, not in MySQL or Redshift.
- **Channel enum mapping** (confirm with app dev team): origin 6=iOS App Store, 4=Google Play, 5=H5/WeChat, others TBD.

---

### 表11: Marketing Campaign ROI (营销活动效果)

| Metric | Source Table | Status |
|--------|-------------|--------|
| Campaign coupon issued | `t_coupon_record.activity_name` + COUNT | ✅ |
| Campaign coupon redeemed | `t_coupon_record WHERE use_status=1` | ✅ |
| Revenue from campaign orders | JOIN `t_coupon_record` + `t_order` on `order_no` | 🔧 |
| Discount cost of campaign | `SUM(coupon_denomination)` WHERE `use_status=1` | ✅ |
| Net revenue after discount | `order_income - coupon_denomination` | 🔧 |
| Incremental orders (lift) | Requires A/B test data | ⚠️ |

**Verdict: 🔧 Needs build (ETL join across 3 tables).**
The raw data is all present, but campaign ROI requires a 3-way join: `t_coupon_record → t_order → t_order_amount`. Currently no pre-aggregated campaign ROI table exists. Recommend building a daily pre-aggregation job.

**Query skeleton:**
```sql
SELECT cr.activity_name,
       COUNT(DISTINCT cr.coupon_no) as issued,
       SUM(CASE WHEN cr.use_status=1 THEN 1 ELSE 0 END) as redeemed,
       SUM(cr.coupon_denomination * CASE WHEN cr.use_status=1 THEN 1 ELSE 0 END) as discount_cost,
       SUM(oa.order_income) as order_revenue
FROM luckyus_sales_marketing.t_coupon_record cr
LEFT JOIN luckyus_sales_order.t_order o ON cr.order_no = o.id
LEFT JOIN luckyus_sales_order.t_order_amount oa ON o.id = oa.order_id
WHERE cr.tenant='LKUS'
GROUP BY cr.activity_name;
```
> Note: Cross-database joins may be slow. Pre-aggregate to a reporting schema (Redshift recommended).

---

### 表12: Push Notification Performance (推送效果)

| Metric | Source Table | Status |
|--------|-------------|--------|
| SMS sent | `luckyus_iupushsms.sms_sent_bulk_lucky` | ✅ |
| SMS delivery rate | `sms_bulk_deliver_record_lucky` / `sms_sent_bulk_lucky` | ✅ |
| In-app messages sent | `luckyus_iupushapp.msg_center_*` (32 shards) | ✅ |
| In-app message status | `msg_center_*.status` field | ⚠️ Status enum unknown |
| Push campaign statistics | `t_msg_statistics` (1,034 rows) | ⚠️ Needs inspection |
| Short URL clicks (CTA) | `luckyus_iupushaid.t_shorturl_access_record_*` (~155K) | ✅ |
| Push open rate (app push) | CDP event `push_click_ck` | ⚠️ CDP only from 2026-03-19 |
| Email performance | `luckyus_iupushemail` | 🔧 Not inspected |

**Verdict: ⚠️ Partial.**
- **SMS send + delivery tracking:** Fully available (~1.4M sent, ~4M delivery receipts showing per-message delivery status).
- **In-app messages:** 9M+ messages across 32 shards. Status field needs enum inspection.
- **Short URL clicks:** ~155K click events — proxy for push CTA engagement.
- **App push open rate:** Only available via CDP event (`push_click_ck`) since 2026-03-19. No historical push open data.
- **Push notification to Apple APNs / Firebase FCM:** Delivery confirmation not stored in MySQL (handled by 3rd-party push provider).

---

### 表13: Store Performance (门店分析)

| Metric | Source Table | Status |
|--------|-------------|--------|
| Orders per store per day | `t_order` GROUP BY `shop_id, shop_name, DATE(pay_time)` | ✅ |
| Revenue per store | `t_order` SUM `pay_money` GROUP BY `shop_id` | ✅ |
| Store opening date | `t_shop_info.set_up_time` | ⚠️ Null for some stores |
| Store count (active) | `t_shop_info WHERE status=1 AND internal=0` | ✅ (15 retail stores) |
| Cups per store | JOIN `t_order_item` on `order_id` | ✅ |
| Store location | `t_shop_info.address, locality_name` | ⚠️ locality_name null |
| Target: 1,200 orders/day | Derived KPI | ✅ (computable) |

**Verdict: ✅ Mostly available.**
**Gap:** `t_shop_info.locality_name` and `administrative_area_name` are NULL for all stores. City/borough data must be added manually or enriched from the store address string. Opening dates are NULL for 8 of 15 stores in `t_shop_info` (but those stores do have orders — dates may be in a different system).

**Pre-aggregated alternative:** `t_order_store_fact` (82K rows) and `t_order_stat_fact` (24K rows) appear to be pre-aggregated store-day fact tables — inspect these first before building new aggregations.

---

## Part 4: Missing Data & External Dependencies

| Required Metric | Availability | Location | Action Needed |
|----------------|-------------|----------|--------------|
| App installs | ❌ Not in DB | Apple App Store Connect / Google Play Console | Manual export or API integration |
| App session MAU (pre-March) | ❌ Not in DB | Redshift (Sensors Data SDK events) | Redshift access (see prior investigation) |
| Ad spend (Meta, Google, TikTok) | ❌ Not in DB | Ad platform dashboards | Marketing API integration or manual export |
| ROAS / CPA | ❌ Not in DB | Derived from ad spend | External |
| App store reviews/ratings | ❌ Not in DB | App Store / Play Store | Manual |
| Push APNs/FCM delivery status | ❌ Not in DB | Push provider (e.g., Braze/OneSignal) | Check push vendor |
| Social media engagement | ❌ Not in DB | Instagram/TikTok API | External |
| DMP audience segments | ⚠️ Partial | `luckyus_isalesdatamarketing` (A/B test only) | CDP segment data growing since 2026-03-19 |
| Web traffic (SEO, referral) | ❌ Not in DB | Google Analytics | External |

---

## Part 5: Recommended Architecture for Dashboard Build

### Tier 1: Direct MySQL Query (Feasible Today)

These dashboards can be built directly against MySQL with minimal engineering:

1. **Daily/Weekly/Monthly Orders & Revenue** → `t_order` + `t_order_amount`
2. **User Registration Trend** → `t_user` (300K rows, fast)
3. **Coupon Redemption Report** → `t_coupon_record` (3.36M rows — needs index on `tenant + use_time`)
4. **SPU Sales Ranking** → `t_order_item` (737K rows — needs index on `create_time + tenant`)
5. **Store Performance** → `t_order_store_fact` or `t_order` GROUP BY `shop_id`
6. **Repeat Purchase Cohort** → `t_user_profile` (209K rows, already pre-aggregated)
7. **New User Conversion** → `t_user_profile` + `t_coupon_record`

### Tier 2: Pre-Aggregation Needed (1–2 Week Build)

These require daily ETL jobs writing to a reporting schema:

8. **Campaign ROI Table** → Daily job joining `t_coupon_record + t_order + t_order_amount`
9. **Daypart Store Heatmap** → Hourly pre-aggregation of orders by shop
10. **MAU Trend** → Monthly rollup of distinct ordering users

### Tier 3: External Data Integration Required (2–4 Weeks)

11. **Channel Attribution with Ad Spend** → Requires Meta/Google Ads API
12. **Full Push Funnel** → Requires push vendor API (sent → delivered → opened → clicked)
13. **App Traffic Dashboard** → Requires Redshift access (Sensors Data SDK events)

### Indexing Needs

| Table | Suggested Index | Reason |
|-------|----------------|--------|
| `t_order` | `(tenant, status, pay_time)` | Most common filter combination |
| `t_order_item` | `(order_id, gift_flag, create_time)` | SPU analysis queries |
| `t_coupon_record` | `(tenant, use_time, use_status)` | Daily redemption reports |
| `t_user` | `(tenant, create_time, status)` | Daily registration trend |
| `t_user_profile` | `(tenant, first_pay_time)` | Cohort analysis |

---

## Part 6: Data Quality Notes & Warnings

| Issue | Severity | Detail |
|-------|----------|--------|
| Order status 0 (pending/failed) | High | 23,569 orders with status=0. Must always filter `status=90` for completed order metrics. |
| `t_order_store_fact.locality_name` = NULL | Medium | All stores missing city/borough info. Revenue cannot be segmented by neighborhood without enrichment. |
| `t_shop_info.set_up_time` = NULL for 8 stores | Medium | Cannot compute days-since-opening for older stores. |
| `t_coupon_record` vs `t_coupon_record_expired` | Medium | Active coupons in `t_coupon_record`, historical in `t_coupon_record_expired`. Reports covering >6 months must UNION both tables. |
| CDP event data starts 2026-03-19 | High | Any behavioral metrics (MAU by app session, push open rate) only available from go-live date. No historical data. |
| `isalesmembermarketing` empty | Low | Member tiers/points system not launched for US. Do not build loyalty tier reports yet. |
| `isalesdatamarketing` is A/B test, not segments | Medium | Do not use this for marketing audience definitions. |
| Timezone: all MySQL timestamps are UTC | High | Always apply `CONVERT_TZ(..., '+00:00', '-05:00')` for ET. Reports without this will show wrong dates for orders placed before 8pm ET (= before midnight UTC). |
| Virtual orders (order_category=2, 3.7K) | Medium | Include in coupon reporting, exclude from cup-count/revenue metrics. |

---

## Appendix: Key Query Reference

### A. Daily Revenue Summary
```sql
SELECT DATE(CONVERT_TZ(pay_time,'+00:00','-05:00')) AS local_date,
       shop_name,
       COUNT(*) AS order_count,
       SUM(oi.sku_num) AS cups_sold,
       SUM(o.pay_money) AS actual_revenue,
       SUM(o.total_money) AS gross_gmv
FROM luckyus_sales_order.t_order o
JOIN luckyus_sales_order.t_order_item oi ON o.id = oi.order_id
WHERE o.tenant = 'LKUS'
  AND o.status = 90
  AND o.order_category = 1   -- exclude virtual orders
  AND oi.gift_flag = 0
  AND o.pay_time >= '2026-01-01'
GROUP BY local_date, shop_id, shop_name
ORDER BY local_date, shop_name;
```

### B. New User Funnel (Weekly)
```sql
SELECT DATE_FORMAT(u.create_time, '%Y-%u') AS week,
       COUNT(u.user_no) AS registrations,
       SUM(p.is_send_coupon) AS coupon_issued,
       COUNT(p.first_pay_time) AS first_purchasers,
       AVG(DATEDIFF(p.first_pay_time, u.create_time)) AS avg_days_to_first_order
FROM luckyus_sales_crm.t_user u
LEFT JOIN luckyus_sales_crm.t_user_profile p ON u.user_no = p.user_no AND p.tenant = 'LKUS'
WHERE u.tenant = 'LKUS' AND u.status = 1
GROUP BY week ORDER BY week;
```

### C. Top SPU by Cups (Fresh-Made Only, Last 30 Days)
```sql
SELECT oi.spu_code, oi.spu_name,
       oi.one_category_name, oi.two_category_name,
       SUM(oi.sku_num) AS cups,
       COUNT(DISTINCT oi.order_id) AS orders,
       SUM(oi.pay_money) AS revenue
FROM luckyus_sales_order.t_order_item oi
JOIN luckyus_sales_order.t_order o ON oi.order_id = o.id
WHERE o.tenant = 'LKUS'
  AND o.status = 90
  AND oi.spu_mode = 0          -- fresh-made only (现制)
  AND oi.gift_flag = 0
  AND oi.create_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY oi.spu_code, oi.spu_name, oi.one_category_name, oi.two_category_name
ORDER BY cups DESC LIMIT 20;
```

### D. Coupon Redemption by Campaign
```sql
SELECT activity_name,
       coupon_denomination,
       COUNT(*) AS issued,
       SUM(CASE WHEN use_status=1 THEN 1 ELSE 0 END) AS redeemed,
       ROUND(SUM(CASE WHEN use_status=1 THEN 1 ELSE 0 END)/COUNT(*)*100,1) AS redemption_pct,
       SUM(CASE WHEN use_status=1 THEN coupon_denomination ELSE 0 END) AS total_discount_cost
FROM luckyus_sales_marketing.t_coupon_record
WHERE tenant = 'LKUS'
GROUP BY activity_name, coupon_denomination
ORDER BY issued DESC LIMIT 20;
```

---

*Report generated 2026-03-19 by David Zeng, DBA/Infrastructure Team*
*Data as of: luckyus_sales_order latest record 2026-03-19 11:40 UTC*
*Next update: Re-run Phase 3 queries after 30 days of additional CDP data accumulation*
