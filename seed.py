import os
import django
from django.utils import timezone
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquaculture.settings')
django.setup()

from django.contrib.auth import get_user_model
from monitoring.models import Farm, Pond, Sensor, SensorReading, Alert

User = get_user_model()

def seed(username='admin', password='adminpass'):
    # Get or create superuser
    user, created = User.objects.get_or_create(username=username, defaults={'email': f"{username}@example.com"})
    if created:
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print(f"Created admin user: {username}")

    # Reset Data
    Farm.objects.all().delete()
    print("Cleaned up old farms.")

    # Create Farms
    farm1 = Farm.objects.create(owner=user, name="Blue Waters Facility", location="Coastal Zone A", latitude=33.5731, longitude=-7.5898)
    farm2 = Farm.objects.create(owner=user, name="Inland Breeder Hub", location="Inland Region B", latitude=30.4278, longitude=-9.5925)

    # Create Ponds
    pond1 = Pond.objects.create(
        farm=farm1, name="Pond Alpha", fish_species="Atlantic Salmon",
        fish_count=12000, status="normal"
    )
    pond2 = Pond.objects.create(
        farm=farm1, name="Pond Beta", fish_species="Atlantic Salmon",
        fish_count=9500, status="warning"
    )
    pond3 = Pond.objects.create(
        farm=farm2, name="Pond Gamma", fish_species="Rainbow Trout",
        fish_count=15000, status="critical"
    )

    now = timezone.now()
    # Create Sensors
    p1_temp = Sensor.objects.create(pond=pond1, sensor_type="temperature", device_code="TMP-A01", unit="°C", status="online", installed_at=now.date())
    p1_do = Sensor.objects.create(pond=pond1, sensor_type="oxygen", device_code="DO-A01", unit="mg/L", status="online", installed_at=now.date())
    
    p2_temp = Sensor.objects.create(pond=pond2, sensor_type="temperature", device_code="TMP-B01", unit="°C", status="online", installed_at=now.date())
    p2_do = Sensor.objects.create(pond=pond2, sensor_type="oxygen", device_code="DO-B01", unit="mg/L", status="faulty", installed_at=now.date())

    p3_temp = Sensor.objects.create(pond=pond3, sensor_type="temperature", device_code="TMP-G01", unit="°C", status="offline", installed_at=now.date())

    # Create Readings
    for i in range(24):
        time = now - timezone.timedelta(hours=i)
        
        # Pond 1
        SensorReading.objects.create(sensor=p1_temp, value=round(random.uniform(14.0, 16.0), 2), recorded_at=time)
        SensorReading.objects.create(sensor=p1_do, value=round(random.uniform(7.5, 9.0), 2), recorded_at=time)

        # Pond 2 (warming up)
        SensorReading.objects.create(sensor=p2_temp, value=round(random.uniform(15.5, 18.2), 2), recorded_at=time)
        SensorReading.objects.create(sensor=p2_do, value=round(random.uniform(5.5, 7.0), 2), recorded_at=time)
        
        # Pond 3 (critical condition)
        SensorReading.objects.create(sensor=p3_temp, value=round(random.uniform(22.0, 25.0), 2), recorded_at=time)

    # Create Alerts
    Alert.objects.create(
        pond=pond3, title="Critical Temperature Spike", 
        message="Temperature has exceeded safe limits for Rainbow Trout. Immediate action required.",
        severity="critical", status="open"
    )
    Alert.objects.create(
        pond=pond2, title="Dissolved Oxygen Warning", 
        message="DO levels are trending downward. Aerators should be checked.",
        severity="warning", status="acknowledged"
    )
    Alert.objects.create(
        pond=pond1, title="Routine Sensor Calibration", 
        message="Scheduled maintenance completed successfully.",
        severity="info", status="resolved"
    )

    print("Successfully seeded the database with Farms, Ponds, Sensors, Readings, and Alerts.")

if __name__ == '__main__':
    seed()
