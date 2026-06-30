from rest_framework import mixins, serializers, status, viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Account, Merchant, Transaction


# ── Serializers ───────────────────────────────────────────────────────────────

class MerchantSerializer(serializers.ModelSerializer):
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


class AccountSerializer(serializers.ModelSerializer):
    """
    id, created_at, and updated_at are read-only (auto-managed by the DB).
    user is writable so staff can create accounts on behalf of any user;
    override perform_create() to lock it to request.user if needed.
    """
    class Meta:
        model  = Account
        fields = [
            "id",
            "user",
            "account_number",
            "account_type",
            "balance",
            "currency",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TransactionSerializer(serializers.ModelSerializer):
    """
    transaction_id (UUID PK) and timestamp are read-only.
    card, merchant, and related_transaction are nullable FKs.
    """
    class Meta:
        model  = Transaction
        fields = [
            "transaction_id",
            "account",
            "card",
            "merchant",
            "amount",
            "currency",
            "transaction_type",
            "status",
            "description",
            "timestamp",
            "related_transaction",
        ]
        read_only_fields = ["transaction_id", "timestamp"]


# ── ① APIView ─────────────────────────────────────────────────────────────────

class MerchantListCreateAPIView(APIView):
    """
    GET  /api/v1/merchants/  → list all merchants
    POST /api/v1/merchants/  → create a merchant
    """

    def get(self, request):
        serializer = MerchantSerializer(Merchant.objects.all(), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MerchantSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MerchantDetailAPIView(APIView):
    """
    GET    /api/v1/merchants/<pk>/  → retrieve
    PUT    /api/v1/merchants/<pk>/  → full update
    PATCH  /api/v1/merchants/<pk>/  → partial update
    DELETE /api/v1/merchants/<pk>/  → delete
    """

    def get_object(self, pk):
        try:
            return Merchant.objects.get(pk=pk)
        except Merchant.DoesNotExist:
            return None

    def get(self, request, pk):
        merchant = self.get_object(pk)
        if merchant is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(MerchantSerializer(merchant).data)

    def put(self, request, pk):
        merchant = self.get_object(pk)
        if merchant is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = MerchantSerializer(merchant, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        merchant = self.get_object(pk)
        if merchant is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = MerchantSerializer(merchant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        merchant = self.get_object(pk)
        if merchant is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        merchant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── ② GenericAPIView + Mixins ─────────────────────────────────────────────────

class MerchantListCreateGenericView(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericAPIView,
):
    """
    GET  /api/v2/merchants/  → list
    POST /api/v2/merchants/  → create
    """
    queryset         = Merchant.objects.all()
    serializer_class = MerchantSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class MerchantDetailGenericView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericAPIView,
):
    """
    GET    /api/v2/merchants/<pk>/
    PUT    /api/v2/merchants/<pk>/
    PATCH  /api/v2/merchants/<pk>/
    DELETE /api/v2/merchants/<pk>/
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


# ── ③ ModelViewSet — Merchant ─────────────────────────────────────────────────

class MerchantViewSet(viewsets.ModelViewSet):
    """Full CRUD for Merchant. Wired via DefaultRouter at /api/v3/merchants/."""

    queryset         = Merchant.objects.all()
    serializer_class = MerchantSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()


# ── ④ ModelViewSet — Account ──────────────────────────────────────────────────

class AccountViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for Account. Wired via DefaultRouter at /api/v3/accounts/.

    Optional query-string filters:
      ?status=ACTIVE
      ?account_type=SAVINGS
      ?currency=USD
    """

    queryset         = Account.objects.all()
    serializer_class = AccountSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status       = self.request.query_params.get("status")
        account_type = self.request.query_params.get("account_type")
        currency     = self.request.query_params.get("currency")
        if status:
            qs = qs.filter(status=status)
        if account_type:
            qs = qs.filter(account_type=account_type)
        if currency:
            qs = qs.filter(currency=currency)
        return qs

    def perform_create(self, serializer):
        # Override to lock the account owner: serializer.save(user=self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        # Swap for soft-delete: instance.status = Account.Status.CLOSED; instance.save()
        instance.delete()


# ── ⑤ ModelViewSet — Transaction ─────────────────────────────────────────────

class TransactionViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for Transaction. Wired via DefaultRouter at /api/v3/transactions/.
    The router uses the UUID transaction_id as the lookup field automatically.

    Optional query-string filters:
      ?status=PENDING
      ?transaction_type=DEBIT
      ?account=<pk>
      ?currency=USD
    """

    queryset         = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def get_queryset(self):
        qs               = super().get_queryset()
        status           = self.request.query_params.get("status")
        transaction_type = self.request.query_params.get("transaction_type")
        account          = self.request.query_params.get("account")
        currency         = self.request.query_params.get("currency")
        if status:
            qs = qs.filter(status=status)
        if transaction_type:
            qs = qs.filter(transaction_type=transaction_type)
        if account:
            qs = qs.filter(account_id=account)
        if currency:
            qs = qs.filter(currency=currency)
        return qs

    def perform_create(self, serializer):
        # Extend to validate business rules (e.g. sufficient balance) or write AuditLog.
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        # Prefer reversals in production: instance.status = Transaction.Status.REVERSED
        instance.delete()
