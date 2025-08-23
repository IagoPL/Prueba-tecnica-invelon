# backend/urls.py
from __future__ import annotations

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView  # opcional: puedes dejarlo

from cine.views import PeliculaViewSet, SesionViewSet, EntradaViewSet


# ---- Admin branding ----
admin.site.site_header = "Cine — Administración"
admin.site.site_title = "Cine Admin"
admin.site.index_title = "Panel de control"


# ---- Health (sin caché) ----
@never_cache
def health_view(_request):
    return JsonResponse({"status": "ok"})


# ---- API v1 router ----
router_v1 = DefaultRouter()
router_v1.register(r"peliculas", PeliculaViewSet, basename="peliculas")
router_v1.register(r"sesiones", SesionViewSet, basename="sesiones")
router_v1.register(r"entradas", EntradaViewSet, basename="entradas")

urlpatterns = [
    path("admin/", admin.site.urls),

    # API v1
    path("api/v1/", include(router_v1.urls)),
    path("api/v1/health/", health_view, name="api-health"),

    # JWT (opcional; puedes dejarlos por si quieres probar con auth)
    path("api/v1/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]


# ---- Documentación OpenAPI (si está instalada) ----
try:
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularSwaggerView,
        SpectacularRedocView,
    )

    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]
except Exception:
    # Si no está instalado, simplemente no exponemos docs.
    pass


# ---- Desarrollo: debug toolbar + media ----
if settings.DEBUG:
    try:
        import debug_toolbar  # type: ignore
        urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    except Exception:
        pass

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
