# Expansio — Personal Finance Architecture & Ledger

Expansio is a full-featured personal finance and budgeting web application built with **Python** and **Django**. Designed as a portfolio project showcasing backend fundamentals, data integrity, clean architecture, secure session-based authentication, and responsive UI design.

---

## 🚀 Key Features & Architectural Highlights

1. **Secure Email OTP Authentication**
   - User registration with session-hashed OTP verification via Gmail SMTP (`secrets.randbelow`, expiry timestamps, attempt limits).
   - Atomic database operations (`transaction.atomic()`) ensuring zero orphaned user profiles or partial signups.
   - Form-level validation with custom validators for email uniqueness and password complexity.

2. **Double-Entry Style Financial Ledger**
   - Precise financial calculations using Python's `Decimal` type to prevent IEEE 754 floating-point inaccuracies.
   - Cross-type validation: ensures an Income transaction cannot be logged under an Expense category.
   - Case-insensitive category uniqueness per user enforced at both database and model layer constraints.

3. **Smart Monthly Budgets & Spending Visuals**
   - Real-time aggregation of expenses per category with warning thresholds (85% warning, 100% exceeded).
   - One-to-one category limit mapping with instant edit and delete workflows.

4. **EMI & Recurring Installment Engine**
   - Independent EMI tracker supporting Monthly and Weekly repayment schedules.
   - Dynamic month-by-month auto-deduction against gross income to calculate actual disposable net income and all-time net worth.

5. **Financial Analytics & 6-Month Trends**
   - 6-month historical trend analysis with CSS-scaled bar graphs.
   - Category expense distribution breakdown and savings rate calculation.

6. **Production & Interview Readiness**
   - Automated unit & integration tests covering auth, financial models, EMI burden, category filters, and edge cases.
   - Fully configured for local SQLite development and cloud deployments (Railway / Docker / PostgreSQL / MySQL) via `DATABASE_URL` and `dj_database_url`.
   - Django Admin fully registered with search, list filters, and select-related optimizations.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, Django 4.2+ / 5.x
- **Database:** SQLite (local development default) / MySQL / PostgreSQL (production via `DATABASE_URL`)
- **Static Assets:** WhiteNoise with Manifest caching
- **Styling & UI:** Tailwind CSS, Material Symbols, Glassmorphism design tokens

---

## 💻 Local Setup Guide

### 1. Clone & create virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```

Generate a secure secret key and set it in `.env`:
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Add your Gmail credentials in `.env`:
```env
DEBUG=True
SECRET_KEY=your-generated-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-gmail-app-password
```

### 3. Run Migrations & Seed Sample Data
```powershell
python manage.py migrate
python manage.py seed_demo --password "DemoPassword123!"
```

### 4. Start Development Server
```powershell
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` and sign in with `demo@example.com` / `DemoPassword123!`.

---

## 🧪 Testing & Verification

Run the test suite:
```powershell
python manage.py test
```

Run deployment security checks:
```powershell
python manage.py check --deploy
```

Verify static collection:
```powershell
python manage.py collectstatic --noinput --dry-run
```
