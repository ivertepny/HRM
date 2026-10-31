from rest_framework.routers import DefaultRouter

from .views import VacationRequestViewSet

router = DefaultRouter()
router.register(r"requests", VacationRequestViewSet)

urlpatterns = router.urls
