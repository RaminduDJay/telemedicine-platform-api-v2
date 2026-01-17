from django.db import transaction

from appointments.application.dto import CancelAppointmentRequest, AppointmentError
from appointments.domain.repositories import AppointmentRepository, AvailabilitySlotRepository
from appointments.domain.value_objects import AppointmentStatus, AvailabilityStatus


class CancelAppointmentUseCase:
    def __init__(
        self,
        appointment_repository: AppointmentRepository,
        availability_repository: AvailabilitySlotRepository,
    ) -> None:
        self.appointment_repository = appointment_repository
        self.availability_repository = availability_repository

    def execute(self, request: CancelAppointmentRequest):
        if request.user_role not in {"doctor", "patient"}:
            raise AppointmentError(
                code="invalid_role",
                message="Unsupported user role for appointments.",
                details={"role": request.user_role},
                status=403,
            )

        with transaction.atomic():
            appointment = self.appointment_repository.get_by_id(request.appointment_id)
            if appointment is None:
                raise AppointmentError(
                    code="appointment_not_found",
                    message="Appointment not found.",
                    details={"appointmentId": request.appointment_id},
                    status=404,
                )
            if request.user_id not in {appointment.patient_id, appointment.doctor_id}:
                raise AppointmentError(
                    code="forbidden",
                    message="You cannot cancel this appointment.",
                    details={"appointmentId": appointment.id},
                    status=403,
                )
            if appointment.status != AppointmentStatus.BOOKED:
                raise AppointmentError(
                    code="invalid_status",
                    message="Only booked appointments can be canceled.",
                    details={"status": appointment.status},
                    status=409,
                )

            updated = self.appointment_repository.update_status(
                appointment_id=appointment.id,
                status=AppointmentStatus.CANCELED,
            )

            slot = self.availability_repository.get_by_times(
                doctor_id=appointment.doctor_id,
                start_time=appointment.start_time,
                end_time=appointment.end_time,
            )
            if slot and slot.status == AvailabilityStatus.BOOKED:
                self.availability_repository.mark_status(slot.id, AvailabilityStatus.AVAILABLE)

        return updated
