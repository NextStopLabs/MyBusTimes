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
    path('ban-user/<int:user_id>/', ban_user, name='ban-user'),
    path('submit-ban-user/<int:user_id>/', submit_ban_user, name='submit-ban-user'),
    path('submit-ip-ban-user/<int:user_id>/', submit_ip_ban_user, name='submit-ip-ban-user'),
    path('edit-ad/<int:ad_id>/', edit_ad, name='edit-ad'),
    path('delete-ad/<int:ad_id>/', delete_ad, name='delete-ad'),
    path('add-ad/', add_ad, name='add-ad'),
    path('enable-feature/<int:feature_id>/', enable_feature, name='enable-feature'),
    path('enable-ad-feature/<int:feature_id>/', enable_ad_feature, name='enable-ad-feature'),
    path('maintenance-feature/<int:feature_id>/', maintenance_feature, name='maintenance-feature'),
    path('disable-feature/<int:feature_id>/', disable_feature, name='disable-feature'),
    path('disable-ad-feature/<int:feature_id>/', disable_ad_feature, name='disable-ad-feature'),
    path('vehicle-management/', vehicle_management, name='vehicle-management'),
    path('livery-management/', livery_management, name='livery-management'),
    path('livery-management/pending/', livery_approver, name='livery-approver'),
    path('vehicle-management/pending/', vehicle_approver, name='vehicle-approver'),
    path('edit-livery/<int:livery_id>/', edit_livery, name='edit-livery'),
    path('edit-vehicle/<int:vehicle_id>/', edit_vehicle, name='edit-vehicle'),
    path('delete-livery/<int:livery_id>/', delete_livery, name='delete-livery'),
    path('delete-vehicle/<int:vehicle_id>/', delete_vehicle, name='delete-vehicle'),
    path('replace-livery/', replace_livery, name='replace-livery'),
    path('publish-livery/<int:livery_id>/', publish_livery, name='publish-livery'),
    path('publish-vehicle/<int:vehicle_id>/', publish_vehicle, name='publish-vehicle'),
    path('flip-livery/', flip_livery, name='flip-livery'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)