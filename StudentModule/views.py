# StudentModule views
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Avg, Sum, Count, When
from django.contrib import messages
from django.utils import timezone
import json

from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

# Model imports
from .models import Student, Enrollment, Result, Reviews, Transcript
from AcademicStructure.models import Program, Class, Course, Semesterdetails
from FacultyModule.models import Faculty, Courseallocation, Assessment, Assessmentchecked
from Person.models import Qualification

# Form imports
from .forms import StudentForm, EnrollmentForm, ReviewForm, TranscriptForm


def is_admin(user):
    """Check if user is admin - shared utility"""
    return user.groups.filter(name='admin').exists()


def is_student(user):
    """Check if user is student"""
    try:
        return Student.objects.filter(studentid__personid=user.username).exists()
    except:
        return False


def is_faculty(user):
    """Check if user is faculty member"""
    try:
        return Faculty.objects.filter(employeeid__personid=user.username).exists()
    except:
        return False


# ===========================================
# STUDENT CRUD OPERATIONS (Admin only)
# ===========================================

@login_required
@user_passes_test(is_admin)
def student_list(request):
    """List all students with search and filtering"""
    students = Student.objects.select_related('studentid', 'classid', 'programid').all()

    # Search functionality
    search = request.GET.get('search')
    if search:
        students = students.filter(
            Q(studentid__fname__icontains=search) |
            Q(studentid__lname__icontains=search) |
            Q(studentid__institutionalemail__icontains=search) |
            Q(studentid__personid__icontains=search)
        )

    # Program filtering
    program = request.GET.get('program')
    if program:
        students = students.filter(programid__programid=program)

    # Class filtering
    class_filter = request.GET.get('class')
    if class_filter:
        students = students.filter(classid__classid=class_filter)

    # Status filtering
    status = request.GET.get('status')
    if status:
        students = students.filter(status=status)

    total_students_count = Student.objects.count()
    enrolled_students_count = Student.objects.filter(status='Enrolled').count()
    graduated_student_count = Student.objects.filter(status='Graduated').count()

    # Pagination
    paginator = Paginator(students, 25)
    page = request.GET.get('page')
    students = paginator.get_page(page)

    return render(request, 'student/student_list.html', {
        'students': students,
        'programs': Program.objects.all(),
        'classes': Class.objects.all(),
        'status': status,
        'total_students_count': total_students_count,
        'enrolled_students_count': enrolled_students_count,
        'graduated_student_count': graduated_student_count,
    })


@login_required
@user_passes_test(is_admin)
def student_create(request):
    """Create new student with dynamic qualifications and dual submit actions"""
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            try:
                # Extract dynamic qualifications data from POST
                qualifications_data = extract_qualifications_from_post(request.POST)

                # Save student with qualifications
                student = form.save_with_qualifications(qualifications_data, commit=True)

                # Get the action from the submit button clicked
                action = request.POST.get('action', 'add_another')

                if action == 'done':
                    messages.success(request,
                                     f'Student {student.studentid.fname} {student.studentid.lname} created successfully!')
                    return redirect('/person/admin/dashboard/?section=students')
                else:  # action == 'add_another'
                    messages.success(request,
                                     f'Student {student.studentid.fname} {student.studentid.lname} created successfully! You can add another student below.')
                    return render(request, 'student/student_create.html', {'form': StudentForm()})

            except Exception as e:
                messages.error(request, f'Error creating student: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentForm()

    return render(request, 'student/student_create.html', {'form': form})


def extract_qualifications_from_post(post_data):
    """Extract dynamic qualifications from POST data"""
    qualifications = []

    # Find all qualification indices
    qualification_indices = set()
    for key in post_data.keys():
        if key.startswith('qualifications[') and '][' in key:
            # Extract index from qualifications[INDEX][field]
            try:
                index = key.split('[')[1].split(']')[0]
                qualification_indices.add(int(index))
            except (ValueError, IndexError):
                continue

    # Extract data for each qualification
    for index in sorted(qualification_indices):
        qualification_data = {}
        fields = ['degreetitle', 'educationboard', 'institution', 'passingyear',
                  'totalmarks', 'obtainedmarks', 'iscurrent']

        for field in fields:
            key = f'qualifications[{index}][{field}]'
            value = post_data.get(key, '')

            # Handle checkbox for iscurrent
            if field == 'iscurrent':
                qualification_data[field] = bool(value)
            # Handle numeric fields
            elif field in ['totalmarks', 'obtainedmarks']:
                try:
                    qualification_data[field] = int(value) if value else None
                except ValueError:
                    qualification_data[field] = None
            else:
                qualification_data[field] = value.strip() if value else ''

        # Only add qualification if it has at least a degree title
        if qualification_data.get('degreetitle'):
            qualifications.append(qualification_data)

    return qualifications


@login_required
def get_program_classes(request, program_id):
    """API endpoint to get classes for a specific program"""
    try:
        classes = Class.objects.filter(programid_id=program_id).select_related('programid')
        classes_data = [{
            'id': cls.classid,
            'program_id': cls.programid.programid,
            'batch_year': cls.batchyear
        } for cls in classes]

        return JsonResponse({'classes': classes_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@user_passes_test(is_admin)
def student_update(request, student_id):
    """Edit student - now a dedicated page matching faculty implementation"""
    student = get_object_or_404(Student, studentid__personid=student_id)

    if request.method == 'POST':
        try:
            # Use the same form handling pattern as faculty
            form = StudentForm(request.POST, instance=student)
            if form.is_valid():
                # Extract qualifications using your existing function
                qualifications_data = extract_qualifications_from_post(request.POST)

                # Save student with qualifications (same pattern as faculty)
                updated_student = form.save_with_qualifications(qualifications_data, commit=True)

                # Add success message and redirect (no JSON - same as faculty)
                messages.success(request,
                                 f'Student {updated_student.studentid.fname} {updated_student.studentid.lname} updated successfully!')
                return redirect(f"/person/admin/students/{student_id}/")
            else:
                # Form errors will be displayed in template
                messages.error(request, 'Please correct the errors below.')

        except Exception as e:
            messages.error(request, f'Error updating student: {str(e)}')

    else:
        # GET request - show form with existing data
        form = StudentForm(instance=student)

    # Get existing qualifications for template (same as faculty)
    qualifications = Qualification.objects.filter(personid=student.studentid)
    qualifications_data = []
    for qual in qualifications:
        qual_dict = {
            'degreetitle': qual.degreetitle or '',
            'educationboard': qual.educationboard or '',
            'institution': qual.institution or '',
            'passingyear': qual.passingyear or '',
            'totalmarks': qual.totalmarks,
            'obtainedmarks': qual.obtainedmarks,
            'iscurrent': bool(qual.iscurrent)
        }
        qualifications_data.append(qual_dict)

    qualifications_json = json.dumps(qualifications_data)
    context = {
        'student': student,
        'form': form,
        'qualifications': qualifications,
        'qualifications_json': qualifications_json,
    }
    return render(request, 'student/student_edit.html', context)



@login_required
@user_passes_test(is_admin)
def student_detail(request, student_id):
    """View student details"""
    student = get_object_or_404(Student, studentid__personid=student_id)

    # Get current enrollments
    current_enrollments = Enrollment.objects.filter(
        studentid=student,
        status='Active'
    ).select_related('allocationid')
    for enrollment in current_enrollments:
        # Get GPA from Result model
        try:
      # Replace with your actual app name
            result = Result.objects.get(enrollmentid=enrollment)
            gpa = result.coursegpa
        except Result.DoesNotExist:
            gpa = None

    current_enrollments_data = [{
        'id': enrollment.enrollmentid,
        'studentid': enrollment.studentid.studentid.personid,  # Fix: get the actual ID
        'allocationid': enrollment.allocationid.allocationid,
        'enrollmentDate': enrollment.enrollmentdate if enrollment.enrollmentdate else None,
        'status': enrollment.status,
        'faculty_id': enrollment.allocationid.teacherid.employeeid.personid,
        'faculty_fname': enrollment.allocationid.teacherid.employeeid.fname,
        'faculty_lname': enrollment.allocationid.teacherid.employeeid.lname,
        'faculty_name': f"{enrollment.allocationid.teacherid.employeeid.fname} {enrollment.allocationid.teacherid.employeeid.lname}",
        'course_code': enrollment.allocationid.coursecode.coursecode,
        'course_name': enrollment.allocationid.coursecode.coursename,
        'gpa': gpa
    } for enrollment in current_enrollments]

    print(current_enrollments_data[0]['enrollmentDate'])
    # Get enrollment history
    history_enrollments = Enrollment.objects.filter(
        studentid=student,
        status__in=[ 'Dropped','Completed']
    ).select_related('allocationid').order_by('-enrollmentid')

    for enrollment in history_enrollments:
        try:
            result = Result.objects.get(enrollmentid=enrollment)
            gpa = result.coursegpa
        except Result.DoesNotExist:
            gpa = None

    history_enrollments_data = [{
        'id': enrollment.enrollmentid,
        'studentid': enrollment.studentid.studentid.personid,  # Fix: get the actual ID
        'allocationid': enrollment.allocationid.allocationid,
        'enrollmentDate': enrollment.enrollmentdate if enrollment.enrollmentdate else None,  # Fix: serialize date
        'status': enrollment.status,
        # Additional data for the new template
        'faculty_id': enrollment.allocationid.teacherid.employeeid.personid,
        'faculty_initial': enrollment.allocationid.teacherid.employeeid.fname[0] if enrollment.allocationid.teacherid.employeeid.fname else '',
        'faculty_name': f"{enrollment.allocationid.teacherid.employeeid.fname} {enrollment.allocationid.teacherid.employeeid.lname}",
        'course_code': enrollment.allocationid.coursecode.coursecode,
        'course_name': enrollment.allocationid.coursecode.coursename,
        'gpa': gpa
    } for enrollment in history_enrollments]

    # Get address information
    address_data = None
    try:
        from Person.models import Address
        address = Address.objects.get(personid=student.studentid)
        address_data = {
            'country': address.country,
            'province': address.province,
            'city': address.city,
            'zipcode': address.zipcode,
            'streetaddress': address.streetaddress
        }
    except Address.DoesNotExist:
        address_data = None  # Explicitly set to None

    # Get qualifications
    qualifications_data = []
    try:
        from Person.models import Qualification
        qualifications = Qualification.objects.filter(personid=student.studentid)
        qualifications_data = [{
            'degreetitle': qual.degreetitle,
            'educationboard': qual.educationboard,
            'institution': qual.institution,
            'passingyear': qual.passingyear,
            'totalmarks': qual.totalmarks,
            'obtainedmarks': qual.obtainedmarks,
            'iscurrent': bool(qual.iscurrent)
        } for qual in qualifications]
    except Exception:
        qualifications_data = []  # Explicitly set to empty list

    # Get admin profile info from API
    admin_profile = {
        'name': 'Administrator',  # Default fallback
        'initials': 'A',
        'role': 'System Administrator'
    }

    return render(request, 'student/student_detail.html', {
        'student': student,
        'current_enrollments': current_enrollments_data,  # For JSON and template
        'enrollments_history': history_enrollments_data,  # For JSON and template
        'address': address_data,  # For JSON and template
        'qualifications': qualifications_data,  # For JSON and template
        'admin_profile': admin_profile,
    })


@login_required
@user_passes_test(is_admin)
def student_delete(request, student_id):
    """Delete student and associated Person record"""
    student = get_object_or_404(Student, studentid__personid=student_id)

    if request.method == 'POST':
        try:
            person = student.studentid
            with transaction.atomic():
                student.delete()
                person.delete()

            messages.success(request, 'Student deleted successfully')
            return redirect('student:student_list')

        except Exception as e:
            messages.error(request, f'Error deleting student: {str(e)}')

    return render(request, 'student/student_confirm_delete.html', {'student': student})


# ===========================================
# ENROLLMENT CRUD OPERATIONS (Admin only)
# ===========================================

def enrollment_list(request):
    """List all enrollments with filtering and pagination"""

    # Get filter parameters
    search = request.GET.get('search', '').strip()
    class_filter = request.GET.get('class', '')
    course_filter = request.GET.get('course', '')
    session_filter = request.GET.get('session', '')
    status_filter = request.GET.get('status', '')

    # Base queryset with related data
    enrollments = Enrollment.objects.select_related(
        'studentid__studentid',  # Person data for student
        'allocationid__coursecode',  # Course data
        'allocationid__teacherid__employeeid',  # Person data for teacher
        'studentid__classid__programid'  # Program data
    ).all()

    # Apply search filter
    if search:
        enrollments = enrollments.filter(
            Q(studentid__studentid__fname__icontains=search) |
            Q(studentid__studentid__lname__icontains=search) |
            Q(studentid__studentid__personid__icontains=search) |
            Q(allocationid__teacherid__employeeid__fname__icontains=search) |
            Q(allocationid__teacherid__employeeid__lname__icontains=search) |
            Q(allocationid__coursecode__coursecode__icontains=search) |
            Q(allocationid__coursecode__coursename__icontains=search)
        )

    # Apply class filter
    if class_filter:
        enrollments = enrollments.filter(studentid__classid_id=class_filter)

    # Apply course filter
    if course_filter:
        enrollments = enrollments.filter(allocationid__coursecode_id=course_filter)

    # Apply session filter
    if session_filter:
        enrollments = enrollments.filter(allocationid__session=session_filter)

    # Apply status filter
    if status_filter:
        enrollments = enrollments.filter(status=status_filter)

    # Order by most recent enrollments
    enrollments = enrollments.order_by('-enrollmentdate')

    # Get statistics for the filtered enrollments
    stats = get_enrollment_stats(enrollments)

    # Pagination
    paginator = Paginator(enrollments, 20)
    page_number = request.GET.get('page')
    enrollments_page = paginator.get_page(page_number)

    # Get filter options
    filter_options = get_enrollment_filter_options()

    # Prepare enrollment data with additional info
    enrollment_data = []
    for enrollment in enrollments_page:
        # Get student initials
        student_name = f"{enrollment.studentid.studentid.fname} {enrollment.studentid.studentid.lname}"
        student_initials = get_initials(student_name)

        # Get teacher initials
        teacher_name = f"{enrollment.allocationid.teacherid.employeeid.fname} {enrollment.allocationid.teacherid.employeeid.lname}"
        teacher_initials = get_initials(teacher_name)

        enrollment_data.append({
            'enrollment': enrollment,
            'student_name': student_name,
            'student_initials': student_initials,
            'teacher_name': teacher_name,
            'teacher_initials': teacher_initials,
        })

    context = {
        'enrollments': enrollments_page,
        'enrollment_data': enrollment_data,
        'stats': stats,
        'filter_options': filter_options,
        'search': search,
        'class_filter': class_filter,
        'course_filter': course_filter,
        'session_filter': session_filter,
        'status_filter': status_filter,
    }

    return render(request, 'student/enrollment_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
@csrf_protect
def enrollment_create(request):
    """Unified enrollment creation with single and bulk modes"""

    # Get mode from URL parameter or form
    mode = request.GET.get('mode', request.POST.get('current_mode', 'single'))

    if request.method == 'POST':
        try:
            allocation_id = request.POST.get('allocationid')
            current_mode = request.POST.get('current_mode', 'single')

            if not allocation_id:
                messages.error(request, "Please select a course allocation.")
                return redirect(f'/person/admin/enrollments/create/?mode={current_mode}')

            # Get allocation
            allocation = get_object_or_404(Courseallocation, allocationid=allocation_id)

            # Validate allocation is active
            if allocation.status != 'Ongoing':
                messages.error(request, "Cannot enroll students in inactive course allocation.")
                return redirect(f'/person/admin/enrollments/create/?mode={current_mode}')

            if current_mode == 'single':
                return handle_single_enrollment(request, allocation, current_mode)
            else:
                return handle_bulk_enrollment(request, allocation, current_mode)

        except Exception as e:
            messages.error(request, f"Error processing enrollment: {str(e)}")
            return redirect(f'/person/admin/enrollments/create/?mode={mode}')

    # GET request - show form
    allocations = Courseallocation.objects.select_related(
        'coursecode', 'teacherid__employeeid'
    ).filter(status='Ongoing').order_by('coursecode__coursecode')

    context = {
        'allocations': allocations,
        'mode': mode,
        'title': f'{"Bulk" if mode == "bulk" else "Single"} Enrollment',
        'submit_text': 'Enroll Student(s)',
        'is_edit': False,
        'form': type('Form', (), {
            'allocationid': type('Field', (), {
                'id_for_label': 'id_allocationid',
                'name': 'allocationid',
                'queryset': allocations,
                'errors': [],
                'value': None
            })(),
            'non_field_errors': []
        })()
    }

    return render(request, 'student/enrollment_create.html', context)


def handle_single_enrollment(request, allocation, mode):
    """Handle single student enrollment"""
    student_id = request.POST.get('single_student')

    if not student_id:
        messages.error(request, "Please select a student.")
        return redirect(f'/person/admin/enrollments/create/?mode={mode}')

    try:
        with transaction.atomic():
            student = get_object_or_404(Student, studentid__personid=student_id)

            # Check if already enrolled
            existing = Enrollment.objects.filter(
                studentid=student,
                allocationid=allocation
            ).exists()

            if existing:
                messages.error(request, "Student is already enrolled in this course.")
                return redirect(f'/person/admin/enrollments/create/?mode={mode}')

            # Create enrollment
            enrollment = Enrollment.objects.create(
                studentid=student,
                allocationid=allocation,
                enrollmentdate=timezone.now(),
                status='Active'
            )

            student_name = f"{student.studentid.fname} {student.studentid.lname}"
            course_name = allocation.coursecode.coursename

            messages.success(request, f"Successfully enrolled {student_name} in {course_name}")
            return redirect('/person/admin/dashboard/?section=enrollments')

    except Exception as e:
        messages.error(request, f"Error creating enrollment: {str(e)}")
        return redirect(f'/person/admin/enrollments/create/?mode={mode}')


def handle_bulk_enrollment(request, allocation, mode):
    """Handle bulk student enrollment"""
    selected_students_json = request.POST.get('selected_students')

    if not selected_students_json:
        messages.error(request, "Please select at least one student.")
        return redirect(f'/person/admin/enrollments/create/?mode={mode}')

    # Parse selected students
    try:
        selected_student_ids = json.loads(selected_students_json)
    except json.JSONDecodeError:
        messages.error(request, "Invalid student selection data.")
        return redirect(f'/person/admin/enrollments/create/?mode={mode}')

    if not selected_student_ids:
        messages.error(request, "Please select at least one student.")
        return redirect(f'/person/admin/enrollments/create/?mode={mode}')

    # Process bulk enrollment
    with transaction.atomic():
        successful_enrollments = []
        failed_enrollments = []
        duplicate_enrollments = []

        for student_id in selected_student_ids:
            try:
                # Get student
                student = Student.objects.select_related('studentid').get(
                    studentid__personid=student_id
                )

                # Check if already enrolled
                existing = Enrollment.objects.filter(
                    studentid=student,
                    allocationid=allocation
                ).exists()

                if existing:
                    duplicate_enrollments.append(f"{student_id} ({student.studentid.fname} {student.studentid.lname})")
                    continue

                # Create enrollment
                enrollment = Enrollment.objects.create(
                    studentid=student,
                    allocationid=allocation,
                    enrollmentdate=timezone.now(),
                    status='Active'
                )

                successful_enrollments.append(f"{student_id} ({student.studentid.fname} {student.studentid.lname})")

            except Student.DoesNotExist:
                failed_enrollments.append(f"{student_id} (Student not found)")
            except Exception as e:
                failed_enrollments.append(f"{student_id} (Error: {str(e)})")

        # Generate success/error messages
        course_name = allocation.coursecode.coursename

        if successful_enrollments:
            success_msg = f"Successfully enrolled {len(successful_enrollments)} student(s) in {course_name}"
            messages.success(request, success_msg)

        if duplicate_enrollments:
            warning_msg = f"Following students were already enrolled: {', '.join(duplicate_enrollments[:3])}"
            if len(duplicate_enrollments) > 3:
                warning_msg += f" and {len(duplicate_enrollments) - 3} more"
            messages.warning(request, warning_msg)

        if failed_enrollments:
            error_msg = f"Failed to enroll following students: {', '.join(failed_enrollments[:3])}"
            if len(failed_enrollments) > 3:
                error_msg += f" and {len(failed_enrollments) - 3} more"
            messages.error(request, error_msg)

        # Redirect to enrollment list if any successful
        if successful_enrollments:
            return redirect('/person/admin/dashboard/?section=enrollments')
        else:
            return redirect(f'/person/admin/enrollments/create/?mode={mode}')

@login_required
def enrollment_detail(request, enrollment_id):
    """Display detailed information about a specific enrollment"""

    enrollment = get_object_or_404(
        Enrollment.objects.select_related(
            'studentid__studentid',
            'studentid__classid__programid',
            'allocationid__coursecode',
            'allocationid__teacherid__employeeid'
        ),
        enrollmentid=enrollment_id
    )

    # Get student and teacher names
    student_name = f"{enrollment.studentid.studentid.fname} {enrollment.studentid.studentid.lname}"
    teacher_name = f"{enrollment.allocationid.teacherid.employeeid.fname} {enrollment.allocationid.teacherid.employeeid.lname}"

    # Get initials
    student_initials = get_initials(student_name)
    teacher_initials = get_initials(teacher_name)

    # Get semester information using the complex query you provided
    semester_info = get_student_semester_info(enrollment.studentid, enrollment.allocationid.coursecode)

    # Get enrollment statistics for this specific enrollment
    enrollment_stats = {
        'total_enrollments': 1,
        'student_total_enrollments': Enrollment.objects.filter(
            studentid=enrollment.studentid
        ).count(),
        'course_total_enrollments': Enrollment.objects.filter(
            allocationid__coursecode=enrollment.allocationid.coursecode
        ).count(),
        'faculty_total_enrollments': Enrollment.objects.filter(
            allocationid__teacherid=enrollment.allocationid.teacherid
        ).count(),
    }

    context = {
        'enrollment': enrollment,
        'student_name': student_name,
        'teacher_name': teacher_name,
        'student_initials': student_initials,
        'teacher_initials': teacher_initials,
        'semester_info': semester_info,
        'stats': enrollment_stats,
    }

    return render(request, 'student/enrollment_detail.html', context)


@login_required
@user_passes_test(is_admin)
def enrollment_update(request, enrollment_id):
    """Update enrollment"""
    enrollment = get_object_or_404(Enrollment, enrollmentid=enrollment_id)

    if request.method == 'POST':
        form = EnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Enrollment updated successfully')
                return redirect('student:enrollment_list')

            except Exception as e:
                messages.error(request, f'Error updating enrollment: {str(e)}')
    else:
        form = EnrollmentForm(instance=enrollment)

    return render(request, 'student/enrollment_edit.html', {'form': form, 'enrollment': enrollment})


@login_required
@user_passes_test(is_admin)
def enrollment_delete(request, enrollment_id):
    """Delete enrollment"""
    enrollment = get_object_or_404(Enrollment, enrollmentid=enrollment_id)

    if request.method == 'POST':
        try:
            # Check if enrollment has results/grades
            if Assessmentchecked.objects.filter(enrollmentid=enrollment).exists():
                messages.error(request, 'Cannot delete enrollment with existing grades')
            else:
                with transaction.atomic():
                    # Delete result record first
                    Result.objects.filter(enrollmentid=enrollment).delete()
                    # Delete enrollment
                    enrollment.delete()

                messages.success(request, 'Enrollment deleted successfully')
                return redirect('/person/admin/dashboard/?section=enrollments')

        except Exception as e:
            messages.error(request, f'Error deleting enrollment: {str(e)}')

    return render(request, 'student/enrollment_confirm_delete.html', {'enrollment': enrollment})


# ===========================================
# RESULT MANAGEMENT VIEWS (Admin can CRUD, Students can VIEW)
# ===========================================

@login_required
def result_list(request):
    """List results - admin sees all, students see their own"""
    if is_admin(request.user):
        results = Result.objects.select_related(
            'enrollmentid__studentid__studentid',
            'enrollmentid__allocationid__coursecode'
        ).all()
    elif is_student(request.user):
        student = get_object_or_404(Student, studentid__personid=request.user.username)
        results = Result.objects.filter(
            enrollmentid__studentid=student
        ).select_related('enrollmentid__allocationid__coursecode')
    else:
        return redirect('login')

    # Search functionality
    search = request.GET.get('search')
    if search:
        results = results.filter(
            Q(enrollmentid__studentid__studentid__fname__icontains=search) |
            Q(enrollmentid__studentid__studentid__lname__icontains=search) |
            Q(enrollmentid__allocationid__coursecode__coursename__icontains=search) |
            Q(enrollmentid__allocationid__coursecode__coursecode__icontains=search)
        )

    # GPA filtering
    min_gpa = request.GET.get('min_gpa')
    max_gpa = request.GET.get('max_gpa')
    if min_gpa:
        results = results.filter(coursegpa__gte=min_gpa)
    if max_gpa:
        results = results.filter(coursegpa__lte=max_gpa)

    # Pagination
    paginator = Paginator(results.order_by('-coursegpa'), 25)
    page = request.GET.get('page')
    results = paginator.get_page(page)

    return render(request, 'student/result_list.html', {
        'results': results,
        'is_admin': is_admin(request.user)
    })


@login_required
@user_passes_test(is_faculty)
def result_update(request, result_id):
    """Update result GPA (Admin only)"""
    result = get_object_or_404(Result, resultid=result_id)

    if request.method == 'POST':
        try:
            gpa = float(request.POST.get('coursegpa', result.coursegpa))

            # Validate GPA
            if gpa < 0.0 or gpa > 4.0:
                messages.error(request, 'GPA must be between 0.0 and 4.0')
            else:
                result.coursegpa = gpa
                result.save()
                messages.success(request, 'Result updated successfully')
                return redirect('student:result_list')

        except ValueError:
            messages.error(request, 'Invalid GPA value')
        except Exception as e:
            messages.error(request, f'Error updating result: {str(e)}')

    return render(request, 'student/result_edit.html', {'result': result})


# ===========================================
# TRANSCRIPT MANAGEMENT VIEWS
# ===========================================

@login_required
def transcript_view(request, student_id=None):
    """View student transcript"""
    if is_student(request.user) and not student_id:
        # Student viewing their own transcript
        student = get_object_or_404(Student, studentid__personid=request.user.username)
    elif is_admin(request.user) and student_id:
        # Admin viewing specific student's transcript
        student = get_object_or_404(Student, studentid__personid=student_id)
    else:
        messages.error(request, 'Unauthorized')
        return redirect('login')

    # Get transcript records - Fixed field name (semesterid not semesterid__program)
    transcripts = Transcript.objects.filter(
        studentid=student
    ).select_related('semesterid').order_by('semesterid__semesterno')

    # Get all results for detailed view
    results = Result.objects.filter(
        enrollmentid__studentid=student
    ).select_related('enrollmentid__allocationid__coursecode')

    # Calculate overall statistics
    total_credits = transcripts.aggregate(Sum('totalcredits'))['totalcredits__sum'] or 0
    overall_gpa = transcripts.aggregate(Avg('semestergpa'))['semestergpa__avg'] or 0.0

    context = {
        'student': student,
        'transcripts': transcripts,
        'results': results,
        'total_credits': total_credits,
        'overall_gpa': round(float(overall_gpa), 2) if overall_gpa else 0.0,
        'is_admin': is_admin(request.user)
    }

    return render(request, 'student/transcript.html', context)


@login_required
@user_passes_test(is_admin)
def transcript_create(request):
    """Create/Update transcript record for a semester"""
    if request.method == 'POST':
        form = TranscriptForm(request.POST)
        if form.is_valid():
            try:
                # Create or update transcript
                transcript, created = Transcript.objects.update_or_create(
                    studentid=form.cleaned_data['studentid'],
                    semesterid=form.cleaned_data['semesterid'],
                    defaults={
                        'totalcredits': form.cleaned_data['totalcredits'],
                        'semestergpa': form.cleaned_data['semestergpa']
                    }
                )

                action = 'created' if created else 'updated'
                messages.success(request, f'Transcript {action} successfully')
                return redirect('student:transcript_view', student_id=form.cleaned_data['studentid'].studentid.personid)

            except Exception as e:
                messages.error(request, f'Error saving transcript: {str(e)}')
    else:
        form = TranscriptForm()

    return render(request, 'student/transcript_create.html', {'form': form})


# ===========================================
# REVIEWS MANAGEMENT VIEWS
# ===========================================

@login_required
def review_list(request):
    """List course reviews"""
    if is_admin(request.user):
        reviews = Reviews.objects.select_related(
            'enrollmentid__studentid__studentid',
            'enrollmentid__allocationid__coursecode'
        ).all()
    elif is_student(request.user):
        student = get_object_or_404(Student, studentid__personid=request.user.username)
        reviews = Reviews.objects.filter(
            enrollmentid__studentid=student
        ).select_related('enrollmentid__allocationid__coursecode')
    elif is_faculty(request.user):
        faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
        reviews = Reviews.objects.filter(
            enrollmentid__allocationid__teacherid=faculty
        ).select_related('enrollmentid__studentid__studentid', 'enrollmentid__allocationid__coursecode')
    else:
        return redirect('login')

    # Search functionality
    search = request.GET.get('search')
    if search:
        reviews = reviews.filter(
            Q(enrollmentid__allocationid__coursecode__coursename__icontains=search) |
            Q(enrollmentid__allocationid__coursecode__coursecode__icontains=search) |
            Q(reviewtext__icontains=search)
        )

    # Date filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        reviews = reviews.filter(createdat__date__gte=start_date)
    if end_date:
        reviews = reviews.filter(createdat__date__lte=end_date)

    # Pagination
    paginator = Paginator(reviews.order_by('-createdat'), 25)
    page = request.GET.get('page')
    reviews = paginator.get_page(page)

    return render(request, 'student/review_list.html', {
        'reviews': reviews,
        'is_admin': is_admin(request.user),
        'is_student': is_student(request.user),
        'is_faculty': is_faculty(request.user)
    })


@login_required
def review_create(request):
    """Create new course review"""
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            try:
                enrollment = form.cleaned_data['enrollmentid']

                # Check authorization
                if is_student(request.user):
                    student = get_object_or_404(Student, studentid__personid=request.user.username)
                    if enrollment.studentid != student:
                        messages.error(request, 'Unauthorized')
                        return redirect('student:review_list')
                elif not is_admin(request.user):
                    messages.error(request, 'Unauthorized')
                    return redirect('student:review_list')

                # Check if review already exists
                if Reviews.objects.filter(enrollmentid=enrollment).exists():
                    messages.error(request, 'Review already exists for this enrollment')
                else:
                    review = form.save(commit=False)
                    review.createdat = timezone.now()
                    review.save()

                    messages.success(request, 'Review created successfully')
                    return redirect('student:review_list')

            except Exception as e:
                messages.error(request, f'Error creating review: {str(e)}')
    else:
        form = ReviewForm()

        # Limit enrollments based on user type
        if is_student(request.user):
            student = get_object_or_404(Student, studentid__personid=request.user.username)
            form.fields['enrollmentid'].queryset = Enrollment.objects.filter(studentid=student)

    return render(request, 'student/review_create.html', {'form': form})


@login_required
def review_update(request, review_id):
    """Update review"""
    review = get_object_or_404(Reviews, reviewid=review_id)

    # Check authorization
    can_edit = False
    if is_student(request.user):
        student = get_object_or_404(Student, studentid__personid=request.user.username)
        can_edit = (review.enrollmentid.studentid == student)
    elif is_admin(request.user):
        can_edit = True

    if not can_edit:
        messages.error(request, 'Unauthorized')
        return redirect('student:review_list')

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Review updated successfully')
                return redirect('student:review_list')

            except Exception as e:
                messages.error(request, f'Error updating review: {str(e)}')
    else:
        form = ReviewForm(instance=review)

    return render(request, 'student/review_edit.html', {'form': form, 'review': review})


@login_required
def review_delete(request, review_id):
    """Delete review"""
    review = get_object_or_404(Reviews, reviewid=review_id)

    # Check authorization
    can_delete = False
    if is_student(request.user):
        student = get_object_or_404(Student, studentid__personid=request.user.username)
        can_delete = (review.enrollmentid.studentid == student)
    elif is_admin(request.user):
        can_delete = True

    if not can_delete:
        messages.error(request, 'Unauthorized')
        return redirect('student:review_list')

    if request.method == 'POST':
        try:
            review.delete()
            messages.success(request, 'Review deleted successfully')
            return redirect('student:review_list')

        except Exception as e:
            messages.error(request, f'Error deleting review: {str(e)}')

    return render(request, 'student/review_confirm_delete.html', {'review': review})


# ===========================================
# STUDENT DASHBOARD VIEWS
# ===========================================

@login_required
def student_dashboard(request):
    """Student dashboard with personal academic info"""
    if not is_student(request.user) and not is_admin(request.user):
        return redirect('login')

    if is_student(request.user):
        student = get_object_or_404(Student, studentid__personid=request.user.username)

        # Get student's enrollments
        enrollments = Enrollment.objects.filter(
            studentid=student,
            status='Active'
        ).select_related('allocationid__coursecode', 'allocationid__teacherid__employeeid')

        # Get recent results
        recent_results = Result.objects.filter(
            enrollmentid__studentid=student
        ).select_related('enrollmentid__allocationid__coursecode').order_by('-enrollmentid__enrollmentdate')[:5]

        # Get upcoming assessments
        upcoming_assessments = Assessment.objects.filter(
            allocationid__enrollment__studentid=student,
            assessmentdate__gte=timezone.now().date()
        ).select_related('allocationid__coursecode').order_by('assessmentdate')[:5]

        # Calculate statistics
        total_credits = 0
        total_gpa_points = 0
        course_count = 0

        for result in recent_results:
            course_credits = result.enrollmentid.allocationid.coursecode.credithours
            total_credits += course_credits
            total_gpa_points += float(result.coursegpa) * course_credits
            course_count += 1

        cumulative_gpa = (total_gpa_points / total_credits) if total_credits > 0 else 0.0

        # Get transcript summary
        transcripts = Transcript.objects.filter(studentid=student)
        completed_credits = transcripts.aggregate(Sum('totalcredits'))['totalcredits__sum'] or 0

        context = {
            'student': student,
            'enrollments': enrollments,
            'recent_results': recent_results,
            'upcoming_assessments': upcoming_assessments,
            'cumulative_gpa': round(cumulative_gpa, 2),
            'completed_credits': completed_credits,
            'current_enrollments': enrollments.count(),
        }

        return render(request, 'student/dashboard.html', context)

    else:  # Admin view - redirect to admin dashboard
        return redirect('person:admin_dashboard')


# ===========================================
# ACADEMIC PROGRESS VIEWS
# ===========================================

@login_required
def academic_progress(request, student_id=None):
    """View detailed academic progress for a student"""
    if is_student(request.user) and not student_id:
        student = get_object_or_404(Student, studentid__personid=request.user.username)
    elif is_admin(request.user) and student_id:
        student = get_object_or_404(Student, studentid__personid=student_id)
    else:
        messages.error(request, 'Unauthorized')
        return redirect('login')

    # Get all enrollments and results
    enrollments_with_results = Enrollment.objects.filter(
        studentid=student
    ).select_related(
        'allocationid__coursecode',
        'result'
    ).order_by('-enrollmentdate')

    # Get transcript data - Fixed field reference
    transcripts = Transcript.objects.filter(
        studentid=student
    ).select_related('semesterid').order_by('semesterid__semesterno')

    # Calculate progress statistics
    total_courses = enrollments_with_results.count()
    completed_courses = enrollments_with_results.filter(status='Completed').count()

    # GPA calculation
    gpa_data = []
    cumulative_gpa = 0.0
    total_points = 0
    total_credits = 0

    for enrollment in enrollments_with_results:
        if hasattr(enrollment, 'result'):
            course_credits = enrollment.allocationid.coursecode.credithours
            course_gpa = float(enrollment.result.coursegpa)
            total_points += course_gpa * course_credits
            total_credits += course_credits

            gpa_data.append({
                'course': enrollment.allocationid.coursecode,
                'gpa': course_gpa,
                'credits': course_credits,
                'enrollment_date': enrollment.enrollmentdate
            })

    if total_credits > 0:
        cumulative_gpa = total_points / total_credits

    # Semester-wise progress
    semester_progress = []
    for transcript in transcripts:
        semester_progress.append({
            'semester': transcript.semesterid,
            'credits': transcript.totalcredits,
            'gpa': float(transcript.semestergpa)
        })

    context = {
        'student': student,
        'enrollments_with_results': enrollments_with_results,
        'transcripts': transcripts,
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'cumulative_gpa': round(cumulative_gpa, 2),
        'total_credits': total_credits,
        'gpa_data': gpa_data,
        'semester_progress': semester_progress,
        'is_admin': is_admin(request.user)
    }

    return render(request, 'student/academic_progress.html', context)


# ===========================================
# GRADES AND ASSESSMENT VIEWS
# ===========================================

@login_required
def student_grades(request, student_id=None):
    """View grades for assessments"""
    if is_student(request.user) and not student_id:
        student = get_object_or_404(Student, studentid__personid=request.user.username)
    elif is_admin(request.user) and student_id:
        student = get_object_or_404(Student, studentid__personid=student_id)
    else:
        messages.error(request, 'Unauthorized')
        return redirect('login')

    # Get all graded assessments for the student
    graded_assessments = Assessmentchecked.objects.filter(
        enrollmentid__studentid=student
    ).select_related(
        'assessmentid__allocationid__coursecode',
        'assessmentid',
        'enrollmentid'
    ).order_by('-assessmentid__assessmentdate')

    # Group by course
    courses_grades = {}
    for grade in graded_assessments:
        course = grade.assessmentid.allocationid.coursecode
        if course not in courses_grades:
            courses_grades[course] = []

        courses_grades[course].append({
            'assessment': grade.assessmentid,
            'obtained': grade.obtained,
            'percentage': (float(grade.obtained) / grade.assessmentid.totalmarks) * 100
        })

    context = {
        'student': student,
        'courses_grades': courses_grades,
        'graded_assessments': graded_assessments,
        'is_admin': is_admin(request.user)
    }

    return render(request, 'student/grades.html', context)


# ===========================================
# ADMIN VIEW-ONLY FUNCTIONS (for Person/views.py coordination)
# ===========================================

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

    # Calculate statistics
    total_courses = results.count()
    avg_gpa = results.aggregate(Avg('coursegpa'))['coursegpa__avg'] or 0.0

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
    ).select_related('enrollmentid__studentid__studentid').order_by('-coursegpa')

    # Calculate statistics
    total_students = results.count()
    avg_gpa = results.aggregate(Avg('coursegpa'))['coursegpa__avg'] or 0.0
    high_performers = results.filter(coursegpa__gte=3.5).count()

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
        'semesterid__semesterno')

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
# UTILITY VIEWS
# ===========================================

@login_required
def get_student_enrollments(request):
    """Get enrollments for a specific student (AJAX endpoint)"""
    student_id = request.GET.get('student_id')
    if not student_id:
        return JsonResponse({'success': False, 'message': 'Student ID required'})

    try:
        student = get_object_or_404(Student, studentid__personid=student_id)

        # Check authorization
        if not is_admin(request.user) and is_student(request.user):
            current_student = get_object_or_404(Student, studentid__personid=request.user.username)
            if student != current_student:
                return JsonResponse({'success': False, 'message': 'Unauthorized'})

        enrollments = Enrollment.objects.filter(
            studentid=student
        ).select_related('allocationid__coursecode')

        data = [{
            'enrollment_id': enroll.enrollmentid,
            'course_code': enroll.allocationid.coursecode.coursecode,
            'course_name': enroll.allocationid.coursecode.coursename,
            'session': enroll.allocationid.session,
            'status': enroll.status,
            'enrollment_date': enroll.enrollmentdate.isoformat()
        } for enroll in enrollments]

        return JsonResponse({'success': True, 'enrollments': data})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def get_available_courses(request):
    """Get available courses for enrollment (AJAX endpoint)"""
    student_id = request.GET.get('student_id')
    if not student_id:
        return JsonResponse({'success': False, 'message': 'Student ID required'})

    try:
        student = get_object_or_404(Student, studentid__personid=student_id)

        # Get already enrolled courses
        enrolled_allocations = Enrollment.objects.filter(
            studentid=student
        ).values_list('allocationid', flat=True)

        # Get available course allocations
        available_allocations = Courseallocation.objects.filter(
            status='Active'
        ).exclude(
            allocationid__in=enrolled_allocations
        ).select_related('coursecode', 'teacherid__employeeid')

        data = [{
            'allocation_id': alloc.allocationid,
            'course_code': alloc.coursecode.coursecode,
            'course_name': alloc.coursecode.coursename,
            'session': alloc.session,
            'teacher_name': f"{alloc.teacherid.employeeid.fname} {alloc.teacherid.employeeid.lname}",
            'credits': alloc.coursecode.credithours
        } for alloc in available_allocations]

        return JsonResponse({'success': True, 'courses': data})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# ===========================================
# REPORTS
# ===========================================

@login_required
@user_passes_test(is_admin)
def student_reports(request):
    """Generate various student reports"""
    report_type = request.GET.get('type', 'overview')
    context = {'report_type': report_type}

    if report_type == 'performance':
        # Student performance report
        students_performance = []

        for student in Student.objects.select_related('studentid', 'programid'):
            results = Result.objects.filter(enrollmentid__studentid=student)

            if results.exists():
                avg_gpa = results.aggregate(Avg('coursegpa'))['coursegpa__avg']
                total_courses = results.count()
                completed_credits = Transcript.objects.filter(
                    studentid=student
                ).aggregate(Sum('totalcredits'))['totalcredits__sum'] or 0

                students_performance.append({
                    'student': student,
                    'avg_gpa': round(float(avg_gpa), 2) if avg_gpa else 0.0,
                    'total_courses': total_courses,
                    'completed_credits': completed_credits
                })

        # Sort by GPA
        students_performance.sort(key=lambda x: x['avg_gpa'], reverse=True)
        context['students_performance'] = students_performance

    elif report_type == 'enrollment_statistics':
        # Enrollment statistics
        programs = Program.objects.all()
        enrollment_stats = []

        for program in programs:
            total_students = Student.objects.filter(programid=program).count()
            active_enrollments = Enrollment.objects.filter(
                studentid__programid=program,
                status='Active'
            ).count()

            enrollment_stats.append({
                'program': program,
                'total_students': total_students,
                'active_enrollments': active_enrollments
            })

        context['enrollment_stats'] = enrollment_stats

    return render(request, 'student/reports.html', context)


def get_enrollment_stats(enrollments_queryset):
    """Calculate statistics for enrollments"""

    total_enrollments = enrollments_queryset.count()

    # Count by status using filter
    active_count = enrollments_queryset.filter(status='Active').count()
    completed_count = enrollments_queryset.filter(status='Completed').count()
    dropped_count = enrollments_queryset.filter(status='Dropped').count()
    withdrawn_count = enrollments_queryset.filter(status='Withdrawn').count()

    return {
        'total_enrollments': total_enrollments,
        'active_enrollments': active_count,
        'completed_enrollments': completed_count,
        'dropped_enrollments': dropped_count,
        'withdrawn_enrollments': withdrawn_count,
    }


def get_enrollment_filter_options():
    """Get filter options for dropdowns"""

    # Get all classes
    classes = Class.objects.select_related('programid').all()

    # Get all courses that have allocations
    courses = Course.objects.filter(
        courseallocation__isnull=False
    ).distinct().order_by('coursecode')

    # Get all sessions
    sessions = Courseallocation.objects.values_list(
        'session', flat=True
    ).distinct().order_by('session')

    # Status choices
    status_choices = [
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Dropped', 'Dropped'),
        ('Withdrawn', 'Withdrawn'),
    ]

    return {
        'classes': classes,
        'courses': courses,
        'sessions': [s for s in sessions if s],  # Remove None values
        'status_choices': status_choices,
    }


def get_student_semester_info(student, course):
    """
    Get semester information for a student and course using the exact SQL query:
    SELECT sem.semesterNo FROM student s
    JOIN enrollment e ON s.studentid=e.studentid
    JOIN courseallocation ca ON e.allocationid=ca.allocationid
    JOIN course c ON c.coursecode=ca.coursecode
    JOIN semesterdetails sd ON sd.coursecode=c.coursecode
    JOIN semester sem ON sem.semesterid=sd.semesterid
    WHERE s.classid=sd.classid;
    """

    try:
        # Use raw SQL to execute your exact query for this specific student and course
        from django.db import connection

        with connection.cursor() as cursor:
            sql = """
            SELECT sem.semesterNo, sem.status, sem.session, sem.semesterid
            FROM student s 
            JOIN enrollment e ON s.studentid=e.studentid 
            JOIN courseallocation ca ON e.allocationid=ca.allocationid 
            JOIN course c ON c.coursecode=ca.coursecode 
            JOIN semesterdetails sd ON sd.coursecode=c.coursecode 
            JOIN semester sem ON sem.semesterid=sd.semesterid 
            WHERE s.classid=sd.classid 
            AND s.studentid=%s 
            AND c.coursecode=%s
            LIMIT 1
            """

            cursor.execute(sql, [student.studentid.personid, course.coursecode])
            result = cursor.fetchone()
            print(result)

            if result:
                return {
                    'semester_no': result[0],
                    'semester_status': result[1],
                    'semester_session': result[2],
                    'semester_id': result[3],
                }
            else:
                print(
                    f"DEBUG: No semester found for student {student.studentid.personid} and course {course.coursecode}")
                return {
                    'semester_no': 'Not Found',
                    'semester_status': 'N/A',
                    'semester_session': 'N/A',
                    'semester_id': None,
                }

    except Exception as e:
        print(f"DEBUG: Error in semester query: {str(e)}")
        print(f"DEBUG: Student ID: {student.studentid.personid}")
        print(f"DEBUG: Course Code: {course.coursecode}")
        print(f"DEBUG: Student Class ID: {student.classid}")

        return {
            'semester_no': f'Error: {str(e)}',
            'semester_status': 'Error',
            'semester_session': 'Error',
            'semester_id': None,
        }


def get_initials(full_name):
    """Get initials from a full name"""
    if not full_name:
        return "N/A"

    names = full_name.strip().split()
    if len(names) >= 2:
        return f"{names[0][0]}{names[-1][0]}".upper()
    elif len(names) == 1:
        return names[0][0].upper()
    else:
        return "N/A"


# API endpoint for enrollment statistics (for dashboard)
@login_required
def enrollment_stats_api(request):
    """API endpoint to get enrollment statistics"""

    enrollments = Enrollment.objects.all()
    stats = get_enrollment_stats(enrollments)

    return JsonResponse({
        'success': True,
        'stats': stats
    })


@login_required
def api_get_classes(request):
    """API endpoint to get all classes for dropdown"""
    try:
        classes = Class.objects.select_related('programid').all()
        classes_data = []

        for class_obj in classes:
            classes_data.append({
                'classid': class_obj.classid,
                'program_id': class_obj.programid.programid,
                'batch_year': class_obj.batchyear,
                'display_name': f"{class_obj.programid.programid}-{class_obj.batchyear}"
            })

        return JsonResponse(classes_data, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_get_class_students(request, class_id):
    """API endpoint to get students for a specific class"""
    try:
        class_obj = get_object_or_404(Class, classid=class_id)

        students = Student.objects.select_related(
            'studentid', 'classid__programid'
        ).filter(classid=class_obj).order_by('studentid__personid')

        students_data = []
        for student in students:
            students_data.append({
                'student_id': student.studentid.personid,
                'name': f"{student.studentid.fname} {student.studentid.lname}",
                'email': student.studentid.institutionalemail,
                'status': student.status,
                'class_id': class_id,
                'class_display': f"{student.classid.programid.programid}-{student.classid.batchyear}"
            })

        return JsonResponse(students_data, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_get_all_students(request):
    """API endpoint to get all students for single mode"""
    try:
        students = Student.objects.select_related(
            'studentid', 'classid__programid'
        ).all().order_by('studentid__personid')

        students_data = []
        for student in students:
            class_display = None
            if student.classid:
                class_display = f"{student.classid.programid.programid}-{student.classid.batchyear}"

            students_data.append({
                'student_id': student.studentid.personid,
                'name': f"{student.studentid.fname} {student.studentid.lname}",
                'email': student.studentid.institutionalemail,
                'status': student.status,
                'class_id': student.classid.classid if student.classid else None,
                'class_display': class_display
            })

        return JsonResponse(students_data, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
