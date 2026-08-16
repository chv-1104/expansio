from django.contrib import admin

from .models import Budget, Category, EMI, Transaction, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'age', 'city', 'occupation')
    search_fields = ('user__username', 'user__email', 'city')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'user')
    list_filter = ('type',)
    search_fields = ('name', 'user__username')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount_limit')
    search_fields = ('category__name', 'category__user__username')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'type', 'category', 'user', 'date')
    list_filter = ('type', 'date')
    search_fields = ('description', 'category__name', 'user__username')
    list_select_related = ('category', 'user')


@admin.register(EMI)
class EMIAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'frequency', 'user', 'start_date', 'end_date', 'active')
    list_filter = ('frequency', 'active')
    search_fields = ('description', 'user__username')
