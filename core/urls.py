from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='authentication:login', permanent=False)),
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),
    path('manage/', include('management.urls')),
]
