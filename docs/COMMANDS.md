# Yallastay Backend  -  Command Reference

All important CLI commands from project initialization to daily use. Run from `yallastay_backend` (project root) unless noted.

---

## 1. Project Initialization

### Create virtual environment
```bash
python -m venv venv
```

### Activate virtual environment
**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```
**Windows (CMD):**
```cmd
venv\Scripts\activate.bat
```
**macOS/Linux:**
```bash
source venv/bin/activate
```

### Install dependencies
```bash
pip install -r requirements.txt
```
*(If `requirements.txt` doesn't exist, install Django and packages per ARCHITECTURE or `pip install django djangorestframework djangorestframework-simplejwt django-cors-headers django-filter python-dotenv`.)*

---

## 2. Generate SECRET_KEY

Required for signing sessions and JWT tokens. **Must be 32+ characters** (RFC 7518).

### Generate a secure key
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and add to `.env`:
```
SECRET_KEY=<paste-generated-key-here>
```

### Or use a dev placeholder (not for production)
```
SECRET_KEY=django-insecure-dev-only-not-for-production-min-32-bytes-for-jwt
```

---

## 3. Environment Setup

### Create .env from example
```bash
copy .env.example .env
```
**macOS/Linux:**
```bash
cp .env.example .env
```

### Edit .env
Add or update:
- `SECRET_KEY`  -  see [Generate SECRET_KEY](#2-generate-secret_key) above
- `DJANGO_ENV=dev`
- `ALLOWED_HOSTS=localhost,127.0.0.1` (optional for dev)
- `TIME_ZONE=Asia/Dubai` (optional)

---

## 4. Database

### Create migrations (after model changes)
```bash
cd yallastay
python manage.py makemigrations
```

### Migrate
```bash
python manage.py migrate
```

### Reset database (dev only  -  destroys data)
```bash
python manage.py flush
python manage.py migrate
```

---

## 5. Seed Data

### Seed core data (areas, universities)
```bash
python manage.py seed_core
```

### Seed lifestyle plans
```bash
python manage.py seed_lifestyle
```

---

## 6. Superuser (Admin)

### Create admin user
```bash
python manage.py createsuperuser
```
Follow prompts (email, password).

### Access admin
`http://localhost:8000/admin/`

---

## 7. Run Server

### Development server
```bash
cd yallastay
python manage.py runserver
```
API: `http://localhost:8000/`

### With custom host/port
```bash
python manage.py runserver 0.0.0.0:8000
```

---

## 8. Testing

### Run all tests
```bash
cd yallastay
python manage.py test
```

### Run specific app
```bash
python manage.py test core accounts listings
```

### Run with coverage
```bash
coverage run manage.py test
coverage report
coverage html
```

---

## 9. Code Quality

### Django check
```bash
python manage.py check
```

### Collect static files (production)
```bash
python manage.py collectstatic --noinput
```

---

## 10. Management Commands

| Command | Description |
|--------|-------------|
| `python manage.py seed_core` | Seed Area and University |
| `python manage.py seed_lifestyle` | Seed LifestylePlan and LifestyleService |
| `python manage.py createsuperuser` | Create admin user |
| `python manage.py shell` | Django shell |
| `python manage.py dbshell` | Database shell |

---

## Quick Start (Fresh Clone)

```bash
# 1. Create and activate venv
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate and set SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Add output to .env as SECRET_KEY=...

# 4. Create .env (copy from .env.example, set SECRET_KEY)
copy .env.example .env

# 5. Migrate
cd yallastay
python manage.py migrate

# 6. Seed data
python manage.py seed_core
python manage.py seed_lifestyle

# 7. Create superuser (optional)
python manage.py createsuperuser

# 8. Run
python manage.py runserver
```

---

## Usage Guide (Frontend + Backend)

For step-by-step verification of the full stack (frontend and backend together), see **USAGE_GUIDE.md**.

---

## Paths Reference

| Purpose | Path |
|--------|------|
| Project root | `yallastay_backend/` |
| Django app folder | `yallastay_backend/yallastay/` |
| manage.py | `yallastay_backend/yallastay/manage.py` |
| Settings | `yallastay_backend/yallastay/yallastay/settings/` |
| .env | `yallastay_backend/yallastay/.env` |
