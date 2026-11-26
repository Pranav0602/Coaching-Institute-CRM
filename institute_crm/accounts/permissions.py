from rest_framework.permissions import BasePermission
from accounts.models import Role

#: Roles that run the front desk and the lead pipeline. ``ADMISSION_COUNSELOR`` is kept
#: as a legacy alias so tokens issued before the role transition keep working.
LEAD_DESK_ROLES = (Role.RECEPTIONIST, Role.ADMISSION_COUNSELOR)


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

class IsAdminOrCounselorReadOnly(BasePermission):
    """
    Full CRUD for SUPER_ADMIN / BRANCH_ADMIN (and superusers).
    Read-only (GET/HEAD/OPTIONS) for RECEPTIONIST (and the legacy ADMISSION_COUNSELOR)
    on published docs.
    All other roles / unauthenticated requests are rejected.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        role_code = getattr(user.role, "code", None) if getattr(user, "role", None) else None
        if role_code in [Role.SUPER_ADMIN, Role.BRANCH_ADMIN]:
            return True
        if role_code in LEAD_DESK_ROLES:
            return request.method in ("GET", "HEAD", "OPTIONS")
        return False


class IsAdmissionCounselor(BasePermission):
    """Legacy name retained for compatibility. Now also admits RECEPTIONIST."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role and (
            request.user.role.code in [Role.SUPER_ADMIN, Role.BRANCH_ADMIN, *LEAD_DESK_ROLES]
        ))


class IsReceptionistOrAdmin(BasePermission):
    """Reception desk, plus the administrative roles that always outrank it."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role and (
            request.user.role.code in [Role.SUPER_ADMIN, Role.BRANCH_ADMIN, *LEAD_DESK_ROLES]
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
            request.user.role.code in [Role.SUPER_ADMIN, Role.BRANCH_ADMIN, *LEAD_DESK_ROLES]
        ))
