"""
Layer 2: 12-Module Risk Analysis.
Maps 38 labels to 12 modules, analyzes issue distribution and severity.
"""

import logging

import pandas as pd

from config import (
    DEDUCTION_SEVERITY,
    LABEL_TO_MODULE,
    MODULE_ENGLISH,
    MODULE_ORDER,
    SEVERITY_ORDER,
)

logger = logging.getLogger(__name__)


def analyze_modules(df, layer1_result, total_stores):
    """
    Analyze issues grouped by 12 modules.

    Args:
        df: Full DataFrame for the analysis month (all inspections, not just latest)
        layer1_result: Layer 1 results (for cross-referencing stores)
        total_stores: Total number of unique stores in the month

    Returns:
        dict with layer2 results
    """
    if df.empty:
        return _empty_result()

    # Map labels to modules
    df = df.copy()
    df['module'] = df['label'].map(LABEL_TO_MODULE).fillna('其他')

    # Map deduction types to severity codes
    df['severity'] = df['deduction_type'].map(
        lambda x: DEDUCTION_SEVERITY.get(x, {}).get('code', 'O')
    )

    # Filter to actual issues (deduction_value != 0 or has a non-empty description)
    issues = df[
        (df['deduction_value'].fillna(0) != 0) |
        (df['issue_description'].fillna('').str.strip() != '')
    ].copy()

    if issues.empty:
        return _empty_result()

    # Unmapped labels
    unmapped = df[df['module'] == '其他']['label'].unique().tolist()
    if unmapped:
        logger.warning(f"Unmapped labels (assigned to '其他'): {unmapped}")

    # Per-module analysis
    modules = []
    for module_name in MODULE_ORDER + (['其他'] if '其他' in issues['module'].values else []):
        mod_issues = issues[issues['module'] == module_name]
        if mod_issues.empty:
            continue

        # Severity breakdown
        severity_counts = {}
        for sev in SEVERITY_ORDER:
            count = int((mod_issues['severity'] == sev).sum())
            if count > 0:
                severity_counts[sev] = count

        # Affected stores
        affected_stores = mod_issues['store_serial'].nunique()

        # Total deductions
        total_deductions = float(mod_issues['deduction_value'].fillna(0).sum())

        # Top issues (most frequent issue descriptions)
        top_issues = _get_top_issues(mod_issues, top_n=5)

        # Store-level detail for this module
        store_issues = (
            mod_issues.groupby(['store_serial', 'store_name'])
            .agg(
                issue_count=('deduction_value', 'count'),
                total_deduction=('deduction_value', 'sum'),
            )
            .reset_index()
            .sort_values('total_deduction')
            .to_dict('records')
        )

        modules.append({
            'module_name': module_name,
            'module_name_en': MODULE_ENGLISH.get(module_name, module_name),
            'issue_count': len(mod_issues),
            'affected_store_count': affected_stores,
            'affected_store_pct': round(affected_stores / max(total_stores, 1) * 100, 1),
            'total_deductions': round(total_deductions, 1),
            'severity_breakdown': severity_counts,
            'has_critical': severity_counts.get('S', 0) > 0,
            'is_systemic': affected_stores > total_stores * 0.5,
            'top_issues': top_issues,
            'store_issues': store_issues,
        })

    # Sort by issue count descending
    modules.sort(key=lambda m: m['issue_count'], reverse=True)

    # Rank
    for i, mod in enumerate(modules):
        mod['rank'] = i + 1

    # Cross-reference with Layer 1 stores
    store_module_connection = _connect_to_stores(issues, layer1_result)

    # Identify critical and systemic modules
    critical_modules = [m['module_name'] for m in modules if m['has_critical']]
    systemic_modules = [m['module_name'] for m in modules if m['is_systemic']]

    return {
        'modules': modules,
        'module_ranking': [m['module_name'] for m in modules],
        'critical_modules': critical_modules,
        'systemic_modules': systemic_modules,
        'total_issues': len(issues),
        'unmapped_labels': unmapped,
        'store_module_connection': store_module_connection,
    }


def _get_top_issues(mod_issues, top_n=5):
    """Get the most frequent issue descriptions in a module."""
    descriptions = mod_issues['issue_description'].fillna('').str.strip()
    descriptions = descriptions[descriptions != '']
    if descriptions.empty:
        # Fall back to check_items
        descriptions = mod_issues['check_items'].fillna('').str.strip()
        descriptions = descriptions[descriptions != '']

    if descriptions.empty:
        return []

    counts = descriptions.value_counts().head(top_n)
    result = []
    for desc, count in counts.items():
        stores = mod_issues[
            mod_issues['issue_description'].fillna('').str.strip() == desc
        ]['store_name'].unique().tolist()
        result.append({
            'description': str(desc)[:200],
            'count': int(count),
            'stores': stores[:10],
        })
    return result


def _connect_to_stores(issues, layer1_result):
    """Cross-reference modules back to Layer 1 store results."""
    connection = {
        'lowest_store_modules': [],
        'highest_store_modules': [],
        'most_improved_modules': [],
    }

    if not layer1_result or not layer1_result.get('store_scores'):
        return connection

    # Lowest scoring store: which modules drove the low score?
    lowest = layer1_result.get('lowest_store', {})
    if lowest.get('store_serial'):
        store_issues = issues[issues['store_serial'] == lowest['store_serial']]
        if not store_issues.empty:
            module_deductions = (
                store_issues.groupby('module')['deduction_value']
                .sum()
                .sort_values()
                .reset_index()
            )
            module_deductions.columns = ['module', 'deduction']  # Fix column names after reset
            connection['lowest_store_modules'] = [
                {'module': row['module'], 'deduction': round(float(row['deduction']), 1)}
                for _, row in module_deductions.iterrows()
            ]

    # Highest scoring store: which modules were clean?
    highest = layer1_result.get('highest_store', {})
    if highest.get('store_serial'):
        store_issues = issues[issues['store_serial'] == highest['store_serial']]
        affected_modules = set(store_issues['module'].unique()) if not store_issues.empty else set()
        clean_modules = [m for m in MODULE_ORDER if m not in affected_modules]
        connection['highest_store_modules'] = clean_modules

    # Most improved store
    improved = layer1_result.get('most_improved')
    if improved and improved.get('store_serial'):
        store_issues = issues[issues['store_serial'] == improved['store_serial']]
        if not store_issues.empty:
            connection['most_improved_modules'] = (
                store_issues.groupby('module')['deduction_value']
                .sum()
                .sort_values()
                .reset_index()
                .rename(columns={'deduction_value': 'deduction'})
                .to_dict('records')
            )

    return connection


def _empty_result():
    return {
        'modules': [],
        'module_ranking': [],
        'critical_modules': [],
        'systemic_modules': [],
        'total_issues': 0,
        'unmapped_labels': [],
        'store_module_connection': {
            'lowest_store_modules': [],
            'highest_store_modules': [],
            'most_improved_modules': [],
        },
    }
