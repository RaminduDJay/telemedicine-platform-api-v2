from celery import shared_task
from django.core.mail import send_mail
from apps.messaging.models import MessageNotification
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_message_notifications():
    """Send email/SMS notifications for unread messages"""
    notifications = MessageNotification.objects.filter(is_notified=False)
    
    for notification in notifications:
        try:
            user = notification.user
            message = notification.message
            
            if notification.notification_method == 'email':
                send_mail(
                    subject=f'New message from {message.sender.get_full_name()}',
                    message=f'You have a new message: {message.content[:100]}...',
                    from_email='noreply@telemedicine.com',
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            elif notification.notification_method == 'push':
                # Push notification would be handled by a separate service
                pass
            
            notification.is_notified = True
            notification.notified_at = __import__('django.utils.timezone', fromlist=['now']).now()
            notification.save()
            logger.info(f"Notification sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
