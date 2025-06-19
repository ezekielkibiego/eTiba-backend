from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views 

app_name = 'auth_user'

urlpatterns = [
    path('register/', views.user_registration_view, name='user_registration'),
    path('login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.user_logout_view, name='user_logout'),
    path('verify-email/<str:uidb64>/<str:token>/', views.verify_email_view, name='verify_email'),
    path('resend-verification-email/', views.resend_verification_email_view, name='resend_verification_email'),
]

