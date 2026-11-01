from rest_framework.routers import DefaultRouter

from .views import AttendanceRecordViewSet

router = DefaultRouter()
router.register(r"records", AttendanceRecordViewSet)

urlpatterns = router.urls
