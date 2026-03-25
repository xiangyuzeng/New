#!/usr/bin/env python3
"""
QA Store Audit Monthly Analysis — Python CLI Entry Point.
Reads Excel input, runs 4 analysis layers, outputs JSON + CSV.

Usage:
    python3 run_analysis.py --input data.xlsx [--month 2026-03] [--output-dir output]
    python3 run_analysis.py --input data.xlsx --discover-labels
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LABEL_TO_MODULE, REPORT_AUTHOR
from layer1_store_performance import analyze_store_performance
from layer2_module_analysis import analyze_modules
from layer3_risk_level import analyze_risk_levels
from layer4_capa_attribution import analyze_capa
from utils import (
    export_summary_csv,
    filter_by_month,
    get_analysis_month,
    normalize_columns,
    parse_date_column,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


def find_input_file():
    """Search for QA Excel files in common locations."""
    search_dirs = [
        Path('/app/qa-store-audit-report'),
        Path('/app'),
        Path('/mnt/user-data/uploads'),
    ]
    patterns = ['*opportunity_points*.xlsx', '*Check_the_report*.xlsx', '*QA*.xlsx']

    for d in search_dirs:
        if not d.exists():
            continue
        for pattern in patterns:
            matches = list(d.glob(pattern))
            if matches:
                # Return the most recently modified file
                matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                return str(matches[0])

    return None


def discover_labels(df):
    """Print all unique Label values for mapping verification."""
    if 'label' not in df.columns:
        print("ERROR: 'label' column not found in data")
        return

    labels = df['label'].dropna().unique()
    labels.sort()

    print(f"\n{'='*60}")
    print(f"UNIQUE LABEL VALUES ({len(labels)} found)")
    print(f"{'='*60}\n")

    mapped = 0
    unmapped = 0
    for label in labels:
        module = LABEL_TO_MODULE.get(label)
        if module:
            print(f"  [MAPPED]   {label!r:55s} → {module}")
            mapped += 1
        else:
            print(f"  [UNMAPPED] {label!r}")
            unmapped += 1

    print(f"\n{'='*60}")
    print(f"Mapped: {mapped}, Unmapped: {unmapped}, Total: {len(labels)}")
    print(f"{'='*60}\n")


def read_excel(input_path):
    """Read and normalize the Excel input."""
    logger.info(f"Reading Excel file: {input_path}")
    df = pd.read_excel(input_path, engine='openpyxl')
    logger.info(f"Raw data: {len(df)} rows, {len(df.columns)} columns")

    df = normalize_columns(df)

    # Parse dates
    if 'check_date' in df.columns:
        df['check_date'] = parse_date_column(df['check_date'])

    # Ensure numeric columns
    if 'deduction_value' in df.columns:
        df['deduction_value'] = pd.to_numeric(df['deduction_value'], errors='coerce').fillna(0)
    if 'report_score' in df.columns:
        df['report_score'] = pd.to_numeric(df['report_score'], errors='coerce')

    return df


def run_analysis(df, analysis_month_tuple, prior_month_tuple):
    """Run all 4 analysis layers."""
    year, month = analysis_month_tuple

    logger.info(f"Running analysis for {year}-{month:02d}")

    # Current month data (all inspections)
    current_month_df = filter_by_month(df, year, month)
    total_stores = current_month_df['store_serial'].nunique() if 'store_serial' in current_month_df.columns else 0
    total_inspections = current_month_df['checklist_number'].nunique() if 'checklist_number' in current_month_df.columns else 0

    logger.info(f"Current month: {len(current_month_df)} rows, {total_stores} stores, {total_inspections} inspections")

    # Layer 1: Store Performance
    logger.info("Running Layer 1: Store Performance...")
    layer1 = analyze_store_performance(df, analysis_month_tuple, prior_month_tuple)

    # Layer 2: Module Analysis
    logger.info("Running Layer 2: Module Analysis...")
    layer2 = analyze_modules(current_month_df, layer1, total_stores)

    # Layer 3: Risk Level
    logger.info("Running Layer 3: Risk Level...")
    layer3 = analyze_risk_levels(current_month_df)

    # Layer 4: CAPA Attribution
    logger.info("Running Layer 4: CAPA Attribution...")
    layer4 = analyze_capa(current_month_df)

    # Check prior month existence
    prior_year, prior_month_num = prior_month_tuple
    prior_df = filter_by_month(df, prior_year, prior_month_num)
    has_prior = not prior_df.empty

    # Assemble results
    results = {
        'metadata': {
            'schema_version': '1.0',
            'analysis_month': f"{year}-{month:02d}",
            'analysis_month_cn': f"{year}年{month:02d}月",
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'prior_month': f"{prior_year}-{prior_month_num:02d}",
            'has_prior_month': has_prior,
            'total_inspections': total_inspections,
            'total_stores': total_stores,
            'total_rows': len(current_month_df),
            'date_range': {
                'start': str(current_month_df['check_date'].min())[:10] if not current_month_df.empty else '',
                'end': str(current_month_df['check_date'].max())[:10] if not current_month_df.empty else '',
            },
            'report_id': f"LCNA-QA-{year}-{month:03d}",
            'author': REPORT_AUTHOR,
        },
        'layer1_store_performance': layer1,
        'layer2_module_analysis': layer2,
        'layer3_risk_analysis': layer3,
        'layer4_capa': layer4,
    }

    return results


def main():
    parser = argparse.ArgumentParser(
        description='QA Store Audit Monthly Analysis — reads Excel, outputs JSON+CSV'
    )
    parser.add_argument('--input', '-i', help='Path to Excel file (.xlsx)')
    parser.add_argument('--month', '-m', help='Analysis month YYYY-MM (auto-detect if omitted)')
    parser.add_argument('--output-dir', '-o', default=None, help='Output directory (default: ../output)')
    parser.add_argument('--discover-labels', action='store_true', help='Print all unique Label values and exit')

    args = parser.parse_args()

    # Resolve input file
    input_path = args.input or find_input_file()
    if not input_path:
        logger.error(
            "No input file specified and none found automatically.\n"
            "Usage: python3 run_analysis.py --input <path_to_excel.xlsx>"
        )
        sys.exit(1)

    if not os.path.exists(input_path):
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    # Resolve output directory
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    output_dir = Path(args.output_dir) if args.output_dir else script_dir.parent / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read data
    df = read_excel(input_path)

    # Discover labels mode
    if args.discover_labels:
        discover_labels(df)
        sys.exit(0)

    # Determine analysis month
    analysis_month, prior_month = get_analysis_month(df, args.month)
    year, month = analysis_month

    # Run analysis
    results = run_analysis(df, analysis_month, prior_month)

    # Write JSON
    json_path = output_dir / f"qa_analysis_results_{year}-{month:02d}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"JSON results written to {json_path}")

    # Write CSV summary
    csv_path = output_dir / f"qa_summary_{year}-{month:02d}.csv"
    export_summary_csv(results, str(csv_path))

    print(f"\nAnalysis complete for {year}-{month:02d}")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")
    print(f"  Stores: {results['metadata']['total_stores']}")
    print(f"  Inspections: {results['metadata']['total_inspections']}")
    print(f"  Average score: {results['layer1_store_performance']['monthly_average']}")
    print(f"  Total issues: {results['layer2_module_analysis']['total_issues']}")


if __name__ == '__main__':
    main()
