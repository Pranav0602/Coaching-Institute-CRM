from django.contrib import admin
from accounts.models import User, Role, Branch, AuditLog

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'branch', 'is_active']
    search_fields = ['username', 'email', 'phone']

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'description']

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'city', 'phone', 'email']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['actor', 'action', 'model_name', 'target_id', 'timestamp']