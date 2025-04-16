# backend/messaging/helpers.py

from messaging.services.sms_service import send_sms
from messaging.models import MessageTemplate
from django.template import Template, Context

def trigger_message(event_type, context, store):
    try:
        template_obj = MessageTemplate.objects.get(event=event_type, store=store)
        if not template_obj.active:
            return
    except MessageTemplate.DoesNotExist:
        return

    # Render safely using Django’s template engine
    template = Template(template_obj.content)
    rendered_message = template.render(Context(context))

    to_number = context.get("phone_number")
    send_sms(to_number, rendered_message)