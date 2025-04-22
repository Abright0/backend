from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.core.management import call_command
from django_apscheduler.models import DjangoJob
import logging

logger = logging.getLogger(__name__)

def run_process_emails():
    logger.info("Running process_emails management command")
    try:
        call_command('process_emails')
    except Exception:
        logger.exception("Error running process_emails command")

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        run_process_emails,
        trigger="interval",
        minutes=5,
        id="process_emails",
        name="Process emails every 5 minutes",
        replace_existing=True,
    )

    scheduler.start()
