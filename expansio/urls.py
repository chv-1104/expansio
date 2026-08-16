from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_view, name='expansio_health'),
    path('signup/', views.signup_view, name='expansio_signup'),
    path('verify-otp/', views.verify_otp_view, name='expansio_verify_otp'),
    path('login/', views.login_view, name='expansio_login'),
    path('logout/', views.logout_view, name='expansio_logout'),

    path('', views.dashboard_view, name='expansio_dashboard'),
    path('transactions/', views.transaction_list_view, name='expansio_transactions'),
    path('categories/', views.category_list_view, name='expansio_categories'),
    path('budgets/', views.budget_list_view, name='expansio_budgets'),
    path('reports/', views.reports_view, name='expansio_reports'),
    path('profile/', views.profile_view, name='expansio_profile'),
    path('transactions/delete/<int:pk>/', views.delete_transaction_view, name='expansio_delete_transaction'),
    path('categories/delete/<int:pk>/', views.delete_category_view, name='expansio_delete_category'),
    path('budgets/delete/<int:pk>/', views.delete_budget_view, name='expansio_delete_budget'),
    path('emi/', views.emi_list_view, name='expansio_emi'),
    path('emi/delete/<int:pk>/', views.delete_emi_view, name='expansio_delete_emi'),
]
