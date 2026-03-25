#!/usr/bin/env python3
"""Generate synthetic QA inspection test data for pipeline validation."""

import random
from datetime import datetime, timedelta

import pandas as pd

random.seed(42)

STORES = [
    ('US00001', 'LKUS00000001', 'Times Square', 'New York City', 'Area 1', 'Pickup'),
    ('US00002', 'LKUS00000002', 'Herald Square', 'New York City', 'Area 1', 'Relax'),
    ('US00003', 'LKUS00000003', 'Bryant Park', 'New York City', 'Area 1', 'Pickup'),
    ('US00004', 'LKUS00000004', 'Wall Street', 'New York City', 'Area 2', 'Pickup'),
    ('US00005', 'LKUS00000005', 'Midtown East', 'New York City', 'Area 2', 'Pickup'),
    ('US00006', 'LKUS00000006', '28th & 6th', 'New York City', 'Area 2', 'Relax'),
    ('US00007', 'LKUS00000007', 'Penn Station', 'New York City', 'Area 3', 'Pickup'),
    ('US00008', 'LKUS00000054', 'JFK Terminal 1', 'New York City', 'Area 3', 'Pickup'),
    ('US00009', 'LKUS00000009', 'Columbus Circle', 'New York City', 'Area 1', 'Relax'),
    ('US00010', 'LKUS00000010', 'Union Square', 'New York City', 'Area 2', 'Pickup'),
]

LABELS = [
    'Equipment and Food Processing Utensils',
    'Storage/Maintenance of Utensils',
    'Equipment Inspection and Maintenance',
    'Facility Inspection and Maintenance',
    'Procedures for Cleaning and Disinfection',
    'Handwashing Standards',
    'Disposable Gloves and Blue Bandages',
    'Devices for Monitoring the Temperatures of All Refrigerators and Freezers',
    'Product Storage Conditions',
    'Material Storage Location Specification',
    'Storage and Inventory Transfer of Food',
    'Approved Goods',
    'Food Processing Area',
    'Operation Stand, Shelf, Cabinet and Water Sink',
    'Cross Contamination',
    'Water Filtration Device',
    'Water Sinks & Pipes',
    'Grease traps&Residue traps&Sewer lines',
    'Insect Pest Control Facilities & Suppliers',
    'No Sign of Insect Pests',
    'Expiration Date',
    'Food',
    'Personal Hygiene',
    "Employees' Health",
    'Chemical Mark/Storage',
    'Customer Area',
    'Trash Cans',
    'Lights',
    'Licenses and certificates',
    'License Documents',
    'Operating Specifications',
    'Requirements',
    'Avoidance of Falling Foreign Objects',
    'Workplace Safety',
    'Personal certificate',
    'No pests enter',
    'Potable Water Supply is Adequate',
    'Unqualified Goods',
    'Government inspection',
]

DEDUCTION_TYPES = ['Key', 'Important', 'General', 'Slight', 'Other']
DEDUCTION_VALUES = {'Key': [-5, 0], 'Important': [-5], 'General': [-2], 'Slight': [-1], 'Other': [0]}

CHECK_CATEGORIES = [
    'Store food safety self-check',
    'Store food safety audit',
    'Area food safety Check',
]

ISSUE_DESCRIPTIONS = [
    'Food item past expiration date found in storage area',
    'Temperature log not completed for refrigerator',
    'Handwashing station missing soap',
    'Floor not clean under the sink area',
    'Equipment not properly maintained - ice machine leaking',
    'Chemical storage area not properly labeled',
    'Pest trap not checked in the last 30 days',
    'Employee health certificate expired',
    'Cross contamination risk: raw and cooked food stored together',
    'Water filter replacement date overdue',
    'Trash can lid broken, needs repair',
    'Operating license not displayed visibly',
    'Gloves not worn during food preparation',
    'Food storage containers not labeled with date',
    'Grease trap not cleaned on schedule',
    'Light fixture damaged in food prep area',
    'No air gap in plumbing under sink',
    'Food items stored directly on floor',
    'Personal items in food preparation area',
    'Temperature of freezer above acceptable range',
    '',  # Some entries have no description
]

CHECKERS = ['Zhang Wei', 'Li Ming', 'Wang Fang', 'Chen Yu']

def generate_data():
    rows = []
    checklist_counter = 1000

    # Generate data for Feb and March 2026
    for month_offset in [1, 0]:  # Feb (prior), March (current)
        month = 3 - month_offset
        year = 2026

        for store in STORES:
            serial, dept, name, city, area, level = store

            # 1-2 inspections per store per month
            num_inspections = random.choice([1, 2])

            for insp in range(num_inspections):
                checklist_counter += 1
                checklist_num = f'CK-2026-{checklist_counter}'
                check_category = random.choice(CHECK_CATEGORIES)
                checker = random.choice(CHECKERS)
                check_day = random.randint(1, 28)
                check_date = f'{year}-{month:02d}-{check_day:02d}'
                gen_time = f'{check_date} {random.randint(8,18):02d}:{random.randint(0,59):02d}:00'

                # Base score between 70-98
                base_score = random.randint(70, 98)

                # Generate 5-15 check items per inspection
                num_items = random.randint(5, 15)

                for _ in range(num_items):
                    label = random.choice(LABELS)
                    deduction_type = random.choices(
                        DEDUCTION_TYPES,
                        weights=[2, 5, 30, 40, 23],
                        k=1
                    )[0]
                    deduction_value = random.choice(DEDUCTION_VALUES[deduction_type])

                    # Only some items have issue descriptions
                    if deduction_value != 0:
                        desc = random.choice([d for d in ISSUE_DESCRIPTIONS if d])
                    else:
                        desc = random.choice(ISSUE_DESCRIPTIONS)

                    rows.append({
                        'City': city,
                        'Operational Management Area': area,
                        'Store serial number': serial,
                        'Department code': dept,
                        'Store name': name,
                        'Checklist number': checklist_num,
                        'Check category': check_category,
                        'Check items': f'Check: {label} compliance requirement',
                        'Opportunity point description': desc if desc else None,
                        'Label': label,
                        'Opportunity point value': deduction_value,
                        'Deduction type': deduction_type,
                        'Check route': 'On-site check',
                        'checker': checker,
                        'Checker position': 'QA Inspector',
                        'Voiding Approval Position': None,
                        'Voiding Submission Time': None,
                        'Voiding Approval Time': None,
                        'Report score': base_score,
                        'Store level': level,
                        'Check date': check_date,
                        'Check report generation time': gen_time,
                    })

    # Add one anomalous negative score (US Store Food Safety Audit)
    rows.append({
        'City': 'New York City',
        'Operational Management Area': 'Area 1',
        'Store serial number': 'US00001',
        'Department code': 'LKUS00000001',
        'Store name': 'Times Square',
        'Checklist number': 'CK-2026-9999',
        'Check category': 'US Store Food Safety Audit',
        'Check items': 'Full audit check',
        'Opportunity point description': None,
        'Label': 'Equipment and Food Processing Utensils',
        'Opportunity point value': 0,
        'Deduction type': 'Other',
        'Check route': 'On-site check',
        'checker': 'External Auditor',
        'Checker position': 'Senior Auditor',
        'Voiding Approval Position': None,
        'Voiding Submission Time': None,
        'Voiding Approval Time': None,
        'Report score': -192,
        'Store level': 'Pickup',
        'Check date': '2026-03-20',
        'Check report generation time': '2026-03-20 14:30:00',
    })

    return pd.DataFrame(rows)


if __name__ == '__main__':
    df = generate_data()
    output_path = '/app/qa-store-audit-report/sample-data/test_qa_data.xlsx'
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_excel(output_path, index=False, engine='openpyxl')
    print(f'Generated {len(df)} rows → {output_path}')
    print(f'Stores: {df["Store serial number"].nunique()}')
    print(f'Months: {df["Check date"].str[:7].unique()}')
    print(f'Labels: {df["Label"].nunique()}')
