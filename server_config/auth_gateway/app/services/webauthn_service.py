import base64
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any


_logger = logging.getLogger(__name__)


class WebAuthnService:
    def __init__(self, enabled: bool, rp_id: str, rp_name: str):
        self.enabled = enabled
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.store_path = Path(
            os.getenv("WEBAUTHN_STORE_PATH", "/opt/auth-gateway/data/webauthn_store.json")
        )
        if not self.enabled:
            return

        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            fallback = Path(
                os.getenv("WEBAUTHN_STORE_FALLBACK_PATH", "./.auth_gateway_data/webauthn_store.json")
            )
            fallback.parent.mkdir(parents=True, exist_ok=True)
            _logger.warning(
                "No write permission for WebAuthn store '%s'. Falling back to '%s'.",
                self.store_path,
                fallback,
            )
            self.store_path = fallback

        if not self.store_path.exists():
            self.store_path.write_text(json.dumps({"challenges": {}, "credentials": {}}), encoding="utf-8")

    def _read(self) -> dict[str, Any]:
        return json.loads(self.store_path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]):
        self.store_path.write_text(json.dumps(data), encoding="utf-8")

    def registration_options(self, username: str) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False}
        challenge = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        data = self._read()
        data["challenges"][f"reg:{username}"] = challenge
        self._write(data)
        return {
            "enabled": True,
            "challenge": challenge,
            "rp": {"name": self.rp_name, "id": self.rp_id},
            "user": {
                "id": base64.urlsafe_b64encode(username.encode()).decode().rstrip("="),
                "name": username,
                "displayName": username,
            },
            "pubKeyCredParams": [{"alg": -7, "type": "public-key"}],
            "timeout": 60000,
            "attestation": "none",
        }

    def verify_registration(self, username: str, credential: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "verified": False}
        data = self._read()
        challenge = data["challenges"].get(f"reg:{username}")
        if not challenge:
            return {"enabled": True, "verified": False, "reason": "missing_challenge"}

        cred_id = credential.get("id")
        if not cred_id:
            return {"enabled": True, "verified": False, "reason": "missing_credential_id"}

        data["credentials"][username] = {
            "credential_id": cred_id,
            "raw": credential,
        }
        self._write(data)
        return {"enabled": True, "verified": True}

    def auth_options(self, username: str) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False}
        data = self._read()
        user_cred = data["credentials"].get(username)
        if not user_cred:
            return {"enabled": True, "has_credential": False}

        challenge = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        data["challenges"][f"auth:{username}"] = challenge
        self._write(data)
        return {
            "enabled": True,
            "has_credential": True,
            "challenge": challenge,
            "timeout": 60000,
            "rpId": self.rp_id,
            "allowCredentials": [{"id": user_cred["credential_id"], "type": "public-key"}],
            "userVerification": "preferred",
        }

    def verify_auth(self, username: str, credential: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "verified": False}
        data = self._read()
        challenge = data["challenges"].get(f"auth:{username}")
        user_cred = data["credentials"].get(username)
        if not challenge or not user_cred:
            return {"enabled": True, "verified": False}

        verified = credential.get("id") == user_cred.get("credential_id")
        return {"enabled": True, "verified": verified}
