import uuid

from django.conf import settings
from django.db import models


class RecordType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return self.name


class MedicalRecordStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"
    DELETED = "DELETED", "Deleted"


class MedicalRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medical_records",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_medical_records",
    )
    record_type = models.ForeignKey(
        RecordType,
        on_delete=models.PROTECT,
        related_name="records",
    )
    title = models.CharField(max_length=255)
    file_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=MedicalRecordStatus.choices,
        default=MedicalRecordStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["patient", "created_at"]),
            models.Index(fields=["record_type"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.patient_id}:{self.title}"


class RecordAccessAction(models.TextChoices):
    VIEW = "VIEW", "View"
    DOWNLOAD = "DOWNLOAD", "Download"
    EDIT = "EDIT", "Edit"
    DELETE = "DELETE", "Delete"


class RecordAccessLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.PROTECT,
        related_name="access_logs",
    )
    accessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="record_access_logs",
    )
    action = models.CharField(max_length=20, choices=RecordAccessAction.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["record", "created_at"]),
            models.Index(fields=["accessed_by"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self) -> str:
        return f"{self.record_id}:{self.action}"


class HealthSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="health_summary",
    )
    summary_text = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"HealthSummary({self.patient_id})"
