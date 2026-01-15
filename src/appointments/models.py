from django.db import models
from django.utils import timezone
from apps.users.models import Patient, Doctor
from datetime import timedelta

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    APPOINTMENT_TYPE = [
        ('telemedicine', 'Telemedicine'),
        ('in_person', 'In Person'),
        ('phone', 'Phone Call'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE, default='telemedicine')
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    
    reason_for_visit = models.TextField()
    notes = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Virtual room details
    virtual_room_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    video_call_started_at = models.DateTimeField(blank=True, null=True)
    video_call_ended_at = models.DateTimeField(blank=True, null=True)
    
    # Reminders
    reminder_sent_24h = models.BooleanField(default=False)
    reminder_sent_1h = models.BooleanField(default=False)
    
    # Cancellation details
    cancelled_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='cancelled_appointments')
    cancellation_reason = models.TextField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'appointments_appointment'
        indexes = [
            models.Index(fields=['patient', 'scheduled_start']),
            models.Index(fields=['doctor', 'scheduled_start']),
            models.Index(fields=['status']),
        ]
        ordering = ['-scheduled_start']
    
    def __str__(self):
        return f"Appointment: {self.patient} with Dr. {self.doctor} on {self.scheduled_start}"
    
    def is_upcoming(self):
        return self.scheduled_start > timezone.now() and self.status != 'cancelled'
    
    def is_past(self):
        return self.scheduled_end < timezone.now()

class AppointmentNotes(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='clinical_notes')
    chief_complaint = models.TextField()
    diagnosis = models.TextField()
    treatment_plan = models.TextField()
    medications_prescribed = models.TextField()
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'appointments_clinical_notes'
    
    def __str__(self):
        return f"Notes for {self.appointment}"

class CallSession(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='call_session')
    session_token = models.CharField(max_length=255, unique=True)
    recording_url = models.URLField(blank=True, null=True)
    recording_duration = models.IntegerField(blank=True, null=True)  # seconds
    
    started_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    
    patient_joined_at = models.DateTimeField(blank=True, null=True)
    doctor_joined_at = models.DateTimeField(blank=True, null=True)
    
    patient_disconnected_at = models.DateTimeField(blank=True, null=True)
    doctor_disconnected_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'appointments_call_session'
    
    def __str__(self):
        return f"Call Session for {self.appointment}"
