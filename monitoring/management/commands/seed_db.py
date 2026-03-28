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
    cycle = math.sin(math.pi * (hour - 3) / 12) 
    noise = random.gauss(0, 0.3)
    trend = -0.005 * day  # slight long-term decline (pond aging)
    return round(max(1.5, min(14.0, base + 1.5 * cycle + noise + trend)), 3)


def generate_temp(hour: int, day: int, base: float = 24.5) -> float:
    """
    Temperature has a daily cycle and slow seasonal trend.
    """
    daily_cycle = 0.8 * math.sin(math.pi * (hour - 6) / 12)
    seasonal = 0.05 * day  # warming trend over 30 days
    noise = random.gauss(0, 0.2)
    return round(max(18.0, min(32.0, base + daily_cycle + seasonal + noise)), 3)


def generate_ph(hour: int, base: float = 7.8) -> float:
    """
    pH correlates with DO (photosynthesis consumes CO2 → pH rises by day).
    """
    cycle = 0.2 * math.sin(math.pi * (hour - 3) / 12)
    noise = random.gauss(0, 0.05)
    return round(max(6.5, min(9.0, base + cycle + noise)), 3)


def generate_ammonia(hour: int, feeding_hours: list) -> float:
    """
    Ammonia spikes 1-2 hours after feeding, then decays.
    Feeding typically at 08:00 and 4:00PM.
    """
    base = 0.08
    spike = 0.0
    for fh in feeding_hours:
        hours_since = (hour - fh) % 24
        if 0 < hours_since <= 3:
            spike += 0.25 * math.exp(-hours_since * 0.8)
    noise = random.gauss(0, 0.02)
    return round(max(0.0, min(2.0, base + spike + noise)), 4)


def generate_turbidity(hour: int, base: float = 12.0) -> float:
    """
    Turbidity is higher in afternoon (wind, feeding activity).
    """
    daily = 3.0 * math.sin(math.pi * (hour - 8) / 12)
    noise = random.gauss(0, 1.5)
    return round(max(0.5, min(50.0, base + daily + noise)), 2)


def generate_nitrite(ammonia: float) -> float:
    """
    Nitrite is correlated with ammonia (nitrogen cycle lag).
    """
    base = ammonia * 0.3 + random.gauss(0, 0.05)
    return round(max(0.0, min(3.0, base)), 4)


def is_alert_condition(readings: dict) -> tuple:
    """
    Check if readings cross alert thresholds.
    Returns (should_alert, severity, alert_type, message, action)
    """
    do        = readings.get("oxygen", 10)
    ammonia   = readings.get("ammonia", 0)
    ph        = readings.get("pH", 7.5)
    turbidity = readings.get("turbidity", 10)
    nitrite   = readings.get("nitrite", 0)
    temp      = readings.get("temperature", 24)

    if do < 3.0:
        return True, "critical", "oxygen", \
            f"Dissolved oxygen critically low: {do:.2f} mg/L", \
            "Activate aeration pump immediately. Stop feeding."
    if do < 5.5:
        return True, "warning", "oxygen", \
            f"Dissolved oxygen dropping: {do:.2f} mg/L", \
            "Check and increase aeration system."
    if ammonia > 0.8:
        return True, "critical", "water_quality", \
            f"Ammonia critically high: {ammonia:.3f} mg/L", \
            "Stop feeding immediately. Perform partial water change."
    if ph < 6.8:
        return True, "critical", "water_quality", \
            f"pH critically low: {ph:.2f}", \
            "Add buffering agent. Check CO2 levels."
    if turbidity > 35:
        return True, "warning", "pollution", \
            f"Turbidity elevated: {turbidity:.1f} NTU", \
            "Monitor water clarity. Check for algal bloom or upstream pollution."
    if temp > 30:
        return True, "warning", "temperature", \
            f"Temperature elevated: {temp:.1f}°C", \
            "Increase water circulation. Monitor closely."
    if nitrite > 1.5:
        return True, "warning", "water_quality", \
            f"Nitrite elevated: {nitrite:.3f} mg/L", \
            "Reduce feeding rate. Improve biofiltration."

    return False, None, None, None, None


#H: main logic

class Command(BaseCommand):
    help = "Seed the database with realistic aquaculture data"

    def add_arguments(self, parser):
        parser.add_argument("--days",  type=int, default=30,
                            help="Number of days of sensor data to generate")
        parser.add_argument("--clear", action="store_true",
                            help="Clear existing data before seeding")

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

        pond_configs = [
            {"name": "Zone A", "fish_species": "Mytilus galloprovincialis", "fish_count": 50000},
            {"name": "Zone B", "fish_species": "Mytilus galloprovincialis", "fish_count": 45000},
            {"name": "Zone C", "fish_species": "Mytilus galloprovincialis", "fish_count": 48000},
        ]

        cage_configs = [
            {"name": "Cage 1", "fish_species": "Sparus aurata (Daurade)", "fish_count": 2000},
            {"name": "Cage 2", "fish_species": "Dicentrarchus labrax (Bar)", "fish_count": 1800},
            {"name": "Cage 3", "fish_species": "Sparus aurata (Daurade)", "fish_count": 2200},
        ]
        
        hatchery_configs = [
            {"name": "Bassin 1", "fish_species": "Sparus aurata (Alevins)", "fish_count": 10000},
            {"name": "Bassin 2", "fish_species": "Dicentrarchus labrax (Alevins)", "fish_count": 8000},
            {"name": "Bassin 3", "fish_species": "Sparus aurata (Alevins)", "fish_count": 12000},
        ]

        all_ponds = []
        for cfg in pond_configs:
            pond, _ = Pond.objects.get_or_create(farm=farm1, name=cfg["name"], defaults={
                "fish_species": cfg["fish_species"],
                "fish_count":   cfg["fish_count"],
                "status":       "normal",
            })
            all_ponds.append(pond)

        for cfg in cage_configs:
            pond, _ = Pond.objects.get_or_create(farm=farm2, name=cfg["name"], defaults={
                "fish_species": cfg["fish_species"],
                "fish_count":   cfg["fish_count"],
                "status":       "normal",
            })
            all_ponds.append(pond)
        
        for cfg in hatchery_configs:
            pond, _ = Pond.objects.get_or_create(farm=farm3, name=cfg["name"], defaults={
                "fish_species": cfg["fish_species"],
                "fish_count":   cfg["fish_count"],
                "status":       "normal",
            })
            all_ponds.append(pond)

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

        now        = datetime.now(timezone.utc)
        start_time = now - timedelta(days=days)
        feeding_hours = [8, 16]
        total_readings = 0
        alert_count    = 0

        for pond in all_ponds:
            sensors = all_sensors[pond.id]
            if "Zone A" in pond.name:
                # High Risk Pond: Low Oxygen & High Temp
                pond_base_do = random.uniform(3.2, 4.2)  
                pond_base_temp = random.uniform(28.5, 30.5)
                pond_base_ph = 6.5
                pond_base_turb = 45.0
            elif "Cage 2" in pond.name:
                # Warning Pond: High Turbidity & fluctuating pH
                pond_base_do = 6.0
                pond_base_temp = 25.0
                pond_base_ph = random.uniform(6.8, 7.2)
                pond_base_turb = 38.0
            else:
                # Normal healthy baseline
                pond_base_do = random.uniform(6.5, 8.5)
                pond_base_temp = random.uniform(23.0, 26.0)
                pond_base_ph = random.uniform(7.4, 8.0)
                pond_base_turb = random.uniform(8.0, 18.0)

            readings_bulk = []
            alerts_to_create = []

            for day_offset in range(days):
                for hour in range(24):
                    # We add a random minute and second so they look sequential 
                    # instead of stacked on the hour
                    ts = start_time + timedelta(
                        days=day_offset, 
                        hours=hour,
                        minutes=random.randint(0, 59),
                        seconds=random.randint(0, 59)
                    )

                    # Simulate occasional stress events (day 10, 20)
                    stress = day_offset in [10, 20] and 2 <= hour <= 6

                    do_val   = generate_do(hour, day_offset, pond_base_do)
                    if stress:
                        do_val = round(do_val * 0.45, 3)  # oxygen crash

                    temp_val = generate_temp(hour, day_offset, pond_base_temp)
                    ph_val   = generate_ph(hour, pond_base_ph)
                    amm_val  = generate_ammonia(hour, feeding_hours)
                    turb_val = generate_turbidity(hour, pond_base_turb)
                    nit_val  = generate_nitrite(amm_val)

                    param_map = {
                        "temperature": temp_val,
                        "oxygen":      do_val,
                        "pH":          ph_val,
                        "turbidity":   turb_val,
                        "salinity":    round(random.gauss(35.2, 0.4), 2),
                    }

                    for stype, value in param_map.items():
                        if stype in sensors:
                            readings_bulk.append(SensorReading(
                                sensor=sensors[stype],
                                value=value,
                                recorded_at=ts,
                            ))

                    # Check for alert conditions
                    readings_dict = {
                        "oxygen":      do_val,
                        "ammonia":     amm_val,
                        "pH":          ph_val,
                        "turbidity":   turb_val,
                        "temperature": temp_val,
                        "nitrite":     nit_val,
                    }
                    should_alert, severity, atype, message, action = is_alert_condition(readings_dict)
                    if should_alert and random.random() < 0.15:  # don't create alert every hour
                        alerts_to_create.append(Alert(
                            pond=pond,
                            title=f"{atype.replace('_', ' ').title()} Alert — {pond.name}",
                            alert_type=atype,
                            severity=severity,
                            message=message,
                            recommended_action=action,
                            status=random.choice(["open", "acknowledged", "resolved"]),
                            created_at=ts,
                        ))
                        alert_count += 1

            # Bulk insert for performance
            SensorReading.objects.bulk_create(readings_bulk, batch_size=500)
            total_readings += len(readings_bulk)

            if alerts_to_create:
                Alert.objects.bulk_create(alerts_to_create[:5])  # max 5 per pond

            self.stdout.write(f"  {pond.farm.name} / {pond.name}: {len(readings_bulk)} readings")

        # H: camera detetions
        self.stdout.write("Creating AI detections...")

        cameras = list(Camera.objects.all())
        detection_types = [
            ("Abnormal Fish Movement", "high",   "Fish swimming erratically near surface — possible oxygen stress."),
            ("Fish Crowding",          "medium",  "Unusual crowding detected in zone B — monitor water quality."),
            ("Surface Gulping",        "critical","Fish observed gulping at surface — critical oxygen depletion likely."),
            ("Normal Behavior",        "low",     "Fish movement patterns within normal range."),
        ]

        for i, (dtype, risk, desc) in enumerate(detection_types * 3):
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
        self.stdout.write("    Hajar.farm / farm126       (farm manager)")
        self.stdout.write("    Aymen.farm / farm226       (farm manager)")
        self.stdout.write("    Amine.farm / farm326       (farm manager)")
        
        
        
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
        