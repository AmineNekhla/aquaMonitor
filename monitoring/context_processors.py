"""
monitoring/context_processors.py
Provides global notification context variables to all templates.
"""
from .models import Farm, Pond, Alert

def notifications(request):
    """
    Makes unread_alert_count and recent_alerts available in all templates
    for the logged-in user.
    """
    if request.user.is_authenticated:
        # Get all ponds belonging to this user
        user_farms = Farm.objects.filter(owner=request.user)
        user_ponds = Pond.objects.filter(farm__in=user_farms)
        
        # Unread notifications = alerts where status is "open" 
        # (This aligns with the existing 'open' status covering the 'new' state)
        unread_alerts_count = Alert.objects.filter(
            pond__in=user_ponds, 
            status='open'
        ).count()
        
        # Recent notifications = latest 5 alerts
        recent_alerts = Alert.objects.filter(
            pond__in=user_ponds
        ).order_by('-created_at')[:5]
        
        return {
            'unread_alert_count': unread_alerts_count,
            'recent_alerts': recent_alerts,
        }
    return {}
