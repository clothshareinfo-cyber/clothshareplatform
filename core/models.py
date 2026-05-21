from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.crypto import get_random_string
from django.urls import reverse
from django.db.models import Q

def validate_image_size(value):
    filesize = value.size
    if filesize > 5 * 1024 * 1024: 
        raise ValidationError(_("The maximum file size that can be uploaded is 5MB"))
    return value

class Category(models.Model):
    CATEGORY_CHOICES = [
        ('women', "Women's Clothing"),
        ('men', "Men's Clothing"),
        ('kids', "Kids Clothing"),
        ('shoes', "Shoes"),
        ('accessories', "Accessories"),
    ]
    
    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-tshirt')
    image = models.ImageField(
        upload_to='categories/%Y/%m/%d/', 
        null=True, 
        blank=True,
        validators=[validate_image_size]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.get_name_display()
    
    @property
    def display_name(self):
        return self.get_name_display()

class Size(models.Model):
    SIZE_CHOICES = [
        ('xs', 'XS'),
        ('s', 'S'),
        ('m', 'M'),
        ('l', 'L'),
        ('xl', 'XL'),
        ('xxl', 'XXL'),
        ('one-size', 'One Size'),
    ]
    
    name = models.CharField(max_length=10, choices=SIZE_CHOICES, unique=True)
    description = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return self.get_name_display()

class Condition(models.Model):
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('like-new', 'Like New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
    ]
    
    name = models.CharField(max_length=20, choices=CONDITION_CHOICES, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.get_name_display()

class Gender(models.Model):
    GENDER_CHOICES = [
        ('men', 'Men'),
        ('women', 'Women'),
        ('unisex', 'Unisex'),
        ('kids', 'Kids'),
    ]
    
    name = models.CharField(max_length=10, choices=GENDER_CHOICES, unique=True)
    
    def __str__(self):
        return self.get_name_display()

class ClothingItem(models.Model):
    MODE_CHOICES = [
        ('donation', 'Donation (Free)'),
        ('exchange', 'Exchange'),
    ]
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('taken', 'Taken'),
        ('expired', 'Expired'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Categorical Information
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True, blank=True)
    condition = models.ForeignKey(Condition, on_delete=models.CASCADE)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True, blank=True)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='donation')
    
    # Ownership and Status
    donor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='donated_items')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    
  
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.CharField(max_length=50, blank=True, choices=[
        ('user_deletion', 'User Account Deleted'),
        ('manual', 'Manual Deactivation'),
        ('expired', 'Auto-expired'),
    ])
    
    # Location
    location = models.CharField(max_length=100, blank=True)
    
    # Flags
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    
    # Additional fields from your HTML forms
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['category', 'mode']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = "Clothing Item"
        verbose_name_plural = "Clothing Items"
    
    def __str__(self):
        return f"{self.title} - {self.donor.username}"
    
    def save(self, *args, **kwargs):
        if not self.expiry_date:
            # Set expiry date to 30 days from creation
            self.expiry_date = timezone.now() + timezone.timedelta(days=30)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return self.expiry_date and timezone.now() > self.expiry_date
    
    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()
    
    @property
    def image_count(self):
        return self.images.count()
    
    def get_tags_list(self):
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []

class ItemImage(models.Model):
    item = models.ForeignKey(ClothingItem, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to='clothing_items/%Y/%m/%d/',
        validators=[validate_image_size]
    )
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', 'uploaded_at']
        verbose_name = "Item Image"
        verbose_name_plural = "Item Images"
    
    def __str__(self):
        return f"Image for {self.item.title}"
    
    def save(self, *args, **kwargs):
       
        if self.is_primary:
            ItemImage.objects.filter(item=self.item, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)

class ClothingRequest(models.Model):
    URGENCY_CHOICES = [
        ('low', 'Low - Whenever available'),
        ('medium', 'Medium - In the next few weeks'),
        ('high', 'High - As soon as possible'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='clothing_requests')
    
    # Request Details
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True, blank=True)
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='medium')
    
    # Status and Timestamps
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=50, blank=True, choices=[
        ('user_deletion', 'User Account Deleted'),
        ('manual', 'Manual Cancellation'),
        ('expired', 'Auto-expired'),
    ])
    
    # Fulfillment
    fulfilled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='fulfilled_requests'
    )
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    fulfilled_with_item = models.ForeignKey(
        ClothingItem, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='fulfilled_requests'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'urgency']),
            models.Index(fields=['category', 'status']),
        ]
        verbose_name = "Clothing Request"
        verbose_name_plural = "Clothing Requests"
    
    def __str__(self):
        return f"Request by {self.requester.username} - {self.category.display_name}"
    
    def save(self, *args, **kwargs):
        if not self.expiry_date and self.status == 'open':
           
            if self.urgency == 'high':
                days = 7
            elif self.urgency == 'medium':
                days = 30
            else:
                days = 90
            self.expiry_date = timezone.now() + timezone.timedelta(days=days)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return self.expiry_date and timezone.now() > self.expiry_date

class Exchange(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(ClothingItem, on_delete=models.CASCADE, related_name='exchanges')
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requested_exchanges')
    donor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='donated_exchanges')
    

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True)
    
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
   
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=50, blank=True, choices=[
        ('user_deletion', 'User Account Deleted'),
        ('manual', 'Manual Cancellation'),
        ('agreement', 'Mutual Agreement'),
    ])
    
   
    exchange_location = models.CharField(max_length=200, blank=True)
    exchange_notes = models.TextField(blank=True)
    
   
    donor_rating = models.PositiveSmallIntegerField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    requester_rating = models.PositiveSmallIntegerField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    donor_feedback = models.TextField(blank=True)
    requester_feedback = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
        verbose_name = "Exchange"
        verbose_name_plural = "Exchanges"
    
    def __str__(self):
        return f"Exchange: {self.item.title} - {self.requester.username}"

class UserProfile(models.Model):
    AFFILIATION_CHOICES = [
        ('university', 'University'),
        ('church', 'Church'),
        ('community', 'Community Center'),
        ('other', 'Other'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    
    
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True)
    affiliation = models.CharField(max_length=20, choices=AFFILIATION_CHOICES, blank=True)
    bio = models.TextField(blank=True)
    
  
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/%d/', 
        null=True, 
        blank=True,
        validators=[validate_image_size]
    )
    
   
    items_donated = models.PositiveIntegerField(default=0)
    items_received = models.PositiveIntegerField(default=0)
    exchanges_completed = models.PositiveIntegerField(default=0)
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    community_updates = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"Profile of {self.user.username}"
    
    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
    
    @property
    def is_online(self):
        """Check if user was active in the last 15 minutes"""
        if self.user.last_login:
            return (timezone.now() - self.user.last_login).total_seconds() < 900
        return False

class Badge(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class")
    criteria_donations = models.PositiveIntegerField(default=0)
    criteria_exchanges = models.PositiveIntegerField(default=0)
    criteria_community = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=7, default='#4a6fa5', help_text="Hex color code")
    
    class Meta:
        ordering = ['name']
        verbose_name = "Badge"
        verbose_name_plural = "Badges"
    
    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'badge']
        ordering = ['-earned_at']
        verbose_name = "User Badge"
        verbose_name_plural = "User Badges"
    
    def __str__(self):
        return f"{self.badge.name} - {self.user.username}"

class CommunityImpact(models.Model):
    # These fields store aggregated community statistics
    total_items_donated = models.PositiveIntegerField(default=0)
    total_items_exchanged = models.PositiveIntegerField(default=0)
    total_waste_prevented = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # in kg
    total_community_members = models.PositiveIntegerField(default=0)
    
    # Timestamp for when these stats were last updated
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Community Impact"
    
    def __str__(self):
        return f"Community Impact Stats - {self.last_updated.date()}"
    
    def save(self, *args, **kwargs):
     
        if not self.pk and CommunityImpact.objects.exists():
            
            existing = CommunityImpact.objects.first()
            existing.total_items_donated = self.total_items_donated
            existing.total_items_exchanged = self.total_items_exchanged
            existing.total_waste_prevented = self.total_waste_prevented
            existing.total_community_members = self.total_community_members
            return existing.save(*args, **kwargs)
        super().save(*args, **kwargs)

class Notification(models.Model):
    TYPE_CHOICES = [
        ('exchange_request', 'Exchange Request'),
        ('request_fulfilled', 'Request Fulfilled'),
        ('donation_approved', 'Donation Approved'),
        ('community_update', 'Community Update'),
        ('system', 'System Notification'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_item = models.ForeignKey(ClothingItem, on_delete=models.CASCADE, null=True, blank=True)
    related_request = models.ForeignKey(ClothingRequest, on_delete=models.CASCADE, null=True, blank=True)
    
    # Read status
    is_read = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
    
    def __str__(self):
        return f"{self.type} - {self.user.username}"


class NewsletterSubscriberManager(models.Manager):
    def get_subscribers_for_notification(self, notification_type):
        """Get subscribers who want to receive specific notification types"""
        field_map = {
            'donation_updates': 'receive_donation_updates',
            'community_news': 'receive_community_news',
            'new_items_alerts': 'receive_new_items_alerts',
            'exchange_notifications': 'receive_exchange_notifications',
            'request_updates': 'receive_request_updates',  # ADDED THIS LINE
        }
        
        field_name = field_map.get(notification_type)
        if not field_name:
            return self.none()
            
    
        if not hasattr(NewsletterSubscriber, field_name):
            print(f"⚠️ Field {field_name} not found in NewsletterSubscriber, using fallback")
           
            if notification_type == 'request_updates':
                field_name = 'receive_community_news'
            else:
                return self.none()
            
        filter_kwargs = {
            'is_active': True,
            field_name: True
        }
        return self.filter(**filter_kwargs)


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    unsubscribe_token = models.CharField(max_length=100, unique=True, blank=True)
    
  
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='newsletter_subscription'
    )
    
   
    receive_donation_updates = models.BooleanField(default=True, verbose_name="Donation Updates")
    receive_community_news = models.BooleanField(default=True, verbose_name="Community News")
    receive_new_items_alerts = models.BooleanField(default=True, verbose_name="New Items Alerts")
    receive_exchange_notifications = models.BooleanField(default=True, verbose_name="Exchange Notifications")
    receive_request_updates = models.BooleanField(default=True, verbose_name="Clothing Request Updates")  # ADDED THIS LINE
    
   
    last_notification_sent = models.DateTimeField(null=True, blank=True)
    
    objects = NewsletterSubscriberManager()
    
    class Meta:
        ordering = ['-subscribed_at']
        verbose_name = "Newsletter Subscriber"
        verbose_name_plural = "Newsletter Subscribers"
    
    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        if not self.unsubscribe_token:
            self.unsubscribe_token = get_random_string(50)
        super().save(*args, **kwargs)
    
    @property
    def can_receive_emails(self):
        """Check if subscriber should receive emails based on preferences"""
        return self.is_active and (
            self.receive_donation_updates or 
            self.receive_community_news or 
            self.receive_new_items_alerts or
            self.receive_exchange_notifications or
            self.receive_request_updates 
        )
    
    def get_unsubscribe_url(self):
        """Generate unsubscribe URL for emails"""
        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        return f"{site_url}/newsletter/unsubscribe/{self.unsubscribe_token}/"
    
    @classmethod
    def get_subscribers_for_notification(cls, notification_type):
        """Get all subscribers who want to receive specific notification types via Gmail"""
        return cls.objects.get_subscribers_for_notification(notification_type)


def get_community_stats():
    """
    Get community statistics for homepage and impact section
    Returns consistent data structure for all views
    """
    try:
        impact = CommunityImpact.objects.first()
        if not impact:
            impact = CommunityImpact.objects.create()
        
        return {
            'items_donated': impact.total_items_donated,
            'successful_exchanges': impact.total_items_exchanged,
            'community_members': impact.total_community_members,
            'waste_prevented_kg': impact.total_waste_prevented,
        }
    except Exception as e:
        print(f"Error getting community stats: {e}")
        return {
            'items_donated': 0,
            'successful_exchanges': 0,
            'community_members': 0,
            'waste_prevented_kg': 0,
        }

# Helper function for newsletter statistics - UPDATED
def get_newsletter_stats():
    """
    Get newsletter subscription statistics
    """
    try:
        total_subscribers = NewsletterSubscriber.objects.filter(is_active=True).count()
        recent_subscribers = NewsletterSubscriber.objects.filter(
            is_active=True,
            subscribed_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        
        total_inactive = NewsletterSubscriber.objects.filter(is_active=False).count()
        
        # Get preference statistics
        stats = {
            'total_subscribers': total_subscribers,
            'recent_subscribers': recent_subscribers,
            'total_inactive': total_inactive,
            'subscription_rate': (recent_subscribers / total_subscribers * 100) if total_subscribers > 0 else 0,
            'donation_updates': NewsletterSubscriber.objects.filter(is_active=True, receive_donation_updates=True).count(),
            'community_news': NewsletterSubscriber.objects.filter(is_active=True, receive_community_news=True).count(),
            'new_items_alerts': NewsletterSubscriber.objects.filter(is_active=True, receive_new_items_alerts=True).count(),
            'exchange_notifications': NewsletterSubscriber.objects.filter(is_active=True, receive_exchange_notifications=True).count(),
            'request_updates': NewsletterSubscriber.objects.filter(is_active=True, receive_request_updates=True).count(),  # ADDED THIS LINE
        }
        
        # Calculate percentages
        if total_subscribers > 0:
            for key in ['donation_updates', 'community_news', 'new_items_alerts', 'exchange_notifications', 'request_updates']:
                stats[f'{key}_percent'] = round((stats[key] / total_subscribers) * 100, 1)
        
        return stats
        
    except Exception as e:
        print(f"Error getting newsletter stats: {e}")
        return {
            'total_subscribers': 0,
            'recent_subscribers': 0,
            'total_inactive': 0,
            'subscription_rate': 0,
            'donation_updates': 0,
            'community_news': 0,
            'new_items_alerts': 0,
            'exchange_notifications': 0,
            'request_updates': 0,
        }

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(post_save, sender=Exchange)
@receiver(post_delete, sender=Exchange)
def update_user_statistics(sender, instance, **kwargs):
    
    if not instance or not hasattr(instance, 'donor') or not hasattr(instance, 'requester'):
        return
        
    
    if instance.status == 'completed':
        try:
            
            if instance.donor.is_active and hasattr(instance.donor, 'profile'):
                donor_profile = instance.donor.profile
                donor_profile.items_donated = Exchange.objects.filter(
                    donor=instance.donor, 
                    status='completed'
                ).count()
                donor_profile.save()
        except Exception as e:
            print(f"Error updating donor stats: {e}")
        
        try:
            # Update requester's items_received count
            if instance.requester.is_active and hasattr(instance.requester, 'profile'):
                requester_profile = instance.requester.profile
                requester_profile.items_received = Exchange.objects.filter(
                    requester=instance.requester, 
                    status='completed'
                ).count()
                requester_profile.exchanges_completed = requester_profile.items_received
                requester_profile.save()
        except Exception as e:
            print(f"Error updating requester stats: {e}")


@receiver(post_save, sender=ClothingItem)
@receiver(post_delete, sender=ClothingItem)
def update_community_impact(sender, instance, **kwargs):
    try:
        # Update community impact statistics
        User = get_user_model()
        impact, created = CommunityImpact.objects.get_or_create(pk=1)
        impact.total_items_donated = ClothingItem.objects.filter(is_active=True).count()
        impact.total_items_exchanged = Exchange.objects.filter(status='completed').count()
        impact.total_community_members = User.objects.filter(is_active=True).count()
        
        # Calculate waste prevented (assuming 0.5kg per clothing item saved from landfill)
        impact.total_waste_prevented = impact.total_items_exchanged * 0.5
        impact.save()
    except Exception as e:
        print(f"Error updating community impact: {e}")


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def link_newsletter_subscriber(sender, instance, created, **kwargs):
    """
    When a user registers, check if they have an existing newsletter subscription
    and link it to their user account
    """
    if created and instance.is_active:
        try:
            # Use get() with exception handling for single subscription
            subscriber = NewsletterSubscriber.objects.get(
                email=instance.email, 
                user__isnull=True
            )
            subscriber.user = instance
            subscriber.save()
            print(f"Linked existing newsletter subscription to user: {instance.email}")
        except NewsletterSubscriber.DoesNotExist:
            # No existing subscription found - create one automatically with ALL fields
            try:
                NewsletterSubscriber.objects.create(
                    email=instance.email,
                    user=instance,
                    is_active=True,
                    receive_donation_updates=True,
                    receive_community_news=True,
                    receive_new_items_alerts=True,
                    receive_exchange_notifications=True,
                    receive_request_updates=True  # ADDED THIS LINE
                )
                print(f"Created automatic newsletter subscription for: {instance.email}")
            except Exception as e:
                print(f"Failed to create newsletter subscription: {e}")
        except NewsletterSubscriber.MultipleObjectsReturned:
            # Handle multiple subscriptions (shouldn't happen due to unique email)
            subscribers = NewsletterSubscriber.objects.filter(
                email=instance.email, 
                user__isnull=True
            )
            # Link the first one and deactivate others
            if subscribers.exists():
                primary = subscribers.first()
                primary.user = instance
                primary.save()
                subscribers.exclude(pk=primary.pk).update(is_active=False)
                print(f"Multiple subscriptions found for {instance.email}, linked first and deactivated others")
