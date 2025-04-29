import hashlib
import json

from rest_framework import generics, permissions, viewsets, status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import *
from .filters import *
from .serializers import *
from .permissions import ReadOnlyOrAuthenticatedCreate

from pathlib import Path
from datetime import timedelta

User = get_user_model()

@csrf_exempt
def reset_last_active(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            username = body.get('username')

            if not username:
                return JsonResponse({'error': 'Username is required'}, status=400)

            user = User.objects.get(username=username)
            user.last_active = timezone.now()
            user.save(update_fields=['last_active'])

            return JsonResponse({'message': f'Last active for {username} reset successfully.'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

def user_stats(request):
    now = timezone.now()
    ten_minutes_ago = now - timedelta(minutes=10)

    total_users = User.objects.count()
    online_users = User.objects.filter(is_active=True, last_active__gte=ten_minutes_ago).count()

    return JsonResponse({'total': total_users, 'online': online_users})

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        ip_address = self.get_client_ip(request)
        hashed_ip = hashlib.sha256(ip_address.encode()).hexdigest()

        # Optionally: Save it to the user model, logs, or custom tracking model
        response = super().post(request, *args, **kwargs)

        # If login is successful, you can attach/save this hash
        if response.status_code == 200:
            user = TokenObtainPairSerializer().validate(request.data).get("user", None)
            if user:
                # Example: store to custom model (see step 2 below)
                from .models import LoginIPHashLog
                LoginIPHashLog.objects.create(user=user, ip_hash=hashed_ip)

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

class RefreshTokenView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')

            token = RefreshToken(refresh_token)

            new_access_token = token.access_token
            new_refresh_token = str(token)

            return Response({
                'access': str(new_access_token),
                'refresh': new_refresh_token
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

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
    filter_backends = (DjangoFilterBackend,)
    filterset_class = fleetsFilter

class fleetDetailView(generics.RetrieveAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = fleetsFilter

class fleetUpdateView(generics.UpdateAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

class operatorListView(generics.ListCreateAPIView):
    queryset = MBTOperator.objects.all()
    serializer_class = operatorSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorsFilter

class FeatureToggleView(APIView):
    def get(self, request):
        # Fetch all feature toggles
        toggles = featureToggle.objects.all()
        
        # Prepare the data with both 'enabled' and 'maintenance' fields
        toggles_data = {
            toggle.name: {
                'enabled': toggle.enabled,
                'maintenance': toggle.maintenance,
                'coming_soon': toggle.coming_soon,
                'coming_soon_percent': toggle.coming_soon_percent
            }
            for toggle in toggles
        }
        
        # Return the data in the response
        return Response(toggles_data)

    def post(self, request):
        toggle_name = request.data.get('toggle')
        enabled = request.data.get('enabled')

        if toggle_name is None or enabled is None:
            return Response({"detail": "Missing required fields"}, 
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            # Parse the toggle name and type
            name, toggle_type = toggle_name.split('-')
            toggle = featureToggle.objects.get(name=name)

            # Check permissions based on toggle type
            required_perm = None
            if toggle_type == 'enable':
                required_perm = 'mbt_admin.feature_toggle_enable'
            elif toggle_type == 'maintenance':
                required_perm = 'mbt_admin.feature_toggle_maintenance'
            elif toggle_type == 'coming-soon':
                required_perm = 'mbt_admin.feature_toggle_coming_soon'
            else:
                return Response({"detail": "Invalid toggle type"}, 
                              status=status.HTTP_400_BAD_REQUEST)

            if not request.user.has_perm(required_perm):
                return Response({"detail": "You do not have permission to modify this toggle type"}, 
                              status=status.HTTP_403_FORBIDDEN)

            # Update the appropriate field based on toggle type
            if toggle_type == 'enable':
                toggle.enabled = enabled
            elif toggle_type == 'maintenance':
                toggle.maintenance = enabled  
            elif toggle_type == 'coming-soon':
                toggle.coming_soon = enabled

            toggle.save()
            return Response({"detail": "Toggle updated successfully"})

        except featureToggle.DoesNotExist:
            return Response({"detail": "Toggle not found"}, 
                          status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({"detail": "Invalid toggle format"}, 
                          status=status.HTTP_400_BAD_REQUEST)

class operatorDetailView(generics.RetrieveAPIView):
    queryset = MBTOperator.objects.all()
    serializer_class = operatorSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorsFilter

    def get_object(self):
        # Get the operator name from the URL
        operator_name = self.kwargs['name']
        try:
            # Attempt to fetch the operator by name
            return MBTOperator.objects.get(operator_name=operator_name)
        except MBTOperator.DoesNotExist:
            raise NotFound("Operator not found")

def load_regions():
    json_path = Path(__file__).resolve().parent / 'regions.json'
    with open(json_path, 'r') as f:
        return json.load(f)

class regionsListView(APIView):
    def get(self, request):
        regions = load_regions()
        return Response(regions)

    def post(self, request):
        return Response(
            {"detail": "This endpoint is read-only."},
            status=status.HTTP_403_FORBIDDEN
        )

class regionsDetailView(APIView):
    def get(self, request, region_code):
        regions = load_regions()
        for region in regions:
            if region.get('region_code') == region_code:
                return Response(region)
        return Response({"detail": "Region not found."}, status=404)
    
class liveriesListView(generics.ListCreateAPIView):
    queryset = liverie.objects.filter(published=True)
    serializer_class = liveriesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 

class liveriesDetailView(generics.RetrieveAPIView):
    queryset = liverie.objects.filter(published=True)
    serializer_class = liveriesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 

class organisationsListView(generics.ListCreateAPIView):
    queryset = organisation.objects.all()
    serializer_class = organisationsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = organisationFilter

class organisationsDetailView(generics.RetrieveAPIView):
    queryset = organisation.objects.all()
    serializer_class = organisationsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = organisationFilter

class groupsListView(generics.ListCreateAPIView):
    queryset = group.objects.all()
    serializer_class = groupsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = groupFilter

class groupsDetailView(generics.RetrieveAPIView):
    queryset = group.objects.all()
    serializer_class = groupsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = groupFilter

class fleetChangesListView(generics.ListCreateAPIView):
    queryset = fleetChange.objects.all()
    serializer_class = fleetChangesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = historyFilter


class fleetChangesDetailView(generics.RetrieveAPIView):
    queryset = fleetChange.objects.all()
    serializer_class = fleetChangesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = historyFilter

class helperListView(generics.ListCreateAPIView):
    queryset = helper.objects.all()
    serializer_class = helperSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = helperFilter

class helperDetailView(generics.RetrieveAPIView):
    queryset = helper.objects.all()
    serializer_class = helperSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = helperFilter

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

class helperPermsListView(generics.ListCreateAPIView):
    queryset = helperPerm.objects.all()
    serializer_class = helperPermSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = helperPermFilter

class helperPermsDetailView(generics.RetrieveAPIView):
    queryset = helperPerm.objects.all()
    serializer_class = helperPermSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = helperPermFilter

class typeListView(generics.ListCreateAPIView):
    queryset = vehicleType.objects.filter(active=True)
    serializer_class = typeSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = typeFilter

class typeDetailView(generics.RetrieveAPIView):
    queryset = vehicleType.objects.filter(active=True)
    serializer_class = typeSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = typeFilter

class adViewSet(viewsets.ModelViewSet):
    queryset = ad.objects.all()
    serializer_class = adSerializer

class serviceUpdateListView(generics.ListCreateAPIView):
    queryset = serviceUpdate.objects.all()
    serializer_class = serviceUpdateSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = serviceUpdateFilter

#API ROOT
class ApiRootView(APIView):
    def get(self, request):
        # Base URL of the API
        base_url = settings.API_BASE_URL  # You can set this in your settings.py
        return Response({
                "fleet": f"{base_url}/api/fleet/",
                "history": f"{base_url}/api/history/",
                "operators": f"{base_url}/api/operators/",
                "liveries": f"{base_url}/api/liveries/",
                "type": f"{base_url}/api/type/",
                "groups": f"{base_url}/api/groups/",
                "organisations": f"{base_url}/api/organisations/",
                "regions": f"{base_url}/api/regions/",
                "themes": f"{base_url}/api/themes/",
                "routes": f"{base_url}/api/routes/",
                "game routes": f"{base_url}/api/game/",
                "users": f"{base_url}/api/users/search/"
        })
