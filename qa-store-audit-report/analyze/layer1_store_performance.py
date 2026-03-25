"""
Layer 1: Store Overall Performance Analysis.
Per-store scoring, trends, comparisons.
"""

import logging

import pandas as pd

from utils import (
    detect_anomalous_scores,
    filter_by_month,
    get_latest_inspection_per_store,
)

logger = logging.getLogger(__name__)


def analyze_store_performance(df, analysis_month, prior_month):
    """
    Analyze store-level performance for the analysis month.

    Args:
        df: Full normalized DataFrame (all months)
        analysis_month: (year, month) tuple
        prior_month: (year, month) tuple

    Returns:
        dict with layer1 results
    """
    year, month = analysis_month
    prior_year, prior_month_num = prior_month

    # Filter to current month
    current_df = filter_by_month(df, year, month)
    if current_df.empty:
        logger.warning(f"No data found for {year}-{month:02d}")
        return _empty_result()

    # Get latest inspection per store, split clean vs anomalous
    latest = get_latest_inspection_per_store(current_df)
    clean, anomalous = detect_anomalous_scores(latest)

    # Build anomalous scores list
    anomalous_list = []
    for _, row in anomalous.iterrows():
        anomalous_list.append({
            'store_name': str(row.get('store_name', '')),
            'store_serial': str(row.get('store_serial', '')),
            'score': float(row.get('report_score', 0)),
            'check_date': str(row.get('check_date', '')),
            'check_category': str(row.get('check_category', '')),
        })

    if clean.empty:
        logger.warning("All scores are anomalous — no valid scores for analysis")
        return _empty_result(anomalous_list=anomalous_list)

    # Calculate metrics on clean data
    scores = clean['report_score'].astype(float)
    monthly_avg = round(scores.mean(), 1)

    # Build store scores list
    store_scores = []
    for _, row in clean.sort_values('report_score', ascending=False).iterrows():
        store_scores.append({
            'store_name': str(row.get('store_name', '')),
            'store_serial': str(row.get('store_serial', '')),
            'dept_code': str(row.get('dept_code', '')),
            'city': str(row.get('city', '')),
            'area': str(row.get('area', '')),
            'latest_score': float(row.get('report_score', 0)),
            'store_level': str(row.get('store_level', '')),
            'check_date': str(row.get('check_date', '')),
            'prior_score': None,
            'change': None,
        })

    highest = store_scores[0] if store_scores else None
    lowest = store_scores[-1] if store_scores else None

    result = {
        'monthly_average': monthly_avg,
        'prior_month_average': None,
        'average_trend': None,
        'highest_store': {
            'name': highest['store_name'] if highest else '',
            'score': highest['latest_score'] if highest else 0,
            'store_serial': highest['store_serial'] if highest else '',
        },
        'lowest_store': {
            'name': lowest['store_name'] if lowest else '',
            'score': lowest['latest_score'] if lowest else 0,
            'store_serial': lowest['store_serial'] if lowest else '',
        },
        'most_improved': None,
        'most_declined': None,
        'store_scores': store_scores,
        'anomalous_scores': anomalous_list,
        'total_stores_scored': len(clean),
    }

    # Prior month comparison
    prior_df = filter_by_month(df, prior_year, prior_month_num)
    if not prior_df.empty:
        prior_latest = get_latest_inspection_per_store(prior_df)
        prior_clean, _ = detect_anomalous_scores(prior_latest)

        if not prior_clean.empty:
            prior_scores = prior_clean['report_score'].astype(float)
            prior_avg = round(prior_scores.mean(), 1)
            result['prior_month_average'] = prior_avg
            result['average_trend'] = round(monthly_avg - prior_avg, 1)

            # Build prior score lookup
            prior_lookup = {}
            for _, row in prior_clean.iterrows():
                serial = str(row.get('store_serial', ''))
                prior_lookup[serial] = float(row.get('report_score', 0))

            # Update store_scores with prior data and calculate changes
            best_improvement = None
            worst_decline = None
            for ss in result['store_scores']:
                serial = ss['store_serial']
                if serial in prior_lookup:
                    ss['prior_score'] = prior_lookup[serial]
                    ss['change'] = round(ss['latest_score'] - prior_lookup[serial], 1)

                    if best_improvement is None or ss['change'] > best_improvement['change']:
                        best_improvement = ss
                    if worst_decline is None or ss['change'] < worst_decline['change']:
                        worst_decline = ss

            if best_improvement and best_improvement['change'] > 0:
                result['most_improved'] = {
                    'name': best_improvement['store_name'],
                    'store_serial': best_improvement['store_serial'],
                    'change': best_improvement['change'],
                    'current_score': best_improvement['latest_score'],
                    'prior_score': best_improvement['prior_score'],
                }
            if worst_decline and worst_decline['change'] < 0:
                result['most_declined'] = {
                    'name': worst_decline['store_name'],
                    'store_serial': worst_decline['store_serial'],
                    'change': worst_decline['change'],
                    'current_score': worst_decline['latest_score'],
                    'prior_score': worst_decline['prior_score'],
                }

    return result


def _empty_result(anomalous_list=None):
    return {
        'monthly_average': 0,
        'prior_month_average': None,
        'average_trend': None,
        'highest_store': {'name': '', 'score': 0, 'store_serial': ''},
        'lowest_store': {'name': '', 'score': 0, 'store_serial': ''},
        'most_improved': None,
        'most_declined': None,
        'store_scores': [],
        'anomalous_scores': anomalous_list or [],
        'total_stores_scored': 0,
    }
