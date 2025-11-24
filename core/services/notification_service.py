from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone
from django.db.models import Count
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from core.models import NewsletterSubscriber, ClothingItem, Exchange, ClothingRequest
import logging

# Set up logger
logger = logging.getLogger(__name__)

# Get the custom user model
User = get_user_model()

class NotificationService:
    """
    Comprehensive service class for handling ALL email notifications for ClothShare
    Includes user notifications, admin notifications, and newsletter functionality
    """
    
    @staticmethod
    def safe_get_preference(subscriber, field_name, default=True):
        """Safely get subscriber preference with fallback"""
        try:
            return getattr(subscriber, field_name, default)
        except Exception:
            return default
    
    @staticmethod
    def get_email_context():
        """Get common context for all emails"""
        try:
            domain = get_current_site(None).domain
        except:
            domain = 'localhost:8000'  # Fallback domain
            
        return {
            'protocol': 'https' if not settings.DEBUG else 'http',
            'domain': domain,
            'site_name': 'ClothShare',
            'support_email': 'clothshareinfo@gmail.com',
            'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000'),
            'current_year': datetime.now().year,
            'timestamp': timezone.now().strftime("%Y-%m-%d %H:%M"),
        }
    
    @staticmethod
    def get_admin_email():
        """Get admin email with proper fallback"""
        admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if admin_email and '@' in admin_email:
            return admin_email
        return getattr(settings, 'DEFAULT_FROM_EMAIL', 'clothshareinfo@gmail.com')
    
    @staticmethod
    def safe_render_template(template_path, context):
        """Safely render template with fallback handling"""
        try:
            return render_to_string(template_path, context)
        except Exception as e:
            logger.warning(f"Template {template_path} not found, using fallback: {e}")
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background: #f9f9f9; }}
                    .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>ClothShare Notification</h2>
                    </div>
                    <div class="content">
                        <p><strong>Notification Type:</strong> {template_path}</p>
                        <p><strong>Context Data:</strong></p>
                        <ul>
                            {"".join([f"<li><strong>{key}:</strong> {value}</li>" for key, value in context.items() if key not in ['protocol', 'domain', 'site_name']])}
                        </ul>
                        <p>This is an automated notification from ClothShare.</p>
                    </div>
                    <div class="footer">
                        <p>&copy; {context.get('current_year', 2024)} ClothShare. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
    
    @staticmethod
    def send_notification(subject, template_path, context, recipient_list, extra_log_info=""):
        """Generic method to send notifications with comprehensive error handling"""
        try:
            if not recipient_list or not any(recipient_list):
                logger.warning(f"No valid recipients for: {subject}")
                return False
            
            valid_recipients = [email for email in recipient_list if email and '@' in email]
            if not valid_recipients:
                logger.warning(f"No valid email addresses in recipient list: {recipient_list}")
                return False
            
            # Ensure required context variables are present
            context['subject'] = subject
            if 'timestamp' not in context:
                context['timestamp'] = timezone.now().strftime("%Y-%m-%d %H:%M")
            
            html_message = NotificationService.safe_render_template(template_path, context)
            plain_message = strip_tags(html_message)
            
            log_message = f"📧 SENDING EMAIL: {subject}"
            if extra_log_info:
                log_message += f" | {extra_log_info}"
            log_message += f" | To: {', '.join(valid_recipients)}"
            print(log_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=valid_recipients,
                html_message=html_message,
                fail_silently=False,
            )
            
            print(f"✅ Email sent successfully to: {', '.join(valid_recipients)}")
            return True
            
        except Exception as e:
            error_msg = f"❌ Email sending failed for '{subject}': {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            return False

    # ============================================================================
    # USER-FACING NOTIFICATIONS
    # ============================================================================

    @staticmethod
    def send_user_welcome_email(user):
        """Send welcome email to new user"""
        subject = '👋 Welcome to ClothShare!'
        context = NotificationService.get_email_context()
        context.update({
            'user': user,
            'notification_type': 'welcome',
        })
        
        if user and user.email:
            return NotificationService.send_notification(
                subject=subject,
                template_path='core/emails/user/welcome.html',
                context=context,
                recipient_list=[user.email],
                extra_log_info=f"Welcome email for: {user.username}"
            )

    @staticmethod
    def notify_exchange_request_received(exchange):
        """Notify item owner that someone requested their item"""
        subject = f"🔄 New Exchange Request for '{exchange.item.title}'"
        context = NotificationService.get_email_context()
        context.update({
            'exchange': exchange,
            'requester': exchange.requester,
            'item': exchange.item,
            'notification_type': 'exchange_request_received',
        })
        
        if exchange.item.donor and exchange.item.donor.email:
            return NotificationService.send_notification(
                subject=subject,
                template_path='core/emails/user/exchange_request_received.html',
                context=context,
                recipient_list=[exchange.item.donor.email],
                extra_log_info=f"Exchange request received: {exchange.item.donor.email}"
            )
        return False

    @staticmethod
    def notify_exchange_request_accepted(exchange):
        """Notify requester that their exchange request was accepted"""
        subject = f"✅ Exchange Request Accepted for '{exchange.item.title}'"
        context = NotificationService.get_email_context()
        context.update({
            'exchange': exchange,
            'item_owner': exchange.item.donor,
            'item': exchange.item,
            'notification_type': 'exchange_request_accepted',
        })
        
        if exchange.requester and exchange.requester.email:
            return NotificationService.send_notification(
                subject=subject,
                template_path='core/emails/user/exchange_request_accepted.html',
                context=context,
                recipient_list=[exchange.requester.email],
                extra_log_info=f"Exchange accepted: {exchange.requester.email}"
            )
        return False

    @staticmethod
    def notify_exchange_request_rejected(exchange):
        """Notify requester that their exchange request was rejected"""
        subject = f"❌ Exchange Request Declined for '{exchange.item.title}'"
        context = NotificationService.get_email_context()
        context.update({
            'exchange': exchange,
            'item_owner': exchange.item.donor,
            'item': exchange.item,
            'notification_type': 'exchange_request_rejected',
        })
        
        if exchange.requester and exchange.requester.email:
            return NotificationService.send_notification(
                subject=subject,
                template_path='core/emails/user/exchange_request_rejected.html',
                context=context,
                recipient_list=[exchange.requester.email],
                extra_log_info=f"Exchange rejected: {exchange.requester.email}"
            )
        return False

    @staticmethod
    def notify_exchange_cancelled(exchange, cancelled_by):
        """Notify both parties when exchange is cancelled"""
        context = NotificationService.get_email_context()
        success_count = 0
        
        # Notify requester
        if exchange.requester and exchange.requester.email:
            subject = f"❌ Exchange Cancelled for '{exchange.item.title}'"
            context.update({
                'exchange': exchange,
                'cancelled_by': cancelled_by,
                'notification_type': 'exchange_cancelled',
            })
            
            if NotificationService.send_notification(
                subject=subject,
                template_path='core/emails/user/exchange_cancelled.html',
                context=context,
                recipient_list=[exchange.requester.email],
                extra_log_info=f"Exchange cancelled for requester: {exchange.requester.email}"
            ):
                success_count += 1
        
        # Notify item owner
        if exchange.item.donor and exchange.item.donor.email:
            subject = f"❌ Exchange Cancelled for '{exchange.item.title}'"
            context.update({
                'exchange': exchange,
                'cancelled_by': cancelled_by,
                'notification_type': 'exchange_cancelled',
            })
            
            if NotificationService.send_notification(
                subject=subject,
                template_path='core/emails/user/exchange_cancelled.html',
                context=context,
                recipient_list=[exchange.item.donor.email],
                extra_log_info=f"Exchange cancelled for owner: {exchange.item.donor.email}"
            ):
                success_count += 1
        
        return success_count > 0

    @staticmethod
    def notify_exchange_completed(exchange):
        """Notify both parties when exchange is completed"""
        context = NotificationService.get_email_context()
        success_count = 0
        
        # Notify requester
        if exchange.requester and exchange.requester.email:
            subject = f"✅ Exchange Completed for '{exchange.item.title}'"
            context.update({
                'exchange': exchange,
                'notification_type': 'exchange_completed',
            })
            
            if NotificationService.send_notification(
                subject=subject,
                template_path='core/emails/user/exchange_completed.html',
                context=context,
                recipient_list=[exchange.requester.email],
                extra_log_info=f"Exchange completed for requester: {exchange.requester.email}"
            ):
                success_count += 1
        
        # Notify item owner
        if exchange.item.donor and exchange.item.donor.email:
            subject = f"✅ Exchange Completed for '{exchange.item.title}'"
            context.update({
                'exchange': exchange,
                'notification_type': 'exchange_completed',
            })
            
            if NotificationService.send_notification(
                subject=subject,
                template_path='core/emails/user/exchange_completed.html',
                context=context,
                recipient_list=[exchange.item.donor.email],
                extra_log_info=f"Exchange completed for owner: {exchange.item.donor.email}"
            ):
                success_count += 1
        
        return success_count > 0

    @staticmethod
    def notify_item_approved_to_user(item):
        """Notify user when their item is approved"""
        subject = f"✅ Your Item '{item.title}' Has Been Approved"
        context = NotificationService.get_email_context()
        context.update({
            'item': item,
            'notification_type': 'item_approved',
        })
        
        if item.donor and item.donor.email:
            return NotificationService.send_notification(
                subject=subject,
                template_path='core/emails/user/item_approved.html',
                context=context,
                recipient_list=[item.donor.email],
                extra_log_info=f"Item approved: {item.donor.email}"
            )
        return False

    @staticmethod
    def notify_item_rejected_to_user(item, reason=""):
        """Notify user when their item is rejected"""
        subject = f"❌ Your Item '{item.title}' Needs Changes"
        context = NotificationService.get_email_context()
        context.update({
            'item': item,
            'rejection_reason': reason,
            'notification_type': 'item_rejected',
        })
        
        if item.donor and item.donor.email:
            return NotificationService.send_notification(
                subject=subject,
                template_path='core/emails/user/item_rejected.html',
                context=context,
                recipient_list=[item.donor.email],
                extra_log_info=f"Item rejected: {item.donor.email}"
            )
        return False

    # ============================================================================
    # ADMIN NOTIFICATIONS
    # ============================================================================

    @staticmethod
    def notify_new_user_registration(user):
        """Notify admin when new user creates account"""
        subject = f"👤 New User Registration – {user.username}"
        context = NotificationService.get_email_context()
        context.update({
            'user': user,
            'registration_date': user.date_joined.strftime("%Y-%m-%d %H:%M"),
            'notification_type': 'new_user_registration',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"New user: {user.username}"
        )

    @staticmethod
    def notify_new_item_posted(item):
        """Notify admin when user adds new clothing item"""
        subject = f"👕 New Donation Posted – {item.title}"
        context = NotificationService.get_email_context()
        context.update({
            'item': item,
            'donor': item.donor,
            'notification_type': 'new_item_posted',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"New item: {item.title}"
        )

    @staticmethod
    def notify_new_clothing_request(clothing_request):
        """Notify admin about new clothing request"""
        subject = f"🙏 New Clothing Request – {clothing_request.description[:50]}..."
        context = NotificationService.get_email_context()
        context.update({
            'clothing_request': clothing_request,
            'requester': clothing_request.requester,
            'notification_type': 'new_clothing_request',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"New request by: {clothing_request.requester.username}"
        )

    @staticmethod
    def notify_new_donation(item):
        """Notify admin about new donation"""
        subject = f"👕 New Donation Posted – {item.title} by {item.donor.username}"
        context = NotificationService.get_email_context()
        context.update({
            'item': item,
            'donor': item.donor,
            'notification_type': 'new_donation',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"New donation: {item.title} by {item.donor.username}"
        )

    @staticmethod
    def notify_exchange_initiated(exchange):
        """Notify admin when user requests exchange"""
        subject = f"🔄 Exchange Request – {exchange.requester.username}"
        context = NotificationService.get_email_context()
        context.update({
            'exchange': exchange,
            'notification_type': 'exchange_initiated',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Exchange initiated: {exchange.requester.username}"
        )

    @staticmethod
    def notify_exchange_request(exchange):
        """Notify admin about new exchange request"""
        subject = f"🔄 Exchange Request – {exchange.requester.username} → {exchange.item.title}"
        context = NotificationService.get_email_context()
        context.update({
            'exchange': exchange,
            'notification_type': 'exchange_request',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Exchange request: {exchange.requester.username} for {exchange.item.title}"
        )

    @staticmethod
    def notify_exchange_confirmed(exchange):
        """Notify admin about confirmed exchange"""
        subject = f"✅ Exchange Confirmed – {exchange.item.title}"
        context = NotificationService.get_email_context()
        context.update({
            'exchange': exchange,
            'notification_type': 'exchange_confirmed',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Exchange confirmed: {exchange.item.title}"
        )

    @staticmethod
    def notify_exchange_cancelled_admin(exchange):
        """Notify admin about cancelled exchange"""
        subject = f"❌ Exchange Cancelled – {exchange.item.title}"
        context = NotificationService.get_email_context()
        context.update({
            'exchange': exchange,
            'notification_type': 'exchange_cancelled',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Exchange cancelled: {exchange.item.title}"
        )

    @staticmethod
    def notify_item_approval(item, approved=True, reason=""):
        """Notify admin when item is approved/rejected"""
        status = "Approved" if approved else "Rejected"
        subject = f"✅ Item {status} – {item.title}"
        context = NotificationService.get_email_context()
        context.update({
            'item': item,
            'approval_status': status,
            'approval_reason': reason,
            'approval_date': timezone.now().strftime("%Y-%m-%d %H:%M"),
            'notification_type': 'item_approval',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Item {status.lower()}: {item.title}"
        )

    @staticmethod
    def notify_item_removed(item, action_type, removed_by):
        """Notify admin when item is taken or deleted"""
        action_display = "Marked as Taken" if action_type == 'taken' else "Deleted"
        subject = f"🗑️ Item Removed – {item.title}"
        context = NotificationService.get_email_context()
        context.update({
            'item': item,
            'action_type': action_display,
            'removed_by': removed_by,
            'removal_date': timezone.now().strftime("%Y-%m-%d %H:%M"),
            'notification_type': 'item_removed',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Item removed: {item.title}"
        )

    @staticmethod
    def notify_contact_message(contact_name, contact_email, subject_line, message_content):
        """Notify admin when user sends contact message"""
        subject = f"📩 New Support Message from {contact_name}"
        context = NotificationService.get_email_context()
        context.update({
            'contact_name': contact_name,
            'contact_email': contact_email,
            'message_subject': subject_line,
            'message_content': message_content,
            'received_date': timezone.now().strftime("%Y-%m-%d %H:%M"),
            'notification_type': 'contact_message',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Contact from: {contact_email}"
        )

    @staticmethod
    def notify_user_report(reported_by, reported_item, report_reason, report_type='item'):
        """Notify admin when user reports something"""
        subject = f"⚠️ Report Alert – {report_reason}"
        context = NotificationService.get_email_context()
        context.update({
            'reported_by': reported_by,
            'reported_item': reported_item,
            'report_reason': report_reason,
            'report_type': report_type,
            'report_date': timezone.now().strftime("%Y-%m-%d %H:%M"),
            'notification_type': 'user_report',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Report: {report_reason}"
        )

    @staticmethod
    def notify_system_alert(alert_type, alert_message, details=None):
        """Notify admin about system issues"""
        subject = f"📊 System Alert – {alert_type}"
        context = NotificationService.get_email_context()
        context.update({
            'alert_type': alert_type,
            'alert_message': alert_message,
            'alert_details': details or {},
            'alert_time': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            'notification_type': 'system_alert',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"System alert: {alert_type}"
        )

    @staticmethod
    def notify_account_deletion(user, deletion_type='requested'):
        """Notify admin when user requests account deletion"""
        action = "Requested" if deletion_type == 'requested' else "Completed"
        subject = f"🧍‍♂️ Account Deletion {action} – {user.email}"
        context = NotificationService.get_email_context()
        context.update({
            'user': user,
            'deletion_type': deletion_type,
            'deletion_date': timezone.now().strftime("%Y-%m-%d %H:%M"),
            'notification_type': 'account_deletion',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Account deletion {deletion_type}: {user.username}"
        )

    @staticmethod
    def notify_account_deletion_alt(user_email, username):
        """Notify admin about account deletion (alternative method)"""
        subject = f"🧍‍♂️ Account Deleted – {username} ({user_email})"
        context = NotificationService.get_email_context()
        context.update({
            'user_email': user_email,
            'username': username,
            'deletion_date': timezone.now().strftime("%Y-%m-%d %H:%M"),
            'notification_type': 'account_deletion',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Account deleted: {username} ({user_email})"
        )

    @staticmethod
    def notify_new_newsletter_subscriber(subscriber):
        """Notify admin when new newsletter subscriber"""
        subject = f"📬 New Newsletter Subscriber – {subscriber.email}"
        context = NotificationService.get_email_context()
        context.update({
            'subscriber': subscriber,
            'subscription_date': subscriber.subscribed_at.strftime("%Y-%m-%d %H:%M"),
            'notification_type': 'newsletter_subscriber',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"New subscriber: {subscriber.email}"
        )

    @staticmethod
    def notify_user_removed_item(item, user):
        """Notify admin when user removes their own item"""
        subject = f"🗑️ User Removed Item – {item.title}"
        context = NotificationService.get_email_context()
        context.update({
            'item': item,
            'user': user,
            'removal_date': timezone.now().strftime("%Y-%m-%d %H:%M"),
            'notification_type': 'user_removed_item',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"User removed item: {item.title}"
        )

    @staticmethod
    def notify_user_edited_item(item, user, changes):
        """Notify admin when user edits their item"""
        subject = f"✏️ Item Edited – {item.title}"
        context = NotificationService.get_email_context()
        context.update({
            'item': item,
            'user': user,
            'changes_made': changes,
            'edit_date': timezone.now().strftime("%Y-%m-%d %H:%M"),
            'notification_type': 'item_edited',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Item edited: {item.title}"
        )

    @staticmethod
    def notify_profile_updated(user, changes):
        """Notify admin when user updates profile"""
        subject = f"👤 Profile Updated – {user.username}"
        context = NotificationService.get_email_context()
        context.update({
            'user': user,
            'changes_made': changes,
            'update_date': timezone.now().strftime("%Y-%m-%d %H:%M"),
            'notification_type': 'profile_updated',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Profile updated: {user.username}"
        )

    # ============================================================================
    # NEWSLETTER FUNCTIONALITY - FIXED VERSION
    # ============================================================================

    @staticmethod
    def send_newsletter_welcome_email(subscriber):
        """Send welcome email to new newsletter subscribers"""
        print(f"🔍 DEBUG: Starting welcome email for {subscriber.email}")
        
        subject = "🌟 Welcome to ClothShare Newsletter!"
        
        context = NotificationService.get_email_context()
        context.update({
            'subscriber': subscriber,
            'notification_type': 'newsletter_welcome',
            'preferences': {
                'donation_updates': NotificationService.safe_get_preference(subscriber, 'receive_donation_updates', True),
                'exchange_notifications': NotificationService.safe_get_preference(subscriber, 'receive_exchange_notifications', True),
                'new_items_alerts': NotificationService.safe_get_preference(subscriber, 'receive_new_items_alerts', True),
                'community_news': NotificationService.safe_get_preference(subscriber, 'receive_community_news', True),
                'request_updates': NotificationService.safe_get_preference(subscriber, 'receive_request_updates', True),
            },
            'subscription_date': subscriber.subscribed_at.strftime("%B %d, %Y"),
        })
        
        print(f"🔍 DEBUG: Sending welcome email to {subscriber.email}")
        
        success = NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/newsletter/welcome.html',
            context=context,
            recipient_list=[subscriber.email],
            extra_log_info=f"Newsletter welcome to: {subscriber.email}"
        )
        
        if success:
            print(f"✅ Newsletter welcome email sent to: {subscriber.email}")
        else:
            print(f"❌ Failed to send newsletter welcome email to: {subscriber.email}")
        
        return success

    @staticmethod
    def send_newsletter_to_subscribers(notification_type, context_data):
        """Send newsletter notifications ONLY to subscribers who have opted in"""
        # Map notification types to preference fields - INCLUDING REQUEST UPDATES
        field_map = {
            'donation_updates': 'receive_donation_updates',
            'new_items_alerts': 'receive_new_items_alerts',
            'community_news': 'receive_community_news',
            'request_updates': 'receive_request_updates',
        }
        
        field_name = field_map.get(notification_type)
        if not field_name:
            logger.error(f"Unknown newsletter notification type: {notification_type}")
            return 0
        
        try:
            # Only send to active subscribers who have SPECIFICALLY opted in
            subscribers = NewsletterSubscriber.objects.filter(
                is_active=True,
                **{field_name: True}
            ).select_related('user')
        except Exception as e:
            print(f"❌ Error filtering subscribers: {e}")
            return 0
        
        sent_count = 0
        skipped_count = 0
        
        for subscriber in subscribers:
            try:
                # Additional safety check
                if not subscriber.email or '@' not in subscriber.email:
                    skipped_count += 1
                    continue
                    
                if not subscriber.is_active:
                    skipped_count += 1
                    continue
                    
                context = context_data.copy()
                context.update({
                    'subscriber': subscriber,
                    'unsubscribe_url': f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}/newsletter/unsubscribe/{subscriber.unsubscribe_token}/",
                })
                
                subject = NotificationService.get_newsletter_subject(notification_type, context)
                template_path = f'core/emails/newsletter/{notification_type}.html'
                
                success = NotificationService.send_notification(
                    subject=subject,
                    template_path=template_path,
                    context=context,
                    recipient_list=[subscriber.email],
                    extra_log_info=f"Newsletter: {notification_type} to {subscriber.email}"
                )
                
                if success:
                    # Safely update last_notification_sent if field exists
                    try:
                        if hasattr(subscriber, 'last_notification_sent'):
                            subscriber.last_notification_sent = timezone.now()
                            subscriber.save(update_fields=['last_notification_sent'])
                    except Exception:
                        pass  # Ignore if field doesn't exist
                    
                    sent_count += 1
                    print(f"✅ Newsletter sent to: {subscriber.email} for {notification_type}")
                else:
                    skipped_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to send newsletter to {subscriber.email}: {e}")
                skipped_count += 1
        
        logger.info(f"Newsletter stats - Sent: {sent_count}, Skipped: {skipped_count}, Type: {notification_type}")
        print(f"📊 Newsletter '{notification_type}': {sent_count} sent, {skipped_count} skipped")
        return sent_count

    @staticmethod
    def get_newsletter_subject(notification_type, context):
        """Get subject line for newsletter emails - FIXED VERSION"""
        # FIX: Safely handle clothing_request model instance instead of dictionary
        if notification_type == 'request_updates':
            clothing_request = context.get('clothing_request')
            if clothing_request:
                # Handle both model instance and dictionary
                if hasattr(clothing_request, 'description'):
                    description = clothing_request.description
                else:
                    description = clothing_request.get('description', 'New Request')
                request_desc = description[:50] + '...' if description else 'New Request'
            else:
                request_desc = 'New Request'
        else:
            request_desc = 'New Request'
            
        subjects = {
            'donation_updates': f"🎉 New Donation: {context.get('item_title', 'New Items Available')}",
            'new_items_alerts': "👕 New Clothing Items Available",
            'community_news': "📢 ClothShare Community News",
            'request_updates': f"🙏 New Clothing Request: {request_desc}",
        }
        return subjects.get(notification_type, "ClothShare Update")

    @staticmethod
    def send_new_item_newsletter(item):
        """Send newsletter to subscribers about new item - ONLY if they opted in"""
        # First check if there are any subscribers who want new item alerts
        try:
            subscribers_count = NewsletterSubscriber.objects.filter(
                is_active=True,
                receive_new_items_alerts=True
            ).count()
        except Exception as e:
            print(f"❌ Error checking subscribers: {e}")
            return 0
        
        if subscribers_count == 0:
            print("ℹ️ No subscribers opted in for new item alerts - skipping newsletter")
            return 0
            
        context = NotificationService.get_email_context()
        context.update({
            'item': item,
            'donor': item.donor,
            'item_title': item.title,
            'notification_type': 'new_items_alerts',
        })
        
        return NotificationService.send_newsletter_to_subscribers('new_items_alerts', context)

    @staticmethod
    def send_donation_newsletter(item):
        """Send newsletter to subscribers about new donation - ONLY if they opted in"""
        try:
            subscribers_count = NewsletterSubscriber.objects.filter(
                is_active=True,
                receive_donation_updates=True
            ).count()
        except Exception as e:
            print(f"❌ Error checking subscribers: {e}")
            return 0
        
        if subscribers_count == 0:
            print("ℹ️ No subscribers opted in for donation updates - skipping newsletter")
            return 0
            
        context = NotificationService.get_email_context()
        context.update({
            'item': item,
            'notification_type': 'donation_updates',
        })
        
        return NotificationService.send_newsletter_to_subscribers('donation_updates', context)

    @staticmethod
    def send_community_newsletter(news_content):
        """Send community newsletter to subscribers"""
        try:
            subscribers_count = NewsletterSubscriber.objects.filter(
                is_active=True,
                receive_community_news=True
            ).count()
        except Exception as e:
            print(f"❌ Error checking subscribers: {e}")
            return 0
        
        if subscribers_count == 0:
            print("ℹ️ No subscribers opted in for community news - skipping newsletter")
            return 0
            
        context = NotificationService.get_email_context()
        context.update({
            'news_content': news_content,
            'notification_type': 'community_news',
        })
        
        return NotificationService.send_newsletter_to_subscribers('community_news', context)

    @staticmethod
    def send_request_newsletter(clothing_request):
        """Send newsletter to subscribers about new clothing request - ONLY if they opted in"""
        print(f"🔍 DEBUG: Starting request newsletter for: {clothing_request.description[:50]}...")
        
        # First check if there are any subscribers who want request updates
        try:
            subscribers_count = NewsletterSubscriber.objects.filter(
                is_active=True,
                receive_request_updates=True
            ).count()
        except Exception as e:
            print(f"❌ Error checking request newsletter subscribers: {e}")
            subscribers_count = 0
        
        if subscribers_count == 0:
            print("ℹ️ No subscribers opted in for request updates - skipping request newsletter")
            return 0
            
        context = NotificationService.get_email_context()
        context.update({
            'clothing_request': clothing_request,
            'requester': clothing_request.requester,
            'request_description': clothing_request.description[:50] + '...' if clothing_request.description else 'New Request',  # Pre-process description
            'notification_type': 'request_updates',
        })
        
        return NotificationService.send_newsletter_to_subscribers('request_updates', context)

    @staticmethod
    def get_newsletter_statistics():
        """Get detailed statistics about newsletter subscriptions"""
        try:
            total_subscribers = NewsletterSubscriber.objects.filter(is_active=True).count()
            
            stats = {
                'total_subscribers': total_subscribers,
                'donation_updates': NewsletterSubscriber.objects.filter(
                    is_active=True, receive_donation_updates=True
                ).count(),
                'new_items_alerts': NewsletterSubscriber.objects.filter(
                    is_active=True, receive_new_items_alerts=True
                ).count(),
                'community_news': NewsletterSubscriber.objects.filter(
                    is_active=True, receive_community_news=True
                ).count(),
                'exchange_notifications': NewsletterSubscriber.objects.filter(
                    is_active=True, receive_exchange_notifications=True
                ).count(),
                'request_updates': NewsletterSubscriber.objects.filter(
                    is_active=True, receive_request_updates=True
                ).count(),
            }
            
            # Calculate percentages
            if total_subscribers > 0:
                for key in ['donation_updates', 'new_items_alerts', 'community_news', 'exchange_notifications', 'request_updates']:
                    stats[f'{key}_percent'] = round((stats[key] / total_subscribers) * 100, 1)
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting newsletter stats: {e}")
            return {
                'total_subscribers': 0,
                'donation_updates': 0,
                'new_items_alerts': 0,
                'community_news': 0,
                'exchange_notifications': 0,
                'request_updates': 0,
            }

    @staticmethod
    def debug_newsletter_preferences():
        """Debug method to check newsletter preferences"""
        try:
            stats = NotificationService.get_newsletter_statistics()
            
            print("📊 NEWSLETTER SUBSCRIPTION STATISTICS:")
            print(f"   Total active subscribers: {stats['total_subscribers']}")
            print(f"   Donation updates: {stats['donation_updates']} ({stats.get('donation_updates_percent', 0)}%)")
            print(f"   New items alerts: {stats['new_items_alerts']} ({stats.get('new_items_alerts_percent', 0)}%)")
            print(f"   Community news: {stats['community_news']} ({stats.get('community_news_percent', 0)}%)")
            print(f"   Exchange notifications: {stats['exchange_notifications']} ({stats.get('exchange_notifications_percent', 0)}%)")
            print(f"   Request updates: {stats['request_updates']} ({stats.get('request_updates_percent', 0)}%)")
            
            # Show first few subscribers as sample
            sample_subscribers = NewsletterSubscriber.objects.filter(is_active=True)[:3]
            print("\n🔍 SAMPLE SUBSCRIBERS:")
            for sub in sample_subscribers:
                prefs = []
                if NotificationService.safe_get_preference(sub, 'receive_donation_updates', True): 
                    prefs.append("donations")
                if NotificationService.safe_get_preference(sub, 'receive_new_items_alerts', True): 
                    prefs.append("new_items")
                if NotificationService.safe_get_preference(sub, 'receive_community_news', True): 
                    prefs.append("community")
                if NotificationService.safe_get_preference(sub, 'receive_exchange_notifications', True): 
                    prefs.append("exchanges")
                if NotificationService.safe_get_preference(sub, 'receive_request_updates', True): 
                    prefs.append("requests")
                
                print(f"   📧 {sub.email}: {', '.join(prefs) if prefs else 'no preferences'}")
                
            return stats
            
        except Exception as e:
            print(f"❌ Error debugging newsletter preferences: {e}")
            return None

    @staticmethod
    def verify_subscription_preferences(email):
        """Verify and return subscription preferences for a specific email"""
        try:
            subscriber = NewsletterSubscriber.objects.get(email=email, is_active=True)
            preferences = {
                'is_subscribed': True,
                'receive_donation_updates': NotificationService.safe_get_preference(subscriber, 'receive_donation_updates', True),
                'receive_new_items_alerts': NotificationService.safe_get_preference(subscriber, 'receive_new_items_alerts', True),
                'receive_community_news': NotificationService.safe_get_preference(subscriber, 'receive_community_news', True),
                'receive_exchange_notifications': NotificationService.safe_get_preference(subscriber, 'receive_exchange_notifications', True),
                'receive_request_updates': NotificationService.safe_get_preference(subscriber, 'receive_request_updates', True),
            }
            return preferences
        except NewsletterSubscriber.DoesNotExist:
            return {'is_subscribed': False}

    @staticmethod
    def send_unsubscribe_confirmation_email(subscriber):
        """Send confirmation email when user unsubscribes"""
        try:
            subject = "😢 You've Been Unsubscribed from ClothShare Newsletter"
            
            context = NotificationService.get_email_context()
            context.update({
                'subscriber': subscriber,
                'unsubscribe_date': timezone.now().strftime("%B %d, %Y at %I:%M %p"),
                'notification_type': 'unsubscribe_confirmation',
                'resubscribe_url': f"{context['site_url']}/newsletter/preferences/",
            })
            
            return NotificationService.send_notification(
                subject=subject,
                template_path='core/emails/newsletter/unsubscribe_confirmation.html',
                context=context,
                recipient_list=[subscriber.email],
                extra_log_info=f"Unsubscribe confirmation to: {subscriber.email}"
            )
            
        except Exception as e:
            print(f"❌ Failed to send unsubscribe confirmation to {subscriber.email}: {e}")
            return False

    @staticmethod
    def notify_newsletter_unsubscribe_admin(subscriber):
        """Notify admin when someone unsubscribes"""
        subject = f"📉 Newsletter Unsubscribe: {subscriber.email}"
        
        context = NotificationService.get_email_context()
        context.update({
            'subscriber': subscriber,
            'user_info': f"User: {subscriber.user.username}" if subscriber.user else "No user account",
            'unsubscribe_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            'notification_type': 'newsletter_unsubscribe_admin',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Newsletter unsubscribe: {subscriber.email}"
        )

    # ============================================================================
    # SCHEDULED TASKS AND SUMMARY REPORTS
    # ============================================================================

    @staticmethod
    def send_weekly_activity_summary():
        """Send weekly activity summary to admin"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        
        # Get statistics
        new_users = User.objects.filter(date_joined__range=[start_date, end_date]).count()
        new_items = ClothingItem.objects.filter(created_at__range=[start_date, end_date]).count()
        completed_exchanges = Exchange.objects.filter(
            status='completed',
            completed_at__range=[start_date, end_date]
        ).count()
        new_requests = ClothingRequest.objects.filter(created_at__range=[start_date, end_date]).count()
        
        subject = '📊 Weekly Activity Summary'
        context = NotificationService.get_email_context()
        context.update({
            'period': 'Weekly',
            'start_date': start_date.strftime("%Y-%m-%d"),
            'end_date': end_date.strftime("%Y-%m-%d"),
            'new_users': new_users,
            'new_items': new_items,
            'completed_exchanges': completed_exchanges,
            'new_requests': new_requests,
            'notification_type': 'weekly_summary',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Weekly summary: {new_users} users, {new_items} items, {completed_exchanges} exchanges"
        )

    @staticmethod
    def send_monthly_statistics():
        """Send monthly statistics to admin"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Get comprehensive statistics
        total_users = User.objects.count()
        new_users = User.objects.filter(date_joined__range=[start_date, end_date]).count()
        total_items = ClothingItem.objects.count()
        new_items = ClothingItem.objects.filter(created_at__range=[start_date, end_date]).count()
        total_exchanges = Exchange.objects.filter(status='completed').count()
        new_exchanges = Exchange.objects.filter(
            status='completed',
            completed_at__range=[start_date, end_date]
        ).count()
        
        # User growth rate
        previous_month_users = User.objects.filter(
            date_joined__range=[start_date - timedelta(days=30), start_date]
        ).count()
        user_growth = ((new_users - previous_month_users) / previous_month_users * 100) if previous_month_users > 0 else 0
        
        subject = '📈 Monthly Statistics Report'
        context = NotificationService.get_email_context()
        context.update({
            'period': 'Monthly',
            'start_date': start_date.strftime("%Y-%m-%d"),
            'end_date': end_date.strftime("%Y-%m-%d"),
            'total_users': total_users,
            'new_users': new_users,
            'user_growth': round(user_growth, 1),
            'total_items': total_items,
            'new_items': new_items,
            'total_exchanges': total_exchanges,
            'new_exchanges': new_exchanges,
            'notification_type': 'monthly_statistics',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info=f"Monthly stats: {new_users} new users ({user_growth}% growth)"
        )

    @staticmethod
    def setup_scheduled_notifications():
        """Method to be called by celery or cron for scheduled notifications"""
        try:
            # Send weekly summary
            NotificationService.send_weekly_activity_summary()
            
            # Send monthly summary on 1st of each month
            if timezone.now().day == 1:
                NotificationService.send_monthly_statistics()
                
            print("✅ Scheduled notifications completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to send scheduled notifications: {e}")
            print(f"❌ Scheduled notifications failed: {e}")

    # ============================================================================
    # DEBUG AND TESTING METHODS
    # ============================================================================

    @staticmethod
    def test_welcome_email():
        """Test welcome email functionality"""
        try:
            # Get the most recent subscriber
            subscriber = NewsletterSubscriber.objects.filter(is_active=True).last()
            if subscriber:
                print(f"🔍 Testing welcome email for: {subscriber.email}")
                result = NotificationService.send_newsletter_welcome_email(subscriber)
                print(f"🔍 Test result: {result}")
                return result
            else:
                print("❌ No subscribers found to test")
                return False
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False

    @staticmethod
    def debug_notification_delivery():
        """Debug method to test notification delivery"""
        try:
            test_user = User.objects.first()
            test_item = ClothingItem.objects.first()
            test_request = ClothingRequest.objects.first()
            
            if test_user and test_item and test_request:
                print("🔍 Testing notification delivery...")
                
                # Test user notifications
                test_changes = {'username': 'test_old → test_new'}
                result = NotificationService.notify_profile_updated(test_user, test_changes)
                print(f"🔍 Profile update notification: {result}")
                
                # Test admin notifications
                item_changes = {'title': 'Test Old → Test New'}
                result = NotificationService.notify_user_edited_item(test_item, test_user, item_changes)
                print(f"🔍 Item edit notification: {result}")
                
                # Test request newsletter
                result = NotificationService.send_request_newsletter(test_request)
                print(f"🔍 Request newsletter: {result}")
                
                return True
            else:
                print("❌ No test data available")
                return False
                
        except Exception as e:
            print(f"❌ Debug error: {e}")
            return False

    @staticmethod
    def test_email_configuration():
        """Test email configuration by sending a test email"""
        subject = "🧪 Test Email - ClothShare Notification System"
        context = NotificationService.get_email_context()
        context.update({
            'test_message': 'This is a test email to verify the notification system is working correctly.',
            'notification_type': 'test',
        })
        
        admin_email = NotificationService.get_admin_email()
        return NotificationService.send_notification(
            subject=subject,
            template_path='core/emails/admin/general_notification.html',
            context=context,
            recipient_list=[admin_email],
            extra_log_info="Email configuration test"
        )