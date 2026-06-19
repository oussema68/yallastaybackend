# Yallastay backend

Django REST API for the Yallastay rental marketplace (listings, bookings, payments, messaging, documents, e-sign, …).

## Quick start

- Python 3.11+ recommended; create a venv and install dependencies from `yallastay/requirements*.txt` (or your project’s lockfile).
- From `yallastay/`: `python manage.py migrate` then `python manage.py runserver`.
- Settings: `DJANGO_ENV` (default dev) or `prod`  -  see `yallastay/yallastay/settings/`.

## Documentation

**All maintained docs live under [`docs/`](docs/README.md)**  -  start with the index there for:

- Security checklist & PostgreSQL RLS  
- Platform vision & workflows  
- MVP gap analysis & mobile roadmap  
- Stripe, e-sign, and commercial/SOW templates  

**Publishing to GitHub:** [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md) (init, CI, local parity commands).

## Repositories

- **This repo:** Django API (`yallastay/` package).
- **Frontend:** separate Vite/React app (same-origin `/api` or `VITE_API_URL`).
