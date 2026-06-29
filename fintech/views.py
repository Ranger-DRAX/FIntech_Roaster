from django.db.models import (
    Sum, Count, Avg, Max, Min, F, Q, Subquery, OuterRef,
    Case, When, Value, DecimalField,
)
from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.shortcuts import render
from datetime import timedelta

from .models import Account, Transaction, Merchant, Card
from .forms import AccountForm, CardForm, MerchantForm


class HomePageView(TemplateView):
    template_name = "fintech/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_accounts"] = Account.objects.count()
        ctx["active_accounts"] = Account.objects.active().count()
        ctx["total_transactions"] = Transaction.objects.count()
        ctx["completed_transactions"] = Transaction.objects.completed().count()
        ctx["total_volume"] = (
            Transaction.objects.completed().aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
        ctx["top_merchants"] = (
            Merchant.objects.annotate(
                total_volume=Sum("transactions__amount"),
                txn_count=Count("transactions"),
            )
            .order_by("-total_volume")[:5]
        )
        return ctx


class HealthCheckView(View):
    def get(self, request):
        account_count = Account.objects.count()
        active_accounts = Account.objects.active().count()
        frozen_accounts = Account.objects.filter(status=Account.Status.FROZEN).count()
        closed_accounts = Account.objects.filter(status=Account.Status.CLOSED).count()
        card_count = Card.objects.count()
        merchant_count = Merchant.objects.count()
        txn_count = Transaction.objects.count()
        total_volume = Transaction.objects.completed().aggregate(total=Sum("amount"))["total"] or 0
        pending_txns = Transaction.objects.pending().count()
        failed_txns = Transaction.objects.filter(status=Transaction.Status.FAILED).count()

        return render(request, "fintech/health_check.html", {
            "account_count": account_count,
            "active_accounts": active_accounts,
            "frozen_accounts": frozen_accounts,
            "closed_accounts": closed_accounts,
            "card_count": card_count,
            "merchant_count": merchant_count,
            "txn_count": txn_count,
            "total_volume": total_volume,
            "pending_txns": pending_txns,
            "failed_txns": failed_txns,
            "request_method": request.method,
            "request_path": request.path,
            "now": timezone.now(),
        })


class AccountListView(ListView):
    model = Account
    template_name = "fintech/account_list.html"
    context_object_name = "accounts"
    paginate_by = 20

    def get_queryset(self):
        return (
            Account.objects
            .select_related("user")
            .prefetch_related("cards", "transactions")
            .order_by("-created_at")
        )


class AccountDetailView(DetailView):
    model = Account
    template_name = "fintech/account_detail.html"
    context_object_name = "account"

    def get_queryset(self):
        return Account.objects.select_related("user").prefetch_related(
            "cards", "transactions__merchant"
        )


class AccountCreateView(CreateView):
    model = Account
    form_class = AccountForm
    template_name = "fintech/account_form.html"
    success_url = reverse_lazy("fintech:account-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Create Account"
        ctx["submit_label"] = "Create Account"
        return ctx


class AccountUpdateView(UpdateView):
    model = Account
    form_class = AccountForm
    template_name = "fintech/account_form.html"
    success_url = reverse_lazy("fintech:account-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"Edit Account {self.object.account_number}"
        ctx["submit_label"] = "Save Changes"
        return ctx


class TransactionListView(ListView):
    model = Transaction
    template_name = "fintech/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 50

    def get_queryset(self):
        return (
            Transaction.objects
            .select_related("account__user", "card", "merchant")
            .order_by("-timestamp")
        )


class CardListView(ListView):
    model = Card
    template_name = "fintech/card_list.html"
    context_object_name = "cards"
    paginate_by = 20

    def get_queryset(self):
        return (
            Card.objects
            .select_related("user", "account")
            .order_by("-issued_at")
        )


class CardCreateView(CreateView):
    model = Card
    form_class = CardForm
    template_name = "fintech/card_form.html"
    success_url = reverse_lazy("fintech:card-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Issue New Card"
        ctx["submit_label"] = "Create Card"
        return ctx


class CardUpdateView(UpdateView):
    model = Card
    form_class = CardForm
    template_name = "fintech/card_form.html"
    success_url = reverse_lazy("fintech:card-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"Edit Card ****{self.object.card_number[-4:]}"
        ctx["submit_label"] = "Save Changes"
        return ctx


class CardDeleteView(DeleteView):
    model = Card
    template_name = "fintech/card_confirm_delete.html"
    success_url = reverse_lazy("fintech:card-list")
    context_object_name = "card"


class MerchantListView(ListView):
    model = Merchant
    template_name = "fintech/merchant_list.html"
    context_object_name = "merchants"
    paginate_by = 20

    def get_queryset(self):
        return Merchant.objects.annotate(
            total_volume=Sum("transactions__amount"),
            txn_count=Count("transactions"),
        ).order_by("-total_volume")


class MerchantCreateView(CreateView):
    model = Merchant
    form_class = MerchantForm
    template_name = "fintech/merchant_form.html"
    success_url = reverse_lazy("fintech:merchant-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Create Merchant"
        ctx["submit_label"] = "Create Merchant"
        return ctx


class MerchantUpdateView(UpdateView):
    model = Merchant
    form_class = MerchantForm
    template_name = "fintech/merchant_form.html"
    success_url = reverse_lazy("fintech:merchant-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"Edit Merchant {self.object.name}"
        ctx["submit_label"] = "Save Changes"
        return ctx


class MerchantDeleteView(DeleteView):
    model = Merchant
    template_name = "fintech/merchant_confirm_delete.html"
    success_url = reverse_lazy("fintech:merchant-list")
    context_object_name = "merchant"


class DashboardView(TemplateView):
    template_name = "fintech/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_accounts"] = Account.objects.count()
        ctx["active_accounts"] = Account.objects.active().count()
        ctx["total_transactions"] = Transaction.objects.count()
        ctx["completed_transactions"] = Transaction.objects.completed().count()
        ctx["total_volume"] = (
            Transaction.objects.completed().aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
        ctx["top_merchants"] = (
            Merchant.objects.annotate(
                total_volume=Sum("transactions__amount"),
                txn_count=Count("transactions"),
            )
            .order_by("-total_volume")[:5]
        )
        return ctx


def user_statement_slow(request):
    transactions = Transaction.objects.filter(account__user_id=1)
    result = []
    for tx in transactions:
        result.append({
            'amount': tx.amount,
            'from_account': tx.account.account_number,
            'merchant': tx.merchant.name if tx.merchant else None,
        })
    return render(request, 'fintech/statement.html', {'transactions': result})


def orm_queries_demo(request):
    """Execute all 15 advanced ORM queries and display results for debug toolbar inspection."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    q1 = Account.objects.filter(
        Q(status=Account.Status.ACTIVE, account_type=Account.Type.SAVINGS) |
        Q(balance__gte=5000, account_type=Account.Type.CHECKING)
    )

    q2 = Transaction.objects.completed().aggregate(total_volume=Sum('amount'))

    q3 = User.objects.annotate(
        active_card_count=Count('cards', filter=Q(cards__status=Card.Status.ACTIVE))
    )

    q4 = Account.objects.annotate(
        total_spent=Sum(
            'transactions__amount',
            filter=Q(transactions__transaction_type=Transaction.Type.DEBIT)
        )
    )

    q5 = Account.objects.filter(updated_at=F('created_at'))

    from decimal import Decimal
    q6 = Merchant.objects.filter(category=Merchant.Category.RETAIL).annotate(
        new_fee_rate=F('fee_rate') + Decimal("0.001")
    )

    q7 = Transaction.objects.filter(
        Q(card__status=Card.Status.BLOCKED) | Q(status=Transaction.Status.FAILED)
    )

    latest_txn = Transaction.objects.filter(account=OuterRef('pk')).order_by('-timestamp')
    q8 = Account.objects.annotate(last_txn_date=Subquery(latest_txn.values('timestamp')[:1]))

    q9 = Account.objects.annotate(
        last_amount=Subquery(latest_txn.values('amount')[:1])
    ).filter(last_amount__gt=1000)

    q10 = Account.objects.annotate(
        tier=Case(
            When(balance__gte=10000, then=Value('VIP')),
            default=Value('Standard'),
            output_field=models.CharField(),
        )
    )

    q11 = Transaction.objects.aggregate(
        avg_txn=Avg('amount'), max_txn=Max('amount'), min_txn=Min('amount')
    )

    q12 = Merchant.objects.values('category').annotate(
        volume=Sum('transactions__amount'), count=Count('transactions')
    ).order_by('-volume')

    thirty_days_ago = timezone.now() - timedelta(days=30)
    q13 = Account.objects.exclude(transactions__timestamp__gte=thirty_days_ago)

    highest_user_txn = Transaction.objects.filter(
        account__user=OuterRef('pk')
    ).order_by('-amount')
    q14 = User.objects.annotate(
        top_merchant_name=Subquery(highest_user_txn.values('merchant__name')[:1])
    )

    q15 = Merchant.objects.annotate(
        total_profit=Sum(
            F('transactions__amount') * F('fee_rate'),
            output_field=DecimalField()
        )
    )

    list(q1)
    list(q3)
    list(q4)
    list(q5)
    list(q6)
    list(q7)
    list(q8)
    list(q9)
    list(q10)
    list(q12)
    list(q13)
    list(q14)
    list(q15)

    queries = [
        {"num": 1, "name": "Q() - Active Savings OR High Balance Checking", "count": q1.count()},
        {"num": 2, "name": "Aggregation - Total volume of completed transactions", "result": q2},
        {"num": 3, "name": "Annotation with Count - Users with active cards", "count": q3.count()},
        {"num": 4, "name": "Annotation with Sum - Total spending per account", "count": q4.count()},
        {"num": 5, "name": "F() Expression - Accounts never updated", "count": q5.count()},
        {"num": 6, "name": "F() Math - Simulated fee rate increase", "count": q6.count()},
        {"num": 7, "name": "Relational Q() - Blocked card OR failed transactions", "count": q7.count()},
        {"num": 8, "name": "Subquery - Latest transaction date per account", "count": q8.count()},
        {"num": 9, "name": "Subquery filter - Accounts with last txn > $1000", "count": q9.count()},
        {"num": 10, "name": "Case/When - VIP vs Standard tier", "count": q10.count()},
        {"num": 11, "name": "Multiple Aggregations - Global txn stats", "result": q11},
        {"num": 12, "name": "GroupBy - Volume by merchant category", "count": q12.count()},
        {"num": 13, "name": "Exclude with Q() - Dormant accounts (30 days)", "count": q13.count()},
        {"num": 14, "name": "Nested Subquery - Top merchant per user", "count": q14.count()},
        {"num": 15, "name": "Complex Sum - Merchant profit calculation", "count": q15.count()},
    ]

    return render(request, "fintech/orm_queries_demo.html", {"queries": queries})
