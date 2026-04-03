"""
monitoring/models.py
Django ORM models for the Smart Aquaculture Monitoring System.

Entities:
  Profile      – extends built-in User with phone and role
  Farm         – fish farm owned by a User
  Pond         – pond inside a Farm
  Sensor       – sensor attached to a Pond
  SensorReading– one measurement from a Sensor
  Camera       – IP/stream camera attached to a Pond
  AIDetection  – AI-based detection result linked to a Camera/Pond
  Alert        – warning or critical event for a Pond
"""

from django.db import models
from django.contrib.auth.models import User
import uuid


# ─── Profile ──────────────────────────────────────────────────────────────────
class Profile(models.Model):
    """Extends the built-in User model with extra fields."""

    ROLE_CHOICES = [
        ('admin',   'Admin'),
        ('manager', 'Farm Manager'),
        ('viewer',  'Viewer'),
    ]

    # One-to-one link: each User has exactly one Profile
    user  = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, default='')
    role  = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"

    class Meta:
        verbose_name = 'Profile'


# ─── Farm ─────────────────────────────────────────────────────────────────────
class Farm(models.Model):
    """A fish farm owned by a user."""

    STATUS_CHOICES = [
        ('active',   'Active'),
        ('inactive', 'Inactive'),
    ]

    owner    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='farms')
    name     = models.CharField(max_length=200)
    location = models.CharField(max_length=300, blank=True, default='')
    latitude = models.FloatField(null=True, blank=True, help_text="GPS latitude (e.g., 33.5731)")
    longitude = models.FloatField(null=True, blank=True, help_text="GPS longitude (e.g., -7.5898)")
    status   = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Farm'


# ─── Pond ─────────────────────────────────────────────────────────────────────
class Pond(models.Model):
    """A single pond inside a farm."""

    STATUS_CHOICES = [
        ('normal',  'Normal'),
        ('warning', 'Warning'),
        ('critical','Critical'),
    ]

    farm         = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='ponds')
    name         = models.CharField(max_length=200)
    fish_species = models.CharField(max_length=200, blank=True, default='')
    fish_count   = models.PositiveIntegerField(default=0)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='normal')
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.farm.name})"

    class Meta:
        ordering = ['farm', 'name']
        verbose_name = 'Pond'


# ─── Sensor ───────────────────────────────────────────────────────────────────
class Sensor(models.Model):
    """A monitoring sensor attached to a pond."""

    TYPE_CHOICES = [
        ('temperature', 'Temperature'),
        ('oxygen',      'Dissolved Oxygen'),
        ('pH',          'pH Level'),
        ('salinity',    'Salinity'),
        ('turbidity',   'Turbidity'),
    ]

    STATUS_CHOICES = [
        ('online',   'Online'),
        ('offline',  'Offline'),
        ('faulty',   'Faulty'),
    ]

    pond        = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='sensors')
    sensor_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    device_code = models.CharField(max_length=100, unique=True)
    unit        = models.CharField(max_length=20, blank=True, default='')  # e.g. "°C", "mg/L"
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='online')
    installed_at = models.DateField()

    def __str__(self):
        return f"{self.get_sensor_type_display()} – {self.device_code}"

    class Meta:
        ordering = ['pond', 'sensor_type']
        verbose_name = 'Sensor'


# ─── SensorReading ────────────────────────────────────────────────────────────
class SensorReading(models.Model):
    """A single measurement recorded by a sensor."""

    sensor      = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='readings')
    value       = models.DecimalField(max_digits=10, decimal_places=4)
    recorded_at = models.DateTimeField() #H: removed the auto to accept the time generated

    def __str__(self):
        return f"{self.sensor} → {self.value} @ {self.recorded_at:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ['-recorded_at']
        verbose_name = 'Sensor Reading'


# ─── Camera ───────────────────────────────────────────────────────────────────
class Camera(models.Model):
    """An IP or stream camera attached to a pond."""

    STATUS_CHOICES = [
        ('online',  'Online'),
        ('offline', 'Offline'),
    ]

    pond         = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='cameras')
    name         = models.CharField(max_length=200)
    stream_url   = models.URLField(blank=True, default='')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='online')
    installed_at = models.DateField()

    def __str__(self):
        return f"{self.name} ({self.pond.name})"

    class Meta:
        ordering = ['pond', 'name']
        verbose_name = 'Camera'


# ─── AIDetection ──────────────────────────────────────────────────────────────
class AIDetection(models.Model):
    """Result of an AI-based analysis of camera footage."""

    RISK_CHOICES = [
        ('low',      'Low'),
        ('medium',   'Medium'),
        ('high',     'High'),
        ('critical', 'Critical'),
    ]

    pond             = models.ForeignKey(Pond,   on_delete=models.CASCADE, related_name='ai_detections')
    camera           = models.ForeignKey(Camera, on_delete=models.SET_NULL, null=True, blank=True, related_name='detections')
    detection_type   = models.CharField(max_length=200)        # e.g. "Disease Outbreak"
    confidence_score = models.FloatField(default=0.0)          # 0.0 – 1.0
    description      = models.TextField(blank=True, default='')
    prediction_text  = models.TextField(blank=True, default='')
    risk_level       = models.CharField(max_length=20, choices=RISK_CHOICES, default='low')
    detected_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.detection_type} [{self.risk_level}] – {self.pond.name}"

    class Meta:
        ordering = ['-detected_at']
        verbose_name = 'AI Detection'


# ─── Alert ────────────────────────────────────────────────────────────────────
class Alert(models.Model):
    """A warning or critical alert raised for a pond."""

    TYPE_CHOICES = [
        ('water_quality', 'Water Quality'),
        ('disease',       'Disease'),
        ('oxygen',        'Low Oxygen'),
        ('temperature',   'Temperature'),
        ('pollution',     'Pollution'),
        ('other',         'Other'),
    ]

    SEVERITY_CHOICES = [
        ('info',     'Info'),
        ('warning',  'Warning'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('open',         'Open'),
        ('acknowledged', 'Acknowledged'),
        ('resolved',     'Resolved'),
    ]

    pond               = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='alerts')
    title              = models.CharField(max_length=300)
    alert_type         = models.CharField(max_length=50, choices=TYPE_CHOICES, default='other')
    severity           = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='warning')
    message            = models.TextField()
    recommended_action = models.TextField(blank=True, default='')
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at         = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title} – {self.pond.name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Alert'

#H: forcastes model (for forcasted data)

class Forecast(models.Model):
    STATUS_CHOICES = [
        ('Good', 'Good'),
        ('Warning', 'Warning'),
        ('Risk', 'Risk'),
    ]

    pond        = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='forecasts')
    created_at  = models.DateTimeField(auto_now_add=True)  #H: pred time
    target_time = models.DateTimeField()                    # the future hour (now + N)
    hour_offset = models.PositiveSmallIntegerField()        # 1 to 6 (the nbr of pred hour) — easier to query

    # Predicted values from LSTM
    temp    = models.FloatField()
    do      = models.FloatField()
    ph      = models.FloatField()
    ammonia = models.FloatField(default=0.0)               # store current ammonia too

    # Classification from Model 1
    status  = models.CharField(max_length=10, choices=STATUS_CHOICES)
    issues  = models.TextField(blank=True, default='')     # use default='' not null=True
    actions = models.TextField(blank=True, default='')     # Storing the CTA

    class Meta:
        ordering = ['target_time']
        # prevent duplicate forecasts for same pond/hour
        unique_together = ['pond', 'target_time']

    def __str__(self):
        return f"Forecast {self.pond.name} +{self.hour_offset}h → {self.status}"

# ─── ESP32 Device & Command Models ────────────────────────────────────────────
class ESPDevice(models.Model):
    """An ESP32 device registry linking to a farm and holding an API key."""
    STATUS_CHOICES = [('active', 'Active'), ('offline', 'Offline'), ('maintenance', 'Maintenance')]

    farm = models.ForeignKey('Farm', on_delete=models.CASCADE, related_name='devices')
    name = models.CharField(max_length=200)
    mac_address = models.CharField(max_length=50, unique=True, help_text="e.g. 00:1B:44:11:3A:B7")
    api_key = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.api_key:
            import secrets
            self.api_key = secrets.token_hex(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} [{self.mac_address}]"

class DeviceCommand(models.Model):
    """Commands queued for an ESP32 to fetch."""
    STATUS_CHOICES = [('pending', 'Pending'), ('delivered', 'Delivered'), ('acknowledged', 'Acknowledged'), ('failed', 'Failed')]

    device = models.ForeignKey(ESPDevice, on_delete=models.CASCADE, related_name='commands')
    command_name = models.CharField(max_length=100)  # e.g. "RELAY_ON"
    payload = models.JSONField(default=dict, blank=True)
    message_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.command_name} -> {self.device.name} [{self.status}]"