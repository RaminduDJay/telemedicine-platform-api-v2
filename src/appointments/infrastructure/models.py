import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class AvailabilityStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    BOOKED = "BOOKED", "Booked"
    BLOCKED = "BLOCKED", "Blocked"


class AppointmentStatus(models.TextChoices):
    BOOKED = "BOOKED", "Booked"
    CANCELED = "CANCELED", "Canceled"
    COMPLETED = "COMPLETED", "Completed"


class AvailabilitySlot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="availability_slots",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE,
    )

    class Meta:
        indexes = [
            models.Index(fields=["doctor", "start_time"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "start_time", "end_time"],
                name="uniq_slot_doctor_time_range",
            ),
            models.CheckConstraint(
                check=Q(end_time__gt=models.F("start_time")),
                name="slot_end_after_start",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.doctor_id} {self.start_time.isoformat()} {self.status}"


class Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="doctor_appointments",
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patient_appointments",
    )
    slot = models.ForeignKey(
        AvailabilitySlot,
        on_delete=models.PROTECT,
        related_name="appointments",
        null=True,
        blank=True,
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.BOOKED,
    )
    notes = models.TextField(blank=True, null=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["doctor", "start_time"]),
            models.Index(fields=["patient", "start_time"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(end_time__gt=models.F("start_time")),
                name="appointment_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["slot"],
                condition=Q(status=AppointmentStatus.BOOKED),
                name="uniq_booked_slot",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.patient_id} -> {self.doctor_id} {self.start_time.isoformat()}"
