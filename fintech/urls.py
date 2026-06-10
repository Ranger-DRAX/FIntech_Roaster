from django.urls import path

from . import views

app_name = "fintech"

urlpatterns = [
    path("", views.orm_queries_demo, name="orm-queries-demo"),
    path("accounts/", views.AccountListView.as_view(), name="account-list"),
    path("accounts/<int:pk>/", views.AccountDetailView.as_view(), name="account-detail"),
    path("transactions/", views.TransactionListView.as_view(), name="transaction-list"),
    path("merchants/", views.MerchantListView.as_view(), name="merchant-list"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path('statement-slow/', views.user_statement_slow, name='statement_slow'),
]
