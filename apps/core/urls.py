from django.urls import path
from apps.core import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('notifications/', views.notifications_list_view, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read_view, name='mark_notification_read'),
]
