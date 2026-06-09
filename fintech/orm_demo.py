"""
Django ORM Concepts Demo
========================
Demonstrates: select_related, prefetch_related, F(), Q(), annotations
Run: python manage.py shell < fintech/orm_demo.py
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangoInternals.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import F, Q, Count, Sum, Avg, Max, Min, Value, OuterRef, Subquery
from fintech.models import Account, Card, Merchant, Transaction

User = get_user_model()

# ─── 0. SETUP: Create sample data ──────────────────────────────────
print("=" * 72)
print("0. SETUP: Creating sample data")
print("=" * 72)

# Users
alice, _ = User.objects.get_or_create(username="alice", defaults={"email": "alice@example.com"})
bob, _ = User.objects.get_or_create(username="bob", defaults={"email": "bob@example.com"})
charlie, _ = User.objects.get_or_create(username="charlie", defaults={"email": "charlie@example.com"})

# Merchants
amazon, _ = Merchant.objects.get_or_create(
    merchant_id="AMZN001",
    defaults={"name": "Amazon", "category": Merchant.Category.RETAIL, "fee_rate": Decimal("0.0200")},
)
starbucks, _ = Merchant.objects.get_or_create(
    merchant_id="SBUX002",
    defaults={"name": "Starbucks", "category": Merchant.Category.FOOD, "fee_rate": Decimal("0.0150")},
)
delta, _ = Merchant.objects.get_or_create(
    merchant_id="DAL003",
    defaults={"name": "Delta Airlines", "category": Merchant.Category.TRAVEL, "fee_rate": Decimal("0.0250")},
)

# Accounts
acc_a1, _ = Account.objects.get_or_create(
    account_number="1001-001",
    defaults={
        "user": alice, "account_type": Account.Type.CHECKING,
        "balance": Decimal("5000.00"), "currency": "USD",
    },
)
acc_a2, _ = Account.objects.get_or_create(
    account_number="1001-002",
    defaults={
        "user": alice, "account_type": Account.Type.SAVINGS,
        "balance": Decimal("25000.00"), "currency": "USD",
    },
)
acc_b1, _ = Account.objects.get_or_create(
    account_number="1002-001",
    defaults={
        "user": bob, "account_type": Account.Type.CHECKING,
        "balance": Decimal("1500.00"), "currency": "USD",
    },
)
acc_c1, _ = Account.objects.get_or_create(
    account_number="1003-001",
    defaults={
        "user": charlie, "account_type": Account.Type.CREDIT,
        "balance": Decimal("500.00"), "currency": "USD", "status": Account.Status.FROZEN,
    },
)

# Cards
card_a1, _ = Card.objects.get_or_create(
    card_number="4111111111111111",
    defaults={
        "user": alice, "account": acc_a1, "card_type": Card.Type.DEBIT,
        "expiry_date": date(2028, 12, 31), "cvv": "123",
    },
)
card_a2, _ = Card.objects.get_or_create(
    card_number="5500000000000004",
    defaults={
        "user": alice, "account": acc_a2, "card_type": Card.Type.CREDIT,
        "expiry_date": date(2027, 6, 30), "cvv": "456",
    },
)
card_b1, _ = Card.objects.get_or_create(
    card_number="4222222222222222",
    defaults={
        "user": bob, "account": acc_b1, "card_type": Card.Type.DEBIT,
        "expiry_date": date(2029, 3, 15), "cvv": "789",
    },
)

# Transactions
now = timezone.now()
yesterday = now - timedelta(days=1)

Transaction.objects.all().delete()

txns = Transaction.objects.bulk_create([
    Transaction(
        account=acc_a1, card=card_a1, merchant=amazon,
        amount=Decimal("150.00"), transaction_type=Transaction.Type.DEBIT,
        status=Transaction.Status.COMPLETED, timestamp=now - timedelta(hours=2),
        description="Amazon purchase - electronics",
    ),
    Transaction(
        account=acc_a1, card=card_a1, merchant=starbucks,
        amount=Decimal("5.75"), transaction_type=Transaction.Type.DEBIT,
        status=Transaction.Status.COMPLETED, timestamp=now - timedelta(hours=5),
        description="Morning coffee",
    ),
    Transaction(
        account=acc_a2, card=card_a2, merchant=delta,
        amount=Decimal("450.00"), transaction_type=Transaction.Type.DEBIT,
        status=Transaction.Status.PENDING, timestamp=now - timedelta(minutes=30),
        description="Flight booking",
    ),
    Transaction(
        account=acc_b1, card=card_b1, merchant=amazon,
        amount=Decimal("89.99"), transaction_type=Transaction.Type.DEBIT,
        status=Transaction.Status.COMPLETED, timestamp=yesterday,
        description="Book purchase",
    ),
    Transaction(
        account=acc_a1, card=card_a1, merchant=starbucks,
        amount=Decimal("5.75"), transaction_type=Transaction.Type.DEBIT,
        status=Transaction.Status.FAILED, timestamp=yesterday,
        description="Coffee - insufficient funds",
    ),
    Transaction(
        account=acc_b1, card=None, merchant=None,
        amount=Decimal("200.00"), transaction_type=Transaction.Type.CREDIT,
        status=Transaction.Status.COMPLETED, timestamp=yesterday,
        description="Salary deposit",
    ),
])

print(f"Created {len(txns)} transactions")
print()


# ═══════════════════════════════════════════════════════════════════
# 1. select_related  — FK & OneToOne join in ONE query
# ═══════════════════════════════════════════════════════════════════
print("=" * 72)
print("1. select_related  — Joins FK relationships in a single query")
print("=" * 72)

# Without select_related — N+1 queries
print("\n>>> Without select_related (N+1 problem):")
txns_naive = Transaction.objects.filter(amount__gt=Decimal("50"))
for t in txns_naive:
    # Each iteration hits DB for account, then merchant
    print(f"  {t.description}: account={t.account.account_number}, merchant={t.merchant.name if t.merchant else 'N/A'}")

# With select_related — one query with JOINs
print("\n>>> With select_related — single DB query:")
txns_optimized = Transaction.objects.filter(amount__gt=Decimal("50")).select_related("account", "merchant")
for t in txns_optimized:
    print(f"  {t.description}: account={t.account.account_number}, merchant={t.merchant.name if t.merchant else 'N/A'}")

# Chained select_related (deeper joins)
print("\n>>> Deep select_related — account__user:")
txns_deep = Transaction.objects.filter(
    amount__gt=Decimal("10"),
).select_related("account__user", "card", "merchant")
for t in txns_deep:
    print(f"  {t.description}: user={t.account.user.username}, card_ending={str(t.card.card_number)[-4:] if t.card else 'N/A'}")


# ═══════════════════════════════════════════════════════════════════
# 2. prefetch_related  — Reverse FK & M2M in batch queries
# ═══════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("2. prefetch_related  — Batch-fetches reverse FK/M2M relations")
print("=" * 72)

# Without prefetch_related
print("\n>>> Without prefetch_related (N+1):")
accounts = Account.objects.filter(user=alice)
for acc in accounts:
    txn_list = acc.transactions.all()  # Extra query per account
    print(f"  {acc.account_number}: {txn_list.count()} transactions")

# With prefetch_related
print("\n>>> With prefetch_related — 2 queries total:")
accounts = Account.objects.filter(user=alice).prefetch_related("transactions")
for acc in accounts:
    txn_list = acc.transactions.all()  # No extra query — cached
    print(f"  {acc.account_number}: {txn_list.count()} transactions")

# Prefetch with custom queryset
print("\n>>> Prefetch with filtered queryset:")
from django.db.models import Prefetch
completed_txns = Transaction.objects.filter(status=Transaction.Status.COMPLETED)
accounts = Account.objects.filter(user=alice).prefetch_related(
    Prefetch("transactions", queryset=completed_txns, to_attr="completed_txns"),
)
for acc in accounts:
    print(f"  {acc.account_number}: {len(acc.completed_txns)} completed transactions")

# Multi-level prefetch
print("\n>>> Multi-level: prefetch cards then transactions per card:")
users = User.objects.filter(username__in=["alice", "bob"]).prefetch_related(
    Prefetch("accounts", queryset=Account.objects.active()),
    "accounts__cards",
)
for u in users:
    for a in u.accounts.all():
        print(f"  {u.username} — {a.account_number}: {a.cards.count()} card(s)")


# ═══════════════════════════════════════════════════════════════════
# 3. F() expressions  — Refer to fields in queries
# ═══════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("3. F() expressions  — Refer to field values in queries")
print("=" * 72)

# F() in filter — find low-balance accounts
print("\n>>> F() in filter — accounts where balance < 100 * transaction count:")
from django.db.models import Count
accounts_with_many_txns = Account.objects.annotate(
    txn_count=Count("transactions"),
).filter(balance__lt=F("txn_count") * Decimal("100.00"))
for a in accounts_with_many_txns:
    print(f"  {a.account_number}: balance={a.balance}, txn_count={a.txn_count}")

# F() in update — increment field atomically
print("\n>>> F() in update — add 2% interest to all savings accounts:")
savings_count = Account.objects.filter(account_type=Account.Type.SAVINGS).update(
    balance=F("balance") * Decimal("1.02"),
)
print(f"  Updated {savings_count} savings accounts (interest applied)")

# F() with arithmetic in annotation
print("\n>>> F() in annotation — remaining credit limit (credit accounts):")
credit_accounts = Account.objects.filter(
    account_type=Account.Type.CREDIT,
).annotate(
    credit_limit=Value(Decimal("10000.00")),
    available_credit=F("credit_limit") - F("balance"),
)
for a in credit_accounts:
    print(f"  {a.account_number}: balance={a.balance}, available={a.available_credit}")


# ═══════════════════════════════════════════════════════════════════
# 4. Q() expressions  — Complex OR/AND/NOT queries
# ═══════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("4. Q() expressions  — Complex queries with OR/AND/NOT")
print("=" * 72)

# Q with OR — find high-value OR failed transactions
print("\n>>> Q() OR — high-value OR failed transactions:")
q_high_value = Q(amount__gte=Decimal("200"))
q_failed = Q(status=Transaction.Status.FAILED)
high_or_failed = Transaction.objects.filter(q_high_value | q_failed)
for t in high_or_failed:
    print(f"  {t.description}: {t.amount} [{t.status}]")

# Q with AND (default)
print("\n>>> Q() AND — completed AND debit transactions:")
q_completed = Q(status=Transaction.Status.COMPLETED)
q_debit = Q(transaction_type=Transaction.Type.DEBIT)
completed_debits = Transaction.objects.filter(q_completed & q_debit)
for t in completed_debits:
    print(f"  {t.description}: {t.amount}")

# Q with NOT — find non-retail merchant transactions
print("\n>>> Q() NOT — transactions NOT at retail merchants:")
q_not_retail = ~Q(merchant__category=Merchant.Category.RETAIL)
q_has_merchant = Q(merchant__isnull=False)
non_retail = Transaction.objects.filter(q_has_merchant & q_not_retail)
for t in non_retail:
    print(f"  {t.description}: merchant={t.merchant.name} ({t.merchant.category})")

# Complex Q — find pending/travel purchases by Alice
print("\n>>> Complex Q — pending OR travel transactions for Alice:")
q_alice = Q(account__user__username="alice")
q_pending = Q(status=Transaction.Status.PENDING)
q_travel = Q(merchant__category=Merchant.Category.TRAVEL)
result = Transaction.objects.filter(q_alice & (q_pending | q_travel))
for t in result:
    print(f"  {t.description}: {t.amount} [{t.status}] (merchant: {t.merchant.name if t.merchant else 'N/A'})")


# ═══════════════════════════════════════════════════════════════════
# 5. Annotations  — Add computed fields to querysets
# ═══════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("5. Annotations  — Aggregate/compute fields per row")
print("=" * 72)

# Count annotation
print("\n>>> Annotate — transaction count per account:")
accounts_with_count = Account.objects.annotate(txn_count=Count("transactions"))
for a in accounts_with_count:
    print(f"  {a.account_number}: {a.txn_count} transaction(s)")

# Sum annotation
print("\n>>> Annotate — total spend per account:")
accounts_with_spend = Account.objects.annotate(
    total_spent=Sum(
        "transactions__amount",
        filter=Q(transactions__transaction_type=Transaction.Type.DEBIT),
    ),
)
for a in accounts_with_spend:
    print(f"  {a.account_number}: spent ${a.total_spent or 0:.2f}")

# Multiple annotations
print("\n>>> Annotate — stats per merchant:")
merchant_stats = Merchant.objects.annotate(
    txn_count=Count("transactions"),
    total_volume=Sum("transactions__amount"),
    avg_ticket=Avg("transactions__amount"),
    max_txn=Max("transactions__amount"),
    min_txn=Min("transactions__amount"),
)
for m in merchant_stats:
    print(
        f"  {m.name}: {m.txn_count} txns, "
        f"total=${m.total_volume or 0:.2f}, "
        f"avg=${m.avg_ticket or 0:.2f}"
    )

# Conditional annotation with Case/When
print("\n>>> Conditional annotation — tag transaction size:")
from django.db.models import Case, When, Value, CharField
tagged_txns = Transaction.objects.annotate(
    size_tag=Case(
        When(amount__lt=Decimal("10"), then=Value("micro")),
        When(amount__lt=Decimal("100"), then=Value("small")),
        When(amount__lt=Decimal("500"), then=Value("medium")),
        When(amount__gte=Decimal("500"), then=Value("large")),
        output_field=CharField(),
    ),
)
for t in tagged_txns:
    print(f"  ${t.amount:>7.2f} — {t.size_tag:>6} | {t.description[:40]}")

# Combined: annotations + F() + Q()
print("\n>>> Combined — accounts where spend > 50% of balance:")
accounts = Account.objects.annotate(
    total_debits=Sum("transactions__amount",
                     filter=Q(transactions__transaction_type=Transaction.Type.DEBIT,
                              transactions__status=Transaction.Status.COMPLETED)),
).filter(
    Q(total_debits__isnull=False) & Q(total_debits__gt=F("balance") * Decimal("0.5"))
)
for a in accounts:
    print(f"  {a.account_number}: balance=${a.balance}, spent=${a.total_debits:.2f}")


# ─── Cleanup note ──────────────────────────────────────────────────
print("\n" + "=" * 72)
print("DEMO COMPLETE")
print("=" * 72)
print("Note: F() update modified the DB (interest applied to savings).")
print("Re-run the setup section to reset data if needed.")
