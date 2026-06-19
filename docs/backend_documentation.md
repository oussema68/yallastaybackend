# Yallastay Backend Documentation

Django REST API for Yallastay  -  an apartment-finding platform for students and workers in Dubai.

---

## 1. Overview

| Item | Details |
|------|---------|
| **Framework** | Django 5.x + Django REST Framework |
| **Auth** | JWT (Simple JWT) |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Project root** | `yallastay/` (contains `manage.py`) |

---

## 2. Project Structure

```
yallastay_backend/
├── yallastay/                 # Django project
│   ├── manage.py
│   ├── yallastay/             # Config package
│   │   ├── urls.py            # Main URL routing
│   │   ├── settings/          # base.py, dev.py, prod.py
│   │   └── wsgi.py
│   ├── accounts/              # Auth, profiles, verification
│   ├── core/                  # Areas, universities
│   ├── listings/              # Listings, favorites
│   ├── bookings/              # Viewings, reservations
│   ├── reviews/
│   ├── payments/
│   ├── messaging/
│   ├── lifestyle_services/
│   ├── notifications/
│   ├── analytics/
│   ├── reports/
│   ├── roommates/
│   └── documents/
├── docs/                      # Markdown documentation (this tree, guides, checklists)
├── .env
├── .env.example
├── requirements.txt
```

---

## 3. Apps & Responsibilities

| App | Purpose |
|-----|---------|
| **accounts** | User, UserProfile, RealtorProfile; auth (register, login, me, logout); verification (UAE ID, university) |
| **core** | Area, University  -  reference data |
| **listings** | Listing, Favorite |
| **bookings** | ViewingRequest, Reservation |
| **reviews** | Review |
| **payments** | Payment (initiate, webhook) |
| **messaging** | Conversation, Message |
| **lifestyle_services** | LifestylePlan, LifestyleService, LifestyleSubscription |
| **notifications** | Notification, NotificationPreference |
| **analytics** | Aggregated metrics for realtors |
| **reports** | Report (listing or user) |
| **roommates** | RoommateProfile, RoommateInterest |
| **documents** | Document (upload, list, retrieve) |

---

## 4. API Endpoints

### Auth (`/api/auth/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register/` | Register (student/worker, landlord, realtor) |
| POST | `/auth/login/` | Login (email + password) |
| POST | `/auth/logout/` | Logout (blacklist token) |
| GET | `/auth/me/` | Current user + profile |

### Verification (`/api/verification/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/verification/uae-id/` | Submit UAE ID (emirates_id, optional document) |
| POST | `/verification/university/` | Submit university (email, university_id, optional student_id) |
| GET | `/verification/status/` | Get verification status |

### Core (`/api/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/areas/` | List Dubai areas |
| GET | `/universities/` | List universities |

### Listings (`/api/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/listings/` | List (filter: area_slug, type, min_price, max_price) |
| GET | `/listings/{id}/` | Detail |
| POST | `/listings/` | Create (landlord/realtor) |
| PATCH | `/listings/{id}/` | Update |
| DELETE | `/listings/{id}/` | Delete |
| GET | `/favorites/` | List user's favorites |
| POST | `/favorites/` | Add listing |
| DELETE | `/favorites/{id}/` | Remove |

### Bookings (`/api/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/viewings/` | Request viewing (UAE ID required) |
| GET | `/viewings/` | List viewings |
| PATCH | `/viewings/{id}/` | Confirm/reject viewing |
| POST | `/reservations/` | Create reservation |
| GET | `/reservations/` | List reservations |

### Reviews, Messaging, Notifications, Lifestyle
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reviews/` | Create review |
| GET | `/reviews/` | List (by user or listing) |
| GET | `/conversations/` | List conversations |
| POST | `/conversations/` | Create (listing_id) |
| GET | `/conversations/{id}/messages/` | List messages |
| POST | `/conversations/{id}/messages/` | Send message |
| GET | `/notifications/` | List notifications |
| PATCH | `/notifications/{id}/read/` | Mark read |
| GET | `/lifestyle-plans/` | List plans |
| POST | `/lifestyle-subscriptions/` | Subscribe |
| GET | `/lifestyle-subscriptions/` | List subscriptions |

### Analytics (realtors only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/renter-demographics/` | Student vs worker, universities, work areas |
| GET | `/analytics/popular-areas/` | Popular areas (saves, viewings, bookings) |
| GET | `/analytics/my-listings-insights/` | Realtor's listing metrics |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reports/submit/` | Submit report (listing_id or user_id + reason) |
| GET | `/reports/` | List (own; staff: all) |
| GET | `/reports/{id}/` | Detail |
| PATCH | `/reports/{id}/` | Update status (staff only) |

### Roommates (UAE ID required, students/workers only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/roommates/profile/` | Get own profile |
| POST | `/roommates/profile/` | Create profile |
| PATCH | `/roommates/profile/` | Update profile |
| GET | `/roommates/search/` | Search (?area=, ?budget_max=) |
| POST | `/roommates/interest/` | Express interest (to_user_id, message) |
| GET | `/roommates/interests/` | List sent/received |
| PATCH | `/roommates/interests/{id}/` | Accept/decline |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/documents/` | List user's documents |
| POST | `/documents/` | Upload (document_type, file) |
| GET | `/documents/{id}/` | Retrieve |

### Payments (gateway integration)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/payments/initiate/` | Initiate payment |
| POST | `/payments/webhook/` | Provider webhook |

---

## 5. Configuration

### Environment variables

| Variable | Purpose |
|---------|---------|
| `SECRET_KEY` | Django secret (32+ chars) |
| `DJANGO_ENV` | `dev` or `prod` |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `DATABASE_URL` | PostgreSQL connection string (prod) |
| `CORS_ALLOWED_ORIGINS` | Frontend origins |

### Installed apps

See `yallastay/settings/base.py`. Key packages: `rest_framework`, `rest_framework_simplejwt`, `corsheaders`, `django_filters`.

---

## 6. Key Commands

```bash
# From yallastay_backend/ or yallastay/
python manage.py migrate              # Apply migrations
python manage.py makemigrations <app> # Create migrations
python manage.py runserver            # Dev server
python manage.py createsuperuser      # Admin user
python manage.py test                # Run tests
```

Full command reference: see `COMMANDS.md`.

---

## 7. URL Routing

All API routes are under `/api/`. Main `urls.py` includes:

```python
path('api/auth/', include('accounts.urls')),
path('api/verification/', include('accounts.verification_urls')),
path('api/', include('bookings.urls')),
path('api/', include('core.urls')),
path('api/', include('listings.urls')),
# ... other apps
```

---

## 8. Permissions & Access

| Feature | Requirement |
|---------|-------------|
| Browse listings | None |
| Add to favorites | Authenticated |
| Request viewing | UAE ID verified |
| Create listing | Landlord or Realtor |
| Roommate search | Student/worker, UAE ID |
| Analytics | Realtor |
| Reports list | Own reports; staff see all |

---

## 9. Related Docs

- **ARCHITECTURE.md**  -  Full architecture, models, build phases
- **COMMANDS.md**  -  CLI commands
- **MANUAL_TESTING.md**  -  Manual test flows
- **USAGE_GUIDE.md**  -  Frontend + backend verification
- **FRONTEND_BACKEND_MAPPING.md**  -  API client ↔ backend mapping
