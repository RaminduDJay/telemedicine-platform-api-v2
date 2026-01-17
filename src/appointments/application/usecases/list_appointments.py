from appointments.application.dto import ListAppointmentsRequest, ListAppointmentsResult, AppointmentError
from appointments.domain.repositories import AppointmentRepository


class ListAppointmentsUseCase:
    def __init__(self, appointment_repository: AppointmentRepository) -> None:
        self.appointment_repository = appointment_repository

    def execute(self, request: ListAppointmentsRequest) -> ListAppointmentsResult:
        if request.user_role not in {"doctor", "patient"}:
            raise AppointmentError(
                code="invalid_role",
                message="Unsupported user role for appointments.",
                details={"role": request.user_role},
                status=403,
            )

        items, total = self.appointment_repository.list_for_user(
            user_id=request.user_id,
            role=request.user_role,
            limit=request.limit,
            offset=request.offset,
        )

        return ListAppointmentsResult(
            items=items,
            total=total,
            limit=request.limit,
            offset=request.offset,
        )
