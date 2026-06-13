from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from .models import (
    ClothingItem, ItemImage, ClothingRequest,
    UserProfile, Exchange, NewsletterSubscriber
)

class ClothingItemForm(forms.ModelForm):
    # REMOVED the problematic images field - images will be handled via formset
    
    class Meta:
        model = ClothingItem
        fields = [
            'title', 'description', 'category', 'size', 
            'condition', 'gender', 'mode', 'location', 'tags'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Blue Denim Jacket'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input form-textarea',
                'rows': 4,
                'placeholder': 'Describe the item, including brand, material, and any notable features...'
            }),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'size': forms.Select(attrs={'class': 'form-input'}),
            'condition': forms.Select(attrs={'class': 'form-input'}),
            'gender': forms.Select(attrs={'class': 'form-input'}),
            'mode': forms.Select(attrs={'class': 'form-input'}),
            'location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Seattle, WA'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'jacket, denim, casual (comma separated)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make certain fields optional
        self.fields['size'].required = False
        self.fields['gender'].required = False
        self.fields['location'].required = False
        self.fields['tags'].required = False

class ItemImageForm(forms.ModelForm):
    class Meta:
        model = ItemImage
        fields = ['image', 'alt_text', 'is_primary']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': 'image/*'
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Description of the image...'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
        }

# Formset for multiple image uploads
ItemImageFormSet = inlineformset_factory(
    ClothingItem, ItemImage,
    form=ItemImageForm,
    extra=3,
    can_delete=True,
    max_num=10,
    fields=['image', 'alt_text', 'is_primary']
)

class ClothingRequestForm(forms.ModelForm):
    class Meta:
        model = ClothingRequest
        fields = ['category', 'size', 'gender', 'description', 'urgency']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-input'}),
            'size': forms.Select(attrs={'class': 'form-input'}),
            'gender': forms.Select(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={
                'class': 'form-input form-textarea',
                'rows': 4,
                'placeholder': 'Describe what you\'re looking for and why you need it...'
            }),
            'urgency': forms.Select(attrs={'class': 'form-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make size and gender optional
        self.fields['size'].required = False
        self.fields['gender'].required = False

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone', 'location', 'affiliation', 'bio', 'avatar']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+1 (555) 123-4567'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Seattle, WA'
            }),
            'affiliation': forms.Select(attrs={'class': 'form-input'}),
            'bio': forms.Textarea(attrs={
                'class': 'form-input form-textarea',
                'rows': 3,
                'placeholder': 'Tell us about yourself...'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': 'image/*'
            }),
        }

class ExchangeForm(forms.ModelForm):
    class Meta:
        model = Exchange
        fields = ['message', 'exchange_location']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-input form-textarea',
                'rows': 4,
                'placeholder': 'Introduce yourself and propose how you\'d like to exchange...'
            }),
            'exchange_location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Preferred meeting location...'
            }),
        }

# Newsletter Subscription Form
class NewsletterSubscriptionForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'newsletter__input',
                'placeholder': 'Enter your email address',
                'required': 'required'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
    def clean_email(self):
        email = self.cleaned_data.get('email').strip().lower()
        
        # Basic email validation
        if not email:
            raise ValidationError('Please enter an email address.')
        
        if '@' not in email or '.' not in email:
            raise ValidationError('Please enter a valid email address.')
        
        # Check if already actively subscribed
        existing_subscriber = NewsletterSubscriber.objects.filter(
            email=email, 
            is_active=True
        ).first()
        
        if existing_subscriber:
            raise ValidationError('This email is already subscribed to our newsletter.')
        
        return email
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Link to user if authenticated
        if self.request and self.request.user.is_authenticated:
            instance.user = self.request.user
        
        if commit:
            instance.save()
        
        return instance

# Newsletter Preferences Form
class NewsletterPreferencesForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = [
            'receive_donation_updates', 
            'receive_community_news', 
            'receive_new_items_alerts'
        ]
        widgets = {
            'receive_donation_updates': forms.CheckboxInput(attrs={
                'class': 'form-checkbox newsletter-preference'
            }),
            'receive_community_news': forms.CheckboxInput(attrs={
                'class': 'form-checkbox newsletter-preference'
            }),
            'receive_new_items_alerts': forms.CheckboxInput(attrs={
                'class': 'form-checkbox newsletter-preference'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add labels with descriptions
        self.fields['receive_donation_updates'].label = 'Donation Updates'
        self.fields['receive_community_news'].label = 'Community News'
        self.fields['receive_new_items_alerts'].label = 'New Item Alerts'
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Auto-set is_active based on preferences
        instance.is_active = any([
            instance.receive_donation_updates,
            instance.receive_community_news,
            instance.receive_new_items_alerts
        ])
        
        if commit:
            instance.save()
        
        return instance

# Quick Newsletter Form (for footer usage)
class QuickNewsletterForm(forms.Form):
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'newsletter__input',
            'placeholder': 'Enter your email address',
            'required': 'required'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean_email(self):
        email = self.cleaned_data.get('email').strip().lower()
        
        # Basic email validation
        if not email:
            raise ValidationError('Please enter an email address.')
        
        if '@' not in email or '.' not in email:
            raise ValidationError('Please enter a valid email address.')
        
        return email