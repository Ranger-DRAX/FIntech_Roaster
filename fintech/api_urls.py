"""
DRF API URLs — three view-layer styles, mounted under fintech/api/.
Full base URL: http://localhost:8000/fintech/api/

  v1/  APIView               manual, most explicit
  v2/  GenericAPIView        queryset/serializer wired; mixin methods
  v3/  ModelViewSet + Router fully automatic; shortest code

v3 resources (DefaultRouter):
  merchants/    MerchantViewSet
  accounts/     AccountViewSet
  transactions/ TransactionViewSet
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    AccountViewSet,
    MerchantDetailAPIView,
    MerchantDetailGenericView,
    MerchantListCreateAPIView,
    MerchantListCreateGenericView,
    MerchantViewSet,
    TransactionViewSet,
)

# ── v1: APIView ───────────────────────────────────────────────────────────────
v1_urlpatterns = [
    path("merchants/",          MerchantListCreateAPIView.as_view(), name="v1-merchant-list"),
    path("merchants/<int:pk>/", MerchantDetailAPIView.as_view(),     name="v1-merchant-detail"),
]

# ── v2: GenericAPIView + Mixins ───────────────────────────────────────────────
v2_urlpatterns = [
    path("merchants/",          MerchantListCreateGenericView.as_view(), name="v2-merchant-list"),
    path("merchants/<int:pk>/", MerchantDetailGenericView.as_view(),     name="v2-merchant-detail"),
]

# ── v3: ModelViewSet + DefaultRouter ─────────────────────────────────────────
# Each register() generates:
#   <basename>-list   → GET /POST  /<prefix>/
#   <basename>-detail → GET/PUT/PATCH/DELETE  /<prefix>/<pk>/
router = DefaultRouter()
router.register(prefix="merchants",    viewset=MerchantViewSet,     basename="v3-merchant")
router.register(prefix="accounts",     viewset=AccountViewSet,      basename="account")
router.register(prefix="transactions", viewset=TransactionViewSet,  basename="transaction")

v3_urlpatterns = router.urls

# ── Main urlpatterns — included from fintech/urls.py ─────────────────────────
urlpatterns = [
    path("v1/", include(v1_urlpatterns)),
    path("v2/", include(v2_urlpatterns)),
    path("v3/", include(v3_urlpatterns)),
]
