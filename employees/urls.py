from rest_framework.routers import DefaultRouter
from .views import PositionViewSet, EmployeeViewSet

router = DefaultRouter()

router.register(r'positions', PositionViewSet)
router.register(r'employees', EmployeeViewSet)

urlpatterns = router.urls
