@scheduler.scheduled_job("interval", minutes=5, name="process_emails")
def process_emails_job():
    call_command('process_emails')