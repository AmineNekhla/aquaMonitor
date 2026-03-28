"""
For automatic db seeding using the ai models  results: 

Calls the Aqua AI service and saves results to the database.

Usage (manual):
    from monitoring.ai_inference import run_inference_for_pond
    run_inference_for_pond(pond)

Usage (management command):
    python manage.py run_ai_inference
    python manage.py run_ai_inference --pond-id 1
"""

import logging
from datetime import datetime, timedelta, timezone
from django.utils import timezone as django_tz

from monitoring.models import Pond, Sensor, SensorReading, Alert, AIDetection, Forecast
from monitoring.ai_client import get_current_status, get_forecast

logger = logging.getLogger(__name__)

# ── Sensor type mapping ────────────────────────────────────────────────────

SENSOR_MAP = {
    "temperature": "temp",
    "oxygen":      "do",
    "pH":          "ph",
    "turbidity":   "turbidity",
    "salinity":    "salinity",
}

ALERT_TYPE_MAP = {
    "DO dropping":           "oxygen",
    "DO critically low":     "oxygen",
    "Temperature":           "temperature",
    "Ammonia":               "water_quality",
    "pH":                    "water_quality",
    "Turbidity":             "pollution",
    "Nitrite":               "water_quality",
    "Multiple parameters":   "other",
}


def get_latest_readings(pond: "Pond") -> dict:
    """
    Get the most recent reading for each sensor in this pond.
    Returns: {sensor_type: value}
    """
    readings = {}
    for sensor in pond.sensors.filter(status="online"):
        latest = sensor.readings.order_by("-recorded_at").first()
        if latest:
            key = SENSOR_MAP.get(sensor.sensor_type, sensor.sensor_type)
            readings[key] = float(latest.value)
    return readings


def get_history_readings(pond: "Pond", hours: int = 24) -> list:
    """
    Get last N hours of readings for Model 2 (LSTM forecast).
    Returns list of 24 dicts with temp/do/ph/ammonia — one per hour.
    """
    now   = django_tz.now()
    since = now - timedelta(hours=hours)

    history = []
    for h in range(hours):
        hour_start = since + timedelta(hours=h)
        hour_end   = hour_start + timedelta(hours=1)

        hour_readings = {}
        for sensor in pond.sensors.filter(
            status="online",
            sensor_type__in=["temperature", "oxygen", "pH"]
        ):
            reading = sensor.readings.filter(
                recorded_at__gte=hour_start,
                recorded_at__lt=hour_end
            ).order_by("-recorded_at").first()

            if reading:
                key = SENSOR_MAP.get(sensor.sensor_type)
                if key:
                    hour_readings[key] = float(reading.value)

        # Only add if we have all required fields
        if all(k in hour_readings for k in ["temp", "do", "ph"]):
            hour_readings.setdefault("ammonia", 0.1)
            history.append(hour_readings)

    # Pad or trim to exactly 24 entries
    if len(history) < 24:
        # Pad with last known values if not enough history
        pad = history[-1] if history else {"temp": 25.0, "do": 7.0, "ph": 7.8, "ammonia": 0.1}
        while len(history) < 24:
            history.insert(0, pad)
    else:
        history = history[-24:]

    return history


def determine_alert_type(issues: str) -> str:
    """Map issue text to Alert.alert_type choice."""
    for keyword, atype in ALERT_TYPE_MAP.items():
        if keyword.lower() in issues.lower():
            return atype
    return "other"


def status_to_severity(status: str) -> str:
    """Map Model 1 output to Alert.severity choice."""
    return {
        "Good":    "info",
        "Warning": "warning",
        "Risk":    "critical",
    }.get(status, "warning")


def status_to_pond_status(status: str) -> str:
    """Map Model 1 output to Pond.status choice."""
    return {
        "Good":    "normal",
        "Warning": "warning",
        "Risk":    "critical",
    }.get(status, "normal")


#H: the core

def run_inference_for_pond(pond: "Pond", save_forecast: bool = True) -> dict:
    """
    logic: 
    
    1. Get latest sensor readings for this pond
    2. Call Model 1 — classify current status
    3. Save Alert if Warning or Risk
    4. Call Model 2 — get 6-hour forecast
    5. Save forecast for each predicted Risk hour
    6. Update pond status
    Returns summary dict.
    """
    result = {
        "pond":         str(pond),
        "status":       None,
        "alert_saved":  False,
        "forecast":     None,
        "error":        None,
    }

    # ── Step 1: Get current sensor readings ───────────────────────────────
    readings = get_latest_readings(pond)
    if not readings:
        result["error"] = "No sensor readings available"
        logger.warning(f"[{pond}] No readings found.")
        return result

    temp      = readings.get("temp",      25.0)
    turbidity = readings.get("turbidity", 10.0)
    do        = readings.get("do",         7.0)
    ph        = readings.get("ph",         7.8)
    ammonia   = readings.get("ammonia",    0.1)
    nitrite   = readings.get("nitrite",    0.1)

    # ── Step 2: Call Model 1 ───────────────────────────────────────────────
    current = get_current_status(temp, turbidity, do, ph, ammonia, nitrite)
    if not current:
        result["error"] = "AI service unreachable"
        logger.error(f"[{pond}] AI service call failed.")
        return result

    status   = current["current_status"]
    issues   = current["issues"]
    actions  = current["actions"]
    result["status"] = status

    # ── Step 3: Update pond status ─────────────────────────────────────────
    pond.status = status_to_pond_status(status)
    pond.save(update_fields=["status", "last_updated"])

    # ── Step 4: Save Alert if not Good ────────────────────────────────────
    if status in ("Warning", "Risk"):
        # Avoid duplicate alerts — check if same alert exists in last 2 hours
        two_hours_ago = django_tz.now() - timedelta(hours=2)
        duplicate = Alert.objects.filter(
            pond=pond,
            alert_type=determine_alert_type(issues),
            severity=status_to_severity(status),
            created_at__gte=two_hours_ago,
        ).exists()

        if not duplicate:
            Alert.objects.create(
                pond=pond,
                title=f"{status} — {pond.name} ({pond.farm.name})",
                alert_type=determine_alert_type(issues),
                severity=status_to_severity(status),
                message=issues,
                recommended_action=actions,
                status="open",
            )
            result["alert_saved"] = True
            logger.info(f"[{pond}] Alert created: {status} — {issues[:80]}")

   # ── Step 5: Call Model 2 and save Forecast objects ────────────────────────
    if save_forecast:
        history = get_history_readings(pond, hours=24)
        forecast_data = get_forecast(
            history=history,
            current_ammonia=ammonia,
            current_nitrite=nitrite,
            current_turbidity=turbidity,
            n_hours=6,
        )

        if forecast_data:
            result["forecast"] = forecast_data["forecast"]
            now = django_tz.now()

            for hour_pred in forecast_data["forecast"]:
                target_time = now + timedelta(hours=hour_pred["hour"])

                # Save or update forecast
                Forecast.objects.update_or_create(
                    pond=pond,
                    target_time=target_time.replace(minute=0, second=0, microsecond=0),
                    defaults={
                        "hour_offset": hour_pred["hour"],
                        "temp":        hour_pred["temp"],
                        "do":          hour_pred["do"],
                        "ph":          hour_pred["ph"],
                        "ammonia":     ammonia,
                        "status":      hour_pred["status"],
                        "issues":      hour_pred.get("issues", ""),
                        "actions":     hour_pred.get("actions", ""),
                    }
                )

                # Also save AIDetection only for Risk hours
                if hour_pred["status"] == "Risk":
                    AIDetection.objects.create(
                        pond=pond,
                        camera=None,
                        detection_type="Predicted Water Quality Risk",
                        confidence_score=0.85,
                        description=(
                            f"Risk predicted in {hour_pred['hour']} hour(s). "
                            f"DO: {hour_pred['do']} mg/L | pH: {hour_pred['ph']} | "
                            f"Temp: {hour_pred['temp']}°C"
                        ),
                        prediction_text=hour_pred["issues"],
                        risk_level="high",
                    )
                
    logger.info(f"[{pond}] Inference complete — status: {status}")
    return result


def run_inference_all_ponds(save_forecast: bool = True) -> list:
    """Run inference for all active ponds across all farms."""
    ponds = Pond.objects.filter(farm__status="active").select_related("farm")
    results = []
    for pond in ponds:
        result = run_inference_for_pond(pond, save_forecast=save_forecast)
        results.append(result)
    return results