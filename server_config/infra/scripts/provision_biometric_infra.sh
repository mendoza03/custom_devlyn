#!/usr/bin/env bash
set -euo pipefail

PROFILE_AIE=${PROFILE_AIE:-aie}
REGION=${REGION:-us-east-1}
INSTANCE_ID=${INSTANCE_ID:-i-0f59d42c00367eb56}
POOL_NAME=${POOL_NAME:-odoo-biometric-pool}
APP_CLIENT_NAME=${APP_CLIENT_NAME:-odoo-biometric-client}
BUCKET_PREFERRED=${BUCKET_PREFERRED:-biometric}
BUCKET_FALLBACK=${BUCKET_FALLBACK:-biometric-004619892671-us-east-1}
LAMBDA_ROLE_NAME=${LAMBDA_ROLE_NAME:-odoo-biometric-cognito-lambda-role}
EC2_ROLE_NAME=${EC2_ROLE_NAME:-odoo-biometric-gateway-ec2-role}
EC2_INSTANCE_PROFILE_NAME=${EC2_INSTANCE_PROFILE_NAME:-odoo-biometric-gateway-ec2-profile}

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
TMP_DIR=/tmp/odoo-biometric-infra
mkdir -p "$TMP_DIR"

function aws_aie() {
  aws --profile "$PROFILE_AIE" --region "$REGION" "$@"
}

function retry_aws() {
  local attempts="$1"
  local sleep_seconds="$2"
  shift 2

  local i
  for ((i=1; i<=attempts; i++)); do
    if "$@"; then
      return 0
    fi
    if [[ "$i" -lt "$attempts" ]]; then
      sleep "$sleep_seconds"
    fi
  done
  return 1
}

function wait_lambda_ready() {
  local name="$1"
  local max_checks="${2:-60}"
  local i

  for ((i=1; i<=max_checks; i++)); do
    local state
    local update_status
    state=$(aws_aie lambda get-function --function-name "$name" --query 'Configuration.State' --output text 2>/dev/null || true)
    update_status=$(aws_aie lambda get-function --function-name "$name" --query 'Configuration.LastUpdateStatus' --output text 2>/dev/null || true)
    if [[ "$state" == "Active" && "$update_status" == "Successful" ]]; then
      return 0
    fi
    sleep 2
  done

  echo "Lambda $name did not reach Active/Successful state in time" >&2
  aws_aie lambda get-function --function-name "$name" --query 'Configuration.{State:State,LastUpdateStatus:LastUpdateStatus,LastUpdateStatusReason:LastUpdateStatusReason}' --output json || true
  return 1
}

echo "[1/8] Ensure EIP is associated to instance $INSTANCE_ID"
ALLOC_ID=$(aws_aie ec2 describe-addresses --filters Name=instance-id,Values="$INSTANCE_ID" --query 'Addresses[0].AllocationId' --output text)
if [[ "$ALLOC_ID" == "None" || -z "$ALLOC_ID" ]]; then
  ALLOC_ID=$(aws_aie ec2 allocate-address --domain vpc --query 'AllocationId' --output text)
fi
aws_aie ec2 associate-address --instance-id "$INSTANCE_ID" --allocation-id "$ALLOC_ID" --allow-reassociation >/dev/null
PUBLIC_IP=$(aws_aie ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "EIP allocation: $ALLOC_ID | Public IP: $PUBLIC_IP"

echo "[2/8] Ensure S3 bucket exists"
BUCKET_NAME="$BUCKET_PREFERRED"
if ! aws_aie s3api head-bucket --bucket "$BUCKET_NAME" >/dev/null 2>&1; then
  BUCKET_NAME="$BUCKET_FALLBACK"
  if ! aws_aie s3api head-bucket --bucket "$BUCKET_NAME" >/dev/null 2>&1; then
    aws_aie s3api create-bucket --bucket "$BUCKET_NAME"
  fi
fi

aws_aie s3api put-public-access-block --bucket "$BUCKET_NAME" --public-access-block-configuration BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false
aws_aie s3api put-bucket-ownership-controls --bucket "$BUCKET_NAME" --ownership-controls 'Rules=[{ObjectOwnership=BucketOwnerPreferred}]'
cat > "$TMP_DIR/bucket-policy.json" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowPublicReadObjects",
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*"
    }
  ]
}
JSON
aws_aie s3api put-bucket-policy --bucket "$BUCKET_NAME" --policy file://"$TMP_DIR/bucket-policy.json"
echo "Bucket ready: $BUCKET_NAME"

echo "[3/8] Ensure IAM role for Cognito lambdas"
ROLE_ARN=$(aws_aie iam get-role --role-name "$LAMBDA_ROLE_NAME" --query 'Role.Arn' --output text 2>/dev/null || true)
if [[ -z "$ROLE_ARN" || "$ROLE_ARN" == "None" ]]; then
  cat > "$TMP_DIR/lambda-trust-policy.json" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
JSON
  ROLE_ARN=$(aws_aie iam create-role --role-name "$LAMBDA_ROLE_NAME" --assume-role-policy-document file://"$TMP_DIR/lambda-trust-policy.json" --query 'Role.Arn' --output text)
  aws_aie iam attach-role-policy --role-name "$LAMBDA_ROLE_NAME" --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
fi

cat > "$TMP_DIR/lambda-inline-policy.json" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "*"
    }
  ]
}
JSON
aws_aie iam put-role-policy --role-name "$LAMBDA_ROLE_NAME" --policy-name odoo-biometric-inline-policy --policy-document file://"$TMP_DIR/lambda-inline-policy.json"

echo "[3.5/8] Ensure EC2 role/profile for auth-gateway"
GATEWAY_ROLE_ARN=$(aws_aie iam get-role --role-name "$EC2_ROLE_NAME" --query 'Role.Arn' --output text 2>/dev/null || true)
if [[ -z "$GATEWAY_ROLE_ARN" || "$GATEWAY_ROLE_ARN" == "None" ]]; then
  cat > "$TMP_DIR/ec2-trust-policy.json" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
JSON
  GATEWAY_ROLE_ARN=$(aws_aie iam create-role --role-name "$EC2_ROLE_NAME" --assume-role-policy-document file://"$TMP_DIR/ec2-trust-policy.json" --query 'Role.Arn' --output text)
fi

cat > "$TMP_DIR/gateway-inline-policy.json" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RekognitionLiveness",
      "Effect": "Allow",
      "Action": [
        "rekognition:CreateFaceLivenessSession",
        "rekognition:GetFaceLivenessSessionResults"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CognitoCustomAuth",
      "Effect": "Allow",
      "Action": [
        "cognito-idp:InitiateAuth",
        "cognito-idp:RespondToAuthChallenge",
        "cognito-idp:GetUser"
      ],
      "Resource": "*"
    },
    {
      "Sid": "BiometricBucketWriteRead",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*"
    },
    {
      "Sid": "BiometricBucketList",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::${BUCKET_NAME}"
    }
  ]
}
JSON
aws_aie iam put-role-policy --role-name "$EC2_ROLE_NAME" --policy-name odoo-biometric-gateway-inline-policy --policy-document file://"$TMP_DIR/gateway-inline-policy.json"

PROFILE_EXISTS=$(aws_aie iam get-instance-profile --instance-profile-name "$EC2_INSTANCE_PROFILE_NAME" --query 'InstanceProfile.InstanceProfileName' --output text 2>/dev/null || true)
if [[ -z "$PROFILE_EXISTS" || "$PROFILE_EXISTS" == "None" ]]; then
  aws_aie iam create-instance-profile --instance-profile-name "$EC2_INSTANCE_PROFILE_NAME" >/dev/null
fi

if ! aws_aie iam get-instance-profile --instance-profile-name "$EC2_INSTANCE_PROFILE_NAME" --query "InstanceProfile.Roles[?RoleName=='${EC2_ROLE_NAME}'].RoleName | [0]" --output text | grep -q "^${EC2_ROLE_NAME}$"; then
  aws_aie iam add-role-to-instance-profile --instance-profile-name "$EC2_INSTANCE_PROFILE_NAME" --role-name "$EC2_ROLE_NAME" >/dev/null || true
fi

ASSOCIATION_ID=$(aws_aie ec2 describe-iam-instance-profile-associations --filters Name=instance-id,Values="$INSTANCE_ID" --query 'IamInstanceProfileAssociations[0].AssociationId' --output text 2>/dev/null || true)
if [[ -z "$ASSOCIATION_ID" || "$ASSOCIATION_ID" == "None" ]]; then
  retry_aws 12 5 aws_aie ec2 associate-iam-instance-profile --instance-id "$INSTANCE_ID" --iam-instance-profile Name="$EC2_INSTANCE_PROFILE_NAME" >/dev/null || true
  ASSOCIATION_ID=$(aws_aie ec2 describe-iam-instance-profile-associations --filters Name=instance-id,Values="$INSTANCE_ID" --query 'IamInstanceProfileAssociations[0].AssociationId' --output text 2>/dev/null || true)
  if [[ -z "$ASSOCIATION_ID" || "$ASSOCIATION_ID" == "None" ]]; then
    echo "Could not associate instance profile ${EC2_INSTANCE_PROFILE_NAME} to ${INSTANCE_ID}" >&2
    exit 1
  fi
else
  CURRENT_PROFILE_ARN=$(aws_aie ec2 describe-iam-instance-profile-associations --association-ids "$ASSOCIATION_ID" --query 'IamInstanceProfileAssociations[0].IamInstanceProfile.Arn' --output text 2>/dev/null || true)
  if [[ "$CURRENT_PROFILE_ARN" != *"/${EC2_INSTANCE_PROFILE_NAME}" ]]; then
    retry_aws 12 5 aws_aie ec2 replace-iam-instance-profile-association --association-id "$ASSOCIATION_ID" --iam-instance-profile Name="$EC2_INSTANCE_PROFILE_NAME" >/dev/null
  fi
fi

echo "[4/8] Deploy Cognito trigger lambdas"
function upsert_lambda() {
  local name="$1"
  local src_dir="$2"
  local handler="$3"
  local env_json="${4:-}"
  local zip_file="$TMP_DIR/${name}.zip"

  (cd "$src_dir" && zip -q -r "$zip_file" .)

  if aws_aie lambda get-function --function-name "$name" >/dev/null 2>&1; then
    retry_aws 12 5 aws_aie lambda update-function-code --function-name "$name" --zip-file "fileb://${zip_file}" >/dev/null
    wait_lambda_ready "$name"
    if [[ -n "$env_json" ]]; then
      retry_aws 12 5 aws_aie lambda update-function-configuration --function-name "$name" --environment "$env_json" >/dev/null
      wait_lambda_ready "$name"
    fi
  else
    if [[ -n "$env_json" ]]; then
      retry_aws 12 5 aws_aie lambda create-function \
        --function-name "$name" \
        --runtime python3.12 \
        --role "$ROLE_ARN" \
        --handler "$handler" \
        --zip-file "fileb://${zip_file}" \
        --timeout 15 \
        --environment "$env_json" >/dev/null
    else
      retry_aws 12 5 aws_aie lambda create-function \
        --function-name "$name" \
        --runtime python3.12 \
        --role "$ROLE_ARN" \
        --handler "$handler" \
        --zip-file "fileb://${zip_file}" \
        --timeout 15 >/dev/null
    fi
    wait_lambda_ready "$name"
  fi
}

upsert_lambda "odoo-biometric-define-auth-challenge" "$ROOT_DIR/server_config/lambdas/cognito_define_auth_challenge" "lambda_function.lambda_handler"
upsert_lambda "odoo-biometric-create-auth-challenge" "$ROOT_DIR/server_config/lambdas/cognito_create_auth_challenge" "lambda_function.lambda_handler"
upsert_lambda "odoo-biometric-verify-auth-challenge" "$ROOT_DIR/server_config/lambdas/cognito_verify_auth_challenge" "lambda_function.lambda_handler" "Variables={ODOO_URL=https://erp.odootest.mvpstart.click,ODOO_DB=devlyn_com}"

DEFINE_ARN=$(aws_aie lambda get-function --function-name odoo-biometric-define-auth-challenge --query 'Configuration.FunctionArn' --output text)
CREATE_ARN=$(aws_aie lambda get-function --function-name odoo-biometric-create-auth-challenge --query 'Configuration.FunctionArn' --output text)
VERIFY_ARN=$(aws_aie lambda get-function --function-name odoo-biometric-verify-auth-challenge --query 'Configuration.FunctionArn' --output text)

echo "[5/8] Ensure Cognito User Pool + App Client"
USER_POOL_ID=$(aws_aie cognito-idp list-user-pools --max-results 60 --query "UserPools[?Name=='${POOL_NAME}'].Id | [0]" --output text)
if [[ "$USER_POOL_ID" == "None" || -z "$USER_POOL_ID" ]]; then
  USER_POOL_ID=$(aws_aie cognito-idp create-user-pool \
    --pool-name "$POOL_NAME" \
    --alias-attributes email preferred_username \
    --lambda-config "DefineAuthChallenge=${DEFINE_ARN},CreateAuthChallenge=${CREATE_ARN},VerifyAuthChallengeResponse=${VERIFY_ARN}" \
    --query 'UserPool.Id' --output text)
else
  aws_aie cognito-idp update-user-pool \
    --user-pool-id "$USER_POOL_ID" \
    --lambda-config "DefineAuthChallenge=${DEFINE_ARN},CreateAuthChallenge=${CREATE_ARN},VerifyAuthChallengeResponse=${VERIFY_ARN}" >/dev/null
fi

USER_POOL_ARN=$(aws_aie cognito-idp describe-user-pool --user-pool-id "$USER_POOL_ID" --query 'UserPool.Arn' --output text)
aws_aie lambda add-permission \
  --function-name odoo-biometric-define-auth-challenge \
  --statement-id odoo-biometric-cognito-define-auth \
  --action lambda:InvokeFunction \
  --principal cognito-idp.amazonaws.com \
  --source-arn "$USER_POOL_ARN" >/dev/null 2>&1 || true
aws_aie lambda add-permission \
  --function-name odoo-biometric-create-auth-challenge \
  --statement-id odoo-biometric-cognito-create-auth \
  --action lambda:InvokeFunction \
  --principal cognito-idp.amazonaws.com \
  --source-arn "$USER_POOL_ARN" >/dev/null 2>&1 || true
aws_aie lambda add-permission \
  --function-name odoo-biometric-verify-auth-challenge \
  --statement-id odoo-biometric-cognito-verify-auth \
  --action lambda:InvokeFunction \
  --principal cognito-idp.amazonaws.com \
  --source-arn "$USER_POOL_ARN" >/dev/null 2>&1 || true

APP_CLIENT_ID=$(aws_aie cognito-idp list-user-pool-clients --user-pool-id "$USER_POOL_ID" --max-results 60 --query "UserPoolClients[?ClientName=='${APP_CLIENT_NAME}'].ClientId | [0]" --output text)
if [[ "$APP_CLIENT_ID" == "None" || -z "$APP_CLIENT_ID" ]]; then
  APP_CLIENT_ID=$(aws_aie cognito-idp create-user-pool-client \
    --user-pool-id "$USER_POOL_ID" \
    --client-name "$APP_CLIENT_NAME" \
    --no-generate-secret \
    --explicit-auth-flows ALLOW_CUSTOM_AUTH ALLOW_REFRESH_TOKEN_AUTH \
    --prevent-user-existence-errors ENABLED \
    --query 'UserPoolClient.ClientId' --output text)
else
  aws_aie cognito-idp update-user-pool-client \
    --user-pool-id "$USER_POOL_ID" \
    --client-id "$APP_CLIENT_ID" \
    --explicit-auth-flows ALLOW_CUSTOM_AUTH ALLOW_REFRESH_TOKEN_AUTH \
    --prevent-user-existence-errors ENABLED >/dev/null
fi

echo "[6/8] Ensure SG has 80/443"
"$ROOT_DIR/server_config/infra/scripts/configure_security_group.sh"

echo "[7/8] Output summary"
cat <<OUT
PUBLIC_IP=$PUBLIC_IP
S3_BUCKET_NAME=$BUCKET_NAME
COGNITO_USER_POOL_ID=$USER_POOL_ID
COGNITO_CLIENT_ID=$APP_CLIENT_ID
DEFINE_AUTH_LAMBDA_ARN=$DEFINE_ARN
CREATE_AUTH_LAMBDA_ARN=$CREATE_ARN
VERIFY_AUTH_LAMBDA_ARN=$VERIFY_ARN
OUT

echo "[8/8] Done"
