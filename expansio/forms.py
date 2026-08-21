from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Category, Budget, EMI, Transaction

INPUT_CLASS = 'w-full bg-cream-50 border border-cream-400 shadow-sm rounded-xl py-3 px-4 text-sm text-earth-900 placeholder-cream-500 focus:bg-white focus:ring-2 focus:ring-terra-500/30 focus:border-terra-500 transition-all outline-none duration-200'


class CategorySelect(forms.Select):
    """Select widget that adds data-type attribute to each option for JS filtering."""

    def __init__(self, *args, category_types=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._category_types = category_types or {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and str(value) in self._category_types:
            option['attrs']['data-type'] = self._category_types[str(value)]
        return option


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'type']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g., Groceries'}),
            'type': forms.Select(attrs={'class': INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        category_type = self.cleaned_data.get('type')
        if self.user and category_type and Category.objects.filter(
            user=self.user,
            name__iexact=name,
            type=category_type,
        ).exists():
            raise ValidationError('You already have a category with this name and type.')
        return name

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount_limit']
        widgets = {
            'category': forms.Select(attrs={'class': INPUT_CLASS}),
            'amount_limit': forms.NumberInput(attrs={'class': INPUT_CLASS, 'step': '0.01', 'min': '0.01', 'placeholder': 'Limit Amount (e.g., 500.00)'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user, type='Expense')
        else:
            self.fields['category'].queryset = Category.objects.filter(type='Expense')

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['category', 'description', 'amount', 'type', 'date']
        widgets = {
            'category': forms.Select(attrs={'class': INPUT_CLASS}),
            'description': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'What was this for?'}),
            'amount': forms.NumberInput(attrs={'class': INPUT_CLASS, 'step': '0.01', 'min': '0.01', 'placeholder': 'Amount (e.g., 50.00)'}),
            'type': forms.Select(attrs={'class': INPUT_CLASS}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            qs = Category.objects.filter(user=user)
            self.fields['category'].queryset = qs
            # Build type map and swap in the custom widget
            category_types = {str(c.pk): c.type for c in qs}
            self.fields['category'].widget = CategorySelect(
                attrs={'class': INPUT_CLASS},
                category_types=category_types,
                choices=self.fields['category'].choices,
            )

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        transaction_type = cleaned_data.get('type')
        if category and transaction_type and category.type != transaction_type:
            self.add_error('category', 'Choose a category with the same transaction type.')
        return cleaned_data


class EMIForm(forms.ModelForm):
    class Meta:
        model = EMI
        fields = ['description', 'amount', 'frequency', 'start_date', 'end_date']
        widgets = {
            'description': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g., Laptop installment'}),
            'amount': forms.NumberInput(attrs={'class': INPUT_CLASS, 'step': '0.01', 'min': '0.01', 'placeholder': 'Amount'}),
            'frequency': forms.Select(attrs={'class': INPUT_CLASS}),
            'start_date': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date cannot be before the start date.')
        return cleaned_data

class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'John'}))
    email = forms.EmailField(max_length=150, widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'john@example.com'}))
    age = forms.IntegerField(min_value=13, max_value=120, widget=forms.NumberInput(attrs={'class': INPUT_CLASS, 'min': '13', 'max': '120', 'placeholder': '25'}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'New York'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': INPUT_CLASS, 'placeholder': '••••••••'}))

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(username=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)
        return password

class OTPForm(forms.Form):
    otp = forms.RegexField(r'^\d{6}$', widget=forms.TextInput(attrs={'class': 'w-full bg-cream-50 border border-cream-400 shadow-sm rounded-xl py-3.5 sm:py-4 px-3 sm:px-4 text-center tracking-[0.25em] sm:tracking-[0.45em] text-xl sm:text-2xl font-bold text-earth-900 focus:bg-white focus:ring-2 focus:ring-terra-500/30 focus:border-terra-500 transition-all outline-none duration-200', 'placeholder': '------'}))

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'name@example.com'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': INPUT_CLASS, 'placeholder': '••••••••'}))

class UserProfileUpdateForm(forms.Form):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Your name'}))
    age = forms.IntegerField(min_value=13, max_value=120, widget=forms.NumberInput(attrs={'class': INPUT_CLASS, 'min': '13', 'max': '120', 'placeholder': 'Your age'}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Your city'}))
    occupation = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g., Software Engineer'}))
