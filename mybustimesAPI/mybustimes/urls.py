from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import *

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('profile/', UserDetailView.as_view(), name='user_profile'),
    path('public/', PublicUserInfoView.as_view(), name='public_user_info'),
    path('public/<str:username>/', PublicUserInfoView.as_view(), name='public_user_info'),
    path('search/', userListView.as_view(), name='users-list'),
    path('search/<str:username>/', PublicUserInfoView.as_view(), name='public_user_info_search'),
    path('search/<int:pk>/', userDetailView.as_view(), name='users-detail'),
]
