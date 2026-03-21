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
    recorded_at = models.DateTimeField(auto_now_add=True)

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
