# backend/messaging/helpers.py

from messaging.services.sms_service import send_sms
from messaging.models import MessageTemplate
from django.template import Template, Context

def trigger_message(event_type, context, store):
    """
    event_type: str (e.g., 'driver_en_route')
    context: dict (variables to fill in template)
    store: Store instance
    """
    try:
        template_obj = MessageTemplate.objects.get(event=event_type, store=store)
        message_template = Template(template_obj.content)
        message = message_template.render(Context(context))

        to_number = context.get("phone_number")
        if to_number:
            send_sms(to_number, message)
            return True
    except MessageTemplate.DoesNotExist:
        # log that the store doesn't have a template for this event
        pass
    except Exception as e:
        # log unexpected error
        pass

    return False


def send_completion_sms(self, attempt):
    context = {
        "customer_name": attempt.customer.name,
        # Add more if needed
    }
    store = attempt.store
    trigger_message("driver_complete", context, store)
