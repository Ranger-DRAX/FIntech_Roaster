"""
15 Advanced Django ORM Queries – Fully Commented
Run via: python manage.py shell < fintech/orm_queries.py
"""
import os
import sys
import django

# Setup Django environment (adjust settings module to your project)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangoInternals.settings")
django.setup()

from django.db.models import Sum, Count, Avg, Max, Min, F, Q, Subquery, OuterRef, Case, When, Value, DecimalField
from datetime import datetime, timedelta
from django.utils import timezone
from fintech.models import Account, Transaction, Merchant, Card
from django.contrib.auth import get_user_model

User = get_user_model()

# ==================================================================
# 1. Basic Q() - Find Active Savings accounts OR High Balance Checking accounts
# ==================================================================
q1 = Account.objects.filter(
    Q(status=Account.Status.ACTIVE, account_type=Account.Type.SAVINGS) |
    Q(balance__gte=5000, account_type=Account.Type.CHECKING)
)
"""
Explanation:
- Q objects allow OR conditions. Without Q, filter arguments are always AND.
- This query returns accounts that satisfy either:
    (status = 'active' AND type = 'savings')
    OR
    (balance >= 5000 AND type = 'checking')
- SQL equivalent:
    SELECT * FROM account
    WHERE (status = 'active' AND account_type = 'savings')
       OR (balance >= 5000 AND account_type = 'checking');
- Use Case: Bank marketing – target either active savers or high‑balance checking users.
"""

# ==================================================================
# 2. Aggregation - Get total volume of all completed transactions
# ==================================================================
q2 = Transaction.objects.completed().aggregate(total_volume=Sum('amount'))
"""
Explanation:
- .completed() is a custom manager method that filters status='completed'.
- aggregate() performs a calculation over the entire QuerySet and returns a dict.
- Sum('amount') generates SQL: SUM(amount) AS total_volume.
- SQL equivalent:
    SELECT SUM(amount) AS total_volume FROM transaction WHERE status = 'completed';
- Use Case: Dashboard metric – total processed value.
"""

# ==================================================================
# 3. Annotation with Count - Get Users and their total number of active cards
# ==================================================================
q3 = User.objects.annotate(
    active_card_count=Count('cards', filter=Q(cards__status=Card.Status.ACTIVE))
)
"""
Explanation:
- annotate() adds a temporary field (active_card_count) to each User object.
- Count('cards') counts related Card objects through the reverse relation.
- filter=... restricts which cards are counted (only active ones).
- SQL equivalent:
    SELECT user.*, COUNT(CASE WHEN card.status = 'active' THEN 1 END) AS active_card_count
    FROM user
    LEFT OUTER JOIN card ON user.id = card.user_id
    GROUP BY user.id;
- Use Case: Find users who have at least one active card, or sort by card count.
"""

# ==================================================================
# 4. Annotation with Sum - Total spending per account
# ==================================================================
q4 = Account.objects.annotate(
    total_spent=Sum('transactions__amount', filter=Q(transactions__transaction_type=Transaction.Type.DEBIT))
)
"""
Explanation:
- Sum('transactions__amount') sums the amount of all related transactions.
- filter restricts to only DEBIT transactions (money leaving the account).
- SQL uses a conditional SUM with CASE inside.
- SQL equivalent:
    SELECT account.*,
        SUM(CASE WHEN transaction.transaction_type = 'debit' THEN transaction.amount ELSE 0 END) AS total_spent
    FROM account
    LEFT OUTER JOIN transaction ON account.id = transaction.account_id
    GROUP BY account.id;
- Use Case: Customer spending analysis – find top spending accounts.
"""

# ==================================================================
# 5. F() Expression - Find accounts where updated_at is exactly created_at (never updated)
# ==================================================================
q5 = Account.objects.filter(updated_at=F('created_at'))
"""
Explanation:
- F() allows referencing a model field's current value in the database.
- Here we compare two columns: updated_at == created_at.
- This works without pulling values into Python.
- SQL equivalent:
    SELECT * FROM account WHERE updated_at = created_at;
- Use Case: Find accounts that have never been modified since creation.
"""

# ==================================================================
# 6. F() Math - Increase all Retail merchant fee rates by 0.001 (Simulated, not saving)
# ==================================================================
q6 = Merchant.objects.filter(category=Merchant.Category.RETAIL).update(fee_rate=F('fee_rate') + 0.001)
"""
Explanation:
- update() performs a bulk UPDATE, returning the number of changed rows.
- F('fee_rate') + 0.001 increments the existing value.
- This is atomic – no race conditions between read and write.
- SQL equivalent:
    UPDATE merchant SET fee_rate = fee_rate + 0.001 WHERE category = 'retail';
- Use Case: Adjust fee percentages for a merchant category globally.
"""

# ==================================================================
# 7. Relational Q() - Transactions on blocked cards OR failed transactions
# ==================================================================
q7 = Transaction.objects.filter(Q(card__status=Card.Status.BLOCKED) | Q(status=Transaction.Status.FAILED))
"""
Explanation:
- Q objects can span relationships: card__status traverses the card foreign key.
- This query combines two conditions across different tables.
- SQL equivalent:
    SELECT transaction.*
    FROM transaction
    LEFT OUTER JOIN card ON transaction.card_id = card.id
    WHERE card.status = 'blocked' OR transaction.status = 'failed';
- Use Case: Fraud detection – retrieve all suspicious transactions.
"""

# ==================================================================
# 8. Subqueries - Find the latest transaction date for each account
# ==================================================================
latest_txn = Transaction.objects.filter(account=OuterRef('pk')).order_by('-timestamp')
q8 = Account.objects.annotate(last_txn_date=Subquery(latest_txn.values('timestamp')[:1]))
"""
Explanation:
- OuterRef('pk') refers to the primary key of the outer Account query.
- latest_txn is a subquery that, for each account, orders transactions by timestamp descending.
- [:1] slices to get only the first (most recent) transaction.
- Subquery() injects this as a column in the outer SELECT.
- SQL equivalent:
    SELECT account.*,
        (SELECT timestamp FROM transaction WHERE account_id = account.id ORDER BY timestamp DESC LIMIT 1) AS last_txn_date
    FROM account;
- Use Case: Determine customer recency – last activity date.
"""

# ==================================================================
# 9. Subqueries inside filter - Find accounts whose last transaction was over $1000
# ==================================================================
q9 = Account.objects.annotate(
    last_amount=Subquery(latest_txn.values('amount')[:1])
).filter(last_amount__gt=1000)
"""
Explanation:
- Reuses the same subquery but annotates the amount of the last transaction.
- Then filters based on that annotated field.
- SQL equivalent:
    SELECT account.*, (SELECT amount FROM transaction ... LIMIT 1) AS last_amount
    FROM account
    WHERE (SELECT amount FROM transaction ... LIMIT 1) > 1000;
- Use Case: Identify high‑value customers for premium offers.
"""

# ==================================================================
# 10. Case/When Expressions - Categorize accounts into VIP or Standard based on balance
# ==================================================================
q10 = Account.objects.annotate(
    tier=Case(
        When(balance__gte=10000, then=Value('VIP')),
        default=Value('Standard'),
        output_field=django.db.models.CharField(),
    )
)
"""
Explanation:
- Case() mimics SQL's CASE WHEN.
- When(balance__gte=10000, then=Value('VIP')) adds a condition.
- default provides the fallback value.
- output_field must be specified when the result type isn't obvious.
- SQL equivalent:
    SELECT account.*,
        CASE WHEN balance >= 10000 THEN 'VIP' ELSE 'Standard' END AS tier
    FROM account;
- Use Case: Real‑time customer tier assignment for UI display.
"""

# ==================================================================
# 11. Multiple Aggregations - Get global transaction stats
# ==================================================================
q11 = Transaction.objects.aggregate(
    avg_txn=Avg('amount'), max_txn=Max('amount'), min_txn=Min('amount')
)
"""
Explanation:
- aggregate() can compute several aggregations in one database query.
- Returns a dict: {'avg_txn': Decimal, 'max_txn': Decimal, 'min_txn': Decimal}
- SQL equivalent:
    SELECT AVG(amount), MAX(amount), MIN(amount) FROM transaction;
- Use Case: Monitoring platform – overall system metrics.
"""

# ==================================================================
# 12. GroupBy equivalent - Total volume handled by each Merchant Category
# ==================================================================
q12 = Merchant.objects.values('category').annotate(
    volume=Sum('transactions__amount'), count=Count('transactions')
).order_by('-volume')
"""
Explanation:
- values('category') groups results by merchant category.
- annotate() then calculates aggregates per group.
- order_by('-volume') sorts categories by total volume descending.
- SQL equivalent:
    SELECT merchant.category,
        SUM(transaction.amount) AS volume,
        COUNT(transaction.id) AS count
    FROM merchant
    LEFT OUTER JOIN transaction ON merchant.id = transaction.merchant_id
    GROUP BY merchant.category
    ORDER BY volume DESC;
- Use Case: Revenue breakdown by industry.
"""

# ==================================================================
# 13. Exclude with Q() - Find accounts with no transactions in the last 30 days
# ==================================================================
thirty_days_ago = timezone.now() - timedelta(days=30)
q13 = Account.objects.exclude(
    transactions__timestamp__gte=thirty_days_ago
)
"""
Explanation:
- exclude() removes rows that match the condition.
- transactions__timestamp__gte=thirty_days_ago finds accounts that have at least one transaction within the last 30 days.
- Excluding them yields accounts with no recent transactions.
- SQL equivalent:
    SELECT account.* FROM account
    WHERE NOT EXISTS (
        SELECT 1 FROM transaction
        WHERE transaction.account_id = account.id AND transaction.timestamp >= '2026-05-11'
    );
- Use Case: Identify dormant accounts for re‑engagement campaigns.
"""

# ==================================================================
# 14. Nested Subquery - Find the merchant who handled the highest single transaction for each user
# ==================================================================
highest_user_txn = Transaction.objects.filter(
    account__user=OuterRef('pk')
).order_by('-amount')
q14 = User.objects.annotate(
    top_merchant_id=Subquery(highest_user_txn.values('merchant__name')[:1])
)
"""
Explanation:
- OuterRef('pk') refers to the user's primary key.
- highest_user_txn filters transactions belonging to that user, orders by amount descending.
- Subquery picks the merchant name from the first (highest) transaction.
- SQL equivalent:
    SELECT user.*,
        (SELECT merchant.name FROM transaction
         JOIN account ON transaction.account_id = account.id
         WHERE account.user_id = user.id
         ORDER BY transaction.amount DESC LIMIT 1) AS top_merchant_id
    FROM user;
- Use Case: Personalization – know which merchant a user spends the most at.
"""

# ==================================================================
# 15. Complex conditional Sum - Profit calculation for merchants (amount * fee_rate)
# ==================================================================
q15 = Merchant.objects.annotate(
    total_profit=Sum(
        F('transactions__amount') * F('fee_rate'),
        output_field=DecimalField()
    )
)
"""
Explanation:
- F('transactions__amount') * F('fee_rate') multiplies the transaction amount by the merchant's fee rate.
- Sum() aggregates this product over all transactions of each merchant.
- output_field=DecimalField() ensures proper decimal handling for money.
- SQL equivalent:
    SELECT merchant.*,
        SUM(transaction.amount * merchant.fee_rate) AS total_profit
    FROM merchant
    LEFT OUTER JOIN transaction ON merchant.id = transaction.merchant_id
    GROUP BY merchant.id;
- Use Case: Calculate platform revenue earned from each merchant.
"""

print("All 15 queries parsed successfully. To see results, add .values() or iterate.")