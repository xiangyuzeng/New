"""
Layer 3: Risk Level Analysis.
S/M/G/L severity distribution with detailed S-item listing.
"""

import logging

import pandas as pd

from config import DEDUCTION_SEVERITY, LABEL_TO_MODULE, SEVERITY_ORDER

logger = logging.getLogger(__name__)


def analyze_risk_levels(df):
    """
    Analyze overall severity distribution.

    Args:
        df: Full DataFrame for the analysis month (all inspections)

    Returns:
        dict with layer3 results
    """
    if df.empty:
        return _empty_result()

    df = df.copy()

    # Map severity
    df['severity'] = df['deduction_type'].map(
        lambda x: DEDUCTION_SEVERITY.get(x, {}).get('code', 'O')
    )
    df['module'] = df['label'].map(LABEL_TO_MODULE).fillna('其他')

    # Filter to actual issues (deduction_value != 0 or has description)
    issues = df[
        (df['deduction_value'].fillna(0) != 0) |
        (df['issue_description'].fillna('').str.strip() != '')
    ].copy()

    if issues.empty:
        return _empty_result()

    # Overall distribution
    distribution = {}
    percentages = {}
    total = len(issues)

    for sev in SEVERITY_ORDER:
        count = int((issues['severity'] == sev).sum())
        distribution[sev] = count
        percentages[sev] = round(count / max(total, 1) * 100, 1)

    # S-items: list individually
    s_items = issues[issues['severity'] == 'S']
    s_items_detail = []
    for _, row in s_items.iterrows():
        s_items_detail.append({
            'store_name': str(row.get('store_name', '')),
            'store_serial': str(row.get('store_serial', '')),
            'module': str(row.get('module', '')),
            'label': str(row.get('label', '')),
            'check_item': str(row.get('check_items', ''))[:200],
            'description': str(row.get('issue_description', ''))[:200],
            'deduction': float(row.get('deduction_value', 0)),
            'check_date': str(row.get('check_date', '')),
            'checker': str(row.get('checker', '')),
        })

    # M-items: top modules
    m_items = issues[issues['severity'] == 'M']
    m_top_modules = (
        m_items.groupby('module').size()
        .sort_values(ascending=False)
        .head(5)
        .to_dict()
    ) if not m_items.empty else {}

    # G-items: top modules
    g_items = issues[issues['severity'] == 'G']
    g_top_modules = (
        g_items.groupby('module').size()
        .sort_values(ascending=False)
        .head(5)
        .to_dict()
    ) if not g_items.empty else {}

    # L-items: top modules
    l_items = issues[issues['severity'] == 'L']
    l_top_modules = (
        l_items.groupby('module').size()
        .sort_values(ascending=False)
        .head(5)
        .to_dict()
    ) if not l_items.empty else {}

    return {
        'severity_distribution': distribution,
        'severity_percentages': percentages,
        'total_issues': total,
        's_items_count': distribution.get('S', 0),
        's_items_detail': s_items_detail,
        'm_top_modules': m_top_modules,
        'g_top_modules': g_top_modules,
        'l_top_modules': l_top_modules,
    }


def _empty_result():
    return {
        'severity_distribution': {s: 0 for s in SEVERITY_ORDER},
        'severity_percentages': {s: 0.0 for s in SEVERITY_ORDER},
        'total_issues': 0,
        's_items_count': 0,
        's_items_detail': [],
        'm_top_modules': {},
        'g_top_modules': {},
        'l_top_modules': {},
    }
