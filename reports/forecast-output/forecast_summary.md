# Pipeline Candidate Forecast & Performance Analytics
**Generated**: 2026-04-09 17:51
**Model**: v2.0 Lasso (R^2=0.985, MAPE=2.6%, RMSE=110 weekly)
**Candidates**: 18 pipeline locations
**Forecast Period**: 12 weeks per scenario, Apr-Dec 2026 opening months

---

## Key Findings

### Seasonal Impact
- **Summer peak** (Jul): seasonal index ~1.353
- **Winter trough** (Dec-Jan): seasonal index ~0.889-0.866
- **Spring recovery** (Apr-Jun): extrapolated indices 1.06-1.26
- Opening month choice can swing first-month revenue by 2x+ for the same location

### Maturation Pattern
- Fleet average opening week: ~134% of steady state
- Trough at week 2: ~118% of steady state
- Steady state reached by week 4.5

### Top Candidates by Opening Timing

| Candidate | Steady State | Best Month | Best 1st Mo Profit | Worst Month | Worst 1st Mo Profit | Swing |
|-----------|-------------|------------|-------------------|------------|--------------------|----|
| Grand Central Terminal | 534 | 07 | $13,685 | 12 | $-5,764 | $19,449 |
| 211 Schermerhorn | 476 | 07 | $18,513 | 12 | $1,201 | $17,313 |
| 154 Bleecker | 423 | 07 | $8,911 | 12 | $-6,518 | $15,429 |
| 128 W 32nd St | 415 | 07 | $11,041 | 12 | $-4,040 | $15,081 |
| 35th & 5th | 371 | 07 | $2,357 | 12 | $-11,110 | $13,467 |
| 41st & Lexington | 346 | 07 | $1,730 | 12 | $-10,883 | $12,613 |

### Risk Flags

- **Grand Central Terminal**: confidence=high (76.0/100) 
  - v1 underestimated 52nd & Madison (premium office) by 2.8x. v2 still has 8.1% error. Premium office candidates may have upside not captured by the model.
- **211 Schermerhorn**: confidence=medium (73.0/100) OUT-OF-SAMPLE
  - Brooklyn/LIC location -- all training data is Manhattan. Store profile may differ from model assumptions.
- **154 Bleecker**: confidence=medium (72.0/100) 
- **128 W 32nd St**: confidence=medium (70.0/100) 
- **35th & 5th**: confidence=medium (69.0/100) 
  - v1 underestimated 52nd & Madison (premium office) by 2.8x. v2 still has 8.1% error. Premium office candidates may have upside not captured by the model.
- **41st & Lexington**: confidence=medium (71.0/100) 
  - v1 underestimated 52nd & Madison (premium office) by 2.8x. v2 still has 8.1% error. Premium office candidates may have upside not captured by the model.

### Fleet Benchmark Context
- Fleet median daily cups: 401
- Fleet p75: 434
- Profitable stores: 2/11

### Price Sensitivity (Top Candidates)

At $4.20/cup (vs current $3.65), most top candidates become first-month profitable in summer:

**Grand Central Terminal** (rent $25,000):
  - $3.65/cup, Apr: first month $2,247
  - $3.65/cup, Jul: first month $14,760
  - $3.65/cup, Dec: first month $-5,058
  - $4.2/cup, Apr: first month $13,822
  - $4.2/cup, Jul: first month $29,536
  - $4.2/cup, Dec: first month $4,648
  - $4.5/cup, Apr: first month $20,135
  - $4.5/cup, Jul: first month $37,595
  - $4.5/cup, Dec: first month $9,942
**211 Schermerhorn** (rent $14,000):
  - $3.65/cup, Apr: first month $8,345
  - $3.65/cup, Jul: first month $19,471
  - $3.65/cup, Dec: first month $1,830
  - $4.2/cup, Apr: first month $18,666
  - $4.2/cup, Jul: first month $32,638
  - $4.2/cup, Dec: first month $10,484
  - $4.5/cup, Apr: first month $24,295
  - $4.5/cup, Jul: first month $39,820
  - $4.5/cup, Dec: first month $15,205
**154 Bleecker** (rent $18,000):
  - $3.65/cup, Apr: first month $-154
  - $3.65/cup, Jul: first month $9,763
  - $3.65/cup, Dec: first month $-5,959
  - $4.2/cup, Apr: first month $9,016
  - $4.2/cup, Jul: first month $21,470
  - $4.2/cup, Dec: first month $1,726
  - $4.5/cup, Apr: first month $14,018
  - $4.5/cup, Jul: first month $27,855
  - $4.5/cup, Dec: first month $5,918

---

## Methodology

```
forecast_daily = predicted_steady_state × seasonal_index × maturation_pct
forecast_weekly = forecast_daily × 7
80% CI = forecast ± 1.28 × CV × forecast
P&L = (cups × rev_per_cup) - (cups × COGS) - labor - rent - other
```

- Seasonal indices: fleet median of per-store monthly avg / annual mean
- Maturation: fleet average opening ramp (week 0-12 vs weeks 5+ steady state)
- Revenue per cup: area-type-specific (commuter/balanced/tourist), NOT flat $3.65
- COGS: $1.50/cup | Labor: $15K/mo | Other: $3K/mo | Rent: store-specific
- Apr-Jun 2026 seasonal indices are EXTRAPOLATED (flagged in data)
- Jul-Dec 2026 seasonal indices repeat Jul-Dec 2025 (9 months of fleet data)
- Brooklyn/LIC candidates flagged as out-of-sample (all training data is Manhattan)

## Output Files

| File | Description |
|------|-------------|
| `fleet_patterns.json` | Seasonality, maturation, DOW, revenue benchmarks, variance |
| `candidate_forecasts.json` | 12-week forecasts + opening timing matrix |
| `comparable_analysis.json` | Analog store comparisons |
| `cumulative_pnl.json` | 6-month P&L at 3 opening scenarios |
| `risk_metrics.json` | Risk-adjusted confidence scores |
| `fleet_benchmarks.json` | Fleet percentiles and context |
| `sensitivity_scenarios.json` | Price × timing sensitivity + rent targets |
| `forecast_pipeline.py` | Reproducible script |
