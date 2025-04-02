from django.contrib import admin
from django.urls import path, include
from mybustimes.views import themeListView, themeDetailView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('mybustimes.urls')),
    path('api/themes/', themeListView.as_view(), name='theme-list'),
    path('api/themes/<int:pk>/', themeDetailView.as_view(), name='theme-detail'),
]