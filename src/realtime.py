"""Real-time integration utilities for weather and traffic context."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OPEN_METEO_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
TOMTOM_FLOW_ENDPOINT = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _http_get_json(endpoint, params, timeout=8):
    query = urlencode(params, doseq=True)
    url = f"{endpoint}?{query}"

    request = Request(
        url=url,
        headers={"User-Agent": "urban-route-optimizer/1.0"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
        return json.loads(payload)
    except (HTTPError, URLError, TimeoutError) as exc:
        return {"_error": str(exc)}


def fetch_open_meteo_weather(latitude, longitude, timeout=8):
    """Fetch current weather snapshot from Open-Meteo (no API key required)."""
    payload = _http_get_json(
        OPEN_METEO_ENDPOINT,
        {
            "latitude": f"{float(latitude):.6f}",
            "longitude": f"{float(longitude):.6f}",
            "current": [
                "temperature_2m",
                "precipitation",
                "wind_speed_10m",
                "weather_code",
                "is_day",
            ],
            "timezone": "auto",
        },
        timeout=timeout,
    )

    if "_error" in payload:
        return {
            "ok": False,
            "source": "open-meteo",
            "error": payload["_error"],
        }

    current = payload.get("current") or {}
    if not current:
        return {
            "ok": False,
            "source": "open-meteo",
            "error": "No weather payload returned by provider",
        }

    return {
        "ok": True,
        "source": "open-meteo",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "temperature_c": float(current.get("temperature_2m", 0.0)),
        "precipitation_mm": float(current.get("precipitation", 0.0)),
        "wind_kmph": float(current.get("wind_speed_10m", 0.0)),
        "weather_code": int(current.get("weather_code", 0)),
        "is_day": bool(current.get("is_day", 1)),
    }


def estimate_weather_penalty_factor(weather_snapshot):
    """Convert weather conditions to a routing slowdown factor."""
    if not weather_snapshot or not weather_snapshot.get("ok"):
        return 1.0

    precipitation_mm = float(weather_snapshot.get("precipitation_mm", 0.0))
    wind_kmph = float(weather_snapshot.get("wind_kmph", 0.0))
    weather_code = int(weather_snapshot.get("weather_code", 0))

    penalty = 1.0

    if precipitation_mm >= 0.2:
        penalty += 0.08
    if precipitation_mm >= 1.0:
        penalty += 0.10
    if precipitation_mm >= 3.0:
        penalty += 0.12

    if wind_kmph >= 20.0:
        penalty += 0.05
    if wind_kmph >= 30.0:
        penalty += 0.08

    # Thunderstorms and heavy snow/rain conditions from WMO weather code families.
    if weather_code in {65, 67, 75, 82, 86, 95, 96, 99}:
        penalty += 0.10

    return _clamp(penalty, 1.0, 1.75)


def fetch_tomtom_traffic_flow(latitude, longitude, api_key, timeout=8):
    """Fetch live speed data from TomTom Flow API and convert to traffic level."""
    if not api_key:
        return {
            "ok": False,
            "source": "tomtom",
            "error": "Traffic API key not provided",
        }

    payload = _http_get_json(
        TOMTOM_FLOW_ENDPOINT,
        {
            "point": f"{float(latitude):.6f},{float(longitude):.6f}",
            "unit": "KMPH",
            "key": api_key,
        },
        timeout=timeout,
    )

    if "_error" in payload:
        return {
            "ok": False,
            "source": "tomtom",
            "error": payload["_error"],
        }

    segment = payload.get("flowSegmentData") or {}
    current_speed = float(segment.get("currentSpeed", 0.0))
    free_flow_speed = float(segment.get("freeFlowSpeed", 0.0))

    if current_speed <= 0.0 or free_flow_speed <= 0.0:
        return {
            "ok": False,
            "source": "tomtom",
            "error": "Invalid speed values from traffic provider",
        }

    congestion_factor = _clamp(free_flow_speed / max(current_speed, 1e-6), 1.0, 3.0)
    traffic_level = _clamp((congestion_factor - 1.0) * 1.5, 0.0, 3.0)

    return {
        "ok": True,
        "source": "tomtom",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "current_speed_kmph": current_speed,
        "free_flow_speed_kmph": free_flow_speed,
        "congestion_factor": congestion_factor,
        "traffic_level": traffic_level,
        "road_name": segment.get("frc", "unknown"),
    }


def build_realtime_context(
    start_point,
    end_point,
    enabled=False,
    weather_enabled=True,
    traffic_enabled=False,
    traffic_api_key=None,
    timeout=8,
):
    """Build a normalized context object consumed by routing logic."""
    context = {
        "enabled": bool(enabled),
        "weather_penalty_factor": 1.0,
        "traffic_level_override": None,
        "weather": None,
        "live_traffic": None,
        "notes": [],
    }

    if not enabled:
        return context

    center_lat = (float(start_point[0]) + float(end_point[0])) / 2.0
    center_lon = (float(start_point[1]) + float(end_point[1])) / 2.0

    if weather_enabled:
        weather = fetch_open_meteo_weather(center_lat, center_lon, timeout=timeout)
        context["weather"] = weather
        if weather.get("ok"):
            context["weather_penalty_factor"] = estimate_weather_penalty_factor(weather)
            context["notes"].append("Weather-integrated weighting enabled")
        else:
            context["notes"].append("Weather provider unavailable, using neutral weather factor")

    if traffic_enabled:
        live_traffic = fetch_tomtom_traffic_flow(
            center_lat,
            center_lon,
            api_key=traffic_api_key,
            timeout=timeout,
        )
        context["live_traffic"] = live_traffic
        if live_traffic.get("ok"):
            context["traffic_level_override"] = float(live_traffic["traffic_level"])
            context["notes"].append("Live traffic override active")
        else:
            context["notes"].append("Live traffic unavailable, using configured traffic level")

    return context
