from rest_framework.routers import DefaultRouter

from .views import AttendanceRecordViewSet, HolidayViewSet

router = DefaultRouter()
router.register(r"records", AttendanceRecordViewSet)
router.register(r"holidays", HolidayViewSet)

urlpatterns = router.urls
