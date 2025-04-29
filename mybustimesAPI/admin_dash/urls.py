from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('users-management/', users_view, name='users-management'),
    path('ads-management/', ads_view, name='ads-management'),
    path('feature-toggles-management/', feature_toggles_view, name='feature-toggles-management'),
    path('fetch-traffic-day-data/', fetch_traffic_day_data, name='fetch_traffic_day_data'),
    path('fetch-traffic-week-data/', fetch_traffic_week_data, name='fetch_traffic_week_data'),
    path('fetch-traffic-live-data/', fetch_traffic_live_data, name='fetch_traffic_live_data'),
    path('login/', custom_login, name='admin-login'),
    path('permission-denied/', permission_denied, name='permission-denied'),
    path('edit-user/<int:user_id>/', edit_user, name='edit-user'),
    path('update-user/<int:user_id>/', update_user, name='update-user'),
    path('delete-user/<int:user_id>/', delete_user, name='delete-user'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)