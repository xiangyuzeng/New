# EC2 Claude Code Workstation Upgrade Cost Analysis

**Date:** 2026-03-20
**Author:** David Zeng (DBA/Infrastructure)
**Instance:** i-062d7f19b074225fa (10.238.3.43)

## Current Configuration

| Item | Spec | EDP Monthly Cost |
|------|------|-----------------|
| EC2 | c6i.xlarge (4 vCPU, 8 GiB) | $85.63 |
| EBS | 40 GB gp3 (3000 IOPS / 125 MB/s) | $3.20 |
| OS | Debian 12 (Docker container) | — |
| **Total** | | **$88.83/mo** |

- Disk usage: 33/40 GB (81%) — expansion needed
- Memory usage: 2.2/7.6 GB — adequate now but limited headroom for additional MCP servers
- Workload: Claude Code + 8 MCP stdio servers

## Upgrade Goal

Double memory (8 → 16 GiB) and double disk (40 → 80 GB).

## Option A: In-Place Upgrade (Recommended)

Upgrade instance type to **m6i.xlarge** (4 vCPU, 16 GiB) + expand EBS to 80 GB.

| Item | Spec | EDP Monthly Cost |
|------|------|-----------------|
| EC2 | m6i.xlarge (4 vCPU, 16 GiB) | $96.63 |
| EBS | 80 GB gp3 | $6.40 |
| **Total** | | **$103.03/mo** |
| **Delta** | | **+$14.20/mo (+$170/yr)** |

Steps:
1. Stop instance → change instance type to m6i.xlarge → start (~2-3 min downtime)
2. Modify EBS volume to 80 GB online (no downtime, then `growpart` + `resize2fs` inside OS)

## Option B: New Identical Instance

Keep current c6i.xlarge and add a second c6i.xlarge + 40 GB gp3.

| Item | Spec | EDP Monthly Cost |
|------|------|-----------------|
| New EC2 | c6i.xlarge (4 vCPU, 8 GiB) | $85.63 |
| New EBS | 40 GB gp3 | $3.20 |
| **Total additional** | | **$88.83/mo** |
| **Delta** | | **+$88.83/mo (+$1,066/yr)** |

## Comparison

| | Option A: Upgrade | Option B: New Instance |
|---|---|---|
| Monthly increase | **+$14.20** | +$88.83 |
| Annual increase | **+$170** | +$1,066 |
| Downtime | ~2-3 min (instance type change) | None |
| Total resources | 4 vCPU / 16 GB / 80 GB | 8 vCPU / 16 GB / 80 GB (split) |
| Management overhead | None | Additional instance to maintain |

## Recommendation

**Option A (in-place upgrade)** — 6x cheaper, same CPU, doubles both memory and disk with minimal downtime. Option B only justified if additional CPU cores or HA redundancy is required.

---

*Pricing: us-east-1 On-Demand × 730h × 0.69 (EDP 31% discount). EBS gp3 at $0.08/GB/mo.*
