#!/usr/bin/env bash
set -euo pipefail

PROFILE_AIE=${PROFILE_AIE:-aie}
REGION=${REGION:-us-east-1}
SG_ID=${SG_ID:-sg-09c32cf44bfcf52e3}

# Ensure 80/443 open
for port in 80 443; do
  aws ec2 authorize-security-group-ingress \
    --profile "$PROFILE_AIE" \
    --region "$REGION" \
    --group-id "$SG_ID" \
    --ip-permissions "[{\"IpProtocol\":\"tcp\",\"FromPort\":$port,\"ToPort\":$port,\"IpRanges\":[{\"CidrIp\":\"0.0.0.0/0\"}]}]" \
    2>/dev/null || true
done

echo "Ingress rules ensured for ports 80 and 443"
