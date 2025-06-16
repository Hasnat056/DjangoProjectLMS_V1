from django.urls import path
from .views import login_view,register_view, user_logout

app_name = 'accounts'
urlpatterns = [
    path("register/", register_view, name='register'),
    path("login/", login_view, name='login'),
    path("logout/", user_logout, name='logout'),
]
