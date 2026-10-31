import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import DatabaseError, IntegrityError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CareerHistory, Employee, Position
from .serializers import (
    CareerHistorySerializer,
    EmployeeSerializer,
    PositionSerializer,
)

logger = logging.getLogger(__name__)


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
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except (
            IntegrityError,
            ValidationError,
            TypeError,
            ObjectDoesNotExist,
            DatabaseError,
        ) as e:
            logger.error("Error in Position creation: %s", str(e))
            return Response(
                {"error": type(e).__name__, "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
                if isinstance(e, (ValidationError, IntegrityError, TypeError))
                else status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except Exception as e:
            logger.error("Unexpected error: %s", str(e))
            return Response(
                {"error": "Unexpected error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as e:
            logger.error("Error updating Position: %s", str(e))
            return Response(
                {"error": "Unexpected error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ObjectDoesNotExist as e:
            logger.error("Position not found: %s", str(e))
            return Response(
                {"error": "Position not found", "details": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error("Error deleting Position: %s", str(e))
            return Response(
                {"error": "Unexpected error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("user", "structural_unit", "position")
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error("Error creating Employee: %s", str(e))
            return Response(
                {"error": "Unexpected error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as e:
            logger.error("Error updating Employee: %s", str(e))
            return Response(
                {"error": "Unexpected error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ObjectDoesNotExist as e:
            logger.error("Employee not found: %s", str(e))
            return Response(
                {"error": "Employee not found", "details": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error("Error deleting Employee: %s", str(e))
            return Response(
                {"error": "Unexpected error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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
    queryset = CareerHistory.objects.select_related(
        "employee", "position", "structural_unit"
    )
    serializer_class = CareerHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["employee", "position", "date"]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except (
            IntegrityError,
            ValidationError,
            TypeError,
            ObjectDoesNotExist,
            DatabaseError,
        ) as e:
            logger.error("Error creating CareerHistory: %s", str(e))
            return Response(
                {"error": type(e).__name__, "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
                if isinstance(e, (ValidationError, IntegrityError, TypeError))
                else status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            logger.error("Unexpected error: %s", str(e))
            return Response(
                {"error": "Unexpected error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as e:
            logger.error("Error updating CareerHistory: %s", str(e))
            return Response(
                {"error": "Unexpected error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ObjectDoesNotExist as e:
            logger.error("CareerHistory not found: %s", str(e))
            return Response(
                {"error": "CareerHistory not found", "details": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error("Error deleting CareerHistory: %s", str(e))
            return Response(
                {"error": "Unexpected error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
