from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from api.views import (
    ItemViewSet, CategoryViewSet, UserRegisterView,
    user_login, user_logout, user_register, user_me, api_root
)
from django.conf import settings
from django.conf.urls.static import static

router = routers.DefaultRouter()
router.register(r'items', ItemViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'users', UserRegisterView)   # kept for backwards compat

urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),

    # Clean auth endpoints (no CSRF, no sessions)
    path('api/auth/login/',    user_login,    name='login'),
    path('api/auth/logout/',   user_logout,   name='logout'),
    path('api/auth/register/', user_register, name='register'),
    path('api/auth/me/',       user_me,       name='me'),

    # Legacy — keep working just in case
    path('api/users/login/',   user_login,    name='login-legacy'),
    path('api/users/logout/',  user_logout,   name='logout-legacy'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)