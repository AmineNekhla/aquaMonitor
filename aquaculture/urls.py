"""
aquaculture/urls.py
Root URL configuration for the aquaculture project.
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Django admin site
    path('admin/', admin.site.urls),

    # Login / Logout (uses Django's built-in auth views)
    path('login/', auth_views.LoginView.as_view(template_name='monitoring/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # All monitoring app URLs (dashboard, farms, ponds, alerts, profile)
    path('', include('monitoring.urls')),
]
