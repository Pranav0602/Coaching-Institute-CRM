"""
Liveness and readiness probes.

``/healthz`` answers "is this process up?" and must stay dependency-free so it can be used
as a container liveness probe without a database round trip.

``/readyz`` answers "can this process serve traffic?" and therefore does check the
database, the media directory, and - once RAG is enabled - pgvector availability. It
returns 503 while any of those is unsatisfied, which is what a load balancer needs in
order to hold traffic back during a rolling deploy.

Both are deliberately unauthenticated (a probe has no credentials) and deliberately
low-detail: the failure list names *which* subsystem is unhappy, never connection strings,
credentials or stack traces.
"""
from __future__ import annotations

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("institute_crm")


class HealthView(APIView):
    """Liveness. No I/O - if the process can run Python, it is alive."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    # Plain JSON, not the standard envelope: probes parse a fixed shape.
    renderer_classes = [JSONRenderer]

    def get(self, request):
        return Response({"status": "ok"})


class ReadinessView(APIView):
    """Readiness. Exercises the dependencies required to serve a real request."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    renderer_classes = [JSONRenderer]

    def get(self, request):
        from institute_crm.checks import run_readiness_checks

        try:
            failures = run_readiness_checks()
        except Exception as exc:
            logger.exception("Readiness check raised")
            failures = [f"readiness check error: {type(exc).__name__}"]

        payload = {
            "status": "ready" if not failures else "not_ready",
            "checks": {
                "database": "postgresql",
                "rag_enabled": getattr(settings, "RAG_ENABLED", False),
            },
        }
        if failures:
            payload["failures"] = failures
            return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(payload)
