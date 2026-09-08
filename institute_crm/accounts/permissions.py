from rest_framework.permissions import BasePermission
from accounts.models import Role

class HasRolePermission(BasePermission):
    """
    Custom permission to grant access based on allowed roles.
    Usage: permission_classes = [HasRolePermission(Role.SUPER_ADMIN, Role.BRANCH_ADMIN)]
    """
    def __init__(self, *allowed_roles):
        self.allowed_roles = allowed_roles

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if not request.user.role:
            return False
        return request.user.role.code in self.allowed_roles


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.is_superuser or (request.user.role and request.user.role.code == Role.SUPER_ADMIN)
        ))

class IsBranchAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role and (
            request.user.role.code in [Role.SUPER_ADMIN, Role.BRANCH_ADMIN]
        ))

class IsAdmissionCounselor(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role and (
            request.user.role.code in [Role.SUPER_ADMIN, Role.BRANCH_ADMIN, Role.ADMISSION_COUNSELOR]
        ))

class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role and (
            request.user.role.code in [Role.SUPER_ADMIN, Role.BRANCH_ADMIN, Role.TEACHER]
        ))

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role and (
            request.user.role.code == Role.STUDENT
        ))

class IsParent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role and (
            request.user.role.code == Role.PARENT
        ))

class IsAccountant(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role and (
            request.user.role.code in [Role.SUPER_ADMIN, Role.BRANCH_ADMIN, Role.ACCOUNTANT]
        ))

class IsReceptionist(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role and (
            request.user.role.code in [Role.SUPER_ADMIN, Role.BRANCH_ADMIN, Role.RECEPTIONIST]
        ))
