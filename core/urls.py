from django.urls import path
from django.views.generic import RedirectView
from core.views import (
    index, browse_items, item_detail, donate_item, edit_item, delete_item,
    request_clothing, view_requests, my_requests, delete_request,
    profile, edit_profile, initiate_exchange, my_exchanges, manage_exchange,
    community_impact, notifications, get_unread_notification_count, search_items_ajax,
    subscribe_newsletter, unsubscribe_newsletter, manage_newsletter_preferences,
    newsletter_statistics, check_subscription_status,
    help_page, privacy_policy, terms_of_service, cancel_exchange,
    delete_account, delete_account_confirm,
    # ADD THESE IMPORTANT IMPORTS
    newsletter_subscribe_api, newsletter_unsubscribe_api, check_subscription_status_api
)

app_name = "core"

urlpatterns = [
    # 🔥 CRITICAL FIX: Add this line to redirect /accounts/login/ to /auth/sign-in/
    path('accounts/login/', RedirectView.as_view(url='/auth/sign-in/', query_string=True, permanent=False)),
    
    # Main pages
    path("", index, name="index"),
    path("browse/", browse_items, name="browse"),
    path("impact/", community_impact, name="impact"),
    path("help/", help_page, name="help"),
    path("privacy-policy/", privacy_policy, name="privacy_policy"),
    path("terms-of-service/", terms_of_service, name="terms_of_service"),
    
    # Item management
    path("item/<uuid:item_id>/", item_detail, name="item_detail"),
    path("donate/", donate_item, name="donate"),
    path("item/<uuid:item_id>/edit/", edit_item, name="edit_item"),
    path("item/<uuid:item_id>/delete/", delete_item, name="delete_item"),
    
    # Request management
    path("request/", request_clothing, name="request"),
    path("requests/", view_requests, name="view_requests"),
    path("my-requests/", my_requests, name="my_requests"),
    path("request/<uuid:request_id>/delete/", delete_request, name="delete_request"),
    
    # Exchange management
    path("item/<uuid:item_id>/exchange/", initiate_exchange, name="initiate_exchange"),
    path("item/<uuid:item_id>/exchange/cancel/", cancel_exchange, name="cancel_exchange"),
    path("my-exchanges/", my_exchanges, name="my_exchanges"),
    path("exchange/<uuid:exchange_id>/manage/", manage_exchange, name="manage_exchange"),
    
    # User profile
    path("profile/", profile, name="profile"),
    path("profile/edit/", edit_profile, name="edit_profile"),
    path("notifications/", notifications, name="notifications"),
    
    # Account Deletion URLs
    path("profile/delete-account/", delete_account, name="delete_account"),
    path("profile/delete-account/confirm/", delete_account_confirm, name="delete_account_confirm"),
    
    # Newsletter URLs - TRADITIONAL (for forms)
    path("newsletter/subscribe/", subscribe_newsletter, name="subscribe_newsletter"),
    path("newsletter/unsubscribe/<str:token>/", unsubscribe_newsletter, name="unsubscribe_newsletter"),
    path("newsletter/preferences/", manage_newsletter_preferences, name="manage_newsletter_preferences"),
    path("newsletter/statistics/", newsletter_statistics, name="newsletter_statistics"),
    path("newsletter/check-subscription/", check_subscription_status, name="check_subscription_status"),
    
    # 🔥 NEWSLETTER API ENDPOINTS - FOR FOOTER JAVASCRIPT (different URLs)
    path("api/newsletter/subscribe/", newsletter_subscribe_api, name="newsletter_subscribe_api"),
    path("api/newsletter/unsubscribe/", newsletter_unsubscribe_api, name="newsletter_unsubscribe_api"),
    path("api/newsletter/check-subscription/", check_subscription_status_api, name="check_subscription_status_api"),
    
    # AJAX endpoints
    path("ajax/notification-count/", get_unread_notification_count, name="notification_count"),
    path("ajax/search/", search_items_ajax, name="search_ajax"),
]