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
from StudentModule.models import Student, Enrollment, Transcript

# Form imports
from .forms import ProgramForm, CourseForm, SemesterForm, SemesterdetailsForm, ClassForm


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

    # Add statistics to each department
    dept_data = []
    for dept in departments:
        faculty_count = Faculty.objects.filter(departmentid=dept).count()
        program_count = Program.objects.filter(departmentid=dept).count()
        student_count = Student.objects.filter(programid__departmentid=dept).count()

        dept_data.append({
            'department': dept,
            'faculty_count': faculty_count,
            'program_count': program_count,
            'student_count': student_count
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
    """View department details with related data (VIEW ONLY)"""
    department = get_object_or_404(Department, departmentid=department_id)

    # Get related data
    programs = Program.objects.filter(departmentid=department)
    faculty = Faculty.objects.filter(departmentid=department).select_related('employeeid')
    students = Student.objects.filter(programid__departmentid=department).select_related('studentid')

    # Statistics
    total_programs = programs.count()
    total_faculty = faculty.count()
    total_students = students.count()

    context = {
        'department': department,
        'programs': programs,
        'faculty': faculty[:10],  # Show first 10
        'students': students[:10],  # Show first 10
        'total_programs': total_programs,
        'total_faculty': total_faculty,
        'total_students': total_students,
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
    paginator = Paginator(program_data, 15)
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
                        return redirect('/person/admin/academic/programs/create/')  # Stay on create page
                    else:
                        messages.success(request, f'Program {program_id} created successfully!')
                        # Redirect to program detail
                        return redirect(f'/person/admin/academic/programs/{program_id}/')

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
        return redirect('/person/admin/dashboard/?section=programs')

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
        return redirect('/person/admin/dashboard/?section=programs')

    if request.method == 'POST':
        # Use existing ProgramForm with instance - it handles readonly programid automatically
        form = ProgramForm(request.POST, instance=program)
        if form.is_valid():
            try:
                updated_program = form.save()
                messages.success(request, f'Program {program_id} updated successfully!')
                # Redirect to program detail page
                return redirect(f'/person/admin/academic/programs/{program_id}/')
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
                return redirect('academic:program_list')

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
    paginator = Paginator(course_data, 20)
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
                        return redirect('/person/admin/academic/courses/create/')  # Stay on create page
                    else:
                        messages.success(request, f'Course {course_code} created successfully!')
                        # Redirect to course detail
                        return redirect(f'/person/admin/academic/courses/{course_code}/')

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
        return redirect('/person/admin/dashboard/?section=courses')

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
                    'redirect_url': f'/person/admin/dashboard/?section=courses'
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
                return redirect('/person/admin/dashboard/?section=allocations')

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


# FIXED VIEW - NO DUPLICATES FOR SEMESTERS WITHOUT DETAILS

@login_required
@user_passes_test(is_admin)
def semester_list(request):
    """List all semesters with filtering and statistics"""

    # Get filter parameters
    search = request.GET.get('search', '').strip()
    session_filter = request.GET.get('session', '')
    semester_no_filter = request.GET.get('semester_no', '')
    class_filter = request.GET.get('class', '')

    # START WITH SEMESTERS, NOT SEMESTERDETAILS
    semesters = Semester.objects.select_related('programid').all()

    # Apply search filter to semesters
    if search:
        semesters = semesters.filter(
            Q(programid__programname__icontains=search) |
            Q(programid__programid__icontains=search) |
            Q(session__icontains=search) |
            Q(semesterno__icontains=search)
        )

    # Apply session filter
    if session_filter:
        semesters = semesters.filter(session=session_filter)

    # Apply semester number filter
    if semester_no_filter:
        semesters = semesters.filter(semesterno=semester_no_filter)

    # Build the final data
    semester_list_data = []

    for semester in semesters:
        # Get semester details for this semester
        semester_details = Semesterdetails.objects.filter(
            semesterid=semester
        ).select_related('classid__programid')

        # Apply class filter if specified
        if class_filter:
            semester_details = semester_details.filter(classid_id=class_filter)

        if semester_details.exists():
            # Has semester details - group by class
            classes_in_semester = {}
            for detail in semester_details:
                class_id = detail.classid.classid
                if class_id not in classes_in_semester:
                    classes_in_semester[class_id] = {
                        'class_obj': detail.classid,
                        'course_count': 0
                    }
                classes_in_semester[class_id]['course_count'] += 1

            # Add one row per class for this semester
            for class_id, class_info in classes_in_semester.items():
                semester_list_data.append({
                    'semester': semester,
                    'class_obj': class_info['class_obj'],
                    'class_display': f"{class_info['class_obj'].programid.programid}-{class_info['class_obj'].batchyear}",
                    'course_count': class_info['course_count'],
                    'has_details': True  # Has semester details
                })
        else:
            # No semester details - show ONLY ONCE with N/A
            # Skip if class filter is applied (since no class info available)
            if not class_filter:
                semester_list_data.append({
                    'semester': semester,
                    'class_obj': None,  # No class info
                    'class_display': 'N/A',  # No class info
                    'course_count': 0,
                    'has_details': False  # No semester details
                })

    # Sort by semester number
    semester_list_data.sort(key=lambda x: (
        x['semester'].semesterno,
        x['class_obj'].batchyear if x['class_obj'] else 0
    ))

    # Calculate statistics
    all_semester_details = Semesterdetails.objects.all()
    stats = calculate_semester_stats_fixed(all_semester_details)

    # Get filter options
    filter_options = get_semester_filter_options()

    # Pagination
    paginator = Paginator(semester_list_data, 20)
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

# UPDATED HELPER FUNCTIONS

def calculate_semester_stats_fixed(semester_details_queryset):
    """Calculate statistics for semesters - UPDATED VERSION"""

    # Get unique semesters that have details
    unique_semesters_with_details = semester_details_queryset.values_list(
        'semesterid', flat=True
    ).distinct()

    # Get ALL semesters (including those without details)
    total_semesters = Semester.objects.count()

    # Count active semesters (from ALL semesters, not just those with details)
    active_semesters = Semester.objects.filter(status='Active').count()

    # Get unique classes that have semester details
    unique_classes = semester_details_queryset.values_list(
        'classid', flat=True
    ).distinct()

    total_classes = len(unique_classes)

    # Get unique courses in all semester details
    unique_courses = semester_details_queryset.values_list(
        'coursecode', flat=True
    ).distinct()

    total_courses = len(unique_courses)

    return {
        'total_semesters': total_semesters,  # All semesters, not just those with details
        'active_semesters': active_semesters,  # All active semesters
        'total_classes': total_classes,  # Classes that have semester details
        'total_courses': total_courses,  # Unique courses in semester details
    }


def get_semester_filter_options():
    """Get filter options for dropdowns - UPDATED VERSION"""

    # Get all sessions from ALL semesters (not just those with details)
    sessions = Semester.objects.values_list(
        'session', flat=True
    ).distinct().order_by('session')

    # Get all semester numbers from ALL semesters
    semester_numbers = Semester.objects.values_list(
        'semesterno', flat=True
    ).distinct().order_by('semesterno')

    # Get all classes (since we might show semesters without details for any class)
    classes = Class.objects.select_related('programid').all().order_by(
        'programid__programid', 'batchyear'
    )

    return {
        'sessions': [s for s in sessions if s],  # Remove None values
        'semester_numbers': semester_numbers,
        'classes': classes,  # All classes, not just those with semester details
    }

@login_required
@user_passes_test(is_admin)
def semester_detail(request, semester_id):
    """View semester details"""
    semester = get_object_or_404(Semester, semesterid=semester_id)

    return render(request, 'academic/semester_detail.html', {
        'semester': semester
    })



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
    paginator = Paginator(class_data, 15)
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
                    return redirect(f'/person/admin/academic/classes/{class_id}/scheme-of-studies/')

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
        return redirect('/person/admin/academic/classes/')

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
            return redirect('/person/admin/dashboard/?section=classes')

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
def scheme_of_studies_setup(request, class_id):
    """Setup scheme of studies for a class"""
    try:
        class_obj = Class.objects.get(classid=class_id)
    except Class.DoesNotExist:
        messages.error(request, 'Class not found.')
        return redirect('/person/admin/academic/classes/')

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
                                 f'Scheme of Studies saved successfully! {created_entries} course entries created.')
            else:
                messages.warning(request, 'No valid course entries were saved.')

            # Redirect to avoid re-submission on refresh
            return redirect(f'/person/admin/academic/classes/{class_id}/scheme-of-studies/')

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
        return redirect('/person/admin/academic/classes/')

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