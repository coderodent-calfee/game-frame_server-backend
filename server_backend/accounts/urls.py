# accounts/urls.py
from django.urls import path, include
from .views import GoogleCallbackView
from django.contrib import admin
from .views import home
# accounts/
urlpatterns = [
    # accounts/google/login/callback/
    path('google/login/callback/', GoogleCallbackView.as_view(), name='google_callback'),
    # accounts/
    path('', include('allauth.urls')),

    path('home/', home, name='home'),
    
    # manage the user base in accounts 
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
    
]


# accounts/ google/login/callback/ [name='google_callback']
# accounts/ login/ [name='account_login']
# accounts/ logout/ [name='account_logout']
# accounts/ inactive/ [name='account_inactive']
# accounts/ signup/ [name='account_signup']
# accounts/ reauthenticate/ [name='account_reauthenticate']
# accounts/ email/ [name='account_email']
# accounts/ confirm-email/ [name='account_email_verification_sent']
# accounts/ ^confirm-email/(?P<key>[-:\w]+)/$ [name='account_confirm_email']
# accounts/ password/change/ [name='account_change_password']
# accounts/ password/set/ [name='account_set_password']
# accounts/ password/reset/ [name='account_reset_password']
# accounts/ password/reset/done/ [name='account_reset_password_done']
# accounts/ ^password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$ [name='account_reset_password_from_key']
# accounts/ password/reset/key/done/ [name='account_reset_password_from_key_done']
# accounts/ login/code/confirm/ [name='account_confirm_login_code']
# accounts/ 3rdparty/
# accounts/ social/login/cancelled/
# accounts/ social/login/error/
# accounts/ social/signup/
# accounts/ social/connections/
# accounts/ facebook/
# accounts/ facebook/login/token/ [name='facebook_login_by_token']
# accounts/ google/
# accounts/ google/login/token/ [name='google_login_by_token']


# manage the user base in accounts 
# accounts/ auth/
# Login: /api/v1/auth/login/
# Logout: /api/v1/auth/logout/
# Password Reset Request: /api/v1/auth/password/reset/
# Password Reset Confirm: /api/v1/auth/password/reset/confirm/
# Registration (Signup): /api/v1/auth/registration/
# Resend Email Verification: /api/v1/auth/registration/verify-email/
# User Details: /api/v1/auth/user/
# Social Login (via Google/Facebook, etc.): /api/v1/auth/social/login/
# Social Registration: /api/v1/auth/social/registration/
# accounts/ auth/ password/reset/?$ [name='rest_password_reset']
# accounts/ auth/ password/reset/confirm/?$ [name='rest_password_reset_confirm']
# accounts/ auth/ login/?$ [name='rest_login']
# accounts/ auth/ logout/?$ [name='rest_logout']
# accounts/ auth/ user/?$ [name='rest_user_details']
# accounts/ auth/ password/change/?$ [name='rest_password_change']

# accounts/ auth/registration/
# accounts/ auth/registration/ [name='rest_register']
# accounts/ auth/registration/ verify-email/?$ [name='rest_verify_email']
# accounts/ auth/registration/ resend-email/?$ [name='rest_resend_email']
# accounts/ auth/registration/ ^account-confirm-email/(?P<key>[-:\w]+)/$ [name='account_confirm_email']
# accounts/ auth/registration/ account-email-verification-sent/?$ [name='account_email_verification_sent']