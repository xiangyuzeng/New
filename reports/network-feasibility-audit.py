#!/usr/bin/env python3
"""
Luckin Coffee Ops Dashboard — Network Feasibility Audit
Runs all connectivity tests and generates a markdown report.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

REPORT_PATH = "/app/reports/ops-dashboard-network-feasibility.md"
RESULTS = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def run_cmd(cmd, timeout=15):
    """Run a shell command, return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except FileNotFoundError:
        return -2, "", "COMMAND NOT FOUND"
    except Exception as e:
        return -3, "", str(e)


def test_dns(hostname):
    """Resolve hostname via socket.getaddrinfo + getent hosts."""
    result = {"hostname": hostname, "socket": None, "getent": None}
    # socket
    try:
        addrs = socket.getaddrinfo(hostname, None, socket.AF_INET)
        ips = sorted(set(a[4][0] for a in addrs))
        result["socket"] = {"status": "OK", "ips": ips}
    except Exception as e:
        result["socket"] = {"status": "FAIL", "error": str(e)}
    # getent
    rc, out, err = run_cmd(["getent", "hosts", hostname], timeout=5)
    if rc == 0 and out:
        result["getent"] = {"status": "OK", "output": out}
    else:
        result["getent"] = {"status": "FAIL", "error": err or "no result"}
    return result


def test_tcp(host, port, label, timeout=5):
    """Test TCP connectivity via socket.create_connection."""
    start = time.time()
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        elapsed = round((time.time() - start) * 1000, 1)
        # Try to read banner for SMTP
        banner = ""
        if port in (25, 587, 465, 993):
            try:
                s.settimeout(2)
                banner = s.recv(256).decode("utf-8", errors="replace").strip()
            except Exception:
                pass
        s.close()
        return {"label": label, "host": host, "port": port, "status": "OPEN",
                "latency_ms": elapsed, "banner": banner}
    except Exception as e:
        elapsed = round((time.time() - start) * 1000, 1)
        return {"label": label, "host": host, "port": port, "status": "BLOCKED",
                "latency_ms": elapsed, "error": str(e)}


def test_https(url, label, timeout=5):
    """Test HTTPS endpoint with curl."""
    rc, out, err = run_cmd([
        "curl", "-s", "--connect-timeout", str(timeout),
        "-o", "/dev/null", "-w", "%{http_code}|%{time_total}|%{ssl_verify_result}",
        url
    ], timeout=timeout + 3)
    if rc == 0 and out:
        parts = out.split("|")
        code = parts[0] if parts else "000"
        t = parts[1] if len(parts) > 1 else "?"
        ssl = parts[2] if len(parts) > 2 else "?"
        return {"label": label, "url": url,
                "status": "OK" if code != "000" else "FAIL",
                "http_code": code, "time_s": t,
                "ssl_verify": "OK" if ssl == "0" else f"FAIL({ssl})"}
    return {"label": label, "url": url, "status": "FAIL", "error": err[:200]}


# ── Task 1: Network Connectivity Audit ───────────────────────────────────────

def task1_dns():
    print("\n[Task 1a] DNS Resolution Tests")
    hosts = [
        "smtp.gmail.com", "imap.gmail.com",
        "s3.us-east-1.amazonaws.com", "sts.us-east-1.amazonaws.com",
        "api.github.com", "hooks.slack.com",
        "gmail.googleapis.com", "oauth2.googleapis.com",
    ]
    results = []
    for h in hosts:
        r = test_dns(h)
        status = r["socket"]["status"]
        ips = r["socket"].get("ips", [])
        print(f"  {h:40s} {status}  {', '.join(ips) if ips else r['socket'].get('error','')}")
        results.append(r)
    return results


def task1_tcp():
    print("\n[Task 1b] TCP Port Connectivity Tests")
    targets = [
        ("smtp.gmail.com", 587, "SMTP TLS (STARTTLS)"),
        ("smtp.gmail.com", 465, "SMTP SSL"),
        ("smtp.gmail.com", 25,  "SMTP Plain"),
        ("imap.gmail.com", 993, "IMAP SSL"),
        ("s3.us-east-1.amazonaws.com", 443, "AWS S3 HTTPS"),
        ("sts.us-east-1.amazonaws.com", 443, "AWS STS HTTPS"),
        ("api.github.com", 443, "GitHub API HTTPS"),
        ("hooks.slack.com", 443, "Slack Webhook HTTPS"),
        ("gmail.googleapis.com", 443, "Gmail API HTTPS"),
        ("oauth2.googleapis.com", 443, "Google OAuth HTTPS"),
    ]
    results = []
    for host, port, label in targets:
        r = test_tcp(host, port, label)
        icon = "OPEN" if r["status"] == "OPEN" else "BLOCKED"
        detail = f"{r['latency_ms']}ms" if r["status"] == "OPEN" else r.get("error", "")[:60]
        print(f"  {label:30s} {host}:{port:5d}  {icon:8s} {detail}")
        results.append(r)
    return results


def task1_https():
    print("\n[Task 1c] HTTPS Endpoint Tests")
    endpoints = [
        ("https://s3.amazonaws.com", "S3 Global"),
        ("https://sts.amazonaws.com", "STS Global"),
        ("https://api.github.com", "GitHub API"),
        ("https://gmail.googleapis.com", "Gmail REST API"),
        ("https://www.googleapis.com", "Google APIs"),
        ("https://hooks.slack.com", "Slack Webhooks"),
    ]
    results = []
    for url, label in endpoints:
        r = test_https(url, label)
        print(f"  {label:20s} HTTP {r.get('http_code','???'):4s}  {r['status']}  {r.get('time_s','?')}s")
        results.append(r)
    return results


def task1_aws():
    print("\n[Task 1d] AWS CLI Tests")
    results = {}

    # version
    rc, out, err = run_cmd(["aws", "--version"])
    results["version"] = out or err
    print(f"  AWS CLI: {results['version']}")

    # identity
    rc, out, err = run_cmd(["aws", "sts", "get-caller-identity", "--region", "us-east-1"])
    if rc == 0:
        identity = json.loads(out)
        results["identity"] = {"status": "OK", "data": identity}
        print(f"  Identity: {identity.get('Arn', '?')}")
    else:
        results["identity"] = {"status": "FAIL", "error": (err or out)[:200]}
        print(f"  Identity: FAIL — {(err or out)[:100]}")

    # s3 ls
    rc, out, err = run_cmd(["aws", "s3", "ls", "--region", "us-east-1"])
    if rc == 0:
        buckets = out.strip().split("\n")[:5]
        results["s3_ls"] = {"status": "OK", "sample": buckets}
        print(f"  S3 ls: OK ({len(out.strip().split(chr(10)))} buckets visible)")
    else:
        results["s3_ls"] = {"status": "FAIL", "error": (err or out)[:200]}
        print(f"  S3 ls: FAIL — {(err or out)[:100]}")

    # s3 cp dryrun
    rc, out, err = run_cmd([
        "aws", "s3", "cp", "--dryrun", "/dev/null",
        "s3://luckin-ops-test/probe.txt", "--region", "us-east-1"
    ])
    results["s3_dryrun"] = {"status": "OK" if rc == 0 else "FAIL",
                            "output": (out or err)[:200]}
    print(f"  S3 dryrun: {'OK' if rc == 0 else 'FAIL'} — {(out or err)[:80]}")

    # disk space
    rc, out, err = run_cmd(["df", "-h", "/"])
    results["disk"] = out
    if out:
        lines = out.split("\n")
        if len(lines) >= 2:
            print(f"  Disk: {lines[1]}")

    return results


def task1_docker():
    print("\n[Task 1e] Docker Availability")
    results = {}
    for cmd_name, cmd_args in [("docker", ["docker", "--version"]),
                                ("docker-compose-v1", ["docker-compose", "--version"]),
                                ("docker-compose-v2", ["docker", "compose", "version"])]:
        rc, out, err = run_cmd(cmd_args, timeout=5)
        if rc == 0:
            results[cmd_name] = {"status": "OK", "version": out}
            print(f"  {cmd_name}: {out}")
        else:
            results[cmd_name] = {"status": "NOT AVAILABLE", "error": (err or "command not found")[:100]}
            print(f"  {cmd_name}: NOT AVAILABLE")

    # docker pull test
    rc, out, err = run_cmd(["docker", "pull", "hello-world"], timeout=30)
    if rc == 0:
        results["docker_pull"] = {"status": "OK"}
        print(f"  Docker pull: OK")
    else:
        results["docker_pull"] = {"status": "NOT AVAILABLE", "error": (err or "docker not found")[:100]}
        print(f"  Docker pull: NOT AVAILABLE")

    return results


# ── Task 2: S3 Deep-Dive ─────────────────────────────────────────────────────

def task2_s3_deep_dive():
    print("\n[Task 2] S3 Feasibility Deep-Dive")
    results = {}
    bucket = "luckin-ops-dashboard-data"

    # Try to create bucket
    print(f"  Creating test bucket: {bucket}")
    rc, out, err = run_cmd([
        "aws", "s3", "mb", f"s3://{bucket}", "--region", "us-east-1"
    ], timeout=15)
    results["create_bucket"] = {"status": "OK" if rc == 0 else "FAIL",
                                 "output": (out or err)[:300]}
    print(f"  Create bucket: {'OK' if rc == 0 else 'FAIL'} — {(out or err)[:100]}")

    if rc != 0:
        # Try listing existing buckets to find one we can use
        print("  Bucket creation failed. Checking existing buckets...")
        rc2, out2, err2 = run_cmd(["aws", "s3", "ls", "--region", "us-east-1"])
        if rc2 == 0:
            lines = [l for l in out2.split("\n") if "luckin" in l.lower() or "ops" in l.lower() or "lk-" in l.lower()]
            results["existing_buckets"] = [l.strip() for l in lines[:10]]
            print(f"  Relevant existing buckets: {len(lines)}")
            for l in lines[:5]:
                print(f"    {l.strip()}")

        # Try writing to lk-infra-data if it exists
        for test_bucket in ["lk-infra-data", "luckin-ops-dashboard-data"]:
            test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            test_data = json.dumps({
                "test": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "network-feasibility-audit"
            }, indent=2)
            test_file.write(test_data)
            test_file.close()

            print(f"  Testing write to s3://{test_bucket}/ops-dashboard/test.json")
            rc3, out3, err3 = run_cmd([
                "aws", "s3", "cp", test_file.name,
                f"s3://{test_bucket}/ops-dashboard/test.json",
                "--region", "us-east-1"
            ], timeout=15)
            os.unlink(test_file.name)

            if rc3 == 0:
                results["write_test"] = {"status": "OK", "bucket": test_bucket,
                                          "output": out3[:200]}
                print(f"  Write: OK to {test_bucket}")

                # Presigned URL
                rc4, out4, err4 = run_cmd([
                    "aws", "s3", "presign",
                    f"s3://{test_bucket}/ops-dashboard/test.json",
                    "--expires-in", "3600", "--region", "us-east-1"
                ])
                if rc4 == 0 and out4:
                    results["presign"] = {"status": "OK", "url_prefix": out4[:80] + "..."}
                    print(f"  Presigned URL: OK")

                    # Test access
                    rc5, out5, err5 = run_cmd([
                        "curl", "-s", "--connect-timeout", "5",
                        "-o", "/dev/null", "-w", "%{http_code}", out4
                    ])
                    results["presign_access"] = {"status": "OK" if out5 == "200" else "FAIL",
                                                  "http_code": out5}
                    print(f"  Presigned URL access: HTTP {out5}")
                else:
                    results["presign"] = {"status": "FAIL", "error": (err4 or out4)[:200]}
                    print(f"  Presigned URL: FAIL — {(err4 or out4)[:80]}")

                # Cleanup
                run_cmd(["aws", "s3", "rm",
                         f"s3://{test_bucket}/ops-dashboard/test.json",
                         "--region", "us-east-1"])
                results["cleanup"] = "test object removed"
                break
            else:
                results[f"write_{test_bucket}"] = {"status": "FAIL",
                                                    "error": (err3 or out3)[:200]}
                print(f"  Write to {test_bucket}: FAIL — {(err3 or out3)[:80]}")
    else:
        # Bucket created successfully — run full test suite
        test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        test_data = json.dumps({
            "test": True, "timestamp": datetime.now(timezone.utc).isoformat()
        }, indent=2)
        test_file.write(test_data)
        test_file.close()

        # Write
        rc, out, err = run_cmd([
            "aws", "s3", "cp", test_file.name,
            f"s3://{bucket}/test-data.json", "--region", "us-east-1"
        ])
        os.unlink(test_file.name)
        results["write"] = {"status": "OK" if rc == 0 else "FAIL",
                             "output": (out or err)[:200]}
        print(f"  Write: {'OK' if rc == 0 else 'FAIL'}")

        if rc == 0:
            # Presigned URL
            rc, out, err = run_cmd([
                "aws", "s3", "presign", f"s3://{bucket}/test-data.json",
                "--expires-in", "3600", "--region", "us-east-1"
            ])
            if rc == 0 and out:
                results["presign"] = {"status": "OK", "url_prefix": out[:80] + "..."}
                print(f"  Presigned URL: OK")

                # Access test
                rc2, out2, _ = run_cmd([
                    "curl", "-s", "--connect-timeout", "5",
                    "-o", "/dev/null", "-w", "%{http_code}", out
                ])
                results["presign_access"] = {"status": "OK" if out2 == "200" else "FAIL",
                                              "http_code": out2}
                print(f"  Presigned URL access: HTTP {out2}")

        # Cleanup
        run_cmd(["aws", "s3", "rm", f"s3://{bucket}/test-data.json", "--region", "us-east-1"])
        run_cmd(["aws", "s3", "rb", f"s3://{bucket}", "--region", "us-east-1"])
        results["cleanup"] = "test bucket and object removed"
        print("  Cleanup: done")

    return results


# ── Task 3 & 4: SMTP/IMAP Assessment ─────────────────────────────────────────

def task3_smtp_assessment(tcp_results):
    print("\n[Task 3] SMTP Send Assessment")
    smtp_587 = next((r for r in tcp_results if r["port"] == 587), None)
    smtp_465 = next((r for r in tcp_results if r["port"] == 465), None)

    results = {
        "port_587": smtp_587["status"] if smtp_587 else "UNTESTED",
        "port_465": smtp_465["status"] if smtp_465 else "UNTESTED",
    }

    if smtp_587 and smtp_587["status"] == "OPEN":
        results["recommendation"] = "SMTP port 587 is OPEN. Direct SMTP is feasible."
        print("  Port 587: OPEN — Direct SMTP is feasible")
        # Check for credentials
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_pass = os.environ.get("SMTP_PASSWORD", "")
        if smtp_user and smtp_pass:
            print("  SMTP credentials found in environment. Running send test...")
            results["credentials"] = "AVAILABLE"
            # Run actual send test
            try:
                import smtplib
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    results["smtp_test"] = "LOGIN OK"
                    print("  SMTP login: OK")
            except Exception as e:
                results["smtp_test"] = f"FAIL: {e}"
                print(f"  SMTP login: FAIL — {e}")
        else:
            results["credentials"] = "NOT SET (need SMTP_USER and SMTP_PASSWORD env vars)"
            print("  SMTP credentials: NOT SET")
    else:
        err587 = smtp_587.get("error", "") if smtp_587 else ""
        err465 = smtp_465.get("error", "") if smtp_465 else ""
        results["recommendation"] = (
            "SMTP ports 587/465 are BLOCKED. Use Gmail API over HTTPS "
            "(gmail.googleapis.com:443 is reachable) as alternative."
        )
        results["errors"] = {"587": err587, "465": err465}
        print(f"  Port 587: BLOCKED — {err587[:60]}")
        print(f"  Port 465: BLOCKED — {err465[:60]}")
        print("  Recommendation: Use Gmail API over HTTPS instead")

    return results


def task4_imap_assessment(tcp_results):
    print("\n[Task 4] IMAP Read Assessment")
    imap_993 = next((r for r in tcp_results if r["port"] == 993), None)

    results = {
        "port_993": imap_993["status"] if imap_993 else "UNTESTED",
    }

    if imap_993 and imap_993["status"] == "OPEN":
        results["recommendation"] = "IMAP port 993 is OPEN. Direct IMAP read is feasible."
        print("  Port 993: OPEN — Direct IMAP is feasible")
    else:
        err = imap_993.get("error", "") if imap_993 else ""
        results["recommendation"] = (
            "IMAP port 993 is BLOCKED. Use Gmail API over HTTPS for reading emails."
        )
        results["error"] = err
        print(f"  Port 993: BLOCKED — {err[:60]}")
        print("  Recommendation: Use Gmail API over HTTPS for email read")

    return results


# ── Task 5: Docker Compose Feasibility ────────────────────────────────────────

def task5_docker_compose(docker_results):
    print("\n[Task 5] Docker Compose Feasibility")
    docker_ok = docker_results.get("docker", {}).get("status") == "OK"

    if docker_ok:
        print("  Docker available — creating minimal compose test...")
        compose_yml = """version: '3.8'
services:
  node-app:
    image: node:20-slim
    command: ["node", "-e", "console.log('node-app ready')"]
  py-analytics:
    image: python:3.11-slim
    command: ["python3", "-c", "print('py-analytics ready')"]
  py-sender:
    image: python:3.11-slim
    command: ["python3", "-c", "print('py-sender ready')"]
"""
        compose_path = "/tmp/docker-compose-test.yml"
        with open(compose_path, "w") as f:
            f.write(compose_yml)

        rc, out, err = run_cmd(["docker", "compose", "-f", compose_path, "up", "--build"], timeout=120)
        if rc != 0:
            rc, out, err = run_cmd(["docker-compose", "-f", compose_path, "up", "--build"], timeout=120)

        result = {"status": "OK" if rc == 0 else "FAIL", "output": (out or err)[:500]}
        # Cleanup
        run_cmd(["docker", "compose", "-f", compose_path, "down"], timeout=15)
        run_cmd(["docker-compose", "-f", compose_path, "down"], timeout=15)
        os.unlink(compose_path)
        print(f"  Docker Compose up: {'OK' if rc == 0 else 'FAIL'}")
        return result
    else:
        print("  Docker NOT available — compose test skipped")
        return {"status": "NOT AVAILABLE",
                "note": "Docker is not installed on this system. "
                        "To run Docker-based services, install Docker on the EC2 host."}


# ── Report Generation ─────────────────────────────────────────────────────────

def generate_report(dns, tcp, https, aws_cli, docker, s3, smtp, imap, docker_compose):
    """Generate the markdown report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    identity = aws_cli.get("identity", {}).get("data", {})
    account = identity.get("Account", "unknown")
    arn = identity.get("Arn", "unknown")
    region = "us-east-1"

    # Helper to get status
    def tcp_status(port):
        r = next((t for t in tcp if t["port"] == port), None)
        return r if r else {"status": "UNTESTED", "error": "not tested"}

    def https_status(label):
        r = next((h for h in https if h["label"] == label), None)
        return r if r else {"status": "FAIL", "error": "not tested"}

    smtp587 = tcp_status(587)
    smtp465 = tcp_status(465)
    imap993 = tcp_status(993)
    s3_https = https_status("S3 Global")
    sts_https = https_status("STS Global")
    github_https = https_status("GitHub API")
    gmail_https = https_status("Gmail REST API")
    google_https = https_status("Google APIs")
    slack_https = https_status("Slack Webhooks")

    s3_write = s3.get("write_test", s3.get("write", {}))
    s3_presign = s3.get("presign", {})
    docker_ver = docker.get("docker", {})
    compose_ver = docker.get("docker-compose-v2", docker.get("docker-compose-v1", {}))
    docker_pull = docker.get("docker_pull", {})

    # Determine DNS status
    dns_all_ok = all(d["socket"]["status"] == "OK" for d in dns)

    # Disk info
    disk_info = aws_cli.get("disk", "unknown")
    disk_lines = disk_info.split("\n")
    disk_detail = disk_lines[1] if len(disk_lines) >= 2 else disk_info

    def status_str(s):
        return "OK" if s.get("status") in ("OK", "OPEN") else "FAIL"

    def detail_str(r, fallback=""):
        if r.get("status") in ("OK", "OPEN"):
            if "http_code" in r:
                return f"HTTP {r['http_code']}, {r.get('time_s', '?')}s"
            if "latency_ms" in r:
                b = r.get("banner", "")
                return f"{r['latency_ms']}ms" + (f" — {b[:40]}" if b else "")
            if "version" in r:
                return r["version"]
            if "output" in r:
                return str(r["output"])[:60]
            return "connected"
        return r.get("error", fallback)[:60]

    # Build summary table rows
    rows = [
        ("SMTP Gmail (587)", status_str(smtp587), detail_str(smtp587, "port blocked")),
        ("SMTP Gmail (465)", status_str(smtp465), detail_str(smtp465, "port blocked")),
        ("S3 Access", status_str(s3_https), detail_str(s3_https)),
        ("S3 Write", status_str(s3_write) if s3_write else "FAIL",
         detail_str(s3_write) if s3_write else "not tested or permission denied"),
        ("S3 Presigned URL", status_str(s3_presign) if s3_presign else "FAIL",
         detail_str(s3_presign) if s3_presign else "not tested"),
        ("GitHub API", status_str(github_https), detail_str(github_https)),
        ("Gmail IMAP (993)", status_str(imap993), detail_str(imap993, "port blocked")),
        ("Gmail REST API", status_str(gmail_https), detail_str(gmail_https)),
        ("Google APIs", status_str(google_https), detail_str(google_https)),
        ("Slack Webhook", status_str(slack_https), detail_str(slack_https)),
        ("Docker", status_str(docker_ver), detail_str(docker_ver, "not installed")),
        ("Docker Compose", status_str(compose_ver), detail_str(compose_ver, "not installed")),
        ("Docker Hub Pull", status_str(docker_pull), detail_str(docker_pull, "not available")),
        ("Docker Compose Up", docker_compose.get("status", "FAIL") if docker_compose.get("status") == "OK" else "FAIL",
         docker_compose.get("note", docker_compose.get("output", "not available"))[:60]),
        ("AWS CLI", "OK" if aws_cli.get("identity", {}).get("status") == "OK" else "FAIL",
         f"{aws_cli.get('version', '?')[:40]}, {arn}"),
        ("DNS Resolution", "OK" if dns_all_ok else "FAIL",
         f"{'all' if dns_all_ok else 'some'} of {len(dns)} hosts resolved"),
        ("Disk Space", "OK", disk_detail[:60]),
    ]

    table_lines = []
    for name, status, detail in rows:
        table_lines.append(f"| {name:24s}| {status:8s}| {detail:50s}|")

    # Determine recommendations
    s3_ok = s3_https.get("status") == "OK" and s3_write and s3_write.get("status") == "OK"
    smtp_ok = smtp587.get("status") == "OPEN"
    github_ok = github_https.get("status") == "OK"
    gmail_api_ok = gmail_https.get("status") == "OK"
    slack_ok = slack_https.get("status") == "OK"

    # Primary recommendation
    if s3_ok:
        primary = ("AWS S3 + Presigned URLs",
                   "S3 is the most reliable and scalable option. Internal containers write JSON data "
                   "to S3, the Vercel dashboard fetches via presigned URLs or public bucket prefix. "
                   "No credential sharing needed — presigned URLs are self-authenticating.")
    elif github_ok:
        primary = ("GitHub Repository (API push)",
                   "Push JSON data files to a GitHub repo via API. Vercel fetches from GitHub raw content. "
                   "Simple but has rate limits (5000 req/hr authenticated).")
    elif gmail_api_ok:
        primary = ("Gmail API over HTTPS",
                   "Use Gmail API (not SMTP) to send data as email attachments. "
                   "External system reads via Gmail API. Works but adds latency and complexity.")
    else:
        primary = ("NONE — all outbound channels blocked",
                   "No viable data transfer method detected. Escalate to network team.")

    # Architecture
    if s3_ok:
        arch = """EC2 Internal (this machine):
  - Python analytics container → queries MySQL/Redis/Prometheus via MCP
  - Python data-sender → writes JSON to S3 bucket (every N minutes)
  - Cron/scheduler → triggers data refresh cycle

Transport Layer:
  - AWS S3 bucket with CORS enabled for Vercel domain
  - Presigned URLs (auto-expiring, secure) OR public-read prefix
  - Data format: JSON files at s3://bucket/dashboard-data/{metric}.json

External (Vercel):
  - Next.js dashboard fetches S3 presigned URLs via API routes
  - 30-second polling or webhook-triggered refresh
  - No AWS credentials needed on Vercel side (presigned URLs are self-auth)"""
    elif github_ok:
        arch = """EC2 Internal:
  - Python analytics → queries databases
  - Push JSON to GitHub repo via API (PAT token)
  - Cron schedule (every 5-15 min)

Transport: GitHub API → raw.githubusercontent.com

External (Vercel):
  - Dashboard reads from GitHub raw URLs
  - Or: Vercel automatically rebuilds on GitHub push (ISR)"""
    else:
        arch = "No confirmed transport channel. Investigate network firewall rules."

    # Blockers
    blockers = []
    if not smtp_ok:
        blockers.append("SMTP ports 587/465 are BLOCKED — `send_email.py` will not work from this container. "
                        "Migrate to Gmail API over HTTPS or send emails from a different host.")
    if not s3_ok and s3_https.get("status") == "OK":
        blockers.append("S3 endpoint is reachable but IAM user `databasecheck` lacks write permissions. "
                        "Request s3:PutObject, s3:GetObject, s3:CreateBucket for a dedicated ops-dashboard bucket.")
    if docker_ver.get("status") != "OK":
        blockers.append("Docker is NOT installed in this container. If Docker-based deployment is required, "
                        "run directly on the EC2 host (not inside this sandbox).")
    if imap993.get("status") != "OPEN":
        blockers.append("IMAP port 993 blocked — cannot read emails from this container. "
                        "Use Gmail API over HTTPS instead.")
    if not blockers:
        blockers.append("No critical blockers detected.")

    # Next steps
    next_steps = []
    if s3_ok:
        next_steps.extend([
            "Create dedicated S3 bucket `luckin-ops-dashboard-data` with lifecycle policy",
            "Configure CORS for Vercel domain on the bucket",
            "Build Python data-sender service that writes dashboard JSON to S3",
            "Update Vercel dashboard to fetch from S3 presigned URLs",
        ])
    elif s3_https.get("status") == "OK":
        next_steps.extend([
            "Request IAM policy update: add s3:PutObject, s3:GetObject, s3:CreateBucket to `databasecheck` user",
            "Once S3 write is confirmed, proceed with S3-based architecture",
        ])
    if github_ok:
        next_steps.append("Set up GitHub PAT for API-based data push (backup transport channel)")
    if gmail_api_ok:
        next_steps.append("Set up GCP service account for Gmail API as fallback email delivery")
    if not smtp_ok:
        next_steps.append("Migrate send_email.py from smtplib to Gmail API (google-api-python-client)")
    if docker_ver.get("status") != "OK":
        next_steps.append("Install Docker on EC2 host for container-based deployment")

    # DNS detail table
    dns_table = []
    for d in dns:
        ips = ", ".join(d["socket"].get("ips", [])) if d["socket"]["status"] == "OK" else d["socket"].get("error", "?")
        dns_table.append(f"| {d['hostname']:40s}| {d['socket']['status']:6s}| {ips[:40]:40s}|")

    # TCP detail table
    tcp_table = []
    for t in tcp:
        detail = f"{t['latency_ms']}ms" if t["status"] == "OPEN" else t.get("error", "?")[:40]
        tcp_table.append(f"| {t['label']:30s}| {t['host']}:{t['port']:<5d} | {t['status']:8s}| {detail:40s}|")

    # HTTPS detail table
    https_table = []
    for h in https:
        code = h.get("http_code", "?")
        t = h.get("time_s", "?")
        ssl = h.get("ssl_verify", "?")
        https_table.append(f"| {h['label']:20s}| {h['url']:45s}| {code:5s}| {t:8s}| {ssl:12s}|")

    report = f"""# LUCKIN OPS DASHBOARD — NETWORK FEASIBILITY REPORT
# 瑞幸运营看板 — 网络连通性检测报告

| Field | Value |
|-------|-------|
| **Date** | {now} |
| **EC2 Account** | {account} |
| **IAM User** | {arn} |
| **Region** | {region} |
| **Hostname** | {socket.gethostname()} |
| **Python** | {sys.version.split()[0]} |
| **AWS CLI** | {aws_cli.get('version', '?')[:60]} |

---

## Summary Table

| Test                    | Result  | Details                                            |
|-------------------------|---------|----------------------------------------------------|
{chr(10).join(table_lines)}

---

## Detailed Results

### 1. DNS Resolution

| Hostname                                | Status | IPs                                      |
|-----------------------------------------|--------|------------------------------------------|
{chr(10).join(dns_table)}

### 2. TCP Port Connectivity

| Service                       | Target             | Status  | Details                                  |
|-------------------------------|--------------------|---------|------------------------------------------|
{chr(10).join(tcp_table)}

### 3. HTTPS Endpoints

| Service             | URL                                          | HTTP | Time    | SSL         |
|---------------------|----------------------------------------------|------|---------|-------------|
{chr(10).join(https_table)}

### 4. AWS CLI

- **Version:** {aws_cli.get('version', '?')}
- **Identity:** {json.dumps(identity, indent=2) if identity else 'FAILED'}
- **S3 List:** {aws_cli.get('s3_ls', {}).get('status', '?')} — {len(aws_cli.get('s3_ls', {}).get('sample', []))} buckets visible
- **S3 Dryrun:** {aws_cli.get('s3_dryrun', {}).get('status', '?')} — {aws_cli.get('s3_dryrun', {}).get('output', '?')[:100]}
- **Disk:** {disk_detail}

### 5. S3 Deep-Dive

```json
{json.dumps(s3, indent=2, default=str)}
```

### 6. SMTP Assessment

- Port 587: **{smtp.get('port_587', '?')}**
- Port 465: **{smtp.get('port_465', '?')}**
- Credentials: {smtp.get('credentials', 'N/A')}
- SMTP Test: {smtp.get('smtp_test', 'N/A')}
- **Recommendation:** {smtp.get('recommendation', 'N/A')}

### 7. IMAP Assessment

- Port 993: **{imap.get('port_993', '?')}**
- **Recommendation:** {imap.get('recommendation', 'N/A')}

### 8. Docker

```json
{json.dumps(docker, indent=2, default=str)}
```

Docker Compose Test: {docker_compose.get('status', '?')} — {docker_compose.get('note', docker_compose.get('output', '?'))[:100]}

---

## RECOMMENDED DATA TRANSFER METHOD (推荐数据传输方式)

**{primary[0]}**

{primary[1]}

---

## RECOMMENDED ARCHITECTURE (推荐架构方案)

```
{arch}
```

---

## BLOCKERS OR CONCERNS (阻碍或风险)

{chr(10).join(f"- {b}" for b in blockers)}

---

## NEXT STEPS (下一步操作)

{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(next_steps))}

---

*Report generated by network-feasibility-audit.py on {now}*
"""
    return report


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  LUCKIN OPS DASHBOARD — NETWORK FEASIBILITY AUDIT")
    print("  瑞幸运营看板 — 网络连通性检测")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Task 1
    dns = task1_dns()
    tcp = task1_tcp()
    https_results = task1_https()
    aws_cli = task1_aws()
    docker = task1_docker()

    # Task 2
    s3 = task2_s3_deep_dive()

    # Task 3 & 4
    smtp = task3_smtp_assessment(tcp)
    imap = task4_imap_assessment(tcp)

    # Task 5
    docker_compose = task5_docker_compose(docker)

    # Generate report
    print("\n" + "=" * 70)
    print("  Generating report...")
    report = generate_report(dns, tcp, https_results, aws_cli, docker, s3, smtp, imap, docker_compose)

    with open(REPORT_PATH, "w") as f:
        f.write(report)
    print(f"  Report saved to: {REPORT_PATH}")

    # Also save raw JSON
    raw = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dns": dns, "tcp": tcp, "https": https_results,
        "aws_cli": aws_cli, "docker": docker, "s3": s3,
        "smtp": smtp, "imap": imap, "docker_compose": docker_compose,
    }
    json_path = REPORT_PATH.replace(".md", ".json")
    with open(json_path, "w") as f:
        json.dump(raw, f, indent=2, default=str)
    print(f"  Raw JSON saved to: {json_path}")

    print("\n" + "=" * 70)
    print("  AUDIT COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
