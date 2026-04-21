---
Incident ID:          LCNA-INC-2026-025
Report Type:          Root Cause Analysis — Deployment Rollout CPU Spike
Subject:              iscmsims-pd Deployment-Wide CPU Spike — Rolling Update Cold-Start Pattern
EKS Cluster:          prod-worker01-eks-us
Namespace:            rd-supplychains
Deployment:           iscmsims-pd (Helm chart: infra_springboot-0.1.70, revision 62)
Affected Pods:        iscmsims-pdawsus-65c59c694f-brh5s (10.238.46.209)
                      iscmsims-pdawsus-65c59c694f-xtc9r (10.238.39.52)
Pod Resource Spec:    CPU request=1 core, limit=1 core; Memory request=4 GiB, limit=4 GiB (Guaranteed QoS)
HPA:                  min=2, max=10, current=2
Region:               us-east-1
AWS Account:          257394478466
Alert Window:         2026-04-21 13:38–13:50 UTC
Alert Rules:          【pod-cpu】P0 CPU使用率连续3分钟大于70% (strategy ID 71)
                      【pod-cpu-兜底】P0 CPU使用率连续3分钟大于85% (strategy ID 69)
Owner:                @方思扬
Severity:             L2 — self-resolving, no customer impact, no backend degradation
Investigator:         曾翔宇 David Zeng (Senior DBA)
Report Date:          2026-04-21
---

# LCNA-INC-2026-025 — iscmsims CPU Spike: Rolling Update Cold-Start

## 1. Executive Summary

**EN —** On 2026-04-21 at 13:38 UTC, deployment `iscmsims-pd` in `rd-supplychains` was updated (generation 67→68). The Kubernetes rolling update created pod brh5s at 13:38:11 and pod xtc9r at 13:42:30. Both pods immediately saturated their 1-core CPU limit during Spring Boot startup (class loading, JIT compilation, bean initialization), peaking at 99.97% and 99.87% respectively. Heavy CFS throttling (5–8 seconds/second, indicating the JVM wanted 6–9× its allocated CPU) extended startup to ~6 minutes per pod. Both pods self-recovered to 3–5% CPU in steady state by ~13:50 UTC. **No backend dependency was involved** — Redis `luckyus-scm-sims` was healthy (10 clients, 0 blocked), MySQL SCM databases were not contacted during the spike window, and node-level CPU impact was negligible (1.4% → 4.3%). This is the **2nd occurrence** — an identical pattern fired on 2026-03-26 with ReplicaSet `6456779b48`. The root cause is **insufficient CPU allocation for Spring Boot startup on a 1-core Guaranteed QoS pod**.

**中文 —** 2026-04-21 13:38 UTC，`rd-supplychains` 命名空间下的 `iscmsims-pd` 部署更新（generation 67→68）。K8s 滚动更新先后创建 brh5s（13:38:11）和 xtc9r（13:42:30）。两个 Pod 在 Spring Boot 启动阶段（类加载、JIT 编译、Bean 初始化）立即将 1 核 CPU 限制打满，峰值分别为 99.97% 和 99.87%。严重的 CFS 限流（每秒 5–8 秒，即 JVM 实际需要 6–9 倍所分配 CPU）使启动延长至约 6 分钟/Pod。至 ~13:50 UTC 两 Pod 均自行恢复至 3–5% 稳态。**无后端依赖受影响** — Redis 正常、MySQL 无关联、节点资源充裕。这是**第 2 次发生**（2026-03-26 完全相同模式）。根因为 **1 核 Guaranteed QoS Pod 的 CPU 分配不足以支撑 Spring Boot 冷启动**。

---

## 2. Timeline

| Time (UTC) | Event | Evidence Source |
|------------|-------|-----------------|
| ~13:38:00 | Deployment `iscmsims-pd` updated, generation 67→68 | `kube_deployment_metadata_generation` stepped from 67 to 68 at ts 1776778740 |
| 13:38:11 | Pod brh5s created on node `ip-10-238-13-156.ec2.internal` | `kube_pod_start_time` = 1776778691 |
| 13:39:00 | brh5s CPU hits 99.97% of 1-core limit | `container_cpu_usage_seconds_total` rate = 0.9997 |
| 13:39–13:43 | brh5s sustained at 99.5–99.97%, CFS throttled 4.6–7.9 sec/sec | `container_cpu_cfs_throttled_seconds_total` rate |
| **13:40:00** | **Alert fires: brh5s breaches 70% and 85% thresholds** | Per alert notification |
| 13:42:30 | Pod xtc9r created on node `ip-10-238-14-214.ec2.internal` (rolling update) | `kube_pod_start_time` = 1776778950 |
| 13:43–13:47 | xtc9r CPU at 92–99.87%, CFS throttled 2.8–6.0 sec/sec | Prometheus range query |
| 13:44:00 | brh5s CPU drops to 40% — recovery begins | rate = 0.4009 |
| **13:44:00** | **Alert fires: xtc9r breaches 70% and 85% thresholds** | Per alert notification |
| **13:45:30** | **brh5s RESOLVED** — CPU at 7.7% (duration ~5.5 min) | rate = 0.0770 |
| 13:47:31+ | xtc9r still at 96.2% (alert still firing) | rate = 0.9620 |
| 13:48:00 | xtc9r CPU drops to 52.5% — recovery begins | rate = 0.5254 |
| ~13:49:00 | xtc9r CPU at 8.3% — **RESOLVED** (duration ~6.5 min) | rate = 0.0835 |
| 13:50+ | Both pods at 3–5% steady-state CPU | Sustained < 0.05 cores |

**The "traveling" pattern is the rolling update sequence**: K8s creates pod A → A spikes during startup → once A passes readiness probe, K8s creates pod B → B spikes during startup → B recovers.

---

## 3. Root Cause Analysis

### Primary Root Cause: Spring Boot Cold-Start CPU Saturation on 1-Core Guaranteed QoS Pod

**Mechanism:**
1. Deployment updated (rev 62, generation 68) triggers rolling update (maxSurge/maxUnavailable defaults)
2. New pod starts Spring Boot JVM — class loading, annotation scanning, JIT compilation, bean initialization
3. JVM startup demands 6–9 CPU cores (measured via CFS throttled seconds: at 7.9 sec/sec throttled, the container wanted ~9 cores but was limited to 1)
4. Pod is Guaranteed QoS (requests=limits=1 core) — no CPU bursting allowed
5. Container pegs at 100% CPU utilization for ~6 minutes until startup completes
6. K8s rolling update starts second pod after first passes readiness probe → second pod follows identical pattern
7. Result: sequential ~6-minute spikes that look like a "traveling" dependency issue but are simply startup cost

### Why It Looks Like a Backend Problem (But Isn't)

| Misleading Signal | Actual Explanation |
|-------------------|-------------------|
| Sequential spikes across replicas | Rolling update creates pods sequentially |
| Same deployment hash `65c59c694f` | Both pods are from the same (new) ReplicaSet revision |
| 4-minute overlap | brh5s still recovering when xtc9r starts spiking |
| Near-100% CPU | Spring Boot JIT + class loading is CPU-bound, not I/O-bound |

### Contributing Factors
- **CPU limit = request = 1 core**: Guaranteed QoS prevents bursting; the JVM cannot use idle node CPU
- **No startup probe**: If using only readinessProbe with default settings, the pod may receive traffic while still JIT-compiling
- **Node CPU headroom wasted**: Both nodes were at 1.4–1.7% CPU before the spike — ample capacity existed but the cgroup prevented access

---

## 4. Backend Dependency Health — All Clear

| Backend | Status During Window | Evidence |
|---------|---------------------|----------|
| **Redis `luckyus-scm-sims`** | Healthy | 10 connected clients, 0 blocked clients, no anomaly |
| **MySQL SCM databases** | Not involved | No connections from pod IPs 10.238.46.209 / 10.238.39.52 during startup window (pods hadn't finished initializing) |
| **Kafka** | Not measurable | No `kafka_consumergroup_lag` metrics found for iscmsims consumer groups |
| **Node ip-10-238-13-156** | Normal | Peak 4.25% CPU (from 1.4% baseline) — negligible |
| **Node ip-10-238-14-214** | Normal | Peak 4.41% CPU (from 1.7% baseline) — negligible |

---

## 5. Historical Pattern — Recurring on Every Deployment

### 2026-03-26 (ReplicaSet `6456779b48`)

| Time (UTC) | Pod | Alert | Status |
|------------|-----|-------|--------|
| 07:28:47 | rm2b9 (10.238.45.21) | 兜底 85% | firing |
| 07:29:01 | rm2b9 | 70% | firing |
| 07:33:47 | 7ldh4 (10.238.47.35) | 兜底 85% | firing |
| 07:33:47 | rm2b9 | 兜底 85% | **resolved** (duration ~5 min) |
| 07:34:01 | 7ldh4 | 70% | firing |
| 07:34:01 | rm2b9 | 70% | **resolved** |
| 07:38:47 | 7ldh4 | 兜底 85% | **resolved** (duration ~5 min) |
| 07:39:01 | 7ldh4 | 70% | **resolved** |

**Identical pattern**: ~5 min gap between pods, ~5 min spike duration each, both alert rules fire and resolve in lock-step. Different ReplicaSet hash confirms this is deployment-correlated, not workload-correlated.

### Pattern Summary

| Date | ReplicaSet | Pod 1 Start → Resolve | Pod 2 Start → Resolve | Total Alert Count |
|------|-----------|----------------------|----------------------|-------------------|
| 2026-03-26 | `6456779b48` | 07:28 → 07:33 (~5 min) | 07:33 → 07:38 (~5 min) | 8 (4 firing + 4 resolved) |
| **2026-04-21** | **`65c59c694f`** | **13:40 → 13:45 (~5.5 min)** | **13:44 → 13:49 (~5 min)** | **8 (expected)** |

**Conclusion:** Every deployment of `iscmsims-pd` generates exactly 8 alert events (2 rules × 2 pods × firing+resolved). The 26-day gap between incidents corresponds to the deployment frequency.

---

## 6. Alert Policy Assessment — Deduplication Recommended

### Current State

| Strategy ID | Alert Name | Threshold | Duration | Status |
|-------------|-----------|-----------|----------|--------|
| 69 | 【pod-cpu-兜底】P0 CPU使用率连续3分钟大于85% | 85% | 3 min | ENABLED |
| 71 | 【pod-cpu】P0 CPU使用率连续3分钟大于70% | 70% | 3 min | ENABLED |
| 70 | 【pod-cpu】P0 CPU使用率连续10分钟大于50% | 50% | 10 min | ENABLED |
| 68 | 【pod-cpu】P0 CPU周期受限比例大于40% | 40% throttle | — | DISABLED |

### Problem

During cold start, CPU goes from 0% to 99% in < 60 seconds. Both the 70% and 85% rules fire within the **same evaluation cycle** (14-second gap on March 26: 07:28:47 vs 07:29:01). The 兜底 (fallback) rule adds zero incremental signal — when the 70% fires, the 85% always fires simultaneously because the spike overshoots both thresholds instantly.

### Recommendation

**Option A (Preferred) — Merge into tiered alert:**
Replace IDs 69 + 71 with a single strategy using two notification tiers:
- WARN at 70% for 3 min → WeCom only
- CRITICAL at 85% for 3 min → WeCom + Twilio
This halves alert volume without losing coverage.

**Option B — Startup exclusion filter:**
Add condition: `AND (time() - kube_pod_start_time{pod=~"$pod"}) > 600`
This suppresses alerts for pods younger than 10 minutes, eliminating all deployment-triggered noise.

**Option C — Inhibition rule:**
Configure 兜底 (ID 69) to suppress when 70% (ID 71) is already firing for the same `pod` label. This preserves both rules but prevents duplicate notifications.

**Strongest recommendation: Option B** — the cold-start spike is expected, self-resolving, and has no customer impact. Alerting on it wastes on-call attention. Combine with Option A for long-term alert hygiene.

---

## 7. Recommended Mitigations

### Immediate — Alert Noise Reduction (Owner: DBA/Platform team)

| Action | Impact | Effort |
|--------|--------|--------|
| Add startup exclusion filter (Option B above) to strategies 69 + 71 | Eliminates all deployment-triggered false positives | Low — PromQL change |
| Merge 70%/85% into tiered alert (Option A) | Halves alert volume for real incidents too | Medium — strategy restructure |

### Short-Term — Reduce Startup CPU Demand (Owner: @方思扬 / SCM dev team)

| Action | Impact | Effort |
|--------|--------|--------|
| Change CPU resources to `request: 1, limit: 2` (Burstable QoS) | Allows JVM to burst to 2 cores during startup; cuts startup time ~50% | Low — Helm values change |
| Add JVM flags: `-XX:+TieredCompilation -XX:TieredStopAtLevel=1` for startup, then remove | Reduces JIT compilation CPU by skipping C2 compiler during startup | Low — env var change |
| Add `startupProbe` with `failureThreshold: 30, periodSeconds: 10` (5 min budget) | Prevents premature traffic routing and health check failures during startup | Low — Helm values change |

### Long-Term — Architecture (Owner: Platform team)

| Action | Impact | Effort |
|--------|--------|--------|
| Enable Spring AOT / CDS (Class Data Sharing) for `infra_springboot` chart | Reduces class loading CPU by 40–60% on subsequent starts | Medium |
| Implement graceful shutdown + preStop hook + PodDisruptionBudget | Ensures at least 1 warm pod serves traffic during any rollout | Medium |
| Evaluate moving SCM services to `request: 0.5, limit: 2` with HPA CPU target 60% | Better burst/steady-state ratio; HPA scales for sustained load | Medium — requires load testing |

---

## 8. Impact Assessment

| Dimension | Assessment |
|-----------|------------|
| **Customer-facing impact** | None — both pods were in startup phase, not yet serving production traffic |
| **Data integrity** | No risk — no database operations during spike |
| **Service availability** | If this is a 2-replica deployment with no PDB: **potential full outage during rolling update** if both pods are simultaneously starting or unready. Needs verification of `maxUnavailable` setting |
| **Alert fatigue** | **Moderate** — 8 alert events per deployment × unknown deployment frequency = predictable noise. On-call already experienced this on 2026-03-26 |
| **Backend dependency load** | None — Redis, MySQL, Kafka all uninvolved |

---

## 9. Evidence Appendix

### A. CPU Usage Time Series (cores, 1-core limit)

```
Time(UTC)   brh5s       xtc9r
13:39       0.9997      —
13:40       0.9967      —
13:41       0.9958      —
13:42       0.9972      —
13:43       0.9277      0.9259
13:44       0.4009      0.9788
13:45       0.0770      0.9961
13:46       0.1068      0.9987  ← xtc9r peak
13:47       0.0973      0.9620
13:48       0.0737      0.5254
13:49       0.0722      0.0835
13:50       0.0548      0.0894
```

### B. CFS Throttled Seconds (sec/sec — how many seconds per second the container was blocked by cgroup CPU limit)

```
Time(UTC)   brh5s       xtc9r
13:39       7.854       —
13:40       5.976       —
13:41       5.178       —
13:42       4.590       —
13:43       6.937       2.777
13:44       4.803       4.606
13:45       0.087       5.492
13:46       0.173       4.241
13:47       0.172       5.967  ← xtc9r peak throttle
13:48       0.087       4.966
13:49       0.150       0.083
```

**Interpretation:** At 7.854 sec/sec throttled, the JVM was attempting to use ~8.85 CPU cores but was capped at 1. This is the signature of JVM class loading + JIT compilation during Spring Boot startup.

### C. Memory Working Set (bytes → GiB)

```
Time(UTC)   brh5s(GiB)  xtc9r(GiB)
13:39       1.01        —
13:40       1.64        —
13:41       1.78        —
13:42       2.05        —
13:43       2.36        0.88
13:44       2.37        1.60
13:45       2.40        1.71
13:46       2.42        1.93
13:47       2.42        2.37
13:48       2.43        2.40
...         ~2.45       ~2.45    (steady state = 57% of 4 GiB limit)
```

### D. Node CPU (% utilization)

```
Time(UTC)   node-156(brh5s)   node-214(xtc9r)
13:38       1.42%             1.70%
13:40       2.53%             1.68%
13:42       3.83%             1.63%
13:43       4.25%             1.82%   ← brh5s peak; xtc9r just starting
13:45       3.26%             3.13%
13:47       2.11%             4.41%   ← xtc9r peak
13:49       1.75%             1.91%   ← both recovered
```

**Conclusion:** Nodes had ample CPU headroom. The pod-level spike was purely cgroup-confined.

### E. Deployment Generation History

```
12:00–13:37 UTC: generation = 67 (stable)
13:38–13:39 UTC: generation → 68 (deployment updated)
13:39–14:30 UTC: generation = 68 (stable)
```

Single step change at exactly the time pods were created. No subsequent updates.

### F. HPA Configuration

```
iscmsims-pd: min=2, max=10, current=2, desired=2
```

HPA was not involved — the deployment was at its minimum replica count.

---

## 10. Disposition

| Item | Status |
|------|--------|
| Root cause identified | ✅ Deployment rollout cold-start CPU saturation |
| Customer impact | ✅ None |
| Recurring risk | ⚠️ Will recur on every deployment until mitigated |
| Immediate action required | Add startup exclusion to alert strategies 69/71 |
| Owner notification | @方思扬 — recommend CPU limit increase to 2 cores |
| Follow-up incident | Not required — self-resolving, no data integrity risk |
