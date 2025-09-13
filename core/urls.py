from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
    path("telegram/", include("telegram.urls")),
    # path("api/", include("rag_system.urls")),
    path("api/v1/clients/", include("miniapp.urls")),
]

if settings.DEBUG:  # only serve static/media this way in dev
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
