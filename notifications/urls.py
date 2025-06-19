from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.list_notifications, name='list_notifications'),
    path('<uuid:pk>/status/', views.update_notification_status, name='update_notification_status'),
]