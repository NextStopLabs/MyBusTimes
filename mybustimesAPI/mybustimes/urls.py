from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, UserDetailView, PublicUserInfoView, userListView, userDetailView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/profile/', UserDetailView.as_view(), name='user_profile'),
    path('public/', PublicUserInfoView.as_view(), name='public_user_info'),
    path('public/<str:username>/', PublicUserInfoView.as_view(), name='public_user_info'),
    path('search/', userListView.as_view(), name='users-list'),
    path('search/<int:pk>/', userDetailView.as_view(), name='users-detail'),
]
