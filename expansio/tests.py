from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import BudgetForm, SignupForm, TransactionForm
from .models import Budget, Category, EMI, Transaction
from .views import get_all_time_emi_burden


@override_settings(ALLOWED_HOSTS=['testserver'])
class ExpansioWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='owner@example.com',
            email='owner@example.com',
            password='StrongPass123!',
            first_name='Owner',
        )
        self.expense_category = Category.objects.create(
            user=self.user,
            name='Food',
            type='Expense',
        )
        self.income_category = Category.objects.create(
            user=self.user,
            name='Salary',
            type='Income',
        )
        self.client.force_login(self.user)

    def test_signup_verification_creates_one_profile_and_logs_in(self):
        self.client.logout()
        session = self.client.session
        session['signup_data'] = {
            'first_name': 'New User',
            'email': 'new@example.com',
            'age': 25,
            'city': 'Pune',
            'password_hash': make_password('StrongPass123!'),
        }
        session['signup_otp_hash'] = make_password('123456')
        session['signup_otp_expires_at'] = (timezone.now() + timedelta(minutes=5)).timestamp()
        session['signup_otp_attempts'] = 0
        session.save()

        response = self.client.post(reverse('expansio_verify_otp'), {'otp': '123456'})

        self.assertRedirects(response, reverse('expansio_dashboard'))
        user = User.objects.get(email='new@example.com')
        self.assertEqual(user.userprofile.city, 'Pune')
        self.assertEqual(User.objects.filter(email='new@example.com').count(), 1)

    def test_financial_forms_reject_invalid_values_and_mismatched_categories(self):
        transaction_form = TransactionForm(
            data={
                'category': self.expense_category.pk,
                'description': 'Invalid entry',
                'amount': '-5.00',
                'type': 'Income',
                'date': date.today(),
            },
            user=self.user,
        )
        budget_form = BudgetForm(
            data={'category': self.expense_category.pk, 'amount_limit': '-10.00'},
            user=self.user,
        )
        signup_form = SignupForm(
            data={
                'first_name': 'Too Young',
                'email': 'young@example.com',
                'age': 12,
                'city': 'Pune',
                'password': 'StrongPass123!',
            }
        )

        self.assertFalse(transaction_form.is_valid())
        self.assertIn('amount', transaction_form.errors)
        self.assertIn('category', transaction_form.errors)
        self.assertFalse(budget_form.is_valid())
        self.assertFalse(signup_form.is_valid())

    def test_invalid_periods_redirect_instead_of_returning_server_errors(self):
        dashboard_response = self.client.get(f"{reverse('expansio_dashboard')}?month=99&year=2026")
        reports_response = self.client.get(f"{reverse('expansio_reports')}?month=99&year=2026")

        self.assertRedirects(dashboard_response, reverse('expansio_dashboard'))
        self.assertRedirects(reports_response, reverse('expansio_reports'))

    def test_authenticated_pages_render(self):
        for url_name in (
            'expansio_dashboard',
            'expansio_transactions',
            'expansio_categories',
            'expansio_budgets',
            'expansio_reports',
            'expansio_emi',
            'expansio_profile',
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_category_filter_limits_transaction_results(self):
        Transaction.objects.create(
            user=self.user,
            category=self.expense_category,
            description='Food transaction',
            amount='100.00',
            type='Expense',
            date=date.today(),
        )
        Transaction.objects.create(
            user=self.user,
            category=self.income_category,
            description='Salary transaction',
            amount='1000.00',
            type='Income',
            date=date.today(),
        )

        response = self.client.get(
            f"{reverse('expansio_transactions')}?category={self.expense_category.pk}"
        )

        self.assertContains(response, 'Food transaction')
        self.assertNotContains(response, 'Salary transaction')

    def test_invalid_emi_is_rendered_as_a_form_error(self):
        response = self.client.post(
            reverse('expansio_emi'),
            {
                'description': 'Bad EMI',
                'amount': '-1',
                'frequency': 'Invalid',
                'start_date': 'not-a-date',
                'end_date': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(EMI.objects.filter(user=self.user).count(), 0)
        self.assertContains(response, 'Select a valid choice')

    def test_inactive_emi_does_not_reduce_all_time_net_worth(self):
        EMI.objects.create(
            user=self.user,
            description='Inactive installment',
            amount='100.00',
            frequency='Monthly',
            start_date=date(2026, 1, 1),
            active=False,
        )

        self.assertEqual(get_all_time_emi_burden(self.user, date(2026, 8, 16)), Decimal('0'))

    def test_dashboard_emi_toggle(self):
        today = timezone.localdate()
        Transaction.objects.create(
            user=self.user,
            category=self.income_category,
            description='Salary',
            amount='50000.00',
            type='Income',
            date=today,
        )
        EMI.objects.create(
            user=self.user,
            description='Car EMI',
            amount='5000.00',
            frequency='Monthly',
            start_date=today.replace(day=1),
            active=True,
        )

        # Default dashboard (show_emi=true)
        res_default = self.client.get(reverse('expansio_dashboard'))
        self.assertEqual(res_default.status_code, 200)
        self.assertContains(res_default, '45000.00')

        # With show_emi=false
        res_gross = self.client.get(f"{reverse('expansio_dashboard')}?show_emi=false")
        self.assertEqual(res_gross.status_code, 200)
        self.assertContains(res_gross, '50000.00')

    def test_budget_page_shows_spent_and_limits(self):
        today = timezone.localdate()
        budget = Budget.objects.create(category=self.expense_category, amount_limit='5000.00')
        Transaction.objects.create(
            user=self.user,
            category=self.expense_category,
            description='Dinner',
            amount='1500.00',
            type='Expense',
            date=today,
        )

        response = self.client.get(reverse('expansio_budgets'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1500.00')
        self.assertContains(response, '5000.00')
        self.assertContains(response, '30%')

    def test_logout_requires_post(self):
        get_response = self.client.get(reverse('expansio_logout'))
        post_response = self.client.post(reverse('expansio_logout'))

        self.assertEqual(get_response.status_code, 405)
        self.assertRedirects(post_response, reverse('expansio_login'))
