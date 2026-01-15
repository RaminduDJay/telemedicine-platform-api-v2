from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from datetime import timedelta
from apps.appointments.models import Appointment
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_appointment_reminders():
    """Send appointment reminders 24 hours and 1 hour before appointment"""
    now = timezone.now()
    
    # 24-hour reminder
    appointments_24h = Appointment.objects.filter(
        scheduled_start__gte=now + timedelta(hours=23, minutes=30),
        scheduled_start__lte=now + timedelta(hours=24, minutes=30),
        reminder_sent_24h=False,
        status='confirmed'
    )
    
    for apt in appointments_24h:
        try:
            send_mail(
                subject=f'Appointment Reminder - {apt.doctor.user.get_full_name()}',
                message=f'You have an appointment on {apt.scheduled_start} with Dr. {apt.doctor.user.last_name}.',
                from_email='noreply@telemedicine.com',
                recipient_list=[apt.patient.user.email],
                fail_silently=False,
            )
            apt.reminder_sent_24h = True
            apt.save()
            logger.info(f"24-hour reminder sent for appointment {apt.id}")
        except Exception as e:
            logger.error(f"Failed to send reminder for appointment {apt.id}: {str(e)}")
    
    # 1-hour reminder
    appointments_1h = Appointment.objects.filter(
        scheduled_start__gte=now + timedelta(minutes=50),
        scheduled_start__lte=now + timedelta(minutes=70),
        reminder_sent_1h=False,
        status='confirmed'
    )
    
    for apt in appointments_1h:
        try:
            send_mail(
                subject=f'Your appointment starts in 1 hour - {apt.doctor.user.get_full_name()}',
                message=f'Your appointment with Dr. {apt.doctor.user.last_name} starts at {apt.scheduled_start}.',
                from_email='noreply@telemedicine.com',
                recipient_list=[apt.patient.user.email],
                fail_silently=False,
            )
            apt.reminder_sent_1h = True
            apt.save()
            logger.info(f"1-hour reminder sent for appointment {apt.id}")
        except Exception as e:
            logger.error(f"Failed to send reminder for appointment {apt.id}: {str(e)}")

@shared_task
def mark_no_show_appointments():
    """Mark appointments as no-show if they're 30 minutes past their scheduled time"""
    now = timezone.now()
    no_show_time = now - timedelta(minutes=30)
    
    appointments = Appointment.objects.filter(
        scheduled_end__lt=no_show_time,
        status__in=['scheduled', 'confirmed', 'in_progress']
    )
    
    for apt in appointments:
        apt.status = 'no_show'
        apt.save()
        logger.info(f"Appointment {apt.id} marked as no-show")
