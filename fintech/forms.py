from django import forms
from .models import Account, Card, Merchant


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ["user", "account_number", "account_type", "currency", "status"]


class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ["user", "account", "card_number", "card_type", "status", "expiry_date", "cvv"]
        widgets = {
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "cvv": forms.PasswordInput(attrs={"maxlength": "4"}),
        }


class MerchantForm(forms.ModelForm):
    class Meta:
        model = Merchant
        fields = ["name", "merchant_id", "category", "is_active", "fee_rate"]
