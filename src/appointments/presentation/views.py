from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.application.dto import (
    AppointmentError,
    BookAppointmentRequest,
    CancelAppointmentRequest,
    ListAppointmentsRequest,
)
from appointments.application.usecases import (
    BookAppointmentUseCase,
    CancelAppointmentUseCase,
    ListAppointmentsUseCase,
)
from appointments.infrastructure.repositories import (
    DjangoAppointmentRepository,
    DjangoAvailabilitySlotRepository,
)
from appointments.infrastructure.serializers import (
    AppointmentResponseSerializer,
    BookAppointmentSerializer,
)


class AppointmentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = _get_user_role(request.user)
        if role is None:
            return _error_response(
                code="invalid_role",
                message="Unsupported user role for appointments.",
                details={},
                status=403,
            )

        try:
            limit = _parse_int(request.query_params.get("limit"), default=20, min_value=1, max_value=100)
            offset = _parse_int(request.query_params.get("offset"), default=0, min_value=0)
        except ValueError as exc:
            return _error_response(
                code="invalid_pagination",
                message=str(exc),
                details={},
                status=400,
            )

        usecase = ListAppointmentsUseCase(DjangoAppointmentRepository())
        try:
            result = usecase.execute(
                ListAppointmentsRequest(
                    user_id=str(request.user.id),
                    user_role=role,
                    limit=limit,
                    offset=offset,
                )
            )
        except AppointmentError as exc:
            return _error_response(exc.code, exc.message, exc.details, exc.status)

        serializer = AppointmentResponseSerializer(result.items, many=True)
        return Response(
            {
                "data": serializer.data,
                "meta": {
                    "limit": result.limit,
                    "offset": result.offset,
                    "total": result.total,
                },
            }
        )

    def post(self, request):
        role = _get_user_role(request.user)
        if role != "patient":
            return _error_response(
                code="forbidden",
                message="Only patients can book appointments.",
                details={},
                status=403,
            )

        serializer = BookAppointmentSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response(
                code="validation_error",
                message="Invalid booking payload.",
                details=serializer.errors,
                status=400,
            )

        data = serializer.validated_data
        usecase = BookAppointmentUseCase(
            DjangoAppointmentRepository(),
            DjangoAvailabilitySlotRepository(),
        )
        try:
            appointment = usecase.execute(
                BookAppointmentRequest(
                    user_id=str(request.user.id),
                    doctor_id=str(data["doctorId"]),
                    date=data["date"],
                    time=data["time"],
                    notes=(data.get("notes") or None),
                )
            )
        except AppointmentError as exc:
            return _error_response(exc.code, exc.message, exc.details, exc.status)

        response_serializer = AppointmentResponseSerializer(appointment)
        return Response({"data": response_serializer.data, "meta": {}}, status=201)


class AppointmentCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, appointment_id: str):
        role = _get_user_role(request.user)
        if role is None:
            return _error_response(
                code="invalid_role",
                message="Unsupported user role for appointments.",
                details={},
                status=403,
            )

        usecase = CancelAppointmentUseCase(
            DjangoAppointmentRepository(),
            DjangoAvailabilitySlotRepository(),
        )
        try:
            appointment = usecase.execute(
                CancelAppointmentRequest(
                    user_id=str(request.user.id),
                    user_role=role,
                    appointment_id=str(appointment_id),
                )
            )
        except AppointmentError as exc:
            return _error_response(exc.code, exc.message, exc.details, exc.status)

        response_serializer = AppointmentResponseSerializer(appointment)
        return Response({"data": response_serializer.data, "meta": {}})


def _get_user_role(user) -> str | None:
    role = getattr(user, "role", None)
    if role in {"doctor", "patient"}:
        return role
    if getattr(user, "is_doctor", False):
        return "doctor"
    if getattr(user, "is_patient", False):
        return "patient"
    return None


def _parse_int(value, default: int, min_value: int, max_value: int | None = None) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Pagination values must be integers.") from exc
    if parsed < min_value:
        raise ValueError("Pagination values are out of range.")
    if max_value is not None and parsed > max_value:
        raise ValueError("Pagination values are out of range.")
    return parsed


def _error_response(code: str, message: str, details: dict, status: int):
    return Response(
        {"error": {"code": code, "message": message, "details": details or {}}},
        status=status,
    )
