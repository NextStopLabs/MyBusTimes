from django.urls import path
from . import views

urlpatterns = [
    path('', views.wiki_home, name='wiki_home'),
    path('banned/', views.wiki_edit_banned, name='wiki_edit_banned'),
    path('create/', views.create_wiki_page, name='create_wiki_page'),
    path('edit/<slug:slug>/', views.edit_wiki_page, name='edit_wiki_page'),

    path('pending/', views.pending_pages, name='pending_pages'),
    path('approve/<slug:slug>/', views.approve_page, name='approve_page'),

    path('pending/<slug:slug>/', views.pending_page, name='pending_page'),
    path('<slug:slug>/', views.wiki_detail, name='wiki_detail'),
]
