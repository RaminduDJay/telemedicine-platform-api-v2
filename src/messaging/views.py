from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
import logging

from apps.messaging.models import Conversation, Message, MessageNotification
from apps.messaging.serializers import (
    ConversationSerializer, ConversationDetailSerializer, MessageSerializer,
    CreateMessageSerializer, MessageNotificationSerializer
)
from apps.users.models import Patient, Doctor
from apps.compliance.models import AuditLog

logger = logging.getLogger(__name__)

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(participants=user).order_by('-last_message_at')
    
    def retrieve(self, request, *args, **kwargs):
        """Get conversation with all messages"""
        conversation = self.get_object()
        
        # Mark all messages as read
        conversation.messages.filter(is_read=False).exclude(sender=request.user).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        serializer = ConversationDetailSerializer(conversation, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def start_conversation(self, request):
        """Start a new conversation between patient and doctor"""
        patient_id = request.data.get('patient_id')
        doctor_id = request.data.get('doctor_id')
        subject = request.data.get('subject', '')
        
        try:
            patient = Patient.objects.get(id=patient_id)
            doctor = Doctor.objects.get(id=doctor_id)
            
            # Only allow patient to start conversation with their own account
            if patient.user != request.user and request.user.role == 'patient':
                return Response(
                    {'error': 'You can only start conversations from your own account'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            conversation, created = Conversation.objects.get_or_create(
                patient=patient,
                doctor=doctor,
                defaults={'subject': subject}
            )
            
            if created:
                conversation.participants.add(patient.user, doctor.user)
            
            serializer = self.get_serializer(conversation)
            return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        except (Patient.DoesNotExist, Doctor.DoesNotExist):
            return Response({'error': 'Patient or Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in a conversation"""
        conversation = self.get_object()
        
        # Check if user is a participant
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CreateMessageSerializer(data=request.data)
        if serializer.is_valid():
            message = serializer.save(
                sender=request.user,
                conversation=conversation
            )
            
            # Update conversation last message time
            conversation.last_message_at = timezone.now()
            conversation.save()
            
            # Create notifications for other participants
            for participant in conversation.participants.exclude(id=request.user.id):
                MessageNotification.objects.get_or_create(
                    user=participant,
                    message=message,
                    conversation=conversation,
                    defaults={'notification_method': 'push'}
                )
            
            # Log message
            AuditLog.objects.create(
                user=request.user,
                action='modify_phi',
                resource_type='Message',
                resource_id=message.id,
                description=f'Sent message in conversation {conversation.id}',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response(
                MessageSerializer(message, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a conversation"""
        conversation = self.get_object()
        conversation.is_archived = True
        conversation.save()
        return Response(self.get_serializer(conversation).data)
    
    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive a conversation"""
        conversation = self.get_object()
        conversation.is_archived = False
        conversation.save()
        return Response(self.get_serializer(conversation).data)
    
    @action(detail=False, methods=['get'])
    def archived(self, request):
        """Get archived conversations"""
        conversations = self.get_queryset().filter(is_archived=True)
        serializer = self.get_serializer(conversations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active conversations"""
        conversations = self.get_queryset().filter(is_archived=False)
        serializer = self.get_serializer(conversations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get total unread message count"""
        unread_count = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
        return Response({'unread_count': unread_count})
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

class MessageViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get all unread messages"""
        messages = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).order_by('-created_at')
        
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search messages"""
        query = request.query_params.get('q', '')
        if not query or len(query) < 3:
            return Response({'error': 'Search query must be at least 3 characters'})
        
        messages = Message.objects.filter(
            conversation__participants=request.user,
            content__icontains=query
        ).order_by('-created_at')[:50]
        
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)
