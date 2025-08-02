#Academic Structure views
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib import messages

# Model imports
from .models import Department, Program, Course, Semester, Semesterdetails, Class
from FacultyModule.models import Faculty, Courseallocation
from StudentModule.models import Student, Enrollment, Transcript, Result

# Form imports
from .forms import ProgramForm, CourseForm, ClassForm


def is_admin(user):
    """Check if user is admin"""
    return user.groups.filter(name='Admin').exists()


# ===========================================
# DEPARTMENT VIEWS (VIEW ONLY - NO CRUD)
# ===========================================

@login_required
@user_passes_test(is_admin)
def department_list(request):
    """List all departments with statistics (VIEW ONLY)"""
    departments = Department.objects.prefetch_related(
        'program_set',
        'faculty_set__employeeid'
    ).all()

    # Search functionality
    search = request.GET.get('search')
    if search:
        departments = departments.filter(
            Q(departmentname__icontains=search) |
            Q(hod__employeeid__fname__icontains=search) |
            Q(hod__employeeid__lname__icontains=search)
        )

    from Person.models import ChangeRequest
    # Add statistics to each department
    dept_data = []
    for dept in departments:
        faculty_count = Faculty.objects.filter(departmentid=dept).count()
        program_count = Program.objects.filter(departmentid=dept).count()
        student_count = Student.objects.filter(programid__departmentid=dept).count()
        department_faculty = Faculty.objects.filter(departmentid=dept).select_related('employeeid')
        pending_change = ChangeRequest.objects.filter(
            change_type='hod_change',
            department=dept,
            status__in=['pending', 'confirmed', 'declined', 'expired']  # All non-applied statuses
        ).first()

        dept_data.append({
            'department': dept,
            'faculty_count': faculty_count,
            'program_count': program_count,
            'student_count': student_count,
            'faculty_list': department_faculty,
            'pending_hod_change': pending_change,
        })

    # Pagination
    paginator = Paginator(dept_data, 25)
    page = request.GET.get('page')
    dept_data = paginator.get_page(page)

    return render(request, 'academic/department_list.html', {
        'dept_data': dept_data
    })



@login_required
@user_passes_test(is_admin)
def department_detail(request, department_id):
    """Enhanced hierarchical view: Department → Programs → Classes → Scheme of Studies"""

    department = get_object_or_404(Department, departmentid=department_id)
    programs = Program.objects.filter(departmentid=department).order_by('programname')

    def get_class_current_semester(class_obj):
        """Determine current semester for a class using majority rule"""
        from StudentModule.models import Student
        students = Student.objects.filter(classid=class_obj)

        if not students.exists():
            return None, "No Students"

        # Get active enrollments for students in this class
        active_enrollments = Enrollment.objects.filter(
            studentid__classid=class_obj,
            status='Active',
            allocationid__status='Ongoing'
        ).select_related('allocationid__coursecode')

        if not active_enrollments.exists():
            # Check if all students are graduated
            graduated_count = students.filter(status='Graduated').count()
            if graduated_count == students.count():
                return None, "Graduated"
            else:
                return None, "Inactive"

        # Count students per semester
        semester_counts = {}
        for enrollment in active_enrollments:
            course = enrollment.allocationid.coursecode

            # Find semester via semesterdetails
            semester_detail = Semesterdetails.objects.filter(
                coursecode=course,
                classid=class_obj
            ).select_related('semesterid').first()

            if semester_detail and semester_detail.semesterid.status == 'Active':
                sem_no = semester_detail.semesterid.semesterno
                if sem_no not in semester_counts:
                    semester_counts[sem_no] = {
                        'count': 0,
                        'semester': semester_detail.semesterid
                    }
                semester_counts[sem_no]['count'] += 1

        if semester_counts:
            # Get semester with maximum students
            max_sem_no = max(semester_counts.keys(), key=lambda x: semester_counts[x]['count'])
            return semester_counts[max_sem_no]['semester'], f"Semester {max_sem_no}"

        return None, "No Active Semester"

    def get_semester_enrollment_count(semester, class_obj):
        """Get enrollment count for active semester via course allocations"""
        if not semester or semester.status != 'Active':
            return 0

        # Get courses for this semester and class
        semester_details = Semesterdetails.objects.filter(
            semesterid=semester,
            classid=class_obj
        )

        course_codes = [sd.coursecode for sd in semester_details]

        # Get allocations for these courses
        allocations = Courseallocation.objects.filter(
            coursecode__in=course_codes,
            status='Ongoing'
        )

        # Count enrollments from this class only
        total_enrollments = Enrollment.objects.filter(
            allocationid__in=allocations,
            studentid__classid=class_obj,
            status='Active'
        ).count()

        return total_enrollments

    def get_completed_semester_data(class_obj):
        """Get completed semesters with highest achiever and average CGPA"""
        completed_semesters = []

        # Get all transcripts for this class
        transcripts = Transcript.objects.filter(
            studentid__classid=class_obj
        ).select_related('semesterid', 'studentid__studentid__personid')

        if not transcripts.exists():
            return completed_semesters

        # Group by semester
        semester_transcripts = {}
        for transcript in transcripts:
            sem_id = transcript.semesterid.semesterid
            if sem_id not in semester_transcripts:
                semester_transcripts[sem_id] = {
                    'semester': transcript.semesterid,
                    'transcripts': []
                }
            semester_transcripts[sem_id]['transcripts'].append(transcript)

        # Process each completed semester
        for sem_data in semester_transcripts.values():
            semester = sem_data['semester']
            semester_transcripts_list = sem_data['transcripts']

            # Only include if majority of class has transcripts (indicating completion)
            from StudentModule.models import Student
            total_class_students = Student.objects.filter(classid=class_obj).count()
            transcript_count = len(semester_transcripts_list)

            # Majority rule: at least 60% of class should have transcripts
            if transcript_count >= (total_class_students * 0.6):
                # Calculate average CGPA
                gpas = [t.semestergpa for t in semester_transcripts_list if t.semestergpa is not None]
                avg_cgpa = round(sum(gpas) / len(gpas), 2) if gpas else 0

                # Find highest achieving student
                highest_achiever = None
                highest_gpa = 0

                for transcript in semester_transcripts_list:
                    if transcript.semestergpa and transcript.semestergpa > highest_gpa:
                        highest_gpa = transcript.semestergpa
                        highest_achiever = transcript.studentid

                completed_semesters.append({
                    'semester': semester,
                    'semester_no': semester.semesterno,
                    'session': semester.session or 'N/A',
                    'avg_cgpa': avg_cgpa,
                    'highest_achiever': highest_achiever,
                    'highest_gpa': round(highest_gpa, 2),
                    'transcript_count': transcript_count
                })

        # Sort by semester number
        completed_semesters.sort(key=lambda x: x['semester_no'])
        return completed_semesters

    def get_scheme_of_studies(class_obj):
        """Get complete scheme of studies for a class"""
        # Get all semester details for this class
        semester_details = Semesterdetails.objects.filter(
            classid=class_obj
        ).select_related('semesterid', 'coursecode').order_by('semesterid__semesterno', 'coursecode__coursecode')

        # Group by semester
        semesters = {}
        for detail in semester_details:
            sem_no = detail.semesterid.semesterno
            if sem_no not in semesters:
                semesters[sem_no] = {
                    'semester': detail.semesterid,
                    'courses': [],
                    'total_credits': 0
                }
            semesters[sem_no]['courses'].append(detail.coursecode)
            semesters[sem_no]['total_credits'] += detail.coursecode.credithours

        return dict(sorted(semesters.items()))

    # Build program data
    program_data = []
    for program in programs:
        classes = Class.objects.filter(programid=program).order_by('-batchyear')

        class_data = []
        for class_obj in classes:
            # Get student count
            from StudentModule.models import Student
            student_count = Student.objects.filter(classid=class_obj).count()
            enrolled_count = Student.objects.filter(classid=class_obj, status='Enrolled').count()

            # Get current semester info
            current_semester, semester_status = get_class_current_semester(class_obj)

            # Get enrollment count for active semester
            enrollment_count = 0
            if current_semester and current_semester.status == 'Active':
                enrollment_count = get_semester_enrollment_count(current_semester, class_obj)

            # Get completed semesters
            completed_semesters = get_completed_semester_data(class_obj)

            # Get scheme of studies
            scheme_of_studies = get_scheme_of_studies(class_obj)

            class_data.append({
                'class_obj': class_obj,
                'class_display': f"{class_obj.programid.programid}-{class_obj.batchyear}",
                'student_count': student_count,
                'enrolled_count': enrolled_count,
                'current_semester': current_semester,
                'semester_status': semester_status,
                'current_enrollment_count': enrollment_count,
                'completed_semesters': completed_semesters,
                'scheme_of_studies': scheme_of_studies,
                'total_scheme_credits': sum(sem['total_credits'] for sem in scheme_of_studies.values())
            })

        if class_data:  # Only add programs that have classes
            program_data.append({
                'program': program,
                'classes': class_data
            })

    context = {
        'department': department,
        'program_data': program_data,
        'total_programs': len(program_data),
        'total_classes': sum(len(p['classes']) for p in program_data)
    }

    return render(request, 'academic/department_detail.html', context)


# ===========================================
# PROGRAM CRUD OPERATIONS
# ===========================================

@login_required
@user_passes_test(is_admin)
def program_list(request):
    """List all programs for dashboard section"""
    # Base queryset with proper joins
    programs = Program.objects.select_related('departmentid').all()

    # Get search and filter parameters
    search = request.GET.get('search', '').strip()
    department_filter = request.GET.get('department', '').strip()
    fee_range_filter = request.GET.get('fee_range', '').strip()
    semesters_filter = request.GET.get('semesters', '').strip()

    # Apply search filter
    if search:
        programs = programs.filter(
            Q(programname__icontains=search) |
            Q(programid__icontains=search) |
            Q(departmentid__departmentname__icontains=search)
        )

    # Apply department filter
    if department_filter:
        programs = programs.filter(departmentid__departmentid=department_filter)

    # Apply fee range filter
    if fee_range_filter:
        if fee_range_filter == 'low':
            programs = programs.filter(fee__lt=50000)
        elif fee_range_filter == 'medium':
            programs = programs.filter(fee__gte=50000, fee__lt=100000)
        elif fee_range_filter == 'high':
            programs = programs.filter(fee__gte=100000)

    # Apply semesters filter
    if semesters_filter:
        programs = programs.filter(totalsemesters=semesters_filter)

    # Calculate statistics for each program
    program_data = []
    for program in programs:
        # Get student counts
        all_students = Student.objects.filter(programid=program)
        total_students = all_students.count()
        active_students = all_students.filter(status='Enrolled').count()
        graduated_students = all_students.filter(status='Graduated').count()
        dropped_students = all_students.filter(status='Dropped').count()

        # Get class count
        total_classes = Class.objects.filter(programid=program).count()

        program_data.append({
            'program_id': program.programid,
            'program_name': program.programname,
            'department_name': program.departmentid.departmentname,
            'total_semesters': program.totalsemesters,
            'fee_per_semester': program.fee or 0,
            'total_students': total_students,
            'active_students': active_students,
            'graduated_students': graduated_students,
            'dropped_students': dropped_students,
            'total_classes': total_classes,
            'program_obj': program
        })

    # Sort by program name
    program_data.sort(key=lambda x: x['program_name'])

    # Pagination
    paginator = Paginator(program_data, 30)
    page_number = request.GET.get('page', 1)
    programs_page = paginator.get_page(page_number)

    # Calculate overall statistics
    total_programs = Program.objects.count()
    total_students_in_programs = sum(p['total_students'] for p in program_data)
    total_departments = Department.objects.count()
    active_programs = sum(1 for p in program_data if p['active_students'] > 0)

    # Get unique values for filters
    departments = Department.objects.all()
    unique_semesters = Program.objects.values_list('totalsemesters', flat=True).distinct().order_by('totalsemesters')

    # Build pagination URLs with current filters
    pagination_params = {
        'search': search,
        'department': department_filter,
        'fee_range': fee_range_filter,
        'semesters': semesters_filter,
    }

    # Remove empty parameters
    pagination_params = {k: v for k, v in pagination_params.items() if v}

    context = {
        'programs': programs_page,
        'program_data': program_data,
        'departments': departments,
        'unique_semesters': unique_semesters,
        'search': search,
        'department_filter': department_filter,
        'fee_range_filter': fee_range_filter,
        'semesters_filter': semesters_filter,
        'pagination_params': pagination_params,
        # Statistics
        'stats': {
            'total_programs': total_programs,
            'active_programs': active_programs,
            'total_students': total_students_in_programs,
            'total_departments': total_departments,
        }
    }

    # FIXED: Return rendered template instead of context
    return render(request, 'academic/program_list.html', context)


@login_required
@user_passes_test(is_admin)
def program_create(request):
    """Create new program"""
    if request.method == 'POST':
        form = ProgramForm(request.POST)
        if form.is_valid():
            try:
                # Check if program ID already exists
                if Program.objects.filter(programid=form.cleaned_data['programid']).exists():
                    messages.error(request, f'Program with ID {form.cleaned_data["programid"]} already exists')
                else:
                    new_program = form.save()
                    program_id = new_program.programid

                    # Check which action was clicked
                    action = request.POST.get('action', 'done')

                    if action == 'add_another':
                        messages.success(request, f'Program {program_id} created successfully! Add another program.')
                        return redirect('/admin/programs/create/')  # Stay on create page
                    else:
                        messages.success(request, f'Program {program_id} created successfully!')
                        # Redirect to program detail
                        return redirect(f'/admin/programs/{program_id}/')

            except Exception as e:
                messages.error(request, f'Error creating program: {str(e)}')
    else:
        form = ProgramForm()

    # Get departments for the form
    departments = Department.objects.all()

    context = {
        'form': form,
        'departments': departments,
    }

    return render(request, 'academic/program_create.html', context)

@login_required
@user_passes_test(is_admin)
def program_detail(request, program_id):
    """View program details with student information and class breakdown"""
    try:
        program = Program.objects.select_related('departmentid').get(programid=program_id)
    except Program.DoesNotExist:
        messages.error(request, 'Program not found.')
        return redirect('/admin/dashboard/?section=programs')

    # Get all students in this program
    students = Student.objects.filter(programid=program).select_related('studentid', 'classid')

    # Calculate student statistics
    total_students = students.count()
    active_students = students.filter(status='Enrolled').count()
    graduated_students = students.filter(status='Graduated').count()
    dropped_students = students.filter(status='Dropped').count()

    # Get classes for this program with student counts
    classes = Class.objects.filter(programid=program).order_by('-batchyear')
    class_data = []

    for class_obj in classes:
        class_students = students.filter(classid=class_obj)
        class_total = class_students.count()
        class_active = class_students.filter(status='Enrolled').count()
        class_graduated = class_students.filter(status='Graduated').count()
        class_dropped = class_students.filter(status='Dropped').count()

        # Determine class status
        if class_graduated == class_total and class_total > 0:
            status = 'Graduated'
        elif class_active > 0:
            status = 'Active'
        elif class_total > 0:
            status = 'Inactive'
        else:
            status = 'Empty'

        class_data.append({
            'class_id': class_obj.classid,
            'display_id': f"{class_obj.programid.programid}-{class_obj.batchyear}",
            'batch_year': class_obj.batchyear,
            'total_students': class_total,
            'active_students': class_active,
            'graduated_students': class_graduated,
            'dropped_students': class_dropped,
            'status': status,
            'class_obj': class_obj
        })

    # Get recent student activities (last 10)
    recent_students = students.order_by('-studentid__personid')[:10]

    # Calculate program statistics
    stats = {
        'total_students': total_students,
        'active_students': active_students,
        'graduated_students': graduated_students,
        'dropped_students': dropped_students,
        'total_classes': len(class_data),
        'active_classes': sum(1 for c in class_data if c['status'] == 'Active'),
        'graduation_rate': round((graduated_students / total_students * 100), 1) if total_students > 0 else 0,
        'retention_rate': round(((active_students + graduated_students) / total_students * 100),
                                1) if total_students > 0 else 0
    }
    context = {
        'program': program,
        'class_data': class_data,
        'recent_students': recent_students,
        'stats': stats,
    }

    return render(request, 'academic/program_detail.html', context)


@login_required
@user_passes_test(is_admin)
def program_update(request, program_id):
    """Edit existing program"""
    try:
        program = get_object_or_404(Program, programid=program_id)
    except Program.DoesNotExist:
        messages.error(request, f'Program with ID {program_id} not found')
        return redirect('/admin/dashboard/?section=programs')

    if request.method == 'POST':
        # Use existing ProgramForm with instance - it handles readonly programid automatically
        form = ProgramForm(request.POST, instance=program)
        if form.is_valid():
            try:
                updated_program = form.save()
                messages.success(request, f'Program {program_id} updated successfully!')
                # Redirect to program detail page
                return redirect(f'/admin/programs/{program_id}/')
            except Exception as e:
                messages.error(request, f'Error updating program: {str(e)}')
    else:
        form = ProgramForm(instance=program)

    # Get departments for reference
    departments = Department.objects.all()

    context = {
        'form': form,
        'program': program,
        'departments': departments,
    }

    return render(request, 'academic/program_edit.html', context)

@login_required
@user_passes_test(is_admin)
def program_delete(request, program_id):
    """Delete program"""
    program = get_object_or_404(Program, programid=program_id)

    if request.method == 'POST':
        try:
            # Check if program has students
            if Student.objects.filter(programid=program).exists():
                messages.error(request, 'Cannot delete program with existing students')
            # Check if program has semesters
            elif Semester.objects.filter(programid=program).exists():  # Fixed: programid not program
                messages.error(request, 'Cannot delete program with existing semesters')
            else:
                program.delete()
                messages.success(request, 'Program deleted successfully')
                return redirect('/admin/dashboard/?section=programs')

        except Exception as e:
            messages.error(request, f'Error deleting program: {str(e)}')

    return render(request, 'academic/program_confirm_delete.html', {'program': program})


# ===========================================
# COURSE CRUD OPERATIONS
# ===========================================

@login_required
@user_passes_test(is_admin)
def course_list(request):
    """List all courses for dashboard section with enhanced filtering"""
    # Base queryset with proper joins
    courses = Course.objects.select_related('prerequisite').all()

    # Get search and filter parameters
    search = request.GET.get('search', '').strip()
    department_filter = request.GET.get('department', '').strip()
    credits_filter = request.GET.get('credits', '').strip()
    code_prefix_filter = request.GET.get('code_prefix', '').strip()

    # Apply search filter
    if search:
        courses = courses.filter(
            Q(coursename__icontains=search) |
            Q(coursecode__icontains=search) |
            Q(description__icontains=search)
        )

    # Apply department filter (complex join query)
    if department_filter:
        courses = courses.filter(
            semesterdetails__semesterid__programid__departmentid__departmentid=department_filter
        ).distinct()

    # Apply credit hours filter
    if credits_filter:
        courses = courses.filter(credithours=credits_filter)

    # Apply course code prefix filter (e.g., CSC, MTH, SK)
    if code_prefix_filter:
        courses = courses.filter(coursecode__startswith=code_prefix_filter)

    # Calculate statistics for each course
    course_data = []
    for course in courses:
        # Get allocation counts
        total_allocations = Courseallocation.objects.filter(coursecode=course).count()
        active_allocations = Courseallocation.objects.filter(
            coursecode=course,
            status='Ongoing'
        ).count()

        # Get enrollments count
        total_enrollments = Enrollment.objects.filter(
            allocationid__coursecode=course
        ).count()

        # Check if course is prerequisite for others
        is_prerequisite_for = Course.objects.filter(prerequisite=course).count()

        course_data.append({
            'course_code': course.coursecode,
            'course_name': course.coursename,
            'credit_hours': course.credithours,
            'prerequisite': course.prerequisite.coursecode if course.prerequisite else None,
            'prerequisite_name': course.prerequisite.coursename if course.prerequisite else None,
            'description': course.description[:100] + '...' if course.description and len(
                course.description) > 100 else course.description,
            'total_allocations': total_allocations,
            'active_allocations': active_allocations,
            'total_enrollments': total_enrollments,
            'is_prerequisite_for': is_prerequisite_for,
            'course_obj': course
        })

    # Sort by course code
    course_data.sort(key=lambda x: x['course_code'])

    # Pagination
    paginator = Paginator(course_data, 50)
    page_number = request.GET.get('page', 1)
    courses_page = paginator.get_page(page_number)

    # Calculate overall statistics
    total_courses = Course.objects.count()
    active_courses = Course.objects.filter(
        courseallocation__status='Ongoing'
    ).distinct().count()
    total_programs = Program.objects.count()
    total_enrollments = sum(c['total_enrollments'] for c in course_data)

    # Get unique values for filters
    departments = Department.objects.all()
    unique_credits = Course.objects.values_list('credithours', flat=True).distinct().order_by('credithours')

    # Get unique course code prefixes (part before hyphen or first 2-3 letters)
    course_codes = Course.objects.values_list('coursecode', flat=True)
    code_prefixes = set()
    for code in course_codes:
        if '-' in code:
            prefix = code.split('-')[0]
        else:
            # Extract first 2-3 letters
            import re
            match = re.match(r'^([A-Z]{2,4})', code)
            if match:
                prefix = match.group(1)
            else:
                prefix = code[:3]
        code_prefixes.add(prefix)
    code_prefixes = sorted(list(code_prefixes))

    # Build pagination URLs with current filters
    pagination_params = {
        'search': search,
        'department': department_filter,
        'credits': credits_filter,
        'code_prefix': code_prefix_filter,
    }

    # Remove empty parameters
    pagination_params = {k: v for k, v in pagination_params.items() if v}

    context = {
        'courses': courses_page,
        'course_data': course_data,
        'departments': departments,
        'unique_credits': unique_credits,
        'code_prefixes': code_prefixes,
        'search': search,
        'department_filter': department_filter,
        'credits_filter': credits_filter,
        'code_prefix_filter': code_prefix_filter,
        'pagination_params': pagination_params,
        # Statistics
        'stats': {
            'total_courses': total_courses,
            'active_courses': active_courses,
            'total_programs': total_programs,
            'total_enrollments': total_enrollments,
        }
    }

    # Return rendered template for dashboard inclusion
    return render(request, 'academic/course_list.html', context)


@login_required
@user_passes_test(is_admin)
def course_create(request):
    """Create new course"""
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            try:
                # Check if course code already exists
                if Course.objects.filter(coursecode=form.cleaned_data['coursecode']).exists():
                    messages.error(request, f'Course with code {form.cleaned_data["coursecode"]} already exists')
                else:
                    new_course = form.save()
                    course_code = new_course.coursecode

                    # Check which action was clicked
                    action = request.POST.get('action', 'done')

                    if action == 'add_another':
                        messages.success(request, f'Course {course_code} created successfully! Add another course.')
                        return redirect('/admin/courses/create/')  # Stay on create page
                    else:
                        messages.success(request, f'Course {course_code} created successfully!')
                        # Redirect to course detail
                        return redirect(f'/admin/courses/{course_code}/')

            except Exception as e:
                messages.error(request, f'Error creating course: {str(e)}')
    else:
        form = CourseForm()

    # Get courses for prerequisite selection
    courses = Course.objects.all().order_by('coursecode')

    context = {
        'form': form,
        'courses': courses,
    }

    return render(request, 'academic/course_create.html', context)


@login_required
@user_passes_test(is_admin)
def course_detail(request, course_code):
    """View course details with allocations and enrollment information"""
    try:
        course = get_object_or_404(Course, coursecode=course_code)
    except Course.DoesNotExist:
        messages.error(request, f'Course with code {course_code} not found')
        return redirect('/admin/dashboard/?section=courses')

    # Get active allocations
    active_allocations = Courseallocation.objects.filter(
        coursecode=course,
        status='Ongoing'
    ).select_related('teacherid').order_by('-session')

    # Get allocation history (all allocations)
    allocation_history = Courseallocation.objects.filter(
        coursecode=course
    ).select_related('teacherid').order_by('-session', '-allocationid')

    # Calculate course statistics
    total_allocations = allocation_history.count()
    total_enrollments = Enrollment.objects.filter(
        allocationid__coursecode=course
    ).count()

    active_enrollments = Enrollment.objects.filter(
        allocationid__coursecode=course,
        allocationid__status='Ongoing'
    ).count()

    # Get courses that have this course as prerequisite
    dependent_courses = Course.objects.filter(prerequisite=course)

    # Get enrollment statistics by semester
    enrollment_stats = []
    for allocation in allocation_history:
        enrollments = Enrollment.objects.filter(allocationid=allocation)
        enrollment_stats.append({
            'allocation': allocation,
            'total_enrollments': enrollments.count(),
            'active_enrollments': enrollments.filter(status='Active').count(),
            'completed_enrollments': enrollments.filter(status='Completed').count(),
        })

    # Get departments offering this course (through semester details)
    departments = Department.objects.filter(
        program__semester__semesterdetails__coursecode=course
    ).distinct()

    context = {
        'course': course,
        'active_allocations': active_allocations,
        'allocation_history': allocation_history,
        'dependent_courses': dependent_courses,
        'departments': departments,
        'enrollment_stats': enrollment_stats,
        'stats': {
            'total_allocations': total_allocations,
            'active_allocations': active_allocations.count(),
            'total_enrollments': total_enrollments,
            'active_enrollments': active_enrollments,
            'dependent_courses_count': dependent_courses.count(),
        }
    }

    return render(request, 'academic/course_detail.html', context)


@login_required
@user_passes_test(is_admin)
def course_update(request, course_code):
    """Edit course in modal popup"""
    try:
        course = get_object_or_404(Course, coursecode=course_code)
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)

    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            try:
                updated_course = form.save()
                # Return success response for AJAX
                return JsonResponse({
                    'success': True,
                    'message': f'Course {course_code} updated successfully!',
                    'redirect_url': f'/admin/dashboard/?section=courses'
                })
            except Exception as e:
                return JsonResponse({'error': f'Error updating course: {str(e)}'}, status=400)
        else:
            # Return form errors
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = error_list
            return JsonResponse({'errors': errors}, status=400)
    else:
        form = CourseForm(instance=course)

    # Get courses for prerequisite selection (exclude current course)
    courses = Course.objects.exclude(coursecode=course_code).order_by('coursecode')

    context = {
        'form': form,
        'course': course,
        'courses': courses,
    }

    return render(request, 'academic/course_edit.html', context)


@login_required
@user_passes_test(is_admin)
def course_delete(request, course_code):
    """Delete course"""
    course = get_object_or_404(Course, coursecode=course_code)
    allocations = Courseallocation.objects.filter(coursecode=course)

    if request.method == 'POST':
        try:
            # Check if course has allocations
            if Courseallocation.objects.filter(coursecode=course).exists():
                # Clear any existing messages
                list(messages.get_messages(request))
                messages.error(request, 'Cannot delete course with existing allocations')
                return render(request, 'academic/course_confirm_delete.html', {
                    'course': course,
                    'allocations': allocations,
                })
            # Check if course is prerequisite for other courses
            elif Course.objects.filter(prerequisite=course).exists():
                # Clear any existing messages
                list(messages.get_messages(request))
                blocking_courses = Course.objects.filter(prerequisite=course)
                course_list = ", ".join([f"{c.coursecode}" for c in blocking_courses])
                messages.error(request, f'Cannot delete course. It is a prerequisite for: {course_list}')
                return render(request, 'academic/course_confirm_delete.html', {
                    'course': course,
                    'allocations': allocations,
                })
            else:
                # Only delete if both checks pass
                course.delete()
                messages.success(request, 'Course deleted successfully')
                return redirect('/admin/dashboard/?section=allocations')

        except Exception as e:
            # Clear any existing messages
            list(messages.get_messages(request))
            messages.error(request, f'Error deleting course: {str(e)}')

    return render(request, 'academic/course_confirm_delete.html', {
        'course': course,
        'allocations': allocations,
    })


# ===========================================
# SEMESTER CRUD OPERATIONS (Fixed for your model)
# ===========================================


@login_required
@user_passes_test(is_admin)
def semester_list(request):
    """List only claimed semesters with filtering and statistics"""

    def apply_filters():
        """Apply filters to semesterdetails queryset"""
        # Get filter parameters
        search = request.GET.get('search', '').strip()
        session_filter = request.GET.get('session', '')
        semester_no_filter = request.GET.get('semester_no', '')
        class_filter = request.GET.get('class', '')

        # Start with all semesterdetails (only claimed semesters)
        queryset = Semesterdetails.objects.select_related(
            'semesterid', 'classid', 'semesterid__programid'
        ).all()

        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(semesterid__session__icontains=search) |
                Q(classid__programid__programname__icontains=search) |
                Q(classid__programid__programid__icontains=search) |
                Q(semesterid__semesterno__icontains=search)
            )

        # Apply session filter
        if session_filter:
            queryset = queryset.filter(semesterid__session=session_filter)

        # Apply semester number filter
        if semester_no_filter:
            queryset = queryset.filter(semesterid__semesterno=semester_no_filter)

        # Apply class filter
        if class_filter:
            queryset = queryset.filter(classid_id=class_filter)

        return queryset, search, session_filter, semester_no_filter, class_filter

    def build_semester_data(filtered_details):
        """Build semester data grouped by semester"""
        semester_data = {}

        for detail in filtered_details:
            semester_id = detail.semesterid.semesterid

            if semester_id not in semester_data:
                # Count total courses for this semester
                course_count = Semesterdetails.objects.filter(
                    semesterid=detail.semesterid
                ).count()

                semester_data[semester_id] = {
                    'semester_id': semester_id,
                    'semester': detail.semesterid,
                    'class_obj': detail.classid,
                    'class_display': f"{detail.classid.programid.programid}-{detail.classid.batchyear}",
                    'semester_no': detail.semesterid.semesterno,
                    'session': detail.semesterid.session or 'N/A',
                    'status': detail.semesterid.status,
                    'course_count': course_count
                }

        return list(semester_data.values())

    def calculate_stats():
        """Calculate statistics"""
        # Total claimed semesters (unique)
        total_claimed_semesters = Semesterdetails.objects.values_list(
            'semesterid', flat=True
        ).distinct().count()

        # Active claimed semesters
        active_semesters = Semesterdetails.objects.filter(
            semesterid__status='Active'
        ).values_list('semesterid', flat=True).distinct().count()

        # Total classes with semester details
        total_classes = Semesterdetails.objects.values_list(
            'classid', flat=True
        ).distinct().count()

        # Total unique courses in semester details
        total_courses = Semesterdetails.objects.values_list(
            'coursecode', flat=True
        ).distinct().count()

        return {
            'total_semesters': total_claimed_semesters,
            'active_semesters': active_semesters,
            'total_classes': total_classes,
            'total_courses': total_courses,
        }

    def get_filter_options():
        """Get filter options for dropdowns"""
        # Get sessions from claimed semesters only
        sessions = Semesterdetails.objects.values_list(
            'semesterid__session', flat=True
        ).distinct().order_by('semesterid__session')

        # Get semester numbers from claimed semesters only
        semester_numbers = Semesterdetails.objects.values_list(
            'semesterid__semesterno', flat=True
        ).distinct().order_by('semesterid__semesterno')

        # Get classes that have semester details
        classes = Class.objects.filter(
            semesterdetails__isnull=False
        ).select_related('programid').distinct().order_by(
            'programid__programid', 'batchyear'
        )

        return {
            'sessions': [s for s in sessions if s],  # Remove None values
            'semester_numbers': semester_numbers,
            'classes': classes,
        }

    # Main execution
    filtered_details, search, session_filter, semester_no_filter, class_filter = apply_filters()
    semester_list_data = build_semester_data(filtered_details)
    stats = calculate_stats()
    filter_options = get_filter_options()

    # Sort by semester number, then by class batch year
    semester_list_data.sort(key=lambda x: (
        x['semester_no'],
        x['class_obj'].batchyear
    ))

    # Pagination
    paginator = Paginator(semester_list_data, 30)
    page_number = request.GET.get('page')
    semesters_page = paginator.get_page(page_number)

    # Pagination parameters for maintaining filters
    pagination_params = {}
    if search:
        pagination_params['search'] = search
    if session_filter:
        pagination_params['session'] = session_filter
    if semester_no_filter:
        pagination_params['semester_no'] = semester_no_filter
    if class_filter:
        pagination_params['class'] = class_filter

    context = {
        'semesters': semesters_page,
        'stats': stats,
        'filter_options': filter_options,
        'search': search,
        'session_filter': session_filter,
        'semester_no_filter': semester_no_filter,
        'class_filter': class_filter,
        'pagination_params': pagination_params,
    }

    return render(request, 'academic/semester_list.html', context)


@login_required
@user_passes_test(is_admin)
def semester_detail_view(request, semester_id):
    """Semester detail view - basic info, links, and transcript graph"""

    # Get semester and linked class
    semester = get_object_or_404(Semester, semesterid=semester_id)

    # Get the class linked to this semester via semesterdetails
    semester_detail = Semesterdetails.objects.filter(
        semesterid=semester
    ).select_related('classid').first()

    linked_class = semester_detail.classid if semester_detail else None

    # Get all courses in this semester
    semester_details = Semesterdetails.objects.filter(
        semesterid=semester
    ).select_related('coursecode').order_by('coursecode__coursecode')

    courses_data = []
    all_allocations = []
    total_semester_enrollments = 0
    class_specific_enrollments = 0

    # Process each course
    for detail in semester_details:
        course = detail.coursecode

        # Get all allocations for this course
        allocations = Courseallocation.objects.filter(
            coursecode=course
        ).select_related('teacherid__employeeid')

        allocation_data = []

        for allocation in allocations:
            # Get enrollments for this allocation
            all_enrollments = Enrollment.objects.filter(allocationid=allocation)

            # Class-specific enrollments (from the linked class)
            if linked_class:
                class_enrollments = all_enrollments.filter(
                    studentid__classid=linked_class
                )
            else:
                class_enrollments = all_enrollments

            total_semester_enrollments += all_enrollments.count()
            class_specific_enrollments += class_enrollments.count()

            allocation_data.append({
                'allocation': allocation,
                'teacher_name': f"{allocation.teacherid.employeeid.fname} {allocation.teacherid.employeeid.lname}",
                'total_enrollments': all_enrollments.count(),
                'class_enrollments': class_enrollments.count(),
                'status': allocation.status,
                'session': allocation.session
            })

        all_allocations.extend(allocations)

        courses_data.append({
            'course': course,
            'allocations': allocation_data,
            'total_allocations': allocations.count()
        })

    # Get transcript data for completed semesters
    transcript_data = None
    transcript_chart_data = None

    if semester.status == 'Completed' and linked_class:
        # Get transcripts for students in the linked class for this semester
        transcripts = Transcript.objects.filter(
            semesterid=semester,
            studentid__classid=linked_class
        ).select_related('studentid__studentid__personid')

        if transcripts:
            # Calculate transcript statistics
            gpas = [t.semestergpa for t in transcripts if t.semestergpa is not None]

            if gpas:
                import statistics

                transcript_data = {
                    'transcripts': transcripts,
                    'total_transcripts': transcripts.count(),
                    'average_gpa': round(statistics.mean(gpas), 2),
                    'highest_gpa': round(max(gpas), 2),
                    'lowest_gpa': round(min(gpas), 2),
                    'std_deviation': round(statistics.stdev(gpas) if len(gpas) > 1 else 0, 2),
                    'excellent_count': len([g for g in gpas if g >= 3.5]),
                    'good_count': len([g for g in gpas if 3.0 <= g < 3.5]),
                    'average_count': len([g for g in gpas if 2.5 <= g < 3.0]),
                    'below_average_count': len([g for g in gpas if g < 2.5])
                }

                # Prepare chart data for transcript distribution
                transcript_chart_data = {
                    'labels': ['0.0-1.0', '1.0-2.0', '2.0-2.5', '2.5-3.0', '3.0-3.5', '3.5-4.0'],
                    'data': [
                        len([g for g in gpas if 0.0 <= g < 1.0]),
                        len([g for g in gpas if 1.0 <= g < 2.0]),
                        len([g for g in gpas if 2.0 <= g < 2.5]),
                        len([g for g in gpas if 2.5 <= g < 3.0]),
                        len([g for g in gpas if 3.0 <= g < 3.5]),
                        len([g for g in gpas if 3.5 <= g <= 4.0])
                    ],
                    'colors': ['#dc3545', '#fd7e14', '#ffc107', '#20c997', '#0dcaf0', '#198754']
                }

    # Summary statistics
    summary_stats = {
        'total_courses': semester_details.count(),
        'total_allocations': len(all_allocations),
        'total_enrollments': total_semester_enrollments,
        'class_enrollments': class_specific_enrollments,
        'semester_status': semester.status,
        'semester_session': semester.session or 'Not Set',
        'linked_class_display': f"{linked_class.programid.programid}-{linked_class.batchyear}" if linked_class else 'No Class Linked'
    }

    # Students in linked class (for reference)
    class_students = None
    if linked_class:
        from StudentModule.models import Student
        class_students = Student.objects.filter(
            classid=linked_class
        ).select_related('studentid').count()

    context = {
        'semester': semester,
        'linked_class': linked_class,
        'courses_data': courses_data,
        'summary_stats': summary_stats,
        'transcript_data': transcript_data,
        'transcript_chart_data': transcript_chart_data,
        'class_students_count': class_students,
    }

    return render(request, 'academic/semester_detail.html', context)


@login_required
@user_passes_test(is_admin)
def semester_performance_report(request, semester_id):
    """Enhanced semester analytics report with performance analysis"""

    # Get semester and linked class
    semester = get_object_or_404(Semester, semesterid=semester_id)

    # Get the class linked to this semester
    semester_detail = Semesterdetails.objects.filter(
        semesterid=semester
    ).select_related('classid').first()

    linked_class = semester_detail.classid if semester_detail else None

    if not linked_class:
        messages.error(request, 'No class is linked to this semester.')
        return redirect('semester_list')

    # Get all courses and allocations for this semester
    semester_details = Semesterdetails.objects.filter(
        semesterid=semester
    ).select_related('coursecode')

    course_codes = [sd.coursecode for sd in semester_details]

    # Get all course allocations for courses in this semester
    all_allocations = Courseallocation.objects.filter(
        coursecode__in=course_codes
    ).select_related('coursecode', 'teacherid__employeeid')

    # Enhanced allocation performance analysis
    allocation_performance = {}
    total_semester_enrollments = 0
    total_semester_results = 0
    all_semester_marks = []
    all_semester_gpas = []

    for allocation in all_allocations:
        # Get enrollments for this allocation (class-specific only)
        enrollments = Enrollment.objects.filter(
            allocationid=allocation,
            studentid__classid=linked_class
        )

        total_semester_enrollments += enrollments.count()

        # Get results for these enrollments
        results = Result.objects.filter(
            enrollmentid__in=enrollments
        )

        if results:
            # Extract marks and GPAs
            marks_data = []
            gpa_data = []

            for result in results:
                if result.obtainedmarks is not None and result.obtainedmarks > 0:
                    marks_data.append(result.obtainedmarks)
                    all_semester_marks.append(result.obtainedmarks)
                if result.coursegpa is not None:
                    gpa_data.append(result.coursegpa)
                    all_semester_gpas.append(result.coursegpa)

            total_semester_results += len(marks_data)

            if marks_data:
                import statistics

                # Calculate detailed performance metrics
                performance_analysis = {
                    'allocation': allocation,
                    'course_name': allocation.coursecode.coursename,
                    'teacher_name': f"{allocation.teacherid.employeeid.fname} {allocation.teacherid.employeeid.lname}",
                    'total_enrollments': enrollments.count(),
                    'total_results': len(marks_data),

                    # Marks-based analysis
                    'average_marks': round(statistics.mean(marks_data), 2),
                    'highest_marks': max(marks_data),
                    'lowest_marks': min(marks_data),
                    'median_marks': round(statistics.median(marks_data), 2),
                    'std_deviation': round(statistics.stdev(marks_data) if len(marks_data) > 1 else 0, 2),

                    # Performance distribution
                    'excellent_count': len([m for m in marks_data if m >= 80]),  # 80+
                    'good_count': len([m for m in marks_data if 70 <= m < 80]),  # 70-79
                    'average_count': len([m for m in marks_data if 60 <= m < 70]),  # 60-69
                    'below_average_count': len([m for m in marks_data if 50 <= m < 60]),  # 50-59
                    'fail_count': len([m for m in marks_data if m < 50]),  # Below 50

                    # Percentages
                    'excellent_percent': round((len([m for m in marks_data if m >= 80]) / len(marks_data)) * 100, 1),
                    'good_percent': round((len([m for m in marks_data if 70 <= m < 80]) / len(marks_data)) * 100, 1),
                    'average_percent': round((len([m for m in marks_data if 60 <= m < 70]) / len(marks_data)) * 100, 1),
                    'below_average_percent': round(
                        (len([m for m in marks_data if 50 <= m < 60]) / len(marks_data)) * 100, 1),
                    'fail_percent': round((len([m for m in marks_data if m < 50]) / len(marks_data)) * 100, 1),

                    # GPA analysis
                    'average_gpa': round(statistics.mean(gpa_data), 2) if gpa_data else 0,
                    'highest_gpa': round(max(gpa_data), 2) if gpa_data else 0,
                    'lowest_gpa': round(min(gpa_data), 2) if gpa_data else 0,

                    # Raw data for charts
                    'marks_distribution': marks_data,
                    'gpa_distribution': gpa_data,
                }

                # Determine allocation performance category
                avg_marks = performance_analysis['average_marks']
                fail_rate = performance_analysis['fail_percent']

                if avg_marks >= 75 and fail_rate <= 10:
                    performance_analysis['category'] = 'Excellent'
                    performance_analysis['category_class'] = 'success'
                    performance_analysis['category_icon'] = 'fas fa-trophy'
                elif avg_marks >= 65 and fail_rate <= 20:
                    performance_analysis['category'] = 'Good'
                    performance_analysis['category_class'] = 'info'
                    performance_analysis['category_icon'] = 'fas fa-thumbs-up'
                elif avg_marks >= 55 and fail_rate <= 35:
                    performance_analysis['category'] = 'Average'
                    performance_analysis['category_class'] = 'warning'
                    performance_analysis['category_icon'] = 'fas fa-minus-circle'
                else:
                    performance_analysis['category'] = 'Needs Improvement'
                    performance_analysis['category_class'] = 'danger'
                    performance_analysis['category_icon'] = 'fas fa-exclamation-triangle'

                allocation_performance[allocation.allocationid] = performance_analysis

    # Overall semester performance (from existing report logic enhanced)
    semester_summary = {
        'total_courses': len(course_codes),
        'total_allocations': all_allocations.count(),
        'class_enrollments': total_semester_enrollments,
        'total_results': total_semester_results,
        'completion_rate': round((total_semester_results / total_semester_enrollments * 100),
                                 1) if total_semester_enrollments > 0 else 0
    }

    # Calculate overall semester statistics
    if all_semester_marks:
        import statistics

        semester_summary.update({
            'overall_average': round(statistics.mean(all_semester_marks), 2),
            'overall_highest': max(all_semester_marks),
            'overall_lowest': min(all_semester_marks),
            'overall_std_dev': round(statistics.stdev(all_semester_marks) if len(all_semester_marks) > 1 else 0, 2),
            'overall_fail_count': len([m for m in all_semester_marks if m < 50]),
            'overall_fail_rate': round((len([m for m in all_semester_marks if m < 50]) / len(all_semester_marks)) * 100,
                                       1),
            'overall_excellent_rate': round(
                (len([m for m in all_semester_marks if m >= 80]) / len(all_semester_marks)) * 100, 1)
        })

    # Get transcript data and chart (same as detail view)
    transcript_data = None
    transcript_chart_data = None

    if semester.status == 'Completed':
        transcripts = Transcript.objects.filter(
            semesterid=semester,
            studentid__classid=linked_class
        ).select_related('studentid__studentid__personid')

        if transcripts:
            gpas = [t.semestergpa for t in transcripts if t.semestergpa is not None]

            if gpas:
                import statistics

                transcript_data = {
                    'total_transcripts': transcripts.count(),
                    'average_gpa': round(statistics.mean(gpas), 2),
                    'highest_gpa': round(max(gpas), 2),
                    'lowest_gpa': round(min(gpas), 2),
                    'std_deviation': round(statistics.stdev(gpas) if len(gpas) > 1 else 0, 2),
                    'excellent_count': len([g for g in gpas if g >= 3.5]),
                    'good_count': len([g for g in gpas if 3.0 <= g < 3.5]),
                    'average_count': len([g for g in gpas if 2.5 <= g < 3.0]),
                    'below_average_count': len([g for g in gpas if g < 2.5])
                }

                # Transcript chart data
                transcript_chart_data = {
                    'labels': ['0.0-1.0', '1.0-2.0', '2.0-2.5', '2.5-3.0', '3.0-3.5', '3.5-4.0'],
                    'data': [
                        len([g for g in gpas if 0.0 <= g < 1.0]),
                        len([g for g in gpas if 1.0 <= g < 2.0]),
                        len([g for g in gpas if 2.0 <= g < 2.5]),
                        len([g for g in gpas if 2.5 <= g < 3.0]),
                        len([g for g in gpas if 3.0 <= g < 3.5]),
                        len([g for g in gpas if 3.5 <= g <= 4.0])
                    ],
                    'colors': ['#dc3545', '#fd7e14', '#ffc107', '#20c997', '#0dcaf0', '#198754']
                }

    # Prepare chart data for allocations
    allocation_charts = {}
    for allocation_id, perf in allocation_performance.items():
        allocation_charts[allocation_id] = {
            'marks_histogram': {
                'labels': ['0-39', '40-49', '50-59', '60-69', '70-79', '80-89', '90-100'],
                'data': [
                    len([m for m in perf['marks_distribution'] if 0 <= m < 40]),
                    len([m for m in perf['marks_distribution'] if 40 <= m < 50]),
                    len([m for m in perf['marks_distribution'] if 50 <= m < 60]),
                    len([m for m in perf['marks_distribution'] if 60 <= m < 70]),
                    len([m for m in perf['marks_distribution'] if 70 <= m < 80]),
                    len([m for m in perf['marks_distribution'] if 80 <= m < 90]),
                    len([m for m in perf['marks_distribution'] if 90 <= m <= 100])
                ],
                'colors': ['#dc3545', '#dc3545', '#ffc107', '#fd7e14', '#20c997', '#0dcaf0', '#198754']
            },
            'gpa_line': {
                'data': perf['gpa_distribution'],
                'labels': list(range(1, len(perf['gpa_distribution']) + 1))
            }
        }

    # Sort allocations by performance (best to worst)
    sorted_allocations = sorted(
        allocation_performance.values(),
        key=lambda x: x['average_marks'],
        reverse=True
    )
    allocation_data = []
    for allocation_id, perf in allocation_performance.items():
        chart_data = allocation_charts[allocation_id]
        allocation_data.append({
            'allocation_id': allocation_id,
            'performance': perf,
            'charts': chart_data
        })

    context = {
        'semester': semester,
        'linked_class': linked_class,
        'semester_summary': semester_summary,
        'allocation_data': allocation_data,
        'allocation_performance': allocation_performance,
        'sorted_allocations': sorted_allocations,
        'transcript_data': transcript_data,
        'transcript_chart_data': transcript_chart_data,
        'allocation_charts': allocation_charts,
        'class_display': f"{linked_class.programid.programid}-{linked_class.batchyear}",
    }

    return render(request, 'academic/semester_report.html', context)
# ===========================================
# CLASS CRUD OPERATIONS (Fixed for your model)
# ===========================================
@login_required
@user_passes_test(is_admin)
def class_list(request):
    """List all classes with statistics and search functionality"""
    # Base queryset with proper joins
    classes = Class.objects.select_related('programid', 'programid__departmentid').all()

    # Get search and filter parameters
    search = request.GET.get('search', '').strip()
    program_filter = request.GET.get('program', '').strip()
    department_filter = request.GET.get('department', '').strip()
    batch_year_filter = request.GET.get('batch_year', '').strip()

    # Apply search filter
    if search:
        classes = classes.filter(
            Q(programid__programname__icontains=search) |
            Q(programid__programid__icontains=search) |
            Q(batchyear__icontains=search) |
            Q(programid__departmentid__departmentname__icontains=search)
        )

    # Apply program filter
    if program_filter:
        classes = classes.filter(programid__programid=program_filter)

    # Apply department filter
    if department_filter:
        classes = classes.filter(programid__departmentid__departmentid=department_filter)

    # Apply batch year filter
    if batch_year_filter:
        classes = classes.filter(batchyear=batch_year_filter)

    # Calculate statistics for each class
    class_data = []
    for class_obj in classes:
        # Get student count for this class
        students = Student.objects.filter(classid=class_obj)
        student_count = students.count()

        # Determine current semester based on where most students are enrolled with active status
        current_semester_display = None
        is_active = False

        if student_count > 0:
            # Follow the path: Student -> Enrollment -> CourseAllocation -> Course -> Semesterdetails -> Semester
            active_enrollments = Enrollment.objects.filter(
                studentid__classid=class_obj,
                status='Active',  # e.status='Active'
                allocationid__status='Ongoing',  # ca.status='Ongoing'
            ).select_related(
                'allocationid__coursecode',  # Get course
                'studentid'  # Get student
            )

            # Get semester info through the course -> semesterdetails -> semester path
            semester_counts = {}

            for enrollment in active_enrollments:
                course = enrollment.allocationid.coursecode

                # Get semesterdetails for this course
                semester_details = Semesterdetails.objects.filter(
                    coursecode=course,
                    classid=class_obj  # Make sure it's for this class
                ).select_related('semesterid').first()

                if semester_details:
                    semester_obj = semester_details.semesterid

                    # Only count if semester is active
                    if semester_obj.status == 'Active':
                        sem_no = semester_obj.semesterno
                        if sem_no not in semester_counts:
                            semester_counts[sem_no] = {
                                'count': 0,
                                'semester_obj': semester_obj
                            }
                        semester_counts[sem_no]['count'] += 1

            if semester_counts:
                # Find semester with maximum students
                max_sem_no = max(semester_counts.keys(), key=lambda x: semester_counts[x]['count'])
                current_semester_display = f"Semester {max_sem_no}"
                is_active = True
            else:
                # No active enrollments found, check if all students are graduated
                graduated_students = students.filter(status='Graduated').count()

                if graduated_students == student_count and student_count > 0:
                    # All students are graduated
                    current_semester_display = "Graduated"
                else:
                    # Not all students are graduated (some are enrolled/dropped but no active semester)
                    current_semester_display = "Inactive"

                is_active = False
        else:
            current_semester_display = "N/A"
            is_active = False

        class_data.append({
            'class_id': class_obj.classid,
            'display_id': f"{class_obj.programid.programid}-{class_obj.batchyear}",
            'program_name': class_obj.programid.programname,
            'department_name': class_obj.programid.departmentid.departmentname,
            'batch_year': class_obj.batchyear,
            'student_count': student_count,
            'enrolled_count': students.filter(status='Enrolled').count(),
            'current_semester': current_semester_display,
            'is_active': is_active,
            'class_obj': class_obj
        })

    # Sort by batch year (newest first) and then by program name
    class_data.sort(key=lambda x: (-int(x['batch_year']), x['program_name']))

    # Pagination
    paginator = Paginator(class_data, 25)
    page_number = request.GET.get('page', 1)
    classes_page = paginator.get_page(page_number)

    # Calculate overall statistics
    total_classes = Class.objects.count()
    active_classes = sum(1 for cls in class_data if cls['is_active'])
    total_students_in_classes = sum(cls['student_count'] for cls in class_data)
    total_departments = Department.objects.count()
    total_programs = Program.objects.count()

    # Get unique batch years for filter
    batch_years = Class.objects.values_list('batchyear', flat=True).distinct().order_by('-batchyear')

    # Get programs and departments for filters
    programs = Program.objects.select_related('departmentid').all()
    departments = Department.objects.all()

    # Build pagination URLs with current filters
    pagination_params = {
        'search': search,
        'program': program_filter,
        'department': department_filter,
        'batch_year': batch_year_filter,
    }

    # Remove empty parameters
    pagination_params = {k: v for k, v in pagination_params.items() if v}

    context = {
        'classes': classes_page,
        'class_data': class_data,
        'programs': programs,
        'departments': departments,
        'batch_years': batch_years,
        'search': search,
        'program_filter': program_filter,
        'department_filter': department_filter,
        'batch_year_filter': batch_year_filter,
        'pagination_params': pagination_params,
        # Statistics
        'stats': {
            'total_classes': total_classes,
            'active_classes': active_classes,
            'total_students': total_students_in_classes,
            'total_departments': total_departments,
            'total_programs': total_programs,
        }
    }

    return render(request, 'academic/class_list.html', context)


@login_required
@user_passes_test(is_admin)
def class_create(request):
    """Create new class"""
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            try:
                new_class = form.save()  # Let database auto-generate classid (AutoField)
                class_display_id = f"{new_class.programid.programid}-{new_class.batchyear}"
                class_id = new_class.classid

                # Check which action was clicked
                action = request.POST.get('action', 'done')

                if action == 'add_another':
                    messages.success(request, f'Class {class_display_id} created successfully! Add another class.')
                    return redirect('academic:class_create')  # Stay on create page
                else:
                    messages.success(request, f'Class {class_display_id} created successfully!')
                    # Redirect to dashboard with classes section
                    return redirect(f'/admin/classes/{class_id}/scheme-of-studies/')

            except Exception as e:
                messages.error(request, f'Error creating class: {str(e)}')
    else:
        form = ClassForm()

    return render(request, 'academic/class_create.html', {'form': form})

@login_required
@login_required
@user_passes_test(is_admin)
def class_detail(request, class_id):
    """View class details with student information and CGPA calculations"""
    from django.db import connection

    class_obj = get_object_or_404(Class, classid=class_id)

    # Get all students in this class
    students = Student.objects.filter(classid=class_obj).select_related('studentid')

    # Calculate CGPA for each student
    student_data = []
    for student in students:
        # Get all transcripts for this student
        transcripts = Transcript.objects.filter(studentid=student).select_related('semesterid')

        # Calculate proper weighted CGPA
        total_grade_points = 0
        total_attempted_credits = 0

        for transcript in transcripts:
            # Get total credit hours for this semester using your SQL logic
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT SUM(c.credithours) as total_credits
                    FROM course c 
                    JOIN semesterdetails sm ON c.coursecode = sm.coursecode 
                    JOIN semester sem ON sm.semesterid = sem.semesterid 
                    WHERE sem.semesterid = %s
                """, [transcript.semesterid.semesterid])

                result = cursor.fetchone()
                semester_total_credits = result[0] if result and result[0] else 0

            # Calculate grade points for this semester
            # semesterGPA represents the weighted average of all attempted courses
            semester_grade_points = float(transcript.semestergpa) * semester_total_credits

            total_grade_points += semester_grade_points
            total_attempted_credits += semester_total_credits

        # Calculate final CGPA
        cgpa = round(total_grade_points / total_attempted_credits, 2) if total_attempted_credits > 0 else 0.00

        student_data.append({
            'student_id': student.studentid.personid,
            'full_name': f"{student.studentid.fname} {student.studentid.lname}",
            'status': student.status,
            'cgpa': cgpa,
            'student_obj': student
        })

    # Sort by CGPA (highest first), then by name
    student_data.sort(key=lambda x: (-x['cgpa'], x['full_name']))

    # Calculate class statistics
    total_students = len(student_data)
    if total_students > 0:
        cgpas = [s['cgpa'] for s in student_data if s['cgpa'] > 0]
        avg_cgpa = round(sum(cgpas) / len(cgpas), 2) if cgpas else 0.00
        highest_cgpa = max(cgpas) if cgpas else 0.00
        lowest_cgpa = min(cgpas) if cgpas else 0.00
    else:
        avg_cgpa = highest_cgpa = lowest_cgpa = 0.00

    # Status distribution
    status_counts = {}
    for student in student_data:
        status = student['status']
        status_counts[status] = status_counts.get(status, 0) + 1

    context = {
        'class_obj': class_obj,
        'student_data': student_data,
        'stats': {
            'total_students': total_students,
            'avg_cgpa': avg_cgpa,
            'highest_cgpa': highest_cgpa,
            'lowest_cgpa': lowest_cgpa,
            'status_counts': status_counts,
        }
    }

    return render(request, 'academic/class_detail.html', context)

@login_required
@user_passes_test(is_admin)
def class_update(request, class_id):
    """Edit class scheme of studies"""
    try:
        class_obj = Class.objects.get(classid=class_id)
    except Class.DoesNotExist:
        messages.error(request, 'Class not found.')
        return redirect('/admin/classes/<int:class_id>/')

    # Get all available courses
    courses = Course.objects.all().order_by('coursecode')

    # Get total semesters from program
    total_semesters = class_obj.programid.totalsemesters
    semester_range = range(1, total_semesters + 1)

    # Initialize semester data structure
    semester_data = {}
    for sem_no in semester_range:
        semester_data[sem_no] = {
            'session': '',
            'courses': []
        }

    # Get existing scheme if any
    try:
        # Get existing semester details for this class
        existing_details = Semesterdetails.objects.filter(
            classid=class_obj
        ).select_related('semesterid', 'coursecode')

        # Group by semester number
        for detail in existing_details:
            sem_no = detail.semesterid.semesterno
            if sem_no in semester_data:
                # Set session if not already set
                if not semester_data[sem_no]['session']:
                    semester_data[sem_no]['session'] = detail.semesterid.session or ''

                # Add course object directly
                semester_data[sem_no]['courses'].append(detail.coursecode)

    except Exception as e:
        print(f"Error loading existing scheme: {e}")
        # Continue with empty semester_data

    if request.method == 'POST':
        try:
            # Delete existing semester details for this class
            Semesterdetails.objects.filter(classid=class_obj).delete()

            created_entries = 0

            # Process each semester
            for sem_no in semester_range:
                session = request.POST.get(f'semester_{sem_no}_session', '').strip()

                # Get or create semester for this program and semester number
                semester_obj, created = Semester.objects.get_or_create(
                    programid=class_obj.programid,
                    semesterno=sem_no,
                    defaults={'session': session, 'status': 'Inactive'}
                )

                # Update session if provided and different
                if session and semester_obj.session != session:
                    semester_obj.session = session
                    semester_obj.save()

                # Process courses for this semester
                course_index = 0
                while True:
                    course_code = request.POST.get(f'semester_{sem_no}_course_{course_index}')
                    if not course_code:
                        break

                    try:
                        course_obj = Course.objects.get(coursecode=course_code)

                        # Create semester detail entry
                        Semesterdetails.objects.create(
                            semesterid=semester_obj,
                            coursecode=course_obj,
                            classid=class_obj
                        )
                        created_entries += 1

                    except Course.DoesNotExist:
                        messages.warning(request, f'Course {course_code} not found and was skipped.')
                    except Exception as e:
                        messages.warning(request, f'Error adding course {course_code}: {str(e)}')

                    course_index += 1

            if created_entries > 0:
                messages.success(request,
                                 f'Class scheme updated successfully! {created_entries} course entries saved.')
            else:
                messages.warning(request, 'No valid course entries were saved.')

            # Redirect back to class list
            return redirect('/admin/dashboard/?section=classes')

        except Exception as e:
            messages.error(request, f'Error updating class scheme: {str(e)}')

    # Prepare context for template
    context = {
        'class_obj': class_obj,
        'courses': courses,
        'semester_range': semester_range,
        'total_semesters': total_semesters,
        'semester_data': semester_data,
        'is_edit_mode': True,  # Flag to indicate this is edit mode
    }

    return render(request, 'academic/class_edit.html', context)

@login_required
@user_passes_test(is_admin)
def class_delete(request, class_id):
    """Delete class"""
    class_obj = get_object_or_404(Class, classid=class_id)

    if request.method == 'POST':
        try:
            # Check if class has students
            if Student.objects.filter(classid=class_obj).exists():
                messages.error(request, 'Cannot delete class with existing students')
            else:
                class_obj.delete()
                messages.success(request, 'Class deleted successfully')
                return redirect('academic:class_list')

        except Exception as e:
            messages.error(request, f'Error deleting class: {str(e)}')

    return render(request, 'academic/class_confirm_delete.html', {'class_obj': class_obj})



# ==============================================================
# SCHEME OF STUDIES CRUD OPERATIONS LINKED WITH CLASS OPERATIONS
# ==============================================================

@login_required
@user_passes_test(is_admin)
def scheme_of_studies_create(request, class_id):
    """Setup scheme of studies for a class"""
    try:
        class_obj = Class.objects.get(classid=class_id)
    except Class.DoesNotExist:
        messages.error(request, 'Class not found.')
        return redirect('/admin/dashboard/?section=classes/')

    # Get all available courses
    courses = Course.objects.all().order_by('coursecode')

    # Get total semesters from program
    total_semesters = class_obj.programid.totalsemesters
    semester_range = range(1, total_semesters + 1)

    # Initialize semester data structure
    semester_data = {}
    for sem_no in semester_range:
        semester_data[sem_no] = {
            'session': '',
            'courses': []
        }

    # Get existing scheme if any
    try:
        # Get existing semester details for this class
        existing_details = Semesterdetails.objects.filter(
            classid=class_obj
        ).select_related('semesterid', 'coursecode')

        # Group by semester number
        for detail in existing_details:
            sem_no = detail.semesterid.semesterno
            if sem_no in semester_data:
                # Set session if not already set
                if not semester_data[sem_no]['session']:
                    semester_data[sem_no]['session'] = detail.semesterid.session or ''

                # Add course object directly
                semester_data[sem_no]['courses'].append(detail.coursecode)

    except Exception as e:
        print(f"Error loading existing scheme: {e}")
        # Continue with empty semester_data

    if request.method == 'POST':
        try:
            # Delete existing semester details for this class
            Semesterdetails.objects.filter(classid=class_obj).delete()

            created_entries = 0

            # Process each semester
            for sem_no in semester_range:
                session = request.POST.get(f'semester_{sem_no}_session', '').strip()

                # Find an available (unclaimed) semester for this program and semester number
                semester_obj = Semester.objects.filter(
                    programid=class_obj.programid,
                    semesterno=sem_no
                ).exclude(
                    id__in=Semesterdetails.objects.values_list('semesterid', flat=True)
                ).first()

                if not semester_obj:
                    # Create new semester if no available one found
                    semester_obj = Semester.objects.create(
                        programid=class_obj.programid,
                        semesterno=sem_no,
                        session=session,
                        status='Inactive'
                    )

                # Update session if provided and different
                if session and semester_obj.session != session:
                    semester_obj.session = session
                    semester_obj.save()

                # Process courses for this semester
                course_index = 0
                while True:
                    course_code = request.POST.get(f'semester_{sem_no}_course_{course_index}')
                    if not course_code:
                        break

                    try:
                        course_obj = Course.objects.get(coursecode=course_code)

                        # Create semester detail entry
                        Semesterdetails.objects.create(
                            semesterid=semester_obj,
                            coursecode=course_obj,
                            classid=class_obj
                        )
                        created_entries += 1

                    except Course.DoesNotExist:
                        messages.warning(request, f'Course {course_code} not found and was skipped.')
                    except Exception as e:
                        messages.warning(request, f'Error adding course {course_code}: {str(e)}')

                    course_index += 1

            if created_entries > 0:
                messages.success(request,
                                 f'Scheme of Studies saved successfully! {created_entries} course entries created.')
            else:
                messages.warning(request, 'No valid course entries were saved.')

            # Redirect to avoid re-submission on refresh
            return redirect(f'/admin/classes/{class_id}/scheme-of-studies/')

        except Exception as e:
            messages.error(request, f'Error saving scheme: {str(e)}')

    # Prepare context for template
    context = {
        'class_obj': class_obj,
        'courses': courses,
        'semester_range': semester_range,
        'total_semesters': total_semesters,
        'semester_data': semester_data,  # This contains existing data in simple format
    }

    return render(request, 'academic/scheme_of_studies.html', context)


@login_required
@user_passes_test(is_admin)
def scheme_of_studies_view(request, class_id):
    """View scheme of studies for a class (read-only)"""
    try:
        class_obj = Class.objects.get(classid=class_id)
    except Class.DoesNotExist:
        messages.error(request, 'Class not found.')
        return redirect('/admin/dashboard/?section=classes/')

    # Get semester details grouped by semester
    semester_details = Semesterdetails.objects.filter(
        classid=class_obj
    ).select_related('semesterid', 'coursecode').order_by('semesterid__semesterno', 'coursecode__coursecode')

    # Group by semester
    semesters = {}
    total_credits = 0

    for detail in semester_details:
        sem_no = detail.semesterid.semesterno
        if sem_no not in semesters:
            semesters[sem_no] = {
                'semester': detail.semesterid,
                'courses': [],
                'total_credits': 0
            }
        semesters[sem_no]['courses'].append(detail.coursecode)
        semesters[sem_no]['total_credits'] += detail.coursecode.credithours
        total_credits += detail.coursecode.credithours

    # Calculate statistics
    stats = {
        'total_semesters': len(semesters),
        'total_courses': semester_details.count(),
        'total_credits': total_credits,
        'avg_credits_per_semester': round(total_credits / len(semesters), 1) if semesters else 0
    }

    context = {
        'class_obj': class_obj,
        'semesters': dict(sorted(semesters.items())),  # Sort by semester number
        'total_semesters': class_obj.programid.totalsemesters,
        'stats': stats,
    }

    return render(request, 'academic/scheme_of_studies_view.html', context)
# ===========================================
# UTILITY AND HELPER VIEWS
# ===========================================

@login_required
@user_passes_test(is_admin)
def get_program_semesters(request):
    """Get semesters for a specific program (AJAX endpoint)"""
    program_id = request.GET.get('program_id')
    if not program_id:
        return JsonResponse({'success': False, 'message': 'Program ID required'})

    try:
        program = get_object_or_404(Program, programid=program_id)
        semesters = Semester.objects.filter(programid=program).order_by('semesterno')  # Fixed: programid, semesterno

        data = [{
            'semester_id': sem.semesterid,
            'semester_number': sem.semesterno,  # Fixed: semesterno
            'display_name': f'Semester {sem.semesterno}'  # Fixed: semesterno
        } for sem in semesters]

        return JsonResponse({'success': True, 'semesters': data})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@user_passes_test(is_admin)
def get_semester_courses(request):
    """Get courses for a specific semester (AJAX endpoint)"""
    semester_id = request.GET.get('semester_id')
    if not semester_id:
        return JsonResponse({'success': False, 'message': 'Semester ID required'})

    try:
        semester = get_object_or_404(Semester, semesterid=semester_id)
        semester_details = Semesterdetails.objects.filter(
            semesterid=semester
        ).select_related('coursecode')

        data = [{
            'course_code': detail.coursecode.coursecode,
            'course_name': detail.coursecode.coursename,
            'credit_hours': detail.coursecode.credithours
        } for detail in semester_details]

        return JsonResponse({'success': True, 'courses': data})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@user_passes_test(is_admin)
def get_program_classes(request):
    """Get classes for a specific program (AJAX endpoint)"""
    program_id = request.GET.get('program_id')
    if not program_id:
        return JsonResponse({'success': False, 'message': 'Program ID required'})

    try:
        program = get_object_or_404(Program, programid=program_id)
        classes = Class.objects.filter(programid=program)  # Your model has programid

        data = [{
            'class_id': cls.classid,
            'batch_year': cls.batchyear,  # Your model has batchyear
            'display_name': f'{program.programname} - {cls.batchyear}'
        } for cls in classes]

        return JsonResponse({'success': True, 'classes': data})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@user_passes_test(is_admin)
def academic_structure_stats(request):
    """Get academic structure statistics"""
    try:
        stats = {
            'departments': Department.objects.count(),
            'programs': Program.objects.count(),
            'courses': Course.objects.count(),
            'semesters': Semester.objects.count(),
            'classes': Class.objects.count(),
            'semester_details': Semesterdetails.objects.count(),

            # Additional stats
            'courses_with_prerequisites': Course.objects.filter(prerequisite__isnull=False).count(),
            'programs_by_department': list(
                Program.objects.values('departmentid__departmentname')
                .annotate(count=Count('programid'))
                .order_by('-count')
            ),
            'courses_by_credit_hours': list(
                Course.objects.values('credithours')
                .annotate(count=Count('coursecode'))
                .order_by('credithours')
            ),
            'classes_by_program': list(
                Class.objects.values('programid__programname')
                .annotate(count=Count('classid'))
                .order_by('-count')
            )
        }

        return JsonResponse(stats)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


# ===========================================
# HIERARCHICAL VIEWS (Admin coordination functions for Person/views.py)
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
        # Get all courses through semester details
        semester_details = Semesterdetails.objects.filter(
            semesterid__programid=program  # Fixed: programid not program
        ).select_related('coursecode', 'semesterid')

        # Group by semester
        semesters = {}
        for detail in semester_details:
            sem_num = detail.semesterid.semesterno  # Fixed: semesterno not semesternumber
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
        semesters = Semester.objects.filter(programid=program).order_by('semesterno')  # Fixed: programid, semesterno

        semester_data = []
        for semester in semesters:
            semester_details = Semesterdetails.objects.filter(
                semesterid=semester
            ).select_related('coursecode', 'classid')  # Added: classid from your model

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