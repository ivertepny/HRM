from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # users
    path("api/users/", include("apps.users.urls")),
    path("api/employees/", include("apps.employees.urls")),
    # company
    path("api/company/", include("apps.company.urls")),
    path("api/ai/", include("apps.ai_assistant.urls")),
    path("api/access/", include("apps.access.urls")),
]

if settings.DEBUG:
    # У prod файли віддає S3 (підписані URL), не Django
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
