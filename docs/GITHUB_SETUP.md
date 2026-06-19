# GitHub setup (backend)

This repo is intended as a **private** GitHub repository for the Yallastay Django REST API.

## First-time publish

```powershell
cd C:\Users\USER\Desktop\yallastay_backend
git init
git add .
git status   # confirm .env, venv, *.sqlite3, media/ are NOT listed
git commit -m "Initial commit: Yallastay backend"
```

Create an empty **private** repo on GitHub, then:

```powershell
git branch -M main
git remote add origin https://github.com/YOUR_ORG/yallastay_backend.git
git push -u origin main
```

## CI (`.github/workflows/ci.yml`)

On every push and PR:

| Job | What it runs |
|-----|----------------|
| **Lint** | `black --check`, `ruff check`, no tracked `.env` |
| **Django checks** | `makemigrations --check --dry-run`, `manage.py check` |
| **Tests + coverage** | `coverage run manage.py test`, report (≥80% fail-under), XML artifact |
| **Smoke** (optional) | If repo variable `SMOKE_API_BASE` is set, curls `/api/areas/` and `/api/universities/` |

Tooling config: [`pyproject.toml`](../pyproject.toml) (Black, Ruff, Coverage).

## Local parity

```powershell
cd yallastay
..\venv\Scripts\Activate.ps1
pip install -r ..\requirements.txt
black --check .
ruff check .
python manage.py makemigrations --check --dry-run
python manage.py check
coverage run manage.py test
coverage report
```

## Demo database on Railway

After first deploy with Postgres, run once from Railway shell (folder `yallastay`):

```bash
cd yallastay
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

**Service root:** set Railway **Root Directory** to `yallastay`, *or* use repo-root `Procfile` / `railway.toml` (they `cd yallastay` before `migrate` / `collectstatic`). If release never runs, migrations and `staticfiles/` stay missing.

Optional demo seeds: [`DEMO_PRESENTATION.md`](DEMO_PRESENTATION.md).
