from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django import forms
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from .models import (
    Category, Size, Condition, Gender, ClothingItem, ItemImage,
    ClothingRequest, Exchange, UserProfile, Badge, UserBadge,
    CommunityImpact, Notification, NewsletterSubscriber  # ADDED NewsletterSubscriber
)

class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = "__all__"  # ✅ This is correct

        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAdminForm
    list_display = ('name', 'icon', 'image_preview', 'created_at', 'item_count')
    list_filter = ('created_at',)
    search_fields = ('name',)
    readonly_fields = ('created_at', 'image_preview', 'item_count')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'icon', 'description')
        }),
        ('Category Image', {
            'fields': ('image', 'image_preview')
        }),
        ('Statistics', {
            'fields': ('item_count', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items Count'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 8px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image Preview'

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Gender)
class GenderAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class ItemImageInline(admin.TabularInline):
    model = ItemImage
    extra = 3
    readonly_fields = ('uploaded_at', 'image_preview')
    fields = ('image', 'image_preview', 'alt_text', 'is_primary', 'uploaded_at')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Preview'

class ClothingItemAdminForm(forms.ModelForm):
    class Meta:
        model = ClothingItem
        fields = '__all__'  # ✅ FIXED: Changed from '_all_' to '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'tags': forms.TextInput(attrs={'placeholder': 'jacket, denim, casual'}),
        }

@admin.register(ClothingItem)
class ClothingItemAdmin(admin.ModelAdmin):
    form = ClothingItemAdminForm
    list_display = ('title', 'donor', 'category', 'condition', 'mode', 'status', 'is_active', 'featured', 'created_at', 'image_count', 'image_preview')
    list_filter = ('category', 'condition', 'mode', 'status', 'is_active', 'featured', 'created_at', 'gender')
    search_fields = ('title', 'description', 'donor_username', 'donor_email', 'tags')
    readonly_fields = ('created_at', 'updated_at', 'expiry_date', 'image_count', 'image_preview')
    list_editable = ('status', 'is_active', 'featured')
    inlines = [ItemImageInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'donor', 'tags')
        }),
        ('Item Details', {
            'fields': ('category', 'size', 'condition', 'gender', 'mode', 'location')
        }),
        ('Status & Availability', {
            'fields': ('status', 'is_active', 'featured')
        }),
        ('Images', {
            'fields': ('image_preview', 'image_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'expiry_date'),
            'classes': ('collapse',)
        })
    )
    
    def image_count(self, obj):
        return obj.image_count
    image_count.short_description = 'Images'
    
    def image_preview(self, obj):
        primary_image = obj.primary_image
        if primary_image and primary_image.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />', primary_image.image.url)
        return "No Image"
    image_preview.short_description = 'Primary Image'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('donor', 'category', 'condition', 'size', 'gender')

class ClothingRequestAdminForm(forms.ModelForm):
    class Meta:
        model = ClothingRequest
        fields = '__all__'  # ✅ FIXED: Changed from '_all_' to '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

@admin.register(ClothingRequest)
class ClothingRequestAdmin(admin.ModelAdmin):
    form = ClothingRequestAdminForm
    list_display = ('requester', 'category', 'urgency', 'status', 'created_at', 'is_expired')
    list_filter = ('category', 'urgency', 'status', 'created_at', 'gender')
    search_fields = ('description', 'requester_username', 'requester_email')
    readonly_fields = ('created_at', 'updated_at', 'expiry_date', 'is_expired')
    list_editable = ('status', 'urgency')
    fieldsets = (
        ('Requester Information', {
            'fields': ('requester',)
        }),
        ('Request Details', {
            'fields': ('category', 'size', 'gender', 'description', 'urgency')
        }),
        ('Status & Fulfillment', {
            'fields': ('status', 'fulfilled_by', 'fulfilled_with_item', 'fulfilled_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'expiry_date', 'is_expired'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('requester', 'category', 'size', 'gender', 'fulfilled_by', 'fulfilled_with_item')

@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('item', 'requester', 'donor', 'status', 'created_at', 'scheduled_date', 'completed_at')
    list_filter = ('status', 'created_at', 'scheduled_date')
    search_fields = ('item_title', 'requesterusername', 'donor_username', 'message')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('status',)
    fieldsets = (
        ('Exchange Participants', {
            'fields': ('item', 'requester', 'donor')
        }),
        ('Exchange Details', {
            'fields': ('status', 'message', 'exchange_location', 'exchange_notes')
        }),
        ('Scheduling', {
            'fields': ('scheduled_date', 'completed_at')
        }),
        ('Ratings & Feedback', {
            'fields': ('donor_rating', 'requester_rating', 'donor_feedback', 'requester_feedback'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('item', 'requester', 'donor')

class UserProfileAdminForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = '__all__'  # ✅ FIXED: Changed from '_all_' to '__all__'
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ('user', 'full_name', 'location', 'affiliation', 'items_donated', 'items_received', 'exchanges_completed', 'avatar_preview', 'is_online')
    list_filter = ('affiliation', 'created_at')
    search_fields = ('user_username', 'useremail', 'userfirst_name', 'user_last_name', 'location')
    readonly_fields = ('created_at', 'updated_at', 'user_info', 'avatar_preview', 'is_online')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_info', 'is_online')
        }),
        ('Personal Details', {
            'fields': ('phone', 'location', 'affiliation', 'bio')
        }),
        ('Statistics', {
            'fields': ('items_donated', 'items_received', 'exchanges_completed')
        }),
        ('Preferences', {
            'fields': ('email_notifications', 'community_updates'),
            'classes': ('collapse',)
        }),
        ('Avatar', {
            'fields': ('avatar', 'avatar_preview')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def user_info(self, obj):
        return f"Email: {obj.user.email} | Joined: {obj.user.date_joined.strftime('%Y-%m-%d')}"
    user_info.short_description = 'User Details'
    
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 50%;" />', obj.avatar.url)
        return format_html('<i class="fas fa-user-circle" style="font-size: 50px; color: #6c757d;"></i>')
    avatar_preview.short_description = 'Avatar Preview'
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Full Name'
    
    def is_online(self, obj):
        if obj.is_online:
            return format_html('<span style="color: #28a745;">● Online</span>')
        return format_html('<span style="color: #6c757d;">● Offline</span>')
    is_online.short_description = 'Status'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'criteria_donations', 'criteria_exchanges', 'criteria_community', 'user_count', 'color_display')
    list_filter = ('criteria_donations', 'criteria_exchanges')
    search_fields = ('name', 'description')
    
    def user_count(self, obj):
        return obj.userbadge_set.count()
    user_count.short_description = 'Users Earned'
    
    def color_display(self, obj):
        return format_html(
            '<div style="background-color: {}; width: 20px; height: 20px; border-radius: 50%; display: inline-block; margin-right: 8px;"></div> {}',
            obj.color, obj.color
        )
    color_display.short_description = 'Color'

@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'earned_at')
    list_filter = ('badge', 'earned_at')
    search_fields = ('user_username', 'badge_name')
    readonly_fields = ('earned_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'badge')

@admin.register(CommunityImpact)
class CommunityImpactAdmin(admin.ModelAdmin):
    list_display = ('total_items_donated', 'total_items_exchanged', 'total_waste_prevented', 'total_community_members', 'last_updated')
    readonly_fields = ('last_updated',)
    
    def has_add_permission(self, request):
        # Only allow one instance of CommunityImpact
        return not CommunityImpact.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at',)
    list_editable = ('is_read',)
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'type', 'title', 'message')
        }),
        ('Related Content', {
            'fields': ('related_item', 'related_request'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'related_item', 'related_request')

# NEW: Newsletter Subscriber Admin
class NewsletterSubscriberAdminForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = '__all__'
        widgets = {
            'unsubscribe_token': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    form = NewsletterSubscriberAdminForm
    list_display = ('email', 'user', 'is_active', 'subscribed_at', 'preferences_summary', 'can_receive_emails')
    list_filter = ('is_active', 'subscribed_at', 'receive_donation_updates', 'receive_community_news', 'receive_new_items_alerts')
    search_fields = ('email', 'user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('subscribed_at', 'unsubscribe_token', 'preferences_summary', 'can_receive_emails')
    list_editable = ('is_active',)
    actions = ['activate_subscribers', 'deactivate_subscribers', 'send_test_newsletter']
    
    fieldsets = (
        ('Subscriber Information', {
            'fields': ('email', 'user', 'is_active')
        }),
        ('Email Preferences', {
            'fields': ('receive_donation_updates', 'receive_community_news', 'receive_new_items_alerts')
        }),
        ('Subscription Details', {
            'fields': ('subscribed_at', 'unsubscribe_token', 'preferences_summary', 'can_receive_emails'),
            'classes': ('collapse',)
        })
    )
    
    def preferences_summary(self, obj):
        preferences = []
        if obj.receive_donation_updates:
            preferences.append('Donation Updates')
        if obj.receive_community_news:
            preferences.append('Community News')
        if obj.receive_new_items_alerts:
            preferences.append('New Items')
        
        if preferences:
            return ', '.join(preferences)
        return 'No Preferences'
    preferences_summary.short_description = 'Email Preferences'
    
    def can_receive_emails(self, obj):
        if obj.can_receive_emails:
            return format_html('<span style="color: #28a745;">✓ Can Receive</span>')
        return format_html('<span style="color: #dc3545;">✗ Cannot Receive</span>')
    can_receive_emails.short_description = 'Email Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    # Custom Admin Actions
    def activate_subscribers(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} subscribers activated successfully.')
    activate_subscribers.short_description = "Activate selected subscribers"
    
    def deactivate_subscribers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} subscribers deactivated successfully.')
    deactivate_subscribers.short_description = "Deactivate selected subscribers"
    
    def send_test_newsletter(self, request, queryset):
        # This is a placeholder for sending test newsletters
        # You would integrate with your email service here
        count = queryset.count()
        self.message_user(request, f'Test newsletter would be sent to {count} subscribers. (Email integration required)')
    send_test_newsletter.short_description = "Send test newsletter to selected subscribers"

# NEW: Custom Admin View for Newsletter Statistics
class NewsletterStatsAdmin(admin.AdminSite):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('newsletter-stats/', self.admin_view(self.newsletter_stats_view), name='newsletter-stats'),
        ]
        return custom_urls + urls
    
    def newsletter_stats_view(self, request):
        from .models import get_newsletter_stats
        
        stats = get_newsletter_stats()
        context = {
            **self.each_context(request),
            'title': 'Newsletter Statistics',
            'stats': stats,
            'subscribers': NewsletterSubscriber.objects.filter(is_active=True).order_by('-subscribed_at')[:10],
        }
        return render(request, 'admin/newsletter_stats.html', context)

# Add newsletter stats to admin index if needed
def newsletter_stats_link(request):
    return {
        'newsletter_stats_url': '/admin/newsletter-stats/',
    }

# Custom admin site header and title
admin.site.site_header = 'ClothShare Administration'
admin.site.site_title = 'ClothShare Admin'
admin.site.index_title = 'Welcome to ClothShare Administration'

# Optional: If you want to add newsletter stats to the main admin index
# You can customize the admin index template to include this link