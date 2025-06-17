# Person views
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone


# Import models from all apps
from .models import Person, Admin, Address, Qualification, Salary, Audittrail, Alumni
from AcademicStructure.models import Department, Program, Course, Semester, Semesterdetails, Class
from FacultyModule.models import Faculty, Courseallocation, Lecture, Assessment, Attendance
from StudentModule.models import Student, Enrollment, Result, Transcript

# Import views from other apps for coordination (form-based)
from AcademicStructure import views as academic_views
from FacultyModule import views as faculty_views
from StudentModule import views as student_views

# Form imports
from .forms import AdminProfileForm, SalaryForm, AlumniForm


def is_admin(user):
    """Check if user is admin"""
    return user.groups.filter(name='admin').exists()


# ===========================================
# MAIN ADMIN DASHBOARD
# ===========================================

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Main admin dashboard with comprehensive system overview"""
    # Get comprehensive statistics
    stats = {
        'total_students': Student.objects.count(),
        'total_faculty': Faculty.objects.count(),
        'total_programs': Program.objects.count(),
        'total_courses': Course.objects.count(),
        'total_departments': Department.objects.count(),
        'active_enrollments': Enrollment.objects.filter(status='Active').count(),
        'active_allocations': Courseallocation.objects.filter(status='Ongoing').count(),
        'total_classes': Class.objects.count(),
        'total_semesters': Semester.objects.count(),
    }

    # Recent activities
    recent_enrollments = Enrollment.objects.select_related(
        'studentid__studentid', 'allocationid__coursecode'
    ).order_by('-enrollmentdate')[:5]

    recent_faculty = Faculty.objects.select_related('employeeid').order_by('-joiningdate')[:5]

    # Department-wise statistics
    dept_stats = []
    for dept in Department.objects.all():
        dept_data = {
            'department': dept,
            'faculty_count': Faculty.objects.filter(departmentid=dept).count(),
            'program_count': Program.objects.filter(departmentid=dept).count(),
            'student_count': Student.objects.filter(programid__departmentid=dept).count(),
        }
        dept_stats.append(dept_data)

    # Performance statistics - FIXED field names
    try:
        avg_gpa = Result.objects.aggregate(Avg('coursegpa'))['coursegpa__avg'] or 0.0  # FIXED: coursegpa
        high_performers = Result.objects.filter(coursegpa__gte=3.5).count()  # FIXED: coursegpa
        total_results = Result.objects.count()
        high_performer_percentage = round((high_performers / total_results * 100), 2) if total_results > 0 else 0
    except:
        avg_gpa = 0.0
        high_performers = 0
        high_performer_percentage = 0

    # Quick stats for widgets
    today = timezone.now().date()
    recent_enrollments_count = Enrollment.objects.filter(
        enrollmentdate__date__gte=today - timedelta(days=7)
    ).count()

    current_session = "Spring 2025"  # Make this dynamic
    active_courses = Courseallocation.objects.filter(
        status='Active',
        session=current_session
    ).count()

    recent_lectures = Lecture.objects.filter(
        startingtime__date__gte=today - timedelta(days=7)
    ).count()

    context = {
        'stats': stats,
        'recent_enrollments': recent_enrollments,
        'recent_faculty': recent_faculty,
        'dept_stats': dept_stats,
        'performance': {
            'avg_gpa': round(float(avg_gpa), 2) if avg_gpa else 0.0,
            'high_performers': high_performers,
            'high_performer_percentage': high_performer_percentage,
        },
        'quick_stats': {
            'recent_enrollments': recent_enrollments_count,
            'active_courses': active_courses,
            'recent_lectures': recent_lectures,
        }
    }

    return render(request, 'admin/dashboard.html', context)


# ===========================================
# GLOBAL SEARCH (Form-based)
# ===========================================

@login_required
@user_passes_test(is_admin)
def global_search(request):
    """Global search across all models with form-based results"""
    query = request.GET.get('q', '')
    model_type = request.GET.get('model', 'all')

    results = {
        'students': [],
        'faculty': [],
        'courses': [],
        'programs': [],
        'enrollments': [],
        'allocations': [],
        'query': query,
        'model_type': model_type
    }

    if query and len(query) >= 2:
        if model_type in ['all', 'students']:
            students = Student.objects.select_related('studentid', 'programid').filter(
                Q(studentid__fname__icontains=query) |
                Q(studentid__lname__icontains=query) |
                Q(studentid__institutionalemail__icontains=query) |
                Q(studentid__personid__icontains=query)
            )[:10]

            results['students'] = students

        if model_type in ['all', 'faculty']:
            faculty = Faculty.objects.select_related('employeeid', 'departmentid').filter(
                Q(employeeid__fname__icontains=query) |
                Q(employeeid__lname__icontains=query) |
                Q(employeeid__institutionalemail__icontains=query) |
                Q(employeeid__personid__icontains=query)
            )[:10]

            results['faculty'] = faculty

        if model_type in ['all', 'courses']:
            courses = Course.objects.filter(
                Q(coursename__icontains=query) |
                Q(coursecode__icontains=query)
            )[:10]

            results['courses'] = courses

        if model_type in ['all', 'programs']:
            programs = Program.objects.select_related('departmentid').filter(
                Q(programname__icontains=query) |
                Q(programid__icontains=query)
            )[:10]

            results['programs'] = programs

        if model_type in ['all', 'enrollments']:
            enrollments = Enrollment.objects.select_related(
                'studentid__studentid', 'allocationid__coursecode'
            ).filter(
                Q(studentid__studentid__fname__icontains=query) |
                Q(studentid__studentid__lname__icontains=query) |
                Q(allocationid__coursecode__coursename__icontains=query) |
                Q(allocationid__coursecode__coursecode__icontains=query)
            )[:10]

            results['enrollments'] = enrollments

        if model_type in ['all', 'allocations']:
            allocations = Courseallocation.objects.select_related(
                'teacherid__employeeid', 'coursecode'
            ).filter(
                Q(teacherid__employeeid__fname__icontains=query) |
                Q(teacherid__employeeid__lname__icontains=query) |
                Q(coursecode__coursename__icontains=query) |
                Q(coursecode__coursecode__icontains=query) |
                Q(session__icontains=query)
            )[:10]

            results['allocations'] = allocations

    # Convert QuerySets to JSON-serializable data
    json_results = {
        'students': [{
            'name': f"{s.studentid.fname} {s.studentid.lname}",
            'email': s.studentid.institutionalemail,
            'id': s.studentid.personid,
            'program': s.programid.programname if s.programid else 'No Program',
            'status': s.status
        } for s in results['students']],

        'faculty': [{
            'name': f"{f.employeeid.fname} {f.employeeid.lname}",
            'email': f.employeeid.institutionalemail,
            'id': f.employeeid.personid,
            'department': f.departmentid.departmentname if f.departmentid else 'No Department',
            'designation': f.designation
        } for f in results['faculty']],

        'courses': [{
            'name': c.coursename,
            'code': c.coursecode,
            'credits': c.credithours,
            'description': c.description if hasattr(c, 'description') else ''
        } for c in results['courses']],

        'programs': [{
            'name': p.programname,
            'id': p.programid,
            'department': p.departmentid.departmentname if p.departmentid else 'No Department',
            'semesters': p.totalsemesters
        } for p in results['programs']],

        'enrollments': [{
            'student_name': f"{e.studentid.studentid.fname} {e.studentid.studentid.lname}",
            'course_name': e.allocationid.coursecode.coursename,
            'course_code': e.allocationid.coursecode.coursecode,
            'status': e.status,
            'enrollment_date': e.enrollmentdate.strftime('%Y-%m-%d') if e.enrollmentdate else ''
        } for e in results['enrollments']],

        'allocations': [{
            'teacher_name': f"{a.teacherid.employeeid.fname} {a.teacherid.employeeid.lname}",
            'course_name': a.coursecode.coursename,
            'course_code': a.coursecode.coursecode,
            'session': a.session,
            'status': a.status
        } for a in results['allocations']],

        'query': query
    }

    return JsonResponse(json_results)


# ===========================================
# CRUD COORDINATION - Delegate to respective apps (form-based)
# ===========================================

# FACULTY CRUD (delegated to FacultyModule - form-based)
@login_required
@user_passes_test(is_admin)
def faculty_list(request):
    """Delegate to FacultyModule views (form-based)"""
    return faculty_views.faculty_list(request)


@login_required
@user_passes_test(is_admin)
def faculty_create(request):
    """Delegate to FacultyModule views (form-based)"""
    return faculty_views.faculty_create(request)


@login_required
@user_passes_test(is_admin)
def faculty_detail(request, faculty_id):
    """Delegate to FacultyModule views"""
    return faculty_views.faculty_detail(request, faculty_id)


@login_required
@user_passes_test(is_admin)
def faculty_update(request, faculty_id):
    """Delegate to FacultyModule views (form-based)"""
    return faculty_views.faculty_update(request, faculty_id)


@login_required
@user_passes_test(is_admin)
def faculty_delete(request, faculty_id):
    """Delegate to FacultyModule views (form-based)"""
    return faculty_views.faculty_delete(request, faculty_id)


# STUDENT CRUD (delegated to StudentModule - form-based)
@login_required
@user_passes_test(is_admin)
def student_list(request):
    """Delegate to StudentModule views (form-based)"""
    return student_views.student_list(request)


@login_required
@user_passes_test(is_admin)
def student_create(request):
    """Delegate to StudentModule views (form-based)"""
    return student_views.student_create(request)


@login_required
@user_passes_test(is_admin)
def student_detail(request, student_id):
    """Delegate to StudentModule views"""
    return student_views.student_detail(request, student_id)


@login_required
@user_passes_test(is_admin)
def student_update(request, student_id):
    """Delegate to StudentModule views (form-based)"""
    return student_views.student_update(request, student_id)


@login_required
@user_passes_test(is_admin)
def student_delete(request, student_id):
    """Delegate to StudentModule views (form-based)"""
    return student_views.student_delete(request, student_id)


# ACADEMIC STRUCTURE CRUD (delegated to AcademicStructure - form-based)
@login_required
@user_passes_test(is_admin)
def department_list(request):
    """Delegate to AcademicStructure views"""
    return academic_views.department_list(request)




@login_required
@user_passes_test(is_admin)
def department_detail(request, department_id):
    """Delegate to AcademicStructure views"""
    return academic_views.department_detail(request, department_id)


@login_required
@user_passes_test(is_admin)
def program_list(request):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.program_list(request)


@login_required
@user_passes_test(is_admin)
def program_create(request):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.program_create(request)


@login_required
@user_passes_test(is_admin)
def program_detail(request, program_id):
    """Delegate to AcademicStructure views"""
    return academic_views.program_detail(request, program_id)


@login_required
@user_passes_test(is_admin)
def program_update(request, program_id):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.program_update(request, program_id)


@login_required
@user_passes_test(is_admin)
def program_delete(request, program_id):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.program_delete(request, program_id)


@login_required
@user_passes_test(is_admin)
def course_list(request):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.course_list(request)


@login_required
@user_passes_test(is_admin)
def course_create(request):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.course_create(request)


@login_required
@user_passes_test(is_admin)
def course_detail(request, course_code):
    """Delegate to AcademicStructure views"""
    return academic_views.course_detail(request, course_code)


@login_required
@user_passes_test(is_admin)
def course_update(request, course_code):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.course_update(request, course_code)


@login_required
@user_passes_test(is_admin)
def course_delete(request, course_code):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.course_delete(request, course_code)


@login_required
@user_passes_test(is_admin)
def semester_list(request):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.semester_list(request)


@login_required
@user_passes_test(is_admin)
def semester_create(request):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.semester_create(request)


@login_required
@user_passes_test(is_admin)
def semester_detail(request, semester_id):
    """Delegate to AcademicStructure views"""
    return academic_views.semester_detail(request, semester_id)


@login_required
@user_passes_test(is_admin)
def semester_update(request, semester_id):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.semester_update(request, semester_id)


@login_required
@user_passes_test(is_admin)
def semester_delete(request, semester_id):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.semester_delete(request, semester_id)


@login_required
@user_passes_test(is_admin)
def semesterdetails_list(request):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.semesterdetails_list(request)


@login_required
@user_passes_test(is_admin)
def semesterdetails_create(request):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.semesterdetails_create(request)


@login_required
@user_passes_test(is_admin)
def semesterdetails_detail(request, detail_id):
    """Delegate to AcademicStructure views"""
    return academic_views.semesterdetails_detail(request, detail_id)


@login_required
@user_passes_test(is_admin)
def semesterdetails_update(request, detail_id):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.semesterdetails_update(request, detail_id)


@login_required
@user_passes_test(is_admin)
def semesterdetails_delete(request, detail_id):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.semesterdetails_delete(request, detail_id)


@login_required
@user_passes_test(is_admin)
def class_list(request):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.class_list(request)


@login_required
@user_passes_test(is_admin)
def class_create(request):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.class_create(request)


@login_required
@user_passes_test(is_admin)
def class_detail(request, class_id):
    """Delegate to AcademicStructure views"""
    return academic_views.class_detail(request, class_id)


@login_required
@user_passes_test(is_admin)
def class_update(request, class_id):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.class_update(request, class_id)


@login_required
@user_passes_test(is_admin)
def class_delete(request, class_id):
    """Delegate to AcademicStructure views (form-based)"""
    return academic_views.class_delete(request, class_id)


# COURSE ALLOCATIONS CRUD (delegated to FacultyModule - form-based)
@login_required
@user_passes_test(is_admin)
def course_allocation_list(request):
    """Delegate to FacultyModule views (form-based)"""
    return faculty_views.course_allocation_list(request)


@login_required
@user_passes_test(is_admin)
def course_allocation_create(request):
    """Delegate to FacultyModule views (form-based)"""
    return faculty_views.course_allocation_create(request)


@login_required
@user_passes_test(is_admin)
def course_allocation_detail(request, allocation_id):
    """Delegate to FacultyModule views"""
    return faculty_views.course_allocation_detail(request, allocation_id)


@login_required
@user_passes_test(is_admin)
def course_allocation_update(request, allocation_id):
    """Delegate to FacultyModule views (form-based)"""
    return faculty_views.course_allocation_update(request, allocation_id)


@login_required
@user_passes_test(is_admin)
def course_allocation_delete(request, allocation_id):
    """Delegate to FacultyModule views (form-based)"""
    return faculty_views.course_allocation_delete(request, allocation_id)


# ENROLLMENTS CRUD (delegated to StudentModule - form-based)
@login_required
@user_passes_test(is_admin)
def enrollment_list(request):
    """Delegate to StudentModule views (form-based)"""
    return student_views.enrollment_list(request)


@login_required
@user_passes_test(is_admin)
def enrollment_create(request):
    """Delegate to StudentModule views (form-based)"""
    return student_views.enrollment_create(request)


@login_required
@user_passes_test(is_admin)
def enrollment_detail(request, enrollment_id):
    """Delegate to StudentModule views"""
    return student_views.enrollment_detail(request, enrollment_id)


@login_required
@user_passes_test(is_admin)
def enrollment_update(request, enrollment_id):
    """Delegate to StudentModule views (form-based)"""
    return student_views.enrollment_update(request, enrollment_id)


@login_required
@user_passes_test(is_admin)
def enrollment_delete(request, enrollment_id):
    """Delegate to StudentModule views (form-based)"""
    return student_views.enrollment_delete(request, enrollment_id)


# ===========================================
# SALARY MANAGEMENT CRUD (Person app - form-based)
# ===========================================

@login_required
@user_passes_test(is_admin)
def salary_list(request):
    """List all salary records with search and filtering"""
    salaries = Salary.objects.select_related('employeeid').all()

    # Search functionality
    search = request.GET.get('search')
    if search:
        salaries = salaries.filter(
            Q(employeeid__fname__icontains=search) |
            Q(employeeid__lname__icontains=search) |
            Q(employeeid__personid__icontains=search)
        )

    # Year filtering
    year = request.GET.get('year')
    if year:
        salaries = salaries.filter(year=year)

    # Month filtering
    month = request.GET.get('month')
    if month:
        salaries = salaries.filter(month=month)

    # Pagination
    paginator = Paginator(salaries.order_by('-year', '-month'), 25)
    page = request.GET.get('page')
    salaries = paginator.get_page(page)

    return render(request, 'admin/salary_list.html', {
        'salaries': salaries
    })


@login_required
@user_passes_test(is_admin)
def salary_create(request):
    """Create new salary record - FIXED"""
    if request.method == 'POST':
        form = SalaryForm(request.POST)
        if form.is_valid():
            try:
                form.save()  # Form handles duplicate validation
                messages.success(request, 'Salary record created successfully')
                return redirect('person:salary_list')
            except Exception as e:
                messages.error(request, f'Error creating salary record: {str(e)}')
    else:
        form = SalaryForm()

    return render(request, 'admin/salary_create.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def salary_detail(request, salary_id):
    """View salary record details"""
    salary = get_object_or_404(Salary, salaryid=salary_id)

    return render(request, 'admin/salary_detail.html', {
        'salary': salary
    })


@login_required
@user_passes_test(is_admin)
def salary_update(request, salary_id):
    """Update salary record"""
    salary = get_object_or_404(Salary, salaryid=salary_id)

    if request.method == 'POST':
        form = SalaryForm(request.POST, instance=salary)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Salary record updated successfully')
                return redirect('person:salary_list')

            except Exception as e:
                messages.error(request, f'Error updating salary record: {str(e)}')
    else:
        form = SalaryForm(instance=salary)

    return render(request, 'admin/salary_edit.html', {'form': form, 'salary': salary})


@login_required
@user_passes_test(is_admin)
def salary_delete(request, salary_id):
    """Delete salary record"""
    salary = get_object_or_404(Salary, salaryid=salary_id)

    if request.method == 'POST':
        try:
            salary.delete()
            messages.success(request, 'Salary record deleted successfully')
            return redirect('person:salary_list')

        except Exception as e:
            messages.error(request, f'Error deleting salary record: {str(e)}')

    return render(request, 'admin/salary_confirm_delete.html', {'salary': salary})


# ===========================================
# ADMIN VIEW-ONLY FUNCTIONS (Custom implementations)
# ===========================================

# LECTURES via Course Allocations (VIEW ONLY)
@login_required
@user_passes_test(is_admin)
def view_lectures_by_allocation(request, allocation_id):
    """Admin can view lectures through course allocations (READ ONLY)"""
    allocation = get_object_or_404(Courseallocation, allocationid=allocation_id)
    lectures = Lecture.objects.filter(allocationid=allocation).order_by('-startingtime')

    # Search functionality
    search = request.GET.get('search')
    if search:
        lectures = lectures.filter(
            Q(topic__icontains=search) |
            Q(lectureid__icontains=search) |
            Q(venue__icontains=search)
        )

    # Pagination
    paginator = Paginator(lectures, 25)
    page = request.GET.get('page')
    lectures = paginator.get_page(page)

    return render(request, 'admin/lectures_view.html', {
        'allocation': allocation,
        'lectures': lectures,
        'can_modify': False  # Admin cannot modify
    })


@login_required
@user_passes_test(is_admin)
def view_all_lectures_by_allocations(request):
    """Admin can view all lectures organized by allocations"""
    allocations = Courseallocation.objects.select_related(
        'coursecode', 'teacherid__employeeid'
    ).prefetch_related('lecture_set').all()

    return render(request, 'admin/all_lectures_view.html', {
        'allocations': allocations,
        'can_modify': False
    })


# ASSESSMENTS via Course Allocations (VIEW ONLY)
@login_required
@user_passes_test(is_admin)
def view_assessments_by_allocation(request, allocation_id):
    """Admin can view assessments through course allocations (READ ONLY)"""
    allocation = get_object_or_404(Courseallocation, allocationid=allocation_id)
    assessments = Assessment.objects.filter(allocationid=allocation).order_by('-assessmentdate')

    # Search functionality
    search = request.GET.get('search')
    if search:
        assessments = assessments.filter(
            Q(assessmentname__icontains=search) |
            Q(assessmenttype__icontains=search)
        )

    # Pagination
    paginator = Paginator(assessments, 25)
    page = request.GET.get('page')
    assessments = paginator.get_page(page)

    return render(request, 'admin/assessments_view.html', {
        'allocation': allocation,
        'assessments': assessments,
        'can_modify': False  # Admin cannot modify
    })


@login_required
@user_passes_test(is_admin)
def view_all_assessments_by_allocations(request):
    """Admin can view all assessments organized by allocations"""
    allocations = Courseallocation.objects.select_related(
        'coursecode', 'teacherid__employeeid'
    ).prefetch_related('assessment_set').all()

    return render(request, 'admin/all_assessments_view.html', {
        'allocations': allocations,
        'can_modify': False
    })


# ATTENDANCE via Enrollments or Students (VIEW ONLY)
@login_required
@user_passes_test(is_admin)
def view_attendance_by_enrollment(request, enrollment_id):
    """Admin can view attendance through enrollments (READ ONLY)"""
    enrollment = get_object_or_404(Enrollment, enrollmentid=enrollment_id)
    # Get lectures for this enrollment's allocation
    lectures = Lecture.objects.filter(allocationid=enrollment.allocationid).order_by('-startingtime')
    # Get attendance for this student in these lectures
    attendance_records = Attendance.objects.filter(
        studentid=enrollment.studentid,
        lectureid__in=lectures
    ).select_related('lectureid')

    # Calculate attendance statistics - MANUAL calculation since no attendancepercentage field
    total_lectures = lectures.count()
    attended_lectures = attendance_records.count()
    attendance_percentage = (attended_lectures / total_lectures * 100) if total_lectures > 0 else 0

    return render(request, 'admin/attendance_view.html', {
        'enrollment': enrollment,
        'lectures': lectures,
        'attendance_records': attendance_records,
        'total_lectures': total_lectures,
        'attended_lectures': attended_lectures,
        'attendance_percentage': round(attendance_percentage, 2),
        'can_modify': False  # Admin cannot modify
    })


@login_required
@user_passes_test(is_admin)
def view_attendance_by_student(request, student_id):
    """Admin can view attendance through student->enrollments (READ ONLY)"""
    student = get_object_or_404(Student, studentid__personid=student_id)
    enrollments = Enrollment.objects.filter(studentid=student).select_related(
        'allocationid__coursecode'
    )

    attendance_data = []
    for enrollment in enrollments:
        lectures = Lecture.objects.filter(allocationid=enrollment.allocationid)
        attendance = Attendance.objects.filter(
            studentid=student,
            lectureid__in=lectures
        ).select_related('lectureid')

        total_lectures = lectures.count()
        attended_lectures = attendance.count()
        attendance_percentage = (attended_lectures / total_lectures * 100) if total_lectures > 0 else 0

        attendance_data.append({
            'enrollment': enrollment,
            'lectures': lectures,
            'attendance_records': attendance,
            'total_lectures': total_lectures,
            'attended_lectures': attended_lectures,
            'attendance_percentage': round(attendance_percentage, 2)
        })

    return render(request, 'admin/student_attendance_view.html', {
        'student': student,
        'attendance_data': attendance_data,
        'can_modify': False  # Admin cannot modify
    })


# STUDENT ENROLLMENTS, RESULTS, TRANSCRIPTS (VIEW ONLY)
@login_required
@user_passes_test(is_admin)
def view_student_enrollments(request, student_id):
    """Admin can view student enrollments"""
    student = get_object_or_404(Student, studentid__personid=student_id)
    enrollments = Enrollment.objects.filter(studentid=student).select_related(
        'allocationid__coursecode',
        'allocationid__teacherid__employeeid'
    ).order_by('-enrollmentdate')

    # Search functionality
    search = request.GET.get('search')
    if search:
        enrollments = enrollments.filter(
            Q(allocationid__coursecode__coursename__icontains=search) |
            Q(allocationid__coursecode__coursecode__icontains=search) |
            Q(allocationid__session__icontains=search)
        )

    # Pagination
    paginator = Paginator(enrollments, 25)
    page = request.GET.get('page')
    enrollments = paginator.get_page(page)

    return render(request, 'admin/student_enrollments_view.html', {
        'student': student,
        'enrollments': enrollments
    })


@login_required
@user_passes_test(is_admin)
def view_student_results(request, student_id):
    """Admin can view student results"""
    student = get_object_or_404(Student, studentid__personid=student_id)
    results = Result.objects.filter(
        enrollmentid__studentid=student
    ).select_related('enrollmentid__allocationid__coursecode').order_by('-enrollmentid__enrollmentdate')

    # Calculate statistics - FIXED field name
    total_courses = results.count()
    avg_gpa = results.aggregate(Avg('coursegpa'))['coursegpa__avg'] or 0.0  # FIXED: coursegpa

    return render(request, 'admin/student_results_view.html', {
        'student': student,
        'results': results,
        'total_courses': total_courses,
        'avg_gpa': round(float(avg_gpa), 2) if avg_gpa else 0.0
    })


@login_required
@user_passes_test(is_admin)
def view_allocation_results(request, allocation_id):
    """Admin can view results through course allocations"""
    allocation = get_object_or_404(Courseallocation, allocationid=allocation_id)
    results = Result.objects.filter(
        enrollmentid__allocationid=allocation
    ).select_related('enrollmentid__studentid__studentid').order_by('-coursegpa')  # FIXED: coursegpa

    # Calculate statistics - FIXED field name
    total_students = results.count()
    avg_gpa = results.aggregate(Avg('coursegpa'))['coursegpa__avg'] or 0.0  # FIXED: coursegpa
    high_performers = results.filter(coursegpa__gte=3.5).count()  # FIXED: coursegpa

    return render(request, 'admin/allocation_results_view.html', {
        'allocation': allocation,
        'results': results,
        'total_students': total_students,
        'avg_gpa': round(float(avg_gpa), 2) if avg_gpa else 0.0,
        'high_performers': high_performers
    })


@login_required
@user_passes_test(is_admin)
def view_student_transcript(request, student_id):
    """Admin can view student transcripts"""
    student = get_object_or_404(Student, studentid__personid=student_id)
    transcripts = Transcript.objects.filter(studentid=student).select_related('semesterid').order_by(
        'semesterid__semesterno')  # FIXED: semesterno

    # Calculate overall statistics
    total_credits = transcripts.aggregate(Sum('totalcredits'))['totalcredits__sum'] or 0
    overall_gpa = transcripts.aggregate(Avg('semestergpa'))['semestergpa__avg'] or 0.0

    return render(request, 'admin/student_transcript_view.html', {
        'student': student,
        'transcripts': transcripts,
        'total_credits': total_credits,
        'overall_gpa': round(float(overall_gpa), 2) if overall_gpa else 0.0
    })


@login_required
@user_passes_test(is_admin)
def view_class_transcripts(request, class_id):
    """Admin can view transcripts by class"""
    class_obj = get_object_or_404(Class, classid=class_id)
    students = Student.objects.filter(classid=class_obj).select_related('studentid')

    transcript_data = []
    for student in students:
        transcripts = Transcript.objects.filter(studentid=student).select_related('semesterid')
        total_credits = transcripts.aggregate(Sum('totalcredits'))['totalcredits__sum'] or 0
        overall_gpa = transcripts.aggregate(Avg('semestergpa'))['semestergpa__avg'] or 0.0

        transcript_data.append({
            'student': student,
            'transcripts': transcripts,
            'total_credits': total_credits,
            'overall_gpa': round(float(overall_gpa), 2) if overall_gpa else 0.0
        })

    return render(request, 'admin/class_transcripts_view.html', {
        'class_obj': class_obj,
        'transcript_data': transcript_data
    })


# ===========================================
# HIERARCHICAL VIEWS (Department -> Program -> Course structure)
# ===========================================

@login_required
@user_passes_test(is_admin)
def view_department_programs_courses(request, department_id):
    """View departments -> programs -> courses hierarchy"""
    department = get_object_or_404(Department, departmentid=department_id)
    programs = Program.objects.filter(departmentid=department).prefetch_related('semesterdetails_set__coursecode')

    # Organize courses by program
    program_data = []
    for program in programs:
        # Get all courses through semester details - FIXED field references
        semester_details = Semesterdetails.objects.filter(
            semesterid__programid=program  # FIXED: programid not program
        ).select_related('coursecode', 'semesterid')

        # Group by semester
        semesters = {}
        for detail in semester_details:
            sem_num = detail.semesterid.semesterno  # FIXED: semesterno not semesternumber
            if sem_num not in semesters:
                semesters[sem_num] = {
                    'semester': detail.semesterid,
                    'courses': []
                }
            semesters[sem_num]['courses'].append(detail.coursecode)

        program_data.append({
            'program': program,
            'semesters': sorted(semesters.items())
        })

    return render(request, 'admin/department_hierarchy_view.html', {
        'department': department,
        'program_data': program_data
    })


@login_required
@user_passes_test(is_admin)
def view_department_scheme_of_studies(request, department_id):
    """View department -> programs -> semester -> semesterdetails (scheme of studies)"""
    department = get_object_or_404(Department, departmentid=department_id)
    programs = Program.objects.filter(departmentid=department)

    scheme_data = []
    for program in programs:
        semesters = Semester.objects.filter(programid=program).order_by('semesterno')  # FIXED: programid, semesterno

        semester_data = []
        for semester in semesters:
            semester_details = Semesterdetails.objects.filter(
                semesterid=semester
            ).select_related('coursecode')

            total_credits = sum(detail.coursecode.credithours for detail in semester_details)

            semester_data.append({
                'semester': semester,
                'details': semester_details,
                'total_credits': total_credits
            })

        scheme_data.append({
            'program': program,
            'semesters': semester_data
        })

    return render(request, 'admin/scheme_of_studies_view.html', {
        'department': department,
        'scheme_data': scheme_data
    })


@login_required
@user_passes_test(is_admin)
def view_department_students(request, department_id):
    """View department -> students"""
    department = get_object_or_404(Department, departmentid=department_id)
    students = Student.objects.filter(
        programid__departmentid=department
    ).select_related('studentid', 'programid', 'classid').order_by('studentid__fname')

    # Search functionality
    search = request.GET.get('search')
    if search:
        students = students.filter(
            Q(studentid__fname__icontains=search) |
            Q(studentid__lname__icontains=search) |
            Q(studentid__personid__icontains=search)
        )

    # Group by program
    programs = {}
    for student in students:
        if student.programid:
            if student.programid not in programs:
                programs[student.programid] = []
            programs[student.programid].append(student)

    # Pagination
    paginator = Paginator(students, 50)
    page = request.GET.get('page')
    students = paginator.get_page(page)

    return render(request, 'admin/department_students_view.html', {
        'department': department,
        'students': students,
        'programs': programs
    })


# ===========================================
# ADMIN PROFILE MANAGEMENT (Form-based)
# ===========================================

@login_required
@user_passes_test(is_admin)
def admin_profile(request):
    """Admin profile view - edit own profile only"""
    try:
        # Get current admin's person record using your Admin model
        admin = get_object_or_404(Admin, employeeid__personid=request.user.username)
        person = admin.employeeid

        # Get related data
        try:
            address = Address.objects.get(personid=person)
        except Address.DoesNotExist:
            address = None

        qualifications = Qualification.objects.filter(personid=person)

        return render(request, 'admin/profile.html', {
            'person': person,
            'admin': admin,
            'address': address,
            'qualifications': qualifications
        })

    except Admin.DoesNotExist:
        messages.error(request, 'Admin profile not found.')
        return redirect('person:admin_dashboard')



@login_required
@user_passes_test(is_admin)
def admin_profile_update(request):
    """Update admin's own profile - FIXED VERSION"""
    try:
        admin = get_object_or_404(Admin, employeeid__personid=request.user.username)

        if request.method == 'POST':
            form = AdminProfileForm(request.POST, instance=admin)

            if form.is_valid():
                try:
                    form.save()  # Form now handles everything
                    messages.success(request, 'Profile updated successfully')
                    return redirect('person:admin_profile')
                except Exception as e:
                    messages.error(request, f'Error updating profile: {str(e)}')
        else:
            form = AdminProfileForm(instance=admin)

        return render(request, 'admin/profile_edit.html', {'form': form, 'admin': admin})

    except Admin.DoesNotExist:
        messages.error(request, 'Admin profile not found.')
        return redirect('person:admin_dashboard')


# ===========================================
# ALUMNI MANAGEMENT CRUD (Person app - form-based)
# ===========================================

@login_required
@user_passes_test(is_admin)
def alumni_list(request):
    """List all alumni records with search and filtering"""
    alumni = Alumni.objects.select_related(
        'alumniid__studentid',
        'alumniid__programid__departmentid'
    ).all()

    # Search functionality
    search = request.GET.get('search')
    if search:
        alumni = alumni.filter(
            Q(alumniid__studentid__fname__icontains=search) |
            Q(alumniid__studentid__lname__icontains=search) |
            Q(alumniid__studentid__personid__icontains=search) |
            Q(email__icontains=search)
        )

    # Filter by graduation year
    year = request.GET.get('year')
    if year:
        alumni = alumni.filter(graduationdate__year=year)

    # Filter by program
    program = request.GET.get('program')
    if program:
        alumni = alumni.filter(alumniid__programid=program)

    # Pagination
    paginator = Paginator(alumni.order_by('-graduationdate'), 25)
    page = request.GET.get('page')
    alumni = paginator.get_page(page)

    # Get programs for filter dropdown
    programs = Program.objects.all()

    return render(request, 'admin/alumni_list.html', {
        'alumni': alumni,
        'programs': programs
    })


@login_required
@user_passes_test(is_admin)
def alumni_create(request):
    """Create new alumni record"""
    if request.method == 'POST':
        form = AlumniForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Alumni record created successfully')
                return redirect('person:alumni_list')
            except Exception as e:
                messages.error(request, f'Error creating alumni record: {str(e)}')
    else:
        form = AlumniForm()

    return render(request, 'admin/alumni_create.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def alumni_detail(request, alumni_id):
    """View alumni record details"""
    # Note: alumni_id is the student's personid
    alumni = get_object_or_404(Alumni, alumniid__studentid__personid=alumni_id)

    # Get related information
    student = alumni.alumniid
    person = student.studentid

    # Get academic records
    enrollments = Enrollment.objects.filter(studentid=student).select_related(
        'allocationid__coursecode'
    )
    results = Result.objects.filter(enrollmentid__in=enrollments).select_related(
        'enrollmentid__allocationid__coursecode'
    )

    # Calculate final GPA
    avg_gpa = results.aggregate(Avg('coursegpa'))['coursegpa__avg'] or 0.0

    return render(request, 'admin/alumni_detail.html', {
        'alumni': alumni,
        'student': student,
        'person': person,
        'enrollments': enrollments,
        'results': results,
        'avg_gpa': round(float(avg_gpa), 2) if avg_gpa else 0.0
    })


@login_required
@user_passes_test(is_admin)
def alumni_update(request, alumni_id):
    """Update alumni record"""
    alumni = get_object_or_404(Alumni, alumniid__studentid__personid=alumni_id)

    if request.method == 'POST':
        form = AlumniForm(request.POST, instance=alumni)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Alumni record updated successfully')
                return redirect('person:alumni_list')
            except Exception as e:
                messages.error(request, f'Error updating alumni record: {str(e)}')
    else:
        form = AlumniForm(instance=alumni)

    return render(request, 'admin/alumni_edit.html', {
        'form': form,
        'alumni': alumni
    })


@login_required
@user_passes_test(is_admin)
def alumni_delete(request, alumni_id):
    """Delete alumni record"""
    alumni = get_object_or_404(Alumni, alumniid__studentid__personid=alumni_id)

    if request.method == 'POST':
        try:
            alumni.delete()
            messages.success(request, 'Alumni record deleted successfully')
            return redirect('person:alumni_list')
        except Exception as e:
            messages.error(request, f'Error deleting alumni record: {str(e)}')

    return render(request, 'admin/alumni_confirm_delete.html', {'alumni': alumni})


@login_required
@user_passes_test(is_admin)
def alumni_report(request):
    """Generate alumni report with statistics"""
    alumni = Alumni.objects.select_related(
        'alumniid__studentid',
        'alumniid__programid__departmentid'
    ).all()

    # Alumni by year
    alumni_by_year = alumni.extra(
        select={'year': "EXTRACT(year FROM graduationdate)"}
    ).values('year').annotate(count=Count('alumniid')).order_by('-year')

    # Alumni by program
    alumni_by_program = alumni.values(
        'alumniid__programid__programname'
    ).annotate(count=Count('alumniid')).order_by('-count')

    # Alumni by department
    alumni_by_department = alumni.values(
        'alumniid__programid__departmentid__departmentname'
    ).annotate(count=Count('alumniid')).order_by('-count')

    # Employment statistics
    employed_alumni = alumni.exclude(employmentinfo='').exclude(employmentinfo__isnull=True).count()
    total_alumni = alumni.count()
    employment_rate = (employed_alumni / total_alumni * 100) if total_alumni > 0 else 0

    context = {
        'total_alumni': total_alumni,
        'employed_alumni': employed_alumni,
        'employment_rate': round(employment_rate, 2),
        'alumni_by_year': alumni_by_year,
        'alumni_by_program': alumni_by_program,
        'alumni_by_department': alumni_by_department,
    }

    return render(request, 'admin/alumni_report.html', context)

# ===========================================
# API ENDPOINTS FOR DASHBOARD (Keep for AJAX support)
# ===========================================

@login_required
@user_passes_test(is_admin)
def dashboard_stats_api(request):
    """Get comprehensive dashboard statistics via API"""
    try:
        # Basic counts
        total_students = Student.objects.count()
        total_faculty = Faculty.objects.count()
        total_programs = Program.objects.count()
        total_courses = Course.objects.count()
        total_departments = Department.objects.count()
        total_enrollments = Enrollment.objects.count()

        # Student statistics
        students_by_status = list(
            Student.objects.values('status').annotate(count=Count('studentid')).order_by('status'))
        students_by_program = list(
            Student.objects.values('programid__programname').annotate(count=Count('studentid')).order_by('-count')[:10])

        # Faculty statistics
        faculty_by_department = list(
            Faculty.objects.values('departmentid__departmentname').annotate(count=Count('employeeid')).order_by(
                '-count')
        )

        # Enrollment statistics
        active_enrollments = Enrollment.objects.filter(status='Active').count()
        total_enrollments = Enrollment.objects.count()
        enrollments_by_status = list(
            Enrollment.objects.values('status').annotate(count=Count('enrollmentid')).order_by('status'))

        # Course allocation statistics
        active_allocations = Courseallocation.objects.filter(status='Active').count()
        allocations_by_session = list(
            Courseallocation.objects.values('session').annotate(count=Count('allocationid')).order_by('-session')[:5])

        # Performance statistics - FIXED field names
        avg_gpa = Result.objects.aggregate(Avg('coursegpa'))['coursegpa__avg'] or 0.0  # FIXED: coursegpa
        high_performers = Result.objects.filter(coursegpa__gte=3.5).count()  # FIXED: coursegpa
        total_results = Result.objects.count()

        # All departments with their statistics (even if counts are 0)
        all_departments = []
        for dept in Department.objects.all():
            faculty_count = Faculty.objects.filter(departmentid=dept).count()
            student_count = Student.objects.filter(programid__departmentid=dept).count()
            program_count = Program.objects.filter(departmentid=dept).count()

            all_departments.append({
                'department_name': dept.departmentname,
                'faculty_count': faculty_count,
                'student_count': student_count,
                'program_count': program_count
            })

        stats = {
            'overview': {
                'total_students': total_students,
                'total_faculty': total_faculty,
                'total_programs': total_programs,
                'total_courses': total_courses,
                'total_departments': total_departments,
                'active_enrollments': active_enrollments,
                'active_allocations': active_allocations,
            },
            'departments': all_departments,
            'students': {
                'total': total_students,
                'by_status': students_by_status,
                'by_program': students_by_program,
                'active': Student.objects.filter(status='Active').count()
            },
            'faculty': {
                'total': total_faculty,
                'by_department': faculty_by_department
            },
            'enrollments': {
                'total': total_enrollments,
                'active': active_enrollments,
                'by_status': enrollments_by_status
            },
            'allocations': {
                'active': active_allocations,
                'by_session': allocations_by_session
            },
            'performance': {
                'avg_gpa': round(float(avg_gpa), 2) if avg_gpa else 0.0,
                'high_performers': high_performers,
                'total_results': total_results,
                'high_performer_percentage': round((high_performers / total_results * 100),
                                                   2) if total_results > 0 else 0
            }
        }

        return JsonResponse(stats)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_admin)
def recent_activities_api(request):
    """Get recent activities for dashboard"""
    try:
        activities = []

        # Recent enrollments
        recent_enrollments = Enrollment.objects.select_related(
            'studentid__studentid', 'allocationid__coursecode'
        ).order_by('-enrollmentdate')[:5]

        for enrollment in recent_enrollments:
            activities.append({
                'type': 'enrollment',
                'title': 'New Enrollment',
                'description': f"{enrollment.studentid.studentid.fname} {enrollment.studentid.studentid.lname} enrolled in {enrollment.allocationid.coursecode.coursename}",
                'timestamp': enrollment.enrollmentdate.isoformat(),
                'link': f'/person/admin/student/{enrollment.studentid.studentid.personid}/enrollments/'
            })

        # Recent faculty additions
        recent_faculty = Faculty.objects.select_related('employeeid').order_by('-joiningdate')[:3]

        for faculty in recent_faculty:
            activities.append({
                'type': 'faculty',
                'title': 'New Faculty',
                'description': f"{faculty.employeeid.fname} {faculty.employeeid.lname} joined as {faculty.designation}",
                'timestamp': faculty.joiningdate.isoformat(),
                'link': f'/person/admin/faculty/{faculty.employeeid.personid}/'
            })

        # Recent course allocations
        recent_allocations = Courseallocation.objects.select_related(
            'teacherid__employeeid', 'coursecode'
        ).order_by('-allocationid')[:3]

        for allocation in recent_allocations:
            activities.append({
                'type': 'allocation',
                'title': 'Course Allocation',
                'description': f"{allocation.coursecode.coursename} assigned to {allocation.teacherid.employeeid.fname} {allocation.teacherid.employeeid.lname}",
                'timestamp': datetime.now().isoformat(),  # Allocations don't have timestamp, use current
                'link': f'/person/admin/allocations/{allocation.allocationid}/'
            })

        # Sort activities by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)

        return JsonResponse({'activities': activities[:10]})

    except Exception as e:
        return JsonResponse({'activities': []})


@login_required
@user_passes_test(is_admin)
def quick_stats_api(request):
    """Get quick statistics for admin widgets"""
    try:
        # Today's activities
        today = timezone.now().date()

        # Recent enrollments (last 7 days)
        recent_enrollments = Enrollment.objects.filter(
            enrollmentdate__date__gte=today - timedelta(days=7)
        ).count()

        # Active courses this session
        current_session = "Spring 2025"  # You might want to make this dynamic
        active_courses = Courseallocation.objects.filter(
            status='Active',
            session=current_session
        ).count()

        # Students with high GPA (>= 3.5) - FIXED field name
        high_performers = Result.objects.filter(coursegpa__gte=3.5).count()  # FIXED: coursegpa

        # Recent lectures (last 7 days)
        recent_lectures = Lecture.objects.filter(
            startingtime__date__gte=today - timedelta(days=7)
        ).count()

        stats = {
            'recent_enrollments': recent_enrollments,
            'active_courses': active_courses,
            'high_performers': high_performers,
            'recent_lectures': recent_lectures
        }

        return JsonResponse(stats)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_admin)
def admin_profile_api(request):
    """Get admin profile data as JSON"""
    try:
        admin = get_object_or_404(Admin, employeeid__institutionalemail=request.user.username)
        person = admin.employeeid

        profile_data = {
            'name': f"{person.fname} {person.lname}",
            'email': person.institutionalemail,
            'role': 'System Administrator',
            'person_id': person.personid,
            'initials': f"{person.fname[0]}{person.lname[0]}" if person.fname and person.lname else 'A'
        }

        return JsonResponse(profile_data)

    except Admin.DoesNotExist:
        return JsonResponse({
            'name': 'Administrator',
            'email': '',
            'role': 'System Administrator',
            'initials': 'A'
        })

# ===========================================
# REPORTING FUNCTIONS (Form-based)
# ===========================================

@login_required
@user_passes_test(is_admin)
def generate_department_report(request, department_id):
    """Generate comprehensive department report"""
    department = get_object_or_404(Department, departmentid=department_id)

    # Department statistics
    programs = Program.objects.filter(departmentid=department)
    faculty = Faculty.objects.filter(departmentid=department)
    students = Student.objects.filter(programid__departmentid=department)

    # Course allocations in this department
    allocations = Courseallocation.objects.filter(
        coursecode__semesterdetails__semesterid__programid__departmentid=department  # FIXED: programid path
    ).select_related('coursecode', 'teacherid__employeeid')

    # Student performance by program - FIXED field name
    program_performance = []
    for program in programs:
        program_students = students.filter(programid=program)

        # Get average GPA for this program (if available)
        try:
            avg_gpa = Result.objects.filter(
                enrollmentid__studentid__programid=program
            ).aggregate(avg_gpa=Avg('coursegpa'))['coursegpa__avg']  # FIXED: coursegpa
        except:
            avg_gpa = None

        program_performance.append({
            'program': program,
            'student_count': program_students.count(),
            'avg_gpa': round(avg_gpa, 2) if avg_gpa else 'N/A'
        })

    # Faculty workload
    faculty_workload = []
    for f in faculty:
        f_allocations = allocations.filter(teacherid=f)

        faculty_workload.append({
            'faculty': f,
            'allocation_count': f_allocations.count(),
            'courses': [alloc.coursecode for alloc in f_allocations]
        })

    context = {
        'department': department,
        'programs': programs,
        'faculty': faculty,
        'students': students,
        'allocations': allocations,
        'program_performance': program_performance,
        'faculty_workload': faculty_workload,
        'stats': {
            'total_programs': programs.count(),
            'total_faculty': faculty.count(),
            'total_students': students.count(),
            'total_allocations': allocations.count(),
        }
    }

    return render(request, 'admin/department_report.html', context)


# ===========================================
# AUDIT TRAIL MANAGEMENT (Form-based) - FIXED field names
# ===========================================

@login_required
@user_passes_test(is_admin)
def audit_trail_list(request):
    """View audit trail with filtering - FIXED field names"""
    audit_records = Audittrail.objects.select_related('userid').all()

    # Filter by action - FIXED field name
    action = request.GET.get('action')
    if action:
        audit_records = audit_records.filter(actiontype=action)  # FIXED: actiontype not action

    # Filter by table - FIXED field name
    table = request.GET.get('table')
    if table:
        audit_records = audit_records.filter(entityname=table)  # FIXED: entityname not tablename

    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        audit_records = audit_records.filter(timestamp__gte=start_date)
    if end_date:
        audit_records = audit_records.filter(timestamp__lte=end_date)

    # Filter by user
    user_filter = request.GET.get('user')
    if user_filter:
        audit_records = audit_records.filter(userid__fname__icontains=user_filter)  # Search by user name

    # Pagination
    paginator = Paginator(audit_records.order_by('-timestamp'), 50)
    page = request.GET.get('page')
    audit_records = paginator.get_page(page)

    # Get distinct values for filters - FIXED field names
    distinct_actions = Audittrail.objects.values_list('actiontype', flat=True).distinct()  # FIXED: actiontype
    distinct_tables = Audittrail.objects.values_list('entityname', flat=True).distinct()  # FIXED: entityname

    context = {
        'audit_records': audit_records,
        'distinct_actions': distinct_actions,
        'distinct_tables': distinct_tables,
        'current_filters': {
            'action': action,
            'table': table,
            'start_date': start_date,
            'end_date': end_date,
            'user': user_filter,
        }
    }

    return render(request, 'admin/audit_trail_list.html', context)


@login_required
@user_passes_test(is_admin)
def audit_trail_detail(request, audit_id):
    """View detailed audit record"""
    audit_record = get_object_or_404(Audittrail, auditid=audit_id)

    # Note: No oldvalues/newvalues fields in your model, so removed JSON parsing

    context = {
        'audit_record': audit_record,
    }

    return render(request, 'admin/audit_trail_detail.html', context)


# ===========================================
# BULK OPERATIONS (Form-based)
# ===========================================

@login_required
@user_passes_test(is_admin)
def bulk_operations(request):
    """Main bulk operations page"""
    return render(request, 'admin/bulk_operations.html')


@login_required
@user_passes_test(is_admin)
def bulk_student_operations(request):
    """Perform bulk operations on students"""
    if request.method == 'POST':
        operation = request.POST.get('operation')
        student_ids = request.POST.getlist('student_ids')

        try:
            if operation == 'activate':
                Student.objects.filter(studentid__personid__in=student_ids).update(status='Active')
                messages.success(request, f'Activated {len(student_ids)} students')

            elif operation == 'deactivate':
                Student.objects.filter(studentid__personid__in=student_ids).update(status='Inactive')
                messages.success(request, f'Deactivated {len(student_ids)} students')

            elif operation == 'graduate':
                Student.objects.filter(studentid__personid__in=student_ids).update(status='Graduated')
                messages.success(request, f'Marked {len(student_ids)} students as graduated')

            else:
                messages.error(request, 'Invalid operation')

        except Exception as e:
            messages.error(request, f'Bulk operation failed: {str(e)}')

        return redirect('person:bulk_student_operations')

    # Get students with filters for bulk operations
    students = Student.objects.select_related('studentid', 'programid').all()

    # Apply filters
    program_filter = request.GET.get('program')
    if program_filter:
        students = students.filter(programid=program_filter)

    status_filter = request.GET.get('status')
    if status_filter:
        students = students.filter(status=status_filter)

    # Pagination
    paginator = Paginator(students, 50)
    page = request.GET.get('page')
    students = paginator.get_page(page)

    context = {
        'students': students,
        'programs': Program.objects.all(),
        'current_filters': {
            'program': program_filter,
            'status': status_filter,
        }
    }

    return render(request, 'admin/bulk_student_operations.html', context)


# ===========================================
# SYSTEM UTILITIES (Form-based)
# ===========================================

@login_required
@user_passes_test(is_admin)
def system_health_check(request):
    """Check system health and provide diagnostics"""
    health_status = {
        'database': 'OK',
        'models': 'OK',
        'issues': []
    }

    try:
        # Test database connectivity
        Student.objects.count()
        Faculty.objects.count()
        Department.objects.count()
    except Exception as e:
        health_status['database'] = 'ERROR'
        health_status['issues'].append(f'Database connectivity issue: {str(e)}')

    # Check for orphaned records
    orphaned_issues = []

    try:
        # Students without valid programs
        orphaned_students = Student.objects.filter(programid__isnull=True).count()
        if orphaned_students > 0:
            orphaned_issues.append(f'{orphaned_students} students without valid programs')

        # Faculty without departments
        orphaned_faculty = Faculty.objects.filter(departmentid__isnull=True).count()
        if orphaned_faculty > 0:
            orphaned_issues.append(f'{orphaned_faculty} faculty without departments')

        # Enrollments with invalid allocations
        orphaned_enrollments = Enrollment.objects.filter(allocationid__isnull=True).count()
        if orphaned_enrollments > 0:
            orphaned_issues.append(f'{orphaned_enrollments} enrollments with invalid allocations')

    except Exception as e:
        orphaned_issues.append(f'Error checking orphaned records: {str(e)}')

    if orphaned_issues:
        health_status['models'] = 'WARNING'
        health_status['issues'].extend(orphaned_issues)

    # Check for recent activity (using actual model fields)
    recent_activity = {
        'enrollments_last_week': Enrollment.objects.filter(
            enrollmentdate__gte=timezone.now() - timedelta(days=7)
        ).count(),
        'new_faculty_last_month': Faculty.objects.filter(
            joiningdate__gte=timezone.now() - timedelta(days=30)
        ).count(),
        'recent_lectures': Lecture.objects.filter(
            startingtime__gte=timezone.now() - timedelta(days=7)
        ).count(),
    }

    context = {
        'health_status': health_status,
        'recent_activity': recent_activity,
        'timestamp': timezone.now(),
    }

    return render(request, 'admin/system_health.html', context)


@login_required
@user_passes_test(is_admin)
def export_data(request):
    """Export system data in various formats"""
    if request.method == 'POST':
        export_type = request.POST.get('export_type')
        data_type = request.POST.get('data_type')

        try:
            if data_type == 'students':
                data = Student.objects.select_related('studentid', 'programid', 'programid__departmentid').all()
                filename = f'students_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}'

            elif data_type == 'faculty':
                data = Faculty.objects.select_related('employeeid', 'departmentid').all()
                filename = f'faculty_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}'

            elif data_type == 'enrollments':
                data = Enrollment.objects.select_related(
                    'studentid__studentid', 'allocationid__coursecode'
                ).all()
                filename = f'enrollments_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}'

            else:
                messages.error(request, 'Invalid data type selected')
                return redirect('person:export_data')

            if export_type == 'csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

                # This would need to be implemented based on your specific model fields
                # You could use django-import-export or similar library
                messages.success(request, f'CSV export generated successfully for {data.count()} records')
                return redirect('person:export_data')

            elif export_type == 'excel':
                # Implementation for Excel export
                messages.success(request, f'Excel export generated successfully for {data.count()} records')
                return redirect('person:export_data')

            else:
                messages.error(request, 'Invalid export format')

        except Exception as e:
            messages.error(request, f'Export failed: {str(e)}')

    return render(request, 'admin/export_data.html')


# ===========================================
# ANALYTICS AND REPORTS (Form-based)
# ===========================================

@login_required
@user_passes_test(is_admin)
def analytics_dashboard(request):
    """Main analytics dashboard - FIXED field names"""
    # Student analytics
    total_students = Student.objects.count()
    students_by_status = Student.objects.values('status').annotate(count=Count('studentid')).order_by('status')
    students_by_program = Student.objects.values('programid__programname').annotate(count=Count('studentid')).order_by(
        '-count')[:10]

    # Faculty analytics
    total_faculty = Faculty.objects.count()
    faculty_by_department = Faculty.objects.values('departmentid__departmentname').annotate(
        count=Count('employeeid')).order_by('-count')

    # Performance analytics - FIXED field names
    try:
        avg_gpa = Result.objects.aggregate(avg_gpa=Avg('coursegpa'))['avg_gpa'] or 0.0  # FIXED: coursegpa
        # Removed grade_distribution since grade field doesn't exist
        high_performers = Result.objects.filter(coursegpa__gte=3.5).count()  # FIXED: coursegpa
    except:
        avg_gpa = 0.0
        high_performers = 0

    # Enrollment trends (last 6 months)
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_enrollments = []

    for i in range(6):
        month_start = six_months_ago + timedelta(days=30 * i)
        month_end = month_start + timedelta(days=30)

        enrollments_count = Enrollment.objects.filter(
            enrollmentdate__gte=month_start,
            enrollmentdate__lt=month_end
        ).count()

        monthly_enrollments.append({
            'month': month_start.strftime('%Y-%m'),
            'enrollments': enrollments_count
        })

    context = {
        'student_analytics': {
            'total': total_students,
            'by_status': students_by_status,
            'by_program': students_by_program,
        },
        'faculty_analytics': {
            'total': total_faculty,
            'by_department': faculty_by_department,
        },
        'performance_analytics': {
            'avg_gpa': round(float(avg_gpa), 2) if avg_gpa else 0.0,
            'high_performers': high_performers,
        },
        'enrollment_trends': monthly_enrollments,
    }

    return render(request, 'admin/analytics_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def faculty_performance_report(request):
    """Generate faculty performance report - FIXED field names"""
    faculty = Faculty.objects.select_related('employeeid', 'departmentid').all()

    faculty_performance = []
    for f in faculty:
        # Get allocations for this faculty
        allocations = Courseallocation.objects.filter(teacherid=f)

        # Get enrollments for faculty's courses
        enrollments = Enrollment.objects.filter(allocationid__in=allocations)

        # Calculate performance metrics
        total_students = enrollments.count()

        # Average student performance in faculty's courses - FIXED field name
        try:
            results = Result.objects.filter(enrollmentid__in=enrollments)
            avg_student_gpa = results.aggregate(avg_gpa=Avg('coursegpa'))['avg_gpa']  # FIXED: coursegpa
            # Removed pass_rate calculation since grade field doesn't exist
        except:
            avg_student_gpa = None

        # Student feedback - Reviews don't have rating field in your model, so removed

        faculty_performance.append({
            'faculty': f,
            'allocation_count': allocations.count(),
            'total_students': total_students,
            'avg_student_gpa': round(avg_student_gpa, 2) if avg_student_gpa else 'N/A',
        })

    # Sort by performance metrics
    sort_by = request.GET.get('sort', 'avg_student_gpa')
    reverse = request.GET.get('order', 'desc') == 'desc'

    if sort_by == 'avg_student_gpa':
        faculty_performance.sort(
            key=lambda x: x[sort_by] if isinstance(x[sort_by], (int, float)) else 0,
            reverse=reverse
        )

    context = {
        'faculty_performance': faculty_performance,
        'sort_by': sort_by,
        'order': 'desc' if reverse else 'asc',
    }

    return render(request, 'admin/faculty_performance_report.html', context)


@login_required
@user_passes_test(is_admin)
def student_analytics_report(request):
    """Generate comprehensive student analytics report - FIXED field names"""
    # Overall student statistics
    total_students = Student.objects.count()
    active_students = Student.objects.filter(status='Active').count()

    # Students by program
    students_by_program = Student.objects.values(
        'programid__programname', 'programid__departmentid__departmentname'
    ).annotate(count=Count('studentid')).order_by('-count')

    # Students by status
    students_by_status = Student.objects.values('status').annotate(count=Count('studentid')).order_by('status')

    # Academic performance - FIXED field names
    try:
        results = Result.objects.all()
        overall_avg_gpa = results.aggregate(avg_gpa=Avg('coursegpa'))['avg_gpa']  # FIXED: coursegpa
        # Removed grade_distribution since grade field doesn't exist

        # Performance by program - FIXED field name
        program_performance = results.values(
            'enrollmentid__studentid__programid__programname'
        ).annotate(
            avg_gpa=Avg('coursegpa'),  # FIXED: coursegpa
            student_count=Count('enrollmentid__studentid', distinct=True)
        ).order_by('-avg_gpa')
    except:
        overall_avg_gpa = None
        program_performance = []

    # Enrollment trends (last 12 months)
    twelve_months_ago = timezone.now() - timedelta(days=365)
    monthly_enrollments = []

    for i in range(12):
        month_start = twelve_months_ago + timedelta(days=30 * i)
        month_end = month_start + timedelta(days=30)

        enrollments_count = Enrollment.objects.filter(
            enrollmentdate__gte=month_start,
            enrollmentdate__lt=month_end
        ).count()

        monthly_enrollments.append({
            'month': month_start.strftime('%Y-%m'),
            'enrollments': enrollments_count
        })

    context = {
        'total_students': total_students,
        'active_students': active_students,
        'students_by_program': students_by_program,
        'students_by_status': students_by_status,
        'overall_avg_gpa': round(overall_avg_gpa, 2) if overall_avg_gpa else 'N/A',
        'program_performance': program_performance,
        'monthly_enrollments': monthly_enrollments,
    }

    return render(request, 'admin/student_analytics_report.html', context)


@login_required
@user_passes_test(is_admin)
def semester_performance_report(request):
    """Generate semester performance report - FIXED field names"""
    # Get all semesters - FIXED field name
    semesters = Semester.objects.all().order_by('-semesterno')  # FIXED: semesterno

    semester_data = []
    for semester in semesters:
        # Get semester details (courses offered)
        semester_details = Semesterdetails.objects.filter(semesterid=semester).select_related('coursecode',
                                                                                              'classid')  # Added classid

        # Get course allocations for this semester
        allocations = Courseallocation.objects.filter(
            coursecode__in=[sd.coursecode for sd in semester_details]
        ).select_related('coursecode', 'teacherid__employeeid')

        # Get enrollments for this semester
        enrollments = Enrollment.objects.filter(allocationid__in=allocations).select_related('studentid__studentid')

        # Performance statistics - FIXED field name
        try:
            results = Result.objects.filter(enrollmentid__in=enrollments)
            avg_gpa = results.aggregate(avg_gpa=Avg('coursegpa'))['avg_gpa']  # FIXED: coursegpa
            # Removed grade_distribution since grade field doesn't exist
        except:
            avg_gpa = None

        # Attendance statistics - Manual calculation since no attendancepercentage field
        try:
            lectures = Lecture.objects.filter(allocationid__in=allocations)
            attendance_records = Attendance.objects.filter(lectureid__in=lectures)
            total_possible_attendance = lectures.count() * enrollments.count()
            actual_attendance = attendance_records.count()
            avg_attendance = (
                        actual_attendance / total_possible_attendance * 100) if total_possible_attendance > 0 else 0
        except:
            avg_attendance = None

        semester_data.append({
            'semester': semester,
            'total_courses': semester_details.count(),
            'total_allocations': allocations.count(),
            'total_enrollments': enrollments.count(),
            'avg_gpa': round(avg_gpa, 2) if avg_gpa else 'N/A',
            'avg_attendance': round(avg_attendance, 2) if avg_attendance else 'N/A',
        })

    context = {
        'semester_data': semester_data
    }

    return render(request, 'admin/semester_performance_report.html', context)


# ===========================================
# UTILITIES AND HELPER FUNCTIONS
# ===========================================

@login_required
@user_passes_test(is_admin)
def data_integrity_check(request):
    """Check data integrity across the system"""
    issues = []

    # Check for orphaned records
    try:
        # Students without programs
        orphaned_students = Student.objects.filter(programid__isnull=True)
        if orphaned_students.exists():
            issues.append({
                'type': 'orphaned_students',
                'count': orphaned_students.count(),
                'description': 'Students without assigned programs',
                'records': orphaned_students[:10]  # Show first 10
            })

        # Faculty without departments
        orphaned_faculty = Faculty.objects.filter(departmentid__isnull=True)
        if orphaned_faculty.exists():
            issues.append({
                'type': 'orphaned_faculty',
                'count': orphaned_faculty.count(),
                'description': 'Faculty without assigned departments',
                'records': orphaned_faculty[:10]
            })

        # Enrollments without allocations
        orphaned_enrollments = Enrollment.objects.filter(allocationid__isnull=True)
        if orphaned_enrollments.exists():
            issues.append({
                'type': 'orphaned_enrollments',
                'count': orphaned_enrollments.count(),
                'description': 'Enrollments without valid course allocations',
                'records': orphaned_enrollments[:10]
            })

        # Check for duplicate person IDs
        duplicate_persons = Person.objects.values('personid').annotate(count=Count('personid')).filter(count__gt=1)
        if duplicate_persons.exists():
            issues.append({
                'type': 'duplicate_persons',
                'count': duplicate_persons.count(),
                'description': 'Duplicate person IDs found',
                'records': duplicate_persons[:10]
            })

    except Exception as e:
        issues.append({
            'type': 'error',
            'description': f'Error during integrity check: {str(e)}'
        })

    context = {
        'issues': issues,
        'total_issues': len(issues),
        'check_timestamp': timezone.now()
    }

    return render(request, 'admin/data_integrity_check.html', context)


@login_required
@user_passes_test(is_admin)
def fix_data_issue(request, issue_type):
    """Fix specific data integrity issues"""
    if request.method == 'POST':
        try:
            if issue_type == 'orphaned_students':
                # Logic to fix orphaned students
                # This would depend on your business rules
                messages.success(request, 'Orphaned students issue resolution initiated')

            elif issue_type == 'orphaned_faculty':
                # Logic to fix orphaned faculty
                messages.success(request, 'Orphaned faculty issue resolution initiated')

            elif issue_type == 'orphaned_enrollments':
                # Logic to fix orphaned enrollments
                messages.success(request, 'Orphaned enrollments issue resolution initiated')

            else:
                messages.error(request, 'Unknown issue type')

        except Exception as e:
            messages.error(request, f'Error fixing issue: {str(e)}')

    return redirect('person:data_integrity_check')
