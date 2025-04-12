from django.contrib import admin
from messaging.models import MessageTemplate

@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['store', 'event']
    list_filter = ['store', 'event']
    search_fields = ['store__name', 'event']
    ordering = ['store', 'event']
