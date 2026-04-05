from django.urls import path
from . import views

urlpatterns = [
    # Device Routes
    path('devices/register/', views.DeviceRegisterView.as_view(), name='api_device_register'),
    path('devices/heartbeat/', views.DeviceHeartbeatView.as_view(), name='api_device_heartbeat'),
    path('devices/<int:device_id>/commands/', views.DeviceCommandsView.as_view(), name='api_device_commands'),
    path('devices/<int:device_id>/ack/', views.DeviceAckView.as_view(), name='api_device_ack'),
    
    # Sensor Routes
    path('sensors/data/', views.SensorDataView.as_view(), name='api_sensor_data'),
    path('sensors/history/', views.SensorHistoryView.as_view(), name='api_sensor_history'),
    
    # Alert Routes
    path('alerts/', views.AlertsView.as_view(), name='api_alerts'),
    
    # Forecast Routes
    path('forecasts/', views.ForecastListView.as_view(), name='forecast-list'),
    path('ponds/<int:pond_id>/forecasts/', views.PondForecastView.as_view(), name='pond-forecasts'),
    
    #H: cam fish disease detection routes
    path('disease-detections/', views.DiseaseDetectionListView.as_view(), name='disease-detections'),
    path('disease-alerts/', views.DiseaseAlertsView.as_view(), name='disease-alerts'),
    path('disease-alerts/<int:alert_id>/acknowledge/', views.DiseaseAlertsView.as_view(), name='acknowledge-alert'),
]
