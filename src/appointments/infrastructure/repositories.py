from datetime import datetime
from typing import Optional, Tuple, List

from appointments.domain.entities import Appointment, AvailabilitySlot
from appointments.domain.repositories import AppointmentRepository, AvailabilitySlotRepository
from appointments.domain.value_objects import AppointmentStatus, AvailabilityStatus
from appointments.infrastructure.models import Appointment as AppointmentModel
from appointments.infrastructure.models import AvailabilitySlot as AvailabilitySlotModel


class DjangoAppointmentRepository(AppointmentRepository):
    def list_for_user(
        self, user_id: str, role: str, limit: int, offset: int
    ) -> Tuple[List[Appointment], int]:
        queryset = AppointmentModel.objects.select_related("doctor", "patient")
        if role == "doctor":
            queryset = queryset.filter(doctor_id=user_id)
        else:
            queryset = queryset.filter(patient_id=user_id)

        queryset = queryset.order_by("-start_time")
        total = queryset.count()
        items = queryset[offset : offset + limit]
        return [self._to_entity(item) for item in items], total

    def create(
        self,
        doctor_id: str,
        patient_id: str,
        slot_id: Optional[str],
        start_time: datetime,
        end_time: datetime,
        status: AppointmentStatus,
        notes: Optional[str],
    ) -> Appointment:
        appointment = AppointmentModel.objects.create(
            doctor_id=doctor_id,
            patient_id=patient_id,
            slot_id=slot_id,
            start_time=start_time,
            end_time=end_time,
            status=status.value,
            notes=notes or "",
        )
        appointment = AppointmentModel.objects.select_related("doctor", "patient").get(pk=appointment.pk)
        return self._to_entity(appointment)

    def get_by_id(self, appointment_id: str) -> Optional[Appointment]:
        try:
            appointment = AppointmentModel.objects.select_related("doctor", "patient").get(pk=appointment_id)
        except AppointmentModel.DoesNotExist:
            return None
        return self._to_entity(appointment)

    def update_status(
        self, appointment_id: str, status: AppointmentStatus
    ) -> Appointment:
        appointment = AppointmentModel.objects.select_related("doctor", "patient").get(pk=appointment_id)
        appointment.status = status.value
        appointment.save(update_fields=["status", "updated_at"])
        return self._to_entity(appointment)

    def _to_entity(self, appointment: AppointmentModel) -> Appointment:
        return Appointment(
            id=str(appointment.pk),
            doctor_id=str(appointment.doctor_id),
            patient_id=str(appointment.patient_id),
            doctor_name=_doctor_display_name(appointment.doctor),
            start_time=appointment.start_time,
            end_time=appointment.end_time,
            status=AppointmentStatus(appointment.status),
            notes=appointment.notes or None,
        )


class DjangoAvailabilitySlotRepository(AvailabilitySlotRepository):
    def get_for_update(
        self, doctor_id: str, start_time: datetime
    ) -> Optional[AvailabilitySlot]:
        slot = (
            AvailabilitySlotModel.objects.select_for_update()
            .filter(doctor_id=doctor_id, start_time=start_time)
            .first()
        )
        return self._to_entity(slot) if slot else None

    def get_by_times(
        self, doctor_id: str, start_time: datetime, end_time: datetime
    ) -> Optional[AvailabilitySlot]:
        slot = AvailabilitySlotModel.objects.filter(
            doctor_id=doctor_id, start_time=start_time, end_time=end_time
        ).first()
        return self._to_entity(slot) if slot else None

    def mark_status(self, slot_id: str, status: AvailabilityStatus) -> None:
        AvailabilitySlotModel.objects.filter(pk=slot_id).update(status=status.value)

    def _to_entity(self, slot: AvailabilitySlotModel) -> AvailabilitySlot:
        return AvailabilitySlot(
            id=str(slot.pk),
            doctor_id=str(slot.doctor_id),
            start_time=slot.start_time,
            end_time=slot.end_time,
            status=AvailabilityStatus(slot.status),
        )


def _doctor_display_name(user) -> str:
    if hasattr(user, "get_full_name"):
        full_name = user.get_full_name()
        if full_name:
            return full_name
    for attr in ("name", "username", "email"):
        value = getattr(user, attr, "")
        if value:
            return value
    return str(user)
