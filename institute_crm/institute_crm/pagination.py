"""Optional pagination that stays backwards compatible.

When no ``page`` / ``page_size`` query parameter is supplied the full list is
returned (existing behaviour for clients that filter/sort client-side). When a
``page`` is requested the standard DRF ``{count, next, previous, results}``
envelope is produced, inside the app's ``{success, message, data}`` wrapper,
and - because pagination runs *after* scoping and filtering - totals always
reflect the applied branch filter, search, etc.
"""
from rest_framework.pagination import PageNumberPagination


class OptionalPageNumberPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500

    def paginate_queryset(self, queryset, request, view=None):
        params = request.query_params
        if (
            self.page_query_param not in params
            and self.page_size_query_param not in params
        ):
            return None  # no pagination requested -> full list
        return super().paginate_queryset(queryset, request, view=view)
