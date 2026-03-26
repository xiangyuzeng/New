# Alert System Upgrade Proposal — Data Collection & Gap Analysis Plan

## Context

Luckin Coffee North America is preparing a management-facing proposal (告警体系升级提案) for HQ in China. The proposal compares the **OLD** alert system (135 rules, 16 categories, P0-P3) with the **NEW** three-tier system (165 rules, 11 categories, Info/Warning/Critical). This task is **pure data collection and analysis** — no dashboard or UI will be built.

### Key Discovery: Three Evolution Stages
The alert system has three stages, not two:
1. **OLD** (legacy): 135 rules, 16 categories, P0/P1/P2/P3 priority — with _语音 duplicates, iZeus strategy duplicates, day/night pairs
2. **INTERMEDIATE** (2026-02-14): 72 rules, 10 categories, Info/Warning/Critical — the first consolidation
3. **NEW** (2026-03-25): 165 rules, 11 categories, Info/Warning/Critical — full three-tier expansion (every metric gets 3 severity levels)

### Data Sources (All Local)
| File | Path | Content |
|------|------|---------|
| Three-tier YAML | `/app/reports/alert-rules-three-tier-full-2026-03-25.yaml` | 165 rules, 1878 lines |
| Optimization report | `/app/reports/alert-rules-optimization-2026-03-25.md` | 29 proposals, incidents, thresholds |
| Validation report | `/app/reports/alert-optimization-validation-report.md` | Cross-validation, gaps, priority matrix |
| Alert inventory | `/app/alertrebuild/alert-inventory.md` | Complete ALR-001→ALR-135 mapping to 72 new rules |
| Old rules YAML | `/app/alertrebuild/alert-rules-complete.yml` | 72 rules + 14 recording rules (2057 lines) |
| Alertmanager config | `/app/alertrebuild/alertmanager-config.yml` | Routing, inhibition, muting (165 lines) |
| Completeness audit | `/app/alertrebuild/alert-definition-completeness-audit.md` | Gap analysis (546 lines) |
| Migration plan | `/app/alertrebuild/migration-plan.md` | Phased migration (436 lines) |
| Incident: Redis 02-10 | `/app/redis-memory-alert-luckyus-isales-market-2026-02-10.md` | Redis memory spike RCA |
| Incident: Redis 02-12 | `/app/reports/redis-memory-alert-luckyus-isales-market-2026-02-12.md` | Redis 2nd occurrence RCA |
| Incident: isalescdp | `/app/rds-isalescdp-alert-analysis-2026-02-11.md` | RDS OOM failover RCA |
| Dashboard HTML | `/app/alertrebuild/alert-dashboard.html` | 95KB interactive alert dashboard |
| Runbooks | `/app/alertrebuild/runbooks-part-*.md` | 8 runbook files, ~300KB total |

**Note:** `/mnt/user-data/uploads/` does not exist. All input files are in `/app/reports/` and `/app/alertrebuild/`.

### External URLs to Fetch
1. `https://luckin-alert-dashboard-old.vercel.app/` — old alert dashboard (likely SPA)
2. `https://luckin-alert-dashboard-new.vercel.app/` — new alert dashboard (likely SPA)
3. `https://alert-system-report.vercel.app/` — upgrade report site

---

## Phase 1: Old System Archaeology (Tasks 1-3)

### Task 1 — Extract old system rules (ALL 135)
**Sources:** `/app/alertrebuild/alert-inventory.md` (primary — has complete ALR-001 to ALR-135 mapping)
**Also fetch:** `https://luckin-alert-dashboard-old.vercel.app/` to attempt extraction of PromQL expressions
**Also read:** `/app/alertrebuild/alert-dashboard.html` (may contain embedded rule data)

**Extract for each of 135 old rules:**
- Old ID (ALR-XXX), Chinese name, priority (P0/P1/P2/P3)
- Category (one of 16 old categories)
- Disposition: ELIMINATE / MERGE / KEEP / SPLIT
- New ID mapping (LCK-XX-NNN)
- PromQL expression if available (from dashboard HTML or web fetch)

**Compute:**
- Priority distribution: P0=41, P1=?, P2=?, P3=?
- Category distribution (16 categories with counts)
- _语音 duplicate list (7 pairs)
- PromQL duplicate list (8 pairs)
- iZeus strategy duplicate list (8 rules)
- DataLink day/night pairs (10 rules merged to 4)

### Task 2 — Extract report site content
**Action:** Fetch all 3 external URLs. For each:
1. Try HTML source for inline data (__NEXT_DATA__, bundled JSON, static data)
2. If SPA with no data, document the attempt and note as data gap
**Expected:** These are likely client-rendered SPAs; primary data is already in local files. URL fetch is best-effort.

### Task 3 — Old system gap identification
**Source:** Cross-reference alert-inventory.md against the new YAML
**Output:**
- New metrics with ZERO coverage in old 135 rules (e.g., FreeableMemory, SwapUsage, MSK ConsumerLag, ExporterDown)
- List every eliminated rule with reason
- List every rule that was split into 3 tiers

---

## Phase 2: New System Complete Extraction (Tasks 4-6)

### Task 4 — Parse full YAML (165 rules)
**Source:** `/app/reports/alert-rules-three-tier-full-2026-03-25.yaml`
**Extract for each rule (NO truncation):**
- alert_name, category (labels.category), severity (labels.severity)
- expr (COMPLETE PromQL), for_duration
- summary (annotations.summary), description (annotations.description)
- All other labels and annotations

**Organize by:** category group (11 groups)
**Verify:** total == 165, balanced 55/55/55 across severity tiers

### Task 5 — Category-level statistics
**For each of 11 categories compute:**
- Rule count per severity tier
- Unique metric names in expressions
- Expression pattern per rule: absolute | ratio | compound | boolean | rate-of-change | histogram | custom
- Average and range of for_duration per severity tier
- Which rules have compound conditions (OR, AND)
- Which rules reference recording rules vs raw metrics

### Task 6 — Alertmanager routing analysis
**Sources:** `/app/alertrebuild/alertmanager-config.yml` + YAML labels + validation report
**Extract:**
- Inhibition rules (3 defined): source/target matchers, equal labels, feasibility
- Routing tree: severity → receiver mapping with group_by, intervals
- Time-based muting: us-offhours-non-biz (07:00-12:00 UTC weekdays)
- Labels present on ALL vs SOME rules
- Labels MISSING but needed (from validation report: alert_group, env, instance, team, service)

---

## Phase 3: Incident Cross-Reference (Task 7)

### Task 7 — Real incident compilation
**Sources:** Incident report files + optimization report + validation report

**Known incidents to document:**

| Date | System | Source File |
|------|--------|-------------|
| 2026-02-10 | Redis isales-market memory surge | `/app/redis-memory-alert-luckyus-isales-market-2026-02-10.md` |
| 2026-02-11 | RDS iluckyhealth active threads | `/app/rds-isalescdp-alert-analysis-2026-02-11.md` |
| 2026-02-12 | Redis isales-market 2nd occurrence | `/app/reports/redis-memory-alert-luckyus-isales-market-2026-02-12.md` |
| 2026-02-12 | ES luckylfe-log cluster Yellow | Optimization report (inline reference) |
| 2026-03-12 | isalescdp RDS OOM failover | Optimization report (inline reference) |

**For each incident output:**
- date_utc, date_est, affected_system, alert_that_fired, alert_that_should_have_fired
- root_cause, resolution, new_rule_that_covers_it, new_rule_promql
- estimated_earlier_detection (minutes/hours)

---

## Phase 4: Before/After Delta Analysis (Tasks 8-10)

### Task 8 — Rule migration mapping
**Source:** `/app/alertrebuild/alert-inventory.md` (already has complete ALR→LCK mapping)
**Then:** Map LCK (72-rule intermediate) → new YAML (165-rule final)

**Build two-stage mapping:**
1. OLD (ALR-001..135) → INTERMEDIATE (LCK-XX-NNN, 72 rules) — from alert-inventory.md
2. INTERMEDIATE (72 rules) → NEW (165 rules) — by comparing alert-rules-complete.yml with new YAML

**Summary stats:**
- rules_eliminated: 63 (4 meta + 7 _语音 + 8 PromQL dup + 8 iZeus dup + 10 DataLink + 9 VM/K8S + 17 Platform)
- rules_split_to_3_tiers: count from inventory
- completely_new_rules: rules in 165 not traceable to any ALR
- expressions_improved: rules where PromQL changed between old→intermediate→new

### Task 9 — Threshold comparison table
**Source:** Optimization report threshold table + cross-reference with YAML
**For every metric in BOTH old and new:**
| metric | old_threshold | new_info | new_warning | new_critical | change_type |

### Task 10 — Notification routing comparison
**Sources:** Alertmanager config + alert-inventory.md + optimization report
**Document side by side:**
- Old: P0→voice+WeCom, P1→WeCom, P2→WeCom, P3→dashboard only
- New: info→WeCom text, warning→WeCom+Twilio lead, critical→WeCom+Twilio all DevOps
- WeCom: single channel → three separate channels
- Twilio: hardcoded _语音 rules → severity-based routing
- iZeus: all alerts forwarded (new: webhook with continue:true)
- Time muting: none (old) → us-offhours-non-biz weekdays 07:00-12:00 UTC (new)

---

## Phase 5: Validation Gap Compilation (Tasks 11-12)

### Task 11 — Extract all validation findings
**Source:** `/app/reports/alert-optimization-validation-report.md`
**Extract into structured lists:**
- 29 proposals with status (DONE/PARTIAL/NOT_DONE)
- PromQL issues (high/medium/low severity)
- Inhibition feasibility issues (5 items)
- Missing label gaps (6 items)
- Coverage gaps high-priority (6 items)
- Coverage gaps medium-priority (9 items)
- Risk flags (5 items)
- Priority matrix tasks (P0-P3, ~40 items)

### Task 12 — Cross-document contradictions
**Compare:** Optimization report vs validation report vs YAML
**Known contradictions to verify:**
1. Optimization report describes 72-rule baseline (2026-02-14), not 165-rule YAML (2026-03-25)
2. REDIS-04 Warning: report proposes 75% + PreCritical 88%, YAML still at 80%
3. Inhibition: report proposes `alertname_prefix` label, YAML doesn't have it
4. `mongo_mem_*` vs `aws_docdb_*` metric names
5. PLAT Gateway Critical: report says 20%, YAML has 15%
6. Batch maintenance window: report says 04:30-06:30 UTC, Alertmanager has 07:00-12:00 UTC

---

## Phase 6: Architecture & Infrastructure Context (Tasks 13-14)

### Task 13 — Infrastructure inventory
**Sources:** CLAUDE.md + alert files + incident reports
**Compile:**
- AWS account 257394478466, us-east-1
- 233 EC2, 143 DB instances (62 MySQL, 3 PostgreSQL, 78 Redis, 4 DocumentDB, 2 OpenSearch)
- Monitoring stack: Prometheus, VictoriaMetrics (VMAlert), Grafana, CloudWatch, iZeus
- Alertmanager routing: WeCom webhooks (3 channels), Twilio (proxy at localhost:9097), iZeus webhook
- Rule file location: Alertmanager + VMAlert

### Task 14 — Three-tier design rationale
**Document from all sources:**
- Why 3 tiers: P0→Critical, P1→Warning, P2+P3→Info (merge low priorities)
- Response SLA: info=next business day, warning=30min, critical=immediate
- Notification scope per tier (who gets notified)
- for_duration pattern: info 5-10m, warning 3-5m, critical 1-3m
- Exceptions with reasoning (Failover 0m, VipUnreachable 30s/45s/1m)

---

## Phase 7: Expression Quality Audit (Tasks 15-16)

### Task 15 — Validate all 165 PromQL expressions
**Source:** YAML file — check every expression for:
- Balanced parentheses
- Valid function usage (rate/increase need range vectors, histogram_quantile args)
- Division-by-zero risk (ratios without guard clauses)
- Metric name consistency per category
- Label selector completeness
- for_duration ordering: info >= warning >= critical per alert group (flag violations)

### Task 16 — Expression pattern statistics
**Compare old vs new:**
- Old: absolute-only thresholds vs ratio-based (from 72-rule YAML + inventory)
- New: absolute vs compound (pct OR abs) vs ratio
- Guard clause usage (AND min_volume > N)
- Recording rule vs inline computation

---

## Output Files

### File 1: `/home/claude/alert-proposal-data.json`
Complete structured JSON with ALL collected data (~16 sections matching the schema in the user prompt). Must be valid JSON — verify with `python3 -c 'import json; json.load(...)'`.

### File 2: `/home/claude/alert-proposal-data-summary.md`
Human-readable summary:
- Executive summary of findings
- Data completeness checklist (16 tasks: found/missing/partial)
- Top 10 proposal-worthy findings
- Recommended dashboard tab structure
- Data gaps requiring manual input

### File 3: Copy both to `/mnt/user-data/outputs/` (create dir if needed)

---

## Execution Order

```
1. Read all local files first (Tasks 1,3,4-6,7,8-12,13-14,15-16)
   - Parse YAML completely (Task 4)
   - Read alert-inventory.md completely (Task 1,8)
   - Read all incident reports (Task 7)
   - Read optimization + validation reports (Tasks 11-12)
   - Read alertmanager config (Task 6)
   - Read old alert-rules-complete.yml (Task 8,16)

2. Attempt external fetches (Task 2) — best-effort, max 2 retries per URL

3. Cross-reference and analyze (Tasks 3,5,9,10,15,16)

4. Build JSON output (all tasks → alert-proposal-data.json)

5. Write summary (alert-proposal-data-summary.md)

6. Validate JSON and copy outputs
```

## Potential Blockers
- External URLs are likely SPAs → document as data gap, proceed with local data
- Old system PromQL expressions may not be extractable → note gap, rely on names/thresholds
- `/mnt/user-data/outputs/` doesn't exist → create it or use `/app/reports/` as fallback
- Some incidents referenced only briefly in reports → extract what's available, flag incomplete

## Verification
- JSON validation: `python3 -c 'import json; json.load(open("/home/claude/alert-proposal-data.json"))'`
- Rule count verification: 135 old + 165 new rules accounted for
- Cross-check: every ALR-XXX has a disposition, every new rule has a source
- Expression count: all 165 PromQL expressions captured complete (no truncation)
