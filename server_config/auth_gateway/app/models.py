from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class TelemetryPayload(BaseModel):
    ip_public: Optional[str] = None
    x_forwarded_for: Optional[str] = None
    user_agent: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    device_type: Optional[str] = None

    lat: Optional[float] = None
    lon: Optional[float] = None
    accuracy: Optional[float] = None
    geo_permission_granted: bool = True

    country: Optional[str] = None
    city: Optional[str] = None
    asn: Optional[str] = None
    isp: Optional[str] = None

    network_type: Optional[str] = None
    downlink: Optional[float] = None
    rtt: Optional[float] = None


class LoginStartRequest(BaseModel):
    username: str
    password: str
    telemetry: TelemetryPayload


class LoginStartResponse(BaseModel):
    flow_id: str
    liveness_session_id: str
    max_attempts: int


class LoginLivenessResultRequest(BaseModel):
    flow_id: str
    liveness_session_id: str
    video_base64: Optional[str] = None


class LoginLivenessResultResponse(BaseModel):
    flow_id: str
    status: str
    score: float
    attempts_used: int
    passed: bool
    s3_video_url: Optional[str] = None


class LoginCompleteRequest(BaseModel):
    flow_id: str
    redirect: Optional[str] = "/odoo"


class LoginCompleteResponse(BaseModel):
    redirect_url: str


class LocalCompleteRequest(BaseModel):
    username: str
    password: Optional[str] = None
    action: Literal["check_in", "check_out"] = "check_in"
    auth_channel: Literal["standard", "admin_demo"] = "standard"
    redirect: Optional[str] = "/odoo"
    next_logout_url: Optional[str] = None
    trusted_logout_login: Optional[str] = None
    trusted_logout_ts: Optional[int] = None
    trusted_logout_sig: Optional[str] = None
    telemetry: TelemetryPayload
    probe_image_base64: Optional[str] = None
    video_base64: Optional[str] = None
    liveness_meta: dict[str, Any] = Field(default_factory=dict)


class LocalCompleteResponse(BaseModel):
    redirect_url: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    completed_at: Optional[datetime] = None


class LocalCredentialsCheckRequest(BaseModel):
    username: str
    password: str
    action: Literal["check_in", "check_out"] = "check_in"
    auth_channel: Literal["standard", "admin_demo"] = "standard"


class LocalCredentialsCheckResponse(BaseModel):
    ok: bool
    is_admin: bool = False
    has_employee: bool = False
    requires_biometric: bool = True
    block_reason: Optional[str] = None


class LocalFailureRequest(BaseModel):
    username: str
    action: Literal["check_in", "check_out"] = "check_in"
    auth_channel: Literal["standard", "admin_demo"] = "standard"
    reason: str
    telemetry: TelemetryPayload
    probe_image_base64: Optional[str] = None
    video_base64: Optional[str] = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class LocalFailureResponse(BaseModel):
    ok: bool
    event_id: Optional[int] = None


class LogoutStartRequest(BaseModel):
    next_logout_url: str
    username: Optional[str] = None
    telemetry: TelemetryPayload


class LogoutStartResponse(BaseModel):
    flow_id: str
    liveness_session_id: str
    max_attempts: int


class LogoutCompleteRequest(BaseModel):
    flow_id: str
    liveness_session_id: str
    next_logout_url: str
    video_base64: Optional[str] = None


class LogoutCompleteResponse(BaseModel):
    redirect_url: str
    passed: bool


class EventPayload(BaseModel):
    event_type: str
    login: Optional[str] = None
    result: str
    reason: Optional[str] = None
    flow_mode: Optional[str] = None
    auth_channel: Literal["standard", "admin_demo"] = "standard"
    attendance_action: Optional[str] = None
    attendance_status: Optional[str] = None
    attendance_id: Optional[int] = None
    liveness_score: Optional[float] = None
    liveness_passed: Optional[bool] = None
    liveness_provider: Optional[str] = None
    rekognition_session_id: Optional[str] = None
    s3_video_url: Optional[str] = None
    face_match_attempted: Optional[bool] = None
    face_match_passed: Optional[bool] = None
    face_match_similarity: Optional[float] = None
    face_match_reason: Optional[str] = None
    face_match_request_id: Optional[str] = None
    auto_close_applied: Optional[bool] = None
    auto_close_reason: Optional[str] = None
    auto_closed_attendance_id: Optional[int] = None
    cognito_sub: Optional[str] = None
    telemetry: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class WebAuthnOptionsRequest(BaseModel):
    username: str


class WebAuthnVerifyRequest(BaseModel):
    username: str
    credential: dict[str, Any]
