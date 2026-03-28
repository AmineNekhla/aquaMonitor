"""
monitoring/admin.py
Register all models with Django's admin site.
Each model gets useful list_display, list_filter, and search_fields.
"""

from django.contrib import admin
from .models import Profile, Farm, Pond, Sensor, SensorReading, Camera, AIDetection, Alert, Forecast


# ─── Inline: SensorReadings inside Sensor ────────────────────────────────────
class SensorReadingInline(admin.TabularInline):
    model = SensorReading
    extra = 0
    readonly_fields = ('recorded_at',)


# ─── Inline: AIDetections inside Camera ──────────────────────────────────────
class AIDetectionInline(admin.TabularInline):
    model = AIDetection
    extra = 0
    readonly_fields = ('detected_at',)


# ─── Profile ──────────────────────────────────────────────────────────────────
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'phone', 'role')
    list_filter   = ('role',)
    search_fields = ('user__username', 'user__email', 'phone')


# ─── Farm ─────────────────────────────────────────────────────────────────────
@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display  = ('name', 'owner', 'location', 'status', 'created_at')
    list_filter   = ('status',)
    search_fields = ('name', 'location', 'owner__username')


# ─── Pond ─────────────────────────────────────────────────────────────────────
@admin.register(Pond)
class PondAdmin(admin.ModelAdmin):
    list_display  = ('name', 'farm', 'fish_species', 'fish_count', 'status', 'last_updated')
    list_filter   = ('status', 'farm')
    search_fields = ('name', 'fish_species', 'farm__name')


# ─── Sensor ───────────────────────────────────────────────────────────────────
@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display  = ('device_code', 'sensor_type', 'pond', 'unit', 'status', 'installed_at')
    list_filter   = ('sensor_type', 'status')
    search_fields = ('device_code', 'pond__name')
    inlines       = [SensorReadingInline]


# ─── SensorReading ────────────────────────────────────────────────────────────
@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display  = ('sensor', 'value', 'recorded_at')
    list_filter   = ('sensor__sensor_type',)
    search_fields = ('sensor__device_code',)
    readonly_fields = ('recorded_at',)


# ─── Camera ───────────────────────────────────────────────────────────────────
@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display  = ('name', 'pond', 'status', 'installed_at')
    list_filter   = ('status',)
    search_fields = ('name', 'pond__name')
    inlines       = [AIDetectionInline]


# ─── AIDetection ──────────────────────────────────────────────────────────────
@admin.register(AIDetection)
class AIDetectionAdmin(admin.ModelAdmin):
    list_display  = ('detection_type', 'pond', 'camera', 'risk_level', 'confidence_score', 'detected_at')
    list_filter   = ('risk_level', 'detection_type')
    search_fields = ('detection_type', 'pond__name')
    readonly_fields = ('detected_at',)


# ─── Alert ────────────────────────────────────────────────────────────────────
@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display  = ('title', 'pond', 'alert_type', 'severity', 'status', 'created_at')
    list_filter   = ('severity', 'status', 'alert_type')
    search_fields = ('title', 'pond__name', 'message')
    readonly_fields = ('created_at',)



@admin.register(Forecast)
class ForecastAdmin(admin.ModelAdmin):
    list_display = ('pond', 'target_time', 'temp', 'status')
    list_filter = ('status', 'pond')