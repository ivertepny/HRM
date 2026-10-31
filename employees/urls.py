from rest_framework.routers import DefaultRouter

from .views import CareerHistoryViewSet, EmployeeViewSet, PositionViewSet

router = DefaultRouter()

router.register(r"positions", PositionViewSet)
router.register(r"employees", EmployeeViewSet)
router.register(r"career-history", CareerHistoryViewSet)

urlpatterns = router.urls
