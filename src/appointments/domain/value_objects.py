from enum import Enum


class AvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    BLOCKED = "BLOCKED"


class AppointmentStatus(str, Enum):
    BOOKED = "BOOKED"
    CANCELED = "CANCELED"
    COMPLETED = "COMPLETED"
