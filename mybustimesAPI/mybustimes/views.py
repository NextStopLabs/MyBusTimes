from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.filters import SearchFilter
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend

from .models import theme, CustomUser
from .filters import CustomUserFilter 
from .serializers import themeSerializer, UserSerializer, userSerializer

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

class UserDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'theme_id': user.theme_id,
            'badges': user.badges,
            'ticketer_code': user.ticketer_code,
            'static_ticketer_code': user.static_ticketer_code,
            'last_login_ip': user.last_login_ip,
            'banned': user.banned,
            'banned_date': user.banned_date,
            'banned_reason': user.banned_reason,
            'total_user_reports': user.total_user_reports
        })

class PublicUserInfoView(generics.ListAPIView):  # Change to ListAPIView for list-based filtering
    permission_classes = [permissions.AllowAny]
    filter_backends = (DjangoFilterBackend,)  # This enables filtering
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer 

    def get(self, request, username=None):
        # If a username is provided, fetch that specific user
        if username:
            try:
                user = CustomUser.objects.get(username=username)
                return Response({
                    'id': user.id,
                    'username': user.username,
                    'theme': user.theme_id,
                    'banned': user.banned
                })
            except CustomUser.DoesNotExist:
                return Response({'error': 'User not found'}, status=404)
        else:
            users = CustomUser.objects.all()
            filtered_users = CustomUserFilter(request.query_params, queryset=users)
            users_data = filtered_users.qs.values('id', 'username', 'theme_id', 'banned')
            return Response(users_data)
        
class userListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = userSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = CustomUserFilter
    permission_classes = [permissions.AllowAny] 

class userDetailView(generics.RetrieveAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = userSerializer
        
class themeListView(generics.ListAPIView):
    queryset = theme.objects.all()
    serializer_class = themeSerializer
    permission_classes = [permissions.AllowAny] 

class themeDetailView(generics.RetrieveAPIView):
    queryset = theme.objects.all()
    serializer_class = themeSerializer