from rest_framework import serializers
from monitoring.models import ESPDevice, DeviceCommand, SensorReading, Alert, Forecast


class DeviceRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ESPDevice
        fields = ['farm', 'name', 'mac_address']

class DeviceCommandSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceCommand
        fields = ['message_id', 'command_name', 'payload', 'status', 'created_at', 'expires_at']
        read_only_fields = ['message_id']

class SensorReadingPayloadSerializer(serializers.Serializer):
    device_code = serializers.CharField(max_length=100)
    value = serializers.DecimalField(max_digits=10, decimal_places=4)

class AlertSerializer(serializers.ModelSerializer):
    pond_name = serializers.ReadOnlyField(source='pond.name')
    farm_name = serializers.ReadOnlyField(source='pond.farm.name')
    class Meta:
        model = Alert
        fields = ['id', 'farm_name', 'pond_name', 'title', 'alert_type', 'severity', 'message', 'status', 'created_at']

class SensorReadingHistorySerializer(serializers.ModelSerializer):
    sensor_type = serializers.CharField(source='sensor.sensor_type', read_only=True)
    device_code = serializers.CharField(source='sensor.device_code', read_only=True)
    
    class Meta:
        model = SensorReading
        fields = ['id', 'sensor_type', 'device_code', 'value', 'recorded_at']



class ForecastSerializer(serializers.ModelSerializer):
    """Serializer for Forecast objects."""
    pond_name = serializers.CharField(source='pond.name', read_only=True)
    farm_name = serializers.CharField(source='pond.farm.name', read_only=True)
    
    class Meta:
        model = Forecast
        fields = [
            'id',
            'pond',
            'pond_name',
            'farm_name',
            'created_at',
            'target_time',
            'hour_offset',
            'temp',
            'do',
            'ph',
            'ammonia',
            'status',
            'issues',
            'actions',
        ]
        read_only_fields = ['id', 'created_at']