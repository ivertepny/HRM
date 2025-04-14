from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, DatabaseError
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Department, Position, Employee, CareerHistory
from .serializers import (
    DepartmentSerializer,
    PositionSerializer,
    EmployeeSerializer,
    CareerHistorySerializer,
)

import logging
logger = logging.getLogger(__name__)


@extend_schema_view(
    create=extend_schema(
        summary="Create a new department",
        description="Adds a new department to the company structure.",
        responses={
            201: DepartmentSerializer,
            400: {"description": "Validation or integrity error"},
            500: {"description": "Internal server error"},
        },
    )
)
class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except (IntegrityError, ValidationError, TypeError, ObjectDoesNotExist, DatabaseError) as e:
            logger.error("Error in Department creation: %s", str(e))
            return Response(
                {"error": type(e).__name__, "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST if isinstance(e, (ValidationError, IntegrityError, TypeError)) else status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except Exception as e:
            logger.error("Unexpected error: %s", str(e))
            return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as e:
            logger.error("Error updating Department: %s", str(e))
            return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ObjectDoesNotExist as e:
            logger.error("Department not found: %s", str(e))
            return Response({"error": "Department not found", "details": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error deleting Department: %s", str(e))
            return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema_view(
    create=extend_schema(
        summary="Create a new position",
        description="Adds a new position to the system.",
        responses={
            201: PositionSerializer,
            400: {"description": "Validation or integrity error"},
            500: {"description": "Internal server error"},
        },
    )
)
class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except (IntegrityError, ValidationError, TypeError, ObjectDoesNotExist, DatabaseError) as e:
            logger.error("Error in Position creation: %s", str(e))
            return Response(
                {"error": type(e).__name__, "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST if isinstance(e, (ValidationError, IntegrityError, TypeError)) else status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except Exception as e:
            logger.error("Unexpected error: %s", str(e))
            return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as e:
            logger.error("Error updating Position: %s", str(e))
            return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ObjectDoesNotExist as e:
            logger.error("Position not found: %s", str(e))
            return Response({"error": "Position not found", "details": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error deleting Position: %s", str(e))
            return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related('user', 'department', 'position')
    serializer_class = EmployeeSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error("Error creating Employee: %s", str(e))
            return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as e:
            logger.error("Error updating Employee: %s", str(e))
            return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ObjectDoesNotExist as e:
            logger.error("Employee not found: %s", str(e))
            return Response({"error": "Employee not found", "details": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error deleting Employee: %s", str(e))
            return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema_view(
    create=extend_schema(
        summary="Create career history record",
        description="Adds a new career history entry for an employee.",
        responses={
            201: CareerHistorySerializer,
            400: {"description": "Bad request or validation error"},
            404: {"description": "Related object not found"},
            500: {"description": "Internal server error"},
        },
    )
)
class CareerHistoryViewSet(viewsets.ModelViewSet):
    queryset = CareerHistory.objects.select_related('employee', 'position')
    serializer_class = CareerHistorySerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'position', 'date']

    def create(self, request, *args, **kwargs):
        logger.info("Create CareerHistory request received: %s", request.data)
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            logger.info("CareerHistory created with ID: %s", serializer.instance.id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            logger.error("Integrity error: %s", str(e))
            return Response({"error": "Integrity error", "details": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except ValidationError as e:
            logger.error("Validation error: %s", str(e))
            return Response({"error": "Validation error", "details": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            logger.error("Object not found: %s", str(e))
            return Response({"error": "Object not found", "details": str(e)}, status=status.HTTP_404_NOT_FOUND)

        except TypeError as e:
            logger.error("Type error: %s", str(e))
            return Response({"error": "Type error", "details": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except DatabaseError as e:
            logger.error("Database error: %s", str(e))
            return Response({"error": "Database error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error("Unexpected error: %s", str(e))
            return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as e:
            logger.error("Error updating CareerHistory: %s", str(e))
            return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ObjectDoesNotExist as e:
            logger.error("CareerHistory not found: %s", str(e))
            return Response({"error": "CareerHistory not found", "details": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error deleting CareerHistory: %s", str(e))
            return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
