# email_processor/apps.py
import os
import threading
from django.apps import AppConfig

class EmailProcessorConfig(AppConfig):
    default_auto_field = 'django.db.BigAutoField'
    name = 'email_processor'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':
            pass
            # Start the scheduler in a new thread after the app is fully loaded
            #from . import scheduler
            #threading.Thread(target=scheduler.start, daemon=True).start()
