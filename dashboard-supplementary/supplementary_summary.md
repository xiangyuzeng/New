# Supplementary Analytics for Site Selection Dashboard v2.0

**Generated**: 2026-04-09 | **Data through**: 2026-04-07 | **Stores**: 12 active, 9 qualifying for seasonality

---

## Key Surprises from the Data

### 1. Seasonality is Far More Extreme Than Expected
The seasonal index reveals a **52% swing** between peak and trough months:
- **Jul-Aug**: Index 1.50 — fleet averages 50% above annual mean
- **Dec-Jan**: Index 0.66-0.70 — fleet drops 30-34% below mean
- This means a candidate predicted at 476 cups/day (annual average) will likely do **~315 cups/day in January** and **~714 cups/day in August**
- **Implication**: Opening in summer makes first-month P&L look strong; opening in winter makes it look catastrophic — same store, same location

### 2. Cannibalization is Real But Confounded by Seasonality
| New Store | Affected Store | Distance | Raw Change | Market-Adjusted | Huff Predicted |
|-----------|---------------|----------|-----------|----------------|---------------|
| 33rd & 10th (Dec 1) | 28th & 6th | 0.65 mi | -28.7% | **-13.8%** | -4.3% |
| 21st & 3rd (Feb 6) | 15th & 3rd | 0.26 mi | -6.8% | **-8.8%** | -11.1% |
| 52nd & Madison (Feb 26) | 37th & Broadway | 0.85 mi | +20.3% | **+13.6%** | -3.1% |
| 16th & 6th (Mar 23) | 8th & Broadway | 0.60 mi | +38.5% | **+20.8%** | -6.3% |
| 16th & 6th (Mar 23) | 15th & 3rd | 0.65 mi | +21.0% | **-0.5%** | -5.8% |

**Key findings**:
- The Huff model **underestimated** cannibalization for the closest pair that opened in winter (33rd→28th: actual -13.8% vs predicted -4.3%). The winter seasonal dip amplified the effect.
- The Huff model was **reasonably accurate** for 21st→15th (actual -8.8% vs predicted -11.1%).
- Spring openings (16th & 6th in March) show **no cannibalization** — spring recovery masks any diversion effect. This is a seasonality confound, not proof of zero cannibalization.
- **Recommendation**: Huff WEIGHT=0.15 is reasonable for stores >0.5 mi apart. For stores <0.3 mi, actual impact may be higher than predicted in low-season, lower in high-season.

### 3. Rent Data Has Major Discrepancies
| Store | Model Rent | GL-Verified Rent | Delta |
|-------|-----------|-----------------|-------|
| **16th & 6th** | $17,000 | $10,125 | **-40.4%** |
| **21st & 3rd** | $13,000 | $18,000 | **+38.5%** |
| 52nd & Madison | $22,000 | $19,360 | -12.0% |
| 102 Fulton | $15,000 | $16,000 | +6.7% |
| 221 Grand | $14,000 | $13,000 | -7.1% |

- The 16th & 6th and 21st & 3rd discrepancies are large enough to **change model predictions and P&L rankings**
- If 21st & 3rd actually pays $18K (not $13K), its rent efficiency ranking drops significantly and it's even further from breakeven

### 4. Opening Spike is Consistent at ~127% of Steady State
Every store shows a similar pattern:
- **Week 0-1**: 120-130% of steady state (promotional opening)
- **Week 2-3**: 105-115% (settling)
- **Week 4+**: Steady state reached
- **Management rule**: Don't judge a store's true performance until week 5+

### 5. Day-of-Week Patterns Reveal Store DNA
| Pattern | Stores | Characteristics |
|---------|--------|----------------|
| **Commuter** | 33rd & 10th, 37th & Broadway, 100 Maiden Ln, 102 Fulton | Weekday index >1.3×, dead weekends (Sun 40-60% of avg) |
| **Tourist** | 221 Grand, 54th & 8th | Weekend index >1.1×, Saturday peak |
| **Balanced** | 8th & Broadway, 28th & 6th, 15th & 3rd, 21st & 3rd | <15% weekday-weekend variance |

### 6. Revenue Per Cup Varies 25% Across Fleet
- Highest: 100 Maiden Ln at $3.97/cup (financial district, fewer promotions?)
- Lowest: 52nd & Madison at $3.17/cup (heavy promotion to drive volume?)
- Average order value: $4.50-$5.25 (1.27 cups/order fleet average)
- A store with 400 cups/day at $3.97 generates $1,588/day vs 400 cups at $3.17 = $1,268 — **$9,600/month difference**

---

## Highest-Value Additions for Management

**Ranked by decision impact:**

1. **Monthly Seasonality** (highest) — Directly affects opening timing, first-month P&L expectations, and whether to delay pipeline candidates until spring
2. **Cannibalization Evidence** — Validates Huff model accuracy, informs whether "Weak" candidates near existing stores are truly risky
3. **Rent Efficiency** — Identifies which stores give best ROI, informs rent negotiation targets ($X/cup benchmark)
4. **Weekly Time Series** — Shows trajectory, not just average — critical for "is this store improving?" questions
5. **DOW Heatmap** — Helps match candidate locations to comparable store patterns (office vs tourist)
6. **Maturation Curves** — Sets expectations for new store evaluation timeline
7. **Opening Cohort Analysis** — Answers "are we getting better at picking locations?"
8. **Revenue Composition** — Reveals AOV and cups/order variations that affect per-store economics

---

## Recommended Dashboard Sections & Chart Types

| Dataset | Chart Type | Section Name |
|---------|-----------|-------------|
| Weekly Time Series | Multi-line sparklines (one per store) with fleet average overlay | "Performance Trajectories" |
| Monthly Seasonality | Bar chart with seasonal index coloring (green >1.0, red <1.0) | "Seasonal Patterns" |
| Maturation Curves | Overlaid line chart (% of steady state, x=weeks since open) | "Store Ramp-Up" |
| Cannibalization | Before/after bar pairs with Huff prediction markers | "Cannibalization: Model vs Reality" |
| DOW Heatmap | Color-coded heatmap (stores × days) | "Weekly Rhythm" |
| Revenue Composition | Stacked bar (orders, cups/order, AOV) | "Revenue Breakdown" |
| Rent Efficiency | Scatter plot (cups/day vs rent, bubble=sqft) | "Rent Value Map" |
| Cohort Analysis | Grouped bar chart (cohort × metric) | "Cohort Performance" |

---

## Data Gaps and Caveats

1. **16th & 6th (US00012)**: Only 15 days of data — excluded from seasonality, DOW, and maturation analysis. Flagged as "insufficient for trend analysis"
2. **52nd & Madison (US00027)**: Only 1 full steady-state week in CSV — maturation curve is short
3. **Cannibalization confounders**: Winter dip (Dec-Jan) and spring recovery (Mar-Apr) strongly affect before/after comparisons. Market-adjusted figures partially control for this, but sample sizes are small
4. **Hourly data**: No hourly granularity found in `t_order_item_stat_fact` (only daily cycle_type=5). Peak hour distribution not available without querying `t_order.create_time` directly
5. **Rent data**: Model estimates differ from GL-verified rents for 5 stores. All P&L and efficiency calculations should use GL-verified where available
6. **Revenue composition**: `avg_daily_items` from REVENUE_DATA includes non-cup menu items — cups_per_order (1.27) may slightly overcount actual drink cups
7. **Fleet size effect**: With only 9-12 stores, fleet averages are sensitive to outliers. 8th & Broadway (675 cups) alone shifts fleet metrics significantly

---

## Output Files

| File | Size | Description |
|------|------|-------------|
| `supplementary_data.json` | ~72 KB | All 8 datasets in structured JSON |
| `supplementary_summary.md` | This file | Key findings and recommendations |
| `collect_supplementary_analytics.py` | Script | Reproducible — rerun anytime with updated CSV |
