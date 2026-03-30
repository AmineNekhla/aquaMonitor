from rest_framework import authentication
from rest_framework import exceptions
from monitoring.models import ESPDevice

class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class for ESP32 devices validating X-Device-API-Key header.
    """
    def authenticate(self, request):
        api_key = request.headers.get('X-Device-API-Key')
        if not api_key:
            return None  # Pass to next auth class (e.g. SessionAuth for frontend)

        try:
            device = ESPDevice.objects.get(api_key=api_key)
        except ESPDevice.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API Key provided')

        # DRF expects a tuple of (user, auth)
        return (device, api_key)
