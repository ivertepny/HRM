from rest_framework.routers import DefaultRouter

from .views import EquipmentAssignmentViewSet, EquipmentViewSet

router = DefaultRouter()
router.register(r"items", EquipmentViewSet, basename="equipment")
router.register(r"assignments", EquipmentAssignmentViewSet)

urlpatterns = router.urls
