from django.urls import path

from . import views

app_name = "fintech"

urlpatterns = [
    path("", views.orm_queries_demo, name="orm-queries-demo"),
    path("home/", views.HomePageView.as_view(), name="home"),
    path("health/", views.HealthCheckView.as_view(), name="health-check"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    # Accounts
    path("accounts/", views.AccountListView.as_view(), name="account-list"),
    path("accounts/create/", views.AccountCreateView.as_view(), name="account-create"),
    path("accounts/<int:pk>/", views.AccountDetailView.as_view(), name="account-detail"),
    path("accounts/<int:pk>/update/", views.AccountUpdateView.as_view(), name="account-update"),
    # Cards
    path("cards/", views.CardListView.as_view(), name="card-list"),
    path("cards/create/", views.CardCreateView.as_view(), name="card-create"),
    path("cards/<int:pk>/update/", views.CardUpdateView.as_view(), name="card-update"),
    path("cards/<int:pk>/delete/", views.CardDeleteView.as_view(), name="card-delete"),
    # Transactions
    path("transactions/", views.TransactionListView.as_view(), name="transaction-list"),
    # Merchants
    path("merchants/", views.MerchantListView.as_view(), name="merchant-list"),
    path("merchants/create/", views.MerchantCreateView.as_view(), name="merchant-create"),
    path("merchants/<int:pk>/update/", views.MerchantUpdateView.as_view(), name="merchant-update"),
    path("merchants/<int:pk>/delete/", views.MerchantDeleteView.as_view(), name="merchant-delete"),
    # Legacy
    path('statement-slow/', views.user_statement_slow, name='statement_slow'),
]
