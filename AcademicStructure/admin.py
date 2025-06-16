from django.contrib import admin

from StudentModule.models import Student
from .models import *
# Register your models here.
admin.site.register(Department)
admin.site.register(Program)
admin.site.register(Semester)
admin.site.register(Class)
admin.site.register(Course)
admin.site.register(Semesterdetails)
