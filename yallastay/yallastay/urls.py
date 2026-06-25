"""
URL configuration for yallastay project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import re

from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as serve_media


def api_root(request):
    return JsonResponse({"message": "Yallastay API", "status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", api_root),
    path("api/auth/", include("accounts.urls")),
    path("api/staff/verification/", include("accounts.staff_verification_urls")),
    path("api/verification/", include("accounts.verification_urls")),
    path("api/", include("bookings.urls")),
    path("api/", include("reviews.urls")),
    path("api/", include("payments.urls")),
    path("api/", include("messaging.urls")),
    path("api/", include("lifestyle_services.urls")),
    path("api/", include("notifications.urls")),
    path("api/", include("analytics.urls")),
    path("api/", include("reports.urls")),
    path("api/", include("roommates.urls")),
    path("api/", include("documents.urls")),
    path("api/", include("core.urls")),
    path("api/", include("listings.urls")),
    path("api/sms/", include("sms.urls")),
    path("api/emails/", include("emails.urls")),
    path("api/", include("esign.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, "SERVE_MEDIA_LOCALLY", False):
    # Production without S3: uploads live on local disk and must be served by the app.
    # ``static()`` is a no-op when DEBUG is False, and WhiteNoise only serves static files
    # (it also caches its file list at startup, so it can't serve images uploaded later).
    # Django's serve view reads from disk per request, so freshly uploaded photos resolve.
    _media_prefix = re.escape(settings.MEDIA_URL.lstrip("/"))
    urlpatterns += [
        re_path(
            rf"^{_media_prefix}(?P<path>.*)$",
            serve_media,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
