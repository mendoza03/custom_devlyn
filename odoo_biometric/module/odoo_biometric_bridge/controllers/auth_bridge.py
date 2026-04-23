import json
import hashlib
import hmac
import ipaddress
import urllib.parse
import base64
import time

from odoo import http
from odoo.http import request
from werkzeug.utils import redirect as wz_redirect

from odoo.addons.auth_oauth.controllers.main import OAuthLogin
from odoo.addons.web.controllers.session import Session


def _is_dev_direct_access() -> bool:
    """
    Dev bypass: if Odoo is being accessed directly by IP/localhost (not via the
    ERP domain behind Nginx), allow normal login/logout without forcing the
    biometric gateway.
    """
    # If we're behind the public Nginx/TLS endpoint, do not allow the dev bypass.
    xf_proto = (request.httprequest.headers.get("x-forwarded-proto") or "").lower().strip()
    if xf_proto == "https":
        return False

    host = (request.httprequest.host or "").split(":", 1)[0].strip()
    host = host.strip("[]")  # IPv6 in Host header
    if host in {"localhost"}:
        return True
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _is_biometric_admin_bypass() -> bool:
    return bool(
        request.params.get("biometric_admin") == "1"
        and (request.httprequest.headers.get("X-Biometric-Admin-Bypass") or "").strip() == "1"
    )


class BiometricHome(OAuthLogin):
    def _should_hide_biometric_provider(self, policy):
        return bool(policy) and not policy.should_force_gateway()

    def _is_biometric_provider(self, policy, provider):
        auth_base = (policy.auth_base_url or "https://auth.odootest.mvpstart.click").rstrip("/")
        for field_name in ("auth_endpoint", "validation_endpoint", "data_endpoint"):
            value = (provider.get(field_name) or "").rstrip("/")
            if value.startswith(auth_base):
                return True
        return False

    def list_providers(self):
        providers = super().list_providers()
        policy = request.env["biometric.policy"].sudo().get_active_policy()
        if not self._should_hide_biometric_provider(policy):
            return providers
        return [provider for provider in providers if not self._is_biometric_provider(policy, provider)]

    @http.route("/web/login", type="http", auth="none")
    def web_login(self, *args, **kw):
        if _is_dev_direct_access() or _is_biometric_admin_bypass():
            return super().web_login(*args, **kw)

        policy = request.env["biometric.policy"].sudo().get_active_policy()
        if not policy.should_force_gateway():
            return super().web_login(*args, **kw)

        redirect = request.params.get("redirect") or "/odoo"
        auth_base = (policy.auth_base_url or "https://auth.odootest.mvpstart.click").rstrip("/")
        target = f"{auth_base}/login?next={urllib.parse.quote_plus(redirect)}"
        return wz_redirect(target, code=303)

    @http.route("/__admin_login__", type="http", auth="none")
    def admin_login(self, *args, **kw):
        return wz_redirect("/web/login?biometric_admin=1", code=303)

    @http.route("/biometric/demo/login", type="http", auth="none")
    def biometric_demo_login(self, *args, **kw):
        policy = request.env["biometric.policy"].sudo().get_active_policy()
        if policy.biometric_mode == "disabled":
            return wz_redirect("/web/login", code=303)

        redirect = request.params.get("redirect") or request.params.get("next") or "/odoo"
        auth_base = (policy.auth_base_url or "https://auth.odootest.mvpstart.click").rstrip("/")
        params = {
            "next": redirect,
            "auth_channel": "admin_demo",
        }
        target = f"{auth_base}/demo/login?{urllib.parse.urlencode(params)}"
        return wz_redirect(target, code=303)


class BiometricSession(Session):
    def _build_check_out_target(
        self,
        auth_base,
        final_logout,
        api_key,
        login,
        *,
        auth_path="/login",
        extra_params=None,
    ):
        params = {
            "mode": "check_out",
            "next_logout_url": final_logout,
        }
        if extra_params:
            params.update(extra_params)
        if login and api_key:
            ts = int(time.time())
            message = f"{login}|{ts}|{final_logout}"
            sig = hmac.new(
                api_key.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            params.update(
                {
                    "logout_login": login,
                    "logout_ts": str(ts),
                    "logout_sig": sig,
                }
            )
        return f"{auth_base}{auth_path}?{urllib.parse.urlencode(params)}"

    def _session_login(self):
        if not request.session.uid:
            return None
        user = request.env["res.users"].sudo().browse(request.session.uid)
        if not user or not user.exists():
            return None
        return user.login

    @http.route("/biometric/logout", type="http", auth="public")
    def biometric_logout(self, redirect="/odoo", **kw):
        policy = request.env["biometric.policy"].sudo().get_active_policy()
        if not policy.should_force_gateway():
            return super().logout(redirect=redirect, **kw)

        auth_base = (policy.auth_base_url or "https://auth.odootest.mvpstart.click").rstrip("/")
        erp_base = (policy.erp_base_url or request.httprequest.url_root).rstrip("/")
        final_logout = f"{erp_base}/web/session/logout?biometric_final=1"
        login = self._session_login()
        target = self._build_check_out_target(auth_base, final_logout, policy.api_key, login)
        return wz_redirect(target, code=303)

    @http.route("/biometric/demo/logout", type="http", auth="public")
    def biometric_demo_logout(self, redirect="/odoo", **kw):
        policy = request.env["biometric.policy"].sudo().get_active_policy()
        login = self._session_login()
        if not login or not policy.is_demo_login_allowed(login):
            return wz_redirect("/web/login", code=303)

        auth_base = (policy.auth_base_url or "https://auth.odootest.mvpstart.click").rstrip("/")
        erp_base = (policy.erp_base_url or request.httprequest.url_root).rstrip("/")
        final_logout = (
            f"{erp_base}/web/session/logout?biometric_final=1"
            f"&redirect={urllib.parse.quote_plus('/web/login')}"
        )
        target = self._build_check_out_target(
            auth_base,
            final_logout,
            policy.api_key,
            login,
            auth_path="/demo/logout",
            extra_params={"auth_channel": "admin_demo"},
        )
        return wz_redirect(target, code=303)

    @http.route("/web/session/logout", type="http", auth="public")
    def logout(self, redirect="/odoo", **kw):
        if request.params.get("biometric_final") == "1":
            return super().logout(redirect=redirect, **kw)

        if not request.session.uid:
            return super().logout(redirect=redirect, **kw)

        if _is_dev_direct_access() or _is_biometric_admin_bypass():
            return super().logout(redirect=redirect, **kw)

        policy = request.env["biometric.policy"].sudo().get_active_policy()
        if not policy.should_force_gateway():
            return super().logout(redirect=redirect, **kw)

        auth_base = (policy.auth_base_url or "https://auth.odootest.mvpstart.click").rstrip("/")
        erp_base = (policy.erp_base_url or request.httprequest.url_root).rstrip("/")
        final_logout = f"{erp_base}/web/session/logout?biometric_final=1"
        login = self._session_login()
        target = self._build_check_out_target(auth_base, final_logout, policy.api_key, login)
        return wz_redirect(target, code=303)


class BiometricApiController(http.Controller):
    def _authorized(self):
        policy = request.env["biometric.policy"].sudo().get_active_policy()
        expected = policy.api_key
        provided = request.httprequest.headers.get("X-Biometric-API-Key")
        return bool(expected and provided and provided == expected)

    @http.route(
        "/biometric/api/v1/event",
        type="http",
        auth="none",
        csrf=False,
        methods=["POST"],
    )
    def ingest_event(self, **kwargs):
        if not self._authorized():
            return request.make_response(
                json.dumps({"ok": False, "error": "unauthorized"}),
                status=401,
                headers=[("Content-Type", "application/json")],
            )

        payload = request.httprequest.get_json(silent=True)
        if not payload:
            raw = request.httprequest.data
            if raw:
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except Exception:  # noqa: BLE001
                    payload = {}
        payload = payload or kwargs or {}

        event, error = request.env["biometric.auth.event"].sudo().create_from_gateway(payload)
        if error:
            body = {
                "ok": False,
                "error": error.get("error") or "attendance_error",
                "message": error.get("message"),
                "event_id": event.id,
                "attendance_status": event.attendance_status,
                "attendance_id": event.attendance_id.id if event.attendance_id else None,
            }
            return request.make_response(
                json.dumps(body),
                status=409,
                headers=[("Content-Type", "application/json")],
            )

        return request.make_response(
            json.dumps(
                {
                    "ok": True,
                    "event_id": event.id,
                    "attendance_status": event.attendance_status,
                    "attendance_id": event.attendance_id.id if event.attendance_id else None,
                }
            ),
            headers=[("Content-Type", "application/json")],
        )

    @http.route(
        "/biometric/api/v1/user-context",
        type="http",
        auth="none",
        csrf=False,
        methods=["POST"],
    )
    def user_context(self, **kwargs):
        if not self._authorized():
            return request.make_response(
                json.dumps({"ok": False, "error": "unauthorized"}),
                status=401,
                headers=[("Content-Type", "application/json")],
            )

        payload = request.httprequest.get_json(silent=True) or kwargs or {}
        login = (payload.get("login") or "").strip()
        if not login:
            return request.make_response(
                json.dumps({"ok": False, "error": "missing_login"}),
                status=400,
                headers=[("Content-Type", "application/json")],
            )

        user = request.env["res.users"].sudo().search([("login", "=", login)], limit=1)
        if not user:
            return request.make_response(
                json.dumps({"ok": False, "error": "user_not_found"}),
                status=404,
                headers=[("Content-Type", "application/json")],
            )

        employee = request.env["hr.employee"].sudo().search([("user_id", "=", user.id)], limit=1)
        photo_status = "photo_missing"
        photo_mime = None
        photo_b64 = None

        def _extract_attachment_photo(res_model, res_id, fields_candidates):
            for field_name in fields_candidates:
                attachment = request.env["ir.attachment"].sudo().search(
                    [
                        ("res_model", "=", res_model),
                        ("res_field", "=", field_name),
                        ("res_id", "=", res_id),
                    ],
                    order="id desc",
                    limit=1,
                )
                if not attachment:
                    continue

                mime = attachment.mimetype or ""
                if mime == "image/svg+xml":
                    return None, None, "invalid_mime_svg"
                if not str(mime).startswith("image/"):
                    return None, None, "invalid_mime"

                data = attachment.datas
                if not data:
                    return None, None, "photo_missing_data"
                if isinstance(data, bytes):
                    try:
                        photo = data.decode("ascii")
                    except Exception:  # noqa: BLE001
                        photo = base64.b64encode(data).decode("ascii")
                else:
                    photo = data
                return mime, photo, "ok"

            return None, None, "photo_missing"

        if employee:
            photo_mime, photo_b64, photo_status = _extract_attachment_photo(
                "hr.employee",
                employee.id,
                ["image_1920"],
            )
        else:
            photo_status = "employee_not_found"

        if photo_status != "ok":
            user_photo_mime, user_photo_b64, user_photo_status = _extract_attachment_photo(
                "res.users",
                user.id,
                ["image_1920", "avatar_1920"],
            )
            if user_photo_status == "ok":
                photo_mime = user_photo_mime
                photo_b64 = user_photo_b64
                photo_status = "ok_user_photo_fallback"

        policy = request.env["biometric.policy"].sudo().get_active_policy()
        body = {
            "ok": True,
            "user_id": user.id,
            "employee_id": employee.id if employee else None,
            "is_admin": user.login == (policy.admin_demo_login or "admin"),
            "has_employee": bool(employee),
            "reference_photo_mime": photo_mime,
            "reference_photo_base64": photo_b64,
            "photo_status": photo_status,
            "biometric_mode": policy.biometric_mode,
            "demo_channel_allowed": policy.is_demo_login_allowed(user.login),
        }
        return request.make_response(
            json.dumps(body),
            headers=[("Content-Type", "application/json")],
        )
