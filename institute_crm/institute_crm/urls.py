"""
Root URL configuration.

API surface is versioned under ``/api/v1/``. The ``rag`` app, when it lands, mounts at
``/api/v1/assistant/`` (customer chat) and ``/api/v1/rag/`` (admin-only editorial control
plane) - see ``RAG_IMPLEMENTATION_PLAN.md`` section 9.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from institute_crm.analytics_views import DashboardAnalyticsView
from institute_crm.health_views import HealthView, ReadinessView

urlpatterns = [
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

# Reserved mount points for the RAG app. Activated only once the app exists and
# RAG_ENABLED is on, so this file needs no further edit at that point.
if getattr(settings, "RAG_ENABLED", False):
    try:
        urlpatterns += [
            path("api/v1/assistant/", include("rag.api.customer_urls")),
            path("api/v1/rag/", include("rag.api.admin_urls")),
        ]
    except ImportError:
        # RAG_ENABLED was set before the app was installed; the system checks report
        # this properly, so failing to boot here would only obscure the real message.
        pass

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
