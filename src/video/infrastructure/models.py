import uuid

from django.db import models


class VideoSessionStatus(models.TextChoices):
    INITIATED = "INITIATED", "Initiated"
    ACTIVE = "ACTIVE", "Active"
    ENDED = "ENDED", "Ended"
    FAILED = "FAILED", "Failed"


class VideoSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.PROTECT,
        related_name="video_session",
    )
    status = models.CharField(
        max_length=20,
        choices=VideoSessionStatus.choices,
        default=VideoSessionStatus.INITIATED,
    )
    provider_session_id = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"VideoSession({self.appointment_id})"


class VideoEventLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        VideoSession,
        on_delete=models.PROTECT,
        related_name="event_logs",
    )
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.session_id}:{self.event_type}"
