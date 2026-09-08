"""
Dashboard endpoints.

Thin HTTP wrappers. All aggregation, scoping and role gating lives in
:mod:`institute_crm.analytics_service`.
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from institute_crm.analytics_service import DashboardAnalyticsService
from institute_crm.viewsets import int_param


class DashboardAnalyticsView(APIView):
    """``GET /api/v1/analytics/dashboard/`` - cards and charts for the caller's scope.

    Figures are real. A metric with no underlying data returns ``0`` (or ``null`` for a
    percentage that has no denominator) rather than a plausible-looking placeholder.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        months = int_param(request.query_params.get("months"), default=6, maximum=24)
        return Response(
            DashboardAnalyticsService.dashboard(request.user, months=months)
        )
