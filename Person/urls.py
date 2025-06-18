# Person/urls.py - URL Configuration for Person Module (Admin Coordination Center)
from django.urls import path, include
from . import views
from AcademicStructure.views import scheme_of_studies_view,scheme_of_studies_create

app_name = 'management'
urlpatterns = [

    # ===========================================
    # MAIN ADMIN DASHBOARD & COORDINATION
    # ===========================================

    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('search/', views.global_search, name='global_search'),

    # ===========================================
    # Faculty CURD views via reference views in Person
    # ===========================================
    path ('faculty/', views.faculty_list, name='faculty_list'),
    path('faculty/create/', views.faculty_create, name='faculty_create'),
    path('faculty/<str:faculty_id>/edit/', views.faculty_update, name='faculty_edit'),
    path('faculty/<str:faculty_id>/delete/', views.faculty_delete, name='faculty_delete'),
    path('faculty/<str:faculty_id>/', views.faculty_detail, name='faculty_detail'),

    # ==========================================================
    # Course Allocation CURD views via reference views in Person
    # ==========================================================

    path('allocations/',views.course_allocation_list, name='course_allocation_list'),
    path('allocations/create/', views.course_allocation_create, name='allocation_create'),
    path('allocations/<int:allocation_id>/', views.course_allocation_detail, name='course_allocation_detail'),
    path('allocations/<int:allocation_id>/delete/', views.course_allocation_delete, name='course_allocation_delete'),
    path('allocations/<int:allocation_id>/edit/',views.course_allocation_update, name='course_allocation_update'),

    # ===============================================
    # Course CURD views via reference views in Person
    # ===============================================

    path('courses/', views.course_list, name='course_list'),
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<str:course_code>/', views.course_detail, name='course_detail'),
    path('courses/<str:course_code>/edit/', views.course_update, name='course_update'),
    path('courses/<str:course_code>/delete/', views.course_delete, name='course_delete'),

    # ================================================
    # Program CURD views via reference views in Person
    # ================================================

    path('programs/', views.program_list, name='program_list'),
    path('programs/create/', views.program_create, name='program_create'),
    path('programs/<str:program_id>/', views.program_detail, name='program'),
    path('programs/<str:program_id>/edit/', views.program_update, name='program_update'),
    path('programs/<str:program_id>/delete/', views.program_delete, name='program_delete'),

    # ==============================================
    # Class CURD views via reference views in Person
    # ==============================================

    path('classes/', views.class_list, name='class_list'),
    path('classes/create/', views.class_create, name='class_create'),
    path('classes/<int:class_id>/', views.class_detail, name='class_detail'),
    path('classes/<int:class_id>/edit/', views.class_update, name='class_update'),
    path('classes/<int:class_id>/delete/', views.class_delete, name='class_delete'),
    path('classes/<int:class_id>/edit/',scheme_of_studies_create, name='scheme_of_studies_create'),
    path('classes/<int:class_id>/scheme-of-studies/view/', scheme_of_studies_view, name='scheme_of_studies_view'),


    # ================================================
    # Student CURD views via reference views in Person
    # ================================================

    path('students/', views.student_list, name='student_list'),
    path('students/create/', views.student_create, name='student_create'),
    path('students/<str:student_id>/', views.student_detail, name='student_detail'),
    path('students/<str:student_id>/edit/', views.student_update, name='student_update'),
    path('students/<str:student_id>/delete/', views.student_delete, name='student_delete'),

    # ===========================================
    # Enrollment CURD views via views in Person
    # ===========================================

    path('enrollments/', views.enrollment_list, name='enrollment_list'),
    path('enrollments/create/', views.enrollment_create, name='enrollment_create'),
    path('enrollment/<int:enrollment_id>/', views.enrollment_detail, name='enrollment_detail'),
    path ('enrollments/<int:enrollment_id>/edit/',views.enrollment_update, name='enrollment_update'),
    path('enrollments/<int:enrollment_id>/delete/', views.enrollment_delete, name='enrollment_delete'),


    # ===========================================
    # PERSON MODULE SPECIFIC URLS (Native to this app)
    # ===========================================

    # Admin Profile Management
    path('profile/', views.admin_profile, name='admin_profile'),
    path('profile/edit/', views.admin_profile_update, name='admin_profile_update'),

    # Salary Management
    path('salaries/', views.salary_list, name='salary_list'),
    path('salaries/create/', views.salary_create, name='salary_create'),
    path('salaries/<int:salary_id>/', views.salary_detail, name='salary_detail'),
    path('salaries/<int:salary_id>/edit/', views.salary_update, name='salary_update'),
    path('salaries/<int:salary_id>/delete/', views.salary_delete, name='salary_delete'),

    # Alumni Management
    path('alumni/', views.alumni_list, name='alumni_list'),
    path('alumni/create/', views.alumni_create, name='alumni_create'),
    path('alumni/<str:alumni_id>/', views.alumni_detail, name='alumni_detail'),
    path('alumni/<str:alumni_id>/edit/', views.alumni_update, name='alumni_update'),
    path('alumni/<str:alumni_id>/delete/', views.alumni_delete, name='alumni_delete'),
    path('alumni/report/', views.alumni_report, name='alumni_report'),

    # ===========================================
    # ADMIN COORDINATION & VIEW-ONLY FUNCTIONS
    # ===========================================

    # Hierarchical Views
    path('department/<int:department_id>/programs-courses/',
         views.view_department_programs_courses,
         name='view_department_programs_courses'),

    path('department/<int:department_id>/scheme-of-studies/',
         views.view_department_scheme_of_studies,
         name='view_department_scheme_of_studies'),

    path('department/<int:department_id>/students/',
         views.view_department_students,
         name='view_department_students'),

    # Cross-Module View Functions
    path('allocation/<int:allocation_id>/lectures/',
         views.view_lectures_by_allocation,
         name='view_lectures_by_allocation'),

    path('allocation/<int:allocation_id>/assessments/',
         views.view_assessments_by_allocation,
         name='view_assessments_by_allocation'),

    path('student/<str:student_id>/attendance/',
         views.view_attendance_by_student,
         name='view_attendance_by_student'),

    path('student/<str:student_id>/transcript/',
         views.view_student_transcript,
         name='view_student_transcript'),

    # ===========================================
    # REPORTING & ANALYTICS
    # ===========================================

    path('reports/department/<int:department_id>/',
         views.generate_department_report,
         name='generate_department_report'),

    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('reports/faculty-performance/', views.faculty_performance_report, name='faculty_performance_report'),
    path('reports/student-analytics/', views.student_analytics_report, name='student_analytics_report'),
    path('reports/semester-performance/', views.semester_performance_report, name='semester_performance_report'),

    # ===========================================
    # AUDIT TRAIL MANAGEMENT
    # ===========================================

    path('audit/', views.audit_trail_list, name='audit_trail_list'),
    path('audit/<int:audit_id>/', views.audit_trail_detail, name='audit_trail_detail'),

    # ===========================================
    # BULK OPERATIONS & SYSTEM UTILITIES
    # ===========================================

    path('bulk-operations/', views.bulk_operations, name='bulk_operations'),
    path('bulk-operations/students/', views.bulk_student_operations, name='bulk_student_operations'),

    path('system/health-check/', views.system_health_check, name='system_health_check'),
    path('system/data-integrity/', views.data_integrity_check, name='data_integrity_check'),
    path('system/fix-issue/<str:issue_type>/', views.fix_data_issue, name='fix_data_issue'),
    path('system/export-data/', views.export_data, name='export_data'),

    # ===========================================
    # API ENDPOINTS FOR DASHBOARD
    # ===========================================

    path('api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('api/recent-activities/', views.recent_activities_api, name='recent_activities_api'),
    path('api/quick-stats/', views.quick_stats_api, name='quick_stats_api'),
    path('api/user-profile/', views.admin_profile_api, name='admin_profile_api'),
]
