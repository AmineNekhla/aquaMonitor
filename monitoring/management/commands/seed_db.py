"""
Populates the database with realistic aquaculture data for development and testing.
Note: the conditions for the main quality params are aligned with real conditions of species present is Souss-Massa farms (mussels,...)

Usage:
    python manage.py seed_db
    python manage.py seed_db --days 30 --clear

What it creates:
    - 1 admin + 3 farm managers
    - 3 farms (offshore mussel, net cage)
    - 3 ponds per farm
    - 6 sensors per pond
    - 30 days of realistic time-series sensor readings
    - ~15 realistic alerts with correct severity and CTAs
    - ~10 AI detection events
"""

import random
import math
from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from monitoring.models import (
    Profile, Farm, Pond, Sensor, SensorReading, Camera, AIDetection, Alert
)


#H: geneating parameters 

def generate_do(hour: int, day: int, base: float = 7.5) -> float:
    """
    DO follows a day/night photosynthesis cycle.
    Peaks at 2PM (photosynthesis), lowest at 03:00.
    """
    cycle = 1.2 * math.sin(math.pi * (hour - 3) / 12)
    noise = random.gauss(0, 0.25)
    trend = -0.004 * day
    raw = base + cycle + noise + trend
    return round(max(0.5, min(14.0, raw)), 3)


def generate_temp(hour: int, day: int, base: float) -> float:
    """
    Temperature has a daily cycle and slow seasonal trend.
    """
    daily_cycle = 0.8 * math.sin(math.pi * (hour - 6) / 12)
    seasonal = 0.04 * day
    noise = random.gauss(0, 0.15)
    return round(max(15.0, min(35.0, base + daily_cycle + seasonal + noise)), 3)


def generate_ph(hour: int, base: float, do_val: float) -> float:
    """
    pH correlates with DO (photosynthesis consumes CO2 → pH rises by day).
    """
    do_influence = (do_val - 6.0) * 0.05  # low DO pulls pH down
    cycle = 0.15 * math.sin(math.pi * (hour - 3) / 12)
    noise = random.gauss(0, 0.04)
    return round(max(5.5, min(9.5, base + cycle + do_influence + noise)), 3)


def generate_ammonia(hour: int, feeding_hours: list, stress: bool = False) -> float:
    """
    Ammonia spikes 1-2 hours after feeding, then decays.
    Feeding typically at 08:00 and 4:00PM.
    """
    base = 0.12 if not stress else 0.35
    spike = 0.0
    for fh in feeding_hours:
        hours_since = (hour - fh) % 24
        if 0 < hours_since <= 4:
            spike += 0.3 * math.exp(-hours_since * 0.7)
    noise = random.gauss(0, 0.02)
    return round(max(0.0, min(2.0, base + spike + noise)), 4)


def generate_turbidity(hour: int, base: float, stress: bool = False) -> float:
    """
    Turbidity is higher in afternoon (wind, feeding activity).
    """
    daily = 2.5 * math.sin(math.pi * (hour - 8) / 12)
    bloom_boost = random.uniform(8, 15) if stress else 0.0
    noise = random.gauss(0, 1.2)
    return round(max(0.5, min(60.0, base + daily + bloom_boost + noise)), 2)


def generate_nitrite(ammonia: float) -> float:
    """
    Nitrite is correlated with ammonia (nitrogen cycle lag).
    """
    base = ammonia * 0.28 + random.gauss(0, 0.04)
    return round(max(0.0, min(3.0, base)), 4)


def generate_salinity(base: float = 35.2, rain_event: bool = False) -> float:
    """Stable offshore salinity, drops slightly during simulated rain events."""
    drop = random.uniform(-2.5, -1.0) if rain_event else 0.0
    noise = random.gauss(0, 0.3)
    return round(max(28.0, min(40.0, base + drop + noise)), 2)
 
 
# ── Alert threshold checker ────────────────────────────────────────────────
 
def is_alert_condition(readings: dict):
    """
    Returns (should_alert, severity, alert_type, message, action)
    aligned with real marine aquaculture standards.
    """
    do        = readings.get("oxygen", 10.0)
    ammonia   = readings.get("ammonia",      0.0)
    ph        = readings.get("pH",           7.5)
    turbidity = readings.get("turbidity",   10.0)
    nitrite   = readings.get("nitrite",      0.0)
    temp      = readings.get("temperature", 24.0)

    if do < 3.0:
        return True, "critical", "oxygen", \
            f"Dissolved oxygen critically low: {do:.2f} mg/L — fish suffocation risk.", \
            "Activate aeration pump immediately. Stop feeding. Alert farm technician."
    if do < 5.5:
        return True, "warning", "oxygen", \
            f"Dissolved oxygen dropping: {do:.2f} mg/L — below safe threshold.", \
            "Check and increase aeration. Monitor every 30 minutes."
    if ammonia > 0.8:
        return True, "critical", "water_quality", \
            f"Ammonia critically high: {ammonia:.3f} mg/L — toxic to fish.", \
            "Stop feeding immediately. Perform 20% water change. Check biofiltration."
    if ammonia > 0.3:
        return True, "warning", "water_quality", \
            f"Ammonia elevated: {ammonia:.3f} mg/L — monitor closely.", \
            "Reduce feeding by 50%. Increase water flow."
    if ph < 6.8:
        return True, "critical", "water_quality", \
            f"pH critically low: {ph:.2f} — acid stress on fish.", \
            "Add buffering agent (lime or sodium bicarbonate). Check CO2 buildup."
    if ph < 7.0:
        return True, "warning", "water_quality", \
            f"pH slightly low: {ph:.2f} — approaching stress range.", \
            "Monitor pH trend. Prepare buffering agent."
    if ph > 9.0:
        return True, "warning", "water_quality", \
            f"pH high: {ph:.2f} — possible algal bloom.", \
            "Increase aeration. Check for algal bloom. Monitor chlorophyll."
    if turbidity > 40:
        return True, "critical", "pollution", \
            f"Turbidity critically high: {turbidity:.1f} NTU — visibility near zero.", \
            "Check for algal bloom or pollution event. Alert INRH. Consider harvest."
    if turbidity > 25:
        return True, "warning", "pollution", \
            f"Turbidity elevated: {turbidity:.1f} NTU.", \
            "Monitor water clarity. Check upstream current direction."
    if temp > 30:
        return True, "critical", "temperature", \
            f"Temperature critically high: {temp:.1f}°C — thermal stress.", \
            "Increase water circulation. Stop feeding. Monitor DO closely."
    if temp > 28:
        return True, "warning", "temperature", \
            f"Temperature elevated: {temp:.1f}°C.", \
            "Increase water flow. Monitor closely over next 2 hours."
    if nitrite > 1.5:
        return True, "critical", "water_quality", \
            f"Nitrite critically high: {nitrite:.3f} mg/L.", \
            "Stop feeding. Perform emergency partial water change."
    if nitrite > 0.8:
        return True, "warning", "water_quality", \
            f"Nitrite elevated: {nitrite:.3f} mg/L.", \
            "Reduce feeding rate. Improve biofiltration system."
 
    return False, None, None, None, None
 
 
# ── Pond profile definitions ───────────────────────────────────────────────
 
POND_PROFILES = {
    # Critical pond — chronic low oxygen, high temp
    "critical": {
        "base_do":   3.0,   # will regularly drop below 3.0 with cycle
        "base_temp": 29.5,
        "base_ph":   6.9,
        "base_turb": 42.0,
        "stress_prob": 0.35,  # 35% chance of stress any given day
    },
    # Warning pond — borderline conditions
    "warning": {
        "base_do":   5.2,
        "base_temp": 27.5,
        "base_ph":   7.1,
        "base_turb": 26.0,
        "stress_prob": 0.20,
    },
    # Healthy pond — normal conditions with occasional events
    "healthy": {
        "base_do":   7.8,
        "base_temp": 24.5,
        "base_ph":   7.8,
        "base_turb": 10.0,
        "stress_prob": 0.08,
    },
}
 
 
#H: main logic

class Command(BaseCommand):
    help = "Seed the database with realistic aquaculture data"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        days  = options["days"]
        clear = options["clear"]

        if clear:
            self.stdout.write("Clearing existing data...")
            Alert.objects.all().delete()
            AIDetection.objects.all().delete()
            SensorReading.objects.all().delete()
            Sensor.objects.all().delete()
            Camera.objects.all().delete()
            Pond.objects.all().delete()
            Farm.objects.all().delete()
            Profile.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()
            self.stdout.write(self.style.WARNING("Data cleared."))

        # ── Users ──────────────────────────────────────────────────────────
        self.stdout.write("Creating users...")

        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@aqua.ma", "is_staff": True, "is_superuser": True}
        )
        admin.set_password("admin321")
        admin.save()
        Profile.objects.get_or_create(user=admin, defaults={"role": "admin", "phone": "+212600000001"})

        manager1, _ = User.objects.get_or_create(
            username="Hajar_farm",
            defaults={"first_name": "Hajar", "last_name": "A", "email": "hajar@aqua.ma"}
        )
        manager1.set_password("farm126")
        manager1.save()
        Profile.objects.get_or_create(user=manager1, defaults={"role": "manager", "phone": "+212612345678"})

        manager2, _ = User.objects.get_or_create(
            username="Aymen_farm",
            defaults={"first_name": "Aymen", "last_name": "S", "email": "aymen@aqua.ma"}
        )
        manager2.set_password("farm226")
        manager2.save()
        Profile.objects.get_or_create(user=manager2, defaults={"role": "manager", "phone": "+212698765432"})
        
        manager3, _ = User.objects.get_or_create(
            username="Amine_farm",
            defaults={"first_name": "Amine", "last_name": "N", "email": "amine@aqua.ma"}
        )
        manager3.set_password("farm326")
        manager3.save()
        Profile.objects.get_or_create(user=manager3, defaults={"role": "manager", "phone": "+212698765433"})


        self.stdout.write(self.style.SUCCESS("  Users created."))

        # ── Farms ──────────────────────────────────────────────────────────
        self.stdout.write("Creating farms...")

        farm1, _ = Farm.objects.get_or_create(
            name="Ferme AquaLife Imiouadar",
            defaults={
                "owner":    manager1,
                "location": "Imiouadar, Souss-Massa, Maroc",
                "status":   "active",
            }
        )
        
        farm2, _ = Farm.objects.get_or_create(
            name="Agadir Blue Farm",
            defaults={
                "owner":    manager2,
                "location": "Agadir, Souss-Massa, Maroc",
                "status":   "active",
            }
        )

        farm3, _ = Farm.objects.get_or_create(
            name="Agadir Central Farm",
            defaults={
                "owner":    manager3,
                "location": "Agadir, Souss-Massa, Maroc",
                "status":   "active",
            }
        )

        self.stdout.write(self.style.SUCCESS("  Farms created."))

        #H: ponds' data, the species chosed are specific/aligned with the data conditions 
        self.stdout.write("Creating ponds...")

        # (farm, config, profile_key)
        pond_definitions = [
            # Farm 1 — Mussels (offshore)
            (farm1, {"name": "Zone A", "fish_species": "Mytilus galloprovincialis", "fish_count": 50000}, "critical"),
            (farm1, {"name": "Zone B", "fish_species": "Mytilus galloprovincialis", "fish_count": 45000}, "warning"),
            (farm1, {"name": "Zone C", "fish_species": "Mytilus galloprovincialis", "fish_count": 48000}, "healthy"),
            (farm2, {"name": "Cage 1", "fish_species": "Sparus aurata (Daurade)", "fish_count": 2000}, "healthy"),
            (farm2, {"name": "Cage 2", "fish_species": "Dicentrarchus labrax (Bar)", "fish_count": 1800}, "warning"),
            (farm2, {"name": "Cage 3", "fish_species": "Sparus aurata (Daurade)", "fish_count": 2200}, "healthy"),
            (farm3, {"name": "Bassin 1", "fish_species": "Sparus aurata (Alevins)",          "fish_count": 10000}, "warning"),
            (farm3, {"name": "Bassin 2", "fish_species": "Dicentrarchus labrax (Alevins)",   "fish_count": 8000},  "critical"),
            (farm3, {"name": "Bassin 3", "fish_species": "Sparus aurata (Alevins)",          "fish_count": 12000}, "healthy"),
        ]

        all_ponds = []
        pond_profiles_map = {}  # pond.id -> profile dict
 
        for farm, cfg, profile_key in pond_definitions:
            pond, _ = Pond.objects.get_or_create(farm=farm, name=cfg["name"], defaults={
                "fish_species": cfg["fish_species"],
                "fish_count":   cfg["fish_count"],
                "status":       "normal",
            })
            all_ponds.append(pond)
            pond_profiles_map[pond.id] = POND_PROFILES[profile_key]
 
        self.stdout.write(self.style.SUCCESS(f"  {len(all_ponds)} ponds created."))

        #H: sensors data
        self.stdout.write("Creating sensors...")

        sensor_types = [
            ("temperature", "°C"),
            ("oxygen",      "mg/L"),
            ("pH",          "pH"),
            ("turbidity",   "NTU"),
            ("salinity",    "ppt"),
        ]

        all_sensors = {}  # pond_id -> {sensor_type -> sensor}
        for pond in all_ponds:
            all_sensors[pond.id] = {}
            for stype, unit in sensor_types:
                device_code = f"{pond.farm.name[:3].upper()}-{pond.name[:1]}-{stype[:3].upper()}-{pond.id:03d}"
                sensor, _ = Sensor.objects.get_or_create(
                    device_code=device_code,
                    defaults={
                        "pond":         pond,
                        "sensor_type":  stype,
                        "unit":         unit,
                        "status":       "online",
                        "installed_at": "2024-01-01",
                    }
                )
                all_sensors[pond.id][stype] = sensor

        self.stdout.write(self.style.SUCCESS(f"  {len(all_ponds) * len(sensor_types)} sensors created."))

        #H:  Cameras 
        for pond in all_ponds[:3]:  # cameras only on first 3 ponds
            Camera.objects.get_or_create(
                pond=pond,
                name=f"Camera Underwater {pond.name}",
                defaults={
                    "stream_url":   f"rtsp://192.168.1.{10 + pond.id}/stream",
                    "status":       "online",
                    "installed_at": "2024-01-01",
                }
            )

        #H: sensors readings
        self.stdout.write(f"Generating {days} days of sensor readings...")

        now        = datetime.now()
        start_time = now - timedelta(days=days)
        feeding_hours = [8, 16]
        total_readings = 0

        for pond in all_ponds:
            sensors = all_sensors[pond.id]
            profile = pond_profiles_map[pond.id]
 
            base_do   = profile["base_do"]
            base_temp = profile["base_temp"]
            base_ph   = profile["base_ph"]
            base_turb = profile["base_turb"]
            stress_prob = profile["stress_prob"]

            readings_bulk    = []
            alerts_to_create = []
            alert_cooldown   = 0  # hours since last alert (avoid spam)
 
            for day_offset in range(days):
                # Day-level events
                is_stress_day = random.random() < stress_prob
                is_rain_day   = random.random() < 0.10  # 10% chance of rain
 
                for hour in range(24):
                    # Stress happens at night / early morning (worst time)
                    stress = is_stress_day and 1 <= hour <= 5
 
                    # Moving clock — each sensor fires at a slightly different second
                    base_time = start_time + timedelta(days=day_offset)

                    hour_base = base_time.replace(
                        hour=hour,
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59),
                        microsecond=0
                    )

                    moving_clock = hour_base
 
                    # Generate values
                    do_val   = generate_do(hour, day_offset, base_do)
                    if stress:
                        do_val = round(do_val * random.uniform(0.35, 0.55), 3)

                    temp_val = generate_temp(hour, day_offset, base_temp)
                    ph_val   = generate_ph(hour, base_ph, do_val)
                    amm_val  = generate_ammonia(hour, feeding_hours, stress)
                    turb_val = generate_turbidity(hour, base_turb, stress)
                    nit_val  = generate_nitrite(amm_val)
                    sal_val  = generate_salinity(35.2, is_rain_day and hour < 6)

                    param_map = {
                        "temperature": temp_val,
                        "oxygen":      do_val,
                        "pH":          ph_val,
                        "turbidity":   turb_val,
                        "salinity":    sal_val,
                    }
 
                    # Staggered timestamps — each sensor fires 5-30s after previous
                    for stype, value in param_map.items():
                        if stype in sensors:
                            jitter = random.randint(5, 30)
                            moving_clock += timedelta(seconds=jitter)
                            readings_bulk.append(SensorReading(
                                sensor=sensors[stype],
                                value=value,
                                recorded_at=moving_clock,
                            ))

                    # Alert logic — with cooldown to avoid flooding
                    alert_cooldown = max(0, alert_cooldown - 1)
                    readings_dict = {
                        "oxygen":      do_val,
                        "ammonia":     amm_val,
                        "pH":          ph_val,
                        "turbidity":   turb_val,
                        "temperature": temp_val,
                        "nitrite":     nit_val,
                    }
                    should_alert, severity, atype, message, action = is_alert_condition(readings_dict)
                    if should_alert and alert_cooldown == 0:
                        # Cooldown: critical = 4h, warning = 2h
                        alert_cooldown = 4 if severity == "critical" else 2
                        alerts_to_create.append(Alert(
                            pond=pond,
                            title=f"{atype.replace('_', ' ').title()} — {pond.name} ({pond.farm.name})",
                            alert_type=atype,
                            severity=severity,
                            message=message,
                            recommended_action=action,
                            status=random.choice(["open", "acknowledged", "resolved"]),
                            created_at=moving_clock,
                        ))

            # Bulk insert for performance
            SensorReading.objects.bulk_create(readings_bulk, batch_size=500)
            total_readings += len(readings_bulk)

            if alerts_to_create:
                Alert.objects.bulk_create(alerts_to_create)

            alert_badge = f" | {len(alerts_to_create)} alerts" if alerts_to_create else ""
            self.stdout.write(f"  {pond.farm.name} / {pond.name}: {len(readings_bulk)} readings{alert_badge}")

        # H: camera detetions
        self.stdout.write("Creating AI detections...")

        cameras = list(Camera.objects.all())
        detection_types = [
            ("Abnormal Fish Movement", "high",   "Fish swimming erratically near surface — possible oxygen stress."),
            ("Fish Crowding",          "medium",  "Unusual crowding detected — monitor water quality."),
            ("Surface Gulping",        "critical","Fish observed gulping at surface — critical oxygen depletion."),
            ("Lethargy Detected",      "high",     "Fish showing reduced movement — possible disease or hypoxia."),
            ("Normal Behavior",        "low",     "Fish movement patterns within normal range."),
        ]

        for dtype, risk, desc in detection_types * 2:
            pond = random.choice(all_ponds[:3])
            AIDetection.objects.create(
                pond=pond,
                camera=cameras[0] if cameras else None,
                detection_type=dtype,
                confidence_score=round(random.uniform(0.72, 0.98), 3),
                description=desc,
                prediction_text=f"Model confidence: {round(random.uniform(72, 98), 1)}%",
                risk_level=risk,
            )

        # ── Summary ────────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("Aqua Database Seeded Successfully"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"  Users:          {User.objects.count()}")
        self.stdout.write(f"  Farms:          {Farm.objects.count()}")
        self.stdout.write(f"  Ponds:          {Pond.objects.count()}")
        self.stdout.write(f"  Sensors:        {Sensor.objects.count()}")
        self.stdout.write(f"  Readings:       {total_readings:,}")
        self.stdout.write(f"  Alerts:         {Alert.objects.count()}")
        self.stdout.write(f"  AI Detections:  {AIDetection.objects.count()}")
        self.stdout.write("")
        self.stdout.write("  Login credentials:")
        self.stdout.write("    admin       / admin321  (superuser)")
        self.stdout.write("    Hajar_farm / farm126       (farm manager)")
        self.stdout.write("    Aymen_farm / farm226       (farm manager)")
        self.stdout.write("    Amine_farm / farm326       (farm manager)")
        
        
        
        # H: run the ai inference for the forcasting based on the previous data
        self.stdout.write("")
        self.stdout.write("Running AI inference on seeded ponds...")
 
        from monitoring.ai_client import check_ai_health
        from monitoring.ai_inference import run_inference_for_pond
 
        if not check_ai_health():
            self.stdout.write(self.style.WARNING(
                "  AI service not reachable — skipping AI inference.\n"
                "  Run manually after AI container starts:\n"
                "  python manage.py run_ai_inference"
            ))
        else:
            for pond in all_ponds:
                result = run_inference_for_pond(pond, save_forecast=True)
                status = result.get("status", "unknown")
                alert  = " [ALERT SAVED]" if result.get("alert_saved") else ""
                error  = result.get("error", "")
 
                if error:
                    self.stdout.write(self.style.ERROR(f"  {pond}: ERROR — {error}"))
                else:
                    style_fn = {
                        "Good":    self.style.SUCCESS,
                        "Warning": self.style.WARNING,
                        "Risk":    self.style.ERROR,
                    }.get(status, self.style.NOTICE)
                    self.stdout.write(style_fn(f"  {pond}: {status}{alert}"))
 
            self.stdout.write(self.style.SUCCESS("AI inference complete."))
            self.stdout.write(f"  Alerts in DB:        {Alert.objects.count()}")
            self.stdout.write(f"  AI Detections in DB: {AIDetection.objects.count()}")
        