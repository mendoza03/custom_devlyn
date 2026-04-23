#!/usr/bin/env python3
import os
import random
import string
import sys
import xmlrpc.client
import re

import boto3
from botocore.exceptions import ClientError


def random_password(length: int = 24) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(random.choice(chars) for _ in range(length))


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_email(value: str) -> bool:
    return bool(EMAIL_RE.match((value or "").strip()))


def main() -> int:
    region = os.getenv("AWS_REGION", "us-east-1")
    profile = os.getenv("AWS_PROFILE", "aie")

    odoo_url = os.getenv("ODOO_URL", "https://erp.odootest.mvpstart.click")
    odoo_db = os.getenv("ODOO_DB", "devlyn_com")
    odoo_admin_login = os.getenv("ODOO_ADMIN_LOGIN", "admin")
    odoo_admin_password = os.getenv("ODOO_ADMIN_PASSWORD")

    user_pool_id = os.getenv("COGNITO_USER_POOL_ID")

    if not odoo_admin_password:
      print("Missing ODOO_ADMIN_PASSWORD", file=sys.stderr)
      return 1
    if not user_pool_id:
      print("Missing COGNITO_USER_POOL_ID", file=sys.stderr)
      return 1

    session = boto3.Session(profile_name=profile, region_name=region)
    cognito = session.client("cognito-idp")

    common = xmlrpc.client.ServerProxy(f"{odoo_url}/xmlrpc/2/common")
    uid = common.authenticate(odoo_db, odoo_admin_login, odoo_admin_password, {})
    if not uid:
        print("Could not authenticate against Odoo with admin credentials", file=sys.stderr)
        return 1

    models = xmlrpc.client.ServerProxy(f"{odoo_url}/xmlrpc/2/object")
    user_ids = models.execute_kw(
        odoo_db,
        uid,
        odoo_admin_password,
        "res.users",
        "search",
        [[("active", "=", True), ("share", "=", False)]],
    )

    fields = ["id", "login", "name", "active"]
    users = models.execute_kw(
        odoo_db,
        uid,
        odoo_admin_password,
        "res.users",
        "read",
        [user_ids],
        {"fields": fields},
    )

    created = 0
    updated = 0
    skipped = 0

    for user in users:
        login = (user.get("login") or "").strip().lower()
        if not login:
            skipped += 1
            continue

        try:
            cognito.admin_get_user(UserPoolId=user_pool_id, Username=login)
            updated += 1
            continue
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "UserNotFoundException":
                print(f"Error checking user {login}: {exc}", file=sys.stderr)
                continue

        temp_password = random_password()
        attrs = [
            {"Name": "name", "Value": user.get("name") or login},
            {"Name": "preferred_username", "Value": login},
        ]
        if is_email(login):
            attrs.append({"Name": "email", "Value": login})
            attrs.append({"Name": "email_verified", "Value": "true"})

        try:
            cognito.admin_create_user(
                UserPoolId=user_pool_id,
                Username=login,
                UserAttributes=attrs,
                MessageAction="SUPPRESS",
            )
            cognito.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=login,
                Password=temp_password,
                Permanent=True,
            )
            created += 1
        except ClientError as exc:
            print(f"Error creating user {login}: {exc}", file=sys.stderr)

    print(f"Done. created={created} updated={updated} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
