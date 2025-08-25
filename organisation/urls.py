from django.urls import path
from group.views import *

urlpatterns = [
    path('<str:organisation_name>/', organisation_view, name='organisation'),
]
