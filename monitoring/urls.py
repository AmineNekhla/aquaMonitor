"""
monitoring/urls.py
URL patterns for the monitoring application.
All routes here are prefixed by '' (root) from the project urls.py.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('',                    views.dashboard,    name='dashboard'),

    # Farms
    path('farms/',              views.farms_list,   name='farms_list'),
    path('farms/<int:farm_id>/',views.farm_detail,  name='farm_detail'),

    # Ponds
    path('ponds/',                                views.ponds_list,         name='ponds_list'),
    path('ponds/<int:pond_id>/',                  views.pond_detail,        name='pond_detail'),
    path('ponds/<int:pond_id>/live-readings/',    views.pond_live_readings, name='pond_live_readings'),
    path('ponds/<int:pond_id>/action/aerator/',   views.pond_action_aerator,   name='pond_action_aerator'),
    path('ponds/<int:pond_id>/action/calibrate/', views.pond_action_calibrate, name='pond_action_calibrate'),
    path('ponds/<int:pond_id>/action/report/',    views.pond_action_report,    name='pond_action_report'),

    # Alerts
    path('alerts/',                           views.alerts_list,          name='alerts_list'),
    path('alerts/mark-all-read/',             views.mark_all_alerts_read, name='mark_all_alerts_read'),
    path('alerts/<int:alert_id>/mark-read/',  views.mark_alert_read,      name='mark_alert_read'),

    # Profile
    path('profile/',            views.profile,      name='profile'),
]
