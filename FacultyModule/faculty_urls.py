from django.urls import path
from .views import faculty_dashboard
app_name = 'faculty'
urlpatterns = [

    path('dashboard/', faculty_dashboard, name='faculty_dashboard'),
]

