"""
aquaculture/asgi.py
ASGI config for the aquaculture project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquaculture.settings')
application = get_asgi_application()
