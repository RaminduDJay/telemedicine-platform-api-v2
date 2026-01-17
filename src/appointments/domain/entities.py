from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from appointments.domain.value_objects import AppointmentStatus, AvailabilityStatus


@dataclass(frozen=True)
class AvailabilitySlot:
    id: str
    doctor_id: str
    start_time: datetime
    end_time: datetime
    status: AvailabilityStatus


@dataclass(frozen=True)
class Appointment:
    id: str
    doctor_id: str
    patient_id: str
    doctor_name: str
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    notes: Optional[str]
