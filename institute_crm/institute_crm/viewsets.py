"""
Shared DRF base classes.

Every write endpoint in this project follows the same four steps: validate with a serialiser,
call exactly one service method, serialise the result, return it. Repeating that in each
viewset produced ~40 lines of near-identical boilerplate per app and, more importantly, gave
each app a chance to forget a piece - branch scoping, the audit actor, or the soft delete.

:class:`ServiceBackedViewSet` centralises the plumbing and leaves subclasses with three small
hooks that contain nothing but the service call.

It also fixes the default that caused the most damage in the original code: DRF's
``perform_destroy`` calls ``instance.delete()``, a hard row delete, on a model family that
implements soft deletion. Here ``destroy`` has no default at all - a subclass that does not
implement :meth:`service_delete` returns 405 rather than silently destroying data.
"""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from institute_crm.audit import client_ip
from institute_crm.exceptions import PermissionDeniedError


def bool_param(raw, default=None):
    """Parse an optional tri-state query parameter (``None`` when absent)."""
    if raw is None or raw == "":
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def int_param(raw, default=None, *, maximum=None):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return min(value, maximum) if maximum is not None else value


class ServiceBackedViewSet(viewsets.ModelViewSet):
    """A ``ModelViewSet`` whose writes are delegated to a service class.

    Subclasses provide :meth:`service_create`, :meth:`service_update` and
    :meth:`service_delete`. Anything not implemented is *not exposed* - the corresponding
    HTTP method returns 405 instead of falling back to DRF's direct ORM behaviour.

    Reads come from :meth:`get_queryset`, which subclasses point at the service's
    ``visible_*``/``filter_*`` helper so list, retrieve and every ``get_object()`` lookup
    (including the ones inside custom actions) share one scoping implementation.
    """

    permission_classes = [IsAuthenticated]

    #: Serialiser used to render responses. Defaults to ``serializer_class``; override when
    #: writes accept a different shape from what reads return.
    read_serializer_class = None

    # ------------------------------------------------------------- helpers

    @property
    def ip(self) -> str | None:
        return client_ip(self.request)

    @property
    def actor(self):
        return self.request.user

    def get_read_serializer(self, instance, **kwargs):
        serializer_class = self.read_serializer_class or self.get_serializer_class()
        return serializer_class(
            instance, context=self.get_serializer_context(), **kwargs
        )

    def respond(self, instance, *, status_code=status.HTTP_200_OK, many=False):
        return Response(
            self.get_read_serializer(instance, many=many).data, status=status_code
        )

    # --------------------------------------------------------------- hooks

    def service_create(self, data: dict):
        raise NotImplementedError

    def service_update(self, instance, data: dict, *, partial: bool):
        raise NotImplementedError

    def service_delete(self, instance) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------ handlers

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = self.service_create(dict(serializer.validated_data))
        except NotImplementedError:
            return self._not_allowed()
        return self.respond(instance, status_code=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            updated = self.service_update(
                instance, dict(serializer.validated_data), partial=partial
            )
        except NotImplementedError:
            return self._not_allowed()
        return self.respond(updated)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.service_delete(instance)
        except NotImplementedError:
            return self._not_allowed()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _not_allowed(self):
        return Response(
            {"detail": f"Method '{self.request.method}' is not allowed on this resource."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class ReadOnlyServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only counterpart, for resources written only through custom actions."""

    permission_classes = [IsAuthenticated]

    @property
    def ip(self) -> str | None:
        return client_ip(self.request)

    @property
    def actor(self):
        return self.request.user


def require_authenticated_actor(actor):
    """Guard for services called outside a DRF permission class."""
    if actor is None or not getattr(actor, "is_authenticated", False):
        raise PermissionDeniedError("Authentication is required.", code="not_authenticated")
