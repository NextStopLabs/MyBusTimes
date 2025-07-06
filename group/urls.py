from django.urls import path
from group.views import *

urlpatterns = [
    path('create/', create_group, name='create_group'),
    path('<str:group_name>/', group_view, name='group'),
    path('<str:group_name>/edit/', group_edit, name='group_edit'),
    path('<str:group_name>/delete/', group_delete, name='group_delete'),
]
