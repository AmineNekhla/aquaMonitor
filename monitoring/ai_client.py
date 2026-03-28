"""
monitoring/ai_client.py
Django utility to call the Aqua AI microservice.
Usage:
    from monitoring.ai_client import get_current_status, get_forecast
"""

import os
import httpx
from typing import Optional

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")
TIMEOUT = 10.0


def get_current_status(
    temp: float,
    turbidity: float,
    do: float,
    ph: float,
    ammonia: float,
    nitrite: float,
) -> Optional[dict]:
    """
    Call Model 1 — classify current water quality.
    Returns dict with current_status, confidence, issues, actions, probabilities.
    Returns None on failure.
    """
    try:
        response = httpx.post(
            f"{AI_SERVICE_URL}/predict/current",
            json={
                "temp": temp,
                "turbidity": turbidity,
                "do": do,
                "ph": ph,
                "ammonia": ammonia,
                "nitrite": nitrite,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[Aqua AI] current status error: {e}")
        return None


def get_forecast(
    history: list,
    current_ammonia: float,
    current_nitrite: float,
    current_turbidity: float,
    n_hours: int = 6,
) -> Optional[dict]:
    """
    Call Model 2 — recursive 6-hour forecast.
    history: list of 24 dicts with keys temp, do, ph, ammonia
    Returns dict with forecast list (hour, temp, do, ph, status, issues, actions).
    Returns None on failure.
    """
    try:
        response = httpx.post(
            f"{AI_SERVICE_URL}/predict/forecast",
            json={
                "history": history,
                "current_ammonia": current_ammonia,
                "current_nitrite": current_nitrite,
                "current_turbidity": current_turbidity,
                "n_hours": n_hours,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[Aqua AI] forecast error: {e}")
        return None


def check_ai_health() -> bool:
    """Check if the AI service is reachable."""
    try:
        response = httpx.get(f"{AI_SERVICE_URL}/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False