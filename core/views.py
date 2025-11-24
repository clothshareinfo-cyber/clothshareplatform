from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
import requests
from django.utils.crypto import get_random_string
from django.contrib.auth import login, get_user_model, logout
from django.contrib.auth.models import User
from django.db import IntegrityError

from .models import (
    Category, Size, Condition, Gender, ClothingItem, ItemImage,
    ClothingRequest, Exchange, UserProfile, Badge, UserBadge,
    CommunityImpact, Notification, NewsletterSubscriber, get_community_stats, get_newsletter_stats
)
from .forms import (
    ClothingItemForm, ItemImageFormSet, ClothingRequestForm,
    UserProfileForm, ExchangeForm, NewsletterSubscriptionForm
)

# Notification Service for Gmail Emails
from .services.notification_service import NotificationService



def index(request):
    """Home page view with featured items and community stats"""
    featured_items = ClothingItem.objects.filter(
        featured=True, 
        is_active=True, 
        status='available'
    )[:12]
    
    recent_items = ClothingItem.objects.filter(
        is_active=True, 
        status='available'
    ).order_by('-created_at')[:12]
    
    impact_stats = get_community_stats()
    
    categories = Category.objects.annotate(
        item_count=Count('items', filter=Q(items__is_active=True, items__status='available'))
    )
    
    user_donation_count = 0
    if request.user.is_authenticated:
        user_donation_count = ClothingItem.objects.filter(
            donor=request.user,
            is_active=True,
            mode='donation'
        ).count()
    
    context = {
        'featured_items': featured_items,
        'recent_items': recent_items,
        'impact_stats': impact_stats,
        'categories': categories,
        'user_donation_count': user_donation_count,
        'active_nav': 'home',
    }
    return render(request, 'core/index.html', context)


def browse_items(request):
    """Browse all available items with filtering and search"""
    items = ClothingItem.objects.filter(is_active=True, status='available')
    
    search_query = request.GET.get('search', '')
    if search_query:
        items = items.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(tags__icontains=search_query)
        )
    
    category_filter = request.GET.get('category', '')
    if category_filter:
        items = items.filter(category__name=category_filter)
    
    size_filter = request.GET.get('size', '')
    if size_filter:
        items = items.filter(size__name=size_filter)
    
    condition_filter = request.GET.get('condition', '')
    if condition_filter:
        items = items.filter(condition__name=condition_filter)
    
    gender_filter = request.GET.get('gender', '')
    if gender_filter:
        items = items.filter(gender__name=gender_filter)
    
    mode_filter = request.GET.get('mode', '')
    if mode_filter:
        items = items.filter(mode=mode_filter)
    
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by in ['title', 'created_at', '-created_at']:
        items = items.order_by(sort_by)
    
    paginator = Paginator(items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    sizes = Size.objects.all()
    conditions = Condition.objects.all()
    genders = Gender.objects.all()
    
    context = {
        'page_obj': page_obj,
        'items': page_obj,
        'categories': categories,
        'sizes': sizes,
        'conditions': conditions,
        'genders': genders,
        'search_query': search_query,
        'active_filters': {
            'category': category_filter,
            'size': size_filter,
            'condition': condition_filter,
            'gender': gender_filter,
            'mode': mode_filter,
            'sort': sort_by,
        },
        'active_nav': 'catalog',
    }
    return render(request, 'core/browse.html', context)


def item_detail(request, item_id):
    """Detailed view for a single clothing item"""
    item = get_object_or_404(ClothingItem, id=item_id, is_active=True)
    images = item.images.all()
    related_items = ClothingItem.objects.filter(
        category=item.category,
        is_active=True,
        status='available'
    ).exclude(id=item.id)[:4]
    
    user_has_pending_exchange = False
    if request.user.is_authenticated and request.user != item.donor:
        user_has_pending_exchange = Exchange.objects.filter(
            item=item,
            requester=request.user,
            status='pending'
        ).exists()
    
    context = {
        'item': item,
        'images': images,
        'related_items': related_items,
        'user_has_pending_exchange': user_has_pending_exchange,
        'active_nav': 'catalog',
    }
    return render(request, 'core/item_detail.html', context)


@login_required(login_url='/auth/sign-in/')
def donate_item(request):
    """View for donating new clothing items - requires login"""
    if request.method == 'POST':
        form = ClothingItemForm(request.POST)
        formset = ItemImageFormSet(request.POST, request.FILES, queryset=ItemImage.objects.none())
        
        if form.is_valid() and formset.is_valid():
            try:
                # Save the main item
                item = form.save(commit=False)
                item.donor = request.user
                item.mode = 'donation'
                item.save()
                
                # Save the images via formset
                formset.instance = item
                formset.save()
                
                # ✅ ADMIN + NEWSLETTER SUBSCRIBERS (public activity)
                NotificationService.notify_new_item_posted(item)  # Admin only
                NotificationService.send_new_item_newsletter(item)  # Newsletter subscribers
                
                messages.success(request, 'Your item has been listed successfully!')
                return redirect('core:item_detail', item_id=item.id)
                
            except Exception as e:
                messages.error(request, f'Error creating donation: {str(e)}')
        else:
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ClothingItemForm()
        formset = ItemImageFormSet(queryset=ItemImage.objects.none())
    
    context = {
        'form': form,
        'formset': formset,
        'categories': Category.objects.all(),
        'sizes': Size.objects.all(),
        'conditions': Condition.objects.all(),
        'genders': Gender.objects.all(),
        'active_nav': 'donate',
    }
    return render(request, 'core/donate.html', context)


@login_required
def edit_item(request, item_id):
    """Edit an existing clothing item"""
    item = get_object_or_404(ClothingItem, id=item_id, donor=request.user)
    
    if request.method == 'POST':
        form = ClothingItemForm(request.POST, instance=item)
        
        if form.is_valid():
            try:
                # Track changes for notification
                original_item = ClothingItem.objects.get(id=item_id)
                changes = {}
                
                # Check for changes
                for field in ['title', 'description', 'category', 'size', 'condition']:
                    original_value = getattr(original_item, field)
                    new_value = getattr(form.instance, field)
                    if original_value != new_value:
                        changes[field] = f"{original_value} → {new_value}"
                
                # Save the main form
                form.save()
                
                # Handle image deletions
                delete_images = request.POST.getlist('delete_images')
                if delete_images:
                    ItemImage.objects.filter(id__in=delete_images).delete()
                
                # Handle new image uploads
                new_images = request.FILES.getlist('new_images')
                for i, image in enumerate(new_images):
                    is_primary = (i == 0 and not item.images.exists())
                    ItemImage.objects.create(
                        item=item, 
                        image=image,
                        is_primary=is_primary
                    )
                
                # ✅ ADMIN ONLY (private action)
                if changes:
                    NotificationService.notify_user_edited_item(item, request.user, changes)
                
                messages.success(request, 'Item updated successfully!')
                return redirect('core:item_detail', item_id=item.id)
                
            except Exception as e:
                messages.error(request, f'Error updating item: {str(e)}')
        else:
            print("Form errors:", form.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ClothingItemForm(instance=item)
    
    context = {
        'form': form,
        'item': item,
        'active_nav': 'profile',
    }
    return render(request, 'core/edit_item.html', context)


@login_required
def delete_item(request, item_id):
    """Delete a clothing item"""
    item = get_object_or_404(ClothingItem, id=item_id, donor=request.user)
    
    if request.method == 'POST':
        item.is_active = False
        item.save()
        
        # ✅ ADMIN ONLY (private action)
        NotificationService.notify_user_removed_item(item, request.user)
        
        messages.success(request, 'Item deleted successfully!')
        return redirect('core:profile')
    
    context = {
        'item': item,
        'active_nav': 'profile',
    }
    return render(request, 'core/delete_item.html', context)


@login_required(login_url='/auth/sign-in/')
def request_clothing(request):
    """View for requesting clothing items - requires login"""
    if request.method == 'POST':
        form = ClothingRequestForm(request.POST)
        if form.is_valid():
            clothing_request = form.save(commit=False)
            clothing_request.requester = request.user
            clothing_request.save()
            
            # ✅ ADMIN + NEWSLETTER SUBSCRIBERS (public activity)
            NotificationService.notify_new_clothing_request(clothing_request)  # Admin only
            NotificationService.send_request_newsletter(clothing_request)  # Newsletter subscribers
            
            messages.success(request, 'Your request has been submitted successfully!')
            return redirect('core:view_requests')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ClothingRequestForm()
    
    context = {
        'form': form,
        'active_nav': 'request',
    }
    return render(request, 'core/request.html', context)


@login_required
def view_requests(request):
    """View all clothing requests"""
    requests = ClothingRequest.objects.filter(status='open').order_by('-urgency', '-created_at')
    
    category_filter = request.GET.get('category', '')
    if category_filter:
        requests = requests.filter(category__name=category_filter)
    
    context = {
        'requests': requests,
        'categories': Category.objects.all(),
        'active_nav': 'request',
    }
    return render(request, 'core/requests.html', context)


@login_required
def my_requests(request):
    """View user's own clothing requests"""
    requests = ClothingRequest.objects.filter(requester=request.user).order_by('-created_at')
    
    context = {
        'requests': requests,
        'active_nav': 'profile',
    }
    return render(request, 'core/my_requests.html', context)


@login_required
def delete_request(request, request_id):
    """Delete a clothing request"""
    clothing_request = get_object_or_404(ClothingRequest, id=request_id, requester=request.user)
    
    if request.method == 'POST':
        clothing_request.status = 'cancelled'
        clothing_request.save()
        
        messages.success(request, 'Request deleted successfully!')
        return redirect('core:my_requests')
    
    context = {
        'clothing_request': clothing_request,
        'active_nav': 'profile',
    }
    return render(request, 'core/delete_request.html', context)


def help_page(request):
    """Help and FAQ page"""
    faqs = [
        {
            'question': 'How do I donate clothes?',
            'answer': 'Click on the "Donate" button in the navigation, fill out the item details, upload photos, and submit. Your item will be listed for others to see.'
        },
        {
            'question': 'How do I request clothes?',
            'answer': 'Click on "Request" in the navigation, describe what you need, and submit your request. Donors can then offer items that match your needs.'
        },
        {
            'question': 'Is there any cost involved?',
            'answer': 'No! ClothShare is completely free. We believe in building sustainable communities through sharing.'
        },
        {
            'question': 'How do exchanges work?',
            'answer': 'When you find an item you like, click "Request Exchange". The donor will review your request and can confirm or decline. Once confirmed, you can arrange pickup.'
        },
    ]
    
    context = {
        'faqs': faqs,
        'active_nav': 'help',
    }
    return render(request, 'core/help_standalone.html', context)


@login_required
def profile(request):
    """User profile dashboard"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)
    
    user_items = ClothingItem.objects.filter(donor=request.user, is_active=True)
    user_requests = ClothingRequest.objects.filter(requester=request.user)
    user_exchanges = Exchange.objects.filter(
        Q(requester=request.user) | Q(donor=request.user)
    ).order_by('-created_at')[:5]
    user_badges = UserBadge.objects.filter(user=request.user)
    
    # Check newsletter subscription status
    newsletter_subscribed = NewsletterSubscriber.objects.filter(
        user=request.user, 
        is_active=True
    ).exists()
    
    context = {
        'profile': user_profile,
        'user_items': user_items,
        'user_requests': user_requests,
        'user_exchanges': user_exchanges,
        'user_badges': user_badges,
        'newsletter_subscribed': newsletter_subscribed,
        'active_nav': 'profile',
    }
    return render(request, 'core/profile.html', context)

@login_required
def edit_profile(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    
    # Don't auto-create newsletter subscription
    newsletter_subscription = None
    try:
        newsletter_subscription = NewsletterSubscriber.objects.get(user=request.user)
    except NewsletterSubscriber.DoesNotExist:
        try:
            # Try to get by email, but don't auto-create
            newsletter_subscription = NewsletterSubscriber.objects.get(email=request.user.email)
            # If found by email, update the user field but don't auto-activate
            newsletter_subscription.user = request.user
            newsletter_subscription.save()
        except NewsletterSubscriber.DoesNotExist:
            # Don't create subscription - user must manually subscribe
            newsletter_subscription = None
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'personal_info':
            # Update User model fields
            user = request.user
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.save()
            
            # Update UserProfile model fields
            profile.phone = request.POST.get('phone', '')
            profile.location = request.POST.get('location', '')
            profile.affiliation = request.POST.get('affiliation', '')
            profile.bio = request.POST.get('bio', '')
            
            # Handle avatar upload
            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
            
            # Handle avatar removal
            if request.POST.get('clear_avatar'):
                if profile.avatar:
                    profile.avatar.delete(save=False)
                profile.avatar = None
            
            profile.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('core:edit_profile')
            
        elif form_type == 'preferences':
            # Update notification preferences
            profile.email_notifications = 'email_notifications' in request.POST
            profile.community_updates = 'community_updates' in request.POST
            profile.save()
            
            messages.success(request, 'Preferences updated successfully!')
            return redirect('core:edit_profile')
            
        elif form_type == 'newsletter':
            # FIXED: Get the action from the submitted button
            action = request.POST.get('action')
            print(f"🔍 Newsletter action received: {action}")  # Debug print
            
            if action == 'subscribe_newsletter':
                print("🔍 Processing newsletter subscription...")
                # ✅ USER EXPLICITLY CLICKS SUBSCRIBE
                if not newsletter_subscription:
                    # Create new subscription with user's explicit consent
                    newsletter_subscription = NewsletterSubscriber.objects.create(
                        user=request.user,
                        email=request.user.email,
                        is_active=True,
                        receive_donation_updates=True,
                        receive_community_news=True,
                        receive_new_items_alerts=True,
                        receive_exchange_notifications=True,
                        receive_request_updates=True
                    )
                    print(f"✅ Created new subscription for: {request.user.email}")
                else:
                    # Reactivate existing subscription
                    newsletter_subscription.is_active = True
                    newsletter_subscription.save()
                    print(f"✅ Reactivated subscription for: {request.user.email}")
                
                # ✅ Send welcome email to subscriber
                try:
                    NotificationService.send_newsletter_welcome_email(newsletter_subscription)
                    print(f"✅ Welcome email sent to {request.user.email}")
                except Exception as e:
                    print(f"❌ Failed to send welcome email: {e}")
                
                # ✅ Notify admin about new subscription
                try:
                    NotificationService.notify_new_newsletter_subscriber(newsletter_subscription)
                    print(f"✅ Admin notified about new subscriber: {request.user.email}")
                except Exception as e:
                    print(f"❌ Failed to notify admin about new subscriber: {e}")
                
                messages.success(request, 'Successfully subscribed to newsletter! Welcome email sent.')
                
            elif action == 'unsubscribe_newsletter':
                print("🔍 Processing newsletter unsubscribe...")
                # Unsubscribe from newsletter
                if newsletter_subscription:
                    email = newsletter_subscription.email
                    newsletter_subscription.is_active = False
                    newsletter_subscription.receive_donation_updates = False
                    newsletter_subscription.receive_community_news = False
                    newsletter_subscription.receive_new_items_alerts = False
                    newsletter_subscription.receive_exchange_notifications = False
                    newsletter_subscription.receive_request_updates = False
                    newsletter_subscription.save()
                    
                    print(f"✅ Unsubscribed: {email}")
                    
                    # ✅ NOTIFY ADMIN ABOUT UNSUBSCRIBE
                    try:
                        NotificationService.notify_newsletter_unsubscribe_admin(newsletter_subscription)
                        print(f"✅ Admin notified about unsubscribe: {email}")
                    except Exception as e:
                        print(f"❌ Failed to notify admin about unsubscribe: {e}")
                    
                    # ✅ SEND CONFIRMATION EMAIL TO USER
                    try:
                        NotificationService.send_unsubscribe_confirmation_email(newsletter_subscription)
                        print(f"✅ Unsubscribe confirmation sent to: {email}")
                    except Exception as e:
                        print(f"❌ Failed to send unsubscribe confirmation to {email}: {e}")
                    
                    messages.success(request, 'You have been unsubscribed from all newsletter emails. A confirmation email has been sent to you.')
                else:
                    messages.info(request, 'You are not currently subscribed.')
                    print("ℹ️ No subscription found to unsubscribe")
                
            elif action == 'update_newsletter':
                print("🔍 Processing newsletter preference update...")
                # Update newsletter preferences - only if already subscribed
                if newsletter_subscription and newsletter_subscription.is_active:
                    newsletter_subscription.receive_donation_updates = 'receive_donation_updates' in request.POST
                    newsletter_subscription.receive_community_news = 'receive_community_news' in request.POST
                    newsletter_subscription.receive_new_items_alerts = 'receive_new_items_alerts' in request.POST
                    newsletter_subscription.receive_exchange_notifications = 'receive_exchange_notifications' in request.POST
                    newsletter_subscription.receive_request_updates = 'receive_request_updates' in request.POST
                    newsletter_subscription.save()
                    
                    print(f"✅ Updated preferences for: {request.user.email}")
                    print(f"   Donation updates: {newsletter_subscription.receive_donation_updates}")
                    print(f"   Community news: {newsletter_subscription.receive_community_news}")
                    print(f"   New items alerts: {newsletter_subscription.receive_new_items_alerts}")
                    print(f"   Exchange notifications: {newsletter_subscription.receive_exchange_notifications}")
                    print(f"   Request updates: {newsletter_subscription.receive_request_updates}")
                    
                    messages.success(request, 'Your newsletter preferences have been updated!')
                else:
                    messages.error(request, 'Please subscribe to the newsletter first to update preferences.')
                    print("❌ Cannot update preferences - no active subscription")
            
            return redirect('core:edit_profile')
    
    context = {
        'profile': profile,
        # Only pass active subscription
        'newsletter_subscription': newsletter_subscription if newsletter_subscription and newsletter_subscription.is_active else None,
    }
    
    return render(request, 'core/edit_profile.html', context)

@login_required
def delete_account(request):
    """Database-safe account deletion that handles all constraints"""
    if request.method == 'POST':
        password = request.POST.get('password', '')
        
        if not request.user.check_password(password):
            messages.error(request, 'Incorrect password.')
            return redirect('core:delete_account_confirm')
        
        try:
            user = request.user
            user_id = user.id
            username = user.username
            user_email = user.email
            
            print(f"🔧 DATABASE DELETION STARTED: {username} (ID: {user_id})")
            
            # ✅ STEP 1: Handle all related objects in correct order
            from django.db import transaction
            
            try:
                with transaction.atomic():
                    # 1A: Handle exchanges where user is requester
                    try:
                        Exchange.objects.filter(requester=user).update(
                            status='cancelled',
                            cancelled_at=timezone.now(),
                            cancellation_reason='user_deletion'
                        )
                        print("✅ User's exchange requests cancelled")
                    except Exception as e:
                        print(f"⚠️ Exchange requester cleanup: {e}")
                    
                    # 1B: Handle exchanges where user is donor  
                    try:
                        Exchange.objects.filter(donor=user).update(
                            status='cancelled',
                            cancelled_at=timezone.now(),
                            cancellation_reason='user_deletion'
                        )
                        print("✅ User's donor exchanges cancelled")
                    except Exception as e:
                        print(f"⚠️ Exchange donor cleanup: {e}")
                    
                    # 1C: Deactivate clothing items (soft delete)
                    try:
                        ClothingItem.objects.filter(donor=user).update(
                            is_active=False, 
                            status='taken',
                            deactivated_at=timezone.now(),
                            deactivation_reason='user_deletion'
                        )
                        print("✅ User's clothing items deactivated")
                    except Exception as e:
                        print(f"⚠️ Clothing items cleanup: {e}")
                    
                    # 1D: Cancel clothing requests
                    try:
                        ClothingRequest.objects.filter(requester=user).update(
                            status='cancelled',
                            cancelled_at=timezone.now(),
                            cancellation_reason='user_deletion'
                        )
                        print("✅ User's clothing requests cancelled")
                    except Exception as e:
                        print(f"⚠️ Clothing requests cleanup: {e}")
                    
                    # 1E: Delete notifications
                    try:
                        Notification.objects.filter(user=user).delete()
                        print("✅ User's notifications deleted")
                    except Exception as e:
                        print(f"⚠️ Notifications cleanup: {e}")
                    
                    # 1F: Delete user badges
                    try:
                        UserBadge.objects.filter(user=user).delete()
                        print("✅ User's badges deleted")
                    except Exception as e:
                        print(f"⚠️ Badges cleanup: {e}")
            except Exception as e:
                print(f"⚠️ Transaction cleanup failed: {e}")
                raise e
            
            # ✅ STEP 2: Handle newsletter subscription
            try:
                NewsletterSubscriber.objects.filter(
                    Q(user=user) | Q(email=user_email)
                ).delete()
                print("✅ Newsletter subscription deleted")
            except Exception as e:
                print(f"⚠️ Newsletter cleanup: {e}")
            
            # ✅ STEP 3: Logout user BEFORE deletion
            logout(request)
            print("✅ User logged out")
            
            # ✅ STEP 4: Get fresh user instance and delete
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                fresh_user = User.objects.get(id=user_id)
                
                # Delete user profile first (if exists)
                try:
                    UserProfile.objects.filter(user=fresh_user).delete()
                    print("✅ User profile deleted")
                except Exception as e:
                    print(f"⚠️ Profile deletion: {e}")
                
                # Finally delete the user
                fresh_user.delete()
                print("🎉 USER ACCOUNT DELETED SUCCESSFULLY!")
                
            except User.DoesNotExist:
                print("ℹ️ User already deleted")
            
            # ✅ STEP 5: Send admin notification
            try:
                NotificationService.notify_account_deletion(user_email, username)
                print("✅ Admin notification sent")
            except Exception as e:
                print(f"⚠️ Notification failed: {e}")
            
            messages.success(request, 'Your account has been permanently deleted successfully!')
            return redirect('core:index')
            
        except Exception as e:
            print(f"❌ CRITICAL ERROR: {str(e)}")
            import traceback
            print(f"❌ TRACEBACK: {traceback.format_exc()}")
            messages.error(request, 'We encountered a system error. Please contact support.')
            return redirect('core:profile')
    
    return redirect('core:delete_account_confirm')

@login_required
def delete_account_confirm(request):
    """Show account deletion confirmation page"""
    user_items_count = ClothingItem.objects.filter(donor=request.user, is_active=True).count()
    user_requests_count = ClothingRequest.objects.filter(requester=request.user).count()
    user_exchanges_count = Exchange.objects.filter(
        Q(requester=request.user) | Q(donor=request.user)
    ).count()
    
    context = {
        'user_items_count': user_items_count,
        'user_requests_count': user_requests_count,
        'user_exchanges_count': user_exchanges_count,
        'active_nav': 'profile',
    }
    return render(request, 'core/delete_account_confirm.html', context)


def calculate_donor_statistics(donor):
    """Calculate comprehensive donor statistics"""
    items_listed = ClothingItem.objects.filter(donor=donor, is_active=True).count()
    successful_exchanges = Exchange.objects.filter(donor=donor, status='completed').count()
    
    total_requests = Exchange.objects.filter(donor=donor).count()
    if total_requests > 0:
        responded_requests = Exchange.objects.filter(donor=donor).exclude(status='pending').count()
        response_rate = round((responded_requests / total_requests) * 100)
    else:
        response_rate = 100
    
    rating_data = Exchange.objects.filter(
        donor=donor,
        donor_rating__isnull=False,
        status='completed'
    ).aggregate(
        avg_rating=Avg('donor_rating'),
        total_reviews=Count('donor_rating')
    )
    
    avg_rating = round(rating_data['avg_rating'] or 0, 1)
    total_reviews = rating_data['total_reviews'] or 0
    
    trust_score = 50
    if successful_exchanges > 0:
        trust_score += min(successful_exchanges * 2, 20)
    if avg_rating >= 4.0:
        trust_score += 15
    elif avg_rating >= 3.0:
        trust_score += 10
    elif avg_rating > 0:
        trust_score += 5
    if response_rate >= 90:
        trust_score += 10
    elif response_rate >= 75:
        trust_score += 5
    
    trust_score = min(trust_score, 100)
    
    is_online = donor.last_login and (
        timezone.now() - donor.last_login
    ).total_seconds() < 900
    
    return {
        'items_listed': items_listed,
        'successful_exchanges': successful_exchanges,
        'response_rate': response_rate,
        'avg_rating': avg_rating,
        'total_reviews': total_reviews,
        'trust_score': trust_score,
        'is_online': is_online,
        'member_since': donor.date_joined,
    }


@login_required
def initiate_exchange(request, item_id):
    """Initiate an exchange for an item"""
    item = get_object_or_404(ClothingItem, id=item_id, is_active=True, status='available')
    
    existing_exchange = Exchange.objects.filter(
        item=item,
        requester=request.user,
        status='pending'
    ).first()
    
    if existing_exchange:
        messages.info(request, 'You have already requested an exchange for this item.')
        return redirect('core:item_detail', item_id=item.id)
    
    donor_stats = calculate_donor_statistics(item.donor)
    
    if request.method == 'POST':
        form = ExchangeForm(request.POST)
        if form.is_valid():
            exchange = form.save(commit=False)
            exchange.item = item
            exchange.requester = request.user
            exchange.donor = item.donor
            exchange.save()
            
            # Create in-app notification for donor
            Notification.objects.create(
                user=item.donor,
                type='exchange_request',
                title=f'New Exchange Request for {item.title}',
                message=f'{request.user.username} has requested to exchange for your item "{item.title}".',
                related_item=item
            )
            
            # ✅ ADMIN + ITEM OWNER ONLY (private exchange)
            NotificationService.notify_exchange_initiated(exchange)  # Admin only
            NotificationService.notify_exchange_request_received(exchange)  # Item owner only
            
            messages.success(request, 'Exchange request sent successfully!')
            return redirect('core:item_detail', item_id=item.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ExchangeForm()
    
    context = {
        'form': form,
        'item': item,
        'donor_stats': donor_stats,
        'active_nav': 'catalog',
    }
    return render(request, 'core/initiate_exchange.html', context)

@login_required
def cancel_exchange(request, item_id):
    """Cancel an exchange request"""
    item = get_object_or_404(ClothingItem, id=item_id)
    
    exchange = get_object_or_404(
        Exchange, 
        item=item, 
        requester=request.user, 
        status='pending'
    )
    
    if request.method == 'POST':
        exchange.status = 'cancelled'
        exchange.cancelled_at = timezone.now()
        exchange.save()
        
        # Create in-app notification for donor
        Notification.objects.create(
            user=item.donor,
            type='exchange_cancelled',
            title=f'Exchange Request Cancelled for {item.title}',
            message=f'{request.user.username} has cancelled their exchange request for "{item.title}".',
            related_item=item
        )
        
        # Fix the notification service call
        try:
            NotificationService.notify_exchange_cancelled_admin(exchange)
            NotificationService.notify_exchange_cancelled(exchange, request.user)  # Add cancelled_by parameter
        except Exception as e:
            print(f"Notification error: {e}")
        
        messages.success(request, 'Exchange request cancelled successfully.')
        return redirect('core:item_detail', item_id=item_id)
    
    return redirect('core:item_detail', item_id=item_id)

@login_required
def my_exchanges(request):
    """View user's exchanges"""
    requested_exchanges = Exchange.objects.filter(requester=request.user).order_by('-created_at')
    donated_exchanges = Exchange.objects.filter(donor=request.user).order_by('-created_at')
    
    context = {
        'requested_exchanges': requested_exchanges,
        'donated_exchanges': donated_exchanges,
        'active_nav': 'profile',
    }
    return render(request, 'core/my_exchanges.html', context)


@login_required
def manage_exchange(request, exchange_id):
    """Manage an exchange (confirm, complete, cancel)"""
    exchange = get_object_or_404(Exchange, id=exchange_id)
    
    if exchange.requester != request.user and exchange.donor != request.user:
        messages.error(request, 'You are not authorized to manage this exchange.')
        return redirect('core:my_exchanges')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm' and exchange.donor == request.user:
            exchange.status = 'confirmed'
            exchange.save()
            
            # Create in-app notification for requester
            Notification.objects.create(
                user=exchange.requester,
                type='exchange_request',
                title='Exchange Confirmed',
                message=f'Your exchange request for "{exchange.item.title}" has been confirmed.',
                related_item=exchange.item
            )
            
            # ✅ ADMIN + REQUESTER ONLY (private exchange)
            NotificationService.notify_exchange_confirmed(exchange)  # Admin only
            NotificationService.notify_exchange_request_accepted(exchange)  # Requester only
            
            messages.success(request, 'Exchange confirmed!')
            
        elif action == 'complete':
            if (exchange.requester == request.user and exchange.status == 'confirmed') or \
               (exchange.donor == request.user and exchange.status == 'confirmed'):
                exchange.status = 'completed'
                exchange.completed_at = timezone.now()
                exchange.item.status = 'taken'
                exchange.item.save()
                exchange.save()
                
                # ✅ BOTH PARTIES ONLY (private exchange completion)
                NotificationService.notify_exchange_completed(exchange)  # Both parties only
                
                messages.success(request, 'Exchange completed successfully!')
                
        elif action == 'cancel':
            exchange.status = 'cancelled'
            exchange.save()
            
            # ✅ ADMIN + BOTH PARTIES ONLY (private exchange cancellation)
            NotificationService.notify_exchange_cancelled_admin(exchange)  # Admin only
            NotificationService.notify_exchange_cancelled(exchange, request.user)  # Both parties only
            
            messages.success(request, 'Exchange cancelled.')
        
        return redirect('core:my_exchanges')
    
    context = {
        'exchange': exchange,
        'active_nav': 'profile',
    }
    return render(request, 'core/manage_exchange.html', context)


def community_impact(request):
    """Community impact statistics page"""
    impact_stats = get_community_stats()
    
    top_donors = UserProfile.objects.filter(
        user__donated_items__is_active=True
    ).annotate(
        donation_count=Count('user__donated_items')
    ).order_by('-donation_count')[:5]
    
    context = {
        'impact_stats': impact_stats,
        'top_donors': top_donors,
        'active_nav': 'impact',
    }
    return render(request, 'core/impact.html', context)


@login_required
def notifications(request):
    """User notifications"""
    user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    unread_notifications = user_notifications.filter(is_read=False)
    unread_notifications.update(is_read=True)
    
    context = {
        'notifications': user_notifications,
        'active_nav': 'profile',
    }
    return render(request, 'core/notifications.html', context)


# Google OAuth Views
def google_oauth(request):
    """Initiate Google OAuth flow with custom parameters"""
    state = get_random_string(32)
    request.session['oauth_state'] = state
    
    from django.conf import settings
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'response_type': 'code',
        'scope': 'openid email profile',
        'redirect_uri': request.build_absolute_uri('/auth/google/callback/'),
        'state': state,
        'access_type': 'offline',
        'prompt': 'select_account',
    }
    
    auth_url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    return redirect(auth_url)


def google_callback(request):
    """Handle Google OAuth callback and create/authenticate user - NO AUTO-SUBSCRIBE"""
    state = request.GET.get('state')
    if state != request.session.get('oauth_state'):
        messages.error(request, 'Invalid OAuth state. Please try again.')
        return redirect('userauths:sign-up')
    
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Authorization failed. No code received.')
        return redirect('userauths:sign-up')
    
    try:
        from django.conf import settings
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': request.build_absolute_uri('/auth/google/callback/'),
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        if 'error' in token_json:
            messages.error(request, f"Token exchange failed: {token_json['error']}")
            return redirect('userauths:sign-up')
        
        access_token = token_json['access_token']
        
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo = userinfo_response.json()
        
        if 'error' in userinfo:
            messages.error(request, f"Failed to get user info: {userinfo['error']}")
            return redirect('userauths:sign-up')
        
        google_id = userinfo['sub']
        email = userinfo['email']
        first_name = userinfo.get('given_name', '')
        last_name = userinfo.get('family_name', '')
        picture = userinfo.get('picture', '')
        
        user, created = get_or_create_google_user(
            google_id=google_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            picture=picture
        )
        
        login(request, user)
        
        request.session['google_picture'] = picture
        
        # ✅ CHANGED: Only send welcome email, NO auto-newsletter subscription
        if created:
            NotificationService.send_user_welcome_email(user)
            messages.success(request, f'Welcome {first_name}! Your account has been created successfully.')
            
            # ✅ OPTIONAL: Show newsletter opt-in suggestion (but don't auto-subscribe)
            messages.info(request, 'Want to stay updated? Subscribe to our newsletter in your profile settings!')
        else:
            messages.success(request, f'Welcome back {first_name}!')
        
        next_url = request.session.pop('next', None) or 'core:index'
        return redirect(next_url)
        
    except Exception as e:
        messages.error(request, f'Authentication failed: {str(e)}')
        return redirect('userauths:sign-up')


def get_or_create_google_user(google_id, email, first_name, last_name, picture):
    """Get existing user or create new one from Google data - NO AUTO-SUBSCRIPTION"""
    User = get_user_model()
    
    try:
        user = User.objects.get(google_id=google_id)
        created = False
    except User.DoesNotExist:
        try:
            user = User.objects.get(email=email)
            user.google_id = google_id
            user.save()
            created = False
        except User.DoesNotExist:
            username = generate_unique_username(email)
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                google_id=google_id,
                is_active=True,
            )
            
            try:
                profile = UserProfile.objects.get(user=user)
                if picture and not profile.avatar:
                    profile.avatar = picture
                    profile.save()
            except UserProfile.DoesNotExist:
                UserProfile.objects.create(
                    user=user,
                    avatar=picture if picture else ''
                )
            
            # ✅ CHANGED: Don't auto-create newsletter subscription
            # User must manually subscribe in profile settings
            
            created = True
    
    return user, created


def generate_unique_username(email):
    """Generate unique username from email"""
    base_username = email.split('@')[0]
    username = base_username
    counter = 1
    
    User = get_user_model()
    
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    return username


def google_auth_ajax(request):
    """AJAX endpoint to initiate Google OAuth (optional)"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'auth_url': request.build_absolute_uri('/auth/google/')
        })
    return redirect('userauths:sign-up')


def oauth_error(request):
    """Custom OAuth error page"""
    error = request.GET.get('error', 'Unknown error')
    error_description = request.GET.get('error_description', '')
    
    context = {
        'error': error,
        'error_description': error_description,
    }
    return render(request, 'userauths/oauth_error.html', context)

# Newsletter Views
@require_POST
@csrf_exempt
def subscribe_newsletter(request):
    """Handle newsletter subscription via AJAX - OPT-IN ONLY"""
    email = request.POST.get('email', '').strip().lower()
    
    if not email:
        return JsonResponse({
            'success': False,
            'message': 'Please enter an email address.'
        })
    
    if '@' not in email or '.' not in email:
        return JsonResponse({
            'success': False,
            'message': 'Please enter a valid email address.'
        })
    
    try:
        # Check if already subscribed
        existing_subscriber = NewsletterSubscriber.objects.filter(email=email, is_active=True).first()
        if existing_subscriber:
            return JsonResponse({
                'success': False,
                'message': 'This email is already subscribed to our newsletter.'
            })
        
        # Check for inactive subscription (don't auto-reactivate)
        inactive_subscriber = NewsletterSubscriber.objects.filter(email=email, is_active=False).first()
        if inactive_subscriber:
            return JsonResponse({
                'success': False,
                'message': 'This email was previously unsubscribed. Please visit your profile to resubscribe.'
            })
        
        # Create new subscription with default preferences
        subscriber = NewsletterSubscriber(
            email=email,
            is_active=True,
            receive_donation_updates=True,
            receive_community_news=True,
            receive_new_items_alerts=True
        )
        
        if request.user.is_authenticated:
            subscriber.user = request.user
        
        subscriber.save()
        
        # ✅ FIXED: Send welcome email to new subscriber FIRST
        try:
            NotificationService.send_newsletter_welcome_email(subscriber)
            print(f"✅ Welcome email sent to {email}")
        except Exception as e:
            print(f"❌ Failed to send welcome email to {email}: {e}")
        
        # ✅ FIXED: Then notify admin about new subscriber
        try:
            NotificationService.notify_new_newsletter_subscriber(subscriber)
            print(f"✅ Admin notified about new subscriber: {email}")
        except Exception as e:
            print(f"❌ Failed to notify admin about new subscriber {email}: {e}")
        
        return JsonResponse({
            'success': True,
            'message': 'Thank you for subscribing! Check your email for a welcome message with updates on new donations and community news.'
        })
        
    except IntegrityError as e:
        # Handle unique constraint violation
        if 'UNIQUE constraint failed' in str(e) and 'user_id' in str(e):
            return JsonResponse({
                'success': False,
                'message': 'You are already subscribed to our newsletter.'
            })
        return JsonResponse({
            'success': False,
            'message': 'Subscription error. Please try again.'
        })
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        print(f"❌ Newsletter subscription error for {email}: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again later.'
        })


def unsubscribe_newsletter(request, token=None):
    """Handle newsletter unsubscription with multiple methods"""
    # Handle token-based unsubscribe (from email links)
    if token:
        try:
            subscriber = NewsletterSubscriber.objects.get(unsubscribe_token=token, is_active=True)
            email = subscriber.email
            subscriber.is_active = False
            subscriber.save()
            
            # ✅ NOTIFY ADMIN ABOUT UNSUBSCRIBE
            try:
                NotificationService.notify_newsletter_unsubscribe_admin(subscriber)
            except Exception as e:
                print(f"❌ Failed to notify admin about unsubscribe: {e}")
            
            # ✅ SEND CONFIRMATION EMAIL TO USER
            try:
                NotificationService.send_unsubscribe_confirmation_email(subscriber)
            except Exception as e:
                print(f"❌ Failed to send unsubscribe confirmation to {email}: {e}")
            
            messages.success(request, f'You have been unsubscribed from our newsletter. We\'re sorry to see you go!')
            
        except NewsletterSubscriber.DoesNotExist:
            messages.error(request, 'Invalid unsubscribe link or you are already unsubscribed.')
        
        return redirect('core:index')
    
    # Handle email-based unsubscribe (from profile page)
    elif request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, 'Please provide an email address to unsubscribe.')
            return redirect('core:manage_newsletter_preferences')
        
        try:
            subscriber = NewsletterSubscriber.objects.get(email=email, is_active=True)
            subscriber.is_active = False
            subscriber.save()
            
            # ✅ NOTIFY ADMIN ABOUT UNSUBSCRIBE
            try:
                NotificationService.notify_newsletter_unsubscribe_admin(subscriber)
            except Exception as e:
                print(f"❌ Failed to notify admin about unsubscribe: {e}")
            
            # ✅ SEND CONFIRMATION EMAIL TO USER
            try:
                NotificationService.send_unsubscribe_confirmation_email(subscriber)
            except Exception as e:
                print(f"❌ Failed to send unsubscribe confirmation to {email}: {e}")
            
            messages.success(request, f'You have been unsubscribed from our newsletter. A confirmation email has been sent to {email}.')
            
        except NewsletterSubscriber.DoesNotExist:
            messages.error(request, 'No active subscription found for this email address.')
        
        return redirect('core:manage_newsletter_preferences')
    
    # Show unsubscribe form for GET requests
    else:
        context = {
            'active_nav': 'newsletter',
        }
        return render(request, 'core/unsubscribe_form.html', context)


@login_required
def manage_newsletter_preferences(request):
    """Allow users to MANUALLY manage their newsletter preferences"""
    # Don't auto-create subscription
    newsletter_subscription = None
    try:
        newsletter_subscription = NewsletterSubscriber.objects.get(user=request.user)
    except NewsletterSubscriber.DoesNotExist:
        try:
            newsletter_subscription = NewsletterSubscriber.objects.get(email=request.user.email)
            newsletter_subscription.user = request.user
            newsletter_subscription.save()
        except NewsletterSubscriber.DoesNotExist:
            # Don't create - user must manually subscribe
            pass

    if request.method == 'POST':
        if 'subscribe' in request.POST:
            # ✅ USER EXPLICITLY CLICKS SUBSCRIBE
            if not newsletter_subscription:
                # Create new subscription with explicit consent
                newsletter_subscription = NewsletterSubscriber.objects.create(
                    user=request.user,
                    email=request.user.email,
                    is_active=True,
                    receive_donation_updates=True,
                    receive_community_news=True,
                    receive_new_items_alerts=True
                )
            else:
                # Reactivate existing subscription
                newsletter_subscription.is_active = True
                newsletter_subscription.save()
            
            # ✅ FIXED: Send welcome email to subscriber
            try:
                NotificationService.send_newsletter_welcome_email(newsletter_subscription)
                print(f"✅ Welcome email sent to {request.user.email}")
            except Exception as e:
                print(f"❌ Failed to send welcome email: {e}")
            
            # ✅ FIXED: Notify admin about new subscription
            try:
                NotificationService.notify_new_newsletter_subscriber(newsletter_subscription)
                print(f"✅ Admin notified about new subscriber: {request.user.email}")
            except Exception as e:
                print(f"❌ Failed to notify admin about new subscriber: {e}")
            
            messages.success(request, 'You have been subscribed to our newsletter! A welcome email has been sent to you.')
            
        elif 'unsubscribe' in request.POST:
            # Unsubscribe from newsletter
            if newsletter_subscription:
                email = newsletter_subscription.email
                newsletter_subscription.is_active = False
                newsletter_subscription.receive_donation_updates = False
                newsletter_subscription.receive_community_news = False
                newsletter_subscription.receive_new_items_alerts = False
                newsletter_subscription.save()
                
                # ✅ NOTIFY ADMIN ABOUT UNSUBSCRIBE
                try:
                    NotificationService.notify_newsletter_unsubscribe_admin(newsletter_subscription)
                except Exception as e:
                    print(f"❌ Failed to notify admin about unsubscribe: {e}")
                
                # ✅ SEND CONFIRMATION EMAIL TO USER
                try:
                    NotificationService.send_unsubscribe_confirmation_email(newsletter_subscription)
                except Exception as e:
                    print(f"❌ Failed to send unsubscribe confirmation to {email}: {e}")
                
                messages.success(request, 'You have been unsubscribed from all newsletter emails. A confirmation email has been sent to you.')
            else:
                messages.info(request, 'You are not currently subscribed.')
                
        elif 'update_preferences' in request.POST:
            # Update newsletter preferences - only if already subscribed
            if newsletter_subscription and newsletter_subscription.is_active:
                newsletter_subscription.receive_donation_updates = 'receive_donation_updates' in request.POST
                newsletter_subscription.receive_community_news = 'receive_community_news' in request.POST
                newsletter_subscription.receive_new_items_alerts = 'receive_new_items_alerts' in request.POST
                newsletter_subscription.save()
                messages.success(request, 'Your newsletter preferences have been updated!')
            else:
                messages.error(request, 'Please subscribe to the newsletter first to update preferences.')
        
        return redirect('core:manage_newsletter_preferences')

    context = {
        'newsletter_subscription': newsletter_subscription,
    }
    
    return render(request, 'core/newsletter_preferences.html', context)


@login_required
def newsletter_statistics(request):
    """View newsletter statistics (staff only)"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('core:index')
    
    stats = get_newsletter_stats()
    subscribers = NewsletterSubscriber.objects.filter(is_active=True).order_by('-subscribed_at')
    
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    recent_subscriptions = NewsletterSubscriber.objects.filter(
        subscribed_at__gte=thirty_days_ago,
        is_active=True
    ).count()
    
    context = {
        'stats': stats,
        'subscribers': subscribers,
        'recent_subscriptions': recent_subscriptions,
        'active_nav': 'admin',
    }
    return render(request, 'core/newsletter_stats.html', context)


# AJAX Views
@login_required
def get_unread_notification_count(request):
    """Get count of unread notifications for AJAX updates"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


def search_items_ajax(request):
    """AJAX search for items"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'items': []})
    
    items = ClothingItem.objects.filter(
        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(tags__icontains=query),
        is_active=True,
        status='available'
    )[:8]
    
    results = []
    for item in items:
        primary_image = item.primary_image
        image_url = primary_image.image.url if primary_image and primary_image.image else None
        
        results.append({
            'id': str(item.id),
            'title': item.title,
            'category': item.category.name,
            'condition': item.condition.name,
            'image_url': image_url,
            'url': reverse('core:item_detail', kwargs={'item_id': item.id})
        })
    
    return JsonResponse({'items': results})


def check_subscription_status(request):
    """Check if an email is already subscribed"""
    email = request.GET.get('email', '').strip().lower()
    
    if not email:
        return JsonResponse({'subscribed': False})
    
    is_subscribed = NewsletterSubscriber.objects.filter(
        email=email, 
        is_active=True
    ).exists()
    
    return JsonResponse({'subscribed': is_subscribed})


# Error handlers
def handler404(request, exception):
    return render(request, 'core/404.html', status=404)


def handler500(request):
    return render(request, 'core/500.html', status=500)


def privacy_policy(request):
    """Privacy Policy page"""
    context = {
        'active_nav': 'privacy',
    }
    return render(request, 'core/privacy_standalone.html', context)


def terms_of_service(request):
    """Terms of Service page"""
    context = {
        'active_nav': 'terms',
    }
    return render(request, 'core/terms_standalone.html', context)

# Newsletter API Views - Add these to your views.py
@require_POST
@csrf_exempt
def newsletter_subscribe_api(request):
    """API endpoint for newsletter subscription - used by footer JavaScript"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        
        if not email:
            return JsonResponse({
                'success': False, 
                'message': 'Email is required'
            }, status=400)
        
        # Email validation
        if '@' not in email or '.' not in email:
            return JsonResponse({
                'success': False,
                'message': 'Please enter a valid email address.'
            })
        
        # Check if already subscribed
        existing_subscriber = NewsletterSubscriber.objects.filter(email=email, is_active=True).first()
        if existing_subscriber:
            return JsonResponse({
                'success': False,
                'message': 'This email is already subscribed to our newsletter.'
            })
        
        # Check for inactive subscription
        inactive_subscriber = NewsletterSubscriber.objects.filter(email=email, is_active=False).first()
        if inactive_subscriber:
            # Reactivate with user's explicit consent
            inactive_subscriber.is_active = True
            inactive_subscriber.receive_donation_updates = True
            inactive_subscriber.receive_community_news = True
            inactive_subscriber.receive_new_items_alerts = True
            inactive_subscriber.receive_exchange_notifications = True
            inactive_subscriber.receive_request_updates = True
            
            # Link to user if authenticated
            if request.user.is_authenticated:
                inactive_subscriber.user = request.user
            
            inactive_subscriber.save()
            subscriber = inactive_subscriber
        else:
            # Create new subscription
            subscriber = NewsletterSubscriber(
                email=email,
                is_active=True,
                receive_donation_updates=True,
                receive_community_news=True,
                receive_new_items_alerts=True,
                receive_exchange_notifications=True,
                receive_request_updates=True
            )
            
            # Link to user if authenticated
            if request.user.is_authenticated:
                subscriber.user = request.user
            
            subscriber.save()
        
        # Send welcome email
        try:
            NotificationService.send_newsletter_welcome_email(subscriber)
            print(f"✅ Welcome email sent to {email}")
        except Exception as e:
            print(f"❌ Failed to send welcome email to {email}: {e}")
        
        # Notify admin about new subscription
        try:
            NotificationService.notify_new_newsletter_subscriber(subscriber)
            print(f"✅ Admin notified about new subscriber: {email}")
        except Exception as e:
            print(f"❌ Failed to notify admin about new subscriber {email}: {e}")
        
        return JsonResponse({
            'success': True,
            'message': 'Successfully subscribed to newsletter! Welcome email sent.'
        })
        
    except IntegrityError as e:
        return JsonResponse({
            'success': False,
            'message': 'Subscription error. Please try again.'
        })
    except Exception as e:
        print(f"❌ Newsletter subscription API error: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again later.'
        })

@require_POST
@csrf_exempt
def newsletter_unsubscribe_api(request):
    """API endpoint for newsletter unsubscription - used by footer JavaScript"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        
        if not email:
            return JsonResponse({
                'success': False, 
                'message': 'Email is required'
            }, status=400)
        
        # Verify email belongs to authenticated user
        if request.user.is_authenticated and email != request.user.email:
            return JsonResponse({
                'success': False,
                'message': 'Invalid email address'
            }, status=400)
        
        try:
            subscriber = NewsletterSubscriber.objects.get(email=email, is_active=True)
            subscriber.is_active = False
            subscriber.receive_donation_updates = False
            subscriber.receive_community_news = False
            subscriber.receive_new_items_alerts = False
            subscriber.receive_exchange_notifications = False
            subscriber.receive_request_updates = False
            subscriber.unsubscribed_at = timezone.now()
            subscriber.save()
            
            # Notify admin about unsubscribe
            try:
                NotificationService.notify_newsletter_unsubscribe_admin(subscriber)
                print(f"✅ Admin notified about unsubscribe: {email}")
            except Exception as e:
                print(f"❌ Failed to notify admin about unsubscribe: {e}")
            
            # Send confirmation email to user
            try:
                NotificationService.send_unsubscribe_confirmation_email(subscriber)
                print(f"✅ Unsubscribe confirmation sent to: {email}")
            except Exception as e:
                print(f"❌ Failed to send unsubscribe confirmation to {email}: {e}")
            
            return JsonResponse({
                'success': True,
                'message': 'Successfully unsubscribed from newsletter. Confirmation email sent.'
            })
            
        except NewsletterSubscriber.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'No active subscription found for this email address.'
            })
            
    except Exception as e:
        print(f"❌ Newsletter unsubscribe API error: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again later.'
        })

def check_subscription_status_api(request):
    """API endpoint to check subscription status - used by footer JavaScript"""
    email = request.GET.get('email', '').strip().lower()
    
    if not email:
        return JsonResponse({'subscribed': False})
    
    try:
        subscriber = NewsletterSubscriber.objects.get(email=email, is_active=True)
        return JsonResponse({
            'subscribed': True,
            'preferences': {
                'receive_donation_updates': subscriber.receive_donation_updates,
                'receive_community_news': subscriber.receive_community_news,
                'receive_new_items_alerts': subscriber.receive_new_items_alerts,
                'receive_exchange_notifications': subscriber.receive_exchange_notifications,
                'receive_request_updates': subscriber.receive_request_updates,
            }
        })
    except NewsletterSubscriber.DoesNotExist:
        return JsonResponse({'subscribed': False})