from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.utils import timezone
from .serializers import *
from .auth import APIKeyAuthentication
from monitoring.models import ESPDevice, DeviceCommand, Sensor, SensorReading, Alert, Forecast, Pond, Farm
from django.shortcuts import get_object_or_404

class DeviceRegisterView(views.APIView):
    """
    Register a new ESP32 device or fetch existing API key.
    Requires no auth so devices can auto-provision using their hardcoded farm ID and MAC.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = DeviceRegisterSerializer(data=request.data)
        if serializer.is_valid():
            mac = serializer.validated_data.get('mac_address')
            device, created = ESPDevice.objects.get_or_create(
                mac_address=mac,
                defaults=serializer.validated_data
            )
            return Response({
                'device_id': device.id, 
                'api_key': device.api_key, 
                'is_new': created
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeviceHeartbeatView(views.APIView):
    """
    Simple ping to mark the device as active.
    """
    authentication_classes = [APIKeyAuthentication]

    def post(self, request):
        device = request.user
        device.last_heartbeat = timezone.now()
        device.status = 'active'
        device.save()
        return Response({"status": "ok", "timestamp": device.last_heartbeat})

class DeviceCommandsView(views.APIView):
    """
    ESP32 polls this endpoint to fetch pending commands (Relays, Configs).
    """
    authentication_classes = [APIKeyAuthentication]

    def get(self, request, device_id):
        device = request.user
        if device.id != device_id:
            return Response({"error": "Unauthorized device ID"}, status=status.HTTP_403_FORBIDDEN)
            
        cmds = DeviceCommand.objects.filter(device=device, status='pending')
        
        now = timezone.now()
        valid_cmds = []
        for cmd in cmds:
            if cmd.expires_at and now > cmd.expires_at:
                cmd.status = 'failed'
                cmd.save()
            else:
                valid_cmds.append(cmd)
                
        serializer = DeviceCommandSerializer(valid_cmds, many=True)
        return Response(serializer.data)

class DeviceAckView(views.APIView):
    """
    ESP32 acknowledges successful execution of a command to ensure idempotency.
    """
    authentication_classes = [APIKeyAuthentication]

    def post(self, request, device_id):
        device = request.user
        if device.id != device_id:
            return Response({"error": "Unauthorized device ID"}, status=status.HTTP_403_FORBIDDEN)

        message_id = request.data.get('message_id')
        cmd_status = request.data.get('status', 'acknowledged')
        
        try:
            cmd = DeviceCommand.objects.get(device=device, message_id=message_id)
            cmd.status = cmd_status
            cmd.acknowledged_at = timezone.now()
            cmd.save()
            return Response({"status": "acknowledged"})
        except DeviceCommand.DoesNotExist:
            return Response({"error": "Command not found"}, status=status.HTTP_404_NOT_FOUND)

class SensorDataView(views.APIView):
    """
    Endpoint for the ESP32 to push an array of sensor readings.
    """
    authentication_classes = [APIKeyAuthentication]

    def post(self, request):
        serializer = SensorReadingPayloadSerializer(data=request.data, many=True)
        if serializer.is_valid():
            now = timezone.now()
            saved_count = 0
            for item in serializer.validated_data:
                try:
                    sensor = Sensor.objects.get(device_code=item['device_code'])
                    SensorReading.objects.create(sensor=sensor, value=item['value'], recorded_at=now)
                    saved_count += 1
                except Sensor.DoesNotExist:
                    pass
            
            # Implicit heartbeat update
            device = request.user
            device.last_heartbeat = now
            device.status = 'active'
            device.save()
            
            return Response({"status": "data processed", "saved": saved_count}, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AlertsView(views.APIView):
    """
    Fetch open alerts. Can be used by mobile app or front-end.
    """
    def get(self, request):
        alerts = Alert.objects.filter(status='open')
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)

class SensorHistoryView(views.APIView):
    """
    Fetch sensor history. Useful for charts if transitioning to a SPA frontend.
    """
    def get(self, request):
        readings = SensorReading.objects.all()[:100] # Limiting for demo
        serializer = SensorReadingHistorySerializer(readings, many=True)
        return Response(serializer.data)


#H: forecast view
class ForecastListView(views.APIView):
    """
    GET /api/forecasts/
    
    Fetch all forecasts for current user's ponds.
    Returns only future forecasts (target_time >= now).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_farms = Farm.objects.filter(owner=request.user)
        user_ponds = Pond.objects.filter(farm__in=user_farms)
        
        # Get forecasts from now onwards
        now = timezone.now()
        forecasts = Forecast.objects.filter(
            pond__in=user_ponds,
            target_time__gte=now
        ).order_by('target_time').select_related('pond', 'pond__farm')[:30]  # Limit to 30
        
        serializer = ForecastSerializer(forecasts, many=True)
        return Response({
            'count': len(forecasts),
            'data': serializer.data
        })


class PondForecastView(views.APIView):
    """
    GET /api/ponds/<pond_id>/forecasts/
    
    Fetch 6-hour forecast for a specific pond.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pond_id):
        pond = get_object_or_404(Pond, id=pond_id, farm__owner=request.user)
        
        now = timezone.now()
        forecasts = Forecast.objects.filter(
            pond=pond,
            target_time__gte=now
        ).order_by('target_time')[:6]  # Next 6 hours
        
        serializer = ForecastSerializer(forecasts, many=True)
        return Response({
            'pond_id': pond.id,
            'pond_name': pond.name,
            'count': len(forecasts),
            'data': serializer.data
        })