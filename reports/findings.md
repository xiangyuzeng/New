# Database Investigation Report — LCNA-OPS-2026-021-v2

**Generated**: 2026-04-12  
**Method**: Direct production queries via mcp-db-gateway (read-only)  
**Scope**: 7-day lookback (2026-04-05 to 2026-04-12) for distributions; full history for depth check  
**Databases**: luckyus_sales_order, luckyus_iluckyhealth, luckyus_opshop

---

## 1. Executive Summary

### What Works (go for it)
- **Store ranking composite score** (Ch2): All 4 inputs (revenue, completion, avg ticket, prep time) are reliable per store across 12 active stores
- **Per-store satisfaction** (Ch3): t_order_comment has `order_id` — JOIN confirmed working, 44-488 reviews/store/week
- **Product-hour heatmap** (Ch5): 3 categories (Drink 91%, Food 8%, Merch 0.3%), 42 active products, full item-level pricing
- **Customer repeat frequency** (Ch6): 100% user_no coverage on valid orders, clear repeat distribution
- **Spend tier analysis** (Ch6): $3/$5/$8 boundaries create meaningful 23/43/22/12% segments
- **Channel commission estimates** (Ch4): All 6 channel codes present and stable

### What Needs Adjustment
- **Cancel reason breakdown** (Ch3): **NOT FEASIBLE** — no `cancel_reason` column exists
- **Per-channel new/returning** (Ch4): **PARTIAL** — 3P channels (Grubhub/UberEats/DoorDash) route through single system account
- **Cancel rate threshold O-2 >5%**: Actual rate is 3.1% — threshold would never fire
- **Prep SLA threshold OPS-3 3 min**: Only 63.7% of orders meet it — would flag every store every week
- **Channel concentration MKT-2 >50%**: Own App is 84.1% — threshold always fires

### Key Discoveries
- t_order_item has **rich discount columns**: `origin_price`, `sale_price`, `coupon_share_money`, `voucher_share_money` — enables full discount decomposition
- t_order_make has **barista identity**: `make_id` + `make_name` — enables per-barista performance analysis
- t_shop_info has **GPS coordinates**: `location_longitude`/`location_latitude` — enables geographic analysis
- t_order has `total_money`/`payable_money`/`pay_money` chain — gross-to-net revenue analysis feasible
- 289 days of order history (since 2025-06-27), 672K total orders — sufficient for MoM trends

---

## 2. Full Table Schemas

### 2.1 luckyus_sales_order.t_order (46 columns)

| Column | Type | Null | Key | Notes |
|--------|------|------|-----|-------|
| id | bigint unsigned | NO | PRI | |
| tenant | varchar(10) | NO | | Always 'LKUS' for US |
| parent_id | bigint unsigned | NO | | Parent order for split orders |
| **channel** | smallint | NO | | 1=MiniProg, 2=OwnApp, 3=POS, 8=UberEats, 9=DoorDash, 10=Grubhub |
| order_category | smallint unsigned | NO | | |
| order_type | smallint unsigned | NO | | |
| **user_no** | varchar(32) | NO | MUL | 100% coverage on valid orders; 3P uses system account |
| user_type | tinyint unsigned | NO | | |
| user_nick_name | varchar(64) | YES | | PII — mask in reports |
| user_sex | smallint | YES | | |
| **shop_id** | bigint unsigned | NO | MUL | FK to store |
| shop_type | smallint unsigned | NO | | |
| **shop_name** | varchar(100) | YES | | Denormalized store name |
| **shop_number** | varchar(100) | YES | | US-prefixed store code |
| country_code | varchar(20) | YES | | |
| country_name | varchar(100) | YES | | |
| city_code | varchar(20) | YES | | |
| city_name | varchar(100) | YES | | |
| **status** | tinyint unsigned | NO | | 0=cancelled, 20=paid/in-progress, 90=completed |
| produce_status | smallint | YES | | Production pipeline status |
| express_status | smallint | YES | | Delivery status |
| invoice_status | smallint | YES | | |
| **refund_status** | smallint | YES | | 0=none, 1=pending, 2=no-refund, 3=other, 5=refunded |
| comment_status | smallint | YES | | |
| display_flag | tinyint unsigned | NO | | |
| currency_code | varchar(10) | NO | | |
| **total_money** | decimal(12,4) | NO | | Original price before discounts |
| **payable_money** | decimal(12,4) | NO | | After platform discounts |
| **pay_money** | decimal(12,4) | NO | | Actual amount paid |
| pay_time | datetime | YES | MUL | |
| cancel_time | datetime | YES | | |
| finish_time | datetime | YES | MUL | |
| create_type | smallint | NO | | |
| create_id | varchar(32) | YES | | |
| create_name | varchar(60) | YES | | |
| **create_time** | datetime | NO | MUL | Primary time filter (indexed) |
| modify_id | varchar(32) | YES | | |
| modify_name | varchar(60) | YES | | |
| modify_time | datetime | NO | | |
| version | int | NO | | |
| refund_time | datetime | YES | | |
| order_sub_type | smallint | YES | | |
| fulfill_status | smallint | YES | | |
| order_language | varchar(20) | YES | | |
| user_timezone | varchar(60) | YES | | |
| invoiced_time | datetime | YES | | |

**Key finding**: No `cancel_reason`, `cancel_type`, `coupon_id`, `delivery_fee`, or `original_price` columns. Discount analysis must use `total_money - pay_money` gap or item-level `coupon_share_money`.

### 2.2 luckyus_sales_order.t_order_item (48 columns)

| Column | Type | Null | Key | Notes |
|--------|------|------|-----|-------|
| id | bigint unsigned | NO | PRI | |
| tenant | varchar(10) | NO | | |
| **order_id** | bigint unsigned | NO | MUL | FK to t_order.id |
| spu_type | smallint | NO | | |
| **spu_code** | varchar(50) | NO | | Product code |
| **spu_name** | varchar(100) | NO | | Product name |
| spu_mode | smallint | YES | | |
| one_category_mid | varchar(20) | YES | | L1 category ID |
| two_category_mid | varchar(20) | YES | | L2 category ID |
| three_category_mid | varchar(20) | YES | | L3 category ID |
| **one_category_name** | varchar(100) | YES | | L1: Drink, Food, Merchandise |
| **two_category_name** | varchar(100) | YES | | L2 subcategory |
| **three_category_name** | varchar(100) | YES | | L3 subcategory |
| **sku_code** | varchar(255) | NO | | SKU identifier |
| **sku_name** | varchar(400) | YES | | Full SKU name (includes size/options) |
| **sku_attributes** | varchar(2000) | YES | | JSON: size, ice level, sugar level, add-ons |
| sku_image | varchar(255) | YES | | |
| sort | int | YES | | Display order |
| **origin_price** | decimal(12,4) | NO | | Original menu price |
| **sale_price** | decimal(12,4) | YES | | Sale/promotional price |
| **addition_money** | decimal(12,4) | YES | | Add-on charges (extra shots, etc.) |
| payable_money | decimal(12,4) | NO | | |
| **pay_money** | decimal(12,4) | NO | | Actual paid for this item |
| invoice_status | smallint | NO | | |
| invoice_money | decimal(12,4) | NO | | |
| invoiced_money | decimal(12,4) | NO | | |
| refund_status | smallint | NO | | |
| refund_money | decimal(12,4) | NO | | |
| refunded_money | decimal(12,4) | NO | | |
| return_type | smallint | YES | | |
| tax_info | varchar(500) | NO | | |
| stock_flag | tinyint unsigned | NO | | |
| **sku_num** | tinyint unsigned | NO | | Quantity ordered |
| gift_flag | tinyint unsigned | NO | | Gifted item flag |
| commodity_info | varchar(500) | NO | | |
| delete_flag | tinyint unsigned | NO | | |
| create_time | datetime | NO | | |
| modify_time | datetime | NO | | |
| version | int | NO | | |
| tax_rate | decimal(14,6) | YES | | |
| tax | decimal(14,4) | YES | | |
| sku_type | smallint | YES | | |
| spu_show_name | varchar(100) | YES | | Display name (may differ from spu_name) |
| sxu_code | varchar(255) | YES | | |
| spu_src_type | smallint | NO | | |
| **voucher_share_money** | decimal(14,4) | YES | | Voucher discount allocated to this item |
| **coupon_share_money** | decimal(14,4) | YES | | Coupon discount allocated to this item |
| tax_mode | tinyint | YES | | |

**Key finding**: Rich product data! 3-level category hierarchy, SKU attributes (size/ice/sugar), pricing chain (origin -> sale -> pay), and per-item discount decomposition (coupon + voucher). Enables deep product analytics.

### 2.3 luckyus_sales_order.t_order_make (21 columns)

| Column | Type | Null | Key | Notes |
|--------|------|------|-----|-------|
| id | bigint unsigned | NO | PRI | |
| tenant | varchar(10) | NO | | |
| **order_id** | bigint | NO | MUL | FK to t_order.id |
| dispatch_type | smallint | YES | | |
| dispatch_status | smallint | YES | | |
| dispatch_again | smallint | NO | | Re-dispatch flag |
| dispatch_no | varchar(30) | YES | | |
| **dispatch_time** | datetime | YES | | When order dispatched to barista |
| accept_type | smallint | NO | | |
| **accept_time** | datetime | YES | | When barista accepted |
| finish_type | smallint | YES | | |
| **finish_time** | datetime | YES | | When preparation completed |
| cancel_time | datetime | YES | | |
| **expect_time** | datetime | YES | | Expected completion time (SLA target) |
| make_order_no | varchar(32) | YES | | |
| **make_id** | varchar(32) | YES | | Barista/maker identifier |
| **make_name** | varchar(50) | YES | | Barista/maker name |
| make_type | smallint | YES | | |
| create_time | datetime | NO | | |
| modify_time | datetime | NO | | |
| auto_finish_flag | smallint | NO | | Auto-completed flag |

**Key finding**: Full production timeline: `dispatch_time` -> `accept_time` -> `finish_time`. Queue time = `accept_time - dispatch_time`. Prep time = `finish_time - accept_time`. Barista identity via `make_id`/`make_name`. No explicit queue_position column.

### 2.4 luckyus_sales_order.t_order_comment (31 columns)

| Column | Type | Null | Key | Notes |
|--------|------|------|-----|-------|
| id | bigint unsigned | NO | PRI | |
| tenant | varchar(10) | NO | | |
| **order_id** | bigint | NO | MUL | FK to t_order.id — enables per-store JOIN |
| type | smallint | NO | | Comment type |
| **level** | smallint | YES | | 1=satisfied, 2=unsatisfied (binary only) |
| **labels** | varchar(200) | YES | | Category labels (e.g., taste, speed, service) |
| **comment** | varchar(1000) | YES | | Free-text comment |
| comment_business_type | varchar(100) | YES | | |
| reply | varchar(300) | YES | | Store reply |
| reply_time | datetime | YES | | |
| create_id | varchar(32) | YES | | |
| create_user | varchar(60) | YES | | PII — mask |
| create_type | smallint | YES | | |
| create_time | datetime | YES | | |
| complaint_flag | smallint | NO | | Escalated complaint flag |
| picture_url | varchar(1024) | YES | | Photo attachment |
| dept_id | bigint | NO | MUL | |
| **user_no** | varchar(32) | NO | MUL | Customer identifier |
| origin | smallint | YES | | |
| customer_reply_status | tinyint | NO | | |
| customer_reply_content | varchar(500) | YES | | |
| compensation_send_coupon | tinyint | YES | | Was coupon sent as compensation? |
| contact_customer | tinyint | YES | | Was customer contacted? |
| reach_agreement | tinyint | YES | | Was resolution reached? |
| compensation_reason_id | bigint | YES | | |
| proposal_no | varchar(45) | YES | | |

**Key finding**: Beyond level, has `labels` (category tags), `comment` (free text), `complaint_flag`, and full complaint resolution tracking. NLP on comment text and label analysis would enrich satisfaction reporting significantly.

### 2.5 luckyus_iluckyhealth.t_collect_order_tenant_inter (10 columns)

| Column | Type | Null | Key |
|--------|------|------|-----|
| id | bigint unsigned | NO | PRI |
| metric_tenant_name | varchar(100) | YES | MUL |
| metric_name | varchar(100) | YES | |
| metric_name_comment | varchar(200) | YES | |
| metric_value | int | YES | |
| metric_value_comment | varchar(200) | YES | |
| metric_count | int | YES | |
| metric_count_comment | varchar(200) | YES | |
| create_time | timestamp | NO | MUL |
| insert_time | datetime | YES | MUL |

**Available metrics**: 20 types including `order_all_*`, `order_channel_*`, `order_shop_*`, `order_type_*`, `order_coffee_*` — each with create/pay/cancel/done variants. Rich real-time funnel data.

### 2.6 luckyus_iluckyhealth.t_collect_shop_inter (9 columns)

Same structure as above minus `metric_tenant_name`. Used for shop opening count (`tenant_shop_now_opening`).

### 2.7 luckyus_opshop.t_shop_info (53 columns)

| Column | Type | Null | Key | Notes |
|--------|------|------|-----|-------|
| id | bigint unsigned | NO | PRI | |
| tenant | varchar(4) | YES | MUL | |
| dept_id | bigint | NO | MUL | |
| **shop_no** | varchar(8) | NO | | US-prefixed code |
| **shop_name** | varchar(128) | YES | | |
| **status** | int | YES | | 1=active, 2=inactive |
| dept_name | varchar(128) | YES | | |
| manager_name | varchar(128) | YES | | PII |
| manager_phone | varchar(64) | YES | | PII |
| time_zone | varchar(32) | YES | | |
| shop_email | varchar(64) | YES | | |
| shop_phone | varchar(64) | YES | | |
| brand_no | varchar(32) | YES | | |
| **shop_level** | varchar(32) | YES | | Store tier/classification |
| **operation_mode** | tinyint(1) | YES | | |
| cooperation_no | varchar(32) | YES | | |
| **shop_model** | tinyint(1) | YES | | Store model type |
| shop_price_level | varchar(10) | YES | | Pricing tier |
| shop_out_price_level | varchar(10) | YES | | |
| dispatch_range | varchar(2000) | YES | | Delivery zone polygon |
| **set_up_time** | datetime | YES | | Store opening date |
| **shut_up_time** | datetime | YES | | Store closing date (if closed) |
| off_time | datetime | YES | | |
| internal | tinyint(1) | YES | | Internal/test store flag |
| eat_in | tinyint(1) | YES | | Dine-in capability |
| scene_type | varchar(32) | YES | | Location type (office, retail, etc.) |
| scene_detail | varchar(32) | YES | | |
| country_no | varchar(32) | YES | | |
| country_name | varchar(64) | YES | | |
| administrative_area_name | varchar(128) | YES | | State |
| locality_name | varchar(128) | YES | | City |
| sublocality_name | varchar(128) | YES | | Neighborhood |
| **location_longitude** | decimal(10,6) | YES | | GPS longitude |
| **location_latitude** | decimal(10,6) | YES | | GPS latitude |
| **address** | varchar(500) | YES | | Full street address |
| **operation_area** | varchar(40) | YES | | Operating area classification |
| remark | varchar(1000) | YES | | |
| *(+ audit columns)* | | | | |

**Key finding**: 13 active US stores, 17 inactive. Has GPS, opening dates, store model/level, operation area, scene type. No capacity/sqft column. Staffing proxy must come from order volume, not physical capacity.

---

## 3. Critical Questions Answered

| # | Question | Answer | Impact on Requirements |
|---|----------|--------|----------------------|
| Q1 | Does t_order_comment have order_id? | **YES** — bigint, indexed (MUL) | Per-store satisfaction is **FEASIBLE**. JOIN confirmed working across all 12 stores. |
| Q2 | Does t_order have cancel_reason? | **NO** — only refund_status (4 values: 0,1,2,3,5) | Cancel reason breakdown is **NOT FEASIBLE**. Must use refund_status categories or comment labels as proxy. |
| Q3 | t_order_item extra columns? | **YES** — sku_num (qty), origin_price, sale_price, addition_money, coupon_share_money, voucher_share_money, sku_attributes, 3-level category | Product analysis depth is **MUCH RICHER** than expected. Full discount decomposition possible. |
| Q4 | t_order coupon/discount columns? | **PARTIAL** — total_money/payable_money/pay_money chain exists. No coupon_id. Item-level coupon_share_money exists. | Gross-to-net discount analysis feasible. Cannot identify specific coupon campaigns by ID. |
| Q5 | t_order_make barista/timing columns? | **YES** — make_id/make_name (barista), dispatch_time/accept_time/finish_time/expect_time | Full production timeline. Queue time derivable. Per-barista analysis possible. |
| Q6 | t_shop_info geographic/capacity? | **YES for geo** — location_longitude/latitude, address, scene_type. **NO for capacity** — no sqft/capacity column. | Geographic heatmap feasible. Staffing proxy must use order volume, not physical capacity. |

---

## 4. Data Distribution Results

### 4.1 Channel Distribution (3A) — 7 days

| Channel | Code | Orders | Revenue | Avg Ticket | Share % | Unique Customers |
|---------|------|--------|---------|------------|---------|-----------------|
| Own App | 2 | 20,683 | $97,241 | $4.70 | 84.1% | 14,263 |
| Mini Program | 1 | 2,088 | $10,318 | $4.94 | 8.5% | 1,478 |
| POS / Walk-in | 3 | 1,456 | $10,443 | $7.17 | 5.9% | 1,292 |
| Grubhub | 10 | 204 | $3,895 | $19.09 | 0.8% | 1* |
| UberEats | 8 | 109 | $1,490 | $13.67 | 0.4% | 1* |
| DoorDash | 9 | 40 | $595 | $14.87 | 0.2% | 1* |
| **Total** | | **24,580** | **$123,982** | **$5.04** | | **17,034** |

*3P channels show unique_customers=1 because all orders route through a single system/API account.

**Analysis**: All 6 known channels present. No unknown channel codes. 3P marketplace avg tickets ($13-19) are 3-4x higher than 1P ($4.70-7.17) due to delivery markups. Total weekly revenue = $124K.

### 4.2 Order Status Distribution (3C) — 7 days

| Status | Count | Share % | Meaning |
|--------|-------|---------|---------|
| 90 | 24,535 | 96.7% | Completed |
| 0 | 791 | 3.1% | Cancelled |
| 20 | 45 | 0.2% | In-progress (at query time) |

**Cancel rate = 3.1%**. Only 3 status codes exist.

### 4.3 Refund Status Distribution (3B) — 7 days

| Refund Status | Count | Share % | Meaning |
|---------------|-------|---------|---------|
| 2 | 24,538 | 96.7% | No refund (normal) |
| 1 | 589 | 2.3% | Refund pending/partial |
| 5 | 222 | 0.9% | Fully refunded |
| 3 | 22 | 0.1% | Other |

**Refund rate = 3.2%** (status 1+5). Not granular enough for cancel _reason_ analysis.

### 4.4 Product Category Distribution (3D) — 7 days

| Category | Items | Unique Products | Share % |
|----------|-------|-----------------|---------|
| Drink | 29,320 | 36 | 91.3% |
| Food | 2,665 | 5 | 8.3% |
| Merchandise | 111 | 1 | 0.3% |

**Analysis**: 3 categories (not just Drink). Food at 8.3% is meaningful for category mix analysis. 42 total active products.

### 4.5 Customer Repeat Behavior (3E) — 30 days

| Frequency Bucket | Customers | Share % |
|-----------------|-----------|---------|
| 1 time | 32,082 | 63.9% |
| 2-3 times | 11,790 | 23.5% |
| 4-7 times | 4,722 | 9.4% |
| 8-14 times | 1,361 | 2.7% |
| 15+ times | 342 | 0.7% |

**Total unique customers (30d)**: 50,297  
**Repeat rate**: 36.1% (18,215 customers ordered 2+ times)  
**Power users (8+)**: 3.4% (1,703 customers)

### 4.6 Spend Tier Distribution (3F) — 7 days

| Tier | Orders | Revenue | Avg in Tier | Order % | Revenue % |
|------|--------|---------|-------------|---------|-----------|
| $0-3 | 5,622 | $13,618 | $2.42 | 22.9% | 11.0% |
| $3-5 | 10,561 | $40,577 | $3.84 | 43.0% | 32.7% |
| $5-8 | 5,499 | $35,113 | $6.39 | 22.4% | 28.3% |
| $8+ | 2,898 | $34,675 | $11.97 | 11.8% | 28.0% |

**Analysis**: $3-5 is the dominant order tier (43%). The $8+ tier is only 11.8% of orders but contributes 28% of revenue — mainly 3P marketplace orders and multi-item orders.

### 4.7 Review/Satisfaction Volume (3G) — 7 days

| Metric | Value |
|--------|-------|
| Total reviews | 2,890 |
| Satisfied (level=1) | 2,802 (96.95%) |
| Unsatisfied (level=2) | 88 (3.05%) |
| Distinct levels | 2 (binary only) |

**Analysis**: ~413 reviews/day. Binary satisfaction only (no NPS). 2,890/week is sufficient for per-store breakdown. Additional depth available via `labels` and `comment` text columns.

### 4.8 Prep Time Distribution (3H) — 7 days

| Metric | Value |
|--------|-------|
| Total records | 25,389 |
| Average prep time | 3.0 min |
| Minimum | 0.1 min |
| Maximum | 111.7 min (outlier) |
| Within 3 min | 16,174 (63.7%) |
| Within 5 min | 21,981 (86.6%) |
| Null timestamps | 622 (2.5%) |

**Analysis**: 3-minute SLA = 63.7% compliance. 5-minute SLA = 86.6% compliance. The 111.7 min max is a clear outlier (forgotten/reopened order). Null rate of 2.5% is acceptable.

### 4.9 User Coverage for New/Returning (3I) — 7 days

| Metric | Value |
|--------|-------|
| Unique users | 17,017 |
| Orders with null/empty user_no | 0 |
| Total valid orders | 24,578 |
| **User coverage** | **100%** |

**Analysis**: Perfect user_no coverage. New/returning analysis is fully reliable for 1P channels. Exclude 3P channels (353 orders/week) from customer-level analysis.

### 4.10 Per-Store Satisfaction (3J) — 7 days

| Store | Reviews | Satisfaction % |
|-------|---------|---------------|
| 8th & Broadway | 488 | 96.1% |
| 37th & Broadway | 432 | 95.4% |
| 52nd & Madison | 288 | 98.3% |
| 102 Fulton | 287 | 96.5% |
| 54th & 8th | 284 | 97.2% |
| 28th & 6th | 229 | 98.3% |
| 33rd & 10th | 214 | 98.1% |
| 21st & 3rd | 191 | 98.4% |
| 15th & 3rd | 153 | 98.0% |
| 100 Maiden Ln | 142 | 94.4% |
| 16th & 6th | 138 | 98.6% |
| 29th & 3rd | 44 | 95.5% |

**Analysis**: JOIN confirmed across all 12 stores. Range: 94.4% (100 Maiden Ln) to 98.6% (16th & 6th). Lowest-volume store (29th & 3rd, 44 reviews) is likely a newer location. All stores have statistically meaningful sample sizes.

### 4.11 Historical Data Depth (3K)

| Metric | Value |
|--------|-------|
| Earliest order | 2025-06-27 |
| Latest order | 2026-04-12 |
| Total orders | 672,002 |
| Days span | 289 (~9.6 months) |

**Analysis**: Sufficient for 30-day trend, MoM comparison, and partial seasonal analysis. Not enough for full YoY.

### 4.12 Discount Analysis (Supplemental)

| Discount Gap (total - pay) | Orders |
|----------------------------|--------|
| $4.46 | 1,651 |
| $3.22 | 1,411 |
| $2.76 | 1,291 |
| $0.00 (full price) | 1,040 |
| $1.46 | 899 |

**Analysis**: 95.8% of orders have some discount. Average discount ~$3-4. `total_money - pay_money` is a reliable discount proxy at order level.

---

## 5. Requirements Feasibility Matrix

| Req Section | Metric | Status | Data Gap | Recommendation |
|-------------|--------|--------|----------|----------------|
| Ch2 | Store ranking composite score | CONFIRMED | None | All 4 inputs reliable per store |
| Ch3 | Cancel reason breakdown | NOT FEASIBLE | No `cancel_reason` column | Use refund_status categories (4 values) OR mine t_order_comment.labels for complaint categories |
| Ch3 | Per-store satisfaction | CONFIRMED | None | JOIN via order_id works. 44-488 reviews/store/week. Consider adding labels analysis. |
| Ch4 | Per-channel new/returning | PARTIAL | 3P channels use single system account | Report for 1P only (98.6% of orders). Footnote 3P limitation. |
| Ch4 | Commission estimates | CONFIRMED | None | All 6 channel codes stable. Apply commission rates to 3P revenue. |
| Ch5 | Product-hour heatmap | CONFIRMED | None | 3 categories, 42 products. Item JOIN by hour works. |
| Ch5 | Product margin analysis | CONFIRMED | None (better than expected) | origin_price/sale_price/pay_money/coupon_share_money enables full decomposition |
| Ch6 | Spend tier ($3/$5/$8) | CONFIRMED | None | Segments are meaningful: 23/43/22/12%. Consider adding $15+ tier. |
| Ch6 | Repeat purchase frequency | CONFIRMED | None | 100% user_no coverage. 36.1% repeat rate (30d). |
| AI O-2 | Cancel rate >5% | ADJUST THRESHOLD | None | Actual rate = 3.1%. Lower to 4% or use relative threshold (>1.5x fleet avg). |
| AI OPS-3 | Prep SLA 3 min | ADJUST THRESHOLD | None | 63.7% within 3 min. Use 5 min (86.6%) or percentile-based (flag if p75 > 5 min). |
| AI MKT-2 | Channel concentration >50% | ADJUST THRESHOLD | None | Own App = 84.1%. Raise to 85-90% or use WoW shift detection instead. |

---

## 6. Recommended Threshold Adjustments

### 6.1 Cancel Rate (AI Rule O-2)
- **Current**: >5% triggers alert
- **Actual**: 3.1% fleet-wide
- **Recommendation**: Lower to **4%** absolute, OR use **relative threshold**: alert when any store's cancel rate exceeds 1.5x the fleet average (currently ~4.65%). This catches outlier stores without constant false positives.

### 6.2 Prep Time SLA (AI Rule OPS-3)
- **Current**: 3 minutes
- **Actual**: Average 3.0 min, only 63.7% meet 3 min
- **Recommendation**: Two-tier SLA:
  - **Standard**: 5 minutes (86.6% compliance currently)
  - **Stretch goal**: 3 minutes for reporting/trending only
  - **Alert trigger**: Flag stores where **average** exceeds 5 min or **p75** exceeds 7 min

### 6.3 Channel Concentration (AI Rule MKT-2)
- **Current**: >50% triggers alert
- **Actual**: Own App = 84.1% (always triggers)
- **Recommendation**: Replace absolute threshold with **WoW change detection**: alert if any channel's share shifts by >5 percentage points WoW. This catches meaningful changes (e.g., 3P growth, POS decline) without constant noise.

### 6.4 Spend Tiers (Ch6)
- **Current**: $3/$5/$8 boundaries
- **Recommendation**: Add **$15+ tier** to isolate 3P marketplace multi-item orders (avg $14-19). Boundaries: $0-3 / $3-5 / $5-8 / $8-15 / $15+.

---

## 7. Data Gaps and Suggested Alternatives

### 7.1 Cancel Reason (Critical Gap)
- **Missing**: `cancel_reason` column on t_order
- **Alternatives**:
  1. **refund_status breakdown**: 4 categories (none / pending / no-refund / refunded) — coarse but available
  2. **t_order_comment.labels**: Category tags on complaints may indicate dissatisfaction reasons
  3. **t_order_comment.comment**: Free text — amenable to NLP/keyword extraction for reason categorization
  4. **App team request**: Add `cancel_reason` enum to t_order (requires backend change)

### 7.2 Coupon Campaign Identification
- **Missing**: No `coupon_id` or `promotion_id` on t_order
- **Available**: `coupon_share_money` and `voucher_share_money` at item level, `total_money - pay_money` at order level
- **Workaround**: Track discount patterns by amount clusters. Cannot attribute to specific campaigns.

### 7.3 Store Capacity / Sqft
- **Missing**: No capacity or area_sqft column on t_shop_info
- **Available**: `operation_area`, `shop_model`, `eat_in` flag
- **Workaround**: Use orders/hour as capacity proxy. Benchmark stores against each other.

### 7.4 3P Customer Identity
- **Missing**: Real customer identity for Grubhub/UberEats/DoorDash orders
- **Impact**: 1.4% of orders (353/week) — minimal
- **Workaround**: Exclude 3P from all customer-level metrics. Report 3P as revenue/order metrics only.

### 7.5 NPS / Multi-Level Satisfaction
- **Missing**: Only binary satisfaction (1=good, 2=bad). No 1-5 or NPS scale.
- **Available**: `labels` (tags), `comment` (text), `complaint_flag`, resolution tracking
- **Workaround**: Derive a richer satisfaction score from: base level + has_complaint_flag + has_photo + response_time + resolution_status

---

## Appendix: Column Discoveries Affecting Requirements Doc

| Discovery | Column(s) | Impact |
|-----------|-----------|--------|
| Barista identity available | t_order_make.make_id, make_name | Add per-barista prep time metrics to Ch3 ops section |
| Full production timeline | dispatch_time -> accept_time -> finish_time | Queue time = accept - dispatch, prep = finish - accept. Can separate queue from prep. |
| 3-level product taxonomy | one/two/three_category_name | Product analysis can go deeper than L1 (Drink/Food) |
| SKU attributes (JSON) | t_order_item.sku_attributes | Size/ice/sugar customization analysis possible |
| Item-level discount tracking | coupon_share_money, voucher_share_money | Discount impact per product, not just per order |
| GPS coordinates | location_longitude, location_latitude | Store proximity analysis, delivery radius validation |
| Store opening dates | set_up_time | Normalize new store performance by age |
| Complaint resolution pipeline | complaint_flag, contact_customer, reach_agreement, compensation_send_coupon | Customer service quality metrics beyond satisfaction % |
| 20 health metric types | t_collect_order_tenant_inter | Per-channel and per-shop funnel data available from iluckyhealth (not just 4 aggregate metrics) |
| Order language / timezone | t_order.order_language, user_timezone | Customer language preference analysis |
