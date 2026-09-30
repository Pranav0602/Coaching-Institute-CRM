"""
Root URL configuration.

API surface is versioned under ``/api/v1/``. The ``rag`` app mounts at
``/api/v1/rag/`` (query/ingest/documents) - see ``RAG_IMPLEMENTATION_PLAN.md``.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from institute_crm.analytics_views import DashboardAnalyticsView
from institute_crm.health_views import HealthView, ReadinessView
from django.http import JsonResponse


def _root_view(request):
    """Landing for https://coaching-institute-crm.onrender.com/ — avoids 404 on empty path."""
    return JsonResponse(
        {
            "service": "Coaching Institute CRM API",
            "status": "ok",
            "message": "Backend is running. See /api/docs/ for API documentation.",
            "health": "/healthz/",
            "ready": "/readyz/",
            "docs": "/api/docs/",
            "schema": "/api/schema/",
            "admin": "/admin/",
        }
    )


urlpatterns = [
    path("", _root_view, name="root"),
    path("admin/", admin.site.urls),

    # Operational probes (unauthenticated, no data exposure)
    path("healthz/", HealthView.as_view(), name="healthz"),
    path("readyz/", ReadinessView.as_view(), name="readyz"),

    # Core API Endpoints (v1)
    path("api/v1/accounts/", include("accounts.urls")),
    path("api/v1/profiles/", include("users_profiles.urls")),
    path("api/v1/crm/", include("crm_leads.urls")),
    path("api/v1/academics/", include("academics.urls")),
    path("api/v1/exams/", include("assignments_exams.urls")),
    path("api/v1/finance/", include("finance.urls")),
    path("api/v1/communications/", include("communications.urls")),
    path("api/v1/rag/", include("rag.urls")),
    path("api/v1/analytics/dashboard/", DashboardAnalyticsView.as_view(), name='dashboard_analytics'),
]

if settings.DEBUG:
    # In production, media is served by nginx/S3/CloudFront - never by Django.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

try:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]
except ImportError:
    pass
