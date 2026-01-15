from django.db import models
from apps.users.models import User, Patient, Doctor

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='conversations_as_patient')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='conversations_as_doctor')
    
    subject = models.CharField(max_length=255, blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'messaging_conversation'
        unique_together = ['patient', 'doctor']
        indexes = [
            models.Index(fields=['patient', 'doctor']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Conversation: {self.patient.user.email} - {self.doctor.user.email}"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    
    content = models.TextField()
    attachment = models.FileField(upload_to='message_attachments/%Y/%m/%d/', blank=True, null=True)
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'messaging_message'
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Message from {self.sender} in conversation {self.conversation.id}"

class MessageNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_notifications')
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    
    is_notified = models.BooleanField(default=False)
    notified_at = models.DateTimeField(blank=True, null=True)
    notification_method = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
    ])
    
    class Meta:
        db_table = 'messaging_notification'
        unique_together = ['user', 'message']
