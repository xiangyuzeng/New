#!/usr/bin/env bash
#
# QA Store Audit Monthly Analysis Report — Pipeline Runner
#
# Usage:
#   bash run.sh <excel_file.xlsx> [YYYY-MM]
#
# Arguments:
#   $1  Path to the QA inspection Excel file (.xlsx)
#   $2  Analysis month in YYYY-MM format (optional; auto-detects latest month)
#
# Output:
#   output/qa_analysis_results_YYYY-MM.json   — Analysis data (JSON)
#   output/qa_summary_YYYY-MM.csv             — Summary metrics (CSV)
#   output/QA门店巡检月度分析报告_YYYY年MM月.docx  — Final report (DOCX)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT_FILE="${1:-}"
MONTH="${2:-}"
OUTPUT_DIR="${SCRIPT_DIR}/output"

if [ -z "$INPUT_FILE" ]; then
    echo "Usage: bash run.sh <excel_file.xlsx> [YYYY-MM]"
    echo ""
    echo "  excel_file.xlsx  Path to the QA inspection data Excel file"
    echo "  YYYY-MM          Analysis month (optional, auto-detects latest month)"
    exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo "ERROR: Input file not found: $INPUT_FILE"
    exit 1
fi

echo "============================================"
echo "QA Store Audit Monthly Analysis Report"
echo "============================================"
echo "Input:  $INPUT_FILE"
echo "Month:  ${MONTH:-auto-detect}"
echo "Output: $OUTPUT_DIR/"
echo ""

# Step 0: Install dependencies
echo "=== Step 0: Installing dependencies ==="
pip3 install --break-system-packages -q pandas openpyxl 2>/dev/null || pip3 install -q pandas openpyxl 2>/dev/null || pip install -q pandas openpyxl
cd "${SCRIPT_DIR}/generate-docx" && npm install --silent 2>/dev/null
cd "${SCRIPT_DIR}"
echo "  Dependencies ready."
echo ""

# Step 1: Python analysis
echo "=== Step 1: Running Python analysis ==="
PYTHON_ARGS="--output-dir ${OUTPUT_DIR}"
[ -n "$INPUT_FILE" ] && PYTHON_ARGS="--input $INPUT_FILE $PYTHON_ARGS"
[ -n "$MONTH" ] && PYTHON_ARGS="--month $MONTH $PYTHON_ARGS"

python3 analyze/run_analysis.py $PYTHON_ARGS
echo ""

# Find the generated JSON
JSON_FILE=$(ls -t "${OUTPUT_DIR}"/qa_analysis_results_*.json 2>/dev/null | head -1)
if [ -z "$JSON_FILE" ]; then
    echo "ERROR: No analysis JSON found in ${OUTPUT_DIR}/"
    exit 1
fi
echo "  JSON output: $JSON_FILE"

# Step 2: Node.js DOCX generation
echo ""
echo "=== Step 2: Generating DOCX report ==="
node generate-docx/generate_report.js "$JSON_FILE" "$OUTPUT_DIR"
echo ""

# Summary
echo "============================================"
echo "Pipeline complete!"
echo "============================================"
echo ""
echo "Output files:"
ls -la "${OUTPUT_DIR}"/*.json 2>/dev/null || true
ls -la "${OUTPUT_DIR}"/*.csv 2>/dev/null || true
ls -la "${OUTPUT_DIR}"/*.docx 2>/dev/null || true
echo ""
echo "Done."
