#!/usr/bin/env python3
"""Generate CSV exports from empapp inspection data extracted via mcp-db-gateway."""
import csv
import json
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Raw data from MCP queries ───

STORE_MASTER = [
    {"dept_id": 1131, "shop_no": "US00000", "shop_name": "NJ Test Kitchen", "status": 1, "set_up_time": "2025-05-09", "shop_level": "SL02"},
    {"dept_id": 1127, "shop_no": "US00001", "shop_name": "8th & Broadway", "status": 1, "set_up_time": "2025-06-30", "shop_level": "SL02"},
    {"dept_id": 1128, "shop_no": "US00002", "shop_name": "28th & 6th", "status": 1, "set_up_time": "2025-06-30", "shop_level": "SL02"},
    {"dept_id": 1140, "shop_no": "US00003", "shop_name": "100 Maiden Ln", "status": 1, "set_up_time": "2025-09-09", "shop_level": "SL02"},
    {"dept_id": 20011, "shop_no": "US00004", "shop_name": "37th & Broadway", "status": 1, "set_up_time": "2025-11-20", "shop_level": "SL02"},
    {"dept_id": 1141, "shop_no": "US00005", "shop_name": "54th & 8th", "status": 1, "set_up_time": "2025-08-24", "shop_level": "SL02"},
    {"dept_id": 20010, "shop_no": "US00006", "shop_name": "102 Fulton", "status": 1, "set_up_time": "2025-08-28", "shop_level": "SL02"},
    {"dept_id": 20009, "shop_no": "US00007", "shop_name": "108th & Broadway", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20008, "shop_no": "US00008", "shop_name": "33rd & 10th", "status": 1, "set_up_time": "2025-12-01", "shop_level": "SL02"},
    {"dept_id": 20015, "shop_no": "US00009", "shop_name": "48th & 3rd", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20016, "shop_no": "US00010", "shop_name": "154 Bleecker", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20017, "shop_no": "US00011", "shop_name": "180 Varick", "status": 2, "set_up_time": None, "shop_level": "SL02"},
    {"dept_id": 20019, "shop_no": "US00012", "shop_name": "16th & 6th", "status": 1, "set_up_time": "2026-03-23", "shop_level": "SL02"},
    {"dept_id": 20020, "shop_no": "US00013", "shop_name": "Grand Central Terminal", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20021, "shop_no": "US00014", "shop_name": "25 Park Row", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20022, "shop_no": "US00015", "shop_name": "41st & Lexington", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20023, "shop_no": "US00016", "shop_name": "Reade & Broadway", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20024, "shop_no": "US00017", "shop_name": "63rd & 3rd", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20025, "shop_no": "US00018", "shop_name": "40th & 10th", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20026, "shop_no": "US00019", "shop_name": "29th & 3rd", "status": 2, "set_up_time": None, "shop_level": "SL02"},
    {"dept_id": 20027, "shop_no": "US00020", "shop_name": "21st & 3rd", "status": 1, "set_up_time": "2026-02-06", "shop_level": "SL03"},
    {"dept_id": 20028, "shop_no": "US00021", "shop_name": "128 W 32nd St", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20029, "shop_no": "US00022", "shop_name": "23rd & 8th", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20030, "shop_no": "US00023", "shop_name": "23rd & 1st", "status": 2, "set_up_time": None, "shop_level": "SL02"},
    {"dept_id": 20031, "shop_no": "US00024", "shop_name": "15th & 3rd", "status": 1, "set_up_time": "2025-12-14", "shop_level": "SL02"},
    {"dept_id": 20032, "shop_no": "US00025", "shop_name": "221 Grand", "status": 1, "set_up_time": "2025-12-15", "shop_level": "SL02"},
    {"dept_id": 20034, "shop_no": "US00026", "shop_name": "211 Schermerhorn", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20035, "shop_no": "US00027", "shop_name": "52nd & Madison", "status": 1, "set_up_time": "2026-02-26", "shop_level": "SL02"},
    {"dept_id": 20054, "shop_no": "US00028", "shop_name": "Jackson Ave - LIC", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20055, "shop_no": "US00029", "shop_name": "148 Chambers", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20036, "shop_no": "US00035", "shop_name": "35th & 5th", "status": 2, "set_up_time": None, "shop_level": None},
    {"dept_id": 20046, "shop_no": "US99998", "shop_name": "Shanghai Test Kitchen", "status": 1, "set_up_time": "2025-11-14", "shop_level": "SL02"},
    {"dept_id": 20007, "shop_no": "US99999", "shop_name": "NJ Test Kitchen 2", "status": 1, "set_up_time": "2025-06-26", "shop_level": "SL05"},
]

# Category hierarchy (id -> name) for resolving module from cat_path
CATEGORIES = {
    1084: "Store food safety self-check", 1085: "Store food safety self-check",
    1086: "Document Record", 1087: "Licenses and certificates", 1088: "Personal certificate", 1089: "Government inspection",
    1090: "Employees' Health and Personal Hygiene", 1091: "Employees' Health", 1092: "Personal Hygiene",
    1093: "Disposable Gloves and Blue Bandages", 1094: "Handwashing Standards",
    1095: "Approved Supplier", 1096: "Approved Goods",
    1097: "Process Control", 1098: "Material Storage Location Specification",
    1099: "Storage/Maintenance of Utensils", 1100: "Cross-Contamination",
    1101: "Foreign Material Control", 1102: "Cleaning and Sanitation",
    1103: "Procedures for Cleaning and Disinfection", 1104: "Equipment and Food Processing Utensils",
    1105: "Operation Stand, Shelf, Cabinet and Water Sink", 1106: "Food Processing Area",
    1107: "Trash Cans", 1108: "Customer Area", 1109: "Temperature Control / Expiration Date Management.",
    1113: "Expiration Date", 1115: "Operating Specifications",
    1116: "Maintenance of Equipment", 1118: "Equipment Inspection and Maintenance",
    1119: "Chemicals", 1120: "Chemical Mark/Storage",
    1121: "Pests Control", 1123: "Insect Pest Control Facilities & Suppliers",
    1125: "Facility", 1126: "Water Sinks & Pipes",
    1127: "Grease traps&Residue traps&Sewer lines", 1128: "Water Filtration Device",
    1130: "Workplace Safety", 1131: "Workplace Safety",
    1132: "Requirements on Store Audit Management Procedures",
    # Store food safety audit (1134) hierarchy
    1134: "Store food safety audit", 1475: "Store food safety self-check",
    1476: "Document Record", 1477: "Licenses and certificates",
    1480: "Employees' Health and Personal Hygiene", 1482: "Personal Hygiene",
    1485: "Approved Supplier", 1486: "Approved Goods",
    1487: "Process Control", 1488: "Material Storage Location Specification",
    1489: "Storage/Maintenance of Utensils", 1490: "Cross-Contamination",
    1494: "Cleaning and Sanitation", 1495: "Chemicals",
    1496: "Clean & Sanitize", 1497: "Equipment and utensils",
    1498: "Operation Stand, Shelf, Cabinet and Water Sink",
    1499: "Food Processing Area", 1500: "Customer Area",
    1501: "Restroom", 1502: "Cleaning and Sanitation",
    1503: "Waste Management",
    1504: "Temperature Control / Expiration Date Management.",
    1508: "Expiration Date", 1509: "Maintenance of Equipment",
    1512: "Facility", 1513: "Good condition", 1514: "Sinks and Pipes",
    1515: "Grease traps", 1517: "Pests Control",
    1521: "Site Security", 1523: "Workplace Safety", 1524: "Workplace Safety",
    1525: "Requirements on Store Audit Management Procedures", 1526: "Requirements",
    1527: "Waste Management",
    # Area food safety Check (1184) hierarchy
    1184: "Area food safety Check", 1630: "Store food safety self-check",
    1579: "Store food safety self-check",
    1580: "Document Record", 1584: "Employees' Health and Personal Hygiene",
    1589: "Approved Supplier", 1591: "Process Control",
    1598: "Cleaning and Sanitation", 1607: "Temperature Control / Expiration Date Management.",
    1612: "Maintenance of Equipment", 1615: "Facility",
    1620: "Pests Control", 1624: "Site Security",
    1626: "Workplace Safety", 1628: "Requirements on Store Audit Management Procedures",
}

# Module resolution: from cat_path, pick the 3rd element (level-2 = module)
# Path structure: root_category, sub_category, module, [leaf_category]
# e.g. "1084,1085,1097" -> module is at index 2 = 1097 = "Process Control"
# e.g. "1084,1085,1102" -> module at index 2 = 1102 = "Cleaning and Sanitation"
# For deeper paths: "1084,1085,1086" -> module at index 2 = 1086 = "Document Record"

# Module-level IDs for self-check (path depth 2 under 1084,1579)
SELFCHECK_MODULES = {
    1580: "Document Record", 1584: "Employees' Health and Personal Hygiene",
    1589: "Approved Supplier", 1591: "Process Control",
    1598: "Cleaning and Sanitation", 1607: "Temperature Control / Expiration Date Management",
    1612: "Maintenance of Equipment", 1615: "Facility",
    1620: "Pests Control", 1624: "Site Security",
    1626: "Workplace Safety", 1628: "Requirements on Store Audit Management Procedures",
}

# Module-level IDs for audit (path depth 2 under 1134,1475)
AUDIT_MODULES = {
    1476: "Document Record", 1480: "Employees' Health and Personal Hygiene",
    1485: "Approved Supplier", 1487: "Process Control",
    1494: "Cleaning and Sanitation", 1504: "Temperature Control / Expiration Date Management",
    1509: "Maintenance of Equipment", 1512: "Facility",
    1517: "Pests Control", 1521: "Site Security",
    1523: "Workplace Safety", 1525: "Requirements on Store Audit Management Procedures",
}

DEDUCTION_TYPE_TO_SEVERITY = {1: "S", 3: "M", 2: "G", 4: "L"}
INSPECTION_TYPE_MAP = {
    "Store food safety self-check": "门店自检",
    "Store food safety audit": "QA审计",
    "Area food safety Check": "区经检查",
}
STATUS_MAP = {1: "Active", 2: "Not Yet Opened"}
POST_CODE_ROLE = {
    "LKUS00000082": "Store Manager / Asst. Store Manager",
    "LKUS00000083": "Area Operations Manager",
    "LKUS00000223": "Senior QA Manager",
}

REPORTS = [
    {"shopcheck_data_id": 1956, "dept_id": 20032, "check_date": "2026-03-04", "score": 89, "large_category_name": "Store food safety self-check", "checker_name": "Juliana Li", "checker_post_code": "LKUS00000082"},
    {"shopcheck_data_id": 1959, "dept_id": 20031, "check_date": "2026-03-06", "score": 70, "large_category_name": "Store food safety self-check", "checker_name": "Clara Mae Venturina", "checker_post_code": "LKUS00000082"},
    {"shopcheck_data_id": 1961, "dept_id": 20010, "check_date": "2026-03-08", "score": 100, "large_category_name": "Store food safety self-check", "checker_name": "Shangxian Piao", "checker_post_code": "LKUS00000082"},
    {"shopcheck_data_id": 1963, "dept_id": 20031, "check_date": "2026-03-09", "score": 47, "large_category_name": "Store food safety self-check", "checker_name": "Clara Mae Venturina", "checker_post_code": "LKUS00000082"},
    {"shopcheck_data_id": 1962, "dept_id": 20035, "check_date": "2026-03-09", "score": 81, "large_category_name": "Store food safety self-check", "checker_name": "Wenny Lin", "checker_post_code": "LKUS00000082"},
    {"shopcheck_data_id": 1966, "dept_id": 1127, "check_date": "2026-03-09", "score": 95, "large_category_name": "Store food safety self-check", "checker_name": "Jian Ming Juo", "checker_post_code": "LKUS00000082"},
    {"shopcheck_data_id": 1965, "dept_id": 20008, "check_date": "2026-03-09", "score": 100, "large_category_name": "Store food safety self-check", "checker_name": "Derson Liang", "checker_post_code": "LKUS00000083"},
    {"shopcheck_data_id": 1969, "dept_id": 20027, "check_date": "2026-03-10", "score": 73, "large_category_name": "Store food safety self-check", "checker_name": "Darwin Coronel", "checker_post_code": "LKUS00000082"},
    {"shopcheck_data_id": 1971, "dept_id": 20008, "check_date": "2026-03-10", "score": 55, "large_category_name": "Store food safety self-check", "checker_name": "Yaqing Zuo", "checker_post_code": "LKUS00000082"},
    {"shopcheck_data_id": 1972, "dept_id": 20010, "check_date": "2026-03-11", "score": 92, "large_category_name": "Store food safety self-check", "checker_name": "Shangxian Piao", "checker_post_code": "LKUS00000082"},
    {"shopcheck_data_id": 1973, "dept_id": 20008, "check_date": "2026-03-15", "score": 84, "large_category_name": "Store food safety self-check", "checker_name": "Derson Liang", "checker_post_code": "LKUS00000083"},
    {"shopcheck_data_id": 1977, "dept_id": 20010, "check_date": "2026-03-27", "score": 96, "large_category_name": "Store food safety self-check", "checker_name": "Shangxian Piao", "checker_post_code": "LKUS00000082"},
    {"shopcheck_data_id": 1979, "dept_id": 20035, "check_date": "2026-03-31", "score": 60, "large_category_name": "Store food safety audit", "checker_name": "Eamonn Caballar", "checker_post_code": "LKUS00000223"},
]

SEVERITY_COUNTS = {
    1956: {"s": 0, "m": 0, "g": 5, "l": 1, "total_deduction": -11, "total_items": 6},
    1959: {"s": 1, "m": 1, "g": 0, "l": 0, "total_deduction": -10, "total_items": 2},
    1962: {"s": 0, "m": 1, "g": 7, "l": 0, "total_deduction": -19, "total_items": 8},
    1963: {"s": 2, "m": 3, "g": 4, "l": 0, "total_deduction": -33, "total_items": 9},
    1966: {"s": 0, "m": 0, "g": 2, "l": 1, "total_deduction": -5, "total_items": 3},
    1969: {"s": 1, "m": 0, "g": 1, "l": 0, "total_deduction": -7, "total_items": 2},
    1971: {"s": 0, "m": 5, "g": 9, "l": 2, "total_deduction": -45, "total_items": 16},
    1972: {"s": 0, "m": 0, "g": 4, "l": 0, "total_deduction": -8, "total_items": 4},
    1973: {"s": 0, "m": 1, "g": 5, "l": 1, "total_deduction": -16, "total_items": 7},
    1977: {"s": 0, "m": 0, "g": 1, "l": 2, "total_deduction": -4, "total_items": 3},
    1979: {"s": 1, "m": 1, "g": 5, "l": 0, "total_deduction": -20, "total_items": 7},
}

OPPORTUNITIES = [
    {"opportunity_id": 8674, "shopcheck_data_id": 1956, "issue_description": "Water inside \u201cdirect food contacts\u201d container", "deduction_type": 2, "score_config": -2, "leaf_category": "Material Storage Location Specification", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8676, "shopcheck_data_id": 1956, "issue_description": "Standing water and espresso spillage", "deduction_type": 2, "score_config": -2, "leaf_category": "Equipment and Food Processing Utensils", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8677, "shopcheck_data_id": 1956, "issue_description": "No separation of trash types", "deduction_type": 2, "score_config": -2, "leaf_category": "Trash Cans", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8678, "shopcheck_data_id": 1956, "issue_description": "Trash bin overflowing", "deduction_type": 4, "score_config": -1, "leaf_category": "Trash Cans", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8679, "shopcheck_data_id": 1956, "issue_description": "Milk excess spillage", "deduction_type": 2, "score_config": -2, "leaf_category": "Storage/Maintenance of Utensils", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8680, "shopcheck_data_id": 1956, "issue_description": "Opened and partial spillage of materials", "deduction_type": 2, "score_config": -2, "leaf_category": "Operating Specifications", "cat_path": "1084,1085,1109"},
    {"opportunity_id": 8685, "shopcheck_data_id": 1959, "issue_description": "", "deduction_type": 1, "score_config": -5, "leaf_category": "Licenses and certificates", "cat_path": "1084,1085,1086"},
    {"opportunity_id": 8686, "shopcheck_data_id": 1959, "issue_description": "", "deduction_type": 3, "score_config": -5, "leaf_category": "Licenses and certificates", "cat_path": "1084,1085,1086"},
    {"opportunity_id": 8694, "shopcheck_data_id": 1962, "issue_description": "Storage platform is not 6inches above the ground", "deduction_type": 2, "score_config": -2, "leaf_category": "Material Storage Location Specification", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8695, "shopcheck_data_id": 1962, "issue_description": "Safe box was not locked", "deduction_type": 2, "score_config": -2, "leaf_category": "Material Storage Location Specification", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8696, "shopcheck_data_id": 1962, "issue_description": "stains found throughout store.", "deduction_type": 2, "score_config": -2, "leaf_category": "Storage/Maintenance of Utensils", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8706, "shopcheck_data_id": 1962, "issue_description": "Coffee stains found on interior of fridge under hot food section.", "deduction_type": 2, "score_config": -2, "leaf_category": "Equipment and Food Processing Utensils", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8707, "shopcheck_data_id": 1962, "issue_description": "possible leak / scale build up located under rinse sink.", "deduction_type": 2, "score_config": -2, "leaf_category": "Water Sinks & Pipes", "cat_path": "1084,1085,1125"},
    {"opportunity_id": 8708, "shopcheck_data_id": 1962, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Equipment and Food Processing Utensils", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8709, "shopcheck_data_id": 1962, "issue_description": "No open label found on coconut milk below the fridge of juice machine", "deduction_type": 3, "score_config": -5, "leaf_category": "Expiration Date", "cat_path": "1084,1085,1109"},
    {"opportunity_id": 8710, "shopcheck_data_id": 1962, "issue_description": "No inspection signed", "deduction_type": 2, "score_config": -2, "leaf_category": "Workplace Safety", "cat_path": "1084,1085,1130"},
    {"opportunity_id": 8697, "shopcheck_data_id": 1963, "issue_description": "", "deduction_type": 1, "score_config": -5, "leaf_category": "Licenses and certificates", "cat_path": "1084,1085,1086"},
    {"opportunity_id": 8698, "shopcheck_data_id": 1963, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Cross-Contamination", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8699, "shopcheck_data_id": 1963, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Storage/Maintenance of Utensils", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8700, "shopcheck_data_id": 1963, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Storage/Maintenance of Utensils", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8701, "shopcheck_data_id": 1963, "issue_description": "", "deduction_type": 3, "score_config": -5, "leaf_category": "Procedures for Cleaning and Disinfection", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8702, "shopcheck_data_id": 1963, "issue_description": "", "deduction_type": 3, "score_config": -5, "leaf_category": "Procedures for Cleaning and Disinfection", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8703, "shopcheck_data_id": 1963, "issue_description": "", "deduction_type": 3, "score_config": -5, "leaf_category": "Licenses and certificates", "cat_path": "1084,1085,1086"},
    {"opportunity_id": 8704, "shopcheck_data_id": 1963, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Cross-Contamination", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8705, "shopcheck_data_id": 1963, "issue_description": "", "deduction_type": 1, "score_config": -5, "leaf_category": "Chemical Mark/Storage", "cat_path": "1084,1085,1119"},
    {"opportunity_id": 8711, "shopcheck_data_id": 1966, "issue_description": "Significant gap found in the display fridge and the counter top.", "deduction_type": 2, "score_config": -2, "leaf_category": "Equipment Inspection and Maintenance", "cat_path": "1084,1085,1116"},
    {"opportunity_id": 8712, "shopcheck_data_id": 1966, "issue_description": "Coffee ground found beneath the machine", "deduction_type": 2, "score_config": -2, "leaf_category": "Storage/Maintenance of Utensils", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8713, "shopcheck_data_id": 1966, "issue_description": "Stain and water marks on counter top", "deduction_type": 4, "score_config": -1, "leaf_category": "Operation Stand, Shelf, Cabinet and Water Sink", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8716, "shopcheck_data_id": 1969, "issue_description": "Various sani stains by the oven machine on the countertop.\n\n\nstanding water sughted", "deduction_type": 2, "score_config": -2, "leaf_category": "Storage/Maintenance of Utensils", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8717, "shopcheck_data_id": 1969, "issue_description": "Matcha powder found on can opener", "deduction_type": 1, "score_config": -5, "leaf_category": "Cross-Contamination", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8719, "shopcheck_data_id": 1971, "issue_description": "Standing water and dirt food contact containers", "deduction_type": 2, "score_config": -2, "leaf_category": "Expiration Date", "cat_path": "1084,1085,1109"},
    {"opportunity_id": 8720, "shopcheck_data_id": 1971, "issue_description": "Missing label with vanilla syrup", "deduction_type": 3, "score_config": -5, "leaf_category": "Expiration Date", "cat_path": "1084,1085,1109"},
    {"opportunity_id": 8721, "shopcheck_data_id": 1971, "issue_description": "Tear free cover on the table without packing", "deduction_type": 3, "score_config": -5, "leaf_category": "Approved Goods", "cat_path": "1084,1085,1095"},
    {"opportunity_id": 8722, "shopcheck_data_id": 1971, "issue_description": "Necklace outside the shirt", "deduction_type": 3, "score_config": -5, "leaf_category": "Personal Hygiene", "cat_path": "1084,1085,1090"},
    {"opportunity_id": 8723, "shopcheck_data_id": 1971, "issue_description": "Broken package of the Sami strip and the strip is dirty", "deduction_type": 2, "score_config": -2, "leaf_category": "Chemical Mark/Storage", "cat_path": "1084,1085,1119"},
    {"opportunity_id": 8724, "shopcheck_data_id": 1971, "issue_description": "Dust on the lids of drip machines\nDust on the side of juicer", "deduction_type": 2, "score_config": -2, "leaf_category": "Equipment Inspection and Maintenance", "cat_path": "1084,1085,1116"},
    {"opportunity_id": 8725, "shopcheck_data_id": 1971, "issue_description": "Dirty water under the lid of Ice bin\nDust on the table and side of juicer\nBlender\nOven area\nDrip machine\nUnder espresso machines\nUnder syrup machine\nUnder single screen\nLid of the trash bins\nDrinking water sink\nCabinets\nFridges\nA4 poster\nEmployees area table and trash bins", "deduction_type": 2, "score_config": -2, "leaf_category": "Storage/Maintenance of Utensils", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8726, "shopcheck_data_id": 1971, "issue_description": "No sign", "deduction_type": 2, "score_config": -2, "leaf_category": "Personal Hygiene", "cat_path": "1084,1085,1090"},
    {"opportunity_id": 8727, "shopcheck_data_id": 1971, "issue_description": "Dust on the side of juicer\nFridge\nMatcha on the pitchers", "deduction_type": 3, "score_config": -5, "leaf_category": "Procedures for Cleaning and Disinfection", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8728, "shopcheck_data_id": 1971, "issue_description": "Standing water in the containers", "deduction_type": 2, "score_config": -2, "leaf_category": "Material Storage Location Specification", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8729, "shopcheck_data_id": 1971, "issue_description": "Test strips is not full packed and dirty\nOne of sani water not enough to 100ppm", "deduction_type": 3, "score_config": -5, "leaf_category": "Procedures for Cleaning and Disinfection", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8730, "shopcheck_data_id": 1971, "issue_description": "Leaking sink", "deduction_type": 4, "score_config": -1, "leaf_category": "Food Processing Area", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8731, "shopcheck_data_id": 1971, "issue_description": "Standing water", "deduction_type": 4, "score_config": -1, "leaf_category": "Customer Area", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8732, "shopcheck_data_id": 1971, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Water Filtration Device", "cat_path": "1084,1085,1125"},
    {"opportunity_id": 8733, "shopcheck_data_id": 1971, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Grease traps&Residue traps&Sewer lines", "cat_path": "1084,1085,1125"},
    {"opportunity_id": 8734, "shopcheck_data_id": 1971, "issue_description": "No air gap", "deduction_type": 2, "score_config": -2, "leaf_category": "Water Sinks & Pipes", "cat_path": "1084,1085,1125"},
    {"opportunity_id": 8735, "shopcheck_data_id": 1972, "issue_description": "Don't close container properly", "deduction_type": 2, "score_config": -2, "leaf_category": "Cross-Contamination", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8736, "shopcheck_data_id": 1972, "issue_description": "Juice machine leaking wait me the parts\u3002 Broken drip machine needs to pick up\u3002 Steam wand is not working properly\u3002 Water mark on the ice machine", "deduction_type": 2, "score_config": -2, "leaf_category": "Equipment Inspection and Maintenance", "cat_path": "1084,1085,1116"},
    {"opportunity_id": 8737, "shopcheck_data_id": 1972, "issue_description": "Door handle off", "deduction_type": 2, "score_config": -2, "leaf_category": "Workplace Safety", "cat_path": "1084,1085,1130"},
    {"opportunity_id": 8738, "shopcheck_data_id": 1972, "issue_description": "There is no info of Pest control service", "deduction_type": 2, "score_config": -2, "leaf_category": "Insect Pest Control Facilities & Suppliers", "cat_path": "1084,1085,1121"},
    {"opportunity_id": 8748, "shopcheck_data_id": 1973, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Equipment and Food Processing Utensils", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8749, "shopcheck_data_id": 1973, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Storage/Maintenance of Utensils", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8750, "shopcheck_data_id": 1973, "issue_description": "", "deduction_type": 3, "score_config": -5, "leaf_category": "Procedures for Cleaning and Disinfection", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8751, "shopcheck_data_id": 1973, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Material Storage Location Specification", "cat_path": "1084,1085,1097"},
    {"opportunity_id": 8752, "shopcheck_data_id": 1973, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Water Filtration Device", "cat_path": "1084,1085,1125"},
    {"opportunity_id": 8753, "shopcheck_data_id": 1973, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Grease traps&Residue traps&Sewer lines", "cat_path": "1084,1085,1125"},
    {"opportunity_id": 8754, "shopcheck_data_id": 1973, "issue_description": "", "deduction_type": 4, "score_config": -1, "leaf_category": "Operation Stand, Shelf, Cabinet and Water Sink", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8758, "shopcheck_data_id": 1977, "issue_description": "", "deduction_type": 2, "score_config": -2, "leaf_category": "Equipment and Food Processing Utensils", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8759, "shopcheck_data_id": 1977, "issue_description": "", "deduction_type": 4, "score_config": -1, "leaf_category": "Food Processing Area", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8760, "shopcheck_data_id": 1977, "issue_description": "", "deduction_type": 4, "score_config": -1, "leaf_category": "Operation Stand, Shelf, Cabinet and Water Sink", "cat_path": "1084,1085,1102"},
    {"opportunity_id": 8761, "shopcheck_data_id": 1979, "issue_description": "No check signage on fire extinguishers.", "deduction_type": 2, "score_config": -2, "leaf_category": "Workplace Safety", "cat_path": "1134,1475,1523"},
    {"opportunity_id": 8762, "shopcheck_data_id": 1979, "issue_description": "Product stored below 6 inch requirement.", "deduction_type": 2, "score_config": -2, "leaf_category": "Material Storage Location Specification", "cat_path": "1134,1475,1487"},
    {"opportunity_id": 8763, "shopcheck_data_id": 1979, "issue_description": "Sanitizer ppm below acceptable levels.", "deduction_type": 3, "score_config": -5, "leaf_category": "Clean & Sanitize", "cat_path": "1134,1475,1494"},
    {"opportunity_id": 8764, "shopcheck_data_id": 1979, "issue_description": "Leak found under ice holder/ rinsing sink on food processing floor.", "deduction_type": 2, "score_config": -2, "leaf_category": "Good condition", "cat_path": "1134,1475,1512"},
    {"opportunity_id": 8765, "shopcheck_data_id": 1979, "issue_description": "Milk found on door of refrigerator.", "deduction_type": 2, "score_config": -2, "leaf_category": "Equipment and utensils", "cat_path": "1134,1475,1494"},
    {"opportunity_id": 8766, "shopcheck_data_id": 1979, "issue_description": "Leak found under coffee machine. (Right.)", "deduction_type": 1, "score_config": -5, "leaf_category": "Sinks and Pipes", "cat_path": "1134,1475,1512"},
    {"opportunity_id": 8767, "shopcheck_data_id": 1979, "issue_description": "Overflow of trash found.", "deduction_type": 2, "score_config": -2, "leaf_category": "Waste Management", "cat_path": "1134,1475,1494"},
]

INSPECTOR_TREND = [
    {"month": "2026-01", "checker_name": "Afsana Gu", "large_category_name": "Store food safety self-check", "inspection_count": 1},
    {"month": "2026-02", "checker_name": "Andrew Hu", "large_category_name": "Store food safety self-check", "inspection_count": 1},
    {"month": "2026-03", "checker_name": "Clara Mae Venturina", "large_category_name": "Store food safety self-check", "inspection_count": 2},
    {"month": "2026-01", "checker_name": "Daniel Chu", "large_category_name": "Area food safety Check", "inspection_count": 1},
    {"month": "2026-03", "checker_name": "Darwin Coronel", "large_category_name": "Store food safety self-check", "inspection_count": 1},
    {"month": "2026-03", "checker_name": "Derson Liang", "large_category_name": "Store food safety self-check", "inspection_count": 2},
    {"month": "2026-01", "checker_name": "Dominique Meadows", "large_category_name": "Store food safety self-check", "inspection_count": 1},
    {"month": "2026-03", "checker_name": "Eamonn Caballar", "large_category_name": "Store food safety audit", "inspection_count": 1},
    {"month": "2026-03", "checker_name": "Jian Ming Juo", "large_category_name": "Store food safety self-check", "inspection_count": 1},
    {"month": "2026-01", "checker_name": "Joselyn Pacheco", "large_category_name": "Store food safety self-check", "inspection_count": 1},
    {"month": "2026-02", "checker_name": "Joselyn Pacheco", "large_category_name": "Store food safety self-check", "inspection_count": 2},
    {"month": "2026-01", "checker_name": "Juliana Li", "large_category_name": "Store food safety self-check", "inspection_count": 1},
    {"month": "2026-03", "checker_name": "Juliana Li", "large_category_name": "Store food safety self-check", "inspection_count": 1},
    {"month": "2026-01", "checker_name": "Jung Han Liang", "large_category_name": "Area food safety Check", "inspection_count": 3},
    {"month": "2026-01", "checker_name": "Shangxian Piao", "large_category_name": "Store food safety self-check", "inspection_count": 3},
    {"month": "2026-02", "checker_name": "Shangxian Piao", "large_category_name": "Store food safety self-check", "inspection_count": 2},
    {"month": "2026-03", "checker_name": "Shangxian Piao", "large_category_name": "Store food safety self-check", "inspection_count": 3},
    {"month": "2026-03", "checker_name": "Wenny Lin", "large_category_name": "Store food safety self-check", "inspection_count": 1},
    {"month": "2026-03", "checker_name": "Yaqing Zuo", "large_category_name": "Store food safety self-check", "inspection_count": 1},
    {"month": "2026-01", "checker_name": "Yu Jiang", "large_category_name": "Store food safety audit", "inspection_count": 5},
    {"month": "2026-02", "checker_name": "Yu Jiang", "large_category_name": "Store food safety audit", "inspection_count": 2},
]


def get_store(dept_id):
    for s in STORE_MASTER:
        if s["dept_id"] == dept_id:
            return s
    return {"shop_no": f"UNKNOWN-{dept_id}", "shop_name": f"Unknown (dept_id={dept_id})", "status": 0}


def resolve_module(cat_path):
    """Resolve module name from category path. Module is level-2 in the hierarchy."""
    parts = [int(x) for x in cat_path.split(",")]
    if len(parts) >= 3:
        module_id = parts[2]
        # Check selfcheck modules
        if module_id in SELFCHECK_MODULES:
            return SELFCHECK_MODULES[module_id]
        if module_id in AUDIT_MODULES:
            return AUDIT_MODULES[module_id]
        return CATEGORIES.get(module_id, f"Unknown-{module_id}")
    return "Unknown"


def get_report(shopcheck_data_id):
    for r in REPORTS:
        if r["shopcheck_data_id"] == shopcheck_data_id:
            return r
    return None


def write_csv(filename, headers, rows):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
    print(f"  {filename}: {len(rows)} rows -> {path}")
    return path


# ─── Export 1: inspection_summary.csv ───
def export_summary():
    rows = []
    for r in REPORTS:
        store = get_store(r["dept_id"])
        sc = SEVERITY_COUNTS.get(r["shopcheck_data_id"], {"s": 0, "m": 0, "g": 0, "l": 0, "total_deduction": 0, "total_items": 0})
        rows.append({
            "inspection_id": r["shopcheck_data_id"],
            "store_code": store["shop_no"],
            "store_name": store["shop_name"],
            "inspection_date": r["check_date"],
            "inspection_type_en": r["large_category_name"],
            "inspection_type_cn": INSPECTION_TYPE_MAP.get(r["large_category_name"], ""),
            "inspector_name": r["checker_name"],
            "inspector_role": POST_CODE_ROLE.get(r["checker_post_code"], r["checker_post_code"]),
            "total_score": r["score"],
            "total_deduction": sc["total_deduction"],
            "total_items": sc["total_items"],
            "s_count": int(sc["s"]),
            "m_count": int(sc["m"]),
            "g_count": int(sc["g"]),
            "l_count": int(sc["l"]),
        })
    headers = ["inspection_id", "store_code", "store_name", "inspection_date",
               "inspection_type_en", "inspection_type_cn", "inspector_name", "inspector_role",
               "total_score", "total_deduction", "total_items", "s_count", "m_count", "g_count", "l_count"]
    return write_csv("march2026_inspection_summary.csv", headers, rows)


# ─── Export 2: inspection_items.csv ───
def export_items():
    rows = []
    for opp in OPPORTUNITIES:
        report = get_report(opp["shopcheck_data_id"])
        if not report:
            continue
        store = get_store(report["dept_id"])
        module = resolve_module(opp["cat_path"])
        rows.append({
            "opportunity_id": opp["opportunity_id"],
            "inspection_id": opp["shopcheck_data_id"],
            "store_code": store["shop_no"],
            "store_name": store["shop_name"],
            "inspection_date": report["check_date"],
            "inspection_type_en": report["large_category_name"],
            "inspection_type_cn": INSPECTION_TYPE_MAP.get(report["large_category_name"], ""),
            "module_name": module,
            "sub_category": opp["leaf_category"],
            "issue_description": opp["issue_description"],
            "severity": DEDUCTION_TYPE_TO_SEVERITY.get(opp["deduction_type"], "?"),
            "deduction_points": opp["score_config"],
        })
    headers = ["opportunity_id", "inspection_id", "store_code", "store_name", "inspection_date",
               "inspection_type_en", "inspection_type_cn", "module_name", "sub_category",
               "issue_description", "severity", "deduction_points"]
    return write_csv("march2026_inspection_items.csv", headers, rows)


# ─── Export 3: store_master.csv ───
def export_store_master():
    rows = []
    for s in STORE_MASTER:
        if s["shop_no"].startswith("US9999"):
            continue  # skip test kitchens
        rows.append({
            "store_code": s["shop_no"],
            "store_name": s["shop_name"],
            "status": STATUS_MAP.get(s["status"], str(s["status"])),
            "opening_date": s["set_up_time"] or "",
            "shop_level": s["shop_level"] or "",
        })
    headers = ["store_code", "store_name", "status", "opening_date", "shop_level"]
    return write_csv("march2026_store_master.csv", headers, rows)


# ─── Export 4: inspector_trend.csv ───
def export_inspector_trend():
    inspectors = {}
    for row in INSPECTOR_TREND:
        key = (row["checker_name"], row["large_category_name"])
        if key not in inspectors:
            inspectors[key] = {"inspector_name": row["checker_name"],
                              "inspection_type": row["large_category_name"],
                              "jan_2026": 0, "feb_2026": 0, "mar_2026": 0}
        month_col = {"2026-01": "jan_2026", "2026-02": "feb_2026", "2026-03": "mar_2026"}[row["month"]]
        inspectors[key][month_col] = row["inspection_count"]

    rows = sorted(inspectors.values(), key=lambda x: (x["inspector_name"], x["inspection_type"]))
    for r in rows:
        r["total_q1"] = r["jan_2026"] + r["feb_2026"] + r["mar_2026"]

    headers = ["inspector_name", "inspection_type", "jan_2026", "feb_2026", "mar_2026", "total_q1"]
    return write_csv("march2026_inspector_trend.csv", headers, rows)


# ─── Validation ───
def print_validation():
    print("\n" + "=" * 60)
    print("VALIDATION — March 2026 Inspection Data")
    print("=" * 60)

    # Inspection counts by type
    type_counts = {}
    for r in REPORTS:
        t = r["large_category_name"]
        type_counts[t] = type_counts.get(t, 0) + 1
    print("\n--- Inspections by Type (March 2026) ---")
    for t in ["Store food safety self-check", "Store food safety audit", "Area food safety Check"]:
        cnt = type_counts.get(t, 0)
        cn = INSPECTION_TYPE_MAP.get(t, "")
        print(f"  {t} ({cn}): {cnt} inspections")

    # Store coverage
    stores = set()
    for r in REPORTS:
        s = get_store(r["dept_id"])
        stores.add(s["shop_no"])
    print(f"\n--- Store Coverage ---")
    print(f"  {len(stores)} distinct stores: {', '.join(sorted(stores))}")

    # Score range
    scores = [r["score"] for r in REPORTS]
    print(f"\n--- Score Range ---")
    print(f"  Min: {min(scores)}, Max: {max(scores)}, Avg: {sum(scores)/len(scores):.1f}")

    # Severity distribution
    total_s = sum(sc["s"] for sc in SEVERITY_COUNTS.values())
    total_m = sum(sc["m"] for sc in SEVERITY_COUNTS.values())
    total_g = sum(sc["g"] for sc in SEVERITY_COUNTS.values())
    total_l = sum(sc["l"] for sc in SEVERITY_COUNTS.values())
    total_all = sum(sc["total_items"] for sc in SEVERITY_COUNTS.values())
    total_ded = sum(sc["total_deduction"] for sc in SEVERITY_COUNTS.values())
    print(f"\n--- Severity Distribution (March 2026) ---")
    print(f"  S (Critical): {int(total_s)} items")
    print(f"  M (Important): {int(total_m)} items")
    print(f"  G (General): {int(total_g)} items")
    print(f"  L (Slight): {int(total_l)} items")
    print(f"  Total items: {int(total_all)}")
    print(f"  Total deduction: {int(total_ded)} points")

    # Opportunity count check
    print(f"\n--- Data Integrity ---")
    print(f"  Opportunities extracted: {len(OPPORTUNITIES)}")
    print(f"  Severity counts sum: {int(total_s + total_m + total_g + total_l)}")
    assert len(OPPORTUNITIES) == int(total_all), f"Mismatch: {len(OPPORTUNITIES)} vs {int(total_all)}"
    print(f"  OK: Opportunity count matches severity sum ({len(OPPORTUNITIES)} = {int(total_all)})")

    # Inspections with 0 findings (score=100)
    zero_findings = [r for r in REPORTS if r["shopcheck_data_id"] not in SEVERITY_COUNTS]
    print(f"  Inspections with 0 findings (perfect score): {len(zero_findings)}")
    for r in zero_findings:
        s = get_store(r["dept_id"])
        print(f"    - {r['check_date']} {s['shop_no']} {s['shop_name']} (score={r['score']})")

    print()


if __name__ == "__main__":
    print("Generating March 2026 Inspection Data Exports")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}\n")

    export_summary()
    export_items()
    export_store_master()
    export_inspector_trend()
    print_validation()
    print("Done.")
