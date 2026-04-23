#!/usr/bin/env bash
set -euo pipefail

PROFILE_AIE=${PROFILE_AIE:-aie}
REGION=${REGION:-us-east-1}
SG_ID=${SG_ID:-sg-09c32cf44bfcf52e3}

aws ec2 revoke-security-group-ingress \
  --profile "$PROFILE_AIE" \
  --region "$REGION" \
  --group-id "$SG_ID" \
  --protocol tcp --port 8069 --cidr 0.0.0.0/0 \
  2>/dev/null || true

echo "Port 8069 ingress revoked (if it existed)."
