#!/usr/bin/env python3
import os
import secrets
import string
import sys
import xmlrpc.client


def random_key(length=48):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    odoo_url = os.getenv("ODOO_URL", "https://erp.odootest.mvpstart.click")
    db = os.getenv("ODOO_DB", "devlyn_com")
    admin_login = os.getenv("ODOO_ADMIN_LOGIN", "admin")
    admin_password = os.getenv("ODOO_ADMIN_PASSWORD", "admin")

    auth_base_url = os.getenv("AUTH_BASE_URL", "https://auth.odootest.mvpstart.click")
    erp_base_url = os.getenv("ERP_BASE_URL", "https://erp.odootest.mvpstart.click")
    cognito_client_id = os.getenv("COGNITO_CLIENT_ID", "")
    provider_name = os.getenv("ODOO_OAUTH_PROVIDER_NAME", "Cognito Biometric Gateway")
    biometric_mode = os.getenv("BIOMETRIC_MODE", "admin_demo_only")
    attendance_sync_enabled = env_bool("ATTENDANCE_SYNC_ENABLED", False)
    admin_demo_login = os.getenv("BIOMETRIC_ADMIN_DEMO_LOGIN", "admin")

    common = xmlrpc.client.ServerProxy(f"{odoo_url}/xmlrpc/2/common")
    uid = common.authenticate(db, admin_login, admin_password, {})
    if not uid:
        print("Could not authenticate to Odoo", file=sys.stderr)
        return 1

    models = xmlrpc.client.ServerProxy(f"{odoo_url}/xmlrpc/2/object")

    # Ensure auth_oauth installed
    auth_oauth_ids = models.execute_kw(db, uid, admin_password, "ir.module.module", "search", [[("name", "=", "auth_oauth")]])
    if auth_oauth_ids:
        state = models.execute_kw(db, uid, admin_password, "ir.module.module", "read", [auth_oauth_ids], {"fields": ["state"]})[0]["state"]
        if state != "installed":
            models.execute_kw(db, uid, admin_password, "ir.module.module", "button_immediate_install", [auth_oauth_ids])

    # Ensure bridge module installed
    bridge_ids = models.execute_kw(db, uid, admin_password, "ir.module.module", "search", [[("name", "=", "odoo_biometric_bridge")]])
    if bridge_ids:
        state = models.execute_kw(db, uid, admin_password, "ir.module.module", "read", [bridge_ids], {"fields": ["state"]})[0]["state"]
        if state != "installed":
            models.execute_kw(db, uid, admin_password, "ir.module.module", "button_immediate_install", [bridge_ids])

    validation_endpoint = f"{auth_base_url.rstrip('/')}/oidc/odoo-validation"
    provider_vals = {
        "name": provider_name,
        "body": "Iniciar sesión con autenticación biométrica",
        "client_id": cognito_client_id,
        "enabled": True,
        "auth_endpoint": f"{auth_base_url.rstrip('/')}/login",
        "validation_endpoint": validation_endpoint,
        "data_endpoint": validation_endpoint,
        "scope": "openid email profile",
    }

    provider_ids = models.execute_kw(db, uid, admin_password, "auth.oauth.provider", "search", [[("name", "=", provider_name)]])
    if provider_ids:
        models.execute_kw(db, uid, admin_password, "auth.oauth.provider", "write", [provider_ids, provider_vals])
        provider_id = provider_ids[0]
    else:
        provider_id = models.execute_kw(db, uid, admin_password, "auth.oauth.provider", "create", [provider_vals])

    api_key = os.getenv("ODOO_BIOMETRIC_API_KEY") or random_key()

    policy_ids = models.execute_kw(db, uid, admin_password, "biometric.policy", "search", [[("active", "=", True)]], {"limit": 1})
    policy_vals = {
        "auth_base_url": auth_base_url,
        "erp_base_url": erp_base_url,
        "api_key": api_key,
        "biometric_mode": biometric_mode,
        "attendance_sync_enabled": attendance_sync_enabled,
        "admin_demo_login": admin_demo_login,
    }
    if policy_ids:
        models.execute_kw(db, uid, admin_password, "biometric.policy", "write", [policy_ids, policy_vals])
        policy_id = policy_ids[0]
    else:
        policy_id = models.execute_kw(db, uid, admin_password, "biometric.policy", "create", [policy_vals])

    print(f"ODOO_OAUTH_PROVIDER_ID={provider_id}")
    print(f"ODOO_BIOMETRIC_POLICY_ID={policy_id}")
    print(f"ODOO_BIOMETRIC_API_KEY={api_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
