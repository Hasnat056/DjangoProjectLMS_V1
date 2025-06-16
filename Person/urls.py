# Person/urls.py - URL Configuration for Person Module (Admin Coordination Center)
from django.urls import path, include
from . import views

app_name = 'person'

urlpatterns = [

    # ===========================================
    # MAIN ADMIN DASHBOARD & COORDINATION
    # ===========================================

    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/search/', views.global_search, name='global_search'),

    # ===========================================
    # INCLUDE OTHER APP URLS (Clean delegation pattern)
    # ===========================================

    # Include Academic Structure URLs
    path('admin/academic/', include('AcademicStructure.urls')),

    # Include Student Module URLs
    path('admin/', include('StudentModule.urls')),

    # Include Faculty Module URLs
    path('admin/', include('FacultyModule.urls')),

    # ===========================================
    # PERSON MODULE SPECIFIC URLS (Native to this app)
    # ===========================================

    # Admin Profile Management
    path('admin/profile/', views.admin_profile, name='admin_profile'),
    path('admin/profile/edit/', views.admin_profile_update, name='admin_profile_update'),

    # Salary Management
    path('admin/salaries/', views.salary_list, name='salary_list'),
    path('admin/salaries/create/', views.salary_create, name='salary_create'),
    path('admin/salaries/<int:salary_id>/', views.salary_detail, name='salary_detail'),
    path('admin/salaries/<int:salary_id>/edit/', views.salary_update, name='salary_update'),
    path('admin/salaries/<int:salary_id>/delete/', views.salary_delete, name='salary_delete'),

    # Alumni Management
    path('admin/alumni/', views.alumni_list, name='alumni_list'),
    path('admin/alumni/create/', views.alumni_create, name='alumni_create'),
    path('admin/alumni/<str:alumni_id>/', views.alumni_detail, name='alumni_detail'),
    path('admin/alumni/<str:alumni_id>/edit/', views.alumni_update, name='alumni_update'),
    path('admin/alumni/<str:alumni_id>/delete/', views.alumni_delete, name='alumni_delete'),
    path('admin/alumni/report/', views.alumni_report, name='alumni_report'),

    # ===========================================
    # ADMIN COORDINATION & VIEW-ONLY FUNCTIONS
    # ===========================================

    # Hierarchical Views
    path('admin/department/<int:department_id>/programs-courses/',
         views.view_department_programs_courses,
         name='view_department_programs_courses'),

    path('admin/department/<int:department_id>/scheme-of-studies/',
         views.view_department_scheme_of_studies,
         name='view_department_scheme_of_studies'),

    path('admin/department/<int:department_id>/students/',
         views.view_department_students,
         name='view_department_students'),

    # Cross-Module View Functions
    path('admin/allocation/<int:allocation_id>/lectures/',
         views.view_lectures_by_allocation,
         name='view_lectures_by_allocation'),

    path('admin/allocation/<int:allocation_id>/assessments/',
         views.view_assessments_by_allocation,
         name='view_assessments_by_allocation'),

    path('admin/student/<str:student_id>/attendance/',
         views.view_attendance_by_student,
         name='view_attendance_by_student'),

    path('admin/student/<str:student_id>/transcript/',
         views.view_student_transcript,
         name='view_student_transcript'),

    # ===========================================
    # REPORTING & ANALYTICS
    # ===========================================

    path('admin/reports/department/<int:department_id>/',
         views.generate_department_report,
         name='generate_department_report'),

    path('admin/analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('admin/reports/faculty-performance/', views.faculty_performance_report, name='faculty_performance_report'),
    path('admin/reports/student-analytics/', views.student_analytics_report, name='student_analytics_report'),
    path('admin/reports/semester-performance/', views.semester_performance_report, name='semester_performance_report'),

    # ===========================================
    # AUDIT TRAIL MANAGEMENT
    # ===========================================

    path('admin/audit/', views.audit_trail_list, name='audit_trail_list'),
    path('admin/audit/<int:audit_id>/', views.audit_trail_detail, name='audit_trail_detail'),

    # ===========================================
    # BULK OPERATIONS & SYSTEM UTILITIES
    # ===========================================

    path('admin/bulk-operations/', views.bulk_operations, name='bulk_operations'),
    path('admin/bulk-operations/students/', views.bulk_student_operations, name='bulk_student_operations'),

    path('admin/system/health-check/', views.system_health_check, name='system_health_check'),
    path('admin/system/data-integrity/', views.data_integrity_check, name='data_integrity_check'),
    path('admin/system/fix-issue/<str:issue_type>/', views.fix_data_issue, name='fix_data_issue'),
    path('admin/system/export-data/', views.export_data, name='export_data'),

    # ===========================================
    # API ENDPOINTS FOR DASHBOARD
    # ===========================================

    path('admin/api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('admin/api/recent-activities/', views.recent_activities_api, name='recent_activities_api'),
    path('admin/api/quick-stats/', views.quick_stats_api, name='quick_stats_api'),
    path('admin/api/user-profile/', views.admin_profile_api, name='admin_profile_api'),
]
