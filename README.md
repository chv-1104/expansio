# Expansio — Personal Finance Architecture & Ledger

Expansio is a full-featured personal finance and budgeting web application built with **Python** and **Django**. Designed as a portfolio project showcasing backend fundamentals, data integrity, clean architecture, secure session-based authentication, and responsive UI design.

---

## 🚀 Key Features & Architectural Highlights

1. **Secure Email OTP Authentication**
   - User registration with session-hashed OTP verification via Brevo API (`secrets.randbelow`, expiry timestamps, attempt limits).
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
   - Fully configured with **SQLite** (`db.sqlite3`) for persistent, zero-maintenance storage on **PythonAnywhere** and local development.
   - Django Admin fully registered with search, list filters, and select-related optimizations.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, Django 5.x
- **Database:** SQLite (`db.sqlite3`) — persistent, reliable, zero-config
- **WSGI / Web Server:** PythonAnywhere WSGI / Gunicorn / WhiteNoise
- **Email Delivery:** Gmail SMTP (`django.core.mail.backends.smtp.EmailBackend`)
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

Configure `.env`:
```env
DEBUG=True
SECRET_KEY=your-generated-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1,.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://*.pythonanywhere.com
BREVO_API_KEY=your_brevo_api_key
DEFAULT_FROM_EMAIL=your-verified-email@gmail.com
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

Run deployment check:
```powershell
python manage.py check
```

Verify static collection:
```powershell
python manage.py collectstatic --noinput
```

---

## 🌐 PythonAnywhere Deployment Guide

Deploying Expansio to PythonAnywhere is fast, reliable, and completely free using SQLite persistent storage.

### 1. Clone Repository in PythonAnywhere Bash Console
Open a **Bash console** from your PythonAnywhere Dashboard:
```bash
git clone <your-repo-url> expansio_repo
cd expansio_repo/expansio
```

### 2. Create and Activate Virtual Environment
```bash
python3.12 -m venv ~/.virtualenvs/expansio-env
source ~/.virtualenvs/expansio-env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Set Up Environment Variables & Run Migrations
Create your `.env` file in the project folder (`/home/<username>/expansio_repo/expansio/.env`):
```bash
cat << 'EOF' > .env
DEBUG=False
SECRET_KEY=generate-a-strong-random-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,<your-username>.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://<your-username>.pythonanywhere.com
BREVO_API_KEY=your_brevo_api_key
DEFAULT_FROM_EMAIL=your_email@gmail.com
EOF
```

Run database migrations, create superuser, and collect static files:
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### 4. Configure PythonAnywhere Web Tab
1. Go to the **Web** tab in PythonAnywhere.
2. Click **Add a new web app** -> Choose **Manual configuration** -> Select **Python 3.12** (or your preferred Python 3.x version).
3. Set the directory paths:
   - **Source code**: `/home/<username>/expansio_repo/expansio`
   - **Working directory**: `/home/<username>/expansio_repo/expansio`
   - **Virtualenv**: `/home/<username>/.virtualenvs/expansio-env`

4. Set up **Static files** mappings in the Web tab:
   - URL: `/static/`
   - Directory: `/home/<username>/expansio_repo/expansio/staticfiles`

5. Edit the **WSGI configuration file** (click the link under the WSGI section):
```python
import os
import sys
from pathlib import Path

# Path to project directory
path = '/home/<username>/expansio_repo/expansio'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'project.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

6. Click the green **Reload <username>.pythonanywhere.com** button.
7. Open `https://<username>.pythonanywhere.com` to see your live Expansio app!

