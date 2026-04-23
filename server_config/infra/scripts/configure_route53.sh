#!/usr/bin/env bash
set -euo pipefail

PROFILE_DEFAULT=${PROFILE_DEFAULT:-default}
HOSTED_ZONE_ID=${HOSTED_ZONE_ID:-Z01964051HV1ZX1UY5T0N}
TARGET_IP=${TARGET_IP:?Set TARGET_IP}

cat > /tmp/route53-odootest-records.json <<JSON
{
  "Comment": "Upsert auth/erp/mcp records for biometric Odoo PoC",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "auth.odootest.mvpstart.click.",
        "Type": "A",
        "TTL": 60,
        "ResourceRecords": [{"Value": "${TARGET_IP}"}]
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "erp.odootest.mvpstart.click.",
        "Type": "A",
        "TTL": 60,
        "ResourceRecords": [{"Value": "${TARGET_IP}"}]
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "mcp.odootest.mvpstart.click.",
        "Type": "A",
        "TTL": 60,
        "ResourceRecords": [{"Value": "${TARGET_IP}"}]
      }
    }
  ]
}
JSON

aws route53 change-resource-record-sets \
  --profile "$PROFILE_DEFAULT" \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --change-batch file:///tmp/route53-odootest-records.json
