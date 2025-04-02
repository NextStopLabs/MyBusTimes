from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .serializers import UserSerializer
from .models import theme
from .serializers import themeSerializer

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

class PublicUserInfoView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, username):
        try:
            user = User.objects.get(username=username)
            return Response({
                'username': user.username,
                'theme': user.theme_id,
                'banned': user.banned
            })
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

class themeListView(generics.ListAPIView):
    queryset = theme.objects.all()
    serializer_class = themeSerializer
    permission_classes = [permissions.AllowAny] 

class themeDetailView(generics.RetrieveAPIView):
    queryset = theme.objects.all()
    serializer_class = themeSerializer