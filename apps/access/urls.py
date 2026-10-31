from rest_framework.routers import DefaultRouter

from .views import PermissionViewSet, RoleViewSet, UserRoleViewSet

router = DefaultRouter()

router.register(r"permissions", PermissionViewSet)
router.register(r"roles", RoleViewSet)
router.register(r"user-roles", UserRoleViewSet)

urlpatterns = router.urls
