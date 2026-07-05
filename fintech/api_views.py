"""
api_views.py — DRF view layer for the UPay fintech app.

Three view-layer styles are demonstrated side-by-side:
  ①  APIView           (v1) — fully manual, most explicit
  ②  GenericAPIView    (v2) — queryset/serializer wired; mixin methods
  ③  ModelViewSet      (v3) — fully automatic + custom @action extras

New in this version
───────────────────
• Separate List / Detail serializers for Account and Transaction
• get_queryset  — scoped to the logged-in user (staff sees everything)
• get_serializer_class — returns the right serializer per action
• @action freeze    POST /api/v3/accounts/{id}/freeze/
• @action statement GET  /api/v3/accounts/{id}/statement/
• @action reverse   POST /api/v3/transactions/{id}/reverse/
"""

from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import Q, Sum
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Account, AuditLog, Merchant, Transaction


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


# ── Account serializers ───────────────────────────────────────────────────────

class AccountListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views — shows key fields only.
    Omits user FK and timestamps to reduce payload size.
    """
    class Meta:
        model  = Account
        fields = [
            "id",
            "account_number",
            "account_type",
            "balance",
            "currency",
            "status",
        ]
        read_only_fields = ["id"]


class AccountDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for retrieve / create / update — includes all fields.
    id, created_at, and updated_at are read-only (auto-managed by the DB).
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


# Keep a backward-compatible alias used by v1/v2 views
AccountSerializer = AccountDetailSerializer


# ── Transaction serializers ───────────────────────────────────────────────────

class TransactionListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views — key fields only.
    """
    class Meta:
        model  = Transaction
        fields = [
            "transaction_id",
            "account",
            "amount",
            "currency",
            "transaction_type",
            "status",
            "timestamp",
        ]
        read_only_fields = ["transaction_id", "timestamp"]


class TransactionDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for retrieve / create / update — all fields.
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


# Keep a backward-compatible alias
TransactionSerializer = TransactionDetailSerializer


# ── Helpers ───────────────────────────────────────────────────────────────────

def _log_audit(request, action_type, model_name, object_id, description, extra=None):
    """Write a record to AuditLog."""
    AuditLog.objects.create(
        user        = request.user if request.user.is_authenticated else None,
        action      = action_type,
        model_name  = model_name,
        object_id   = str(object_id),
        description = description,
        ip_address  = request.META.get("REMOTE_ADDR"),
        metadata    = extra or {},
    )


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

    Ownership scoping
    ─────────────────
    • Regular users  → see only their own accounts
    • Staff users    → see all accounts

    Optional query-string filters
    ─────────────────────────────
      ?status=ACTIVE
      ?account_type=SAVINGS
      ?currency=USD

    Custom actions
    ──────────────
    POST /api/v3/accounts/{id}/freeze/
        Freeze an ACTIVE account. Returns 400 if already FROZEN or CLOSED.

    GET  /api/v3/accounts/{id}/statement/
        Returns account transactions (newest first).
        Query params: ?from_date=YYYY-MM-DD  ?to_date=YYYY-MM-DD
        Response: { account, transactions, summary }
    """

    # Default queryset — overridden per-request by get_queryset()
    queryset = Account.objects.select_related("user").all()

    def get_queryset(self):
        """
        Scope the queryset to the logged-in user.
        Staff users bypass the filter and see every account.
        """
        qs = Account.objects.select_related("user").all()

        user = self.request.user
        if not user.is_staff:
            qs = qs.filter(user=user)

        # Optional query-string filters
        status_param       = self.request.query_params.get("status")
        account_type_param = self.request.query_params.get("account_type")
        currency_param     = self.request.query_params.get("currency")

        if status_param:
            qs = qs.filter(status=status_param)
        if account_type_param:
            qs = qs.filter(account_type=account_type_param)
        if currency_param:
            qs = qs.filter(currency=currency_param)

        return qs

    def get_serializer_class(self):
        """
        Return a lightweight serializer for list views and the full
        serializer for every other action (retrieve, create, update, etc.).
        """
        if self.action == "list":
            return AccountListSerializer
        return AccountDetailSerializer

    def perform_create(self, serializer):
        """Lock the account owner to the currently authenticated user."""
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        # Soft-delete alternative: instance.status = Account.Status.CLOSED; instance.save()
        instance.delete()

    # ── Custom actions ────────────────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="freeze")
    def freeze(self, request, pk=None):
        """
        POST /api/v3/accounts/{id}/freeze/

        Freeze an ACTIVE account. Responds with:
          200 — account successfully frozen
          400 — account is already FROZEN or CLOSED
        """
        account = self.get_object()  # handles 404 + object-level permissions

        if account.status == Account.Status.FROZEN:
            return Response(
                {"detail": "Account is already frozen."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if account.status == Account.Status.CLOSED:
            return Response(
                {"detail": "Cannot freeze a closed account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account.status = Account.Status.FROZEN
        account.save(update_fields=["status", "updated_at"])

        _log_audit(
            request,
            action_type = AuditLog.Action.UPDATE,
            model_name  = "Account",
            object_id   = account.pk,
            description = f"Account {account.account_number} frozen by {request.user}.",
        )

        serializer = AccountDetailSerializer(account, context={"request": request})
        return Response(
            {"detail": "Account has been frozen.", "account": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="statement")
    def statement(self, request, pk=None):
        """
        GET /api/v3/accounts/{id}/statement/

        Returns paginated transactions for the account, newest first.

        Query params
        ─────────────
          ?from_date=YYYY-MM-DD
          ?to_date=YYYY-MM-DD

        Response shape
        ──────────────
        {
            "account":      { ...AccountDetailSerializer fields... },
            "filters":      { "from_date": "...", "to_date": "..." },
            "summary":      { "total_debit": "...", "total_credit": "...", "count": N },
            "transactions": [ ...TransactionListSerializer fields... ]
        }
        """
        account = self.get_object()

        # Build the transaction queryset for this account
        txn_qs = Transaction.objects.filter(account=account).order_by("-timestamp")

        # Optional date filters
        from_date = request.query_params.get("from_date")
        to_date   = request.query_params.get("to_date")

        try:
            if from_date:
                txn_qs = txn_qs.filter(timestamp__date__gte=from_date)
            if to_date:
                txn_qs = txn_qs.filter(timestamp__date__lte=to_date)
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Aggregate summary
        summary = txn_qs.aggregate(
            total_debit  = Sum("amount", filter=Q(transaction_type=Transaction.Type.DEBIT)),
            total_credit = Sum("amount", filter=Q(transaction_type=Transaction.Type.CREDIT)),
        )

        return Response({
            "account": AccountDetailSerializer(account, context={"request": request}).data,
            "filters": {
                "from_date": from_date,
                "to_date":   to_date,
            },
            "summary": {
                "total_debit":  str(summary["total_debit"]  or Decimal("0.00")),
                "total_credit": str(summary["total_credit"] or Decimal("0.00")),
                "count":        txn_qs.count(),
            },
            "transactions": TransactionListSerializer(
                txn_qs, many=True, context={"request": request}
            ).data,
        })


# ── ⑤ ModelViewSet — Transaction ─────────────────────────────────────────────

class TransactionViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for Transaction. Wired via DefaultRouter at /api/v3/transactions/.
    The router uses the UUID transaction_id as the lookup field.

    Ownership scoping
    ─────────────────
    • Regular users → see only transactions on their own accounts
    • Staff users   → see all transactions

    Optional query-string filters
    ─────────────────────────────
      ?status=PENDING
      ?transaction_type=DEBIT
      ?account=<pk>
      ?currency=USD

    Custom actions
    ──────────────
    POST /api/v3/transactions/{transaction_id}/reverse/
        Reverse a COMPLETED transaction. Creates a linked REFUND transaction
        and marks the original as REVERSED. Returns 400 if not reversible.
    """

    queryset       = Transaction.objects.select_related("account", "card", "merchant").all()
    lookup_field   = "transaction_id"

    def get_queryset(self):
        """
        Scope transactions to accounts owned by the logged-in user.
        Staff users bypass the filter.
        """
        qs = Transaction.objects.select_related("account", "card", "merchant").all()

        user = self.request.user
        if not user.is_staff:
            qs = qs.filter(account__user=user)

        # Optional query-string filters
        status_param           = self.request.query_params.get("status")
        transaction_type_param = self.request.query_params.get("transaction_type")
        account_param          = self.request.query_params.get("account")
        currency_param         = self.request.query_params.get("currency")

        if status_param:
            qs = qs.filter(status=status_param)
        if transaction_type_param:
            qs = qs.filter(transaction_type=transaction_type_param)
        if account_param:
            qs = qs.filter(account_id=account_param)
        if currency_param:
            qs = qs.filter(currency=currency_param)

        return qs

    def get_serializer_class(self):
        """
        Return a lightweight serializer for list views and the full
        serializer for every other action.
        """
        if self.action == "list":
            return TransactionListSerializer
        return TransactionDetailSerializer

    def perform_create(self, serializer):
        # Extend here to validate business rules (e.g. sufficient balance).
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        # Prefer reversals in production.
        instance.delete()

    # ── Custom actions ────────────────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="reverse", lookup_field="transaction_id")
    def reverse(self, request, transaction_id=None):
        """
        POST /api/v3/transactions/{transaction_id}/reverse/

        Reverse a COMPLETED transaction atomically:
          1. Create a new REFUND Transaction linked via related_transaction.
          2. Mark the original transaction as REVERSED.

        Responds with:
          201 — reversal transaction created
          400 — transaction is not reversible (wrong status)
        """
        original = self.get_object()

        if original.status != Transaction.Status.COMPLETED:
            return Response(
                {
                    "detail": (
                        f"Only COMPLETED transactions can be reversed. "
                        f"Current status: {original.status}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with db_transaction.atomic():
            # Create the reversal
            reversal = Transaction.objects.create(
                account             = original.account,
                card                = original.card,
                merchant            = original.merchant,
                amount              = original.amount,
                currency            = original.currency,
                transaction_type    = Transaction.Type.REFUND,
                status              = Transaction.Status.COMPLETED,
                description         = f"Reversal of transaction {original.transaction_id}",
                related_transaction = original,
            )

            # Mark original as reversed
            original.status = Transaction.Status.REVERSED
            original.save(update_fields=["status"])

            _log_audit(
                request,
                action_type = AuditLog.Action.UPDATE,
                model_name  = "Transaction",
                object_id   = str(original.transaction_id),
                description = (
                    f"Transaction {original.transaction_id} reversed by {request.user}. "
                    f"Reversal ID: {reversal.transaction_id}."
                ),
                extra = {"reversal_id": str(reversal.transaction_id)},
            )

        return Response(
            {
                "detail":   "Transaction reversed successfully.",
                "original": TransactionDetailSerializer(
                    original, context={"request": request}
                ).data,
                "reversal": TransactionDetailSerializer(
                    reversal, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )
