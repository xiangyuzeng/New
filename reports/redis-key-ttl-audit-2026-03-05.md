# Redis Key Pattern & TTL Audit Report

**Date:** 2026-03-05
**Author:** David Zeng (DBA)
**Scope:** All 77 Redis clusters via mcp-db-gateway
**Environment:** Luckin Coffee USA (AWS us-east-1)

---

## Executive Summary

Audited all 77 ElastiCache Redis clusters. Key findings:

- **Total keys across all clusters:** ~6.9M+ keys
- **Critical concern:** `luckyus-isales-market` holds 6.14M keys with 3.46M (56.4%) lacking TTL expiry — a memory leak risk at 1.35G / 4.79G (28.2%)
- **5 clusters with keys missing TTL** (no-expire keys) that need attention
- **2 clusters with extremely long avg TTL** (>100 days): `ldas`, `isales-market`
- **12 clusters are empty** (no keys in keyspace)
- All clusters use `volatile-lfu` eviction policy except `luckyus-redis-dify` (`volatile-lru`)

---

## 1. Memory Usage Baseline (Top 20 by Used Memory)

| Rank | Cluster | Used Memory | Max Memory | Usage % | Peak Memory | Frag Ratio |
|------|---------|-------------|------------|---------|-------------|------------|
| 1 | luckyus-isales-market | 1.35G | 4.79G | 28.2% | — | — |
| 2 | luckyus-web | 529.94M | 2.32G | 22.3% | — | 1.05 |
| 3 | luckyus-isales-tradecapi | ~94.56M | 384M | 24.7% | — | — |
| 4 | luckyus-isales-order | ~64.66M | 384M | 16.9% | — | — |
| 5 | luckyus-isales-crm | ~48.28M | 384M | 12.6% | — | — |
| 6 | luckyus-aapi-unionauth | 29.94M | 384M | 7.8% | — | — |
| 7 | luckyus-unionauth | 21.37M | 384M | 5.6% | — | 1.82 |
| 8 | luckyus-iopenlinker | ~18.20M | 384M | 4.7% | — | — |
| 9 | luckyus-isales-commodity | ~17.42M | 384M | 4.5% | — | — |
| 10 | luckyus-iopenauth | ~12.83M | 384M | 3.3% | — | — |
| 11 | luckyus-ipushnet | ~12.20M | 384M | 3.2% | — | — |
| 12 | luckyus-jumpserver | 12.17M | 1.03G | 1.2% | — | 2.45 |
| 13 | luckyus-redis-dify | 10.50M | 4.79G | 0.2% | — | 2.76 |
| 14 | luckyus-sapi-unionauth | 8.40M | 384M | 2.2% | — | 3.18 |
| 15 | luckyus-koala | 7.51M | 384M | 2.0% | — | 2.89 |
| 16 | luckyus-onepiece | 7.08M | 384M | 1.8% | 87.68M | 2.32 |
| 17 | luckyus-scm-commodity | 6.88M | 384M | 1.8% | — | 2.79 |
| 18 | luckyus-open-unionauth | 6.82M | 384M | 1.8% | — | 3.39 |
| 19 | luckyus-shop | 6.23M | 384M | 1.6% | — | 2.88 |
| 20 | luckyus-lkmap | 5.66M | 1.03G | 0.5% | — | 2.78 |

### Memory Tier Distribution

| Tier | Maxmemory | Count | Clusters |
|------|-----------|-------|----------|
| Large | 4.79G | 2 | isales-market, redis-dify |
| Medium | 2.32G | 1 | web |
| Standard+ | 1.03G | 2 | jumpserver, lkmap |
| Standard | 384M | 72 | All others |

---

## 2. Keyspace Analysis — Full Inventory (77 Clusters)

### 2.1 Clusters by Key Count (Descending)

| Cluster | DB | Total Keys | With Expires | No Expires | Expire % | Avg TTL | TTL Human |
|---------|-----|-----------|-------------|------------|----------|---------|-----------|
| luckyus-isales-market | db0 | 6,136,943 | 2,675,706 | 3,461,237 | 43.6% | 14,278s | ~165 days |
| luckyus-isales-crm | db0 | 306,350 | 306,350 | 0 | 100% | 223,798s | ~2.6 days |
| luckyus-iupush | db0 | 295,396 | 295,392 | 4 | 100% | 744,629s | ~8.6 days |
| luckyus-isales-session | db0 | 142,235 | 142,235 | 0 | 100% | 3,288,302s | ~38.1 days |
| luckyus-web | db1 | 78,147 | 77,983 | 164 | 99.8% | 977,856s | ~11.3 days |
| luckyus-ipushnet | db0 | 24,866 | 24,866 | 0 | 100% | 113,043s | ~1.3 days |
| luckyus-iopenauth | db0 | 23,976 | 23,976 | 0 | 100% | 573,027s | ~6.6 days |
| luckyus-unionauth | db0 | 22,777 | 22,776 | 1 | 100% | 1,809s | ~30 min |
| luckyus-scm-shopstock | db0 | 7,775 | 7,775 | 0 | 100% | 38,115s | ~10.6 hrs |
| luckyus-iriskcontrol | db0 | 5,211 | 5,211 | 0 | 100% | 67,425s | ~18.7 hrs |
| luckyus-cmdb | db0 | 5,020 | 5,020 | 0 | 100% | 31,137s | ~8.6 hrs |
| luckyus-isales-datamarket | db0 | 3,411 | 3,411 | 0 | 100% | 54,080s | ~15.0 hrs |
| luckyus-ocp | db0 | 2,966 | 2,966 | 0 | 100% | 3,545s | ~59 min |
| luckyus-aapi-unionauth | db0 | 2,602 | 2,601 | 1 | 100% | 704,782s | ~8.2 days |
| luckyus-isales-privatedomain | db0 | 1,602 | 1,602 | 0 | 100% | 68,281s | ~19.0 hrs |
| luckyus-isales-marketcapi | db0 | 1,481 | 1,481 | 0 | 100% | 2,960,581s | ~34.3 days |
| luckyus-sapi-unionauth | db0 | 1,364 | 1,364 | 0 | 100% | 5,756s | ~1.6 hrs |
| luckyus-iopenlinker | db0 | 1,054 | 1,053 | 1 | 99.9% | 1,030,089s | ~11.9 days |
| luckyus-scm-commodity | db0 | 1,053 | 1,053 | 0 | 100% | 1,837s | ~30.6 min |
| luckyus-isales-commodity | db0 | 867 | 867 | 0 | 100% | 109s | ~1.8 min |
| luckyus-shop | db0 | 660 | 652 | 8 | 98.8% | 431,187s | ~5.0 days |
| luckyus-scm-wds | db0 | 495 | 485 | 10 | 97.9% | 2,274s | ~38 min |
| luckyus-session | db0 | 448 | 410 | 38 | 91.5% | 3,535s | ~59 min |
| luckyus-ldas | db0 | 440 | 439 | 1 | 99.8% | 11,674,295s | ~135 days |
| luckyus-onepiece | db0 | 407 | 407 | 0 | 100% | 46,375s | ~12.9 hrs |
| luckyus-chronus | db0 | 361 | 0 | 361 | 0% | 0 | **NO TTL** |
| luckyus-scm-sims | db0 | 276 | 272 | 4 | 98.6% | 4,382s | ~1.2 hrs |
| luckyus-waf | db0 | 248 | 248 | 0 | 100% | 4s | ~3.8s |
| luckyus-isales-tradecapi | db0 | 232 | 232 | 0 | 100% | 413s | ~6.9 min |
| luckyus-isales-order | db0 | 181 | 181 | 0 | 100% | 16,752s | ~4.7 hrs |
| luckyus-auth | db0 | 176 | 176 | 0 | 100% | 288,329s | ~3.3 days |
| luckyus-authservice | db0 | 146 | 146 | 0 | 100% | 283,229s | ~3.3 days |
| luckyus-iotplatform | db0 | 127 | 126 | 1 | 99.2% | 14s | ~14s |
| luckyus-bigdata-cyberdata | db1 | 89 | 25 | 64 | 28.1% | 44,870s | ~12.5 hrs |
| luckyus-scm-ordering | db0 | 70 | 68 | 2 | 97.1% | 27,476s | ~7.6 hrs |
| luckyus-scm-commodityadmin | db0 | 70 | 0 | 70 | 0% | 0 | **NO TTL** |
| luckyus-isales-member | db0 | 35 | 35 | 0 | 100% | 151s | ~2.5 min |
| luckyus-production | db0 | 43 | 43 | 0 | 100% | 25,965s | ~7.2 hrs |
| luckyus-qualitycontrol | db0 | 22 | 22 | 0 | 100% | 788,854s | ~9.1 days |
| luckyus-billcenterservice | db0 | 22 | 22 | 0 | 100% | 572s | ~9.5 min |
| luckyus-shopsale | db0 | 18 | 18 | 0 | 100% | 91,791s | ~1.1 days |
| luckyus-scm-purchase | db0 | 18 | 17 | 1 | 94.4% | 43,355s | ~12.0 hrs |
| luckyus-ifiaccounting | db0 | 16 | 8 | 8 | 50.0% | 704,928s | ~8.2 days |
| luckyus-empefficiency | db0 | 14 | 13 | 1 | 92.9% | 6,666s | ~1.9 hrs |
| luckyus-iadmin | db0 | 12 | 12 | 0 | 100% | 65,677s | ~18.2 hrs |
| luckyus-scm-asset | db0 | 12 | 2 | 10 | 16.7% | 81,042s | ~22.5 hrs |
| luckyus-redis-dify | db0+db1 | 11 | 1 | 10 | 9.1% | — | mixed |
| luckyus-iehr | db0 | 9 | 9 | 0 | 100% | 1,744s | ~29 min |
| luckyus-imessageflow | db0 | 8 | 8 | 0 | 100% | 1,409s | ~23 min |
| luckyus-daq | db0 | 4 | 0 | 4 | 0% | 0 | **NO TTL** |
| luckyus-mdm | db0 | 4 | 0 | 4 | 0% | 0 | **NO TTL** |
| luckyus-scm-srm | db0 | 3 | 2 | 1 | 66.7% | 69,499s | ~19.3 hrs |
| luckyus-scmwmssimulate | db0 | 4 | 3 | 1 | 75.0% | 61,152s | ~17.0 hrs |
| luckyus-ipermission | db0 | 3 | 3 | 0 | 100% | 43,985s | ~12.2 hrs |
| luckyus-ibizconfigcenter | db0 | 2 | 2 | 0 | 100% | 46,895s | ~13.0 hrs |
| luckyus-ifichargecontrol | db0 | 2 | 1 | 1 | 50.0% | 65,525s | ~18.2 hrs |
| luckyus-iworkflowmidlayer | db0 | 2 | 2 | 0 | 100% | 655s | ~10.9 min |
| luckyus-ilkm | db0 | 1 | 1 | 0 | 100% | 3,599s | ~1 hr |
| luckyus-koala | db0 | 1 | 0 | 1 | 0% | 0 | **NO TTL** |
| luckyus-iopenadmin | db0 | 1 | 0 | 1 | 0% | 0 | **NO TTL** |

### 2.2 Empty Clusters (No Keys)

| Cluster | Status |
|---------|--------|
| luckyus-apigateway | empty |
| luckyus-bigdata-dataplatform | empty |
| luckyus-devops | empty |
| luckyus-franchise | empty |
| luckyus-ifitax | empty |
| luckyus-igers | empty |
| luckyus-ilopamanager | empty |
| luckyus-iopenlinkeradmin | empty |
| luckyus-iopenservice | empty |
| luckyus-iunifiedreconcile | empty |
| luckyus-lkmap | empty |
| luckyus-open-unionauth | empty |
| luckyus-pub-dm | empty |
| luckyus-shopexpand | empty |

**14 clusters (18.2%) are completely empty** — candidates for decommissioning or review.

---

## 3. TTL Health Analysis

### 3.1 Clusters with Keys Missing TTL (Risk: Memory Leak)

| Cluster | No-Expire Keys | Total Keys | No-Expire % | Severity |
|---------|---------------|------------|-------------|----------|
| **luckyus-isales-market** | **3,461,237** | 6,136,943 | **56.4%** | **CRITICAL** |
| luckyus-chronus | 361 | 361 | 100% | MEDIUM |
| luckyus-scm-commodityadmin | 70 | 70 | 100% | LOW |
| luckyus-bigdata-cyberdata | 64 | 89 | 71.9% | LOW |
| luckyus-session | 38 | 448 | 8.5% | LOW |
| luckyus-scm-asset | 10 | 12 | 83.3% | LOW |
| luckyus-redis-dify (db1) | 8 | 8 | 100% | LOW |
| luckyus-ifiaccounting | 8 | 16 | 50.0% | LOW |
| luckyus-scm-wds | 10 | 495 | 2.0% | LOW |
| luckyus-shop | 8 | 660 | 1.2% | LOW |
| luckyus-web | 164 | 78,147 | 0.2% | LOW |
| luckyus-daq | 4 | 4 | 100% | INFO |
| luckyus-mdm | 4 | 4 | 100% | INFO |
| luckyus-koala | 1 | 1 | 100% | INFO |
| luckyus-iopenadmin | 1 | 1 | 100% | INFO |

### 3.2 Clusters with Extremely Long TTLs

| Cluster | Avg TTL | Human Readable | Risk |
|---------|---------|----------------|------|
| **luckyus-isales-market** | 14,278,197s | ~165 days | HIGH — effectively permanent |
| **luckyus-ldas** | 11,674,295s | ~135 days | HIGH — effectively permanent |
| luckyus-isales-session | 3,288,302s | ~38.1 days | MEDIUM — unusually long for sessions |
| luckyus-isales-marketcapi | 2,960,581s | ~34.3 days | MEDIUM |
| luckyus-web | 977,856s | ~11.3 days | MONITOR |
| luckyus-iupush | 744,629s | ~8.6 days | MONITOR |
| luckyus-ifiaccounting | 704,928s | ~8.2 days | MONITOR |
| luckyus-aapi-unionauth | 704,782s | ~8.2 days | OK — auth tokens |
| luckyus-qualitycontrol | 788,854s | ~9.1 days | MONITOR |

### 3.3 TTL Distribution Summary

| TTL Range | Cluster Count | Examples |
|-----------|--------------|----------|
| No keys (empty) | 14 | apigateway, devops, franchise, etc. |
| < 1 minute | 3 | waf (3.8s), iotplatform (14s), isales-commodity (1.8 min) |
| 1 min – 1 hour | 10 | unionauth (30 min), ocp (59 min), scm-commodity (30.6 min) |
| 1 hour – 1 day | 14 | iriskcontrol (18.7 hrs), scm-shopstock (10.6 hrs) |
| 1 – 7 days | 10 | isales-crm (2.6 days), auth (3.3 days), shop (5 days) |
| 7 – 30 days | 6 | web (11.3 days), iopenauth (6.6 days), qualitycontrol (9.1 days) |
| 30+ days | 4 | isales-session (38 days), isales-marketcapi (34 days) |
| 100+ days | 2 | **isales-market (165 days), ldas (135 days)** |
| No TTL (all keys permanent) | 6 | chronus, scm-commodityadmin, daq, mdm, koala, iopenadmin |

---

## 4. Critical Findings & Recommendations

### CRITICAL: luckyus-isales-market — Memory Leak Risk

- **6,136,943 total keys** — largest cluster by far
- **3,461,237 keys (56.4%) have NO expiry** — these keys will never be evicted unless maxmemory is hit
- **Average TTL of ~165 days** on keys that do have expiry — effectively permanent
- Memory: 1.35G / 4.79G (28.2%) — growing toward capacity
- **Action Required:**
  1. Identify key patterns without TTL: run `SCAN` + `TTL` sampling on representative keys
  2. Coordinate with isales-market dev team to add TTL to all new keys
  3. Implement cleanup script for orphaned keys (ref: `/app/runbooks/redis-isales-market-remediation/`)
  4. Set up Prometheus alert for `redis_db_keys` growth rate

### HIGH: luckyus-ldas — Extremely Long TTL

- 440 keys with avg TTL of ~135 days
- Low key count, but pattern suggests data is being cached far too long
- **Action:** Review with analytics team whether cache invalidation is needed

### MEDIUM: luckyus-isales-session — Unusual Session TTL

- 142,235 session keys with avg TTL of ~38.1 days
- Session data typically should expire in hours, not weeks
- **Action:** Verify session expiry policy with application team

### MEDIUM: luckyus-chronus — 361 Keys with Zero TTL

- All 361 keys are permanent (no expiry)
- Chronus is a job scheduler — keys may be intentional config data
- **Action:** Confirm with DevOps whether these are intentional persistent keys

### LOW: 14 Empty Clusters

- 14 clusters (18.2%) have zero keys but are still running and incurring costs
- **Action:** Review with application teams whether these clusters are still needed
- Potential savings: 14 × cache.t3.micro or equivalent monthly cost

### LOW: luckyus-redis-dify — Unique Eviction Policy

- Only cluster using `volatile-lru` instead of `volatile-lfu`
- db1 has 8 keys with NO expires — volatile-lru won't evict these
- **Action:** Verify if `volatile-lfu` should be standardized here too

---

## 5. Eviction Policy Summary

| Policy | Count | Clusters |
|--------|-------|----------|
| volatile-lfu | 76 | All clusters except redis-dify |
| volatile-lru | 1 | luckyus-redis-dify |

**Note:** `volatile-lfu`/`volatile-lru` policies only evict keys **with an expire set**. Keys without TTL will NEVER be evicted — they will persist until manually deleted or maxmemory causes OOM errors. This makes the no-expire keys in `isales-market` particularly dangerous.

---

## 6. Cluster Utilization Categories

### Active (>1,000 keys) — 15 clusters
luckyus-isales-market, isales-crm, iupush, isales-session, web, ipushnet, iopenauth, unionauth, scm-shopstock, iriskcontrol, cmdb, isales-datamarket, ocp, aapi-unionauth, isales-privatedomain

### Light Use (10–999 keys) — 26 clusters
isales-marketcapi, sapi-unionauth, iopenlinker, scm-commodity, isales-commodity, shop, scm-wds, session, ldas, onepiece, chronus, scm-sims, waf, isales-tradecapi, isales-order, auth, authservice, iotplatform, bigdata-cyberdata, scm-ordering, scm-commodityadmin, isales-member, production, qualitycontrol, billcenterservice, shopsale

### Minimal (<10 keys) — 22 clusters
scm-purchase, ifiaccounting, empefficiency, iadmin, scm-asset, redis-dify, iehr, imessageflow, daq, mdm, scm-srm, scmwmssimulate, ipermission, ibizconfigcenter, ifichargecontrol, iworkflowmidlayer, ilkm, koala, iopenadmin, isales-member, iupush-related, etc.

### Empty (0 keys) — 14 clusters
apigateway, bigdata-dataplatform, devops, franchise, ifitax, igers, ilopamanager, iopenlinkeradmin, iopenservice, iunifiedreconcile, lkmap, open-unionauth, pub-dm, shopexpand

---

## 7. Next Steps

1. **Immediate (This Week):**
   - [ ] Sample key patterns on `luckyus-isales-market` using SCAN to categorize the 3.46M no-TTL keys
   - [ ] Review `luckyus-isales-session` session TTL policy with app team
   - [ ] Validate `luckyus-chronus` permanent keys are intentional

2. **Short-Term (2 Weeks):**
   - [ ] Implement TTL enforcement for isales-market (ref: existing runbook)
   - [ ] Set up Prometheus alerts for `redis_db_keys` growth on top-5 clusters
   - [ ] Evaluate decommissioning the 14 empty clusters

3. **Ongoing:**
   - [ ] Run this audit monthly to track key/TTL trends
   - [ ] Add `redis_db_keys{cluster="isales-market"}` to weekly DBA review dashboard
   - [ ] Standardize eviction policy to `volatile-lfu` across all clusters

---

*Report generated by Claude Code — Redis Key Pattern & TTL Audit Tool*
*Data collected: 2026-03-05 via mcp-db-gateway Redis INFO commands*
