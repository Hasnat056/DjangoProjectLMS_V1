# StudentModule/urls.py - URL Configuration for Student Module
from django.urls import path
from . import views
import FacultyModule.views as fviews
import Person.views as pviews

app_name = 'student'

urlpatterns = [

    # ===========================================
    # STUDENT CRUD URLS (Admin only)
    # ===========================================



    # ===========================================
    # ENROLLMENT CRUD URLS (Admin/Student access)
    # ===========================================


    # ===========================================
    # RESULT MANAGEMENT URLS (Admin/Faculty can CRUD, Students VIEW)
    # ===========================================

    path('results/', views.result_list, name='result_list'),
    path('results/<int:result_id>/edit/', views.result_update, name='result_update'),

    # ===========================================
    # TRANSCRIPT MANAGEMENT URLS
    # ===========================================

    path('transcript/', views.transcript_view, name='transcript_view'),
    path('transcript/<str:student_id>/', views.transcript_view, name='transcript_view_student'),
    path('transcript/create/', views.transcript_create, name='transcript_create'),

    # ===========================================
    # REVIEWS MANAGEMENT URLS
    # ===========================================

    path('reviews/', views.review_list, name='review_list'),
    path('reviews/create/', views.review_create, name='review_create'),
    path('reviews/<int:review_id>/edit/', views.review_update, name='review_update'),
    path('reviews/<int:review_id>/delete/', views.review_delete, name='review_delete'),

    # ===========================================
    # STUDENT DASHBOARD URLS
    # ===========================================

    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('academic-progress/', views.academic_progress, name='academic_progress'),
    path('academic-progress/<str:student_id>/', views.academic_progress, name='academic_progress_student'),

    # ===========================================
    # GRADES AND ASSESSMENT URLS
    # ===========================================

    path('grades/', views.student_grades, name='student_grades'),
    path('grades/<str:student_id>/', views.student_grades, name='student_grades_student'),

    # ===========================================
    # ATTENDANCE VIEWS (Student access)
    # ===========================================

    path('attendance/', fviews.student_attendance_view, name='student_attendance'),
    path('attendance/<int:enrollment_id>/', fviews.student_attendance_view, name='student_attendance_admin'),
    path('attendance/course/<int:enrollment_id>/', fviews.student_course_attendance, name='student_course_attendance'),

    # ===========================================
    # ADMIN VIEW-ONLY FUNCTIONS (for Person/views.py coordination)
    # ===========================================

    path('admin/student/<str:student_id>/enrollments/',
         views.view_student_enrollments,
         name='view_student_enrollments'),

    path('admin/student/<str:student_id>/results/',
         views.view_student_results,
         name='view_student_results'),

    path('admin/allocation/<int:allocation_id>/results/',
         views.view_allocation_results,
         name='view_allocation_results'),

    path('admin/student/<str:student_id>/transcript/',
         views.view_student_transcript,
         name='view_student_transcript'),

    path('admin/class/<int:class_id>/transcripts/',
         views.view_class_transcripts,
         name='view_class_transcripts'),

    # ===========================================
    # UTILITY AJAX ENDPOINTS
    # ===========================================

    path('ajax/student-enrollments/', views.get_student_enrollments, name='get_student_enrollments'),
    path('ajax/available-courses/', views.get_available_courses, name='get_available_courses'),

    # ===========================================
    # REPORTING URLS
    # ===========================================

    path('reports/', views.student_reports, name='student_reports'),
    path('reports/performance/', views.student_reports, name='student_performance_report'),
    path('reports/enrollment-statistics/', views.student_reports, name='enrollment_statistics_report'),

    # ===========================================
    # BULK OPERATIONS
    # ===========================================

    path('bulk-operations/', pviews.bulk_student_operations, name='bulk_student_operations'),

    # ===========================================
    # API ENDPOINTS
    # ===========================================




]

