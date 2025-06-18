# AcademicStructure/urls.py - URL Configuration for Academic Structure Module
from django.urls import path
from . import views

app_name = 'academic'

urlpatterns = [

    # ===========================================
    # DEPARTMENT URLS (VIEW ONLY - NO CRUD)
    # ===========================================

    path('departments/', views.department_list, name='department_list'),
    path('departments/<int:department_id>/', views.department_detail, name='department_detail'),

    # ===========================================
    # PROGRAM CRUD URLS
    # ===========================================



    path('programs/<str:program_id>/', views.program_detail, name='program_detail'),


    # ===========================================
    # COURSE CRUD URLS
    # ===========================================



    path('courses/<str:course_code>/', views.course_detail, name='course_detail'),

    # ===========================================
    # SEMESTER CRUD URLS
    # ===========================================




    # ===========================================
    # SEMESTER DETAILS CRUD URLS
    # ===========================================

# Add to your URL patterns

    # ===========================================
    # CLASS CRUD URLS
    # ===========================================


    path('classes/<int:class_id>/', views.class_detail, name='class_detail'),


    # ===========================================
    # UTILITY AJAX ENDPOINTS
    # ===========================================

    path('ajax/program-semesters/', views.get_program_semesters, name='get_program_semesters'),
    path('ajax/semester-courses/', views.get_semester_courses, name='get_semester_courses'),
    path('ajax/program-classes/', views.get_program_classes, name='get_program_classes'),
    path('ajax/academic-stats/', views.academic_structure_stats, name='academic_structure_stats'),

    # ===========================================
    # HIERARCHICAL VIEWS (Admin coordination)
    # ===========================================

    path('departments/<int:department_id>/programs-courses/',
         views.view_department_programs_courses,
         name='view_department_programs_courses'),

    path('departments/<int:department_id>/scheme-of-studies/',
         views.view_department_scheme_of_studies,
         name='view_department_scheme_of_studies'),

    path('departments/<int:department_id>/students/',
         views.view_department_students,
         name='view_department_students'),




]

