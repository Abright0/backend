# email_processor/apps.py
import os
from django.apps import AppConfig

class EmailProcessorConfig(AppConfig):
    default_auto_field = 'django.db.BigAutoField'
    name = 'email_processor'

    def ready(self):
        if os.environ.get('RUN_MAIN', None) != 'true':
            return
        from . import scheduler
        scheduler.start()