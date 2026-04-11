#!/bin/bash
###############################################################################
# Phase A: MySQL 8.0.40/41 → 8.0.45 Minor Version Upgrade Script
# Generated: 2026-04-11
# Operator: David Zeng (DBA), Luckin Coffee North America
# Account: 257394478466 | Region: us-east-1
# Target: 8.0.45
#
# USAGE:
#   chmod +x phase-a-upgrade.sh
#   ./phase-a-upgrade.sh [batch_number]
#   Examples:
#     ./phase-a-upgrade.sh 1    # Run Batch 1 only (pilot)
#     ./phase-a-upgrade.sh 2    # Run Batch 2 only
#     ./phase-a-upgrade.sh all  # Run all batches sequentially (with prompts)
#
# PREREQUISITES:
#   - AWS CLI configured with a user/role that has rds:ModifyDBInstance
#   - Recommended: export AWS_PROFILE=<write-capable-profile>
###############################################################################

set -euo pipefail

TARGET_VERSION="8.0.45"
REGION="us-east-1"
LOGFILE="/home/claude/phase-a/execution.log"
WORKDIR="/home/claude/phase-a"
MAX_FAILURES_PER_BATCH=2
WAIT_TIMEOUT=1800  # 30 minutes

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    local msg="[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $1"
    echo "$msg" >> "$LOGFILE"
    echo -e "$msg"
}

log_error() {
    local msg="[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: $1"
    echo "$msg" >> "$LOGFILE"
    echo -e "${RED}${msg}${NC}"
}

log_success() {
    local msg="[$(date -u +%Y-%m-%dT%H:%M:%SZ)] SUCCESS: $1"
    echo "$msg" >> "$LOGFILE"
    echo -e "${GREEN}${msg}${NC}"
}

log_warn() {
    local msg="[$(date -u +%Y-%m-%dT%H:%M:%SZ)] WARN: $1"
    echo "$msg" >> "$LOGFILE"
    echo -e "${YELLOW}${msg}${NC}"
}

###############################################################################
# Pre-check: verify instance is ready for upgrade
###############################################################################
precheck_instance() {
    local INST_ID="$1"
    local EXPECTED_VER="$2"

    log "PRE-CHECK: $INST_ID (expecting $EXPECTED_VER)"

    local INFO
    INFO=$(aws rds describe-db-instances --db-instance-identifier "$INST_ID" --region "$REGION" \
        --query 'DBInstances[0].{ver:EngineVersion,status:DBInstanceStatus,pg:DBParameterGroups[0].DBParameterGroupName,ps:DBParameterGroups[0].ParameterApplyStatus,pending:PendingModifiedValues}' \
        --output json 2>&1)

    if [ $? -ne 0 ]; then
        log_error "PRE-CHECK FAILED: Cannot describe $INST_ID: $INFO"
        return 1
    fi

    local VER=$(echo "$INFO" | python3 -c "import json,sys; print(json.load(sys.stdin)['ver'])")
    local STATUS=$(echo "$INFO" | python3 -c "import json,sys; print(json.load(sys.stdin)['status'])")
    local PG=$(echo "$INFO" | python3 -c "import json,sys; print(json.load(sys.stdin)['pg'])")
    local PS=$(echo "$INFO" | python3 -c "import json,sys; print(json.load(sys.stdin)['ps'])")
    local PENDING=$(echo "$INFO" | python3 -c "import json,sys; p=json.load(sys.stdin)['pending']; print('NONE' if not p else str(p))")

    if [ "$VER" != "$EXPECTED_VER" ]; then
        if [ "$VER" == "$TARGET_VERSION" ]; then
            log_warn "PRE-CHECK: $INST_ID already on $TARGET_VERSION — SKIPPING"
            return 2  # Already upgraded
        fi
        log_error "PRE-CHECK FAILED: $INST_ID version=$VER (expected $EXPECTED_VER)"
        return 1
    fi
    if [ "$STATUS" != "available" ]; then
        log_error "PRE-CHECK FAILED: $INST_ID status=$STATUS (expected available)"
        return 1
    fi
    if [ "$PS" != "in-sync" ]; then
        log_error "PRE-CHECK FAILED: $INST_ID param_status=$PS (expected in-sync)"
        return 1
    fi
    if [ "$PENDING" != "NONE" ]; then
        log_error "PRE-CHECK FAILED: $INST_ID has pending modifications: $PENDING"
        return 1
    fi

    # Check current FreeableMemory
    local FM
    FM=$(aws cloudwatch get-metric-statistics --namespace AWS/RDS \
        --metric-name FreeableMemory \
        --dimensions Name=DBInstanceIdentifier,Value="$INST_ID" \
        --start-time "$(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%SZ)" \
        --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --period 300 --statistics Minimum --region "$REGION" \
        --query 'Datapoints[0].Minimum' --output text 2>/dev/null || echo "N/A")

    if [ "$FM" != "N/A" ] && [ "$FM" != "None" ]; then
        local FM_MB=$(python3 -c "print(round(float('$FM')/(1024*1024),1))")
        if (( $(echo "$FM_MB < 100" | bc -l) )); then
            log_warn "PRE-CHECK: $INST_ID FreeableMemory=${FM_MB}MB < 100MB — HIGH OOM RISK"
            echo -e "${RED}WARNING: $INST_ID has only ${FM_MB}MB free memory.${NC}"
            read -p "Continue with this instance? (yes/no): " CONFIRM
            if [ "$CONFIRM" != "yes" ]; then
                log "PRE-CHECK: $INST_ID skipped by operator (low memory)"
                return 3  # Skipped by operator
            fi
        fi
        log "PRE-CHECK PASS: $INST_ID | ver=$VER | status=$STATUS | pg=$PG | ps=$PS | FreeMem=${FM_MB}MB"
    else
        log "PRE-CHECK PASS: $INST_ID | ver=$VER | status=$STATUS | pg=$PG | ps=$PS | FreeMem=N/A"
    fi

    # Store param group for post-upgrade verification
    echo "$PG" > "$WORKDIR/.pg_${INST_ID}"
    return 0
}

###############################################################################
# Upgrade: execute the modify-db-instance command
###############################################################################
upgrade_instance() {
    local INST_ID="$1"
    local EXPECTED_VER="$2"
    local START_TS=$(date +%s)

    log "START: $INST_ID $EXPECTED_VER -> $TARGET_VERSION"

    # Execute upgrade
    local RESULT
    RESULT=$(aws rds modify-db-instance \
        --db-instance-identifier "$INST_ID" \
        --engine-version "$TARGET_VERSION" \
        --apply-immediately \
        --region "$REGION" \
        --output json 2>&1)

    if [ $? -ne 0 ]; then
        log_error "MODIFY FAILED: $INST_ID: $RESULT"
        return 1
    fi

    log "MODIFY SUBMITTED: $INST_ID — waiting for available..."

    # Wait for instance to become available
    aws rds wait db-instance-available \
        --db-instance-identifier "$INST_ID" \
        --region "$REGION" 2>&1

    if [ $? -ne 0 ]; then
        log_error "WAIT TIMEOUT: $INST_ID did not become available within timeout"
        return 1
    fi

    local END_TS=$(date +%s)
    local DURATION=$((END_TS - START_TS))

    # Verify upgrade
    local POST_INFO
    POST_INFO=$(aws rds describe-db-instances --db-instance-identifier "$INST_ID" --region "$REGION" \
        --query 'DBInstances[0].{ver:EngineVersion,status:DBInstanceStatus,pg:DBParameterGroups[0].DBParameterGroupName,ps:DBParameterGroups[0].ParameterApplyStatus}' \
        --output json 2>&1)

    local NEW_VER=$(echo "$POST_INFO" | python3 -c "import json,sys; print(json.load(sys.stdin)['ver'])")
    local NEW_STATUS=$(echo "$POST_INFO" | python3 -c "import json,sys; print(json.load(sys.stdin)['status'])")
    local NEW_PG=$(echo "$POST_INFO" | python3 -c "import json,sys; print(json.load(sys.stdin)['pg'])")
    local NEW_PS=$(echo "$POST_INFO" | python3 -c "import json,sys; print(json.load(sys.stdin)['ps'])")

    # Load original param group for comparison
    local ORIG_PG=""
    if [ -f "$WORKDIR/.pg_${INST_ID}" ]; then
        ORIG_PG=$(cat "$WORKDIR/.pg_${INST_ID}")
    fi

    local VERIFY_OK=true
    if [ "$NEW_VER" != "$TARGET_VERSION" ]; then
        log_error "VERIFY FAILED: $INST_ID version=$NEW_VER (expected $TARGET_VERSION)"
        VERIFY_OK=false
    fi
    if [ "$NEW_STATUS" != "available" ]; then
        log_error "VERIFY FAILED: $INST_ID status=$NEW_STATUS (expected available)"
        VERIFY_OK=false
    fi
    if [ -n "$ORIG_PG" ] && [ "$NEW_PG" != "$ORIG_PG" ]; then
        log_error "VERIFY FAILED: $INST_ID param_group changed from $ORIG_PG to $NEW_PG"
        VERIFY_OK=false
    fi

    if $VERIFY_OK; then
        log_success "RESULT: $INST_ID -> $NEW_VER (${DURATION}s) SUCCESS | pg=$NEW_PG | ps=$NEW_PS"
        echo "$INST_ID,$EXPECTED_VER,$NEW_VER,$NEW_PG,$DURATION,SUCCESS" >> "$WORKDIR/.batch_results"
        return 0
    else
        log_error "RESULT: $INST_ID -> $NEW_VER (${DURATION}s) FAIL"
        echo "$INST_ID,$EXPECTED_VER,$NEW_VER,$NEW_PG,$DURATION,FAIL" >> "$WORKDIR/.batch_results"
        return 1
    fi
}

###############################################################################
# Execute a batch of instances
###############################################################################
execute_batch() {
    local BATCH_NUM="$1"
    local BATCH_NAME="$2"
    shift 2
    # Remaining args are "INSTANCE_ID:EXPECTED_VER" pairs
    local INSTANCES=("$@")
    local COUNT=${#INSTANCES[@]}
    local FAILURES=0

    echo ""
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}BATCH $BATCH_NUM: $BATCH_NAME — $COUNT instances${NC}"
    echo -e "${BLUE}================================================================${NC}"
    log "========================================"
    log "BATCH $BATCH_NUM: $BATCH_NAME — $COUNT instances"
    log "========================================"

    # Print instance list
    echo ""
    echo "Instances in this batch:"
    for entry in "${INSTANCES[@]}"; do
        local INST_ID="${entry%%:*}"
        local INST_VER="${entry##*:}"
        echo "  - $INST_ID ($INST_VER)"
    done
    echo ""

    # Confirmation gate
    read -p "Proceed with Batch $BATCH_NUM? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        log "BATCH $BATCH_NUM: SKIPPED by operator"
        echo "Batch $BATCH_NUM skipped."
        return 0
    fi

    # Clear batch results
    > "$WORKDIR/.batch_results"

    for entry in "${INSTANCES[@]}"; do
        local INST_ID="${entry%%:*}"
        local INST_VER="${entry##*:}"

        echo ""
        echo -e "${BLUE}--- Upgrading $INST_ID ($INST_VER -> $TARGET_VERSION) ---${NC}"

        # Pre-check
        precheck_instance "$INST_ID" "$INST_VER"
        local PC_RC=$?

        if [ $PC_RC -eq 2 ]; then
            echo "  Already on target version. Skipping."
            continue
        elif [ $PC_RC -eq 3 ]; then
            echo "  Skipped by operator."
            continue
        elif [ $PC_RC -ne 0 ]; then
            FAILURES=$((FAILURES + 1))
            if [ $FAILURES -gt $MAX_FAILURES_PER_BATCH ]; then
                log_error "BATCH $BATCH_NUM: >$MAX_FAILURES_PER_BATCH failures — STOPPING ALL EXECUTION"
                echo -e "${RED}CRITICAL: >$MAX_FAILURES_PER_BATCH failures in batch. Execution halted.${NC}"
                return 1
            fi
            echo -e "${RED}  Pre-check failed. Skipping. ($FAILURES failures so far)${NC}"
            continue
        fi

        # Execute upgrade
        upgrade_instance "$INST_ID" "$INST_VER"
        local UPG_RC=$?

        if [ $UPG_RC -ne 0 ]; then
            FAILURES=$((FAILURES + 1))
            if [ $FAILURES -gt $MAX_FAILURES_PER_BATCH ]; then
                log_error "BATCH $BATCH_NUM: >$MAX_FAILURES_PER_BATCH failures — STOPPING ALL EXECUTION"
                echo -e "${RED}CRITICAL: >$MAX_FAILURES_PER_BATCH failures in batch. Execution halted.${NC}"
                return 1
            fi
            echo -e "${RED}  Upgrade failed. Skipping. ($FAILURES failures so far)${NC}"
        fi
    done

    # Batch summary
    echo ""
    echo -e "${BLUE}--- Batch $BATCH_NUM Summary ---${NC}"
    log "--- Batch $BATCH_NUM Summary ---"
    if [ -f "$WORKDIR/.batch_results" ]; then
        echo "Instance,Before,After,ParamGroup,Duration(s),Status"
        cat "$WORKDIR/.batch_results"
        cp "$WORKDIR/.batch_results" "$WORKDIR/batch${BATCH_NUM}-summary.txt"
        log "Batch $BATCH_NUM results saved to batch${BATCH_NUM}-summary.txt"
    fi
    echo ""
    log "BATCH $BATCH_NUM COMPLETE: $FAILURES failures out of $COUNT instances"
    return 0
}

###############################################################################
# Batch Definitions
###############################################################################
run_batch_1() {
    execute_batch 1 "PILOT (DBA Internal Analytics)" \
        "aws-luckyus-ldas-rw:8.0.40" \
        "aws-luckyus-ldas01-rw:8.0.41"
}

run_batch_2() {
    execute_batch 2 "LOW-RISK INTERNAL TOOLS" \
        "aws-luckyus-fichargecontrol-rw:8.0.40" \
        "aws-luckyus-fitax-rw:8.0.40" \
        "aws-luckyus-iadmin-rw:8.0.40" \
        "aws-luckyus-ibillingcentersrv-rw:8.0.40" \
        "aws-luckyus-ibizconfigcenter-rw:8.0.40" \
        "aws-luckyus-iehr-rw:8.0.40" \
        "aws-luckyus-ifiaccounting-rw:8.0.40" \
        "aws-luckyus-igers-rw:8.0.40" \
        "aws-luckyus-ijumpserver-jumpserver-rw:8.0.40" \
        "aws-luckyus-ilsopdevopsdata-rw:8.0.40" \
        "aws-luckyus-iluckyauthapi-rw:8.0.40" \
        "aws-luckyus-iluckydorisops-rw:8.0.40" \
        "aws-luckyus-iluckymedia-rw:8.0.40" \
        "aws-luckyus-iopenadmin-rw:8.0.40" \
        "aws-luckyus-iopenlinker-rw:8.0.40" \
        "aws-luckyus-iopenservice-rw:8.0.40" \
        "aws-luckyus-iopocp-rw:8.0.40" \
        "aws-luckyus-iopshopexpand-rw:8.0.40" \
        "aws-luckyus-ipermission-rw:8.0.40" \
        "aws-luckyus-ireplenishment-rw:8.0.40" \
        "aws-luckyus-iriskcontrolservice-rw:8.0.40" \
        "aws-luckyus-iunifiedreconcile-rw:8.0.40" \
        "aws-luckyus-mfranchise-rw:8.0.40" \
        "aws-luckyus-opempefficiency-rw:8.0.40" \
        "aws-luckyus-oplog-rw:8.0.40" \
        "aws-luckyus-opproduction-rw:8.0.40" \
        "aws-luckyus-opqualitycontrol-rw:8.0.40" \
        "aws-luckyus-opshopsale-rw:8.0.40" \
        "aws-luckyus-pubdm-rw:8.0.40" \
        "aws-luckyus-scm-asset-rw:8.0.40" \
        "aws-luckyus-scm-openapi-rw:8.0.40" \
        "aws-luckyus-scm-ordering-rw:8.0.40" \
        "aws-luckyus-scm-plan-rw:8.0.40" \
        "aws-luckyus-scm-purchase-rw:8.0.40" \
        "aws-luckyus-scm-wds-rw:8.0.40" \
        "aws-luckyus-scm-wmssimulate-rw:8.0.40" \
        "aws-luckyus-scmsrm-rw:8.0.40"
}

run_batch_3() {
    execute_batch 3 "OPS/FINANCE + MEDIUM INSTANCES" \
        "aws-luckyus-isalesmembermarketing-rw:8.0.40" \
        "aws-luckyus-iluckyhealth-rw:8.0.40" \
        "aws-luckyus-devops-rw:8.0.40" \
        "aws-luckyus-iotplatform-rw:8.0.40" \
        "aws-luckyus-iworkflowmidlayer-rw:8.0.40" \
        "aws-luckyus-opshop-rw:8.0.40" \
        "aws-luckyus-scm-shopstock-rw:8.0.40" \
        "aws-luckyus-scmcommodity-rw:8.0.40" \
        "aws-luckyus-upush-rw:8.0.40"
}

run_batch_5() {
    echo -e "${YELLOW}NOTE: Batch 5 (Framework) — upgrading ONE AT A TIME with health check between each${NC}"
    log "BATCH 5: CORE FRAMEWORK — sequential with health checks"

    execute_batch "5a" "CORE FRAMEWORK — framework01" \
        "aws-luckyus-framework01-rw:8.0.40"

    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${YELLOW}framework01 complete. Verify via MCP before proceeding to framework02:${NC}"
        echo "  SELECT @@version, @@sql_mode, @@character_set_server;"
        echo "  SHOW GLOBAL STATUS LIKE 'Threads_connected';"
        echo "  SHOW GLOBAL STATUS LIKE 'Aborted_%';"
        echo ""
        read -p "framework01 verified OK? Proceed to framework02? (yes/no): " CONFIRM
        if [ "$CONFIRM" == "yes" ]; then
            execute_batch "5b" "CORE FRAMEWORK — framework02" \
                "aws-luckyus-framework02-rw:8.0.40"
        else
            log "BATCH 5b: SKIPPED by operator"
        fi
    fi
}

run_batch_6() {
    execute_batch 6 "SALES + MARKETING CORE" \
        "aws-luckyus-cdpactivity-rw:8.0.40" \
        "aws-luckyus-icyberdata-rw:8.0.40" \
        "aws-luckyus-isalescdp-rw:8.0.40" \
        "aws-luckyus-isalesdatamarketing-rw:8.0.40" \
        "aws-luckyus-isalesprivatedomain-rw:8.0.40" \
        "aws-luckyus-salescrm-rw:8.0.40" \
        "aws-luckyus-salespayment-rw:8.0.40" \
        "aws-luckyus-salesorder-rw:8.0.40" \
        "aws-luckyus-salesmarketing-rw:8.0.40"

    # Post-batch special checks
    echo ""
    echo -e "${YELLOW}=== Post-Batch 6 Special Verification ===${NC}"
    echo "1. salesorder: SHOW VARIABLES LIKE 'group_concat_max_len'; (must be 1048576)"
    echo "2. isalescdp: Check CloudWatch FreeableMemory for past 15 min"
    echo "3. salesmarketing: Full MCP + CloudWatch CPU/Memory check"
}

###############################################################################
# Post-upgrade fleet verification
###############################################################################
post_upgrade_verify() {
    echo ""
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}POST-UPGRADE FLEET VERIFICATION${NC}"
    echo -e "${BLUE}================================================================${NC}"
    log "========================================"
    log "POST-UPGRADE FLEET VERIFICATION"
    log "========================================"

    # Fleet scan
    aws rds describe-db-instances --region "$REGION" \
        --query 'DBInstances[?Engine==`mysql`].[DBInstanceIdentifier,EngineVersion,DBInstanceClass,DBParameterGroups[0].DBParameterGroupName,DBInstanceStatus]' \
        --output json > "$WORKDIR/post-upgrade-inventory.json"

    echo "Post-upgrade version distribution:"
    python3 -c "
import json
with open('$WORKDIR/post-upgrade-inventory.json') as f:
    data = json.load(f)
dist = {}
for row in data:
    v = row[1]
    dist[v] = dist.get(v, 0) + 1
for v in sorted(dist):
    marker = ' <<< CRITICAL' if v in ('8.0.40', '8.0.41') else ''
    print(f'  {v}: {dist[v]} instances{marker}')
"

    # Event check
    aws rds describe-events --duration 1440 --source-type db-instance --region "$REGION" \
        --query 'Events[?contains(Message, `error`) || contains(Message, `fail`) || contains(Message, `memory`) || contains(Message, `upgrade`)].[SourceIdentifier,Date,Message]' \
        --output table > "$WORKDIR/post-upgrade-events.txt"

    echo ""
    echo "Post-upgrade events saved to post-upgrade-events.txt"
    log "POST-UPGRADE VERIFICATION COMPLETE"
}

###############################################################################
# Main
###############################################################################
log "PHASE A EXECUTION SCRIPT STARTED"
log "Target version: $TARGET_VERSION"

BATCH="${1:-}"

case "$BATCH" in
    1) run_batch_1 ;;
    2) run_batch_2 ;;
    3) run_batch_3 ;;
    5) run_batch_5 ;;
    6) run_batch_6 ;;
    verify) post_upgrade_verify ;;
    all)
        run_batch_1
        echo ""; echo "=== Batch 1 complete. ==="
        run_batch_2
        echo ""; echo "=== Batch 2 complete. ==="
        run_batch_3
        echo ""; echo "=== Batch 3 complete. ==="
        run_batch_5
        echo ""; echo "=== Batch 5 complete. ==="
        run_batch_6
        echo ""; echo "=== Batch 6 complete. ==="
        post_upgrade_verify
        ;;
    *)
        echo "Usage: $0 {1|2|3|5|6|verify|all}"
        echo ""
        echo "Batches:"
        echo "  1     — PILOT: ldas, ldas01 (2 instances)"
        echo "  2     — LOW-RISK: internal tools (37 instances)"
        echo "  3     — OPS/FINANCE: medium instances (9 instances)"
        echo "  5     — FRAMEWORK: framework01, framework02 (2 instances, one at a time)"
        echo "  6     — SALES/MARKETING: core business (9 instances)"
        echo "  verify — Post-upgrade fleet verification"
        echo "  all   — Run all batches sequentially"
        exit 1
        ;;
esac

log "PHASE A EXECUTION SCRIPT ENDED"
echo ""
echo "Done. Check $LOGFILE for full execution log."
