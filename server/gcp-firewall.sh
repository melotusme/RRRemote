#!/usr/bin/env bash
# Open required TCP/UDP ports on Google Cloud VPC firewall for RRRemote.
# Usage:
#   PROJECT_ID=my-gcp-project TARGET_TAG=my-vm-tag bash server/gcp-firewall.sh

set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
TARGET_TAG="${TARGET_TAG:?Set TARGET_TAG}"
RULE_NAME="${RULE_NAME:-rrremote-allow-ports}"

gcloud compute firewall-rules create "${RULE_NAME}" \
  --project="${PROJECT_ID}" \
  --network=default \
  --direction=INGRESS \
  --priority=1000 \
  --action=ALLOW \
  --rules="tcp:21114-21119,udp:21116" \
  --target-tags="${TARGET_TAG}" \
  --description="Allow RRRemote (hbbs/hbbr/api) ports"
