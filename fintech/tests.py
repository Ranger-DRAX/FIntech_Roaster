import uuid
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection
from django.utils import timezone
from django.db.models import Sum, Count, F, Q, Avg, Value, OuterRef, Subquery
from django.db.models.functions import Round

from .models import Account, Card, Merchant, Transaction, AuditLog
from .models import AccountQuerySet, CardQuerySet, TransactionQuerySet

User = get_user_model()


class AccountModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass123")
        self.account = Account.objects.create(
            user=self.user,
            account_number="1001-001",
            account_type=Account.Type.SAVINGS,
            balance=Decimal("5000.00"),
            currency="USD",
        )

    def test_str(self):
        self.assertEqual(str(self.account), "1001-001 (5000.00 USD)")

    def test_default_status(self):
        self.assertEqual(self.account.status, Account.Status.ACTIVE)

    def test_default_balance(self):
        acc = Account.objects.create(
            user=self.user, account_number="1001-999"
        )
        self.assertEqual(acc.balance, Decimal("0.00"))

    def test_unique_account_number(self):
        with self.assertRaises(IntegrityError):
            Account.objects.create(
                user=self.user, account_number="1001-001"
            )

    def test_balance_non_negative_constraint(self):
        with self.assertRaises(IntegrityError):
            Account.objects.create(
                user=self.user,
                account_number="1001-002",
                balance=Decimal("-100.00"),
            )

    def test_account_type_choices(self):
        self.assertEqual(Account.Type.SAVINGS, "SAVINGS")
        self.assertEqual(Account.Type.CHECKING, "CHECKING")
        self.assertEqual(Account.Type.CREDIT, "CREDIT")

    def test_status_choices(self):
        self.assertEqual(Account.Status.ACTIVE, "ACTIVE")
        self.assertEqual(Account.Status.FROZEN, "FROZEN")
        self.assertEqual(Account.Status.CLOSED, "CLOSED")


class AccountCustomManagerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mgruser", password="pass123")
        self.acc_active = Account.objects.create(
            user=self.user, account_number="2001-001",
            balance=Decimal("15000.00"), status=Account.Status.ACTIVE,
        )
        self.acc_frozen = Account.objects.create(
            user=self.user, account_number="2001-002",
            balance=Decimal("500.00"), status=Account.Status.FROZEN,
        )

    def test_active_manager(self):
        active = Account.objects.active()
        self.assertIn(self.acc_active, active)
        self.assertNotIn(self.acc_frozen, active)

    def test_high_balance_manager(self):
        high = Account.objects.high_balance(Decimal("10000.00"))
        self.assertIn(self.acc_active, high)
        self.assertNotIn(self.acc_frozen, high)

    def test_savings_accounts_manager(self):
        Account.objects.create(
            user=self.user, account_number="2001-003",
            account_type=Account.Type.SAVINGS,
        )
        savings = Account.objects.savings_accounts()
        self.assertEqual(savings.count(), 1)


class MerchantModelTest(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(
            name="Test Shop",
            merchant_id="SHOP001",
            category=Merchant.Category.RETAIL,
            fee_rate=Decimal("0.0200"),
        )

    def test_str(self):
        self.assertEqual(str(self.merchant), "Test Shop")

    def test_default_is_active(self):
        self.assertTrue(self.merchant.is_active)

    def test_unique_merchant_id(self):
        with self.assertRaises(IntegrityError):
            Merchant.objects.create(name="Duplicate", merchant_id="SHOP001")


class CardModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carduser", password="pass123")
        self.account = Account.objects.create(
            user=self.user, account_number="3001-001",
        )
        self.card = Card.objects.create(
            user=self.user,
            account=self.account,
            card_number="4111111111111111",
            card_type=Card.Type.DEBIT,
            expiry_date=date(2028, 12, 31),
            cvv="123",
        )

    def test_str(self):
        self.assertIn("1111", str(self.card))
        self.assertIn("Debit", str(self.card))

    def test_default_status(self):
        self.assertEqual(self.card.status, Card.Status.ACTIVE)

    def test_unique_card_number(self):
        with self.assertRaises(IntegrityError):
            Card.objects.create(
                user=self.user, account=self.account,
                card_number="4111111111111111",
                expiry_date=date(2028, 12, 31), cvv="456",
            )

    def test_card_types(self):
        self.assertEqual(Card.Type.DEBIT, "DEBIT")
        self.assertEqual(Card.Type.CREDIT, "CREDIT")


class CardCustomManagerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cardmgr", password="pass123")
        self.account = Account.objects.create(
            user=self.user, account_number="3002-001",
        )
        self.card_active = Card.objects.create(
            user=self.user, account=self.account,
            card_number="4222222222222222",
            status=Card.Status.ACTIVE,
            expiry_date=date(2028, 1, 1), cvv="111",
        )
        self.card_blocked = Card.objects.create(
            user=self.user, account=self.account,
            card_number="4333333333333333",
            status=Card.Status.BLOCKED,
            expiry_date=date(2028, 1, 1), cvv="222",
        )

    def test_active_cards(self):
        active = Card.objects.active()
        self.assertIn(self.card_active, active)
        self.assertNotIn(self.card_blocked, active)

    def test_blocked_cards(self):
        blocked = Card.objects.blocked()
        self.assertIn(self.card_blocked, blocked)
        self.assertNotIn(self.card_active, blocked)


class TransactionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="txnuser", password="pass123")
        self.account = Account.objects.create(
            user=self.user, account_number="4001-001",
        )
        self.merchant = Merchant.objects.create(
            name="Test Store", merchant_id="STORE001",
        )
        self.txn = Transaction.objects.create(
            account=self.account,
            merchant=self.merchant,
            amount=Decimal("99.99"),
            transaction_type=Transaction.Type.DEBIT,
            status=Transaction.Status.COMPLETED,
            description="Test purchase",
        )

    def test_str(self):
        s = str(self.txn)
        self.assertIn("DEBIT", s)
        self.assertIn("99.99", s)
        self.assertIn("COMPLETED", s)

    def test_uuid_primary_key(self):
        self.assertIsInstance(self.txn.transaction_id, uuid.UUID)

    def test_default_status(self):
        txn = Transaction.objects.create(
            account=self.account, amount=Decimal("10.00"),
            transaction_type=Transaction.Type.CREDIT,
        )
        self.assertEqual(txn.status, Transaction.Status.PENDING)

    def test_amount_positive_constraint(self):
        with self.assertRaises(IntegrityError):
            Transaction.objects.create(
                account=self.account, amount=Decimal("-50.00"),
                transaction_type=Transaction.Type.DEBIT,
            )

    def test_related_transaction(self):
        reversal = Transaction.objects.create(
            account=self.account,
            amount=Decimal("99.99"),
            transaction_type=Transaction.Type.REFUND,
            status=Transaction.Status.COMPLETED,
            related_transaction=self.txn,
        )
        self.assertEqual(reversal.related_transaction, self.txn)
        self.assertIn(reversal, self.txn.reversals.all())


class TransactionCustomManagerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="txnmgr", password="pass123")
        self.account = Account.objects.create(
            user=self.user, account_number="4002-001",
        )
        self.pending = Transaction.objects.create(
            account=self.account, amount=Decimal("10.00"),
            transaction_type=Transaction.Type.DEBIT,
            status=Transaction.Status.PENDING,
        )
        self.completed = Transaction.objects.create(
            account=self.account, amount=Decimal("20.00"),
            transaction_type=Transaction.Type.DEBIT,
            status=Transaction.Status.COMPLETED,
        )
        self.failed = Transaction.objects.create(
            account=self.account, amount=Decimal("30.00"),
            transaction_type=Transaction.Type.DEBIT,
            status=Transaction.Status.FAILED,
        )

    def test_pending(self):
        pending = Transaction.objects.pending()
        self.assertIn(self.pending, pending)
        self.assertNotIn(self.completed, pending)

    def test_completed(self):
        completed = Transaction.objects.completed()
        self.assertIn(self.completed, completed)
        self.assertNotIn(self.pending, completed)

    def test_debits(self):
        debits = Transaction.objects.debits()
        self.assertEqual(debits.count(), 3)

    def test_credits(self):
        Transaction.objects.create(
            account=self.account, amount=Decimal("100.00"),
            transaction_type=Transaction.Type.CREDIT,
            status=Transaction.Status.COMPLETED,
        )
        credits = Transaction.objects.credits()
        self.assertEqual(credits.count(), 1)

    def test_all_objects_manager(self):
        all_txns = Transaction.all_objects.all()
        self.assertEqual(all_txns.count(), 3)


class AuditLogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="audituser", password="pass123")
        self.log = AuditLog.objects.create(
            user=self.user,
            action=AuditLog.Action.CREATE,
            model_name="Account",
            object_id="123",
            description="Created new account",
        )

    def test_str(self):
        s = str(self.log)
        self.assertIn("CREATE", s)
        self.assertIn("Account", s)

    def test_default_metadata(self):
        self.assertEqual(self.log.metadata, {})

    def test_ordering(self):
        AuditLog.objects.create(
            user=self.user, action=AuditLog.Action.UPDATE,
            model_name="Account", created_at=timezone.now() - timedelta(hours=1),
        )
        logs = list(AuditLog.objects.all())
        self.assertEqual(logs[0], self.log)


class ORMQueriesTest(TestCase):
    """Test the 15 ORM query patterns."""

    def setUp(self):
        self.user1 = User.objects.create_user(username="alice", password="pass123")
        self.user2 = User.objects.create_user(username="bob", password="pass123")

        self.acc1 = Account.objects.create(
            user=self.user1, account_number="5001-001",
            account_type=Account.Type.CHECKING, balance=Decimal("5000.00"),
        )
        self.acc2 = Account.objects.create(
            user=self.user1, account_number="5001-002",
            account_type=Account.Type.SAVINGS, balance=Decimal("25000.00"),
        )
        self.acc3 = Account.objects.create(
            user=self.user2, account_number="5002-001",
            account_type=Account.Type.CHECKING, balance=Decimal("1500.00"),
        )

        self.merchant1 = Merchant.objects.create(
            name="Amazon", merchant_id="AMZN", category="RETAIL",
        )
        self.merchant2 = Merchant.objects.create(
            name="Starbucks", merchant_id="SBUX", category="FOOD",
        )

        self.card1 = Card.objects.create(
            user=self.user1, account=self.acc1,
            card_number="6000000000000001",
            expiry_date=date(2028, 12, 31), cvv="111",
        )

        now = timezone.now()
        self.txn1 = Transaction.objects.create(
            account=self.acc1, card=self.card1, merchant=self.merchant1,
            amount=Decimal("150.00"), transaction_type=Transaction.Type.DEBIT,
            status=Transaction.Status.COMPLETED, timestamp=now,
        )
        self.txn2 = Transaction.objects.create(
            account=self.acc1, card=self.card1, merchant=self.merchant2,
            amount=Decimal("5.75"), transaction_type=Transaction.Type.DEBIT,
            status=Transaction.Status.COMPLETED, timestamp=now,
        )
        self.txn3 = Transaction.objects.create(
            account=self.acc2, merchant=self.merchant1,
            amount=Decimal("450.00"), transaction_type=Transaction.Type.DEBIT,
            status=Transaction.Status.PENDING, timestamp=now,
        )
        self.txn4 = Transaction.objects.create(
            account=self.acc3, merchant=self.merchant1,
            amount=Decimal("89.99"), transaction_type=Transaction.Type.DEBIT,
            status=Transaction.Status.COMPLETED, timestamp=now,
        )
        self.txn5 = Transaction.objects.create(
            account=self.acc3, merchant=None,
            amount=Decimal("200.00"), transaction_type=Transaction.Type.CREDIT,
            status=Transaction.Status.COMPLETED, timestamp=now,
        )

    def test_q1_basic_filter(self):
        result = Account.objects.filter(
            status=Account.Status.ACTIVE, balance__gt=Decimal("1000"),
        )
        self.assertEqual(result.count(), 3)

    def test_q2_select_related(self):
        result = list(
            Transaction.objects.select_related("account", "merchant")
            .filter(status=Transaction.Status.COMPLETED)
        )
        self.assertEqual(len(result), 3)
        for txn in result:
            self.assertIsNotNone(txn.account)
            self.assertIsNotNone(txn.merchant)

    def test_q3_prefetch_related(self):
        result = Account.objects.prefetch_related("transactions").filter(
            user=self.user1
        )
        for acc in result:
            _ = list(acc.transactions.all())

    def test_q4_f_expression(self):
        result = Account.objects.annotate(
            avg_txn=Avg("transactions__amount"),
        ).filter(balance__gt=F("avg_txn"), avg_txn__isnull=False)
        self.assertTrue(result.exists())

    def test_q5_q_or(self):
        result = Transaction.objects.filter(
            Q(amount__gte=Decimal("200")) | Q(status=Transaction.Status.FAILED)
        )
        self.assertIn(self.txn3, result)
        self.assertIn(self.txn5, result)

    def test_q6_aggregation(self):
        result = Merchant.objects.annotate(
            txn_count=Count("transactions"),
            total_volume=Sum("transactions__amount"),
        ).filter(txn_count__gt=0)
        self.assertTrue(result.exists())
        amazon = result.get(merchant_id="AMZN")
        self.assertEqual(amazon.txn_count, 3)

    def test_q7_case_when(self):
        from django.db.models import Case, When, Value, CharField
        result = Transaction.objects.annotate(
            size=Case(
                When(amount__lt=Decimal("50"), then=Value("small")),
                When(amount__gte=Decimal("50"), then=Value("large")),
                output_field=CharField(),
            ),
        )
        small = result.get(transaction_id=self.txn2.transaction_id)
        self.assertEqual(small.size, "small")
        large = result.get(transaction_id=self.txn1.transaction_id)
        self.assertEqual(large.size, "large")

    def test_q8_subquery(self):
        from django.db.models import Sum as SumF
        global_avg = Transaction.objects.aggregate(avg=Avg("amount"))["avg"]
        result = Account.objects.annotate(
            total_spend=SumF("transactions__amount"),
        ).filter(total_spend__gt=global_avg)
        self.assertTrue(result.exists())

    def test_q9_outerref(self):
        latest_sub = Transaction.objects.filter(
            account=OuterRef("account"),
        ).order_by("-timestamp")
        result = Transaction.objects.annotate(
            latest_ts=Subquery(latest_sub.values("timestamp")[:1]),
        ).filter(timestamp=F("latest_ts"))
        self.assertTrue(result.exists())

    def test_q11_coalesce(self):
        from django.db.models import Coalesce
        result = Account.objects.annotate(
            total_debits=Coalesce(
                Sum(
                    "transactions__amount",
                    filter=Q(transactions__transaction_type=Transaction.Type.DEBIT),
                ),
                Value(Decimal("0.00")),
            ),
        )
        self.assertTrue(result.exists())

    def test_q14_exists(self):
        from django.db.models import Exists
        failed_exists = Transaction.objects.filter(
            account=OuterRef("pk"),
            status=Transaction.Status.FAILED,
        )
        result = Account.objects.annotate(has_failed=Exists(failed_exists)).filter(
            has_failed=True
        )
        self.assertFalse(result.exists())

    def test_select_related_no_n_plus_one(self):
        with self.assertNumQueries(1):
            list(
                Transaction.objects.select_related("account__user", "merchant")[:10]
            )

    def test_prefetch_related_no_n_plus_one(self):
        with self.assertNumQueries(2):
            list(
                Account.objects.prefetch_related("transactions__merchant")[:10]
            )
