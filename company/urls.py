from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StructuralUnitViewSet

router = DefaultRouter()
router.register(r'units', StructuralUnitViewSet, basename='units')

urlpatterns = [
    path('', include(router.urls)),
    path('units/<int:pk>/diagram/', StructuralUnitViewSet.as_view({'get': 'diagram'}), name='unit-diagram'),
    path('units/<int:pk>/history/', StructuralUnitViewSet.as_view({'get': 'history'}), name='unit-history'),
    path('units/children/', StructuralUnitViewSet.as_view({'get': 'children'}), name='unit-children'),  # Додано нове поле для отримання дітей
]
