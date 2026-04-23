from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import get_settings
from .models import (
    LoginCompleteRequest,
    LoginCompleteResponse,
    LoginLivenessResultRequest,
    LoginLivenessResultResponse,
    LoginStartRequest,
    LoginStartResponse,
    LocalCompleteRequest,
    LocalCompleteResponse,
    LocalCredentialsCheckRequest,
    LocalCredentialsCheckResponse,
    LocalFailureRequest,
    LocalFailureResponse,
    LogoutCompleteRequest,
    LogoutCompleteResponse,
    LogoutStartRequest,
    LogoutStartResponse,
    WebAuthnOptionsRequest,
    WebAuthnVerifyRequest,
)
from .services.cognito_service import CognitoService
from .services.event_service import EventService
from .services.mysql_fallback import MySQLFallbackService
from .services.odoo_service import OdooService
from .services.rekognition_service import RekognitionService
from .services.s3_service import S3Service
from .services.telemetry import enrich_geo_by_ip, enrich_user_agent
from .services.webauthn_service import WebAuthnService
from .storage import FlowStore


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.app_debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

flow_store = FlowStore()

cognito_service = CognitoService(
    region=settings.aws_region,
    user_pool_id=settings.cognito_user_pool_id,
    client_id=settings.cognito_client_id,
)
rekognition_service = RekognitionService(region=settings.aws_region)
s3_service = S3Service(
    region=settings.aws_region,
    bucket=settings.s3_bucket_name,
    public_base_url=settings.s3_public_base_url,
)
odoo_service = OdooService(
    base_url=settings.odoo_base_url,
    db_name=settings.odoo_db_name,
    oauth_provider_id=settings.odoo_oauth_provider_id,
    event_ingest_url=settings.odoo_event_ingest_url,
    user_context_url=settings.odoo_user_context_url,
    api_key=settings.odoo_api_key,
)
mysql_fallback_service = MySQLFallbackService(settings.mysql_fallback_connection_file)
event_service = EventService(
    odoo_service=odoo_service,
    mysql_fallback_enabled=settings.mysql_fallback_enabled,
    mysql_fallback_service=mysql_fallback_service,
)
webauthn_service = WebAuthnService(
    enabled=settings.webauthn_enabled,
    rp_id=settings.webauthn_rp_id,
    rp_name=settings.webauthn_rp_name,
)


def _request_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _ensure_geo_rules(telemetry: dict[str, Any]):
    if not settings.gps_required:
        return
    if not telemetry.get("geo_permission_granted"):
        raise HTTPException(status_code=400, detail="Geolocation permission is required")
    if telemetry.get("lat") is None or telemetry.get("lon") is None:
        raise HTTPException(status_code=400, detail="Latitude/longitude are required")


def _emit_or_fail(event: dict[str, Any]) -> dict[str, Any]:
    try:
        response = odoo_service.post_event(event)
    except Exception as exc:  # noqa: BLE001
        _logger.error("event emit failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Could not persist event: {exc}") from exc
    if not response.get("ok", False):
        status_code = int(response.get("_status_code") or 502)
        detail = response.get("message") or response.get("error") or "Could not persist event in Odoo"
        if status_code < 400:
            status_code = 502
        raise HTTPException(status_code=status_code, detail=detail)
    return response


def _safe_emit(event: dict[str, Any]):
    try:
        event_service.emit(event)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("event emit failed: %s", exc)


def _enrich_request_telemetry(telemetry: dict[str, Any], request: Request) -> dict[str, Any]:
    if not telemetry.get("ip_public"):
        telemetry["ip_public"] = _request_ip(request)
    if not telemetry.get("x_forwarded_for"):
        telemetry["x_forwarded_for"] = request.headers.get("x-forwarded-for")
    if not telemetry.get("user_agent"):
        telemetry["user_agent"] = request.headers.get("user-agent")
    telemetry = enrich_user_agent(telemetry)
    telemetry = enrich_geo_by_ip(telemetry)
    return telemetry


def _load_user_context(login: str) -> dict[str, Any]:
    try:
        return odoo_service.fetch_user_context(login)
    except Exception as exc:  # noqa: BLE001
        _logger.error("could not fetch Odoo user context for %s: %s", login, exc)
        raise HTTPException(status_code=502, detail="Could not resolve user context in Odoo") from exc


def _native_login_url() -> str:
    return f"{settings.odoo_base_url.rstrip('/')}/web/login"


def _render_login_page(
    request: Request,
    *,
    login_mode: str,
    auth_channel: str = "standard",
    next_url: str = "/odoo",
    next_logout_url: str = "",
    allow_login_action: bool = True,
    allow_checkout_action: bool = True,
    page_title: str = "Acceso biometrico",
):
    trusted_logout_login = request.query_params.get("logout_login") or ""
    trusted_logout_ts = request.query_params.get("logout_ts") or ""
    trusted_logout_sig = request.query_params.get("logout_sig") or ""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "webauthn_enabled": settings.webauthn_enabled,
            "login_mode": login_mode,
            "auth_channel": auth_channel,
            "next_url": next_url,
            "next_logout_url": next_logout_url or "",
            "trusted_logout_login": trusted_logout_login,
            "trusted_logout_ts": trusted_logout_ts,
            "trusted_logout_sig": trusted_logout_sig,
            "allow_login_action": allow_login_action,
            "allow_checkout_action": allow_checkout_action,
            "page_title": page_title,
        },
    )


def _ensure_demo_channel_allowed(user_context: dict[str, Any]):
    if user_context.get("biometric_mode") == "disabled":
        raise HTTPException(status_code=403, detail="Biometric demo is disabled")
    if not user_context.get("demo_channel_allowed"):
        raise HTTPException(
            status_code=403,
            detail="This biometric demo channel is restricted to the admin user",
        )


def _is_trusted_logout_check_out(payload: LocalCompleteRequest) -> bool:
    return bool(
        payload.action == "check_out"
        and payload.trusted_logout_login
        and payload.trusted_logout_ts
        and payload.trusted_logout_sig
        and payload.next_logout_url
    )


def _verify_trusted_logout_proof(payload: LocalCompleteRequest):
    if not _is_trusted_logout_check_out(payload):
        return

    if not settings.odoo_api_key:
        raise HTTPException(status_code=503, detail="Trusted logout proof is not configured")

    trusted_login = (payload.trusted_logout_login or "").strip()
    if trusted_login != (payload.username or "").strip():
        raise HTTPException(status_code=400, detail="Trusted logout login mismatch")

    try:
        ts = int(payload.trusted_logout_ts or 0)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid trusted logout timestamp") from exc

    now = int(time.time())
    if ts <= 0 or abs(now - ts) > 600:
        raise HTTPException(status_code=401, detail="Trusted logout proof expired")

    message = f"{trusted_login}|{ts}|{payload.next_logout_url or ''}"
    expected = hmac.new(
        (settings.odoo_api_key or "").encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    provided = (payload.trusted_logout_sig or "").strip()
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=401, detail="Invalid trusted logout proof")


def _evaluate_face_match(
    *,
    probe_image_base64: str | None,
    user_context: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "face_match_attempted": False,
        "face_match_passed": False,
        "face_match_similarity": 0.0,
        "face_match_reason": None,
        "face_match_request_id": None,
    }

    if not probe_image_base64:
        result["face_match_reason"] = "probe_image_missing"
        return result
    result["face_match_attempted"] = True

    photo_status = user_context.get("photo_status")
    if photo_status != "ok":
        result["face_match_reason"] = photo_status or "reference_photo_unavailable"
        return result

    reference_photo = user_context.get("reference_photo_base64")
    if not reference_photo:
        result["face_match_reason"] = "reference_photo_missing"
        return result

    try:
        compare = rekognition_service.compare_faces(
            source_image_base64=reference_photo,
            target_image_base64=probe_image_base64,
            similarity_threshold=settings.rekognition_face_match_threshold,
        )
    except Exception as exc:  # noqa: BLE001
        result["face_match_reason"] = f"face_match_error:{exc}"
        return result

    result["face_match_passed"] = bool(compare.get("matched"))
    result["face_match_similarity"] = float(compare.get("similarity") or 0.0)
    result["face_match_request_id"] = compare.get("request_id")
    if not result["face_match_passed"]:
        result["face_match_reason"] = "similarity_below_threshold"
    return result


@app.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse(url="/login", status_code=302)


@app.get("/favicon.ico", response_class=RedirectResponse)
def favicon():
    return RedirectResponse(url="/static/img/logo_devlyn.png", status_code=302)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "env": settings.app_env,
        "liveness_mock_mode": settings.liveness_mock_mode,
    }


@app.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    mode: str | None = None,
    next_logout_url: str | None = None,
):
    if settings.biometric_mode != "all_users":
        return RedirectResponse(url=_native_login_url(), status_code=303)

    login_mode = "check_out" if mode == "check_out" else "check_in"
    next_url = request.query_params.get("next") or "/odoo"
    return _render_login_page(
        request,
        login_mode=login_mode,
        auth_channel="standard",
        next_url=next_url,
        next_logout_url=next_logout_url or "",
    )


@app.get("/demo/login", response_class=HTMLResponse)
def demo_login_page(request: Request):
    if settings.biometric_mode == "disabled":
        return RedirectResponse(url=_native_login_url(), status_code=303)
    next_url = request.query_params.get("next") or "/odoo"
    return _render_login_page(
        request,
        login_mode="check_in",
        auth_channel="admin_demo",
        next_url=next_url,
        allow_login_action=True,
        allow_checkout_action=False,
        page_title="Demo biometrica admin",
    )


@app.get("/demo/logout", response_class=HTMLResponse)
def demo_logout_page(request: Request, next_logout_url: str | None = None):
    if settings.biometric_mode == "disabled":
        target = next_logout_url or request.query_params.get("next_logout_url") or _native_login_url()
        return RedirectResponse(url=target, status_code=303)
    return _render_login_page(
        request,
        login_mode="check_out",
        auth_channel="admin_demo",
        next_url="/odoo",
        next_logout_url=next_logout_url or request.query_params.get("next_logout_url") or "",
        allow_login_action=False,
        allow_checkout_action=True,
        page_title="Demo biometrica admin",
    )


@app.get("/logout", response_class=HTMLResponse)
def logout_page(request: Request, next_logout_url: str | None = None):
    if settings.biometric_mode != "all_users":
        target = next_logout_url or request.query_params.get("next_logout_url") or _native_login_url()
        return RedirectResponse(url=target, status_code=303)
    return templates.TemplateResponse(
        "logout.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "next_logout_url": next_logout_url or f"{settings.odoo_base_url}/web/session/logout?biometric_final=1",
        },
    )


@app.post("/api/v1/login/start", response_model=LoginStartResponse)
def login_start(payload: LoginStartRequest, request: Request):
    telemetry = payload.telemetry.model_dump()
    if not telemetry.get("ip_public"):
        telemetry["ip_public"] = _request_ip(request)
    if not telemetry.get("x_forwarded_for"):
        telemetry["x_forwarded_for"] = request.headers.get("x-forwarded-for")
    if not telemetry.get("user_agent"):
        telemetry["user_agent"] = request.headers.get("user-agent")
    telemetry = enrich_user_agent(telemetry)
    telemetry = enrich_geo_by_ip(telemetry)
    _ensure_geo_rules(telemetry)

    flow_id = str(uuid.uuid4())
    liveness_session_id = ""

    try:
        tokens = cognito_service.custom_auth_with_password(payload.username, payload.password)
    except Exception as exc:  # noqa: BLE001
        _safe_emit(
            {
                "event_type": "login",
                "login": payload.username,
                "result": "failed",
                "auth_channel": "standard",
                "reason": "invalid_credentials",
                "telemetry": telemetry,
                "raw_payload": {"error": str(exc)},
            }
        )
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc

    liveness_key_prefix = f"liveness/login/{payload.username}/{flow_id}"
    try:
        liveness_session_id = rekognition_service.create_liveness_session(
            client_request_token=flow_id,
            bucket=settings.s3_bucket_name,
            key_prefix=liveness_key_prefix,
        )
    except Exception as exc:  # noqa: BLE001
        if settings.liveness_mock_mode:
            liveness_session_id = f"mock-{flow_id}"
        else:
            _safe_emit(
                {
                    "event_type": "login",
                    "login": payload.username,
                    "result": "failed",
                    "auth_channel": "standard",
                    "reason": "liveness_session_error",
                    "telemetry": telemetry,
                    "raw_payload": {"error": str(exc)},
                }
            )
            raise HTTPException(status_code=500, detail="Could not create liveness session") from exc

    flow_store.create_flow(
        flow_id,
        "login",
        {
            "username": payload.username,
            "cognito_access_token": tokens.get("access_token"),
            "cognito_id_token": tokens.get("id_token"),
            "cognito_refresh_token": tokens.get("refresh_token"),
            "liveness_session_id": liveness_session_id,
            "liveness_attempts": 0,
            "status": "credentials_ok",
            "context": {"telemetry": telemetry},
        },
    )

    return LoginStartResponse(
        flow_id=flow_id,
        liveness_session_id=liveness_session_id,
        max_attempts=settings.rekognition_max_attempts,
    )


@app.post("/api/v1/login/liveness-result", response_model=LoginLivenessResultResponse)
def login_liveness_result(payload: LoginLivenessResultRequest):
    flow = flow_store.get_flow(payload.flow_id)
    if not flow or flow.get("kind") != "login":
        raise HTTPException(status_code=404, detail="Flow not found")

    if flow.get("liveness_session_id") != payload.liveness_session_id:
        raise HTTPException(status_code=400, detail="Liveness session mismatch")

    attempts = int(flow.get("liveness_attempts") or 0) + 1
    score = 0.0
    passed = False

    if settings.liveness_mock_mode or str(payload.liveness_session_id).startswith("mock-"):
        score = 99.0
        passed = True
        status = "SUCCEEDED"
    else:
        result = rekognition_service.get_liveness_result(payload.liveness_session_id)
        status = result.get("status") or "UNKNOWN"
        score = float(result.get("confidence") or 0.0)
        passed = status == "SUCCEEDED" and score >= settings.rekognition_liveness_threshold

    s3_video_url = flow.get("s3_video_url")
    if payload.video_base64:
        key = f"videos/login/{payload.flow_id}/{uuid.uuid4()}.webm"
        s3_video_url = s3_service.upload_public_base64_video(key, payload.video_base64)

    flow_store.update_flow(
        payload.flow_id,
        {
            "liveness_attempts": attempts,
            "liveness_score": score,
            "liveness_passed": passed,
            "status": "liveness_passed" if passed else "liveness_failed",
            "s3_video_url": s3_video_url,
        },
    )

    if not passed and attempts >= settings.rekognition_max_attempts:
        _safe_emit(
            {
                "event_type": "login",
                "login": flow.get("username"),
                "result": "failed",
                "auth_channel": "standard",
                "reason": "liveness_failed_max_attempts",
                "liveness_score": score,
                "rekognition_session_id": payload.liveness_session_id,
                "s3_video_url": s3_video_url,
                "telemetry": flow.get("context", {}).get("telemetry", {}),
                "raw_payload": {"status": status, "attempts": attempts},
            }
        )

    return LoginLivenessResultResponse(
        flow_id=payload.flow_id,
        status=status,
        score=score,
        attempts_used=attempts,
        passed=passed,
        s3_video_url=s3_video_url,
    )


@app.post("/api/v1/login/complete", response_model=LoginCompleteResponse)
def login_complete(payload: LoginCompleteRequest):
    flow = flow_store.get_flow(payload.flow_id)
    if not flow or flow.get("kind") != "login":
        raise HTTPException(status_code=404, detail="Flow not found")

    if not flow.get("liveness_passed"):
        raise HTTPException(status_code=400, detail="Liveness step not completed")

    access_token = flow.get("cognito_access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token missing")

    redirect_url = odoo_service.build_oauth_redirect(access_token=access_token, redirect=payload.redirect or "/odoo")
    flow_store.update_flow(payload.flow_id, {"status": "completed"})

    _safe_emit(
        {
            "event_type": "login",
            "login": flow.get("username"),
            "result": "success",
            "auth_channel": "standard",
            "liveness_score": flow.get("liveness_score"),
            "rekognition_session_id": flow.get("liveness_session_id"),
            "s3_video_url": flow.get("s3_video_url"),
            "telemetry": flow.get("context", {}).get("telemetry", {}),
            "raw_payload": {},
        }
    )

    return LoginCompleteResponse(redirect_url=redirect_url)


@app.post("/api/v1/local-complete", response_model=LocalCompleteResponse)
def local_complete(payload: LocalCompleteRequest, request: Request):
    telemetry = _enrich_request_telemetry(payload.telemetry.model_dump(), request)
    _ensure_geo_rules(telemetry)

    if not payload.liveness_meta.get("passed", False):
        raise HTTPException(status_code=400, detail="Liveness validation is required")
    if not payload.video_base64:
        raise HTTPException(status_code=400, detail="Video evidence is required")

    trusted_logout = _is_trusted_logout_check_out(payload)
    if trusted_logout:
        _verify_trusted_logout_proof(payload)

    user_context = _load_user_context(payload.username)
    if payload.auth_channel == "admin_demo":
        _ensure_demo_channel_allowed(user_context)
    is_admin = bool(user_context.get("is_admin"))
    has_employee = bool(user_context.get("has_employee"))
    if not is_admin and not has_employee:
        raise HTTPException(status_code=403, detail="User has no employee linked in Odoo")

    tokens: dict[str, Any] = {}
    if not trusted_logout:
        if not payload.password:
            raise HTTPException(status_code=400, detail="Password is required")
        try:
            tokens = cognito_service.custom_auth_with_password(payload.username, payload.password)
        except Exception as exc:  # noqa: BLE001
            _emit_or_fail(
                {
                    "event_type": "login" if payload.action == "check_in" else "logout",
                    "flow_mode": "local",
                    "auth_channel": payload.auth_channel,
                    "login": payload.username,
                    "result": "failed",
                    "reason": "invalid_credentials",
                    "telemetry": telemetry,
                    "raw_payload": {"error": str(exc)},
                }
            )
            raise HTTPException(status_code=401, detail="Invalid credentials") from exc

    event_type = "login" if payload.action == "check_in" else "logout"
    liveness_score = float(payload.liveness_meta.get("score") or 99.0)
    liveness_passed = bool(payload.liveness_meta.get("passed", True))

    video_key = f"videos/local/{payload.action}/{payload.username}/{uuid.uuid4()}.webm"
    try:
        s3_video_url = s3_service.upload_public_base64_video(video_key, payload.video_base64)
    except ValueError as exc:
        _logger.warning(
            "invalid video payload for user=%s action=%s len=%s err=%s",
            payload.username,
            payload.action,
            len(payload.video_base64 or ""),
            exc,
        )
        raise HTTPException(status_code=400, detail=f"Invalid video payload: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Could not upload video evidence: {exc}") from exc

    face_match = _evaluate_face_match(
        probe_image_base64=payload.probe_image_base64,
        user_context=user_context,
    )

    event_payload: dict[str, Any] = {
        "event_type": event_type,
        "flow_mode": "local",
        "auth_channel": payload.auth_channel,
        "attendance_action": payload.action,
        "login": payload.username,
        "result": "success",
        "reason": None,
        "liveness_provider": "local_ui",
        "liveness_passed": liveness_passed,
        "liveness_score": liveness_score,
        "s3_video_url": s3_video_url,
        "telemetry": telemetry,
        "raw_payload": {
            "next_logout_url": payload.next_logout_url,
            "is_admin": is_admin,
            "photo_status": user_context.get("photo_status"),
            "liveness_meta": payload.liveness_meta,
            "trusted_logout": trusted_logout,
        },
    }
    event_payload.update(face_match)

    event_response = _emit_or_fail(event_payload)
    attendance_status = (event_response or {}).get("attendance_status")
    attendance_error = (event_response or {}).get("error")
    allow_logout_without_open_attendance = (
        payload.action == "check_out"
        and attendance_status == "failed"
        and attendance_error == "attendance_open_missing"
    )
    if attendance_status and attendance_status not in {"success", "skipped"} and not allow_logout_without_open_attendance:
        raise HTTPException(status_code=409, detail=attendance_error or "Attendance rejected")

    if payload.action == "check_out":
        if payload.next_logout_url:
            return LocalCompleteResponse(redirect_url=payload.next_logout_url)
        return LocalCompleteResponse(
            status="ok",
            message="Salida registrada correctamente",
            completed_at=datetime.now(timezone.utc),
        )

    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token missing")

    redirect_url = odoo_service.build_oauth_redirect(access_token=access_token, redirect=payload.redirect or "/odoo")
    return LocalCompleteResponse(redirect_url=redirect_url)


@app.post("/api/v1/local-credentials-check", response_model=LocalCredentialsCheckResponse)
def local_credentials_check(payload: LocalCredentialsCheckRequest):
    """
    Validate credentials before starting UI liveness, to avoid running the camera flow
    for invalid usernames/passwords.
    """
    try:
        cognito_service.custom_auth_with_password(payload.username, payload.password)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc

    context = _load_user_context(payload.username)
    if payload.auth_channel == "admin_demo" and not context.get("demo_channel_allowed"):
        return LocalCredentialsCheckResponse(
            ok=False,
            is_admin=bool(context.get("is_admin")),
            has_employee=bool(context.get("has_employee")),
            requires_biometric=True,
            block_reason="demo_channel_forbidden",
        )
    is_admin = bool(context.get("is_admin"))
    has_employee = bool(context.get("has_employee"))
    if not has_employee and not is_admin:
        return LocalCredentialsCheckResponse(
            ok=False,
            is_admin=is_admin,
            has_employee=has_employee,
            requires_biometric=True,
            block_reason="user_without_employee",
        )

    return LocalCredentialsCheckResponse(
        ok=True,
        is_admin=is_admin,
        has_employee=has_employee,
        requires_biometric=True,
    )


@app.post("/api/v1/local-failure", response_model=LocalFailureResponse)
def local_failure(payload: LocalFailureRequest, request: Request):
    telemetry = _enrich_request_telemetry(payload.telemetry.model_dump(), request)

    user_context = _load_user_context(payload.username)
    if payload.auth_channel == "admin_demo":
        _ensure_demo_channel_allowed(user_context)
    face_match = _evaluate_face_match(
        probe_image_base64=payload.probe_image_base64,
        user_context=user_context,
    )

    s3_video_url = None
    if payload.video_base64:
        video_key = f"videos/local/{payload.action}/{payload.username}/{uuid.uuid4()}-failed.webm"
        try:
            s3_video_url = s3_service.upload_public_base64_video(video_key, payload.video_base64)
        except ValueError:
            s3_video_url = None
        except Exception:  # noqa: BLE001
            s3_video_url = None

    event_payload: dict[str, Any] = {
        "event_type": "login" if payload.action == "check_in" else "logout",
        "flow_mode": "local",
        "auth_channel": payload.auth_channel,
        "login": payload.username,
        "result": "failed",
        "reason": payload.reason,
        "liveness_provider": "local_ui",
        "liveness_passed": False,
        "s3_video_url": s3_video_url,
        "telemetry": telemetry,
        "raw_payload": payload.raw_payload,
    }
    event_payload.update(face_match)
    response = _emit_or_fail(event_payload)
    return LocalFailureResponse(ok=True, event_id=response.get("event_id"))


@app.post("/api/v1/logout/start", response_model=LogoutStartResponse)
def logout_start(payload: LogoutStartRequest, request: Request):
    telemetry = payload.telemetry.model_dump()
    if not telemetry.get("ip_public"):
        telemetry["ip_public"] = _request_ip(request)
    if not telemetry.get("x_forwarded_for"):
        telemetry["x_forwarded_for"] = request.headers.get("x-forwarded-for")
    if not telemetry.get("user_agent"):
        telemetry["user_agent"] = request.headers.get("user-agent")
    telemetry = enrich_user_agent(telemetry)
    telemetry = enrich_geo_by_ip(telemetry)
    _ensure_geo_rules(telemetry)

    flow_id = str(uuid.uuid4())
    liveness_key_prefix = f"liveness/logout/{payload.username or 'unknown'}/{flow_id}"
    try:
        liveness_session_id = rekognition_service.create_liveness_session(
            client_request_token=flow_id,
            bucket=settings.s3_bucket_name,
            key_prefix=liveness_key_prefix,
        )
    except Exception as exc:  # noqa: BLE001
        if settings.liveness_mock_mode:
            liveness_session_id = f"mock-{flow_id}"
        else:
            raise HTTPException(status_code=500, detail="Could not create liveness session") from exc

    flow_store.create_flow(
        flow_id,
        "logout",
        {
            "username": payload.username,
            "liveness_session_id": liveness_session_id,
            "liveness_attempts": 0,
            "next_logout_url": payload.next_logout_url,
            "status": "started",
            "context": {"telemetry": telemetry},
        },
    )

    return LogoutStartResponse(
        flow_id=flow_id,
        liveness_session_id=liveness_session_id,
        max_attempts=settings.rekognition_max_attempts,
    )


@app.post("/api/v1/logout/complete", response_model=LogoutCompleteResponse)
def logout_complete(payload: LogoutCompleteRequest):
    flow = flow_store.get_flow(payload.flow_id)
    if not flow or flow.get("kind") != "logout":
        raise HTTPException(status_code=404, detail="Flow not found")

    if flow.get("liveness_session_id") != payload.liveness_session_id:
        raise HTTPException(status_code=400, detail="Liveness session mismatch")

    attempts = int(flow.get("liveness_attempts") or 0) + 1

    if settings.liveness_mock_mode or str(payload.liveness_session_id).startswith("mock-"):
        status = "SUCCEEDED"
        score = 99.0
    else:
        result = rekognition_service.get_liveness_result(payload.liveness_session_id)
        status = result.get("status") or "UNKNOWN"
        score = float(result.get("confidence") or 0.0)

    passed = status == "SUCCEEDED" and score >= settings.rekognition_liveness_threshold

    s3_video_url = flow.get("s3_video_url")
    if payload.video_base64:
        key = f"videos/logout/{payload.flow_id}/{uuid.uuid4()}.webm"
        s3_video_url = s3_service.upload_public_base64_video(key, payload.video_base64)

    flow_store.update_flow(
        payload.flow_id,
        {
            "liveness_attempts": attempts,
            "liveness_score": score,
            "liveness_passed": passed,
            "status": "completed" if passed else "failed",
            "s3_video_url": s3_video_url,
        },
    )

    _safe_emit(
        {
            "event_type": "logout",
            "login": flow.get("username"),
            "result": "success" if passed else "failed",
            "auth_channel": "standard",
            "reason": None if passed else "liveness_failed",
            "liveness_score": score,
            "rekognition_session_id": flow.get("liveness_session_id"),
            "s3_video_url": s3_video_url,
            "telemetry": flow.get("context", {}).get("telemetry", {}),
            "raw_payload": {"attempts": attempts},
        }
    )

    if not passed:
        raise HTTPException(status_code=400, detail="Liveness validation failed")

    return LogoutCompleteResponse(redirect_url=payload.next_logout_url, passed=True)


@app.get("/oidc/odoo-validation")
def odoo_validation(request: Request, access_token: str | None = None):
    token = access_token
    if not token:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()

    if not token:
        return JSONResponse(status_code=401, content={"error": "missing_token"})

    try:
        user = cognito_service.get_user(token)
    except Exception:  # noqa: BLE001
        return JSONResponse(status_code=401, content={"error": "invalid_token"})

    return {
        "sub": user.get("sub") or user.get("username"),
        "user_id": user.get("sub") or user.get("username"),
        "email": user.get("email"),
        "name": user.get("name"),
        "preferred_username": user.get("username"),
    }


@app.post("/api/v1/webauthn/register/options")
def webauthn_register_options(payload: WebAuthnOptionsRequest):
    return webauthn_service.registration_options(payload.username)


@app.post("/api/v1/webauthn/register/verify")
def webauthn_register_verify(payload: WebAuthnVerifyRequest):
    return webauthn_service.verify_registration(payload.username, payload.credential)


@app.post("/api/v1/webauthn/auth/options")
def webauthn_auth_options(payload: WebAuthnOptionsRequest):
    return webauthn_service.auth_options(payload.username)


@app.post("/api/v1/webauthn/auth/verify")
def webauthn_auth_verify(payload: WebAuthnVerifyRequest):
    return webauthn_service.verify_auth(payload.username, payload.credential)
