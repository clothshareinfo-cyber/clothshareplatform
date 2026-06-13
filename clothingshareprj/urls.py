# clothingshareprj/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.views.generic import RedirectView

def admin_dashboard(request):
    """
    Custom admin dashboard view
    """
    # Add your dashboard logic here
    context = {
        'title': 'Admin Dashboard'
    }
    return render(request, 'admin/dashboard.html', context)

urlpatterns = [
    # 🔥 ADD THIS: Custom admin dashboard route MUST come before admin.site.urls
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),
    
    # Admin URLs
    path('admin/', admin.site.urls),
    
    # Your app URLs
    path('', include('core.urls')),  # Include core URLs at root
    path('auth/', include('userauths.urls')),  # Your auth URLs
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)