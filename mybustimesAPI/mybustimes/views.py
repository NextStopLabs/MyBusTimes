from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.filters import SearchFilter
from rest_framework import generics, permissions, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound

from django.contrib.auth import get_user_model

from django_filters.rest_framework import DjangoFilterBackend

from django.conf import settings

from .models import *
from .filters import *
from .serializers import *
from .permissions import ReadOnlyOrAuthenticatedCreate

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

class UserDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # Handling GET requests
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
    
    # Handling POST requests
    def post(self, request):
        user = request.user

        theme_id = request.data.get('theme_id', user.theme_id)
        badges = request.data.get('badges', None)  # Default to None
        ticketer_code = request.data.get('ticketer_code', user.ticketer_code)
        static_ticketer_code = request.data.get('static_ticketer_code', user.static_ticketer_code)
        last_login_ip = request.data.get('last_login_ip', user.last_login_ip)
        banned = request.data.get('banned', user.banned)
        banned_date = request.data.get('banned_date', user.banned_date)
        banned_reason = request.data.get('banned_reason', user.banned_reason)
        total_user_reports = request.data.get('total_user_reports', user.total_user_reports)

        user.theme_id = theme_id
        user.ticketer_code = ticketer_code
        user.static_ticketer_code = static_ticketer_code
        user.last_login_ip = last_login_ip
        user.banned = banned
        user.banned_date = banned_date
        user.banned_reason = banned_reason
        user.total_user_reports = total_user_reports

        # ✅ Safely set badges if provided
        if badges is not None:
            user.badges.set(badges)

        user.save()

        return Response({
            'message': 'User details updated successfully.',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'theme_id': user.theme_id,
                'badges': list(user.badges.values_list('id', flat=True)),
                'ticketer_code': user.ticketer_code,
                'static_ticketer_code': user.static_ticketer_code,
                'last_login_ip': user.last_login_ip,
                'banned': user.banned,
                'banned_date': user.banned_date,
                'banned_reason': user.banned_reason,
                'total_user_reports': user.total_user_reports
            }
        }, status=status.HTTP_200_OK)


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
                badge_ids = user.badges.values_list('id', flat=True)

                return Response({
                    'id': user.id,
                    'username': user.username,
                    'theme': user.theme_id,
                    'badges': list(badge_ids),
                    'banned': user.banned
                })
            except CustomUser.DoesNotExist:
                return Response({'error': 'User not found'}, status=404)
        else:
            users = CustomUser.objects.all()
            filtered_users = CustomUserFilter(request.query_params, queryset=users)
            users_data = filtered_users.qs.values('id', 'username', 'theme_id', 'badges', 'banned')
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

class fleetListView(generics.ListCreateAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 

class fleetDetailView(generics.RetrieveAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 

class FleetUpdateView(generics.UpdateAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        instance = serializer.save()
        if self.request.user.is_authenticated:
            instance.modified_by = self.request.user  # Assign user modifying the fleet
            instance.save()

class operatorListView(generics.ListCreateAPIView):
    queryset = operator.objects.all()
    serializer_class = operatorSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorsFilter

class FeatureToggleView(APIView):
    def get(self, request):
        toggles = featureToggle.objects.all()
        toggles_data = {toggle.name: toggle.enabled for toggle in toggles}
        return Response(toggles_data)

class operatorDetailView(generics.RetrieveAPIView):
    queryset = operator.objects.all()
    serializer_class = operatorSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorsFilter

    def get_object(self):
        # Get the operator name from the URL
        operator_name = self.kwargs['name']
        try:
            # Attempt to fetch the operator by name
            return operator.objects.get(operator_name=operator_name)
        except operator.DoesNotExist:
            raise NotFound("Operator not found")

class regionsListView(generics.ListCreateAPIView):
    queryset = region.objects.all()
    serializer_class = regionsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 

class regionsDetailView(generics.RetrieveAPIView):
    queryset = region.objects.all()
    serializer_class = regionsSerializer
    lookup_field = 'region_code'
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    
class liveriesListView(generics.ListCreateAPIView):
    queryset = liverie.objects.all()
    serializer_class = liveriesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 

class liveriesDetailView(generics.RetrieveAPIView):
    queryset = liverie.objects.all()
    serializer_class = liveriesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 

class organisationsListView(generics.ListCreateAPIView):
    queryset = organisation.objects.all()
    serializer_class = organisationsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 

class organisationsDetailView(generics.RetrieveAPIView):
    queryset = organisation.objects.all()
    serializer_class = organisationsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 

class groupsListView(generics.ListCreateAPIView):
    queryset = group.objects.all()
    serializer_class = groupsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 

class groupsDetailView(generics.RetrieveAPIView):
    queryset = group.objects.all()
    serializer_class = groupsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 

class routesListView(generics.ListCreateAPIView):
    queryset = route.objects.all()
    serializer_class = routesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = routesFilter

class routesDetailView(generics.RetrieveAPIView):
    queryset = route.objects.all()
    serializer_class = routesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = routesFilter

class badgesListView(generics.ListCreateAPIView):
    queryset = badge.objects.all()
    serializer_class = badgesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = badgesFilter

class badgesDetailView(generics.RetrieveAPIView):
    queryset = badge.objects.all()
    serializer_class = badgesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = badgesFilter

class adViewSet(viewsets.ModelViewSet):
    queryset = ad.objects.all()
    serializer_class = adSerializer

#API ROOT
class ApiRootView(APIView):
    def get(self, request):
        # Base URL of the API
        base_url = settings.API_BASE_URL  # You can set this in your settings.py
        return Response({
                "fleet": f"{base_url}/api/fleet/",
                "operators": f"{base_url}/api/operators/",
                "liveries": f"{base_url}/api/liveries/",
                "groups": f"{base_url}/api/groups/",
                "organisations": f"{base_url}/api/organisations/",
                "regions": f"{base_url}/api/regions/",
                "themes": f"{base_url}/api/themes/",
                "routes": f"{base_url}/api/routes/",
                "users": f"{base_url}/api/users/search/"
        })
