from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from expansio.models import Budget, Category, EMI, Transaction, UserProfile


class Command(BaseCommand):
    help = 'Create a local demo account with safe sample finance data.'

    def add_arguments(self, parser):
        parser.add_argument('--email', default='demo@example.com')
        parser.add_argument('--password', required=True)

    def handle(self, *args, **options):
        email = options['email'].lower()
        password = options['password']
        user, created = User.objects.get_or_create(
            username=email,
            defaults={'email': email, 'first_name': 'Demo'},
        )
        if created:
            user.set_password(password)
            user.save()
            status = 'Created'
        else:
            user.set_password(password)
            user.save()
            status = 'Updated'

        UserProfile.objects.update_or_create(
            user=user,
            defaults={'age': 25, 'city': 'Pune', 'occupation': 'Software Engineer'},
        )
        food, _ = Category.objects.get_or_create(user=user, name='Food', type='Expense')
        transport, _ = Category.objects.get_or_create(user=user, name='Transport', type='Expense')
        salary, _ = Category.objects.get_or_create(user=user, name='Salary', type='Income')
        Budget.objects.update_or_create(category=food, defaults={'amount_limit': '6000.00'})
        Budget.objects.update_or_create(category=transport, defaults={'amount_limit': '2500.00'})

        if not Transaction.objects.filter(user=user).exists():
            today = timezone.localdate()
            Transaction.objects.bulk_create([
                Transaction(user=user, category=salary, description='Monthly salary', amount='60000.00', type='Income', date=today.replace(day=1)),
                Transaction(user=user, category=food, description='Groceries', amount='1850.00', type='Expense', date=today - timedelta(days=2)),
                Transaction(user=user, category=transport, description='Metro and cab', amount='640.00', type='Expense', date=today - timedelta(days=1)),
            ])
        EMI.objects.get_or_create(
            user=user,
            description='Laptop installment',
            defaults={'amount': '2500.00', 'frequency': 'Monthly', 'start_date': timezone.localdate()},
        )

        self.stdout.write(self.style.SUCCESS(f'{status} demo account: {email}'))
