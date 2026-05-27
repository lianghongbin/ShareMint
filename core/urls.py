from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from core.pwa_views import manifest_view, service_worker_view

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='authentication:login', permanent=False)),
    path('manifest.json', manifest_view, name='pwa_manifest'),
    path('service-worker.js', service_worker_view, name='pwa_service_worker'),
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),
    path('manage/', include('management.urls')),
]
