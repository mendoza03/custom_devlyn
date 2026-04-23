import json
import urllib.parse
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class OdooService:
    base_url: str
    db_name: str
    oauth_provider_id: int
    event_ingest_url: str
    user_context_url: str
    api_key: str

    def build_oauth_state(self, redirect: str) -> str:
        absolute_redirect = redirect
        if not absolute_redirect.startswith(("http://", "https://")):
            absolute_redirect = urllib.parse.urljoin(self.base_url.rstrip("/") + "/", redirect.lstrip("/"))
        state = {
            "d": self.db_name,
            "p": self.oauth_provider_id,
            "r": urllib.parse.quote_plus(absolute_redirect),
        }
        return json.dumps(state)

    def build_oauth_redirect(self, access_token: str, redirect: str = "/odoo") -> str:
        state = self.build_oauth_state(redirect)
        fragment = urllib.parse.urlencode(
            {
                "access_token": access_token,
                "state": state,
            }
        )
        return f"{self.base_url.rstrip('/')}/auth_oauth/signin#{fragment}"

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Biometric-API-Key": self.api_key,
        }

    def post_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = self._headers()
        try:
            resp = requests.post(self.event_ingest_url, json=payload, headers=headers, timeout=5)
        except requests.RequestException as exc:
            raise RuntimeError(f"Odoo event ingest transport error: {exc}") from exc
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001
            data = {}
        if not isinstance(data, dict):
            data = {}
        data["_status_code"] = resp.status_code
        if not resp.ok:
            data["ok"] = False
            return data
        data.setdefault("ok", True)
        return data

    def fetch_user_context(self, login: str) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "X-Biometric-API-Key": self.api_key,
        }
        try:
            resp = requests.post(self.user_context_url, json={"login": login}, headers=headers, timeout=5)
        except requests.RequestException as exc:
            raise RuntimeError(f"Odoo user context transport error: {exc}") from exc
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001
            data = {}
        if not resp.ok:
            message = data.get("error") or resp.text
            raise RuntimeError(f"Odoo user context failed ({resp.status_code}): {message}")
        return data
