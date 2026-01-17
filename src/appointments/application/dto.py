from dataclasses import dataclass
from typing import Optional, List

from appointments.domain.entities import Appointment


@dataclass(frozen=True)
class BookAppointmentRequest:
    user_id: str
    doctor_id: str
    date: str
    time: str
    notes: Optional[str]


@dataclass(frozen=True)
class CancelAppointmentRequest:
    user_id: str
    user_role: str
    appointment_id: str


@dataclass(frozen=True)
class ListAppointmentsRequest:
    user_id: str
    user_role: str
    limit: int
    offset: int


@dataclass(frozen=True)
class ListAppointmentsResult:
    items: List[Appointment]
    total: int
    limit: int
    offset: int


class AppointmentError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[dict] = None,
        status: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.status = status
