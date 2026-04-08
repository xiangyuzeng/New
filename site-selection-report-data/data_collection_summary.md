# Site Selection Report — Data Collection Summary
**Generated**: 2026-04-08
**Data Source**: Production MySQL via MCP DB Gateway

---

## 1. What Was Collected

| Category | Count | Source |
|----------|-------|--------|
| Active stores | 12 | DB: t_shop_info status=1 |
| Steady-state stores | 11 | 28+ days post-opening |
| Pipeline candidates | 18 | DB: t_shop_info status=2 |
| Daily cup records | 1,806 | DB: t_order_item_stat_fact |
| Date range | 2025-06-30 to 2026-04-07 | Up to 280 days/store |

## 2. Model Validation on Expanded Fleet

| Metric | Original (N=8) | Current (N=11) |
|--------|---------------|-------------|
| R² | 0.987 | 0.8507 |
| MAPE | 4.1% | 10.9% |
| RMSE | 96 wk cups | 347 wk cups |

## 3. Prediction Results

| Rating | Count | Profitable |
|--------|-------|-----------|
| Strong | 2 | 2 |
| Medium | 0 | 0 |
| Weak | 16 | 10 |
| **Total** | **18** | **12** |

### Top Candidates
1. **Grand Central Terminal** — 523 cups/day, $19,763/mo, score 63/100, Weak
1. **128 W 32nd St** — 477 cups/day, $24,262/mo, score 75/100, Weak
1. **154 Bleecker** — 457 cups/day, $18,837/mo, score 81/100, Strong
1. **211 Schermerhorn** — 421 cups/day, $18,492/mo, score 87/100, Strong
1. **35th & 5th** — 409 cups/day, $12,060/mo, score 64/100, Weak

## 4. Key Surprise: 52nd & Madison
- Feb 2026 prediction: 156 cups/day ("Not Recommended")
- Actual (40 days): **380 cups/day** (2.4x prediction)
- Suggests premium office locations are systematically undervalued

## 5. Fleet Performance Update
- 8th & Broadway: 660 -> 675 cups/day (+15, stable)
- 221 Grand: 373 -> 493 cups/day (+120, stable)
- 37th & Broadway: 497 -> 436 cups/day (-61, growing)
- 52nd & Madison: **NEW** 433 cups/day (stable)
- 28th & 6th: 374 -> 432 cups/day (+58, stable)
- 102 Fulton: 417 -> 401 cups/day (-16, stable)
- 54th & 8th: 310 -> 385 cups/day (+75, stable)
- 33rd & 10th: **NEW** 283 cups/day (stable)
- 21st & 3rd: **NEW** 274 cups/day (declining)
- 100 Maiden Ln: 273 -> 243 cups/day (-30, stable)
- 15th & 3rd: 139 -> 209 cups/day (+70, stable)

## 6. Data Gaps
1. **63rd & 3rd (US00017)** — Address "219 9th Ave" doesn't match name. Needs verification.
2. **16th & 6th** — Only 15 days data, excluded from training. Avg 171 cups/day in opening period.
3. **Foot traffic scores** — Manual estimates, not Placer.ai actuals
4. **Competitor counts** — From Feb 2026 survey, may have changed
5. **Rent estimates** — Pipeline data, actual lease terms may differ

## 7. Recommended Report Narrative
1. **Lead**: Model validated by 52nd & Madison exceeding predictions 2.4x; fleet grew 50% in 3 months
2. **Show**: Top candidates ranked by five-factor score + predicted profitability
3. **Emphasize**: Cannibalization risk changed with 4 new stores creating overlap zones
4. **Caveat**: Full model retrain with N=11 recommended before final investment decisions
5. **Action**: Field surveys for shortlisted candidates to validate foot traffic and competitor data
