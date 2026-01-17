import uuid

from django.db import models


class Specialty(models.Model):
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


class DoctorSpecialty(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        "users.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="specialties",
    )
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.PROTECT,
        related_name="doctors",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "specialty"],
                name="uniq_doctor_specialty",
            ),
        ]
        indexes = [
            models.Index(fields=["doctor"]),
            models.Index(fields=["specialty"]),
        ]

    def __str__(self) -> str:
        return f"{self.doctor_id}:{self.specialty_id}"


class DoctorReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        "users.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="reviews",
    )
    patient = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="doctor_reviews",
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="doctor_review_rating_range",
            ),
            models.UniqueConstraint(
                fields=["doctor", "patient"],
                name="uniq_doctor_review_per_patient",
            ),
        ]
        indexes = [
            models.Index(fields=["doctor"]),
            models.Index(fields=["patient"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.doctor_id}:{self.rating}"
