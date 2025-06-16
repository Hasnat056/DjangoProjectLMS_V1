from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Faculty)
admin.site.register(Courseallocation)
admin.site.register(Lecture)
admin.site.register(Assessment)
admin.site.register(Assessmentchecked)
admin.site.register(Attendance)