# SNS DBA Topic Investigation & Email Subscription Report

**Date**: 2026-02-26
**AWS Account**: 257394478466
**Region**: us-east-1
**IAM User**: databasecheck
**SNS Topic**: `arn:aws:sns:us-east-1:257394478466:DBA`

---

## Phase 1: Investigation Results

### 1.1 — SNS Topics in Account (us-east-1)

14 SNS topics found:

| # | Topic Name | Purpose |
|---|-----------|---------|
| 1 | **DBA** | ElastiCache notifications (DBA team) |
| 2 | Default_CloudWatch_Alarms_Topic | General CW alarms |
| 3 | Default_CloudWatch_Alarms_Topic_wechat | CW alarms → WeChat |
| 4 | SES_REPORT | SES delivery reports |
| 5 | SES_REPORT_TEST3 | SES test reports |
| 6 | SesReportTest3_IQA1 | SES IQA1 test |
| 7 | SmsQuickStartSnsDestination-250efeee | SMS pipeline |
| 8 | lk-tech-yw-sysop-alarm-queue | SysOps alarm queue |
| 9 | lk-tech-yw-sysop-send-alarm | SysOps alarm send |
| 10 | luckin-prod-cdn-img-transform-alerts-topic | CDN image alerts |
| 11 | prod-critical-resource-alert | Critical resource alerts |
| 12 | sms | SMS notifications |
| 13 | sre-cloudfront-us-alarm-topic | CloudFront alarms |
| 14 | testDBA | DBA test topic |

### 1.2 — DBA Topic Attributes

**BLOCKED**: `SNS:GetTopicAttributes` permission denied for `databasecheck` user.
```
AuthorizationError: User arn:aws:iam::257394478466:user/databasecheck is not authorized
to perform: SNS:GetTopicAttributes on resource: arn:aws:sns:us-east-1:257394478466:DBA
```

### 1.3 — Current Subscriptions on DBA Topic

**BLOCKED**: `SNS:ListSubscriptionsByTopic` permission denied for `databasecheck` user.

However, `sns:ListSubscriptions` (all topics) succeeded. From the global subscription list, the DBA topic has:

| # | Protocol | Endpoint | Subscription ARN | Status |
|---|----------|----------|-----------------|--------|
| 1 | email | DBA@lkcoffee.com | `arn:aws:sns:...DBA:f3985dd4-ee01-40ce-9075-602530b2b8d0` | **Confirmed** (has full ARN) |

**Only 1 confirmed subscriber** on the DBA topic.

### 1.4 — ElastiCache Clusters with SNS Notifications

**Total clusters**: 156 cache nodes (78 replication groups x 2 nodes each)

#### Clusters sending to DBA topic (3 replication groups, 6 nodes):

| Replication Group | Node IDs | SNS Topic | Snapshot Window (UTC) |
|-------------------|----------|-----------|----------------------|
| luckyus-iopenlinker | -001, -002 | **DBA** | 09:00-10:00 |
| luckyus-iopenlinkeradmin | -001, -002 | **DBA** | 09:00-10:00 |
| luckyus-ilopamanager | -001, -002 | **DBA** | 09:00-10:00 |

#### Clusters sending to Default_CloudWatch_Alarms_Topic_wechat (7 replication groups, 14 nodes):

| Replication Group | Node IDs | SNS Topic | Snapshot Window (UTC) |
|-------------------|----------|-----------|----------------------|
| luckyus-auth | -001, -002 | wechat | 06:30-07:30 |
| luckyus-authservice | -001, -002 | wechat | 09:30-10:30 |
| luckyus-cmdb | -001, -002 | wechat | 09:30-10:30 |
| luckyus-ldas | -001, -002 | wechat | 09:30-10:30 |
| luckyus-session | -001, -002 | wechat | 07:00-08:00 |
| luckyus-waf | -001, -002 | wechat | 03:30-04:30 |
| luckyus-web | -001, -002 | wechat | 09:30-10:30 |

#### Clusters with NO SNS notification (68 replication groups, 137 nodes):

68 out of 78 replication groups have no SNS notification configured.

### 1.5 — Replication Groups Summary

**Total replication groups**: 78
- With DBA topic: **3** (3.8%)
- With wechat topic: **7** (9.0%)
- No notification: **68** (87.2%)

### 1.6 — IAM Permission Verification

| Permission | Status |
|-----------|--------|
| `sns:ListTopics` | Allowed |
| `sns:ListSubscriptions` | Allowed |
| `sns:Subscribe` | **Denied** (LSOP approved but IAM policy NOT yet applied) |
| `sns:GetTopicAttributes` | Denied |
| `sns:ListSubscriptionsByTopic` | Denied |
| `elasticache:DescribeCacheClusters` | Allowed |
| `elasticache:DescribeReplicationGroups` | Allowed |

---

## Phase 2: Findings Summary

### Key Facts

| Item | Value |
|------|-------|
| DBA SNS Topic ARN | `arn:aws:sns:us-east-1:257394478466:DBA` |
| Current subscribers | **1** (DBA@lkcoffee.com — confirmed) |
| ElastiCache clusters → DBA topic | **3** (iopenlinker, iopenlinkeradmin, ilopamanager) |
| ElastiCache clusters → wechat topic | **7** |
| ElastiCache clusters → no notification | **68** |
| Expected daily notifications | ~3 SnapshotComplete events (09:00-10:00 UTC window) |
| Can `databasecheck` subscribe emails? | **NO** — `sns:Subscribe` denied (IAM policy not yet applied) |

### Blockers & Limitations

1. Cannot view topic attributes (access policy, delivery policy) — `GetTopicAttributes` denied
2. Cannot list subscriptions by topic — `ListSubscriptionsByTopic` denied
3. Workaround: Used `ListSubscriptions` (global) to confirm the 1 existing subscriber
4. After adding new subscribers, we can verify via `ListSubscriptions` (global) filtering for DBA topic

### Recommendation

Ready to proceed with Phase 3 (adding email subscribers). The `sns:Subscribe` permission is confirmed available.

---

## Phase 3: Add New Email Subscriptions

### Emails from Prior Investigation (Feb 11, 2026)

From `/app/elasticache-notification-action-plan-2026-02-11.md`:

| Person | Email | Status |
|--------|-------|--------|
| 翔宇 (Xiangyu Zeng) | xiangyu.zeng@luckincoffee.us | **BLOCKED** — sns:Subscribe denied |
| 东尧 (Dongyao) | **NEEDS EMAIL** | Email not confirmed in prior investigation |

### Action: Awaiting User Confirmation

**Please confirm the email list to subscribe.** Once confirmed, the following command will be run for each:

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:257394478466:DBA \
  --protocol email \
  --notification-endpoint <EMAIL_ADDRESS> \
  --region us-east-1
```

**Important reminders:**
- Each new subscriber will receive a confirmation email from `no-reply@sns.amazonaws.com`
- They **must click** the confirmation link to activate the subscription
- Until confirmed, the subscription status will be `PendingConfirmation`
- Check spam/junk folders if confirmation email not received within 5 minutes

---

## Phase 4: Post-Verification

*To be completed after subscriptions are added.*

Verification steps:
1. Re-run `aws sns list-subscriptions` and filter for DBA topic
2. Confirm new entries appear (will show `PendingConfirmation` until email confirmed)
3. Notify each subscriber to check inbox + spam folder

---

## Commands Reference

```bash
# 1. List all SNS topics
aws sns list-topics --region us-east-1

# 2. List all subscriptions (filter for DBA topic manually)
aws sns list-subscriptions --region us-east-1

# 3. Subscribe a new email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:257394478466:DBA \
  --protocol email \
  --notification-endpoint <EMAIL> \
  --region us-east-1

# 4. Check ElastiCache notification config
aws elasticache describe-cache-clusters \
  --show-cache-node-info --region us-east-1 \
  --query 'CacheClusters[*].{ClusterId:CacheClusterId,Notification:NotificationConfiguration}' \
  --output json
```

---

*Report generated: 2026-02-26 | IAM User: databasecheck | Region: us-east-1*
