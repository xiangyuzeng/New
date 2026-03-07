# Revenue Impact Model — SOM to Revenue

> **Purpose:** Quantitative model linking Share of Model (SOM) improvement to incremental revenue for Luckin Coffee NYC.
> **Baseline period:** Feb 5 – Mar 6, 2026 | **Stores:** 11 (10 Manhattan + 1 JFK)

---

## 1. Current Baseline Metrics

| Metric | Value | Source |
|--------|-------|--------|
| Daily orders | 2,791 | 30-day average (Feb 5 – Mar 6) |
| Monthly orders | ~75,000 | Feb 2026: 74,853 |
| Average order value (AOV) | $5.01 | All channels combined |
| Daily revenue | $13,930 | Calculated: 2,791 × $5.01 |
| Monthly revenue | $375,000 | Feb 2026: $375,436 |
| Active stores | 11 | 10 Manhattan + 1 JFK |
| Revenue per store/month | ~$34,100 | $375K ÷ 11 stores |
| Revenue per store/day | ~$1,266 | $34,100 ÷ 26.9 avg days |

---

## 2. Customer Acquisition Funnel

| Funnel Stage | Value | Notes |
|--------------|-------|-------|
| New customers/week | 4,224 | 37-week average (Jul 2025 – Mar 2026) |
| New customers/month | ~18,300 | 4,224 × 4.33 weeks |
| Repeat customer rate | 37.9% | Customers who order 2+ times |
| Monthly unique customers | 35,608 | Feb 2026 |
| Registered user base | 277,000 | Cumulative |
| Monthly active rate | 12.9% | 35,608 ÷ 277,000 |
| Orders per active customer | 2.1 | 74,853 ÷ 35,608 |

### Customer Lifetime Value (Estimated)
- **First-month revenue per new customer:** $5.01 × 1.5 orders = **$7.52**
- **Repeat customer monthly revenue:** $5.01 × 2.8 orders = **$14.03** (higher frequency)
- **Blended monthly revenue per active customer:** $375,436 ÷ 35,608 = **$10.54**
- **Estimated 12-month LTV (with 37.9% retention):** ~$10.54 × 4.2 active months = **$44.27**

---

## 3. SOM (Share of Model) Framework

### What is SOM?
Share of Model measures what percentage of AI-generated responses mention or recommend Luckin Coffee when a user asks an LLM about coffee in NYC. For example:

- **Query:** "What's the best coffee shop near Times Square?"
- **Current state:** AI might mention Starbucks, Blue Bottle, Dunkin' — but rarely Luckin
- **Target state:** AI includes Luckin in its recommendations with specific talking points

### SOM → Customer Acquisition Path
```
AI Query about NYC coffee
  → AI mentions Luckin (SOM event)
    → User considers Luckin (awareness)
      → User downloads app / visits store (trial)
        → User places first order (acquisition)
          → User returns (retention at 37.9%)
```

### Conversion Assumptions

| Stage | Conversion Rate | Basis |
|-------|----------------|-------|
| SOM mention → User awareness | 60% | User reads/processes the recommendation |
| Awareness → App download/visit | 8% | Industry benchmark for intent-to-action on AI recommendations |
| Download → First order | 40% | Luckin app conversion rate (aggressive promotions) |
| First order → Repeat customer | 37.9% | Measured from production data |

**Net conversion: SOM mention → Paying customer = 1.92%**
(0.60 × 0.08 × 0.40 = 0.0192)

---

## 4. Estimating AI Query Volume for NYC Coffee

### Market sizing
- **NYC metro population:** 8.3 million residents + ~60 million annual tourists
- **Daily coffee drinkers in NYC:** ~4.5 million (54% of adults drink coffee daily)
- **Estimated daily "coffee near me" type queries to AI:** growing rapidly with AI adoption

### AI query volume estimates (NYC coffee-related)

| Scenario | Daily AI queries about NYC coffee | Monthly queries |
|----------|----------------------------------|-----------------|
| Conservative | 5,000 | 150,000 |
| Moderate | 15,000 | 450,000 |
| Aggressive | 40,000 | 1,200,000 |

*Based on: ChatGPT ~200M weekly active users globally, ~3% US urban food/drink queries, NYC share ~4%.*

---

## 5. Revenue Impact Projections

### Formula
```
Monthly incremental customers = Monthly AI queries × SOM% × Net conversion (1.92%)
Monthly incremental revenue = Incremental customers × Monthly revenue per customer ($10.54)
```

### Conservative Scenario (5,000 daily queries)

| SOM | Monthly Mentions | New Customers | Monthly Revenue Lift | Annual Revenue Lift |
|-----|-----------------|---------------|---------------------|-------------------|
| 1% | 1,500 | 29 | $306 | $3,660 |
| 5% | 7,500 | 144 | $1,518 | $18,216 |
| 10% | 15,000 | 288 | $3,035 | $36,420 |
| 20% | 30,000 | 576 | $6,071 | $72,852 |
| 30% | 45,000 | 864 | $9,107 | $109,284 |

### Moderate Scenario (15,000 daily queries)

| SOM | Monthly Mentions | New Customers | Monthly Revenue Lift | Annual Revenue Lift |
|-----|-----------------|---------------|---------------------|-------------------|
| 1% | 4,500 | 86 | $906 | $10,872 |
| 5% | 22,500 | 432 | $4,553 | $54,636 |
| 10% | 45,000 | 864 | $9,107 | $109,284 |
| 20% | 90,000 | 1,728 | $18,213 | $218,556 |
| 30% | 135,000 | 2,592 | $27,320 | $327,840 |

### Aggressive Scenario (40,000 daily queries)

| SOM | Monthly Mentions | New Customers | Monthly Revenue Lift | Annual Revenue Lift |
|-----|-----------------|---------------|---------------------|-------------------|
| 1% | 12,000 | 230 | $2,424 | $29,088 |
| 5% | 60,000 | 1,152 | $12,142 | $145,704 |
| 10% | 120,000 | 2,304 | $24,284 | $291,408 |
| 20% | 240,000 | 4,608 | $48,568 | $582,816 |
| 30% | 360,000 | 6,912 | $72,852 | $874,224 |

---

## 6. Compounding Effects (Not Modeled Above)

The projections above capture only **direct first-order revenue**. Additional revenue multipliers include:

### Retention multiplier
- Each acquired customer has a **37.9% chance** of becoming a repeat customer
- Repeat customers order **2.8× per month** at $5.01 AOV = $14.03/month
- Over 12 months, a retained customer contributes **~$44 in LTV** vs $10.54 in month 1
- **Compounding effect:** SOM-acquired customers in Month 1 continue generating revenue in Months 2–12

### Word-of-mouth amplifier
- Each satisfied customer tells an estimated 2–3 people about Luckin (novelty factor in NYC)
- This creates an **organic multiplier of ~1.3×** on top of direct AI-driven acquisition
- Social media sharing of unique drinks (Coconut Latte, Matcha) amplifies further

### AOV growth from delivery channel
- As customers discover delivery option, some shift from $5 AOV (app) to $7 AOV (delivery)
- Catering discovery: corporate customers finding Luckin through AI → $16–17 AOV orders
- Potential **15–25% AOV uplift** as channel mix evolves

### Applying multipliers (moderate scenario, 10% SOM)

| Component | Monthly Value |
|-----------|--------------|
| Direct first-month revenue | $9,107 |
| Retention revenue (months 2–12 carryover) | +$6,800 |
| Word-of-mouth multiplier (1.3×) | +$2,732 |
| AOV uplift from channel migration (15%) | +$1,366 |
| **Total estimated monthly impact at steady state** | **~$20,000** |
| **Annualized** | **~$240,000** |

---

## 7. Break-Even Analysis for GEO Investment

### What would GEO Agent implementation cost?
- **Development:** Hackathon project → minimal incremental cost
- **Ongoing content updates:** ~2 hours/week of data refresh → ~$500/month labor
- **AI model fine-tuning / SEO equivalent efforts:** ~$1,000–2,000/month

### Break-even SOM needed

| Monthly GEO cost | Break-even SOM (moderate scenario) | Break-even SOM (aggressive scenario) |
|-----------------|-----------------------------------|-------------------------------------|
| $500 | 0.6% | 0.2% |
| $1,500 | 1.7% | 0.6% |
| $2,500 | 2.8% | 1.0% |

**Conclusion:** Even a **1–3% SOM** justifies the GEO investment in almost every scenario.

---

## 8. Strategic Context

### Current competitive landscape (estimated SOM)
- **Starbucks:** ~40–50% SOM (dominant brand, most mentioned)
- **Dunkin':** ~15–20% SOM (value positioned, strong NYC presence)
- **Blue Bottle / specialty:** ~10–15% SOM (quality narrative)
- **Local independents:** ~10–15% SOM (neighborhood favorites)
- **Luckin Coffee:** ~1–3% SOM (new entrant, growing awareness)

### Realistic SOM targets
- **3 months:** Achieve 5% SOM through GEO content optimization
- **6 months:** Reach 10% SOM with consistent data-backed content updates
- **12 months:** Target 15–20% SOM as store count grows and brand awareness increases

### Revenue impact at target milestones (moderate scenario)

| Timeline | Target SOM | Monthly Revenue Lift | Cumulative Annual Impact |
|----------|-----------|---------------------|------------------------|
| Month 3 | 5% | $4,553 | $13,659 |
| Month 6 | 10% | $9,107 | $54,642 |
| Month 12 | 15% | $13,660 | $136,600 |

---

## 9. Key Assumptions & Limitations

1. **AI query volume is estimated** — no public data on NYC-specific coffee queries to LLMs
2. **Conversion rates are modeled**, not measured — would need attribution tracking to validate
3. **SOM measurement methodology** needs definition — how many queries, which LLMs, what prompts
4. **Assumes incremental customers** — some SOM-influenced users may already know Luckin
5. **Does not model cannibalization** — Luckin SOM gain may not proportionally reduce competitors
6. **Store capacity constraint:** at ~600 orders/day/store, 11 stores can handle ~6,600 daily orders; current is 2,791 — **plenty of headroom (57% capacity available)**
7. **Revenue projections are pre-COGS** — actual profit impact depends on ~65–70% gross margin

---

## 10. Recommended SOM Measurement Protocol

To validate this model, the GEO Agent should:

1. **Benchmark current SOM:** Run 100 standardized NYC coffee queries across ChatGPT, Claude, Gemini, Perplexity
2. **Track monthly:** Same query set, measure % mentioning Luckin
3. **Attribution:** Add UTM parameters or promo codes to GEO-influenced content to track actual conversions
4. **A/B testing:** Compare customer acquisition rates in periods with active GEO vs baseline

---

*Generated: 2026-03-07 | Model based on Luckin Coffee USA production data (Feb 5 – Mar 6, 2026)*
