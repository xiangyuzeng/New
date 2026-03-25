"""
Layer 4: CAPA & Attribution (placeholder).
Keyword-based best-effort attribution from issue descriptions.
"""

import logging
import re

import pandas as pd

from config import ATTRIBUTION_KEYWORDS, LABEL_TO_MODULE, SLA_STANDARDS

logger = logging.getLogger(__name__)


def analyze_capa(df):
    """
    Best-effort CAPA analysis from available data.

    Since CAPA tracking fields are not in the current export, this provides:
    - Template structure for when data becomes available
    - Keyword-based attribution from 'Opportunity point description'
    - SLA standards reference

    Args:
        df: Full DataFrame for the analysis month

    Returns:
        dict with layer4 results
    """
    missing_fields = [
        '责任归属（门店/机修/营建）',
        '整改责任人',
        '整改措施描述',
        '整改完成时间',
        '验证结果（通过/未通过）',
        '验证人',
        'SLA达标状态',
    ]

    template_structure = {
        'columns': missing_fields,
        'sla_standards': {
            sev: info for sev, info in SLA_STANDARDS.items()
        },
        'workflow': [
            '1. 巡检发现问题 → 系统自动生成整改工单',
            '2. 根据问题类型自动分配责任方（门店/机修/营建）',
            '3. 责任方在SLA时限内完成整改',
            '4. QA复核验证整改效果',
            '5. 系统记录闭环时间，计算SLA达标率',
        ],
    }

    # Keyword-based attribution
    attribution = _keyword_attribution(df)

    return {
        'data_available': False,
        'missing_fields': missing_fields,
        'template_structure': template_structure,
        'keyword_attribution': attribution,
        'disclaimer': '基于关键词的初步归因（仅供参考）— 实际归因需以整改工单系统数据为准',
    }


def _keyword_attribution(df):
    """Scan issue descriptions for attribution keywords."""
    if df.empty or 'issue_description' not in df.columns:
        return {'summary': {}, 'details': []}

    descriptions = df['issue_description'].fillna('').str.strip()
    descriptions = descriptions[descriptions != '']

    if descriptions.empty:
        return {'summary': {}, 'details': []}

    summary = {}
    details = []

    for category, keywords in ATTRIBUTION_KEYWORDS.items():
        pattern = '|'.join(re.escape(kw) for kw in keywords)
        matches = descriptions.str.contains(pattern, case=False, na=False)
        count = int(matches.sum())
        if count > 0:
            summary[category] = count
            # Get sample matched descriptions
            matched_rows = df[
                df['issue_description'].fillna('').str.contains(
                    pattern, case=False, na=False
                )
            ]
            samples = []
            for _, row in matched_rows.head(5).iterrows():
                samples.append({
                    'store_name': str(row.get('store_name', '')),
                    'module': LABEL_TO_MODULE.get(str(row.get('label', '')), '其他'),
                    'description': str(row.get('issue_description', ''))[:150],
                })
            details.append({
                'category': category,
                'count': count,
                'matched_keywords': [kw for kw in keywords if descriptions.str.contains(re.escape(kw), case=False, na=False).any()],
                'samples': samples,
            })

    return {
        'summary': summary,
        'details': details,
        'total_analyzed': len(descriptions),
        'total_attributed': sum(summary.values()),
        'attribution_rate': round(
            sum(summary.values()) / max(len(descriptions), 1) * 100, 1
        ),
    }
