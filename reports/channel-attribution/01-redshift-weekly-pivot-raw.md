# Redshift Weekly Pivot — Raw Results

**Query Date:** 2026-03-19
**Status:** BLOCKED — Access Denied

## Pre-flight Result

```
Error: An error occurred (AccessDenied) when calling the DescribeClusters operation:
User: arn:aws:iam::257394478466:user/databasecheck is not authorized to perform:
redshift:DescribeClusters on resource: arn:aws:redshift:us-east-1:257394478466:cluster:*
because no identity-based policy allows the redshift:DescribeClusters action
```

## Impact

Redshift path is blocked. The following permissions are required:
- `redshift:DescribeClusters` (for provisioned clusters)
- `redshift-serverless:ListWorkgroups` (for serverless workgroups)
- `redshift-data:ExecuteStatement`
- `redshift-data:DescribeStatement`
- `redshift-data:GetStatementResult`

## Fallback Executed

Reverted to MySQL-only path:
- Primary: `salescrm.t_user` weekly registrations by origin code (Feb 1 – Mar 19)
- Supplement: `isalescdp.t_user_event_track` CDP events (Mar 19 only — CDP went live Mar 19)

## Action Required

Request Redshift `SELECT` permission from Michael (CTO) or Data Platform team for:
- IAM user: `databasecheck` (account 257394478466)
- Target: Redshift Serverless workgroup (likely contains full historical event table with true adid)

## What Redshift Would Enable

| Capability | MySQL Now | Redshift (if unblocked) |
|-----------|-----------|------------------------|
| Feb 1 – Mar 4 channel breakdown | origin code only (no scan/social split) | Full channel + adid + event type |
| True offline QR scan count | Not separable from H5 | Scan page event (`$page.scan$...`) |
| True adid attribution | Not available (p_device_id sparse) | Full IDFA/GAID coverage |
| Social media attribution | Not available | Adjust link data (when deployed) |
