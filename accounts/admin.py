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
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Roles', {
            'fields': (
                'is_store_manager', 
                'is_warehouse_manager', 
                'is_inside_manager', 
                'is_driver', 
                'is_customer_service',
            )
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Store Access', {'fields': ('stores',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2', 'phone_number',
                'is_store_manager', 'is_warehouse_manager', 'is_inside_manager',
                'is_driver', 'is_customer_service'
            ),
        }),
    )

    list_display = (
        'username', 'email', 'first_name', 'last_name', 'is_staff',
        'is_store_manager', 'is_warehouse_manager', 'is_inside_manager',
        'is_driver', 'is_customer_service'
    )

    list_filter = BaseUserAdmin.list_filter + (
        'is_store_manager', 'is_warehouse_manager',
        'is_inside_manager', 'is_driver', 'is_customer_service'
    )

    filter_horizontal = ('groups', 'user_permissions', 'stores')

admin.site.register(User, UserAdmin)
