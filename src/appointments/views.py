from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta, datetime, time
import logging

from apps.appointments.models import Appointment, AppointmentNotes, CallSession
from apps.appointments.serializers import (
    AppointmentSerializer, AppointmentBookingSerializer, AvailableSlotsSerializer,
    CancelAppointmentSerializer, AppointmentRescheduleSerializer
)
from apps.users.models import Doctor, Patient
from apps.users.permissions import IsPatient, IsDoctor
from apps.compliance.models import AuditLog

logger = logging.getLogger(__name__)

class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return Appointment.objects.filter(patient__user=user).order_by('-scheduled_start')
        elif user.role == 'doctor':
            return Appointment.objects.filter(doctor__user=user).order_by('-scheduled_start')
        elif user.is_superuser:
            return Appointment.objects.all().order_by('-scheduled_start')
        return Appointment.objects.none()
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming appointments for current user"""
        now = timezone.now()
        appointments = self.get_queryset().filter(
            scheduled_start__gte=now,
            status__in=['scheduled', 'confirmed']
        )[:10]
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def past(self, request):
        """Get past appointments"""
        now = timezone.now()
        appointments = self.get_queryset().filter(
            scheduled_end__lt=now,
            status__in=['completed', 'no_show']
        )[:10]
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsPatient])
    def book(self, request):
        """Book a new appointment"""
        serializer = AppointmentBookingSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            appointment = serializer.save()
            
            # Log the booking
            AuditLog.objects.create(
                user=request.user,
                action='modify_phi',
                resource_type='Appointment',
                resource_id=appointment.id,
                description=f'Appointment booked with {appointment.doctor.user.get_full_name()}',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response(
                AppointmentSerializer(appointment).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def available_slots(self, request):
        """Get available appointment slots for a doctor"""
        serializer = AvailableSlotsSerializer(data=request.data)
        if serializer.is_valid():
            doctor_id = serializer.validated_data['doctor_id']
            appointment_date = serializer.validated_data['date']
            
            try:
                doctor = Doctor.objects.get(id=doctor_id)
                day_of_week = appointment_date.weekday()
                
                # Get doctor's availability for this day
                availability = doctor.availability_schedule.filter(day_of_week=day_of_week).first()
                if not availability:
                    return Response({'slots': []})
                
                # Generate time slots
                slots = []
                current_time = availability.start_time
                end_time = availability.end_time
                slot_duration = timedelta(minutes=availability.slot_duration_minutes)
                
                while current_time < end_time:
                    # Check if slot is available
                    slot_start = timezone.make_aware(
                        datetime.combine(appointment_date, current_time)
                    )
                    slot_end = slot_start + slot_duration
                    
                    conflict = Appointment.objects.filter(
                        doctor=doctor,
                        scheduled_start__lt=slot_end,
                        scheduled_end__gt=slot_start,
                        status__in=['scheduled', 'confirmed']
                    ).exists()
                    
                    if not conflict:
                        slots.append({
                            'time': current_time.isoformat(),
                            'available': True
                        })
                    
                    # Move to next slot
                    current_time = (datetime.combine(datetime.today(), current_time) + slot_duration).time()
                
                return Response({'slots': slots})
            except Doctor.DoesNotExist:
                return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsPatient])
    def cancel(self, request, pk=None):
        """Cancel an appointment"""
        appointment = self.get_object()
        
        if appointment.patient.user != request.user:
            return Response(
                {'error': 'You can only cancel your own appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if appointment.status in ['completed', 'cancelled']:
            return Response(
                {'error': f'Cannot cancel a {appointment.status} appointment'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CancelAppointmentSerializer(data=request.data)
        if serializer.is_valid():
            appointment.status = 'cancelled'
            appointment.cancelled_by = request.user
            appointment.cancelled_at = timezone.now()
            appointment.cancellation_reason = serializer.validated_data['cancellation_reason']
            appointment.save()
            
            # Log cancellation
            AuditLog.objects.create(
                user=request.user,
                action='modify_phi',
                resource_type='Appointment',
                resource_id=appointment.id,
                description='Appointment cancelled',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response(AppointmentSerializer(appointment).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsDoctor])
    def start_call(self, request, pk=None):
        """Start a video call for an appointment"""
        appointment = self.get_object()
        
        if appointment.doctor.user != request.user:
            return Response(
                {'error': 'Only the assigned doctor can start the call'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if appointment.status not in ['confirmed', 'scheduled']:
            return Response(
                {'error': 'Appointment is not ready for video call'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or get call session
        call_session, created = CallSession.objects.get_or_create(
            appointment=appointment,
            defaults={'session_token': str(timezone.now().timestamp())}
        )
        
        appointment.status = 'in_progress'
        appointment.video_call_started_at = timezone.now()
        appointment.save()
        
        return Response({
            'virtual_room_id': appointment.virtual_room_id,
            'session_token': call_session.session_token,
            'message': 'Call started'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsDoctor])
    def end_call(self, request, pk=None):
        """End a video call"""
        appointment = self.get_object()
        
        if appointment.doctor.user != request.user:
            return Response(
                {'error': 'Only the assigned doctor can end the call'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        appointment.status = 'completed'
        appointment.video_call_ended_at = timezone.now()
        appointment.save()
        
        try:
            call_session = appointment.call_session
            call_session.ended_at = timezone.now()
            call_session.save()
        except CallSession.DoesNotExist:
            pass
        
        return Response({'message': 'Call ended successfully'})
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

class DoctorSearchViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search doctors by specialty, name, or rating"""
        query = request.query_params.get('q', '')
        specialty = request.query_params.get('specialty', '')
        min_rating = request.query_params.get('min_rating', 0)
        
        doctors = Doctor.objects.filter(is_verified=True, availability_status=True)
        
        if query:
            doctors = doctors.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(bio__icontains=query)
            )
        
        if specialty:
            doctors = doctors.filter(specialties=specialty)
        
        if min_rating:
            doctors = doctors.filter(average_rating__gte=min_rating)
        
        doctors = doctors.order_by('-average_rating')[:20]
        
        from apps.users.serializers import DoctorSerializer
        serializer = DoctorSerializer(doctors, many=True)
        return Response(serializer.data)
