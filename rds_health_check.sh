#!/bin/bash
###############################################################################
# RDS Live Health Data Collector
# Luckin Coffee North America — DBA Infrastructure Team
# Collects instance metadata + CloudWatch metrics for all MySQL RDS instances
#
# Usage: ./rds_health_check.sh
# Output: rds_health_snapshot_YYYYMMDD_HHMM.tsv + console table
###############################################################################

set -euo pipefail

REGION="us-east-1"
MAX_CONCURRENT=10
TMPDIR_BASE=$(mktemp -d /tmp/rds_health_XXXXXX)
trap 'rm -rf "$TMPDIR_BASE"' EXIT

TIMESTAMP=$(date +%Y%m%d_%H%M)
TSV_FILE="rds_health_snapshot_${TIMESTAMP}.tsv"

# CloudWatch time range: last 1 hour
END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
START_TIME=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)

# Instance class → RAM (GB)
declare -A RAM_MAP=(
    ["db.t3.micro"]=1    ["db.t3.small"]=2    ["db.t3.medium"]=4
    ["db.t3.large"]=8    ["db.t3.xlarge"]=16   ["db.t3.2xlarge"]=32
    ["db.t4g.micro"]=1   ["db.t4g.small"]=2   ["db.t4g.medium"]=4
    ["db.t4g.large"]=8   ["db.t4g.xlarge"]=16  ["db.t4g.2xlarge"]=32
    ["db.r5.large"]=16   ["db.r5.xlarge"]=32  ["db.r5.2xlarge"]=64
    ["db.r5.4xlarge"]=128 ["db.r5.8xlarge"]=256
    ["db.r6g.large"]=16  ["db.r6g.xlarge"]=32 ["db.r6g.2xlarge"]=64
    ["db.r6g.4xlarge"]=128 ["db.r6g.8xlarge"]=256
    ["db.r6i.large"]=16  ["db.r6i.xlarge"]=32 ["db.r6i.2xlarge"]=64
    ["db.r7g.large"]=16  ["db.r7g.xlarge"]=32 ["db.r7g.2xlarge"]=64
    ["db.m5.large"]=8    ["db.m5.xlarge"]=16  ["db.m5.2xlarge"]=32
    ["db.m6g.large"]=8   ["db.m6g.xlarge"]=16 ["db.m6g.2xlarge"]=32
)

echo "=== RDS Health Check — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "Region: $REGION | CloudWatch window: $START_TIME → $END_TIME"
echo ""

###############################################################################
# Step 1: Fetch all MySQL RDS instances (single API call)
###############################################################################
echo "Fetching RDS instance metadata..."
INSTANCES_JSON=$(aws rds describe-db-instances --region "$REGION" \
    --query 'DBInstances[?Engine==`mysql`].[DBInstanceIdentifier,EngineVersion,DBInstanceClass,DBParameterGroups[0].DBParameterGroupName,DBParameterGroups[0].ParameterApplyStatus,DBInstanceStatus,MultiAZ,PendingModifiedValues]' \
    --output json)

INSTANCE_COUNT=$(echo "$INSTANCES_JSON" | jq 'length')
echo "Found $INSTANCE_COUNT MySQL instances."
echo ""

# Parse instance metadata into temp files
echo "$INSTANCES_JSON" | jq -c '.[]' | while read -r row; do
    INST=$(echo "$row" | jq -r '.[0]')
    VERSION=$(echo "$row" | jq -r '.[1]')
    CLASS=$(echo "$row" | jq -r '.[2]')
    PARAM_GROUP=$(echo "$row" | jq -r '.[3]')
    PARAM_STATUS=$(echo "$row" | jq -r '.[4]')
    STATUS=$(echo "$row" | jq -r '.[5]')
    MULTIAZ=$(echo "$row" | jq -r '.[6]')
    PENDING_RAW=$(echo "$row" | jq -r '.[7]')

    RAM_GB=${RAM_MAP[$CLASS]:-"?"}

    # Check if PendingModifiedValues is empty (all null/empty)
    PENDING="none"
    NON_NULL=$(echo "$PENDING_RAW" | jq 'to_entries | map(select(.value != null and .value != "")) | length')
    if [ "$NON_NULL" -gt 0 ]; then
        PENDING=$(echo "$PENDING_RAW" | jq -c 'to_entries | map(select(.value != null and .value != "")) | from_entries')
    fi

    echo -e "${INST}\t${VERSION}\t${CLASS}\t${RAM_GB}\t${PARAM_GROUP}\t${PARAM_STATUS}\t${STATUS}\t${MULTIAZ}\t${PENDING}" \
        > "${TMPDIR_BASE}/meta_${INST}"
done

###############################################################################
# Step 2: CloudWatch metrics in parallel (max 10 concurrent)
###############################################################################
echo "Querying CloudWatch metrics (max $MAX_CONCURRENT parallel)..."

fetch_metrics() {
    local INST="$1"
    local OUTFILE="${TMPDIR_BASE}/cw_${INST}"

    # FreeableMemory — Minimum over last hour
    local FM_JSON
    FM_JSON=$(aws cloudwatch get-metric-statistics --region "$REGION" \
        --namespace AWS/RDS --metric-name FreeableMemory \
        --dimensions Name=DBInstanceIdentifier,Value="$INST" \
        --start-time "$START_TIME" --end-time "$END_TIME" \
        --period 300 --statistics Minimum \
        --output json 2>/dev/null || echo '{"Datapoints":[]}')

    local FM_BYTES
    FM_BYTES=$(echo "$FM_JSON" | jq '[.Datapoints[].Minimum] | min // empty')
    local FM_MB="N/A"
    if [ -n "$FM_BYTES" ] && [ "$FM_BYTES" != "null" ]; then
        FM_MB=$(awk "BEGIN {printf \"%.0f\", $FM_BYTES / 1048576}")
    fi

    # SwapUsage — Maximum over last hour
    local SW_JSON
    SW_JSON=$(aws cloudwatch get-metric-statistics --region "$REGION" \
        --namespace AWS/RDS --metric-name SwapUsage \
        --dimensions Name=DBInstanceIdentifier,Value="$INST" \
        --start-time "$START_TIME" --end-time "$END_TIME" \
        --period 300 --statistics Maximum \
        --output json 2>/dev/null || echo '{"Datapoints":[]}')

    local SW_BYTES
    SW_BYTES=$(echo "$SW_JSON" | jq '[.Datapoints[].Maximum] | max // empty')
    local SW_MB="N/A"
    if [ -n "$SW_BYTES" ] && [ "$SW_BYTES" != "null" ]; then
        SW_MB=$(awk "BEGIN {printf \"%.0f\", $SW_BYTES / 1048576}")
    fi

    echo -e "${FM_MB}\t${SW_MB}" > "$OUTFILE"
}

# Export function and variables for subshells
export -f fetch_metrics
export REGION START_TIME END_TIME TMPDIR_BASE

# Launch parallel CloudWatch queries with semaphore
RUNNING=0
INSTANCE_LIST=$(echo "$INSTANCES_JSON" | jq -r '.[][0]')

for INST in $INSTANCE_LIST; do
    fetch_metrics "$INST" &
    RUNNING=$((RUNNING + 1))
    if [ "$RUNNING" -ge "$MAX_CONCURRENT" ]; then
        wait -n 2>/dev/null || true
        RUNNING=$((RUNNING - 1))
    fi
done
wait
echo "CloudWatch queries complete."
echo ""

###############################################################################
# Step 3: Merge data, calculate OOM risk, output
###############################################################################

# TSV header
HEADER="Instance\tVersion\tClass\tRAM_GB\tFreeMem_MB\tSwap_MB\tOOM_Risk\tStatus\tParamGroup\tParamSync\tMultiAZ\tPendingChanges"
echo -e "$HEADER" > "$TSV_FILE"

# Also build a sortable temp file for console output
SORT_FILE="${TMPDIR_BASE}/sortable.tsv"

for META_FILE in "${TMPDIR_BASE}"/meta_*; do
    [ -f "$META_FILE" ] || continue
    INST=$(basename "$META_FILE" | sed 's/^meta_//')

    IFS=$'\t' read -r _ VERSION CLASS RAM_GB PARAM_GROUP PARAM_STATUS STATUS MULTIAZ PENDING < "$META_FILE"

    CW_FILE="${TMPDIR_BASE}/cw_${INST}"
    if [ -f "$CW_FILE" ]; then
        IFS=$'\t' read -r FM_MB SW_MB < "$CW_FILE"
    else
        FM_MB="N/A"
        SW_MB="N/A"
    fi

    # OOM risk
    OOM_RISK="N/A"
    if [ "$FM_MB" != "N/A" ]; then
        if [ "$FM_MB" -lt 150 ]; then
            OOM_RISK="RED"
        elif [ "$FM_MB" -lt 300 ]; then
            OOM_RISK="YELLOW"
        else
            OOM_RISK="GREEN"
        fi
    fi

    # Sort key: numeric FreeMem_MB (N/A → 999999 so they sort last)
    SORT_KEY="$FM_MB"
    [ "$FM_MB" = "N/A" ] && SORT_KEY="999999"

    echo -e "${SORT_KEY}\t${INST}\t${VERSION}\t${CLASS}\t${RAM_GB}\t${FM_MB}\t${SW_MB}\t${OOM_RISK}\t${STATUS}\t${PARAM_GROUP}\t${PARAM_STATUS}\t${MULTIAZ}\t${PENDING}" \
        >> "$SORT_FILE"
done

# Sort by FreeMem_MB ascending (numeric), write TSV and console table
CONSOLE_FILE="${TMPDIR_BASE}/console.tsv"
echo -e "Instance\tVersion\tClass\tRAM\tFreeMem\tSwap\tRisk\tStatus\tParamGroup\tParamSync\tMultiAZ\tPending" > "$CONSOLE_FILE"

sort -t$'\t' -k1 -n "$SORT_FILE" | while IFS=$'\t' read -r _SORTKEY INST VERSION CLASS RAM_GB FM_MB SW_MB OOM_RISK STATUS PARAM_GROUP PARAM_STATUS MULTIAZ PENDING; do
    echo -e "${INST}\t${VERSION}\t${CLASS}\t${RAM_GB}\t${FM_MB}\t${SW_MB}\t${OOM_RISK}\t${STATUS}\t${PARAM_GROUP}\t${PARAM_STATUS}\t${MULTIAZ}\t${PENDING}" >> "$TSV_FILE"
    echo -e "${INST}\t${VERSION}\t${CLASS}\t${RAM_GB}\t${FM_MB}\t${SW_MB}\t${OOM_RISK}\t${STATUS}\t${PARAM_GROUP}\t${PARAM_STATUS}\t${MULTIAZ}\t${PENDING}" >> "$CONSOLE_FILE"
done

# Display formatted table
echo "=== RDS HEALTH SNAPSHOT (sorted by FreeMem ascending) ==="
echo ""
awk -F'\t' '{printf "%-32s %-8s %-16s %4s %8s %8s %-8s %-12s %-30s %-14s %-6s %s\n", $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12}' "$CONSOLE_FILE"
echo ""

###############################################################################
# Step 4: Summary
###############################################################################
echo "=== SUMMARY ==="

# Total count
TOTAL=$(tail -n +2 "$TSV_FILE" | wc -l)
echo "Total: $TOTAL MySQL instances"

# Count by version
echo -n "By version: "
tail -n +2 "$TSV_FILE" | awk -F'\t' '{print $2}' | sort | uniq -c | sort -rn | \
    awk '{printf " %s=%s", $2, $1}' | sed 's/^ //'
echo ""

# Count by OOM risk
echo -n "By risk:    "
tail -n +2 "$TSV_FILE" | awk -F'\t' '{print $7}' | sort | uniq -c | sort -rn | \
    awk '{printf " %s=%s", $2, $1}' | sed 's/^ //'
echo ""

# Pending changes
PENDING_LIST=$(tail -n +2 "$TSV_FILE" | awk -F'\t' '$12 != "none" {print $1 " (" $12 ")"}')
if [ -z "$PENDING_LIST" ]; then
    echo "Pending changes: none"
else
    echo "Pending changes:"
    echo "$PENDING_LIST" | sed 's/^/  - /'
fi

# Param sync issues
SYNC_ISSUES=$(tail -n +2 "$TSV_FILE" | awk -F'\t' '$10 != "in-sync" {print $1 " (" $10 ")"}')
if [ -z "$SYNC_ISSUES" ]; then
    echo "Param sync issues: none"
else
    echo "Param sync issues:"
    echo "$SYNC_ISSUES" | sed 's/^/  - /'
fi

echo ""
echo "TSV saved to: $(pwd)/$TSV_FILE"
echo "Done."
