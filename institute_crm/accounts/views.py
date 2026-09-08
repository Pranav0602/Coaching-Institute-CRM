"""
HTTP layer for the ``accounts`` app.

Views are deliberately thin: authenticate, validate with a serializer, call exactly one
service method, serialise the result. Business rules, transactions, audit writes and
external calls all live in ``accounts.services``.

Errors are raised as ``institute_crm.exceptions.DomainError`` subclasses by the services
and translated to HTTP by ``institute_crm.renderers.custom_exception_handler``, so no view
here needs to build an error response by hand.
"""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLog, Role
from accounts.permissions import IsSuperAdmin
from accounts.serializers import (
    AuditLogSerializer,
    BranchSerializer,
    BranchStatisticsSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    ProfilePhotoSerializer,
    ResetPasswordSerializer,
    RoleSerializer,
    UserProfileUpdateSerializer,
    UserSerializer,
    UserWriteSerializer,
)
from accounts.services import AuthService, BranchService, UserService
from institute_crm.audit import client_ip


def _bool_param(raw: str | None) -> bool | None:
    """Parse an optional tri-state query parameter."""
    if raw is None or raw == "":
        return None
    return raw.lower() in ("1", "true", "yes")


# --------------------------------------------------------------------- auth


class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AuthService.login(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
            ip_address=client_ip(request),
        )

        return Response(
            {
                "access": result["tokens"]["access"],
                "refresh": result["tokens"]["refresh"],
                "cognito_tokens": result["cognito_tokens"],
                "user": UserSerializer(result["user"], context={"request": request}).data,
            }
        )


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AuthService.request_password_reset(
            email_or_username=serializer.validated_data["email_or_username"],
            ip_address=client_ip(request),
        )
        return Response(result)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AuthService.reset_password(
            email_or_username=serializer.validated_data["email_or_username"],
            otp=serializer.validated_data["otp"],
            new_password=serializer.validated_data["new_password"],
            ip_address=client_ip(request),
        )
        return Response(result)


class ChangePasswordView(APIView):
    """``POST /api/v1/accounts/auth/change-password/``"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AuthService.change_password(
            user=request.user,
            old_password=serializer.validated_data["old_password"],
            new_password=serializer.validated_data["new_password"],
            ip_address=client_ip(request),
        )
        # Existing access tokens stay valid until they expire; the client is told to
        # re-authenticate so the session reflects the new credential.
        return Response(
            {
                "message": "Your password has been changed successfully.",
                "reauthentication_required": True,
            }
        )


# ------------------------------------------------------------------ profile


class UserMeView(APIView):
    """``GET /api/v1/accounts/auth/me/`` - the authoritative session bootstrap."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = AuthService.get_profile(request.user)
        data = UserSerializer(user, context={"request": request}).data
        data["password_age_days"] = AuthService.days_since_password_change(user)
        return Response(data)


class ProfileView(APIView):
    """``GET`` / ``PATCH /api/v1/accounts/auth/profile/``

    Accepts JSON or multipart, so the profile page can send details and a new avatar in a
    single request.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        user = AuthService.get_profile(request.user)
        return Response(UserSerializer(user, context={"request": request}).data)

    def patch(self, request):
        serializer = UserProfileUpdateSerializer(
            instance=request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        payload = dict(serializer.validated_data)
        photo = payload.pop("photo", None)

        user = UserService.update_profile(
            user=request.user,
            data=payload,
            photo=photo,
            ip_address=client_ip(request),
        )
        return Response(UserSerializer(user, context={"request": request}).data)


class ProfilePhotoView(APIView):
    """``POST`` / ``DELETE /api/v1/accounts/auth/upload-photo/``"""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ProfilePhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = UserService.set_profile_photo(
            user=request.user,
            photo=serializer.validated_data["photo"],
            ip_address=client_ip(request),
        )
        return Response(
            UserSerializer(user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        user = UserService.remove_profile_photo(
            user=request.user, ip_address=client_ip(request)
        )
        return Response(UserSerializer(user, context={"request": request}).data)


class MySessionActivityView(APIView):
    """Recent security-relevant events for the signed-in user.

    Powers the "session log" panel on the profile page. Scoped to the requester's own
    records only.
    """

    permission_classes = [IsAuthenticated]

    SECURITY_ACTIONS = ("LOGIN", "LOGIN_FAILED", "LOGOUT", "PASSWORD_CHANGE", "PASSWORD_RESET")

    def get(self, request):
        limit = min(int(request.query_params.get("limit", 10) or 10), 50)
        entries = AuditLog.objects.filter(
            model_name="User",
            target_id=str(request.user.pk),
            action__in=self.SECURITY_ACTIONS,
        ).order_by("-timestamp")[:limit]
        return Response(AuditLogSerializer(entries, many=True).data)


# -------------------------------------------------------------- collections


class UserViewSet(viewsets.ModelViewSet):
    """Administrative user management.

    Visibility, branch pinning and privilege rules are enforced by ``UserService`` so they
    hold for every caller, not just this viewset.
    """

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UserWriteSerializer
        return UserSerializer

    def get_queryset(self):
        return UserService.filter_users(
            self.request.user,
            role=self.request.query_params.get("role"),
            branch_id=self.request.query_params.get("branch_id"),
            search=self.request.query_params.get("search"),
            is_active=_bool_param(self.request.query_params.get("is_active")),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = UserService.create_user(
            actor=request.user,
            data=serializer.validated_data,
            ip_address=client_ip(request),
        )
        return Response(
            UserSerializer(user, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)

        user = UserService.update_user(
            actor=request.user,
            user=instance,
            data=serializer.validated_data,
            ip_address=client_ip(request),
        )
        return Response(UserSerializer(user, context={"request": request}).data)

    def destroy(self, request, *args, **kwargs):
        UserService.soft_delete_user(
            actor=request.user,
            user=self.get_object(),
            ip_address=client_ip(request),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="role-distribution")
    def role_distribution(self, request):
        return Response(UserService.role_distribution(request.user))


class BranchViewSet(viewsets.ModelViewSet):
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BranchService.visible_branches(self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        branch = BranchService.create_branch(
            actor=request.user,
            data=serializer.validated_data,
            ip_address=client_ip(request),
        )
        return Response(
            BranchSerializer(branch).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)

        branch = BranchService.update_branch(
            actor=request.user,
            branch=instance,
            data=serializer.validated_data,
            ip_address=client_ip(request),
        )
        return Response(BranchSerializer(branch).data)

    def destroy(self, request, *args, **kwargs):
        BranchService.soft_delete_branch(
            actor=request.user,
            branch=self.get_object(),
            ip_address=client_ip(request),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="statistics")
    def statistics(self, request):
        stats = BranchService.branch_statistics(request.user)
        return Response(BranchStatisticsSerializer(stats, many=True).data)


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Role.objects.all().order_by("name")
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("actor")
        params = self.request.query_params
        if params.get("action"):
            queryset = queryset.filter(action=params["action"])
        if params.get("model_name"):
            queryset = queryset.filter(model_name=params["model_name"])
        if params.get("target_id"):
            queryset = queryset.filter(target_id=params["target_id"])
        if params.get("actor_id"):
            queryset = queryset.filter(actor_id=params["actor_id"])
        return queryset
