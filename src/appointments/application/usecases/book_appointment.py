from datetime import datetime
from django.db import transaction
from django.utils import timezone

from appointments.application.dto import BookAppointmentRequest, AppointmentError
from appointments.domain.repositories import AppointmentRepository, AvailabilitySlotRepository
from appointments.domain.value_objects import AppointmentStatus, AvailabilityStatus


class BookAppointmentUseCase:
    def __init__(
        self,
        appointment_repository: AppointmentRepository,
        availability_repository: AvailabilitySlotRepository,
    ) -> None:
        self.appointment_repository = appointment_repository
        self.availability_repository = availability_repository

    def execute(self, request: BookAppointmentRequest):
        start_time = _parse_start_time(request.date, request.time)

        with transaction.atomic():
            slot = self.availability_repository.get_for_update(
                doctor_id=request.doctor_id, start_time=start_time
            )
            if slot is None:
                raise AppointmentError(
                    code="slot_not_found",
                    message="Availability slot not found.",
                    details={"doctorId": request.doctor_id, "startTime": start_time.isoformat()},
                    status=404,
                )
            if slot.status != AvailabilityStatus.AVAILABLE:
                raise AppointmentError(
                    code="slot_unavailable",
                    message="Availability slot is not available.",
                    details={"slotId": slot.id, "status": slot.status},
                    status=409,
                )
            if slot.end_time <= slot.start_time:
                raise AppointmentError(
                    code="invalid_time_range",
                    message="Availability slot has invalid time range.",
                    details={"slotId": slot.id},
                    status=400,
                )
            if slot.start_time < timezone.now():
                raise AppointmentError(
                    code="time_in_past",
                    message="Appointment time is in the past.",
                    details={"startTime": slot.start_time.isoformat()},
                    status=400,
                )

            appointment = self.appointment_repository.create(
                doctor_id=request.doctor_id,
                patient_id=request.user_id,
                slot_id=slot.id,
                start_time=slot.start_time,
                end_time=slot.end_time,
                status=AppointmentStatus.BOOKED,
                notes=request.notes,
            )
            self.availability_repository.mark_status(slot.id, AvailabilityStatus.BOOKED)

        return appointment


def _parse_start_time(date_str: str, time_str: str) -> datetime:
    try:
        date_part = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise AppointmentError(
            code="invalid_date",
            message="Invalid date format. Expected YYYY-MM-DD.",
            details={"date": date_str},
            status=400,
        ) from exc

    try:
        time_part = datetime.strptime(time_str, "%I:%M %p").time()
    except ValueError as exc:
        raise AppointmentError(
            code="invalid_time",
            message="Invalid time format. Expected h:mm AM/PM.",
            details={"time": time_str},
            status=400,
        ) from exc

    naive = datetime.combine(date_part, time_part)
    if timezone.is_aware(naive):
        return naive
    return timezone.make_aware(naive, timezone.get_current_timezone())
