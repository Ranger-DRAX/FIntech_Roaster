import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint


# ─── Custom QuerySets ───────────────────────────────────────────────

class AccountQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=Account.Status.ACTIVE)

    def high_balance(self, min_balance=Decimal("10000.00")):
        return self.filter(balance__gte=min_balance)

    def by_type(self, account_type):
        return self.filter(account_type=account_type)


class CardQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=Card.Status.ACTIVE)

    def blocked(self):
        return self.filter(status=Card.Status.BLOCKED)

    def of_type(self, card_type):
        return self.filter(card_type=card_type)


class TransactionQuerySet(models.QuerySet):
    def pending(self):
        return self.filter(status=Transaction.Status.PENDING)

    def completed(self):
        return self.filter(status=Transaction.Status.COMPLETED)

    def failed(self):
        return self.filter(status=Transaction.Status.FAILED)

    def reversed(self):
        return self.filter(status=Transaction.Status.REVERSED)

    def debits(self):
        return self.filter(transaction_type=Transaction.Type.DEBIT)

    def credits(self):
        return self.filter(transaction_type=Transaction.Type.CREDIT)

    def today(self):
        import datetime
        from django.utils import timezone
        return self.filter(timestamp__date=timezone.localdate())


# ─── Custom Managers ────────────────────────────────────────────────

class AccountManager(models.Manager):
    def get_queryset(self):
        return AccountQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def high_balance(self, min_balance=Decimal("10000.00")):
        return self.get_queryset().high_balance(min_balance)

    def savings_accounts(self):
        return self.get_queryset().by_type(Account.Type.SAVINGS)


class CardManager(models.Manager):
    def get_queryset(self):
        return CardQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def blocked(self):
        return self.get_queryset().blocked()


class TransactionManager(models.Manager):
    def get_queryset(self):
        return TransactionQuerySet(self.model, using=self._db)

    def pending(self):
        return self.get_queryset().pending()

    def completed(self):
        return self.get_queryset().completed()

    def today(self):
        return self.get_queryset().today()


# ─── Models ─────────────────────────────────────────────────────────

class Account(models.Model):
    class Type(models.TextChoices):
        SAVINGS = "SAVINGS", "Savings"
        CHECKING = "CHECKING", "Checking"
        CREDIT = "CREDIT", "Credit"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        FROZEN = "FROZEN", "Frozen"
        CLOSED = "CLOSED", "Closed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="accounts",
    )
    account_number = models.CharField(max_length=20, unique=True, db_index=True)
    account_type = models.CharField(
        max_length=10, choices=Type.choices, default=Type.SAVINGS,
    )
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AccountManager()

    class Meta:
        db_table = "fintech_account"
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["account_type", "status"]),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(balance__gte=0),
                name="account_balance_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.account_number} ({self.balance} {self.currency})"


class Merchant(models.Model):
    class Category(models.TextChoices):
        RETAIL = "RETAIL", "Retail"
        FOOD = "FOOD", "Food & Beverage"
        TRAVEL = "TRAVEL", "Travel"
        ENTERTAINMENT = "ENTERTAINMENT", "Entertainment"
        UTILITIES = "UTILITIES", "Utilities"
        OTHER = "OTHER", "Other"

    name = models.CharField(max_length=200)
    merchant_id = models.CharField(max_length=50, unique=True, db_index=True)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER,
    )
    is_active = models.BooleanField(default=True)
    fee_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.0150"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fintech_merchant"
        indexes = [
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self):
        return self.name


class Card(models.Model):
    class Type(models.TextChoices):
        DEBIT = "DEBIT", "Debit"
        CREDIT = "CREDIT", "Credit"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        BLOCKED = "BLOCKED", "Blocked"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="cards",
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="cards",
    )
    card_number = models.CharField(max_length=16, unique=True, db_index=True)
    card_type = models.CharField(
        max_length=10, choices=Type.choices, default=Type.DEBIT,
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE,
    )
    expiry_date = models.DateField()
    cvv = models.CharField(max_length=4)
    issued_at = models.DateTimeField(auto_now_add=True)

    objects = CardManager()

    class Meta:
        db_table = "fintech_card"
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["account", "status"]),
        ]

    def __str__(self):
        return f"****{self.card_number[-4:]} ({self.card_type})"


class Transaction(models.Model):
    class Type(models.TextChoices):
        DEBIT = "DEBIT", "Debit"
        CREDIT = "CREDIT", "Credit"
        REFUND = "REFUND", "Refund"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        REVERSED = "REVERSED", "Reversed"

    transaction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="transactions",
    )
    card = models.ForeignKey(
        Card, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transactions",
    )
    merchant = models.ForeignKey(
        Merchant, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transactions",
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    transaction_type = models.CharField(
        max_length=10, choices=Type.choices,
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING,
    )
    description = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    related_transaction = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reversals",
    )

    objects = TransactionManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "fintech_transaction"
        indexes = [
            models.Index(fields=["account", "timestamp"]),
            models.Index(fields=["status", "timestamp"]),
            models.Index(fields=["transaction_type", "status"]),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(amount__gt=0),
                name="transaction_amount_positive",
            ),
        ]

    def __str__(self):
        return f"{self.transaction_type} {self.amount} [{self.status}]"
