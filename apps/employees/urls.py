from rest_framework.routers import DefaultRouter

from .views import (
    CareerHistoryViewSet,
    EmployeeDocumentViewSet,
    EmployeeViewSet,
    PositionViewSet,
)

router = DefaultRouter()

router.register(r"positions", PositionViewSet)
router.register(r"employees", EmployeeViewSet)
router.register(r"career-history", CareerHistoryViewSet)
router.register(r"documents", EmployeeDocumentViewSet)

urlpatterns = router.urls
