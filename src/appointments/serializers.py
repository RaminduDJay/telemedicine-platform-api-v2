from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from apps.appointments.models import Appointment, AppointmentNotes, CallSession
from apps.users.serializers import DoctorSerializer, PatientSerializer
from apps.users.models import Doctor
import uuid

class AppointmentNotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentNotes
        fields = ['id', 'chief_complaint', 'diagnosis', 'treatment_plan', 
                  'medications_prescribed', 'follow_up_required', 'follow_up_date', 'notes']
        read_only_fields = ['id']

class CallSessionSerializer(serializers.ModelSerializer):
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = CallSession
        fields = ['id', 'session_token', 'recording_url', 'started_at', 'ended_at', 
                  'patient_joined_at', 'doctor_joined_at', 'duration']
        read_only_fields = ['id', 'session_token']
    
    def get_duration(self, obj):
        if obj.started_at and obj.ended_at:
            return int((obj.ended_at - obj.started_at).total_seconds())
        return None

class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    clinical_notes = AppointmentNotesSerializer(read_only=True)
    call_session = CallSessionSerializer(read_only=True)
    
    class Meta:
        model = Appointment
        fields = ['id', 'patient', 'patient_name', 'doctor', 'doctor_name', 'appointment_type',
                  'scheduled_start', 'scheduled_end', 'reason_for_visit', 'notes', 'status',
                  'virtual_room_id', 'clinical_notes', 'call_session', 'created_at', 'updated_at']
        read_only_fields = ['id', 'virtual_room_id', 'created_at', 'updated_at']

class AppointmentBookingSerializer(serializers.Serializer):
    """Serializer for booking new appointments"""
    doctor_id = serializers.IntegerField()
    appointment_type = serializers.ChoiceField(choices=['telemedicine', 'in_person', 'phone'])
    scheduled_date = serializers.DateField()
    scheduled_time = serializers.TimeField()
    reason_for_visit = serializers.CharField(max_length=500)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_doctor_id(self, value):
        try:
            Doctor.objects.get(id=value, is_verified=True)
        except Doctor.DoesNotExist:
            raise serializers.ValidationError("Invalid doctor or doctor not verified.")
        return value
    
    def validate_scheduled_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Cannot book appointment in the past.")
        if value > timezone.now().date() + timedelta(days=90):
            raise serializers.ValidationError("Cannot book appointment more than 90 days in advance.")
        return value
    
    def create(self, validated_data):
        from apps.users.models import Patient
        
        patient = self.context['request'].user.patient_profile
        doctor = Doctor.objects.get(id=validated_data['doctor_id'])
        
        scheduled_start = timezone.make_aware(
            timezone.datetime.combine(validated_data['scheduled_date'], validated_data['scheduled_time'])
        )
        scheduled_end = scheduled_start + timedelta(minutes=30)
        
        # Check for conflicts
        existing = Appointment.objects.filter(
            doctor=doctor,
            scheduled_start__lte=scheduled_end,
            scheduled_end__gte=scheduled_start,
            status__in=['scheduled', 'confirmed']
        ).exists()
        
        if existing:
            raise serializers.ValidationError("This time slot is not available.")
        
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_type=validated_data['appointment_type'],
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            reason_for_visit=validated_data['reason_for_visit'],
            notes=validated_data.get('notes', ''),
            virtual_room_id=str(uuid.uuid4()) if validated_data['appointment_type'] == 'telemedicine' else None,
            status='scheduled'
        )
        
        return appointment

class AvailableSlotsSerializer(serializers.Serializer):
    """Get available appointment slots for a doctor"""
    doctor_id = serializers.IntegerField()
    date = serializers.DateField()

class CancelAppointmentSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField(max_length=500)

class AppointmentRescheduleSerializer(serializers.Serializer):
    scheduled_date = serializers.DateField()
    scheduled_time = serializers.TimeField()
    reason = serializers.CharField(required=False, allow_blank=True)
