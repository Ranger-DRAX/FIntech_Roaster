from django.db.models import (
    Sum, Count, Avg, Max, Min, F, Q, Subquery, OuterRef,
    Case, When, Value, DecimalField,
)
from django.db import models
from django.views.generic import ListView, DetailView, TemplateView
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

from .models import Account, Transaction, Merchant, Card


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
    # Simulate a logged-in user; replace 1 with actual user id
    transactions = Transaction.objects.filter(account__user_id=1)
    result = []
    for tx in transactions:
        result.append({
            'amount': tx.amount,
            'from_account': tx.account.account_number,   # extra query each time
            'merchant': tx.merchant.name if tx.merchant else None,
        })
    return render(request, 'fintech/statement.html', {'transactions': result})


def orm_queries_demo(request):
    """Execute all 15 advanced ORM queries and display results for debug toolbar inspection."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # ==================================================================
    # 1. Basic Q() - Find Active Savings accounts OR High Balance Checking
    # ==================================================================
    q1 = Account.objects.filter(
        Q(status=Account.Status.ACTIVE, account_type=Account.Type.SAVINGS) |
        Q(balance__gte=5000, account_type=Account.Type.CHECKING)
    )

    # ==================================================================
    # 2. Aggregation - Get total volume of all completed transactions
    # ==================================================================
    q2 = Transaction.objects.completed().aggregate(total_volume=Sum('amount'))

    # ==================================================================
    # 3. Annotation with Count - Users and their total active cards
    # ==================================================================
    q3 = User.objects.annotate(
        active_card_count=Count('cards', filter=Q(cards__status=Card.Status.ACTIVE))
    )

    # ==================================================================
    # 4. Annotation with Sum - Total spending per account
    # ==================================================================
    q4 = Account.objects.annotate(
        total_spent=Sum(
            'transactions__amount',
            filter=Q(transactions__transaction_type=Transaction.Type.DEBIT)
        )
    )

    # ==================================================================
    # 5. F() Expression - Accounts where updated_at == created_at
    # ==================================================================
    q5 = Account.objects.filter(updated_at=F('created_at'))

    # ==================================================================
    # 6. F() Math - Simulate fee rate increase (read-only, not saving)
    # ==================================================================
    from decimal import Decimal
    q6 = Merchant.objects.filter(category=Merchant.Category.RETAIL).annotate(
        new_fee_rate=F('fee_rate') + Decimal("0.001")
    )

    # ==================================================================
    # 7. Relational Q() - Transactions on blocked cards OR failed
    # ==================================================================
    q7 = Transaction.objects.filter(
        Q(card__status=Card.Status.BLOCKED) | Q(status=Transaction.Status.FAILED)
    )

    # ==================================================================
    # 8. Subqueries - Latest transaction date for each account
    # ==================================================================
    latest_txn = Transaction.objects.filter(account=OuterRef('pk')).order_by('-timestamp')
    q8 = Account.objects.annotate(last_txn_date=Subquery(latest_txn.values('timestamp')[:1]))

    # ==================================================================
    # 9. Subqueries inside filter - Accounts whose last transaction > $1000
    # ==================================================================
    q9 = Account.objects.annotate(
        last_amount=Subquery(latest_txn.values('amount')[:1])
    ).filter(last_amount__gt=1000)

    # ==================================================================
    # 10. Case/When Expressions - Categorize accounts as VIP or Standard
    # ==================================================================
    q10 = Account.objects.annotate(
        tier=Case(
            When(balance__gte=10000, then=Value('VIP')),
            default=Value('Standard'),
            output_field=models.CharField(),
        )
    )

    # ==================================================================
    # 11. Multiple Aggregations - Global transaction stats
    # ==================================================================
    q11 = Transaction.objects.aggregate(
        avg_txn=Avg('amount'), max_txn=Max('amount'), min_txn=Min('amount')
    )

    # ==================================================================
    # 12. GroupBy equivalent - Total volume by Merchant Category
    # ==================================================================
    q12 = Merchant.objects.values('category').annotate(
        volume=Sum('transactions__amount'), count=Count('transactions')
    ).order_by('-volume')

    # ==================================================================
    # 13. Exclude with Q() - Accounts with no transactions in last 30 days
    # ==================================================================
    thirty_days_ago = timezone.now() - timedelta(days=30)
    q13 = Account.objects.exclude(transactions__timestamp__gte=thirty_days_ago)

    # ==================================================================
    # 14. Nested Subquery - Top merchant name for each user
    # ==================================================================
    highest_user_txn = Transaction.objects.filter(
        account__user=OuterRef('pk')
    ).order_by('-amount')
    q14 = User.objects.annotate(
        top_merchant_name=Subquery(highest_user_txn.values('merchant__name')[:1])
    )

    # ==================================================================
    # 15. Complex conditional Sum - Profit for merchants (amount * fee_rate)
    # ==================================================================
    q15 = Merchant.objects.annotate(
        total_profit=Sum(
            F('transactions__amount') * F('fee_rate'),
            output_field=DecimalField()
        )
    )

    # Force evaluation of all querysets to generate SQL queries visible in debug toolbar
    list(q1)           # Query 1
    # q2 is already evaluated (it's an aggregate, returns dict)
    list(q3)           # Query 3
    list(q4)           # Query 4
    list(q5)           # Query 5
    list(q6)           # Query 6
    list(q7)           # Query 7
    list(q8)           # Query 8
    list(q9)           # Query 9
    list(q10)          # Query 10
    # q11 is already evaluated
    list(q12)          # Query 12
    list(q13)          # Query 13
    list(q14)          # Query 14
    list(q15)          # Query 15

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
