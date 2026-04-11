# Phase 3: Instance-Level Parameter Group Mapping

**Generated**: 2026-04-11  
**Source**: `aws rds describe-db-instances` (live) + `/app/affected_instances.csv`

---

## Summary

| Metric | Count |
|--------|-------|
| Total MySQL RDS instances | 63 |
| MySQL 8.0.x instances | 61 |
| MySQL 8.4.x instances | 2 |
| Distinct parameter groups in use | 4 |
| Instances in-sync | 62 |
| Instances pending-reboot | 1 |

## Parameter Group Distribution

| Parameter Group | Family | Instance Count | Instances |
|----------------|--------|---------------|-----------|
| `luckyus-prod-80-new` | mysql8.0 | 56 | *(majority — see full list below)* |
| `luckyus-prod` | mysql8.0 | 2 | devops-rw, ldas-rw |
| `luckyus-prod-80-new-groupconcatmaxlen` | mysql8.0 | 1 | salesorder-rw |
| `default.mysql8.4` | mysql8.4 | 2 | dba84test-rw, datalink-84test-rw |
| **luckyus-prod-84-new** | mysql8.4 | 0 | **NOT CREATED YET** |
| **luckyus-prod-84-new-groupconcatmaxlen** | mysql8.4 | 0 | **NOT CREATED YET** |

---

## Anomaly Flags

### FLAG 1: Parameter Apply Status != in-sync

| Instance | Version | Parameter Group | Status | Action |
|----------|---------|----------------|--------|--------|
| aws-luckyus-dbatest-rw | 8.0.42 | luckyus-prod-80-new | **pending-reboot** | Reboot to apply pending parameter changes (test instance, low risk) |

### FLAG 2: Instances on Legacy Parameter Group (`luckyus-prod`)

| Instance | Version | Missing vs luckyus-prod-80-new |
|----------|---------|-------------------------------|
| aws-luckyus-devops-rw | 8.0.40 | `log_bin_trust_function_creators=1`, `lower_case_table_names=1` |
| aws-luckyus-ldas-rw | 8.0.40 | `log_bin_trust_function_creators=1`, `lower_case_table_names=1` |

> **Verified safe (2026-04-10)**: Both instances have all-lowercase table/database names. Migration to `luckyus-prod-84-new` will add these 2 missing params with no breaking impact.

### FLAG 3: 8.4 Test Instances on Default Parameter Group

| Instance | Version | Current PG | Target PG |
|----------|---------|-----------|-----------|
| aws-luckyus-dba84test-rw | 8.4.7 | default.mysql8.4 | luckyus-prod-84-new |
| aws-luckyus-datalink-84test-rw | 8.4.7 | default.mysql8.4 | luckyus-prod-84-new |

> **Action**: Switch to `luckyus-prod-84-new` AFTER creation, BEFORE production upgrades begin. This validates the parameter group on 8.4 before fleet rollout.

### FLAG 4: Version Outliers (non-standard minor versions)

| Instance | Version | Majority Version | Notes |
|----------|---------|-----------------|-------|
| aws-luckyus-dbatest-rw | 8.0.42 | 8.0.40 | Test instance, slightly ahead |
| aws-luckyus-iluckyams-rw | 8.0.44 | 8.0.40 | `auto_minor_upgrade=true` caused drift |
| aws-luckyus-ldas01-rw | 8.0.41 | 8.0.40 | Slightly ahead |

> These version differences do not affect the upgrade plan — all will go to 8.0.45 → 8.4.8 per the two-phase strategy.

---

## CSV Cross-Reference

**Live AWS (63 instances)** vs **CSV `/app/affected_instances.csv` (61 rows)**:
- CSV does not include: `dba84test-rw`, `datalink-84test-rw` (8.4 test instances — created after CSV)
- All 61 CSV instances confirmed present in live AWS
- Parameter group assignments match between CSV and live for all instances
- `dbatest-rw` shows `pending-reboot` in both CSV and live — consistent

---

## Full Instance List

| # | Instance | Version | Parameter Group | Status |
|---|----------|---------|----------------|--------|
| 1 | aws-luckyus-cdpactivity-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 2 | aws-luckyus-datalink-84test-rw | 8.4.7 | default.mysql8.4 | in-sync |
| 3 | aws-luckyus-dba84test-rw | 8.4.7 | default.mysql8.4 | in-sync |
| 4 | aws-luckyus-dbatest-rw | 8.0.42 | luckyus-prod-80-new | pending-reboot |
| 5 | aws-luckyus-devops-rw | 8.0.40 | luckyus-prod | in-sync |
| 6 | aws-luckyus-fichargecontrol-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 7 | aws-luckyus-fitax-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 8 | aws-luckyus-framework01-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 9 | aws-luckyus-framework02-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 10 | aws-luckyus-iadmin-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 11 | aws-luckyus-ibillingcentersrv-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 12 | aws-luckyus-ibizconfigcenter-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 13 | aws-luckyus-icyberdata-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 14 | aws-luckyus-iehr-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 15 | aws-luckyus-ifiaccounting-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 16 | aws-luckyus-igers-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 17 | aws-luckyus-ijumpserver-jumpserver-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 18 | aws-luckyus-ilsopdevopsdata-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 19 | aws-luckyus-iluckyams-rw | 8.0.44 | luckyus-prod-80-new | in-sync |
| 20 | aws-luckyus-iluckyauthapi-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 21 | aws-luckyus-iluckydorisops-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 22 | aws-luckyus-iluckyhealth-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 23 | aws-luckyus-iluckymedia-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 24 | aws-luckyus-iopenadmin-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 25 | aws-luckyus-iopenlinker-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 26 | aws-luckyus-iopenservice-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 27 | aws-luckyus-iopocp-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 28 | aws-luckyus-iopshopexpand-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 29 | aws-luckyus-iotplatform-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 30 | aws-luckyus-ipermission-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 31 | aws-luckyus-ireplenishment-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 32 | aws-luckyus-iriskcontrolservice-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 33 | aws-luckyus-isalescdp-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 34 | aws-luckyus-isalesdatamarketing-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 35 | aws-luckyus-isalesmembermarketing-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 36 | aws-luckyus-isalesprivatedomain-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 37 | aws-luckyus-iunifiedreconcile-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 38 | aws-luckyus-iworkflowmidlayer-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 39 | aws-luckyus-ldas01-rw | 8.0.41 | luckyus-prod-80-new | in-sync |
| 40 | aws-luckyus-ldas-rw | 8.0.40 | luckyus-prod | in-sync |
| 41 | aws-luckyus-mfranchise-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 42 | aws-luckyus-opempefficiency-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 43 | aws-luckyus-oplog-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 44 | aws-luckyus-opproduction-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 45 | aws-luckyus-opqualitycontrol-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 46 | aws-luckyus-opshop-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 47 | aws-luckyus-opshopsale-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 48 | aws-luckyus-pubdm-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 49 | aws-luckyus-salescrm-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 50 | aws-luckyus-salesmarketing-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 51 | aws-luckyus-salesorder-rw | 8.0.40 | luckyus-prod-80-new-groupconcatmaxlen | in-sync |
| 52 | aws-luckyus-salespayment-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 53 | aws-luckyus-scm-asset-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 54 | aws-luckyus-scmcommodity-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 55 | aws-luckyus-scm-openapi-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 56 | aws-luckyus-scm-ordering-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 57 | aws-luckyus-scm-plan-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 58 | aws-luckyus-scm-purchase-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 59 | aws-luckyus-scm-shopstock-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 60 | aws-luckyus-scmsrm-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 61 | aws-luckyus-scm-wds-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 62 | aws-luckyus-scm-wmssimulate-rw | 8.0.40 | luckyus-prod-80-new | in-sync |
| 63 | aws-luckyus-upush-rw | 8.0.40 | luckyus-prod-80-new | in-sync |

---

## Upgrade Migration Plan (Parameter Group Transitions)

| Current PG | Count | Target PG | Notes |
|------------|-------|-----------|-------|
| luckyus-prod-80-new | 56 | luckyus-prod-84-new | Standard migration |
| luckyus-prod | 2 | luckyus-prod-84-new | devops, ldas gain 2 missing params |
| luckyus-prod-80-new-groupconcatmaxlen | 1 | luckyus-prod-84-new-groupconcatmaxlen | salesorder keeps group_concat_max_len |
| default.mysql8.4 | 2 | luckyus-prod-84-new | Test instances switch from default |
| **Total** | **63** | | **2 target parameter groups** |
