"""
================================================================================
  DRF VIEW LAYERS — SAME ENDPOINT, 3 WAYS
  Model used: Merchant  (name, merchant_id, category, is_active, fee_rate)
================================================================================

PROGRESSION:
  1. APIView         → Full manual control, most boilerplate
  2. GenericAPIView  → Queryset/serializer wired in; mixins add behaviour
  3. ModelViewSet    → Everything auto-wired; router generates URLs

All three expose the same functionality:
  GET  /merchants/           → list all merchants
  POST /merchants/           → create a merchant
  GET  /merchants/<pk>/      → retrieve one merchant
  PUT  /merchants/<pk>/      → full update
  PATCH /merchants/<pk>/     → partial update
  DELETE /merchants/<pk>/    → delete

Run the server and test with httpie or curl:
  http GET  http://localhost:8000/fintech/api/v1/merchants/
  http POST http://localhost:8000/fintech/api/v1/merchants/ name="Shopify" merchant_id="SHF-001" category="RETAIL"
================================================================================
"""

from rest_framework import mixins, serializers, status, viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Merchant


# ─────────────────────────────────────────────────────────────────────────────
# SERIALIZER  (shared by all three implementations)
# ─────────────────────────────────────────────────────────────────────────────

class MerchantSerializer(serializers.ModelSerializer):
    """
    Converts Merchant instances ↔ JSON dicts.

    ModelSerializer auto-generates fields from the model, plus a default
    .create() and .update() so we don't have to write them.
    """

    class Meta:
        model  = Merchant
        fields = [
            "id",
            "name",
            "merchant_id",
            "category",
            "is_active",
            "fee_rate",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ─────────────────────────────────────────────────────────────────────────────
# ① APIView  ──────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
#
# APIView is the lowest-level DRF class. It sits one step above Django's
# plain View:
#   • Parses incoming request bodies (JSON, form data …) into request.data
#   • Wraps responses in DRF's Response (content-type negotiation)
#   • Handles authentication, permissions, and throttling hooks
#   • Does NOT know anything about your model/queryset — you write everything
#
# Key attributes you can set on the class:
#   authentication_classes  = [SessionAuthentication, BasicAuthentication]
#   permission_classes      = [IsAuthenticated]
#   throttle_classes        = [UserRateThrottle]
#   parser_classes          = [JSONParser, FormParser]
#   renderer_classes        = [JSONRenderer, BrowsableAPIRenderer]
#
# Lifecycle of a request:
#   dispatch() → initial() → [get/post/put/patch/delete]() → finalize_response()
#
# When to use:
#   • Non-CRUD endpoints (aggregations, webhooks, auth flows, actions)
#   • When business logic is too complex for generic shortcuts
# ─────────────────────────────────────────────────────────────────────────────

class MerchantListCreateAPIView(APIView):
    """
    GET  /api/v1/merchants/       → list all merchants
    POST /api/v1/merchants/       → create a new merchant

    Everything is explicit: we fetch the queryset, we call the serializer,
    we check is_valid(), we call save(), we return Response().
    """

    def get(self, request):
        """List all merchants."""
        merchants  = Merchant.objects.all()               # ← manual queryset
        serializer = MerchantSerializer(                  # ← manual serializer call
            merchants,
            many=True,                                    # ← serialize a list
        )
        return Response(serializer.data)                  # ← DRF Response (auto JSON)

    def post(self, request):
        """Create a merchant."""
        serializer = MerchantSerializer(data=request.data)  # ← bind incoming data

        if serializer.is_valid():                            # ← run all field validators
            serializer.save()                               # ← calls serializer.create()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,             # ← 201, not 200
            )

        # Validation failed → return 400 with error detail
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MerchantDetailAPIView(APIView):
    """
    GET    /api/v1/merchants/<pk>/   → retrieve single merchant
    PUT    /api/v1/merchants/<pk>/   → full replacement
    PATCH  /api/v1/merchants/<pk>/   → partial update
    DELETE /api/v1/merchants/<pk>/   → delete
    """

    def get_object(self, pk):
        """
        Helper to fetch the instance or raise 404.
        In a real project you'd use get_object_or_404(), but this makes
        the mechanics visible.
        """
        try:
            return Merchant.objects.get(pk=pk)
        except Merchant.DoesNotExist:
            return None

    def get(self, request, pk):
        merchant = self.get_object(pk)
        if merchant is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MerchantSerializer(merchant)
        return Response(serializer.data)

    def put(self, request, pk):
        """Full update — every non-read-only field is required."""
        merchant = self.get_object(pk)
        if merchant is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MerchantSerializer(
            merchant,
            data=request.data,
            partial=False,           # ← all fields required
        )
        if serializer.is_valid():
            serializer.save()        # ← calls serializer.update(merchant, validated_data)
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """Partial update — only send the fields you want to change."""
        merchant = self.get_object(pk)
        if merchant is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MerchantSerializer(
            merchant,
            data=request.data,
            partial=True,            # ← missing fields are OK
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        merchant = self.get_object(pk)
        if merchant is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        merchant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)   # 204 = No Content


# ─────────────────────────────────────────────────────────────────────────────
# ② GenericAPIView + Mixins  ──────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
#
# GenericAPIView extends APIView with two class-level shortcuts:
#   queryset         – the base ORM queryset (filtered with get_queryset())
#   serializer_class – the serializer to use   (via get_serializer_class())
#
# It also provides:
#   get_object()        → fetch a single instance (using pk/lookup_field);
#                         automatically calls check_object_permissions()
#   get_queryset()      → can be overridden per-request (e.g. filter by user)
#   get_serializer()    → instantiates the serializer with context injected
#   filter_backends     → list of filter/search/ordering backends
#   pagination_class    → pagination scheme
#
# Mixins live in rest_framework.mixins and each contributes ONE action:
#   ListModelMixin      → .list()     → GET list
#   CreateModelMixin    → .create()   → POST
#   RetrieveModelMixin  → .retrieve() → GET detail
#   UpdateModelMixin    → .update()   → PUT / .partial_update() → PATCH
#   DestroyModelMixin   → .destroy()  → DELETE
#
# You combine them by multiple-inheritance. The method names (list, create …)
# are NOT hooked to HTTP verbs automatically; you must wire them yourself:
#
#   def get(self, request, *args, **kwargs):
#       return self.list(request, *args, **kwargs)   # ← call the mixin method
#
# DRF also ships pre-mixed concrete generics (shortcuts) — you can use them
# directly instead of mixing yourself:
#   ListAPIView                = GenericAPIView + ListModelMixin
#   CreateAPIView              = GenericAPIView + CreateModelMixin
#   ListCreateAPIView          = GenericAPIView + List + Create
#   RetrieveAPIView            = GenericAPIView + RetrieveModelMixin
#   UpdateAPIView              = GenericAPIView + UpdateModelMixin
#   DestroyAPIView             = GenericAPIView + DestroyModelMixin
#   RetrieveUpdateAPIView      = GenericAPIView + Retrieve + Update
#   RetrieveDestroyAPIView     = GenericAPIView + Retrieve + Destroy
#   RetrieveUpdateDestroyAPIView = all three detail mixins
#
# When to use:
#   • Standard CRUD but you need to customise queryset per-request
#     (e.g. filter by request.user), override perform_create(), etc.
# ─────────────────────────────────────────────────────────────────────────────

class MerchantListCreateGenericView(
    mixins.ListModelMixin,    # contributes → .list()
    mixins.CreateModelMixin,  # contributes → .create()
    GenericAPIView,           # ← must be last in MRO; provides the plumbing
):
    """
    GET  /api/v2/merchants/   → delegates to ListModelMixin.list()
    POST /api/v2/merchants/   → delegates to CreateModelMixin.create()

    Notice how much less code there is compared to APIView:
      • no manual queryset loop
      • no manual serializer(many=True)
      • no manual is_valid() + save() + return in get()
    All of that lives inside the mixin methods.
    """

    queryset         = Merchant.objects.all()      # ← GenericAPIView reads this
    serializer_class = MerchantSerializer          # ← GenericAPIView reads this

    def get(self, request, *args, **kwargs):
        """Wire GET → list."""
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Wire POST → create."""
        return self.create(request, *args, **kwargs)

    # ── Optional hooks inside CreateModelMixin ──────────────────────────────
    # def perform_create(self, serializer):
    #     """Called just before save. Good place to attach request.user."""
    #     serializer.save(created_by=self.request.user)


class MerchantDetailGenericView(
    mixins.RetrieveModelMixin,  # → .retrieve()
    mixins.UpdateModelMixin,    # → .update() / .partial_update()
    mixins.DestroyModelMixin,   # → .destroy()
    GenericAPIView,
):
    """
    GET    /api/v2/merchants/<pk>/
    PUT    /api/v2/merchants/<pk>/
    PATCH  /api/v2/merchants/<pk>/
    DELETE /api/v2/merchants/<pk>/

    get_object() is inherited from GenericAPIView — it fetches by pk,
    handles 404 automatically, and calls check_object_permissions().
    """

    queryset         = Merchant.objects.all()
    serializer_class = MerchantSerializer

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    # ── Optional hooks inside UpdateModelMixin ──────────────────────────────
    # def perform_update(self, serializer):
    #     serializer.save(updated_by=self.request.user)


# ─────────────────────────────────────────────────────────────────────────────
# ③ ModelViewSet  ─────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
#
# ViewSet collapses multiple views (list + detail) into a single class.
# Instead of get/post/put/delete methods it has named ACTIONS:
#   list()           ← GET   /merchants/
#   create()         ← POST  /merchants/
#   retrieve()       ← GET   /merchants/<pk>/
#   update()         ← PUT   /merchants/<pk>/
#   partial_update() ← PATCH /merchants/<pk>/
#   destroy()        ← DELETE /merchants/<pk>/
#
# ModelViewSet = ViewSetMixin + all 5 mixins + GenericAPIView
# so it has every standard action out of the box.
#
# To get URLs you use a Router:
#   from rest_framework.routers import DefaultRouter
#   router = DefaultRouter()
#   router.register("merchants", MerchantViewSet, basename="merchant")
#   # generates:
#   #   /merchants/          → list, create
#   #   /merchants/<pk>/     → retrieve, update, partial_update, destroy
#
# Custom actions via @action:
#   @action(detail=False, methods=["get"])
#   def active(self, request):
#       """GET /merchants/active/ → only is_active=True"""
#       ...
#
#   @action(detail=True, methods=["post"])
#   def deactivate(self, request, pk=None):
#       """POST /merchants/<pk>/deactivate/"""
#       ...
#
# Other ViewSet classes:
#   ViewSet           → bare; no mixins; you define every action yourself
#   GenericViewSet    → ViewSet + GenericAPIView plumbing (queryset, serializer)
#                       but no actions; mix in what you need
#   ReadOnlyModelViewSet → list + retrieve only (no write actions)
#
# When to use:
#   • Standard CRUD with minimal customisation → fastest to write
#   • You want consistent URL patterns across your API
#   • You may add custom @action endpoints later
# ─────────────────────────────────────────────────────────────────────────────

class MerchantViewSet(viewsets.ModelViewSet):
    """
    The entire CRUD surface in ~4 lines of real code.

    Router wires:
      list()           ← GET  /api/v3/merchants/
      create()         ← POST /api/v3/merchants/
      retrieve()       ← GET  /api/v3/merchants/<pk>/
      update()         ← PUT  /api/v3/merchants/<pk>/
      partial_update() ← PATCH /api/v3/merchants/<pk>/
      destroy()        ← DELETE /api/v3/merchants/<pk>/
    """

    queryset         = Merchant.objects.all()
    serializer_class = MerchantSerializer

    # ── Common customisation points ─────────────────────────────────────────

    def get_queryset(self):
        """
        Override to filter per-request. E.g. only show active merchants
        unless the user is staff.
        """
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        """
        Called inside create() just before .save().
        Perfect for injecting fields derived from the request
        (e.g. owner, tenant, audit info).
        """
        serializer.save()   # you could pass extra kwargs here

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        """
        Override to do a soft-delete instead of a real DB delete.
        e.g.:  instance.is_active = False; instance.save()
        """
        instance.delete()
