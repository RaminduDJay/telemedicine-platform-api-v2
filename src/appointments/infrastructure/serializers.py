from datetime import datetime

from rest_framework import serializers

from appointments.domain.entities import Appointment
from appointments.domain.value_objects import AppointmentStatus


class BookAppointmentSerializer(serializers.Serializer):
    doctorId = serializers.CharField()
    date = serializers.CharField()
    time = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)
    bookedAt = serializers.CharField(required=False, allow_blank=True)


class AppointmentResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    patientId = serializers.CharField()
    doctorId = serializers.CharField()
    doctorName = serializers.CharField()
    date = serializers.CharField()
    time = serializers.CharField()
    status = serializers.CharField()
    notes = serializers.CharField(allow_null=True, required=False)

    def to_representation(self, instance: Appointment) -> dict:
        return {
            "id": instance.id,
            "patientId": instance.patient_id,
            "doctorId": instance.doctor_id,
            "doctorName": instance.doctor_name,
            "date": instance.start_time.date().isoformat(),
            "time": _format_time(instance.start_time),
            "status": _to_frontend_status(instance.status),
            "notes": instance.notes,
        }


def _to_frontend_status(status: AppointmentStatus) -> str:
    if status == AppointmentStatus.BOOKED:
        return "scheduled"
    if status == AppointmentStatus.CANCELED:
        return "cancelled"
    return "completed"


def _format_time(value: datetime) -> str:
    hour = value.strftime("%I").lstrip("0") or "12"
    return f"{hour}:{value.strftime('%M')} {value.strftime('%p')}"
