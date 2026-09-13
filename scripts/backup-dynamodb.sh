#!/usr/bin/env bash
#
# backup-dynamodb.sh
#
# Backs up the DynamoDB traffic-archive table to a local JSON file. The table
# name is CloudFormation-generated, so it is resolved from the stack's
# `TrafficArchiveTableName` output rather than hardcoded.
#
# The backup is a full scan in native DynamoDB JSON, wrapped as:
#
#   { "TableName": "...", "BackedUpAt": "...", "ItemCount": N, "Items": [ ... ] }
#
# Each item is restorable with `aws dynamodb put-item --item <item>`.
#
# Usage:
#   ./scripts/backup-dynamodb.sh                 # defaults below
#   ./scripts/backup-dynamodb.sh -o /path/dir    # custom output directory
#   STACK_NAME=other AWS_PROFILE=p AWS_REGION=r ./scripts/backup-dynamodb.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

STACK_NAME="${STACK_NAME:-github-traffic-analyzer}"
AWS_PROFILE="${AWS_PROFILE:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"
OUTPUT_DIR="${REPO_ROOT}/backups"

while getopts ":o:h" opt; do
  case "$opt" in
    o) OUTPUT_DIR="$OPTARG" ;;
    h) sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "Unknown option: -$OPTARG" >&2; exit 2 ;;
  esac
done

AWS=(aws --region "$AWS_REGION")
# Only pass --profile when one is set; otherwise use the default credential chain.
[[ -n "$AWS_PROFILE" ]] && AWS+=(--profile "$AWS_PROFILE")

echo "Resolving table name from stack '$STACK_NAME'..."
TABLE_NAME="$("${AWS[@]}" cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='TrafficArchiveTableName'].OutputValue" \
  --output text)"

if [[ -z "$TABLE_NAME" || "$TABLE_NAME" == "None" ]]; then
  echo "ERROR: could not resolve TrafficArchiveTableName from stack '$STACK_NAME'." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_FILE="${OUTPUT_DIR}/${TABLE_NAME}-${TIMESTAMP}.json"

echo "Scanning '$TABLE_NAME' (the CLI auto-paginates)..."
RAW_ITEMS="$(mktemp)"
trap 'rm -f "$RAW_ITEMS"' EXIT

# --output json merges every page's Items into a single array.
"${AWS[@]}" dynamodb scan \
  --table-name "$TABLE_NAME" \
  --output json \
  --query 'Items' >"$RAW_ITEMS"

COUNT="$(TABLE_NAME="$TABLE_NAME" TIMESTAMP="$TIMESTAMP" OUTPUT_FILE="$OUTPUT_FILE" \
  python3 - "$RAW_ITEMS" <<'PY'
import json, os, sys

with open(sys.argv[1]) as f:
    items = json.load(f)

with open(os.environ["OUTPUT_FILE"], "w") as f:
    json.dump(
        {
            "TableName": os.environ["TABLE_NAME"],
            "BackedUpAt": os.environ["TIMESTAMP"],
            "ItemCount": len(items),
            "Items": items,
        },
        f,
        indent=2,
    )

print(len(items))
PY
)"

echo "Backed up $COUNT items to: $OUTPUT_FILE"
