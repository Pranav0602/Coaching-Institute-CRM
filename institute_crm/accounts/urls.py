from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import (
    AuditLogViewSet,
    AuthLoginView,
    BranchViewSet,
    ChangePasswordView,
    ForgotPasswordView,
    LogoutView,
    MySessionActivityView,
    ProfilePhotoView,
    ProfileView,
    ResetPasswordView,
    RoleViewSet,
    TokenRefreshView,
    UserMeView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'branches', BranchViewSet, basename='branch')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')

urlpatterns = [
    # Session
    path('auth/login/', AuthLoginView.as_view(), name='auth_login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth_token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/me/', UserMeView.as_view(), name='auth_me'),

    # Credentials
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='auth_forgot_password'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='auth_reset_password'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth_change_password'),

    # Self-service profile
    path('auth/profile/', ProfileView.as_view(), name='auth_profile'),
    path('auth/upload-photo/', ProfilePhotoView.as_view(), name='auth_upload_photo'),
    path('auth/session-activity/', MySessionActivityView.as_view(), name='auth_session_activity'),

    path('', include(router.urls)),
]
