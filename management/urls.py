from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/accounts/', include('accounts.urls')),
    path('api/core/', include('core.urls')),
    path('api/events/', include('events.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/reporting/', include('reporting.urls')),
    path('api/sales/', include('sales.urls')),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
