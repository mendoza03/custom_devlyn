from __future__ import annotations

from typing import Any
import requests
from user_agents import parse as parse_ua


def enrich_user_agent(telemetry: dict[str, Any]) -> dict[str, Any]:
    user_agent = telemetry.get("user_agent") or ""
    if user_agent:
        ua = parse_ua(user_agent)
        telemetry.setdefault("browser", f"{ua.browser.family} {ua.browser.version_string}".strip())
        telemetry.setdefault("os", f"{ua.os.family} {ua.os.version_string}".strip())
        if ua.is_mobile:
            telemetry.setdefault("device_type", "mobile")
        elif ua.is_tablet:
            telemetry.setdefault("device_type", "tablet")
        elif ua.is_pc:
            telemetry.setdefault("device_type", "desktop")
        else:
            telemetry.setdefault("device_type", "other")
    return telemetry


def enrich_geo_by_ip(telemetry: dict[str, Any]) -> dict[str, Any]:
    ip = telemetry.get("ip_public")
    if not ip:
        return telemetry
    if telemetry.get("country") and telemetry.get("city"):
        return telemetry

    try:
        response = requests.get(f"https://ipwho.is/{ip}", timeout=3)
        if response.ok:
            data = response.json()
            if data.get("success"):
                if not telemetry.get("country"):
                    telemetry["country"] = data.get("country")
                if not telemetry.get("city"):
                    telemetry["city"] = data.get("city")
                connection = data.get("connection") or {}
                if not telemetry.get("isp"):
                    telemetry["isp"] = connection.get("isp")
                if not telemetry.get("asn"):
                    telemetry["asn"] = connection.get("asn")
    except Exception:
        pass

    if telemetry.get("country") and telemetry.get("city"):
        return telemetry

    # Secondary fallback if the primary GeoIP service is unavailable.
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
        if response.ok:
            data = response.json()
            if not telemetry.get("country"):
                telemetry["country"] = data.get("country")
            if not telemetry.get("city"):
                telemetry["city"] = data.get("city")
            if not telemetry.get("isp"):
                telemetry["isp"] = data.get("isp")
            if not telemetry.get("asn"):
                telemetry["asn"] = data.get("as")
    except Exception:
        pass
    return telemetry
