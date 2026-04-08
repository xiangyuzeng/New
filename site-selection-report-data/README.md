# Site Selection Report Data — Luckin Coffee USA

**Generated**: 2026-04-08
**Purpose**: Structured data files for management report compilation

## File Manifest

| File | Phase | Contents |
|------|-------|----------|
| `active_stores_performance.json` | Phase 1 | 12 active stores with steady-state cup metrics, trends, revenue |
| `pipeline_candidates.json` | Phase 2 | 18 pipeline candidates with feature completeness |
| `candidate_features.json` | Phase 3 | 10 model features per candidate with source attribution |
| `candidate_predictions.json` | Phase 4 | Predictions, 5-factor scores, P&L, risk ratings |
| `model_validation.json` | Phase 5 | Model validation on expanded fleet |
| `model_artifacts_v2.json` | Phase 4 | Model coefficients, scaler, metrics |
| `data_collection_summary.md` | Phase 6 | Human-readable summary for report |
| `raw_daily_cups.csv` | Raw | 1,806 daily cup records from production DB |
| `process_all_phases.py` | Script | Pipeline script (reproducible) |

## Data Sources

- **Production MySQL**: `luckyus_sales_order.t_order_item_stat_fact` (daily cups)
- **Store Registry**: `luckyus_opshop.t_shop_info` (store metadata)
- **Revenue**: `luckyus_sales_order.t_income_summary` (financials)
- **Model**: `/app/site-selection-platform/ml_output/model_artifacts.json` (Lasso v1)
- **Pipeline enrichment**: `/app/site-selection-platform/data/pipeline_locations_scored.csv`

## Key Numbers

- **12 active stores** (was 8 in Feb 2026 report)
- **11 training-eligible** (16th & 6th excluded: only 15 days)
- **18 pipeline candidates** (17 original + 1 new)
- **2 Strong, 1 Medium, 15 Weak** candidates by risk rating
- **Model R² = 0.851** on expanded fleet (was 0.987 on original 8)
- **Fleet avg: ~402 cups/day**, breakeven ~260 cups/day at avg rent

## Usage

These files are designed to be uploaded to Claude web for management report compilation (docx/pptx).
