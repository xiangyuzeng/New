"""
Configuration constants for QA Store Audit Monthly Analysis.
Label-to-module mapping, severity mapping, color scheme, CAPA keywords.
"""

# ---------------------------------------------------------------------------
# 38 Label values → 12 analysis modules
# ---------------------------------------------------------------------------
LABEL_TO_MODULE = {
    # 1. 设备与工具 (Equipment & Utensils)
    'Equipment and Food Processing Utensils': '设备与工具',
    'Storage/Maintenance of Utensils': '设备与工具',
    'Equipment Inspection and Maintenance': '设备与工具',
    'Facility Inspection and Maintenance': '设备与工具',

    # 2. 清洁消毒 (Cleaning & Disinfection)
    'Procedures for Cleaning and Disinfection': '清洁消毒',
    'Handwashing Standards': '清洁消毒',
    'Disposable Gloves and Blue Bandages': '清洁消毒',

    # 3. 温控管理 (Temperature Control)
    'Devices for Monitoring the Temperatures of All Refrigerators and Freezers': '温控管理',
    'Product Storage Conditions': '温控管理',

    # 4. 储存管理 (Storage Management)
    'Material Storage Location Specification': '储存管理',
    'Storage and Inventory Transfer of Food': '储存管理',
    'Approved Goods': '储存管理',
    'Unqualified Goods': '储存管理',

    # 5. 食品加工区域 (Food Processing Area)
    'Food Processing Area': '食品加工区域',
    'Operation Stand, Shelf, Cabinet and Water Sink': '食品加工区域',
    'Cross Contamination': '食品加工区域',
    'Avoidance of Falling Foreign Objects': '食品加工区域',

    # 6. 水务与管道 (Water & Plumbing)
    'Water Filtration Device': '水务与管道',
    'Water Sinks & Pipes': '水务与管道',
    'Grease traps&Residue traps&Sewer lines': '水务与管道',
    'Potable Water Supply is Adequate': '水务与管道',

    # 7. 虫害防控 (Pest Control)
    'Insect Pest Control Facilities & Suppliers': '虫害防控',
    'No Sign of Insect Pests': '虫害防控',
    'No pests enter': '虫害防控',

    # 8. 有效期管理 (Expiration Management)
    'Expiration Date': '有效期管理',
    'Food': '有效期管理',

    # 9. 人员卫生 (Personal Hygiene)
    'Personal Hygiene': '人员卫生',
    "Employees' Health": '人员卫生',
    'Personal certificate': '人员卫生',

    # 10. 化学品管理 (Chemical Management)
    'Chemical Mark/Storage': '化学品管理',

    # 11. 环境与客区 (Environment & Customer Area)
    'Customer Area': '环境与客区',
    'Trash Cans': '环境与客区',
    'Lights': '环境与客区',
    'Workplace Safety': '环境与客区',

    # 12. 证照与规范 (Licenses & Compliance)
    'Licenses and certificates': '证照与规范',
    'License Documents': '证照与规范',
    'Government inspection': '证照与规范',
    'Operating Specifications': '证照与规范',
    'Requirements': '证照与规范',
}

# Module display order (for consistent reporting)
MODULE_ORDER = [
    '设备与工具',
    '清洁消毒',
    '温控管理',
    '储存管理',
    '食品加工区域',
    '水务与管道',
    '虫害防控',
    '有效期管理',
    '人员卫生',
    '化学品管理',
    '环境与客区',
    '证照与规范',
]

MODULE_ENGLISH = {
    '设备与工具': 'Equipment & Utensils',
    '清洁消毒': 'Cleaning & Disinfection',
    '温控管理': 'Temperature Control',
    '储存管理': 'Storage Management',
    '食品加工区域': 'Food Processing Area',
    '水务与管道': 'Water & Plumbing',
    '虫害防控': 'Pest Control',
    '有效期管理': 'Expiration Management',
    '人员卫生': 'Personal Hygiene',
    '化学品管理': 'Chemical Management',
    '环境与客区': 'Environment & Customer Area',
    '证照与规范': 'Licenses & Compliance',
}

# ---------------------------------------------------------------------------
# Deduction type → severity mapping
# ---------------------------------------------------------------------------
DEDUCTION_SEVERITY = {
    'Key': {'label_cn': 'S项', 'code': 'S', 'level': '关键项', 'description': 'Critical'},
    'Important': {'label_cn': 'M项', 'code': 'M', 'level': '重要项', 'description': 'Important'},
    'General': {'label_cn': 'G项', 'code': 'G', 'level': '一般项', 'description': 'General'},
    'Slight': {'label_cn': 'L项', 'code': 'L', 'level': '轻微项', 'description': 'Slight'},
    'Other': {'label_cn': '其他', 'code': 'O', 'level': '其他', 'description': 'Other'},
}

SEVERITY_ORDER = ['S', 'M', 'G', 'L', 'O']

# ---------------------------------------------------------------------------
# Luckin color scheme (matches /app/luckin-ops-dashboard/scripts/generate_report.py)
# ---------------------------------------------------------------------------
COLORS = {
    'NAVY': '#1F4E79',
    'BLUE_ACCENT': '#2E75B6',
    'LIGHT_BLUE_BG': '#D6E4F0',
    'ALT_ROW': '#F2F2F2',
    'BORDER_GRAY': '#BFBFBF',
    'TEXT_DARK': '#2C3E50',
    'GREEN': '#27AE60',
    'RED': '#C0392B',
    'WARNING_ORANGE': '#E67E22',
    'CRITICAL_BG': '#FCE4EC',
    'WARNING_BG': '#FDEBD0',
    'HEALTHY_BG': '#D5F5E3',
    'INFO_BG': '#D6E4F0',
}

# ---------------------------------------------------------------------------
# CAPA keyword-based attribution
# ---------------------------------------------------------------------------
ATTRIBUTION_KEYWORDS = {
    '机修': [
        'broken', 'leaking', 'not working', 'needs repair', 'malfunction',
        'damaged', 'out of order', 'defective', 'faulty', 'replace',
        'maintenance', 'repair', 'fix',
    ],
    '门店': [
        'dirty', 'not labeled', 'expired', 'not clean', 'missing label',
        'no label', 'no date', 'not stored', 'improper', 'uncovered',
        'not wearing', 'no gloves', 'no hairnet', 'temperature not recorded',
        'not sanitized', 'not washed',
    ],
    '营建': [
        'no air gap', 'pipes', 'construction', 'structural', 'plumbing',
        'drainage', 'ventilation', 'ceiling', 'wall', 'floor damage',
        'grease trap', 'sewer', 'installation',
    ],
}

# ---------------------------------------------------------------------------
# SLA standards for CAPA
# ---------------------------------------------------------------------------
SLA_STANDARDS = {
    'S': {'days': 2, 'label': 'S项（关键项）', 'deadline': '2天'},
    'M': {'days': 7, 'label': 'M项（重要项）', 'deadline': '7天'},
    'G': {'days': 14, 'label': 'G项（一般项）', 'deadline': '14天'},
    'L': {'days': 14, 'label': 'L项（轻微项）', 'deadline': '14天'},
}

# ---------------------------------------------------------------------------
# Report metadata
# ---------------------------------------------------------------------------
REPORT_AUTHOR = '曾翔宇'
REPORT_DEPARTMENT = '质量保障部 / 基础设施部'
REPORT_COMPANY = '瑞幸咖啡北美（First Ray Holdings USA Inc.）'
