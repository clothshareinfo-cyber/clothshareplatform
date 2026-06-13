from django.shortcuts import redirect, render
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from userauths.forms import UserRegisterForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth import get_user_model

# ✅ ADD: Import NewsletterSubscriber model
from core.models import NewsletterSubscriber

User = get_user_model()

def send_welcome_email(user):
    """Send welcome email to new users - NO AUTO-SUBSCRIPTION"""
    subject = 'Welcome to ClothShare! Start Your Sustainable Fashion Journey'
    
    # HTML email content
    html_message = render_to_string('userauths/welcome_email.html', {
        'user': user,
        'site_name': 'ClothShare',
    })
    
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send welcome email: {e}")
        return False

def register_view(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()  # Save user to DB
            username = form.cleaned_data.get("username")
            
            # ✅ CHANGED: Send welcome email but DON'T auto-subscribe to newsletter
            email_sent = send_welcome_email(user)
            
            # ✅ ADD: Check if user already has a newsletter subscription
            try:
                existing_subscription = NewsletterSubscriber.objects.get(email=user.email)
                # If found, update the user field but don't auto-activate
                existing_subscription.user = user
                existing_subscription.save()
                subscription_status = "existing subscription updated"
            except NewsletterSubscriber.DoesNotExist:
                # ✅ CHANGED: Don't create newsletter subscription - user must manually subscribe
                subscription_status = "no auto-subscription"
            
            # ✅ CHANGED: Success message encourages manual newsletter subscription
            if email_sent:
                messages.success(
                    request, 
                    f"Hey {username}, your account was created successfully! "
                    f"A welcome email has been sent to {user.email}. "
                    f"Want to stay updated? Subscribe to our newsletter in your profile settings!"
                )
            else:
                messages.success(
                    request, 
                    f"Hey {username}, your account was created successfully! "
                    f"Want to stay updated? Subscribe to our newsletter in your profile settings!"
                )

            login(request, user)  # Log in the user immediately
            return redirect("core:index")  # Redirect to home page
    else:
        form = UserRegisterForm()
    
    return render(request, "userauths/sign-up.html", {"form": form})

def login_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "Hey, you are already logged in.")
        return redirect("core:index")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user_obj = User.objects.get(email=email)
            
        except User.DoesNotExist:
            messages.warning(request, f"User with email '{email}' does not exist.")
            return redirect("userauths:sign-in")
        
        # FIX: use username=email instead of email=email
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect("core:index")  # Redirects to homepage
        else:
            messages.error(request, "Invalid email or password. Please try again.")
            return redirect("userauths:sign-in")

    return render(request, "userauths/sign-in.html")

def logout_view(request):
    logout(request)
    messages.success(request, "You logged out.")
    return redirect("userauths:sign-in")