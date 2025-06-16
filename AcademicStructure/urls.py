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

    path('programs/', views.program_list, name='program_list'),
    path('programs/create/', views.program_create, name='program_create'),
    path('programs/<str:program_id>/', views.program_detail, name='program_detail'),
    path('programs/<str:program_id>/edit/', views.program_update, name='program_update'),
    path('programs/<str:program_id>/delete/', views.program_delete, name='program_delete'),

    # ===========================================
    # COURSE CRUD URLS
    # ===========================================

    path('courses/', views.course_list, name='course_list'),
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<str:course_code>/', views.course_detail, name='course_detail'),
    path('courses/<str:course_code>/edit/', views.course_update, name='course_update'),
    path('courses/<str:course_code>/delete/', views.course_delete, name='course_delete'),

    # ===========================================
    # SEMESTER CRUD URLS
    # ===========================================

    path('semesters/', views.semester_list, name='semester_list'),

    path('semesters/<int:semester_id>/', views.semester_detail, name='semester_detail'),


    # ===========================================
    # SEMESTER DETAILS CRUD URLS
    # ===========================================

# Add to your URL patterns
    path('classes/<int:class_id>/edit/', views.class_update, name='class_edit'),
    path('classes/<int:class_id>/scheme-of-studies/view/', views.scheme_of_studies_view, name='scheme_of_studies_view'),
    path('classes/<int:class_id>/scheme-of-studies/', views.scheme_of_studies_setup, name='class_scheme_list'),

    # ===========================================
    # CLASS CRUD URLS
    # ===========================================

    path('classes/', views.class_list, name='class_list'),
    path('classes/create/', views.class_create, name='class_create'),
    path('classes/<int:class_id>/', views.class_detail, name='class_detail'),
    path('classes/<int:class_id>/edit/', views.class_update, name='class_update'),
    path('classes/<int:class_id>/delete/', views.class_delete, name='class_delete'),

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

