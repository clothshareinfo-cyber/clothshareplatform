from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from core.models import NewsletterSubscriber, ClothingItem, Exchange, ClothingRequest
from core.services.notification_service import NotificationService

# Get the custom user model
User = get_user_model()

print(" Loading ClothShare signals...")


# USER SIGNALS

@receiver(post_save, sender=User)
def handle_new_user(sender, instance, created, **kwargs):
    """
    Automatically notify admin when a new user registers
    """
    if created:
        try:
            print(f" New user detected: {instance.username} ({instance.email})")
            NotificationService.notify_new_user_registration(instance)
            print(f" Admin notified about new user: {instance.username}")
        except Exception as e:
            print(f" Failed to notify admin about new user {instance.username}: {e}")


# CLOTHING ITEM SIGNALS


@receiver(post_save, sender=ClothingItem)
def handle_new_item(sender, instance, created, **kwargs):
    """
    Automatically notify admin when a new clothing item is posted
    """
    if created and instance.is_active:
        try:
            print(f" New item detected: '{instance.title}' by {instance.donor.username}")
            NotificationService.notify_new_item_posted(instance)
            print(f" Admin notified about new item: {instance.title}")
        except Exception as e:
            print(f" Failed to notify admin about new item {instance.title}: {e}")

@receiver(pre_save, sender=ClothingItem)
def handle_item_changes(sender, instance, **kwargs):
    """
    Track when items are edited and notify admin
    """
    if instance.pk:  # Only for existing items (not new creations)
        try:
            old_item = ClothingItem.objects.get(pk=instance.pk)
            changes = {}
            
            # Track important field changes
            for field in ['title', 'description', 'mode', 'status']:
                old_value = getattr(old_item, field)
                new_value = getattr(instance, field)
                if old_value != new_value:
                    changes[field] = f"'{old_value}' → '{new_value}'"
            
            # If there are changes, notify admin
            if changes:
                print(f" Item edited: '{instance.title}' by {instance.donor.username}")
                NotificationService.notify_user_edited_item(instance, instance.donor, changes)
                print(f" Admin notified about item edits: {instance.title}")
                
        except ClothingItem.DoesNotExist:
            pass  # Item doesn't exist yet (being created)
        except Exception as e:
            print(f" Failed to track item changes for {instance.title}: {e}")

@receiver(post_delete, sender=ClothingItem)
def handle_item_deletion(sender, instance, **kwargs):
    """
    Notify admin when an item is deleted
    """
    try:
        print(f" Item deleted: '{instance.title}' by {instance.donor.username}")
        NotificationService.notify_item_removed(instance, 'deleted', instance.donor)
        print(f" Admin notified about item deletion: {instance.title}")
    except Exception as e:
        print(f"Failed to notify admin about item deletion {instance.title}: {e}")


# EXCHANGE SIGNALS


@receiver(post_save, sender=Exchange)
def handle_new_exchange(sender, instance, created, **kwargs):
    """
    Automatically notify admin when a new exchange is initiated
    """
    if created:
        try:
            print(f" New exchange detected: {instance.requester.username} → '{instance.item.title}'")
            NotificationService.notify_exchange_initiated(instance)
            print(f" Admin notified about new exchange")
        except Exception as e:
            print(f" Failed to notify admin about new exchange: {e}")

@receiver(pre_save, sender=Exchange)
def handle_exchange_status_changes(sender, instance, **kwargs):
    """
    Track exchange status changes and notify admin
    """
    if instance.pk:  # Only for existing exchanges
        try:
            old_exchange = Exchange.objects.get(pk=instance.pk)
            
            # Check if status changed
            if old_exchange.status != instance.status:
                print(f" Exchange status changed: {old_exchange.status} → {instance.status}")
                
                if instance.status == 'confirmed':
                    NotificationService.notify_exchange_confirmed(instance)
                    print(f" Admin notified about confirmed exchange")
                elif instance.status == 'completed':
                    # Also mark the item as taken
                    instance.item.status = 'taken'
                    instance.item.save()
                    print(f" Item marked as taken: {instance.item.title}")
                elif instance.status == 'cancelled':
                    NotificationService.notify_exchange_cancelled(instance)
                    print(f" Admin notified about cancelled exchange")
                    
        except Exchange.DoesNotExist:
            pass
        except Exception as e:
            print(f" Failed to track exchange status changes: {e}")

# CLOTHING REQUEST SIGNALS

@receiver(post_save, sender=ClothingRequest)
def handle_new_clothing_request(sender, instance, created, **kwargs):
    """
    Automatically notify admin when a new clothing request is made
    """
    if created and instance.status == 'open':
        try:
            print(f" New clothing request: by {instance.requester.username}")
            NotificationService.notify_new_clothing_request(instance)
            print(f" Admin notified about new clothing request")
        except Exception as e:
            print(f" Failed to notify admin about clothing request: {e}")


# NEWSLETTER SIGNALS

@receiver(post_save, sender=NewsletterSubscriber)
def handle_new_subscriber(sender, instance, created, **kwargs):
    """
    Automatically notify admin when someone subscribes to newsletter
    AND send welcome email to the subscriber
    """
    if created and instance.is_active:
        try:
            print(f" New newsletter subscriber: {instance.email}")
            
            # Notify admin about new subscriber
            NotificationService.notify_new_newsletter_subscriber(instance)
            print(f" Admin notified about new subscriber: {instance.email}")
            
            # Send welcome email to the subscriber
            NotificationService.send_newsletter_welcome_email(instance)
            print(f" Welcome email sent to subscriber: {instance.email}")
            
        except Exception as e:
            print(f" Failed to process new subscriber {instance.email}: {e}")

@receiver(pre_save, sender=NewsletterSubscriber)
def handle_subscriber_changes(sender, instance, **kwargs):
    """
    Track when subscribers update their preferences
    """
    if instance.pk:  # Only for existing subscribers
        try:
            old_subscriber = NewsletterSubscriber.objects.get(pk=instance.pk)
            changes = {}
            
            # Track preference changes
            preference_fields = [
                'receive_donation_updates',
                'receive_exchange_notifications', 
                'receive_new_items_alerts',
                'receive_community_news',
                'receive_request_updates'
            ]
            
            for field in preference_fields:
                old_value = getattr(old_subscriber, field)
                new_value = getattr(instance, field)
                if old_value != new_value:
                    changes[field] = f"{'' if new_value else ''}"
            
            if changes:
                print(f"⚙️ Subscriber preferences updated: {instance.email}")
                # You could notify admin about preference changes here if needed
                
        except NewsletterSubscriber.DoesNotExist:
            pass
        except Exception as e:
            print(f" Failed to track subscriber changes: {e}")

# USER PROFILE SIGNALS


@receiver(post_save, sender=User)
def handle_user_profile_updates(sender, instance, created, **kwargs):
    """
    Track user profile updates (via User model changes)
    """
    if not created:  # Only for updates, not new users
        try:
            old_user = User.objects.get(pk=instance.pk)
            changes = {}
            
            # Track important user field changes
            for field in ['first_name', 'last_name', 'email']:
                old_value = getattr(old_user, field)
                new_value = getattr(instance, field)
                if old_value != new_value:
                    changes[field] = f"'{old_value}' → '{new_value}'"
            
            if changes:
                print(f"👤 User profile updated: {instance.username}")
                NotificationService.notify_profile_updated(instance, changes)
                print(f" Admin notified about profile update: {instance.username}")
                
        except User.DoesNotExist:
            pass
        except Exception as e:
            print(f" Failed to track user profile changes: {e}")

print(" All ClothShare signals loaded successfully!")
