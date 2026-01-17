from rest_framework import serializers
from apps.messaging.models import Conversation, Message, MessageNotification
from apps.users.serializers import UserSerializer

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'sender_name', 'sender_email', 'content', 'attachment',
                  'is_read', 'read_at', 'created_at', 'edited_at']
        read_only_fields = ['id', 'sender', 'sender_name', 'sender_email', 'created_at']

class ConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    
    class Meta:
        model = Conversation
        fields = ['id', 'patient', 'patient_name', 'doctor', 'doctor_name', 'subject',
                  'is_archived', 'last_message', 'unread_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'patient_name', 'doctor_name']
    
    def get_last_message(self, obj):
        message = obj.messages.first()
        if message:
            return MessageSerializer(message).data
        return None
    
    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()

class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conversation
        fields = ConversationSerializer.Meta.fields + ['messages']

class CreateMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['content', 'attachment']

class MessageNotificationSerializer(serializers.ModelSerializer):
    message = MessageSerializer(read_only=True)
    
    class Meta:
        model = MessageNotification
        fields = ['id', 'message', 'notification_method', 'is_notified', 'notified_at']
        read_only_fields = ['id', 'message', 'is_notified', 'notified_at']
