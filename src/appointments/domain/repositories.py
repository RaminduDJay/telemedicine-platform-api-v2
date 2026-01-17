from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Tuple, List

from appointments.domain.entities import Appointment, AvailabilitySlot
from appointments.domain.value_objects import AppointmentStatus, AvailabilityStatus


class AppointmentRepository(ABC):
    @abstractmethod
    def list_for_user(
        self, user_id: str, role: str, limit: int, offset: int
    ) -> Tuple[List[Appointment], int]:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, appointment_id: str) -> Optional[Appointment]:
        raise NotImplementedError

    @abstractmethod
    def update_status(
        self, appointment_id: str, status: AppointmentStatus
    ) -> Appointment:
        raise NotImplementedError


class AvailabilitySlotRepository(ABC):
    @abstractmethod
    def get_for_update(
        self, doctor_id: str, start_time: datetime
    ) -> Optional[AvailabilitySlot]:
        raise NotImplementedError

    @abstractmethod
    def get_by_times(
        self, doctor_id: str, start_time: datetime, end_time: datetime
    ) -> Optional[AvailabilitySlot]:
        raise NotImplementedError

    @abstractmethod
    def mark_status(self, slot_id: str, status: AvailabilityStatus) -> None:
        raise NotImplementedError
