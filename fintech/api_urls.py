"""
DRF API URLs — three view-layer styles side-by-side.

Mounted under:  fintech/api/
Full base URL:  http://localhost:8000/fintech/api/

  v1/ → APIView              (manual, most explicit)
  v2/ → GenericAPIView       (queryset/serializer wired; mixin methods)
  v3/ → ModelViewSet + Router (fully automatic; shortest code)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    MerchantDetailAPIView,
    MerchantDetailGenericView,
    MerchantListCreateAPIView,
    MerchantListCreateGenericView,
    MerchantViewSet,
)

# ── v1: APIView ──────────────────────────────────────────────────────────────
# Two separate classes; URLs wired manually just like Django's URLconf always
# has been.  No magic — each path maps to exactly one class.
v1_urlpatterns = [
    path("merchants/",       MerchantListCreateAPIView.as_view(), name="v1-merchant-list"),
    path("merchants/<int:pk>/", MerchantDetailAPIView.as_view(),  name="v1-merchant-detail"),
]

# ── v2: GenericAPIView + Mixins ───────────────────────────────────────────────
# Identical URL structure; classes are smaller because mixins handle the
# repetitive logic.
v2_urlpatterns = [
    path("merchants/",          MerchantListCreateGenericView.as_view(), name="v2-merchant-list"),
    path("merchants/<int:pk>/", MerchantDetailGenericView.as_view(),     name="v2-merchant-detail"),
]

# ── v3: ModelViewSet + Router ─────────────────────────────────────────────────
# The Router generates ALL six URL patterns from a single .register() call.
# DefaultRouter also auto-generates a browsable API root at /api/v3/
router = DefaultRouter()
router.register(
    prefix   = "merchants",          # URL prefix
    viewset  = MerchantViewSet,
    basename = "v3-merchant",        # used for URL name generation
)
# router.urls generates:
#   v3-merchant-list       → GET/POST /merchants/
#   v3-merchant-detail     → GET/PUT/PATCH/DELETE /merchants/<pk>/

v3_urlpatterns = router.urls

# ── Main pattern — included from fintech/urls.py ────────────────────────────
urlpatterns = [
    path("v1/", include(v1_urlpatterns)),
    path("v2/", include(v2_urlpatterns)),
    path("v3/", include(v3_urlpatterns)),
]
