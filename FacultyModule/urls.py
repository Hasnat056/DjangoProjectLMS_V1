# FacultyModule/urls.py - URL Configuration for Faculty Module
from django.urls import path
from . import views

app_name = 'faculty'

urlpatterns = [

    # ===========================================
    # FACULTY CRUD URLS (Admin only)
    # ===========================================

    path('faculty/', views.faculty_list, name='faculty_list'),
    path('faculty/create/', views.faculty_create, name='faculty_create'),
    path('faculty/<str:faculty_id>/', views.faculty_detail, name='faculty_detail'),
    path('faculty/<str:faculty_id>/edit/', views.faculty_update, name='faculty_update'),
    path('faculty/<str:faculty_id>/delete/', views.faculty_delete, name='faculty_delete'),

    # ===========================================
    # COURSE ALLOCATION CRUD URLS (Admin only)
    # ===========================================

    path('allocations/', views.course_allocation_list, name='allocation_list'),
    path('allocations/create/', views.course_allocation_create, name='allocation_create'),
    path('allocations/<int:allocation_id>/', views.course_allocation_detail, name='allocation_detail'),
    path('allocations/<int:allocation_id>/edit/', views.course_allocation_update, name='allocation_update'),
    path('allocations/<int:allocation_id>/delete/', views.course_allocation_delete, name='allocation_delete'),

    # ===========================================
    # LECTURE MANAGEMENT URLS (Faculty CRUD, Admin VIEW)
    # ===========================================

    path('lectures/', views.lecture_list, name='lecture_list'),
    path('lectures/create/', views.lecture_create, name='lecture_create'),
    path('lectures/<str:lecture_id>/', views.lecture_detail, name='lecture_detail'),
    path('lectures/<str:lecture_id>/edit/', views.lecture_update, name='lecture_update'),
    path('lectures/<str:lecture_id>/delete/', views.lecture_delete, name='lecture_delete'),

    # ===========================================
    # ASSESSMENT MANAGEMENT URLS (Faculty CRUD, Admin VIEW)
    # ===========================================

    path('assessments/', views.assessment_list, name='assessment_list'),
    path('assessments/create/', views.assessment_create, name='assessment_create'),
    path('assessments/<int:assessment_id>/edit/', views.assessment_update, name='assessment_update'),
    path('assessments/<int:assessment_id>/delete/', views.assessment_delete, name='assessment_delete'),

    # ===========================================
    # ATTENDANCE MANAGEMENT URLS (Faculty modify, Admin VIEW)
    # ===========================================

    path('attendance/lecture/<str:lecture_id>/', views.attendance_management, name='attendance_management'),

    # ===========================================
    # GRADING URLS (FACULTY ONLY - Admin blocked)
    # ===========================================

    path('grading/assessment/<int:assessment_id>/', views.assessment_grading, name='assessment_grading'),

    # ===========================================
    # STUDENT ATTENDANCE VIEWS (Student/Admin access)
    # ===========================================

    path('student-attendance/', views.student_attendance_view, name='student_attendance_view'),
    path('student-attendance/<int:enrollment_id>/', views.student_attendance_view, name='student_attendance_admin'),
    path('student-attendance/course/<int:enrollment_id>/', views.student_course_attendance,
         name='student_course_attendance'),

    # ===========================================
    # DASHBOARD URLS
    # ===========================================



    # ===========================================
    # ADMIN VIEW-ONLY FUNCTIONS (for Person/views.py coordination)
    # ===========================================

    path('admin/allocation/<int:allocation_id>/lectures/',
         views.view_lectures_by_allocation,
         name='view_lectures_by_allocation'),

    path('admin/allocation/<int:allocation_id>/assessments/',
         views.view_assessments_by_allocation,
         name='view_assessments_by_allocation'),

    path('admin/enrollment/<int:enrollment_id>/attendance/',
         views.view_attendance_by_enrollment,
         name='view_attendance_by_enrollment'),

    path('admin/student/<str:student_id>/attendance/',
         views.view_attendance_by_student,
         name='view_attendance_by_student'),

    # ===========================================
    # FACULTY COURSE MANAGEMENT (Admin access)
    # ===========================================

    path('admin/faculty/<str:faculty_id>/allocations/',
         views.faculty_course_allocations,
         name='faculty_course_allocations'),

    path('admin/faculty/<str:faculty_id>/lectures/',
         views.faculty_lectures,
         name='faculty_lectures'),

    # ===========================================
    # UTILITY AJAX ENDPOINTS
    # ===========================================

    path('ajax/faculty-allocations/', views.get_faculty_allocations, name='get_faculty_allocations'),
    path('ajax/course-students/', views.get_course_students, name='get_course_students'),
    path('ajax/allocation-stats', views.allocation_stats_api, name='get_allocation_stats'),

    # ===========================================
    # REPORTING URLS
    # ===========================================

    path('reports/attendance/', views.attendance_report, name='attendance_report'),
    path('reports/performance/', views.faculty_performance_report, name='faculty_performance_report'),

    # ===========================================
    # DYNAMIC FORM HANDLING (if needed)
    # ===========================================

    path('ajax/attendance-form/<str:lecture_id>/', views.attendance_management, name='ajax_attendance_form'),
    path('ajax/grading-form/<int:assessment_id>/', views.assessment_grading, name='ajax_grading_form'),

    path('faculty/api/profile/', views.faculty_profile_api, name='faculty_profile_api'),
    path('faculty/api/dashboard-stats/', views.faculty_dashboard_stats_api, name='faculty_dashboard_stats_api'),
]
