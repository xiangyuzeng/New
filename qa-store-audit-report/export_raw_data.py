#!/usr/bin/env python3
"""Export raw and intermediate data as CSV files for external analysis."""

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'analyze'))
from config import LABEL_TO_MODULE, DEDUCTION_SEVERITY, MODULE_ORDER

INPUT_EXCEL = 'sample-data/test_qa_data.xlsx'
JSON_FILE = 'output/qa_analysis_results_2026-03.json'
OUTPUT_DIR = 'output/raw-data'

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Raw Excel → CSV (full data, Claude web friendly)
print("Exporting raw inspection data as CSV...")
df = pd.read_excel(INPUT_EXCEL, engine='openpyxl')
df.to_csv(f'{OUTPUT_DIR}/raw_inspection_data.csv', index=False, encoding='utf-8-sig')
print(f"  {len(df)} rows → raw_inspection_data.csv")

# 2. Enriched data with module mapping and severity codes
print("Exporting enriched data with module/severity mapping...")
enriched = df.copy()
enriched['Module_CN'] = enriched['Label'].map(LABEL_TO_MODULE).fillna('其他')
enriched['Severity_Code'] = enriched['Deduction type'].map(
    lambda x: DEDUCTION_SEVERITY.get(x, {}).get('code', 'O')
)
enriched['Severity_CN'] = enriched['Deduction type'].map(
    lambda x: DEDUCTION_SEVERITY.get(x, {}).get('label_cn', '其他')
)
enriched['Severity_Level'] = enriched['Deduction type'].map(
    lambda x: DEDUCTION_SEVERITY.get(x, {}).get('level', '其他')
)
enriched['Month'] = pd.to_datetime(enriched['Check date']).dt.strftime('%Y-%m')
enriched.to_csv(f'{OUTPUT_DIR}/enriched_inspection_data.csv', index=False, encoding='utf-8-sig')
print(f"  {len(enriched)} rows → enriched_inspection_data.csv")

# 3. Store scores per month
print("Exporting store scores...")
scores = enriched.drop_duplicates(subset=['Checklist number'])[
    ['Month', 'Store serial number', 'Store name', 'City',
     'Operational Management Area', 'Store level', 'Report score',
     'Check date', 'Check category', 'checker']
].sort_values(['Month', 'Store serial number', 'Check date'])
scores.to_csv(f'{OUTPUT_DIR}/store_inspection_scores.csv', index=False, encoding='utf-8-sig')
print(f"  {len(scores)} inspections → store_inspection_scores.csv")

# 4. Issues only (deduction != 0)
print("Exporting issues (deductions only)...")
issues = enriched[enriched['Opportunity point value'] != 0].copy()
issues_export = issues[[
    'Month', 'Store serial number', 'Store name', 'City',
    'Module_CN', 'Severity_Code', 'Severity_CN',
    'Label', 'Check items', 'Opportunity point description',
    'Opportunity point value', 'Check date', 'checker'
]].sort_values(['Month', 'Module_CN', 'Severity_Code'])
issues_export.to_csv(f'{OUTPUT_DIR}/issues_deductions_only.csv', index=False, encoding='utf-8-sig')
print(f"  {len(issues_export)} issues → issues_deductions_only.csv")

# 5. Module summary pivot
print("Exporting module summary pivot...")
current = enriched[enriched['Month'] == '2026-03']
current_issues = current[current['Opportunity point value'] != 0]

module_summary = current_issues.groupby('Module_CN').agg(
    issue_count=('Opportunity point value', 'count'),
    total_deduction=('Opportunity point value', 'sum'),
    affected_stores=('Store serial number', 'nunique'),
    S_count=('Severity_Code', lambda x: (x == 'S').sum()),
    M_count=('Severity_Code', lambda x: (x == 'M').sum()),
    G_count=('Severity_Code', lambda x: (x == 'G').sum()),
    L_count=('Severity_Code', lambda x: (x == 'L').sum()),
).reset_index()
module_summary = module_summary.sort_values('issue_count', ascending=False)
module_summary.to_csv(f'{OUTPUT_DIR}/module_summary_2026-03.csv', index=False, encoding='utf-8-sig')
print(f"  {len(module_summary)} modules → module_summary_2026-03.csv")

# 6. Store × Module cross-tab (deduction matrix)
print("Exporting store-module cross-tab...")
cross = current_issues.pivot_table(
    index='Store name',
    columns='Module_CN',
    values='Opportunity point value',
    aggfunc='sum',
    fill_value=0
)
# Reorder columns to MODULE_ORDER
ordered_cols = [m for m in MODULE_ORDER if m in cross.columns]
remaining = [c for c in cross.columns if c not in ordered_cols]
cross = cross[ordered_cols + remaining]
cross['Total_Deduction'] = cross.sum(axis=1)
cross = cross.sort_values('Total_Deduction')
cross.to_csv(f'{OUTPUT_DIR}/store_module_crosstab_2026-03.csv', encoding='utf-8-sig')
print(f"  {cross.shape[0]} stores × {cross.shape[1]} cols → store_module_crosstab_2026-03.csv")

# 7. Severity distribution detail
print("Exporting severity distribution...")
sev_detail = current_issues.groupby(['Severity_Code', 'Severity_CN', 'Module_CN']).agg(
    count=('Opportunity point value', 'count'),
    total_deduction=('Opportunity point value', 'sum'),
    stores_affected=('Store serial number', 'nunique'),
).reset_index().sort_values(['Severity_Code', 'count'], ascending=[True, False])
sev_detail.to_csv(f'{OUTPUT_DIR}/severity_by_module_2026-03.csv', index=False, encoding='utf-8-sig')
print(f"  {len(sev_detail)} rows → severity_by_module_2026-03.csv")

# 8. S-items detail (critical items)
print("Exporting S-items detail...")
s_items = current_issues[current_issues['Severity_Code'] == 'S'][[
    'Store name', 'Store serial number', 'Module_CN', 'Label',
    'Check items', 'Opportunity point description',
    'Opportunity point value', 'Check date', 'checker'
]]
s_items.to_csv(f'{OUTPUT_DIR}/critical_s_items_2026-03.csv', index=False, encoding='utf-8-sig')
print(f"  {len(s_items)} S-items → critical_s_items_2026-03.csv")

# 9. Month-over-month store comparison
print("Exporting month-over-month comparison...")
feb = enriched[enriched['Month'] == '2026-02'].drop_duplicates('Checklist number')
mar = enriched[enriched['Month'] == '2026-03'].drop_duplicates('Checklist number')

feb_scores = feb.groupby(['Store serial number', 'Store name']).agg(
    feb_latest_score=('Report score', 'last'),
    feb_inspections=('Checklist number', 'nunique'),
).reset_index()

mar_scores = mar.groupby(['Store serial number', 'Store name']).agg(
    mar_latest_score=('Report score', 'last'),
    mar_inspections=('Checklist number', 'nunique'),
).reset_index()

comparison = feb_scores.merge(mar_scores, on=['Store serial number', 'Store name'], how='outer')
comparison['score_change'] = comparison['mar_latest_score'] - comparison['feb_latest_score']
comparison = comparison.sort_values('score_change', ascending=True)
comparison.to_csv(f'{OUTPUT_DIR}/month_over_month_comparison.csv', index=False, encoding='utf-8-sig')
print(f"  {len(comparison)} stores → month_over_month_comparison.csv")

# 10. Label mapping reference
print("Exporting label mapping reference...")
labels_in_data = enriched['Label'].unique()
label_ref = pd.DataFrame([
    {'Label': label, 'Module_CN': LABEL_TO_MODULE.get(label, '(unmapped)'), 'In_Data': label in labels_in_data}
    for label in sorted(set(list(LABEL_TO_MODULE.keys()) + list(labels_in_data)))
])
label_ref.to_csv(f'{OUTPUT_DIR}/label_module_mapping_reference.csv', index=False, encoding='utf-8-sig')
print(f"  {len(label_ref)} labels → label_module_mapping_reference.csv")

print(f"\nDone! {len(os.listdir(OUTPUT_DIR))} files exported to {OUTPUT_DIR}/")
