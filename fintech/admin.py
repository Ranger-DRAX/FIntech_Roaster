from django.contrib import admin

from .models import Account, AuditLog, Card, Merchant, Transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("account_number", "user", "account_type", "balance", "currency", "status")
    list_filter = ("account_type", "status", "currency")
    search_fields = ("account_number", "user__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ("name", "merchant_id", "category", "is_active", "fee_rate")
    list_filter = ("category", "is_active")
    search_fields = ("name", "merchant_id")


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("card_number", "user", "account", "card_type", "status", "expiry_date")
    list_filter = ("card_type", "status")
    search_fields = ("card_number", "user__username")
    readonly_fields = ("issued_at",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "account", "amount", "transaction_type", "status", "timestamp")
    list_filter = ("transaction_type", "status", "currency")
    search_fields = ("account__account_number", "description")
    readonly_fields = ("timestamp",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "model_name", "user", "object_id", "created_at")
    list_filter = ("action", "model_name")
    search_fields = ("user__username", "description")
    readonly_fields = ("created_at",)
