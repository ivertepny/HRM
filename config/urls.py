from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views import HealthView, MediaView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view(), name="health"),
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
    path("api/vacations/", include("apps.vacations.urls")),
    path("api/equipment/", include("apps.equipment.urls")),
    path("api/attendance/", include("apps.attendance.urls")),
    # Файли працівників — з перевіркою доступу, в dev і в prod однаково
    path("media/<path:path>", MediaView.as_view(), name="media"),
]
