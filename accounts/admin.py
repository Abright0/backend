# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import User  # Your custom User model

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields

class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Custom Fields', {'fields': ('phone_number', 'is_driver', 'is_customer_service', 'is_manager', 'stores')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'phone_number', 
                    'is_driver', 'is_customer_service', 'is_manager'),
        }),
)
    
    # Add custom fields to the list display
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_driver', 'is_customer_service', 'is_manager')
    
    # Add filters
    list_filter = BaseUserAdmin.list_filter + ('is_driver', 'is_customer_service', 'is_manager')
    
    # For ManyToMany fields like 'stores', you may need to use filter_horizontal
    filter_horizontal = ('groups', 'user_permissions', 'stores')

# Register the User model with the custom admin
admin.site.register(User, UserAdmin)