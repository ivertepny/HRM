from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet, PositionViewSet, EmployeeViewSet, CareerHistoryViewSet

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet)
router.register(r'positions', PositionViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'career-history', CareerHistoryViewSet)  # Register CareerHistoryViewSet

urlpatterns = router.urls
