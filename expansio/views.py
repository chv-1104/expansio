import calendar
import logging
import secrets
from datetime import date, timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction as db_transaction
from django.db.models import Sum, Q
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST

from .models import Category, Budget, Transaction, UserProfile, EMI
from .forms import (
    BudgetForm,
    CategoryForm,
    EMIForm,
    LoginForm,
    OTPForm,
    SignupForm,
    TransactionForm,
    UserProfileUpdateForm,
)


logger = logging.getLogger(__name__)
ZERO = Decimal('0')
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


def health_view(request):
    """Lightweight deployment health check that does not require authentication."""
    return JsonResponse({'status': 'ok'})


def home_view(request):
    """Public home/landing page showcasing Expansio architecture and features."""
    return render(request, 'home.html')


def clear_signup_session(request):
    for key in ('signup_data', 'signup_otp_hash', 'signup_otp_expires_at', 'signup_otp_attempts'):
        request.session.pop(key, None)


def get_requested_period(request, default_date=None):
    """Return a validated (month, year) tuple, or None for malformed input."""
    default_date = default_date or timezone.localdate()
    month_raw = request.GET.get('month')
    year_raw = request.GET.get('year')

    if not month_raw and not year_raw:
        return default_date.month, default_date.year

    try:
        month = int(month_raw)
        year = int(year_raw)
    except (TypeError, ValueError):
        return None

    if not 1 <= month <= 12 or not 2000 <= year <= 2100:
        return None
    return month, year

@login_required(login_url='expansio_login')
def profile_view(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.save()
            user_profile.age = form.cleaned_data['age']
            user_profile.city = form.cleaned_data['city']
            user_profile.occupation = form.cleaned_data.get('occupation', '')
            user_profile.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('expansio_profile')
    else:
        initial_data = {
            'first_name': request.user.first_name,
            'age': user_profile.age,
            'city': user_profile.city,
            'occupation': user_profile.occupation,
        }
        form = UserProfileUpdateForm(initial=initial_data)
    return render(request, 'profile.html', {
        'form': form,
        'user_profile': user_profile,
        'email': request.user.email,
        'member_since': request.user.date_joined,
    })

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('expansio_dashboard')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            otp = f'{secrets.randbelow(1_000_000):06d}'
            request.session['signup_data'] = {
                'first_name': form.cleaned_data['first_name'].strip(),
                'email': form.cleaned_data['email'],
                'age': form.cleaned_data['age'],
                'city': form.cleaned_data['city'].strip(),
                'password_hash': make_password(form.cleaned_data['password']),
            }
            request.session['signup_otp_hash'] = make_password(otp)
            request.session['signup_otp_expires_at'] = (timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)).timestamp()
            request.session['signup_otp_attempts'] = 0

            try:
                html_message = render_to_string('emails/otp_email.html', {
                    'otp': otp,
                    'first_name': form.cleaned_data['first_name']
                })
                plain_message = strip_tags(html_message)
                
                send_mail(
                    'Your Expansio OTP Verification Code',
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [form.cleaned_data['email']],
                    html_message=html_message,
                    fail_silently=False,
                )
                return redirect('expansio_verify_otp')
            except Exception:
                logger.exception('Failed to send signup OTP email.')
                clear_signup_session(request)
                messages.error(request, 'We could not send the verification email. Please try again shortly.')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

def verify_otp_view(request):
    signup_data = request.session.get('signup_data')
    otp_hash = request.session.get('signup_otp_hash')
    expires_at = request.session.get('signup_otp_expires_at')
    if not signup_data or not otp_hash or not expires_at:
        return redirect('expansio_signup')

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            if timezone.now().timestamp() > float(expires_at):
                clear_signup_session(request)
                messages.error(request, 'This verification code has expired. Please sign up again.')
                return redirect('expansio_signup')

            if not check_password(form.cleaned_data['otp'], otp_hash):
                attempts = request.session.get('signup_otp_attempts', 0) + 1
                request.session['signup_otp_attempts'] = attempts
                if attempts >= OTP_MAX_ATTEMPTS:
                    clear_signup_session(request)
                    messages.error(request, 'Too many incorrect attempts. Please sign up again.')
                    return redirect('expansio_signup')
                messages.error(request, 'Invalid verification code. Please try again.')
                return render(request, 'verify_otp.html', {'form': form})

            try:
                with db_transaction.atomic():
                    user = User.objects.create(
                        username=signup_data['email'],
                        email=signup_data['email'],
                        password=signup_data['password_hash'],
                        first_name=signup_data['first_name'],
                    )
                    UserProfile.objects.update_or_create(
                        user=user,
                        defaults={'age': signup_data['age'], 'city': signup_data['city']},
                    )
            except IntegrityError:
                clear_signup_session(request)
                messages.error(request, 'An account with this email already exists.')
                return redirect('expansio_signup')

            clear_signup_session(request)
            login(request, user)
            return redirect('expansio_dashboard')
    else:
        form = OTPForm()
    return render(request, 'verify_otp.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('expansio_dashboard')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            # Authenticate typically uses username, which we set as the email
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('expansio_dashboard')
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

@require_POST
def logout_view(request):
    logout(request)
    return redirect('expansio_login')

def get_emi_deductions(user, year, month):
    """Calculate total EMI burden for a specific month/year"""
    emis = EMI.objects.filter(user=user, active=True, start_date__lte=date(year, month, calendar.monthrange(year, month)[1]))
    total_deduction = ZERO
    
    for emi in emis:
        # Skip if end_date exists and is in the past
        if emi.end_date and emi.end_date < date(year, month, 1):
            continue
            
        if emi.frequency == 'Monthly':
            total_deduction += emi.amount
        elif emi.frequency == 'Weekly':
            # Count occurrences of start_date's weekday in the target month
            weekday = emi.start_date.weekday() # 0=Mon, 6=Sun
            first_day, last_day = calendar.monthrange(year, month)
            count = 0
            for d in range(1, last_day + 1):
                curr_date = date(year, month, d)
                if curr_date.weekday() == weekday and curr_date >= emi.start_date:
                    if not emi.end_date or curr_date <= emi.end_date:
                        count += 1
            total_deduction += (count * emi.amount)
            
    return total_deduction

def get_all_time_emi_burden(user, target_date=None):
    """Calculate total accumulated EMI burden up to a specific date (defaults to today)"""
    if target_date is None:
        target_date = timezone.localdate()

    emis = EMI.objects.filter(user=user, active=True, start_date__lte=target_date)
    total_accumulated = ZERO
    
    for emi in emis:
        # The EMI stops accumulating at either its end_date or the target_date
        effective_end = min(emi.end_date, target_date) if emi.end_date else target_date
        
        if emi.frequency == 'Monthly':
            # Count months: (Year difference * 12) + Month difference
            months_diff = (effective_end.year - emi.start_date.year) * 12 + (effective_end.month - emi.start_date.month)
            count = months_diff
            # If the end day is >= start day, it means the current month's payment has occurred
            if effective_end.day >= emi.start_date.day:
                count += 1
            total_accumulated += (max(0, count) * emi.amount)
            
        elif emi.frequency == 'Weekly':
            days_diff = (effective_end - emi.start_date).days
            count = (days_diff // 7) + 1
            total_accumulated += (max(0, count) * emi.amount)
            
    return total_accumulated

@login_required(login_url='expansio_login')
def dashboard_view(request):
    now = timezone.localdate()
    period = get_requested_period(request, now)
    if period is None:
        messages.error(request, 'Choose a valid month and year.')
        return redirect('expansio_dashboard')
    month, year = period
    
    # Calculate previous and next month for navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    # Selected Month Statistics
    transactions = Transaction.objects.filter(user=request.user, date__month=month, date__year=year).select_related('category').order_by('-date')
    recent_transactions = transactions[:5]
    
    # EMI Deductions
    emi_total = get_emi_deductions(request.user, year, month)
    
    # EMI Toggle State
    show_emi = request.GET.get('show_emi', 'true') == 'true'
    
    # Gross income (before any EMI deduction)
    gross_income = (Transaction.objects.filter(user=request.user, type='Income', date__month=month, date__year=year).aggregate(Sum('amount'))['amount__sum'] or ZERO)
    # Disposable income (after EMI)
    if show_emi:
        disposable_income = max(ZERO, gross_income - emi_total)
    else:
        disposable_income = gross_income
    
    selected_expenses = Transaction.objects.filter(user=request.user, type='Expense', date__month=month, date__year=year).aggregate(Sum('amount'))['amount__sum'] or ZERO
    
    
    # All-time Net Worth (Cumulative)
    all_income = Transaction.objects.filter(user=request.user, type='Income').aggregate(Sum('amount'))['amount__sum'] or ZERO
    all_expenses = Transaction.objects.filter(user=request.user, type='Expense').aggregate(Sum('amount'))['amount__sum'] or ZERO
    total_balance = all_income - all_expenses
    
    emi_all_time = ZERO
    if show_emi:
        # Deduct all-time EMI burden from net worth
        emi_all_time = get_all_time_emi_burden(request.user)
        total_balance -= emi_all_time
    
    # Category summary for the selected month
    categories = Category.objects.filter(user=request.user).annotate(
        total_spent=Sum('transaction__amount', filter=Q(
            transaction__type='Expense', 
            transaction__date__month=month, 
            transaction__date__year=year
        ))
    ).filter(total_spent__gt=0)
    
    context = {
        'recent_transactions': recent_transactions,
        'gross_income': gross_income,
        'disposable_income': disposable_income,
        'selected_expenses': selected_expenses,
        'emi_burden': emi_total,
        'total_balance': total_balance,
        'emi_all_time': emi_all_time,
        'categories_summary': categories,
        'current_month_name': calendar.month_name[month],
        'current_month': month,
        'current_year': year,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'is_current_period': (month == now.month and year == now.year),
        'show_emi': show_emi
    }
    return render(request, 'dashboard.html', context)

@login_required(login_url='expansio_login')
def transaction_list_view(request):
    transactions = Transaction.objects.filter(user=request.user).select_related('category')
    period_name = 'All Time'
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')
    has_period_filter = request.GET.get('month') is not None or request.GET.get('year') is not None

    if query:
        transactions = transactions.filter(Q(description__icontains=query) | Q(category__name__icontains=query))
        period_name = f"Search results for '{query}'"

    if category_id:
        try:
            category = get_object_or_404(Category, pk=int(category_id), user=request.user)
        except (TypeError, ValueError):
            messages.error(request, 'Choose a valid category.')
            return redirect('expansio_transactions')
        transactions = transactions.filter(category=category)
        period_name = category.name if not query else f"{period_name} in {category.name}"

    if has_period_filter:
        period = get_requested_period(request)
        if period is None:
            messages.error(request, 'Choose a valid month and year.')
            return redirect('expansio_transactions')
        month, year = period
        transactions = transactions.filter(date__month=month, date__year=year)
        period_name = f"{period_name} - {calendar.month_name[month]} {year}" if query or category_id else f"{calendar.month_name[month]} {year}"

    transactions = transactions.order_by('-date')

    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            return redirect('expansio_transactions')
    else:
        # Pre-fill type if provided in GET
        initial_type = request.GET.get('type', 'Expense')
        if initial_type not in dict(Transaction.TYPE_CHOICES):
            initial_type = 'Expense'
        form = TransactionForm(initial={'type': initial_type}, user=request.user)
    return render(request, 'transactions.html', {
        'transactions': transactions, 
        'form': form,
        'period_name': period_name
    })

@login_required(login_url='expansio_login')
def category_list_view(request):
    categories = Category.objects.filter(user=request.user)
    if request.method == 'POST':
        form = CategoryForm(request.POST, user=request.user)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            return redirect('expansio_categories')
    else:
        form = CategoryForm(user=request.user)
    
    context = {
        'categories': categories,
        'form': form
    }
    return render(request, 'categories.html', context)

@login_required(login_url='expansio_login')
def budget_list_view(request):
    budgets = Budget.objects.filter(category__user=request.user, category__type='Expense')
    budget_data = []
    today = timezone.localdate()
    current_month = today.month
    current_year = today.year
    
    total_budget_expense = ZERO
    total_spent_expense = ZERO
    
    for budget in budgets:
        spent = Transaction.objects.filter(
            user=request.user,
            category=budget.category, 
            type=budget.category.type,
            date__month=current_month,
            date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or ZERO
        
        # Only include expenses in the header summary totals
        if budget.category.type == 'Expense':
            total_budget_expense += budget.amount_limit
            total_spent_expense += spent
            
        raw_percentage = int((spent / budget.amount_limit) * 100) if budget.amount_limit > 0 else 100
        bar_percentage = min(raw_percentage, 100)
        budget_data.append({
            'budget': budget,
            'spent': spent,
            'percentage': raw_percentage,
            'bar_percentage': bar_percentage,
            'is_exceeded': raw_percentage >= 100,
            'is_warning': raw_percentage >= 85 and raw_percentage < 100
        })
        
    if request.method == 'POST':
        category_id = request.POST.get('category')
        instance = Budget.objects.filter(category_id=category_id, category__user=request.user).first()
        form = BudgetForm(request.POST, instance=instance, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.save()
            messages.success(request, f"Budget limit updated successfully.")
            return redirect('expansio_budgets')
    else:
        form = BudgetForm(user=request.user)
        
    context = {
        'budget_data': budget_data,
        'form': form,
        'total_budget': total_budget_expense,
        'total_spent': total_spent_expense,
    }
    return render(request, 'budgets.html', context)

@login_required(login_url='expansio_login')
def reports_view(request):
    now = timezone.localdate()
    period = get_requested_period(request, now)
    if period is None:
        messages.error(request, 'Choose a valid month and year.')
        return redirect('expansio_reports')
    current_month, current_year = period

    # 1. Monthly Summary (For Selected Period)
    gross_income = Transaction.objects.filter(
        user=request.user,
        type='Income', 
        date__month=current_month, 
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or ZERO
    
    # EMI Deductions for the report period
    emi_total = get_emi_deductions(request.user, current_year, current_month)
    disposable_income = max(ZERO, gross_income - emi_total)
    
    total_expenses = Transaction.objects.filter(
        user=request.user,
        type='Expense', 
        date__month=current_month, 
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or ZERO

    savings = disposable_income - total_expenses
    savings_rate = (savings / disposable_income * 100) if disposable_income > 0 else 0

    # 2. Category Breakdown (Expenses)
    category_expenses = Category.objects.filter(user=request.user, type='Expense').annotate(
        amount=Sum('transaction__amount', filter=Q(
            transaction__type='Expense',
            transaction__date__month=current_month,
            transaction__date__year=current_year
        ))
    ).filter(amount__gt=0).order_by('-amount')

    categories_list = []
    for cat in category_expenses:
        percentage = (cat.amount / total_expenses * 100) if total_expenses > 0 else 0
        categories_list.append({
            'name': cat.name,
            'amount': cat.amount,
            'percentage': round(percentage, 1),
            'icon': cat.icon,
            'color': cat.color_class
        })

    # 3. Monthly Trends (Last 6 Months)
    trends_raw = []
    max_val = 0
    for i in range(5, -1, -1):
        target_month = current_month - i
        target_year = current_year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        m_inc = Transaction.objects.filter(user=request.user, type='Income', date__month=target_month, date__year=target_year).aggregate(Sum('amount'))['amount__sum'] or ZERO
        m_emi = get_emi_deductions(request.user, target_year, target_month)
        m_inc = max(0, m_inc - m_emi) # Net Income
        
        m_exp = Transaction.objects.filter(user=request.user, type='Expense', date__month=target_month, date__year=target_year).aggregate(Sum('amount'))['amount__sum'] or ZERO
        
        max_val = max(max_val, m_inc, m_exp)
        trends_raw.append({
            'month': calendar.month_name[target_month][:3],
            'income': m_inc,
            'expense': m_exp
        })

    # Scale the heights based on max_val
    trends = []
    scale = max_val / 100 if max_val > 0 else 1
    for t in trends_raw:
        trends.append({
            'month': t['month'],
            'income': t['income'],
            'expense': t['expense'],
            'income_h': max(2, int(t['income'] / scale)) if t['income'] > 0 else 2,
            'expense_h': max(2, int(t['expense'] / scale)) if t['expense'] > 0 else 2
        })

    # Calculate previous and next month for navigation
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    next_month = current_month + 1 if current_month < 12 else 1
    next_year = current_year if current_month < 12 else current_year + 1

    context = {
        'gross_income': gross_income,
        'disposable_income': disposable_income,
        'total_expenses': total_expenses,
        'savings': savings,
        'savings_rate': round(savings_rate, 1),
        'category_expenses': categories_list,
        'trends': trends,
        'top_category': categories_list[0] if categories_list else None,
        'current_month_name': calendar.month_name[current_month],
        'current_month': current_month,
        'current_year': current_year,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'is_current_period': (current_month == now.month and current_year == now.year),
        'emi_burden': emi_total
    }
    return render(request, 'reports.html', context)

@login_required(login_url='expansio_login')
@require_POST
def delete_transaction_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    transaction.delete()
    messages.success(request, "Transaction deleted successfully.")
    return redirect('expansio_transactions')

@login_required(login_url='expansio_login')
@require_POST
def delete_category_view(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    category.delete()
    messages.success(request, "Category deleted successfully.")
    return redirect('expansio_categories')

@login_required(login_url='expansio_login')
@require_POST
def delete_budget_view(request, pk):
    budget = get_object_or_404(Budget, pk=pk, category__user=request.user)
    category_name = budget.category.name
    budget.delete()
    messages.success(request, f"Budget for {category_name} removed successfully.")
    return redirect('expansio_budgets')

@login_required(login_url='expansio_login')
def emi_list_view(request):
    if request.method == 'POST':
        form = EMIForm(request.POST)
        if form.is_valid():
            emi = form.save(commit=False)
            emi.user = request.user
            emi.save()
            messages.success(request, f"EMI for '{emi.description}' added successfully.")
            return redirect('expansio_emi')
    else:
        form = EMIForm(initial={'start_date': timezone.localdate()})

    emis = EMI.objects.filter(user=request.user)
    today = timezone.localdate()
    monthly_burden = get_emi_deductions(request.user, today.year, today.month)
    
    return render(request, 'emi.html', {
        'emis': emis,
        'form': form,
        'monthly_burden': monthly_burden
    })

@login_required(login_url='expansio_login')
@require_POST
def delete_emi_view(request, pk):
    emi = get_object_or_404(EMI, pk=pk, user=request.user)
    description = emi.description
    emi.delete()
    messages.success(request, f"EMI for '{description}' removed.")
    return redirect('expansio_emi')
