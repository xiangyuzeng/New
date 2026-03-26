# LUCKIN OPS DASHBOARD — NETWORK FEASIBILITY REPORT
# 瑞幸运营看板 — 网络连通性检测报告

| Field | Value |
|-------|-------|
| **Date** | 2026-03-26 05:27 UTC |
| **EC2 Account** | 257394478466 |
| **IAM User** | arn:aws:iam::257394478466:user/databasecheck |
| **Region** | us-east-1 |
| **Hostname** | 3053f0c209f9 |
| **Python** | 3.11.2 |
| **AWS CLI** | aws-cli/2.34.16 Python/3.14.3 Linux/5.10.247-246.989.amzn2.x |

---

## Summary Table

| Test                    | Result  | Details                                            |
|-------------------------|---------|----------------------------------------------------|
| SMTP Gmail (587)        | FAIL    | [Errno 99] Cannot assign requested address        |
| SMTP Gmail (465)        | FAIL    | [Errno 99] Cannot assign requested address        |
| S3 Access               | OK      | HTTP 307, 0.031611s                               |
| S3 Write                | FAIL    | not tested or permission denied                   |
| S3 Presigned URL        | FAIL    | not tested                                        |
| GitHub API              | OK      | HTTP 200, 0.048819s                               |
| Gmail IMAP (993)        | FAIL    | [Errno 99] Cannot assign requested address        |
| Gmail REST API          | OK      | HTTP 404, 0.045085s                               |
| Google APIs             | OK      | HTTP 404, 0.136182s                               |
| Slack Webhook           | OK      | HTTP 302, 0.039760s                               |
| Docker                  | FAIL    | [Errno 13] Permission denied: 'docker'            |
| Docker Compose          | FAIL    | [Errno 13] Permission denied: 'docker'            |
| Docker Hub Pull         | FAIL    | [Errno 13] Permission denied: 'docker'            |
| Docker Compose Up       | FAIL    | Docker is not installed on this system. To run Docker-based |
| AWS CLI                 | OK      | aws-cli/2.34.16 Python/3.14.3 Linux/5.10, arn:aws:iam::257394478466:user/databasecheck|
| DNS Resolution          | OK      | all of 8 hosts resolved                           |
| Disk Space              | OK      | overlay          40G   29G   12G  72% /           |

---

## Detailed Results

### 1. DNS Resolution

| Hostname                                | Status | IPs                                      |
|-----------------------------------------|--------|------------------------------------------|
| smtp.gmail.com                          | OK    | 142.250.31.109                          |
| imap.gmail.com                          | OK    | 142.251.179.108, 142.251.179.109        |
| s3.us-east-1.amazonaws.com              | OK    | 16.15.219.121                           |
| sts.us-east-1.amazonaws.com             | OK    | 54.239.16.72                            |
| api.github.com                          | OK    | 140.82.114.6                            |
| hooks.slack.com                         | OK    | 3.210.88.6, 3.95.117.96, 34.193.255.5, 3|
| gmail.googleapis.com                    | OK    | 142.250.31.95, 142.251.111.95, 142.251.1|
| oauth2.googleapis.com                   | OK    | 142.251.16.95                           |

### 2. TCP Port Connectivity

| Service                       | Target             | Status  | Details                                  |
|-------------------------------|--------------------|---------|------------------------------------------|
| SMTP TLS (STARTTLS)           | smtp.gmail.com:587   | BLOCKED | [Errno 99] Cannot assign requested addre|
| SMTP SSL                      | smtp.gmail.com:465   | BLOCKED | [Errno 99] Cannot assign requested addre|
| SMTP Plain                    | smtp.gmail.com:25    | BLOCKED | [Errno 99] Cannot assign requested addre|
| IMAP SSL                      | imap.gmail.com:993   | BLOCKED | [Errno 99] Cannot assign requested addre|
| AWS S3 HTTPS                  | s3.us-east-1.amazonaws.com:443   | OPEN    | 7.7ms                                   |
| AWS STS HTTPS                 | sts.us-east-1.amazonaws.com:443   | OPEN    | 8.2ms                                   |
| GitHub API HTTPS              | api.github.com:443   | OPEN    | 7.6ms                                   |
| Slack Webhook HTTPS           | hooks.slack.com:443   | OPEN    | 8.5ms                                   |
| Gmail API HTTPS               | gmail.googleapis.com:443   | OPEN    | 7.1ms                                   |
| Google OAuth HTTPS            | oauth2.googleapis.com:443   | OPEN    | 10.4ms                                  |

### 3. HTTPS Endpoints

| Service             | URL                                          | HTTP | Time    | SSL         |
|---------------------|----------------------------------------------|------|---------|-------------|
| S3 Global           | https://s3.amazonaws.com                     | 307  | 0.031611| OK          |
| STS Global          | https://sts.amazonaws.com                    | 302  | 0.041232| OK          |
| GitHub API          | https://api.github.com                       | 200  | 0.048819| OK          |
| Gmail REST API      | https://gmail.googleapis.com                 | 404  | 0.045085| OK          |
| Google APIs         | https://www.googleapis.com                   | 404  | 0.136182| OK          |
| Slack Webhooks      | https://hooks.slack.com                      | 302  | 0.039760| OK          |

### 4. AWS CLI

- **Version:** aws-cli/2.34.16 Python/3.14.3 Linux/5.10.247-246.989.amzn2.x86_64 exe/x86_64.debian.12
- **Identity:** {
  "UserId": "AIDATX3PIBWBHOR7ZX46M",
  "Account": "257394478466",
  "Arn": "arn:aws:iam::257394478466:user/databasecheck"
}
- **S3 List:** OK — 5 buckets visible
- **S3 Dryrun:** FAIL — Completed 0 file(s) with ~0 file(s) remaining (calculating...)
- **Disk:** overlay          40G   29G   12G  72% /

### 5. S3 Deep-Dive

```json
{
  "create_bucket": {
    "status": "FAIL",
    "output": "make_bucket failed: s3://luckin-ops-dashboard-data An error occurred (AccessDenied) when calling the CreateBucket operation: User: arn:aws:iam::257394478466:user/databasecheck is not authorized to perform: s3:CreateBucket on resource: \"arn:aws:s3:::luckin-ops-dashboard-data\" because no identity-base"
  },
  "existing_buckets": [
    "2025-02-19 06:56:07 lk-infra-charts",
    "2025-02-19 03:09:13 lk-infra-data",
    "2025-05-19 03:14:13 lk-infra-dify",
    "2025-05-21 06:48:54 lk-infra-dify-data",
    "2025-05-27 08:13:01 lk-infra-dify-plugindaemon",
    "2025-01-16 06:03:59 lk-infra-readonly-us",
    "2025-02-10 06:47:22 lk-ops-emr-us",
    "2025-02-10 02:39:34 lk-tech-yw-sysop-kafkalog-region-us",
    "2025-02-21 15:18:15 lk-thanos-data",
    "2025-08-03 00:21:38 luckin-test-dynamic-image-frontenddistributiontos3-apxtken6onc0"
  ],
  "write_lk-infra-data": {
    "status": "FAIL",
    "error": "upload failed: ../tmp/tmpes5ca4od.json to s3://lk-infra-data/ops-dashboard/test.json An error occurred (AccessDenied) when calling the PutObject operation: User: arn:aws:iam::257394478466:user/databas"
  },
  "write_luckin-ops-dashboard-data": {
    "status": "FAIL",
    "error": "upload failed: ../tmp/tmpf0zeps4t.json to s3://luckin-ops-dashboard-data/ops-dashboard/test.json An error occurred (NoSuchBucket) when calling the PutObject operation: The specified bucket does not ex"
  }
}
```

### 6. SMTP Assessment

- Port 587: **BLOCKED**
- Port 465: **BLOCKED**
- Credentials: N/A
- SMTP Test: N/A
- **Recommendation:** SMTP ports 587/465 are BLOCKED. Use Gmail API over HTTPS (gmail.googleapis.com:443 is reachable) as alternative.

### 7. IMAP Assessment

- Port 993: **BLOCKED**
- **Recommendation:** IMAP port 993 is BLOCKED. Use Gmail API over HTTPS for reading emails.

### 8. Docker

```json
{
  "docker": {
    "status": "NOT AVAILABLE",
    "error": "[Errno 13] Permission denied: 'docker'"
  },
  "docker-compose-v1": {
    "status": "NOT AVAILABLE",
    "error": "[Errno 13] Permission denied: 'docker-compose'"
  },
  "docker-compose-v2": {
    "status": "NOT AVAILABLE",
    "error": "[Errno 13] Permission denied: 'docker'"
  },
  "docker_pull": {
    "status": "NOT AVAILABLE",
    "error": "[Errno 13] Permission denied: 'docker'"
  }
}
```

Docker Compose Test: NOT AVAILABLE — Docker is not installed on this system. To run Docker-based services, install Docker on the EC2 host

---

## RECOMMENDED DATA TRANSFER METHOD (推荐数据传输方式)

**GitHub Repository (API push)**

Push JSON data files to a GitHub repo via API. Vercel fetches from GitHub raw content. Simple but has rate limits (5000 req/hr authenticated).

---

## RECOMMENDED ARCHITECTURE (推荐架构方案)

```
EC2 Internal:
  - Python analytics → queries databases
  - Push JSON to GitHub repo via API (PAT token)
  - Cron schedule (every 5-15 min)

Transport: GitHub API → raw.githubusercontent.com

External (Vercel):
  - Dashboard reads from GitHub raw URLs
  - Or: Vercel automatically rebuilds on GitHub push (ISR)
```

---

## BLOCKERS OR CONCERNS (阻碍或风险)

- SMTP ports 587/465 are BLOCKED — `send_email.py` will not work from this container. Migrate to Gmail API over HTTPS or send emails from a different host.
- S3 endpoint is reachable but IAM user `databasecheck` lacks write permissions. Request s3:PutObject, s3:GetObject, s3:CreateBucket for a dedicated ops-dashboard bucket.
- Docker is NOT installed in this container. If Docker-based deployment is required, run directly on the EC2 host (not inside this sandbox).
- IMAP port 993 blocked — cannot read emails from this container. Use Gmail API over HTTPS instead.

---

## NEXT STEPS (下一步操作)

1. Request IAM policy update: add s3:PutObject, s3:GetObject, s3:CreateBucket to `databasecheck` user
2. Once S3 write is confirmed, proceed with S3-based architecture
3. Set up GitHub PAT for API-based data push (backup transport channel)
4. Set up GCP service account for Gmail API as fallback email delivery
5. Migrate send_email.py from smtplib to Gmail API (google-api-python-client)
6. Install Docker on EC2 host for container-based deployment

---

*Report generated by network-feasibility-audit.py on 2026-03-26 05:27 UTC*
