from django.urls import path
from .views import *

app_name = 'pages'
urlpatterns = [
    path('', home_page, name='home'),
]