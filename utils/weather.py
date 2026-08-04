# -*- coding: utf-8 -*-
"""
utils/weather.py
================
Enterprise weather and IP geolocation telemetry service.
Automatically resolves device coordinates via public IP routing and retrieves
ambient outdoor climate metrics from Open-Meteo (no API keys required).
Provides dynamic thermodynamic threshold scaling to prevent false alarms during
extreme ambient weather conditions (e.g. high monsoon humidity or winter dropouts).
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests

from config import ALERT_HUMID_HIGH, ALERT_HUMID_LOW, ALERT_TEMP_HIGH, ALERT_TEMP_LOW
from utils.logger import get_logger
from utils.network import build_http_session

logger = get_logger(__name__)

# WMO Weather interpretation codes (http://open-meteo.com/en/docs)
_WMO_DESCRIPTIONS: Dict[int, str] = {
    0: "Clear Sky",
    1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing Rime Fog",
    51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Dense Drizzle",
    61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
    71: "Slight Snow", 73: "Moderate Snow", 75: "Heavy Snow",
    80: "Slight Rain Showers", 81: "Moderate Rain Showers", 82: "Violent Rain Showers",
    95: "Thunderstorm", 96: "Thunderstorm with Hail",
}


class WeatherService:
    """Retailing local weather data with intelligent in-memory caching and resilient fallback."""

    def __init__(self, cache_ttl_seconds: int = 900) -> None:
        self._session = build_http_session(total=2, backoff=0.5)
        self._cache_ttl = cache_ttl_seconds
        self._last_weather_fetch: float = 0.0
        self._cached_weather: Dict[str, Any] = {
            "city": "Unknown Location",
            "lat": 0.0,
            "lon": 0.0,
            "temperature": 25.0,
            "humidity": 65.0,
            "description": "Unavailable",
            "valid": False,
        }
        self._location_resolved: bool = False

    def _resolve_location(self) -> None:
        """Resolve geographical coordinates via public IP routing."""
        if self._location_resolved and self._cached_weather.get("lat") != 0.0:
            return

        try:
            resp = self._session.get("http://ip-api.com/json/", timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    city = data.get("city", "Unknown")
                    country = data.get("countryCode", "")
                    self._cached_weather["city"] = f"{city}, {country}".strip(", ")
                    self._cached_weather["lat"] = float(data.get("lat", 0.0))
                    self._cached_weather["lon"] = float(data.get("lon", 0.0))
                    self._location_resolved = True
                    logger.info("Auto-IP geolocation resolved: %s (%.4f, %.4f)", self._cached_weather["city"], self._cached_weather["lat"], self._cached_weather["lon"])
        except Exception as exc:
            logger.debug("IP geolocation unreachable (offline or filtered): %s", exc)

    def get_current_conditions(self) -> Dict[str, Any]:
        """Fetch ambient external weather conditions, utilizing cached values within TTL."""
        now = time.time()
        if now - self._last_weather_fetch < self._cache_ttl and self._cached_weather.get("valid"):
            return self._cached_weather

        self._resolve_location()
        lat = self._cached_weather.get("lat", 0.0)
        lon = self._cached_weather.get("lon", 0.0)

        if not self._location_resolved or (lat == 0.0 and lon == 0.0):
            self._cached_weather["valid"] = False
            return self._cached_weather

        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}&current=temperature_2m,relative_humidity_2m,weather_code"
        try:
            resp = self._session.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                curr = data.get("current", {})
                w_code = int(curr.get("weather_code", -1))
                self._cached_weather["temperature"] = float(curr.get("temperature_2m", 25.0))
                self._cached_weather["humidity"] = float(curr.get("relative_humidity_2m", 65.0))
                self._cached_weather["description"] = _WMO_DESCRIPTIONS.get(w_code, "Nominal Conditions")
                self._cached_weather["valid"] = True
                self._last_weather_fetch = now
                logger.debug("Ambient weather refreshed: %s, %.1f°C, %.1f%% RH", self._cached_weather["description"], self._cached_weather["temperature"], self._cached_weather["humidity"])
        except Exception as exc:
            logger.warning("Open-Meteo weather sync failed, serving last known readings: %s", exc)

        return self._cached_weather

    @staticmethod
    def get_adaptive_thresholds(ambient: Dict[str, Any]) -> Dict[str, float]:
        """Calculate dynamic internal climate tolerances based on external outdoor weather.

        In industrial IoT telemetry, fixed thresholds generate persistent false alarms
        during heavy seasonal rainfall or cold weather fronts. This adaptive routine bridges
        thermodynamic differentials between external ambience and internal hive stability.
        """
        base_t_high, base_t_low = ALERT_TEMP_HIGH, ALERT_TEMP_LOW
        base_h_high, base_h_low = ALERT_HUMID_HIGH, ALERT_HUMID_LOW

        if not ambient or not ambient.get("valid"):
            return {
                "temp_high": base_t_high,
                "temp_low": base_t_low,
                "humid_high": base_h_high,
                "humid_low": base_h_low,
            }

        out_temp = float(ambient.get("temperature", 25.0))
        out_humid = float(ambient.get("humidity", 65.0))

        # Dynamically scale allowable limits based on thermodynamic differential
        # In hot summers, allow internal heat up to ambient + 12°C before alerting
        # In cool mornings/monsoons, allow internal drops to ambient - 10°C
        dyn_t_high = max(base_t_high, out_temp + 12.0)
        dyn_t_low = min(base_t_low, out_temp - 8.0)

        # In damp weather or heavy rain (outdoor > 80% RH), allow internal humidity up to 96%
        # without spamming false alarms.
        dyn_h_high = max(base_h_high, min(96.0, out_humid + 15.0))
        dyn_h_low = min(base_h_low, max(20.0, out_humid - 35.0))

        return {
            "temp_high": round(dyn_t_high, 1),
            "temp_low": round(dyn_t_low, 1),
            "humid_high": round(dyn_h_high, 1),
            "humid_low": round(dyn_h_low, 1),
        }


# Global singleton service for uniform app consumption
weather_service = WeatherService()
