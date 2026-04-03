"""
Celery configuration for the tasks' schedualing.
"""

import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquaculture.settings')

app = Celery('aquaculture')


app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

#H: running the forcasting each 2hrs
app.conf.beat_schedule = {
    'run-inference-every-2-hours': {
        'task': 'monitoring.tasks.periodic_inference',
        'schedule': 7200.0,  # 7200 seconds = 2 hours
    },
}


@app.task(bind=True)
def debug_task(self):
    """Test task to verify Celery is working."""
    print(f'Request: {self.request!r}')