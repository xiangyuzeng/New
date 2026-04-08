# Dify Platform Decommission — Execution Runbook

| Field | Value |
|-------|-------|
| **Date** | 2026-04-08 |
| **Author** | David Zeng (DBA/Infrastructure) |
| **Status** | READY FOR EXECUTION (pending permission grant) |
| **AWS Account** | 257394478466 (us-east-1) |
| **IAM User** | databasecheck |
| **EKS Cluster** | prod-worker01-eks-us |
| **Namespace** | baseservices-cloud-dify |
| **Estimated Savings** | ~$2,190/mo (~$12,000 over 6-month pause) |
| **Previous Reports** | v1 Plan (2026-03-24), v2 Technical (2026-03-25), v3 Update (2026-04-07) |

---

## 一、Permission Audit Results

### 1.1 Complete Permission Matrix

Tested 2026-04-08 against IAM user `arn:aws:iam::257394478466:user/databasecheck`.

#### GRANTED Permissions (can proceed)

| # | Resource | Operation | IAM Action | Notes |
|---|----------|-----------|------------|-------|
| G1 | RDS (all) | Describe instances | rds:DescribeDBInstances | Full metadata access |
| G2 | RDS (all) | Describe snapshots | rds:DescribeDBSnapshots | Can verify snapshot status |
| G3 | ElastiCache (all) | Describe replication groups | elasticache:DescribeReplicationGroups | Full config access |
| G4 | ElastiCache (all) | Describe snapshots | elasticache:DescribeSnapshots | Can verify snapshot status |
| G5 | ElastiCache (all) | Describe cache clusters | elasticache:DescribeCacheClusters | Subnet/SG details |
| G6 | OpenSearch | Describe domain | es:DescribeDomain | Full domain status |
| G7 | OpenSearch | Describe domain config | es:DescribeDomainConfig | Security/encryption config |
| G8 | EC2 | Describe instances | ec2:DescribeInstances | Instance metadata |
| G9 | EC2 | Describe volumes | ec2:DescribeVolumes | EBS volume inventory |
| G10 | EC2 | Describe network interfaces | ec2:DescribeNetworkInterfaces | ENI status check |
| G11 | ELBv2 | Describe load balancers | elasticloadbalancing:DescribeLoadBalancers | NLB metadata |
| G12 | ELBv2 | Describe LB attributes | elasticloadbalancing:DescribeLoadBalancerAttributes | Deletion protection check |
| G13 | ELBv2 | Describe target groups | elasticloadbalancing:DescribeTargetGroups | Target group details |
| G14 | EKS | Describe nodegroup | eks:DescribeNodegroup | Scaling config |
| G15 | CloudWatch | Describe alarms | cloudwatch:DescribeAlarms | No Dify alarms found |
| G16 | S3 | Get bucket versioning | s3:GetBucketVersioning | All 3 buckets: versioning OFF |
| G17 | EKS (via MCP) | Read K8s resources | eks:DescribeCluster + RBAC | Namespace, Deployments, Services, ConfigMaps, PVCs, Ingresses |

#### DENIED Permissions (must request before execution)

| # | Resource | Operation | IAM Action Needed | Exact Error | Request From |
|---|----------|-----------|-------------------|-------------|--------------|
| D1 | RDS | Create snapshot | `rds:CreateDBSnapshot` | "no identity-based policy allows rds:CreateDBSnapshot" | AWS Admin (Michael/CTO) |
| D2 | RDS | Modify instance | `rds:ModifyDBInstance` | "no identity-based policy allows rds:ModifyDBInstance" | AWS Admin |
| D3 | RDS | Delete instance | `rds:DeleteDBInstance` | Not tested (likely denied) | AWS Admin |
| D4 | ElastiCache | Create snapshot | `elasticache:CreateSnapshot` | "no identity-based policy allows elasticache:CreateSnapshot" | AWS Admin |
| D5 | ElastiCache | Delete replication group | `elasticache:DeleteReplicationGroup` | Not tested (likely denied) | AWS Admin |
| D6 | EC2 | Stop instances | `ec2:StopInstances` | "not authorized to perform ec2:StopInstances" | AWS Admin |
| D7 | EC2 | Terminate instances | `ec2:TerminateInstances` | "not authorized to perform ec2:TerminateInstances" | AWS Admin |
| D8 | EC2 | Delete ENI | `ec2:DeleteNetworkInterface` | "not authorized to perform ec2:DeleteNetworkInterface" | AWS Admin |
| D9 | S3 | List/Delete objects | `s3:ListBucket`, `s3:DeleteObject`, `s3:DeleteBucket` | "AccessDenied on ListObjectsV2" | AWS Admin |
| D10 | Route53 | Manage DNS | `route53:ListHostedZones`, `route53:ChangeResourceRecordSets` | "AccessDenied" | AWS Admin |
| D11 | KMS | Describe key | `kms:DescribeKey`, `kms:ListAliases`, `kms:ListGrants` | "AccessDeniedException" | AWS Admin |
| D12 | EFS | Describe file systems | `elasticfilesystem:DescribeFileSystems` | "AccessDeniedException" | AWS Admin |
| D13 | SES | List identities | `ses:ListIdentities` | "AccessDenied" | AWS Admin |
| D14 | EKS | Update nodegroup | `eks:UpdateNodegroupConfig` | "not authorized to perform eks:UpdateNodegroupConfig" | AWS Admin |
| D15 | OpenSearch | Delete domain | `es:DeleteDomain` | Not tested (likely denied) | AWS Admin |

#### UNTESTED Permissions (need day-of verification)

| # | Resource | Operation | IAM Action | Test Command |
|---|----------|-----------|------------|--------------|
| U1 | EKS (MCP) | Write K8s resources | RBAC write | `manage_k8s_resource(operation='delete', ...)` — MCP server currently read-only, needs `--allow-write` flag |
| U2 | ELBv2 | Delete load balancer | `elasticloadbalancing:DeleteLoadBalancer` | Not critical — NLB auto-deletes when K8s Service is removed |

### 1.2 Permission Summary

**Current state**: databasecheck has **read-only access** across all services. Cannot create snapshots, modify, or delete ANY resource.

**Required for execution**: 15 additional IAM actions (see Section 八 for the complete permission request template).

**Workaround for K8s**: MCP eks-server needs `--allow-write` flag enabled. Alternatively, use `kubectl` directly if RBAC permits.

---

## 二、K8s Namespace Deletion Runbook

### 2.1 Pre-Deletion Checklist

| # | Check | Status | Details |
|---|-------|--------|---------|
| 1 | Helm releases identified | Done | 2 releases: `dify` (chart dify-0.0.1), `milvus` (chart milvus-4.0.31) |
| 2 | kubectl-applied resources identified | Done | new-dify-api, new-dify-web, new-dify-sandbox, new-dify-plugin-daemon, new-dify-ingress, data-dify-39mdc PVC, hello-world |
| 3 | Namespace finalizers | Done | Standard `kubernetes` finalizer only — clean deletion possible |
| 4 | NetworkPolicies | Done | None |
| 5 | ResourceQuotas | Done | None |
| 6 | LimitRanges | Done | None |
| 7 | PodDisruptionBudgets | Done | None in Dify namespace |
| 8 | ServiceAccounts | Done | 3: default, milvus-pulsar-broker-acct, milvus-s3-access-sa |
| 9 | ClusterRoleBindings | TODO | Check day-of for bindings referencing Dify SAs |
| 10 | Secrets (Helm releases) | Blocked | RBAC 403 on Secret list — coordinate with EKS admin |
| 11 | PVC reclaim policies | Partial | EBS PVCs via ebs.csi.aws.com (default Delete reclaimPolicy). EFS PVC (efs-sc) needs verification. |
| 12 | LoadBalancer Services | Done | 1 service: `milvus` (type LoadBalancer) → creates NLB `inf-milvus-service` |
| 13 | Ingresses | Done | 2: `new-dify-ingress` (dify-console.luckincoffee.us), `milvus-attu` (milvus-attu.luckincoffee.us). Both use shared ingress-nginx-controller. |
| 14 | No external-dns | Done | No external-dns deployment in kube-system → DNS will NOT auto-cleanup |

### 2.2 Deletion Strategy Analysis

#### Option A: Helm Uninstall + kubectl Delete + Namespace Delete (RECOMMENDED)

```
Phase 1: helm uninstall dify -n baseservices-cloud-dify
Phase 2: helm uninstall milvus -n baseservices-cloud-dify
Phase 3: kubectl delete remaining resources + PVCs
Phase 4: kubectl delete namespace baseservices-cloud-dify
```

**Pros**: Cleanest — Helm tracks its own resources and deletes them properly. StatefulSet PVCs from Helm releases get proper cleanup. LoadBalancer Service deletion triggers NLB auto-cleanup via aws-load-balancer-controller.

**Cons**: Requires Helm CLI access. If Helm release metadata (Secrets) is corrupted, uninstall may fail.

**Auto-cleanup**: Helm-managed Deployments, Services, ConfigMaps, StatefulSets. NLB + 2 target groups (via aws-load-balancer-controller). EBS volumes (if StorageClass reclaimPolicy=Delete).

**Manual cleanup**: kubectl-applied new-dify-* resources, EFS PVC, DNS records, ClusterRoleBindings referencing Dify SAs.

#### Option B: Delete All Resources + Namespace

```
kubectl delete all --all -n baseservices-cloud-dify
kubectl delete pvc,configmap,ingress --all -n baseservices-cloud-dify
kubectl delete namespace baseservices-cloud-dify
```

**Pros**: No Helm CLI needed. Works even if Helm release metadata is damaged.

**Cons**: Orphans Helm release Secrets (they persist as `sh.helm.release.v1.*`). Less controlled — all resources deleted simultaneously may cause race conditions (e.g., NLB cleanup timing).

#### Option C: Namespace Delete Only (cascading)

```
kubectl delete namespace baseservices-cloud-dify
```

**Pros**: Simplest single command.

**Cons**: Riskiest. If any resource has a broken finalizer, namespace hangs in Terminating state indefinitely. StatefulSet PVCs may not be cleaned up properly. NLB cleanup timing unpredictable.

**NOT RECOMMENDED** for this namespace due to 6 StatefulSets with PVCs and a LoadBalancer Service.

### 2.3 Recommended Step-by-Step Commands (Option A)

**Prerequisites**: Helm CLI access, kubectl access, MCP eks-server with `--allow-write`

```bash
# === PHASE K1: BACKUP (before any deletion) ===

# K1.1 Backup Ingress YAML
kubectl get ingress new-dify-ingress -n baseservices-cloud-dify -o yaml > ~/backup-new-dify-ingress.yaml
kubectl get ingress milvus-attu -n baseservices-cloud-dify -o yaml > ~/backup-milvus-attu-ingress.yaml

# K1.2 Backup all resource definitions
kubectl get all,pvc,configmap,ingress,sa -n baseservices-cloud-dify -o yaml > ~/backup-dify-namespace-full.yaml

# K1.3 List current state for verification
kubectl get all -n baseservices-cloud-dify
kubectl get pvc -n baseservices-cloud-dify
kubectl get ingress -n baseservices-cloud-dify

# === PHASE K2: SCALE DOWN STATEFULSETS (unmount volumes) ===

# K2.1 Scale down Milvus StatefulSets to 0
kubectl scale statefulset milvus-etcd --replicas=0 -n baseservices-cloud-dify
kubectl scale statefulset milvus-pulsar-bookie --replicas=0 -n baseservices-cloud-dify
kubectl scale statefulset milvus-pulsar-broker --replicas=0 -n baseservices-cloud-dify
kubectl scale statefulset milvus-pulsar-proxy --replicas=0 -n baseservices-cloud-dify
kubectl scale statefulset milvus-pulsar-zookeeper --replicas=0 -n baseservices-cloud-dify

# K2.2 Wait for pods to terminate
kubectl wait --for=delete pod -l app.kubernetes.io/instance=milvus \
  -n baseservices-cloud-dify --timeout=120s

# === PHASE K3: DELETE INGRESSES FIRST (remove routes before backends) ===

kubectl delete ingress new-dify-ingress -n baseservices-cloud-dify
kubectl delete ingress milvus-attu -n baseservices-cloud-dify

# === PHASE K4: HELM UNINSTALL ===

# K4.1 Uninstall Dify Helm release (removes old dify-api, dify-web, etc.)
helm uninstall dify -n baseservices-cloud-dify

# K4.2 Uninstall Milvus Helm release (removes all milvus-*, NLB auto-deletes)
helm uninstall milvus -n baseservices-cloud-dify

# K4.3 Verify NLB deletion started
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[?LoadBalancerName==`inf-milvus-service`].State' \
  --region us-east-1
# Expected: either empty (deleted) or State=active_impaired (deleting)

# === PHASE K5: DELETE KUBECTL-APPLIED RESOURCES ===

kubectl delete deployment new-dify-api new-dify-web new-dify-worker \
  new-dify-sandbox new-dify-plugin-daemon -n baseservices-cloud-dify
kubectl delete service new-dify-api new-dify-web new-dify-sandbox \
  new-dify-plugin-daemon hello-world -n baseservices-cloud-dify
kubectl delete pvc data-dify-39mdc -n baseservices-cloud-dify

# === PHASE K6: DELETE REMAINING PVCs ===

# Delete StatefulSet PVCs (NOT auto-deleted by Helm uninstall for StatefulSets)
kubectl delete pvc --all -n baseservices-cloud-dify

# === PHASE K7: DELETE NAMESPACE ===

kubectl delete namespace baseservices-cloud-dify

# K7.1 Verify namespace is gone
kubectl get namespace baseservices-cloud-dify
# Expected: Error from server (NotFound)

# K7.2 If namespace stuck in Terminating (>5 min), force-remove finalizer:
# kubectl get namespace baseservices-cloud-dify -o json | \
#   jq '.spec.finalizers = []' | \
#   kubectl replace --raw "/api/v1/namespaces/baseservices-cloud-dify/finalize" -f -
```

### 2.4 Expected Automatic Cleanup

| Resource | Auto-cleaned by | Timing |
|----------|----------------|--------|
| NLB `inf-milvus-service` | aws-load-balancer-controller (on Service deletion) | 1-5 min |
| 2 Target Groups (k8s-baseserv-milvus-*) | aws-load-balancer-controller | 1-5 min |
| 12 EBS volumes (etcd, pulsar) | ebs-csi-driver (on PVC deletion, if reclaimPolicy=Delete) | 1-5 min |
| PersistentVolumes | K8s garbage collection | Immediate after PVC delete |
| Pods, ReplicaSets | K8s garbage collection (owner references) | Immediate |
| ConfigMaps (Helm-managed) | Helm uninstall | Immediate |

### 2.5 Manual Cleanup After Namespace Deletion

| # | Resource | Action | Command |
|---|----------|--------|---------|
| 1 | EFS access point / mount targets | Verify EFS cleanup after PVC deletion | `aws efs describe-mount-targets --file-system-id <fs-id>` (need efs:Describe permission) |
| 2 | DNS records | Manual deletion in Route53 | See Section 六 |
| 3 | ClusterRoleBindings | Check and delete any referencing Dify SAs | `kubectl get clusterrolebinding -o json \| jq '.items[] \| select(.subjects[]?.namespace=="baseservices-cloud-dify")'` |
| 4 | EBS volumes | Verify all 12 volumes deleted | `aws ec2 describe-volumes --filters 'Name=tag:kubernetes.io/created-for/pvc/namespace,Values=baseservices-cloud-dify' --region us-east-1` |
| 5 | NLB | Verify deletion completed | `aws elbv2 describe-load-balancers --query 'LoadBalancers[?LoadBalancerName==\`inf-milvus-service\`]' --region us-east-1` |

---

## 三、Milvus + Vector DB Teardown

### 3.1 Milvus Architecture Map

```
                    ┌─────────────────────────────────────────┐
                    │         Milvus v2.2.13 Cluster          │
                    │         (Helm: milvus-4.0.31)           │
                    │                                         │
  NLB               │  ┌──────────┐     ┌──────────────┐     │
  inf-milvus-service│  │ Proxy(2) │────>│ RootCoord(2) │     │
  :19530/:9091  ───>│  └──────────┘     └──────────────┘     │
                    │        │                                 │
                    │  ┌─────┴──────────────────────────┐     │
                    │  │     Query Path                  │     │
                    │  │ QueryCoord(2) → QueryNode(2)   │     │
                    │  └─────────────────────────────────┘     │
                    │  ┌─────────────────────────────────┐     │
                    │  │     Index Path                  │     │
                    │  │ IndexCoord(2) → IndexNode(2)   │     │
                    │  └─────────────────────────────────┘     │
                    │  ┌─────────────────────────────────┐     │
                    │  │     Data Path                   │     │
                    │  │ DataCoord(2) → DataNode(2)     │     │
                    │  └─────────────────────────────────┘     │
                    └───────────┬───────────┬─────────────────┘
                                │           │
                    ┌───────────┘           └──────────┐
                    ▼                                   ▼
         ┌────────────────┐                 ┌─────────────────┐
         │   etcd (3)     │                 │  Pulsar          │
         │  3x10GB EBS    │                 │  Broker(1)       │
         │  Metadata      │                 │  Proxy(1)        │
         └────────────────┘                 │  Bookie(3)       │
                                            │  ZK(3)           │
                                            │  3x100GB journal │
                                            │  3x200GB ledgers │
                                            │  3x20GB ZK data  │
                                            └─────────────────┘
                                                     │
                                            ┌────────┘
                                            ▼
                                 ┌─────────────────────┐
                                 │  S3: lk-infra-dify  │
                                 │  Object Storage     │
                                 │  73MB / 663 objects  │
                                 │  AWS creds embedded  │
                                 └─────────────────────┘
         ServiceAccount: milvus-s3-access-sa
         Attu Web UI: milvus-attu (port 3000)
```

### 3.2 Data Persistence Analysis

| Storage Layer | Location | Size | Auto-cleans with K8s? | Backup needed? |
|--------------|----------|------|-----------------------|----------------|
| etcd (metadata) | 3 EBS volumes (10GB each) | 30GB | YES (PVC delete → EBS delete) | No — metadata only |
| Pulsar journals | 3 EBS volumes (100GB each) | 300GB | YES | No — WAL logs |
| Pulsar ledgers | 3 EBS volumes (200GB each) | 600GB | YES | No — WAL logs |
| Pulsar ZK data | 3 EBS volumes (20GB each) | 60GB | YES | No — cluster state |
| S3 object store | s3://lk-infra-dify | 73MB | NO — requires S3 cleanup | Optional (vector embeddings) |

**Total EBS**: 990GB across 12 volumes. All auto-clean when PVCs are deleted (assuming reclaimPolicy=Delete).

### 3.3 Teardown Strategy

Since Milvus is fully Helm-managed (`helm.sh/release-name: milvus`), `helm uninstall` is the cleanest path.

**What `helm uninstall milvus` removes:**
- All 9 Deployments (proxy, rootcoord, querycoord, querynode, indexcoord, indexnode, datacoord, datanode, attu)
- All 6 StatefulSets (etcd, pulsar-bookie, pulsar-broker, pulsar-proxy, pulsar-recovery, pulsar-zookeeper)
- All 16 Milvus Services (including `milvus` LoadBalancer → triggers NLB deletion)
- All 6 Milvus ConfigMaps
- milvus-attu Ingress
- ServiceAccounts (milvus-pulsar-broker-acct, milvus-s3-access-sa)

**What `helm uninstall milvus` does NOT remove:**
- PVCs from StatefulSets (Helm convention: StatefulSet PVCs persist after uninstall)
- S3 bucket contents
- NLB (deleted by aws-load-balancer-controller, not Helm directly)

### 3.4 PVC/EBS/EFS Cleanup Commands

```bash
# After helm uninstall milvus, delete orphaned StatefulSet PVCs:
kubectl delete pvc data-milvus-etcd-0 data-milvus-etcd-1 data-milvus-etcd-2 \
  -n baseservices-cloud-dify
kubectl delete pvc \
  milvus-pulsar-bookie-journal-milvus-pulsar-bookie-0 \
  milvus-pulsar-bookie-journal-milvus-pulsar-bookie-1 \
  milvus-pulsar-bookie-journal-milvus-pulsar-bookie-2 \
  -n baseservices-cloud-dify
kubectl delete pvc \
  milvus-pulsar-bookie-ledgers-milvus-pulsar-bookie-0 \
  milvus-pulsar-bookie-ledgers-milvus-pulsar-bookie-1 \
  milvus-pulsar-bookie-ledgers-milvus-pulsar-bookie-2 \
  -n baseservices-cloud-dify
kubectl delete pvc \
  milvus-pulsar-zookeeper-data-milvus-pulsar-zookeeper-0 \
  milvus-pulsar-zookeeper-data-milvus-pulsar-zookeeper-1 \
  milvus-pulsar-zookeeper-data-milvus-pulsar-zookeeper-2 \
  -n baseservices-cloud-dify

# Delete EFS PVC (new-dify-api storage):
kubectl delete pvc data-dify-39mdc -n baseservices-cloud-dify

# Verify all EBS volumes are deleted:
aws ec2 describe-volumes \
  --filters 'Name=tag:kubernetes.io/created-for/pvc/namespace,Values=baseservices-cloud-dify' \
  --query 'Volumes[].{ID:VolumeId,State:State,PVC:Tags[?Key==`kubernetes.io/created-for/pvc/name`].Value|[0]}' \
  --region us-east-1
# Expected: empty result
```

### 3.5 NLB Auto-Deletion Verification

The NLB `inf-milvus-service` is managed by the `milvus` K8s Service (type LoadBalancer) with annotation `service.beta.kubernetes.io/aws-load-balancer-type: external`. The aws-load-balancer-controller in kube-system watches for Service deletions and removes the corresponding NLB.

```bash
# NLB details for reference:
# ARN: arn:aws:elasticloadbalancing:us-east-1:257394478466:loadbalancer/net/inf-milvus-service/83c26a421d630082
# Target Groups: k8s-baseserv-milvus-8fb2563e78, k8s-baseserv-milvus-dc861b4290
# Deletion Protection: DISABLED (confirmed)
# Security Groups: sg-0eeb5a6d5c495e30e, sg-0550dcb1098214e38 (NOT the shared SG)

# Verification after Service deletion:
aws elbv2 describe-load-balancers --names inf-milvus-service --region us-east-1 2>&1
# Expected: LoadBalancerNotFound error

aws elbv2 describe-target-groups --names k8s-baseserv-milvus-8fb2563e78 --region us-east-1 2>&1
# Expected: TargetGroupNotFound error
```

---

## 四、AWS Managed Service Deletion Runbook

### 4.1 RDS PostgreSQL Deletion

**Instances**: `aws-luckyus-dify-rw` (old, v16.8), `aws-luckyus-difynew-rw` (new, v16.10)

**Shared resources — DO NOT DELETE**:
- Subnet group: `rds-group` (used by 64 RDS instances)
- Security group: `sg-0deaa7cf7437e39c7` (used by 623 ENIs)
- Parameter group: `default.postgres16` (AWS default, cannot delete)

**Current automated snapshots** (daily, 7-day retention):
- dify-rw: 8 snapshots (latest: 2026-04-08T05:18:46)
- difynew-rw: 9 snapshots (latest: 2026-04-08T06:35:39)

**Execution order** (repeat for each instance):

```bash
# === RDS Step 1: Create final manual snapshot (REQUIRES: rds:CreateDBSnapshot) ===
aws rds create-db-snapshot \
  --db-instance-identifier aws-luckyus-dify-rw \
  --db-snapshot-identifier decom-final-dify-rw-20260408 \
  --region us-east-1

aws rds create-db-snapshot \
  --db-instance-identifier aws-luckyus-difynew-rw \
  --db-snapshot-identifier decom-final-difynew-rw-20260408 \
  --region us-east-1

# === RDS Step 2: Wait for snapshots to complete ===
aws rds wait db-snapshot-available \
  --db-snapshot-identifier decom-final-dify-rw-20260408 \
  --region us-east-1

aws rds wait db-snapshot-available \
  --db-snapshot-identifier decom-final-difynew-rw-20260408 \
  --region us-east-1

# === RDS Step 3: Verify snapshots ===
aws rds describe-db-snapshots \
  --db-snapshot-identifier decom-final-dify-rw-20260408 \
  --query 'DBSnapshots[0].{ID:DBSnapshotIdentifier,Status:Status,Size:AllocatedStorage}' \
  --region us-east-1

aws rds describe-db-snapshots \
  --db-snapshot-identifier decom-final-difynew-rw-20260408 \
  --query 'DBSnapshots[0].{ID:DBSnapshotIdentifier,Status:Status,Size:AllocatedStorage}' \
  --region us-east-1

# === RDS Step 4: Disable deletion protection (REQUIRES: rds:ModifyDBInstance) ===
aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-dify-rw \
  --no-deletion-protection \
  --apply-immediately \
  --region us-east-1

aws rds modify-db-instance \
  --db-instance-identifier aws-luckyus-difynew-rw \
  --no-deletion-protection \
  --apply-immediately \
  --region us-east-1

# Wait for modification to apply (~1-2 min):
aws rds wait db-instance-available \
  --db-instance-identifier aws-luckyus-dify-rw \
  --region us-east-1

aws rds wait db-instance-available \
  --db-instance-identifier aws-luckyus-difynew-rw \
  --region us-east-1

# === RDS Step 5: Delete instances (REQUIRES: rds:DeleteDBInstance) ===
# --skip-final-snapshot because we already created manual snapshots above
# --delete-automated-backups to clean up automated snapshots
aws rds delete-db-instance \
  --db-instance-identifier aws-luckyus-dify-rw \
  --skip-final-snapshot \
  --delete-automated-backups \
  --region us-east-1

aws rds delete-db-instance \
  --db-instance-identifier aws-luckyus-difynew-rw \
  --skip-final-snapshot \
  --delete-automated-backups \
  --region us-east-1

# === RDS Step 6: Verify deletion (takes 5-10 min) ===
aws rds describe-db-instances \
  --db-instance-identifier aws-luckyus-dify-rw \
  --region us-east-1 2>&1
# Expected: DBInstanceNotFoundFault

aws rds describe-db-instances \
  --db-instance-identifier aws-luckyus-difynew-rw \
  --region us-east-1 2>&1
# Expected: DBInstanceNotFoundFault

# === RDS Snapshot retention note ===
# Manual snapshots persist until explicitly deleted. Cost: ~$0.10/GB/mo
# 20GB each = $2/mo for both = $24 for 12-month retention
# Keep until project restarts or 12 months, whichever comes first.
```

### 4.2 ElastiCache Redis Deletion

**Replication groups**: `luckyus-redis-dify` (old, cache.m6g.large x2, Redis 7.0), `luckyus-difynew` (new, cache.t4g.micro x2, Redis 6.0)

**Shared resources — DO NOT DELETE**:
- Subnet group: `redis-group` (used by 76 replication groups)
- Security group: `sg-0deaa7cf7437e39c7` (shared)
- Parameter group `default.redis7` (AWS default, cannot delete)

**Custom parameter group to evaluate**:
- `luckyus-ha-6` (used by luckyus-difynew) — check if other clusters use it before deleting

```bash
# === Redis Step 1: Create manual snapshots (REQUIRES: elasticache:CreateSnapshot) ===
aws elasticache create-snapshot \
  --replication-group-id luckyus-redis-dify \
  --snapshot-name decom-final-redis-dify-20260408 \
  --region us-east-1

aws elasticache create-snapshot \
  --replication-group-id luckyus-difynew \
  --snapshot-name decom-final-redis-difynew-20260408 \
  --region us-east-1

# === Redis Step 2: Wait for snapshots ===
# ElastiCache has no 'wait' command; poll:
aws elasticache describe-snapshots \
  --snapshot-name decom-final-redis-dify-20260408 \
  --query 'Snapshots[0].SnapshotStatus' \
  --region us-east-1
# Repeat until Status = "available" (~2-5 min)

aws elasticache describe-snapshots \
  --snapshot-name decom-final-redis-difynew-20260408 \
  --query 'Snapshots[0].SnapshotStatus' \
  --region us-east-1

# === Redis Step 3: Delete replication groups (REQUIRES: elasticache:DeleteReplicationGroup) ===
aws elasticache delete-replication-group \
  --replication-group-id luckyus-redis-dify \
  --no-retain-primary-cluster \
  --region us-east-1

aws elasticache delete-replication-group \
  --replication-group-id luckyus-difynew \
  --no-retain-primary-cluster \
  --region us-east-1

# === Redis Step 4: Verify deletion (takes 5-10 min) ===
aws elasticache describe-replication-groups \
  --replication-group-id luckyus-redis-dify \
  --region us-east-1 2>&1
# Expected: ReplicationGroupNotFoundFault

aws elasticache describe-replication-groups \
  --replication-group-id luckyus-difynew \
  --region us-east-1 2>&1
# Expected: ReplicationGroupNotFoundFault

# === Redis Step 5: Check custom parameter group usage ===
aws elasticache describe-cache-clusters \
  --query 'CacheClusters[?CacheParameterGroup.CacheParameterGroupName==`luckyus-ha-6`].CacheClusterId' \
  --region us-east-1
# If empty after deletion: safe to delete
# aws elasticache delete-cache-parameter-group \
#   --cache-parameter-group-name luckyus-ha-6 --region us-east-1
```

### 4.3 OpenSearch Deletion

**Domain**: `luckyus-opensearch-dify` (2x r6g.large data + 3x m7g.large, 60GB)

**Key config**:
- VPC: vpc-0dce7ca7770422d33
- Subnets: subnet-01608eef3ea13c7d3, subnet-0acd412a7bc5ebc55
- Security group: `sg-0deaa7cf7437e39c7` (shared — DO NOT DELETE)
- KMS: arn:aws:kms:us-east-1:257394478466:key/0d74cdfc-57ba-4d94-8947-2249228352f1
- Advanced Security: enabled (internal user DB)
- 4 orphaned ENIs (all status=available, description="ES luckyus-opensearch-dify")

**Note**: Domain only has 26 documents — data is trivial, no snapshot needed.

```bash
# === OpenSearch Step 1: Delete domain (REQUIRES: es:DeleteDomain) ===
aws opensearch delete-domain \
  --domain-name luckyus-opensearch-dify \
  --region us-east-1

# === OpenSearch Step 2: Wait for deletion (15-30 min) ===
aws opensearch describe-domain \
  --domain-name luckyus-opensearch-dify \
  --query 'DomainStatus.{Deleted:Deleted,Processing:Processing}' \
  --region us-east-1
# Expected: Deleted=true during processing, then ResourceNotFoundException

# === OpenSearch Step 3: Clean up orphaned ENIs (REQUIRES: ec2:DeleteNetworkInterface) ===
# Wait 30+ min after domain deletion — ENIs may auto-cleanup
aws ec2 describe-network-interfaces \
  --network-interface-ids eni-0d623c6205c24d3a7 eni-0ba40d95964577c62 \
    eni-0d7735e22a081705c eni-0f2adc1cdec3cab8a \
  --query 'NetworkInterfaces[].{ID:NetworkInterfaceId,Status:Status}' \
  --region us-east-1

# If still status=available, delete manually:
aws ec2 delete-network-interface --network-interface-id eni-0d623c6205c24d3a7 --region us-east-1
aws ec2 delete-network-interface --network-interface-id eni-0ba40d95964577c62 --region us-east-1
aws ec2 delete-network-interface --network-interface-id eni-0d7735e22a081705c --region us-east-1
aws ec2 delete-network-interface --network-interface-id eni-0f2adc1cdec3cab8a --region us-east-1

# === OpenSearch Step 4: KMS key assessment ===
# Key: 0d74cdfc-57ba-4d94-8947-2249228352f1
# CANNOT determine scope (kms:DescribeKey/ListGrants denied)
# ACTION: Ask AWS admin to check if this KMS key is used by other services
# If ONLY used by OpenSearch Dify: schedule key deletion (30-day waiting period)
#   aws kms schedule-key-deletion --key-id 0d74cdfc-57ba-4d94-8947-2249228352f1 \
#     --pending-window-in-days 30 --region us-east-1
# If SHARED: leave as-is
```

### 4.4 EC2 Instance Deletion

**Instances**:
- i-06e7301a6e3f28df4 (isredify01, c6i.large) — Milvus-related
- i-02d4ea4bbab7fd574 (iluckydifyjump01, c6i.large) — Dify jump server

**Both have**: DeleteOnTermination=true on root EBS volumes (vol-00f8df5db42547f32, vol-00419fed999cc4e01)

```bash
# === EC2 Step 1: Stop instances (REQUIRES: ec2:StopInstances) ===
aws ec2 stop-instances \
  --instance-ids i-06e7301a6e3f28df4 i-02d4ea4bbab7fd574 \
  --region us-east-1

# === EC2 Step 2: Wait for stopped state ===
aws ec2 wait instance-stopped \
  --instance-ids i-06e7301a6e3f28df4 i-02d4ea4bbab7fd574 \
  --region us-east-1

# === EC2 Step 3: Observe 48 hours ===
# Monitor for any alerts or complaints. If nothing surfaces after 48h, proceed.

# === EC2 Step 4: Terminate (REQUIRES: ec2:TerminateInstances) ===
aws ec2 terminate-instances \
  --instance-ids i-06e7301a6e3f28df4 i-02d4ea4bbab7fd574 \
  --region us-east-1

# EBS volumes auto-delete (DeleteOnTermination=true)

# === EC2 Step 5: Verify ===
aws ec2 describe-instances \
  --instance-ids i-06e7301a6e3f28df4 i-02d4ea4bbab7fd574 \
  --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name}' \
  --region us-east-1
# Expected: State=terminated
```

### 4.5 S3 Bucket Deletion

**Buckets**: lk-infra-dify (Milvus object store), lk-infra-dify-data, lk-infra-dify-plugindaemon

**Key facts**:
- Total: 73MB / 663 objects
- Versioning: NOT enabled on any bucket (confirmed)

```bash
# === S3 Step 1: List and verify contents (REQUIRES: s3:ListBucket, s3:GetObject) ===
aws s3 ls s3://lk-infra-dify --recursive --summarize --region us-east-1
aws s3 ls s3://lk-infra-dify-data --recursive --summarize --region us-east-1
aws s3 ls s3://lk-infra-dify-plugindaemon --recursive --summarize --region us-east-1

# === S3 Step 2: Empty buckets (REQUIRES: s3:DeleteObject) ===
# Since versioning is NOT enabled, simple delete works
aws s3 rm s3://lk-infra-dify --recursive --region us-east-1
aws s3 rm s3://lk-infra-dify-data --recursive --region us-east-1
aws s3 rm s3://lk-infra-dify-plugindaemon --recursive --region us-east-1

# === S3 Step 3: Delete buckets (REQUIRES: s3:DeleteBucket) ===
aws s3 rb s3://lk-infra-dify --region us-east-1
aws s3 rb s3://lk-infra-dify-data --region us-east-1
aws s3 rb s3://lk-infra-dify-plugindaemon --region us-east-1

# === S3 Step 4: Verify ===
aws s3 ls 2>&1 | grep dify
# Expected: no results
```

### 4.6 Shared Resources Safety Checklist

**DO NOT DELETE the following shared resources:**

| Resource | ID/Name | Reason | Used By |
|----------|---------|--------|---------|
| RDS Subnet Group | `rds-group` | Shared | 64 RDS instances |
| ElastiCache Subnet Group | `redis-group` | Shared | 76 replication groups |
| Security Group | `sg-0deaa7cf7437e39c7` | Shared | 623 ENIs across entire environment |
| NLB Security Groups | `sg-0eeb5a6d5c495e30e`, `sg-0550dcb1098214e38` | Milvus NLB-specific | Auto-cleanup when NLB deleted |
| Parameter Group | `default.postgres16` | AWS default | Cannot delete |
| Parameter Group | `default.redis7` | AWS default | Cannot delete |
| KMS Key | `0d74cdfc-57ba-4d94-8947-2249228352f1` | Scope unknown | Need admin verification |
| Ingress-nginx Service/NLB | ingress-nginx-controller | Shared | 6 namespaces, 12+ ingresses |
| VPC | `vpc-0dce7ca7770422d33` | Shared | Entire environment |

---

## 五、EKS Node Scaling

### 5.1 Current Configuration

| Parameter | Value |
|-----------|-------|
| Node group | eksnodegroupworker |
| Instance type | m6i.8xlarge (32 vCPU, 128 GiB) |
| Current desired | 13 |
| Min | 1 |
| Max | 13 |
| Total cluster capacity | 416 vCPU / 1,664 GiB |

### 5.2 Dify Resource Footprint

From reconnaissance (46 pods):

| Component | CPU Requests | Memory Requests |
|-----------|-------------|-----------------|
| Old Dify (5 pods) | ~2.25 vCPU | ~6 GiB |
| New Dify (13 pods) | ~4.75 vCPU | ~9.5 GiB |
| Milvus core (17 pods) | ~10 vCPU | ~20 GiB |
| Milvus etcd (3 pods) | ~1.5 vCPU | ~3 GiB |
| Milvus Pulsar (8 pods) | ~4 vCPU | ~8 GiB |
| **Total Dify** | **~22.5 vCPU** | **~46.5 GiB** |

### 5.3 Post-Dify Capacity Calculation

```
Total capacity (13 nodes):     416 vCPU / 1,664 GiB
Dify footprint to remove:      -22.5 vCPU / -46.5 GiB
DaemonSet overhead (5 DS/node): ~2.5 vCPU / ~5 GiB per node (estimated)
DaemonSet total (13 nodes):    ~32.5 vCPU / ~65 GiB

Remaining for workloads:       416 - 32.5 = 383.5 vCPU / 1,599 GiB
Dify removal frees:            22.5 vCPU / 46.5 GiB
One node capacity:             32 vCPU / 128 GiB
```

**After removing Dify, freed capacity < 1 full node** (22.5 vCPU < 32 vCPU). However, if other nodes have headroom, scaling 13→12 may be safe.

### 5.4 Recommendation

**Conservative (recommended)**: Keep at 13 nodes, monitor utilization for 1-2 weeks post-decommission via Grafana/Prometheus, then evaluate scaling.

**If scaling down**: Need full cluster pod resource audit first.

```bash
# Scale down command (REQUIRES: eks:UpdateNodegroupConfig):
aws eks update-nodegroup-config \
  --cluster-name prod-worker01-eks-us \
  --nodegroup-name eksnodegroupworker \
  --scaling-config minSize=1,maxSize=13,desiredSize=12 \
  --region us-east-1

# Verify:
aws eks describe-nodegroup \
  --cluster-name prod-worker01-eks-us \
  --nodegroup-name eksnodegroupworker \
  --query 'nodegroup.scalingConfig' \
  --region us-east-1
```

### 5.5 PDB Constraints

3 PDBs exist cluster-wide (none in Dify namespace):
- `apisix-etcd` (api-gateway namespace)
- `coredns` (kube-system)
- `ebs-csi-controller` (kube-system)

These may slow node draining but will not block scaling down.

---

## 六、DNS + Ingress Cleanup

### 6.1 DNS Records to Clean Up

| Record | Service | Ingress Class |
|--------|---------|---------------|
| `dify-console.luckincoffee.us` | new-dify-ingress → new-dify-api/new-dify-web | nginx (shared) |
| `milvus-attu.luckincoffee.us` | milvus-attu → milvus-attu:3000 | nginx (shared) |

### 6.2 External-DNS Assessment

**No external-dns deployment found in kube-system.** DNS records will NOT auto-cleanup when Ingresses are deleted. Manual Route53 cleanup is required.

### 6.3 Ingress Backup Reference

Ingress `new-dify-ingress` key config:
```yaml
spec:
  ingressClassName: nginx
  rules:
  - host: dify-console.luckincoffee.us
    http:
      paths:
      - path: /console  -> new-dify-api:5001
      - path: /api      -> new-dify-api:5001
      - path: /v1       -> new-dify-api:5001
      - path: /         -> new-dify-web:3000
  # Load Balancer IP: 10.238.14.214 (ingress-nginx internal)
```

### 6.4 Route53 Cleanup Commands

```bash
# REQUIRES: route53:ListHostedZones, route53:ChangeResourceRecordSets

# Step 1: Find the hosted zone for luckincoffee.us
aws route53 list-hosted-zones-by-name \
  --dns-name luckincoffee.us \
  --max-items 1 \
  --region us-east-1

# Step 2: List Dify records
aws route53 list-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --query "ResourceRecordSets[?contains(Name, 'dify')]" \
  --region us-east-1

# Step 3: Delete records (build JSON from Step 2 output)
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch '{
    "Changes": [
      {
        "Action": "DELETE",
        "ResourceRecordSet": {
          "Name": "dify-console.luckincoffee.us.",
          "Type": "<TYPE>",
          "TTL": <TTL>,
          "ResourceRecords": [{"Value": "<VALUE>"}]
        }
      },
      {
        "Action": "DELETE",
        "ResourceRecordSet": {
          "Name": "milvus-attu.luckincoffee.us.",
          "Type": "<TYPE>",
          "TTL": <TTL>,
          "ResourceRecords": [{"Value": "<VALUE>"}]
        }
      }
    ]
  }' \
  --region us-east-1
```

**Fallback**: If DBA user cannot get Route53 access, provide the record names to DevOps (彭啸) for manual cleanup.

---

## 七、Credential Rotation Checklist

### 7.1 Credentials Found in Dify Deployments

| # | Credential | Location | Scope | Action |
|---|-----------|----------|-------|--------|
| 1 | DB_PASSWORD (dify_w) | new-dify-* annotations | Dify-only | Revoked when RDS deleted |
| 2 | REDIS_PASSWORD | new-dify-* annotations | Dify-only | Revoked when ElastiCache deleted |
| 3 | OPENSEARCH_PASSWORD | new-dify-* annotations | Dify-only | Revoked when OpenSearch deleted |
| 4 | SECRET_KEY | new-dify-* annotations | Dify internal (JWT) | No action needed |
| 5 | SMTP_PASSWORD | new-dify-* annotations | **POTENTIALLY SHARED** | See 7.2 below |
| 6 | PLUGIN_DAEMON_KEY | new-dify-* annotations | Dify internal | No action needed |
| 7 | CODE_EXECUTION_API_KEY | new-dify-* annotations | Dify sandbox | No action needed |
| 8 | AWS_ACCESS_KEY_ID | milvus ConfigMap | Milvus S3 access | **MUST DEACTIVATE/DELETE** |
| 9 | AWS_SECRET_ACCESS_KEY | milvus ConfigMap | Milvus S3 access | **MUST DEACTIVATE/DELETE** |

### 7.2 SMTP Credential Scope

- SMTP user: `dify@luckincoffee.us`
- SMTP host: email-smtp.us-east-1.amazonaws.com (AWS SES)
- Cannot verify SES identity list (ses:ListIdentities denied)

**Action**: Ask DevOps (彭啸) if `dify@luckincoffee.us` is used by any other service. If Dify-only, disable the SES identity after decommission.

### 7.3 AWS IAM Credential Rotation (CRITICAL)

The Milvus ConfigMap contains hardcoded AWS access key `AKIATX3PIBWBAXDXUX65`. After decommission:

```bash
# REQUIRES: IAM admin access (NOT databasecheck user)

# Step 1: Check what IAM user owns the key
aws iam get-access-key-last-used --access-key-id AKIATX3PIBWBAXDXUX65

# Step 2: Deactivate the key (safe — can re-enable if needed)
aws iam update-access-key \
  --access-key-id AKIATX3PIBWBAXDXUX65 \
  --status Inactive \
  --user-name <USER>

# Step 3: After 48h with no issues, delete the key
aws iam delete-access-key \
  --access-key-id AKIATX3PIBWBAXDXUX65 \
  --user-name <USER>
```

### 7.4 MCP Gateway Entries to Remove

3 entries in mcp-db-gateway (http://10.238.3.43:8080):

| # | Type | Server Name | Action |
|---|------|-------------|--------|
| 1 | PostgreSQL | `aws-luckyus-dify-rw` | Remove from gateway config |
| 2 | PostgreSQL | `aws-luckyus-difynew-rw` | Remove from gateway config |
| 3 | Redis | `luckyus-redis-dify` | Remove from gateway config |

**Note**: `luckyus-difynew` Redis is NOT registered in MCP gateway (accessed directly by pods only).

Contact MCP gateway admin to update the configuration file and restart the gateway service.

---

## 八、Complete Permission Request Template

**To**: Michael (CTO) / AWS Account Admin
**From**: David Zeng (DBA/Infrastructure)
**Subject**: IAM Permission Request — Dify Platform Decommission
**Priority**: Medium (non-urgent, cost optimization)

---

**Request**: Temporary IAM policy attachment for user `databasecheck` to execute Dify platform decommission.

**Business Justification**: Dify AI platform has been idle since 2026-03-23 (15+ days zero API activity, 29 days zero user logins). Per DevOps lead 彭啸, project is paused for at least 6 months. Monthly cost: ~$2,190. Total savings over pause period: ~$12,000. All data will be preserved via snapshots before deletion.

**Duration**: 7 days (temporary). Remove after decommission is complete.

**Scope**: Limited to Dify-specific resources only (resource ARNs listed below).

### Required IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RDSDifyDecommission",
      "Effect": "Allow",
      "Action": [
        "rds:CreateDBSnapshot",
        "rds:ModifyDBInstance",
        "rds:DeleteDBInstance"
      ],
      "Resource": [
        "arn:aws:rds:us-east-1:257394478466:db:aws-luckyus-dify-rw",
        "arn:aws:rds:us-east-1:257394478466:db:aws-luckyus-difynew-rw",
        "arn:aws:rds:us-east-1:257394478466:snapshot:decom-final-*"
      ]
    },
    {
      "Sid": "ElastiCacheDifyDecommission",
      "Effect": "Allow",
      "Action": [
        "elasticache:CreateSnapshot",
        "elasticache:DeleteReplicationGroup"
      ],
      "Resource": [
        "arn:aws:elasticache:us-east-1:257394478466:replicationgroup:luckyus-redis-dify",
        "arn:aws:elasticache:us-east-1:257394478466:replicationgroup:luckyus-difynew",
        "arn:aws:elasticache:us-east-1:257394478466:snapshot:decom-final-*"
      ]
    },
    {
      "Sid": "OpenSearchDifyDecommission",
      "Effect": "Allow",
      "Action": [
        "es:DeleteDomain"
      ],
      "Resource": [
        "arn:aws:es:us-east-1:257394478466:domain/luckyus-opensearch-dify"
      ]
    },
    {
      "Sid": "EC2DifyDecommission",
      "Effect": "Allow",
      "Action": [
        "ec2:StopInstances",
        "ec2:TerminateInstances"
      ],
      "Resource": [
        "arn:aws:ec2:us-east-1:257394478466:instance/i-06e7301a6e3f28df4",
        "arn:aws:ec2:us-east-1:257394478466:instance/i-02d4ea4bbab7fd574"
      ]
    },
    {
      "Sid": "ENICleanup",
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteNetworkInterface"
      ],
      "Resource": [
        "arn:aws:ec2:us-east-1:257394478466:network-interface/eni-0d623c6205c24d3a7",
        "arn:aws:ec2:us-east-1:257394478466:network-interface/eni-0ba40d95964577c62",
        "arn:aws:ec2:us-east-1:257394478466:network-interface/eni-0d7735e22a081705c",
        "arn:aws:ec2:us-east-1:257394478466:network-interface/eni-0f2adc1cdec3cab8a"
      ]
    },
    {
      "Sid": "S3DifyDecommission",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:DeleteBucket"
      ],
      "Resource": [
        "arn:aws:s3:::lk-infra-dify",
        "arn:aws:s3:::lk-infra-dify/*",
        "arn:aws:s3:::lk-infra-dify-data",
        "arn:aws:s3:::lk-infra-dify-data/*",
        "arn:aws:s3:::lk-infra-dify-plugindaemon",
        "arn:aws:s3:::lk-infra-dify-plugindaemon/*"
      ]
    },
    {
      "Sid": "Route53DifyDNS",
      "Effect": "Allow",
      "Action": [
        "route53:ListHostedZones",
        "route53:ListResourceRecordSets",
        "route53:ChangeResourceRecordSets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EKSNodeScaling",
      "Effect": "Allow",
      "Action": [
        "eks:UpdateNodegroupConfig"
      ],
      "Resource": [
        "arn:aws:eks:us-east-1:257394478466:nodegroup/prod-worker01-eks-us/eksnodegroupworker/*"
      ]
    },
    {
      "Sid": "KMSAudit",
      "Effect": "Allow",
      "Action": [
        "kms:DescribeKey",
        "kms:ListAliases",
        "kms:ListGrants"
      ],
      "Resource": [
        "arn:aws:kms:us-east-1:257394478466:key/0d74cdfc-57ba-4d94-8947-2249228352f1"
      ]
    }
  ]
}
```

**Policy name suggestion**: `DifyDecommission-Temporary-20260408`

**Recommended approach**: Create an inline policy on user `databasecheck`, set a calendar reminder to remove after 7 days.

---

## 九、Master Execution Checklist

### Phase 0: Prerequisites (before execution day)

| # | Step | Command/Action | Permission | Status |
|---|------|----------------|------------|--------|
| 0.1 | Submit IAM permission request | Send Section 八 to AWS admin | N/A | TODO |
| 0.2 | Get IAM permissions granted | Wait for admin approval | N/A | TODO |
| 0.3 | Enable MCP eks-server write mode | Add `--allow-write` flag to eks-server config | Admin | TODO |
| 0.4 | Verify Helm CLI access | `helm list -n baseservices-cloud-dify` | kubectl/RBAC | TODO |
| 0.5 | Confirm SMTP credential scope | Ask 彭啸 if dify@luckincoffee.us is shared | N/A | TODO |
| 0.6 | Confirm KMS key scope | Ask admin: is key 0d74cdfc-... used by other services? | kms:DescribeKey | TODO |
| 0.7 | Notify stakeholders | Email: ops team, 彭啸, 王东尧 | N/A | TODO |

### Phase 1: Backup & Verify (~30 min)

| # | Step | Command | Permission | Depends On |
|---|------|---------|------------|------------|
| 1.1 | Create RDS snapshot (dify-rw) | `aws rds create-db-snapshot --db-instance-identifier aws-luckyus-dify-rw --db-snapshot-identifier decom-final-dify-rw-20260408` | rds:CreateDBSnapshot | 0.2 |
| 1.2 | Create RDS snapshot (difynew-rw) | `aws rds create-db-snapshot --db-instance-identifier aws-luckyus-difynew-rw --db-snapshot-identifier decom-final-difynew-rw-20260408` | rds:CreateDBSnapshot | 0.2 |
| 1.3 | Create Redis snapshot (redis-dify) | `aws elasticache create-snapshot --replication-group-id luckyus-redis-dify --snapshot-name decom-final-redis-dify-20260408` | elasticache:CreateSnapshot | 0.2 |
| 1.4 | Create Redis snapshot (difynew) | `aws elasticache create-snapshot --replication-group-id luckyus-difynew --snapshot-name decom-final-redis-difynew-20260408` | elasticache:CreateSnapshot | 0.2 |
| 1.5 | Backup K8s namespace YAML | `kubectl get all,pvc,configmap,ingress,sa -n baseservices-cloud-dify -o yaml > ~/backup-dify-namespace-full.yaml` | kubectl | 0.4 |
| 1.6 | Backup Ingress YAML | `kubectl get ingress -n baseservices-cloud-dify -o yaml > ~/backup-dify-ingresses.yaml` | kubectl | 0.4 |
| 1.7 | Export Dify app/token data | MCP postgres_query on difynew-rw: `SELECT id,name,mode,created_at FROM apps` | MCP | — |
| 1.8 | Wait for all snapshots | `aws rds wait db-snapshot-available` + poll elasticache | — | 1.1-1.4 |
| 1.9 | Verify all 4 snapshots available | Describe snapshot commands | Read-only | 1.8 |

### Phase 2: K8s Namespace Teardown (~15 min)

| # | Step | Command | Permission | Depends On |
|---|------|---------|------------|------------|
| 2.1 | Scale down StatefulSets | `kubectl scale statefulset milvus-etcd milvus-pulsar-bookie milvus-pulsar-broker milvus-pulsar-proxy milvus-pulsar-zookeeper --replicas=0 -n baseservices-cloud-dify` | kubectl write | 1.9 |
| 2.2 | Wait for pods to terminate | `kubectl wait --for=delete pod -l app.kubernetes.io/instance=milvus --timeout=120s -n baseservices-cloud-dify` | kubectl | 2.1 |
| 2.3 | Delete Ingresses | `kubectl delete ingress --all -n baseservices-cloud-dify` | kubectl write | 2.2 |
| 2.4 | Helm uninstall dify | `helm uninstall dify -n baseservices-cloud-dify` | Helm + kubectl | 2.3 |
| 2.5 | Helm uninstall milvus | `helm uninstall milvus -n baseservices-cloud-dify` | Helm + kubectl | 2.3 |
| 2.6 | Delete kubectl-applied resources | `kubectl delete deploy new-dify-api new-dify-web new-dify-worker new-dify-sandbox new-dify-plugin-daemon -n baseservices-cloud-dify` | kubectl write | 2.5 |
| 2.7 | Delete remaining services | `kubectl delete svc new-dify-api new-dify-web new-dify-sandbox new-dify-plugin-daemon hello-world -n baseservices-cloud-dify` | kubectl write | 2.6 |
| 2.8 | Delete all PVCs | `kubectl delete pvc --all -n baseservices-cloud-dify` | kubectl write | 2.7 |
| 2.9 | Delete namespace | `kubectl delete namespace baseservices-cloud-dify` | kubectl write | 2.8 |
| 2.10 | Verify NLB deleted | `aws elbv2 describe-load-balancers --names inf-milvus-service 2>&1` | Read-only | 2.5 |
| 2.11 | Verify EBS volumes deleted | `aws ec2 describe-volumes --filters 'Name=tag:kubernetes.io/created-for/pvc/namespace,Values=baseservices-cloud-dify'` | Read-only | 2.8 |
| 2.12 | Verify namespace gone | `kubectl get namespace baseservices-cloud-dify 2>&1` | kubectl | 2.9 |

### Phase 3: AWS Managed Service Deletion (~45 min)

| # | Step | Command | Permission | Depends On |
|---|------|---------|------------|------------|
| 3.1 | Disable RDS deletion protection (dify-rw) | `aws rds modify-db-instance --db-instance-identifier aws-luckyus-dify-rw --no-deletion-protection --apply-immediately` | rds:ModifyDBInstance | 2.12 |
| 3.2 | Disable RDS deletion protection (difynew-rw) | Same for difynew-rw | rds:ModifyDBInstance | 2.12 |
| 3.3 | Wait for RDS modification | `aws rds wait db-instance-available` for both | — | 3.1, 3.2 |
| 3.4 | Delete RDS (dify-rw) | `aws rds delete-db-instance --db-instance-identifier aws-luckyus-dify-rw --skip-final-snapshot --delete-automated-backups` | rds:DeleteDBInstance | 3.3 |
| 3.5 | Delete RDS (difynew-rw) | Same for difynew-rw | rds:DeleteDBInstance | 3.3 |
| 3.6 | Delete ElastiCache (redis-dify) | `aws elasticache delete-replication-group --replication-group-id luckyus-redis-dify --no-retain-primary-cluster` | elasticache:DeleteReplicationGroup | 2.12 |
| 3.7 | Delete ElastiCache (difynew) | Same for luckyus-difynew | elasticache:DeleteReplicationGroup | 2.12 |
| 3.8 | Delete OpenSearch | `aws opensearch delete-domain --domain-name luckyus-opensearch-dify` | es:DeleteDomain | 2.12 |
| 3.9 | Stop EC2 instances | `aws ec2 stop-instances --instance-ids i-06e7301a6e3f28df4 i-02d4ea4bbab7fd574` | ec2:StopInstances | 2.12 |
| 3.10 | Verify RDS deletions | Describe commands for both | Read-only | 3.4, 3.5 |
| 3.11 | Verify ElastiCache deletions | Describe commands for both | Read-only | 3.6, 3.7 |
| 3.12 | Verify OpenSearch deletion | Describe domain command | Read-only | 3.8 |

### Phase 4: Cleanup (~30 min + 48h for EC2)

| # | Step | Command | Permission | Depends On |
|---|------|---------|------------|------------|
| 4.1 | Delete orphaned ENIs | `aws ec2 delete-network-interface` (x4) | ec2:DeleteNetworkInterface | 3.12 + 30 min |
| 4.2 | Empty & delete S3 buckets | `aws s3 rm --recursive` + `aws s3 rb` (x3) | s3:DeleteObject, s3:DeleteBucket | 2.12 |
| 4.3 | Delete DNS records | Route53 change-resource-record-sets | route53:ChangeResourceRecordSets | 2.3 |
| 4.4 | Remove MCP gateway entries | Contact gateway admin | Admin access | 3.10, 3.11 |
| 4.5 | Deactivate Milvus AWS access key | `aws iam update-access-key --access-key-id AKIATX3PIBWBAXDXUX65 --status Inactive` | iam:UpdateAccessKey (admin) | 2.12 |
| 4.6 | Check custom param group usage | `aws elasticache describe-cache-clusters --query '..luckyus-ha-6..'` | Read-only | 3.11 |
| 4.7 | Terminate EC2 (after 48h) | `aws ec2 terminate-instances --instance-ids i-06e7301a6e3f28df4 i-02d4ea4bbab7fd574` | ec2:TerminateInstances | 3.9 + 48h |
| 4.8 | Check ClusterRoleBindings | `kubectl get clusterrolebinding -o json \| jq '..baseservices-cloud-dify..'` | kubectl | 2.12 |

### Phase 5: EKS Node Scaling (1-2 weeks post-decommission)

| # | Step | Command | Permission | Depends On |
|---|------|---------|------------|------------|
| 5.1 | Monitor cluster utilization 1-2 weeks | Grafana / Prometheus | Read-only | Phase 4 |
| 5.2 | Evaluate safe node count | Calculate workload vs capacity | — | 5.1 |
| 5.3 | Scale nodegroup if safe | `aws eks update-nodegroup-config ...desiredSize=12` | eks:UpdateNodegroupConfig | 5.2 |

### Phase 6: Verification & Final Cleanup (1 week+)

| # | Step | Command | Permission | Depends On |
|---|------|---------|------------|------------|
| 6.1 | Verify manual snapshots exist | RDS + ElastiCache describe | Read-only | Phase 3 |
| 6.2 | Delete Milvus AWS key (48h after deactivation) | `aws iam delete-access-key` | iam:DeleteAccessKey (admin) | 4.5 + 48h |
| 6.3 | Remove temporary IAM policy | Delete `DifyDecommission-Temporary-20260408` | Admin | Phase 4 |
| 6.4 | Cost verification | Cost Explorer: compare pre/post | cost-explorer | 30 days post |
| 6.5 | Update CLAUDE.md | Remove Dify references | — | Phase 4 |
| 6.6 | Archive this runbook | Copy to /app/reports/ and push to GitHub | — | Phase 6 |

---

**End of Runbook**

Estimated execution time: Phases 1-3 = ~90 minutes (day-of), Phase 4 = +48 hours (EC2 observation), Phases 5-6 = +2 weeks (monitoring).
