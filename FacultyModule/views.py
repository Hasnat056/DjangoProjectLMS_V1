# FacultyModule views
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
import json

# Model imports
from .models import Faculty, Courseallocation, Lecture, Assessment, Attendance, Assessmentchecked
from AcademicStructure.models import Department
from StudentModule.models import Enrollment, Student
from Person.models import Qualification

# Form imports
from .forms import FacultyForm, CourseAllocationForm, LectureForm, AssessmentForm


def is_admin(user):
    """Check if user is admin - shared utility"""
    return user.groups.filter(name='admin').exists()


def is_faculty(user):
    """Check if user is faculty member"""
    try:

        return Faculty.objects.filter(employeeid__institutionalemail=user.username).exists()
    except:
        return False



# ===========================================
# DASHBOARD VIEWS
# ===========================================

@login_required
def faculty_dashboard(request):
    print("=== FACULTY DASHBOARD DEBUG ===")
    print(f"User: {request.user}")
    print(f"Username: {request.user.username}")
    print(f"Is authenticated: {request.user.is_authenticated}")
    print(f"Is anonymous: {request.user.is_anonymous}")
    """Faculty dashboard with personal overview"""
    if not is_faculty(request.user):
        if is_admin(request.user):
            return redirect('person:admin_dashboard')
        else:
            return redirect('/accounts/login/')

    faculty = get_object_or_404(Faculty, employeeid__institutionalemail=request.user.username)

    # Get faculty's course allocations
    # Get faculty's course allocations
    allocations = Courseallocation.objects.filter(
        teacherid=faculty,
        status='Active'
    ).select_related('coursecode')

    # Get recent lectures
    recent_lectures = Lecture.objects.filter(
        allocationid__teacherid=faculty,
        startingtime__gte=timezone.now() - timedelta(days=7)
    ).select_related('allocationid__coursecode').order_by('-startingtime')[:5]

    # Get upcoming assessments
    upcoming_assessments = Assessment.objects.filter(
        allocationid__teacherid=faculty,
        assessmentdate__gte=timezone.now().date()
    ).select_related('allocationid__coursecode').order_by('assessmentdate')[:5]

    # Get statistics
    total_students = Enrollment.objects.filter(
        allocationid__teacherid=faculty
    ).count()

    total_lectures_this_month = Lecture.objects.filter(
        allocationid__teacherid=faculty,
        startingtime__month=timezone.now().month,
        startingtime__year=timezone.now().year
    ).count()

    context = {
        'faculty': faculty,
        'allocations': allocations,
        'recent_lectures': recent_lectures,
        'upcoming_assessments': upcoming_assessments,
        'total_students': total_students,
        'total_lectures_this_month': total_lectures_this_month,
    }

    return render(request, 'faculty/dashboard.html', context)






ALLOCATION_STATUS_CHOICES = [
    ('Ongoing', 'Ongoing'),
    ('Completed', 'Completed'),
    ('Cancelled', 'Cancelled'),
]


# ===========================================
# FACULTY CRUD OPERATIONS (Admin only)
# ===========================================

@login_required
@user_passes_test(is_admin)
def faculty_list(request):
    """List all faculty members with search and filtering"""
    faculties = Faculty.objects.select_related('employeeid', 'departmentid').all()

    # Search functionality
    search = request.GET.get('search')
    if search:
        faculties = faculties.filter(
            Q(employeeid__fname__icontains=search) |
            Q(employeeid__lname__icontains=search) |
            Q(employeeid__institutionalemail__icontains=search) |
            Q(employeeid__personid__icontains=search)
        )

    # Department filtering
    department = request.GET.get('department')
    if department:
        faculties = faculties.filter(departmentid__departmentid=department)

    # Designation filtering - NEW
    designation = request.GET.get('designation')
    if designation:
        faculties = faculties.filter(designation=designation)

    # Statistics - NEW
    total_faculty = Faculty.objects.count()
    active_faculty_count = total_faculty
    new_faculty_count = Faculty.objects.filter(
        joiningdate__gte=timezone.now().replace(day=1)
    ).count()

    # Pagination
    paginator = Paginator(faculties, 25)
    page = request.GET.get('page')
    faculties = paginator.get_page(page)

    return render(request, 'faculty/faculty_list.html', {
        'faculties': faculties,
        'departments': Department.objects.all(),
        'total_faculty': total_faculty,           # NEW
        'active_faculty_count': active_faculty_count,  # NEW
        'new_faculty_count': new_faculty_count,        # NEW
    })


@login_required
@user_passes_test(is_admin)
def faculty_create(request):
    """Create new faculty member with dynamic qualifications and dual submit actions"""
    if request.method == 'POST':
        form = FacultyForm(request.POST)
        if form.is_valid():
            try:
                # Extract dynamic qualifications data from POST
                qualifications_data = extract_qualifications_from_post(request.POST)

                # Save faculty with qualifications
                faculty = form.save_with_qualifications(qualifications_data, commit=True)

                # Get the action from the submit button clicked
                action = request.POST.get('action', 'add_another')

                if action == 'done':
                    messages.success(request,
                                     f'Faculty {faculty.employeeid.fname} {faculty.employeeid.lname} created successfully!')
                    return redirect('/person/admin/dashboard/')
                else:  # action == 'add_another'
                    messages.success(request,
                                     f'Faculty {faculty.employeeid.fname} {faculty.employeeid.lname} created successfully! You can add another faculty member below.')
                    return render(request, 'faculty/faculty_create.html', {'form': FacultyForm()})

            except Exception as e:
                messages.error(request, f'Error creating faculty: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FacultyForm()

    return render(request, 'faculty/faculty_create.html', {'form': form})


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
@user_passes_test(is_admin)
def faculty_detail(request, faculty_id):
    """View faculty details with all related data"""
    faculty = get_object_or_404(Faculty, employeeid__personid=faculty_id)

    # Get current allocations
    current_allocations = Courseallocation.objects.filter(
        teacherid=faculty,
        status='Ongoing'
    ).select_related('coursecode')

    current_allocations_data = [{
        'id': allocation.allocationid,
        'course_code': allocation.coursecode.coursecode,
        'course_name': allocation.coursecode.coursename,
        'session': allocation.session,
        'status': allocation.status
    } for allocation in current_allocations]

    # Get allocation history
    history_allocations = Courseallocation.objects.filter(
        teacherid=faculty,
        status__in=['Completed', 'Cancelled']
    ).select_related('coursecode').order_by('-allocationid')

    history_allocations_data = [{
        'id': allocation.allocationid,
        'course_code': allocation.coursecode.coursecode,
        'course_name': allocation.coursecode.coursename,
        'session': allocation.session,
        'status': allocation.status
    } for allocation in history_allocations]

    # Get address information
    address_data = None
    try:
        from Person.models import Address
        address = Address.objects.get(personid=faculty.employeeid)
        address_data = {
            'country': address.country,
            'province': address.province,
            'city': address.city,
            'zipcode': address.zipcode,
            'streetaddress': address.streetaddress
        }
    except Address.DoesNotExist:
        pass

    # Get qualifications
    qualifications_data = []
    try:
        from Person.models import Qualification
        qualifications = Qualification.objects.filter(personid=faculty.employeeid)
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
        pass

    # Get admin profile info from API
    admin_profile = {
        'name': 'Administrator',  # Default fallback
        'initials': 'A',
        'role': 'System Administrator'
    }

    return render(request, 'faculty/faculty_detail.html', {
        'faculty': faculty,
        'current_allocations': current_allocations_data,
        'allocation_history': history_allocations_data,
        'address': address_data,
        'qualifications': qualifications_data,
        'admin_profile': admin_profile,
    })



@login_required
@user_passes_test(is_admin)
def faculty_update(request, faculty_id):
    """Edit faculty member - now a dedicated page"""
    faculty = get_object_or_404(Faculty, employeeid__personid=faculty_id)
    if request.method == 'POST':
        try:
            # Use the same form handling as your create view
            form = FacultyForm(request.POST, instance=faculty)
            if form.is_valid():
                # Extract qualifications using your existing function
                qualifications_data = extract_qualifications_from_post(request.POST)

                # Save faculty with qualifications (same as create)
                updated_faculty = form.save_with_qualifications(qualifications_data, commit=True)

                # Add success message and redirect (no JSON)
                messages.success(request,
                                 f'Faculty {updated_faculty.employeeid.fname} {updated_faculty.employeeid.lname} updated successfully!')
                return redirect(f"/person/admin/faculty/{faculty_id}/")
            else:
                # Form errors will be displayed in template
                messages.error(request, 'Please correct the errors below.')

        except Exception as e:
            messages.error(request, f'Error updating faculty: {str(e)}')

    else:
        # GET request - show form with existing data
        form = FacultyForm(instance=faculty)

    # Get existing qualifications for template
    qualifications = Qualification.objects.filter(personid=faculty.employeeid)
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
        'faculty': faculty,
        'form': form,
        'qualifications': qualifications,
        'qualifications_json': qualifications_json,
    }
    return render(request, 'faculty/faculty_edit.html', context)

@login_required
@user_passes_test(is_admin)
def faculty_delete(request, faculty_id):
    """Delete faculty member and associated Person record"""
    faculty = get_object_or_404(Faculty, employeeid__personid=faculty_id)

    if request.method == 'POST':
        try:
            person = faculty.employeeid
            with transaction.atomic():
                faculty.delete()
                person.delete()

            messages.success(request, 'Faculty member deleted successfully')
            return redirect('faculty:faculty_list')

        except Exception as e:
            messages.error(request, f'Error deleting faculty: {str(e)}')

    return render(request, 'faculty/faculty_confirm_delete.html', {'faculty': faculty})


# ===========================================
# COURSE ALLOCATION CRUD OPERATIONS (Admin only)
# ===========================================

@login_required
@user_passes_test(is_admin)
def course_allocation_list(request):
    """List view for Course Allocations with filtering and search"""

    # Get base queryset
    queryset = Courseallocation.objects.select_related(
        'teacherid__employeeid',
        'coursecode'
    ).prefetch_related(
        'enrollment_set'
    ).annotate(
        total_enrollments=Count('enrollment')
    ).order_by('-allocationid')

    # Apply filters
    search_query = request.GET.get('search', '').strip()
    session_filter = request.GET.get('session', '').strip()
    status_filter = request.GET.get('status', '').strip()
    faculty_filter = request.GET.get('faculty', '').strip()

    if search_query:
        queryset = queryset.filter(
            Q(coursecode__coursename__icontains=search_query) |
            Q(coursecode__coursecode__icontains=search_query) |
            Q(teacherid__employeeid__fname__icontains=search_query) |
            Q(teacherid__employeeid__lname__icontains=search_query) |
            Q(session__icontains=search_query)
        )

    if session_filter:
        queryset = queryset.filter(session__icontains=session_filter)

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    if faculty_filter:
        queryset = queryset.filter(teacherid__pk=faculty_filter)

    # Pagination
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    allocations = paginator.get_page(page_number)

    # Statistics
    total_allocations = Courseallocation.objects.count()
    active_allocations = Courseallocation.objects.filter(status='Active').count()
    ongoing_allocations = Courseallocation.objects.filter(status='Ongoing').count()
    total_enrollments = Enrollment.objects.count()

    # Get options for dropdowns
    sessions = Courseallocation.objects.values_list('session', flat=True).distinct().order_by('session')
    status_choices = CourseAllocationForm.STATUS_CHOICES
    faculties = Faculty.objects.select_related('employeeid').all()

    return render(request, 'faculty/allocation_list.html', {
        'allocations': allocations,
        'search': search_query,
        'session_filter': session_filter,
        'status_filter': status_filter,
        'faculty_filter': faculty_filter,
        'sessions': sessions,
        'status_choices': status_choices,
        'faculties': faculties,
        'stats': {
            'total_allocations': total_allocations,
            'active_allocations': active_allocations,
            'ongoing_allocations': ongoing_allocations,
            'inactive_allocations': total_allocations - active_allocations - ongoing_allocations,
            'total_enrollments': total_enrollments,
        },
        'pagination_params': {
            'search': search_query,
            'session': session_filter,
            'status': status_filter,
            'faculty': faculty_filter,
        }
    })


@login_required
@user_passes_test(is_admin)
def course_allocation_create(request):
    """Create view for Course Allocation"""

    if request.method == 'POST':
        form = CourseAllocationForm(request.POST)
        if form.is_valid():
            allocation = form.save(commit=False)
            # Set default status to 'Ongoing' at creation
            allocation.status = 'Ongoing'
            allocation.save()

            messages.success(request, 'Course allocation created successfully!')

            action = request.POST.get('action', 'done')
            if action == 'add_another':
                return redirect('/person/admin/allocations/create/')
            else:
                return redirect('/person/admin/dashboard/?section=allocations')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseAllocationForm()

    return render(request, 'faculty/allocation_create.html', {
        'form': form
    })


@login_required
@user_passes_test(is_admin)
def course_allocation_detail(request, allocation_id):
    """Detail view for a specific Course Allocation"""

    allocation = get_object_or_404(Courseallocation, pk=allocation_id)

    # Get all enrollments for this allocation
    enrollments = Enrollment.objects.filter(
        allocationid=allocation
    ).select_related(
        'studentid__studentid',
        'studentid__classid__programid'
    ).order_by('studentid__studentid__fname', 'studentid__studentid__lname')

    # Group enrollments by class
    class_data = {}
    for enrollment in enrollments:
        student = enrollment.studentid
        if student.classid:
            class_key = student.classid.classid
            if class_key not in class_data:
                class_data[class_key] = {
                    'class_obj': student.classid,
                    'display_id': f"{student.classid.programid.programid}-{student.classid.batchyear}",
                    'enrollments': [],
                    'count': 0
                }
            class_data[class_key]['enrollments'].append(enrollment)
            class_data[class_key]['count'] += 1

    # Find the class with maximum students and get its semester info
    max_class = None
    max_count = 0
    semester_info = None

    for class_info in class_data.values():
        if class_info['count'] > max_count:
            max_count = class_info['count']
            max_class = class_info['class_obj']

    # Get semester information for the class with maximum students
    if max_class:
        try:
            # Assuming there's a SemesterDetails model linking course to semester
            from .models import Semesterdetails, Semester
            semester_detail = Semesterdetails.objects.filter(
                coursecode=allocation.coursecode,
                classid=max_class
            ).select_related('semesterid').first()

            if semester_detail:
                semester_info = {
                    'semester_no': semester_detail.semesterid.semesterno,
                    'semester_name': semester_detail.semesterid.semestername
                }
        except Exception as e:
            semester_info = None

    return render(request, 'faculty/allocation_detail.html', {
        'allocation': allocation,
        'enrollments': enrollments,
        'class_data': class_data,
        'max_class': max_class,
        'max_class_count': max_count,
        'semester_info': semester_info,
        'total_enrollments': enrollments.count(),
        'teacher_name': f"{allocation.teacherid.employeeid.fname} {allocation.teacherid.employeeid.lname}",
    })


@login_required
@user_passes_test(is_admin)
def course_allocation_update(request, allocation_id):
    """Update course allocation"""
    allocation = get_object_or_404(Courseallocation, allocationid=allocation_id)

    if request.method == 'POST':
        form = CourseAllocationForm(request.POST, instance=allocation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course allocation updated successfully!')
            return redirect('course_allocation_detail', allocation_id=allocation.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseAllocationForm(instance=allocation)

        print("Form fields:", form.fields.keys())
        print("Status field:", form.fields.get('status'))
        print("Status choices:", form.fields['status'].choices if 'status' in form.fields else 'No status field')

    return render(request, 'faculty/allocation_edit.html', {'form': form, 'allocation': allocation})


@login_required
@user_passes_test(is_admin)
@login_required
def course_allocation_delete(request, allocation_id):
    allocation = get_object_or_404(Courseallocation, pk=allocation_id)

    if request.method == 'POST':
        course_name = allocation.coursecode.coursename
        allocation.delete()
        messages.success(request, f'Course allocation for {course_name} has been deleted successfully!')
        return redirect('/person/admin/dashboard/?section=allocations')  # ← This redirects back to the list

    # GET request - show confirmation page
    return render(request, 'faculty/allocation_confirm_delete.html', {
        'allocation': allocation
    })


@login_required
def allocation_stats_api(request):
    """API endpoint for allocation statistics"""
    total_allocations = Courseallocation.objects.count()
    ongoing_allocations = Courseallocation.objects.filter(status='Ongoing').count()
    completed_allocations = Courseallocation.objects.filter(status='Completed').count()
    total_enrollments = Enrollment.objects.count()

    # Recent allocations
    recent_allocations = Courseallocation.objects.select_related(
        'teacherid__employeeid', 'coursecode'
    ).order_by('-allocationid')[:5]

    recent_data = []
    for allocation in recent_allocations:
        recent_data.append({
            'id': allocation.allocationid,
            'course': allocation.coursecode.coursename,
            'teacher': f"{allocation.teacherid.employeeid.fname} {allocation.teacherid.employeeid.lname}",
            'session': allocation.session,
            'status': allocation.status
        })

    return JsonResponse({
        'total_allocations': total_allocations,
        'completed_allocations':completed_allocations,
        'ongoing_allocations': ongoing_allocations,
        'cancelled_allocations': total_allocations - completed_allocations - ongoing_allocations,
        'total_enrollments': total_enrollments,
        'recent_allocations': recent_data
    })

# ===========================================
# LECTURE MANAGEMENT VIEWS (Faculty can CRUD, Admin can VIEW only)
# ===========================================

@login_required
def lecture_list(request):
    """List lectures - faculty can modify their own, admin can view all"""
    if is_faculty(request.user):
        faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
        lectures = Lecture.objects.filter(
            allocationid__teacherid=faculty
        ).select_related('allocationid__coursecode')
        can_modify = True
    elif is_admin(request.user):
        # Admin redirected to view by allocation (read-only)
        lectures = Lecture.objects.select_related(
            'allocationid__coursecode', 'allocationid__teacherid__employeeid'
        ).all()
        can_modify = False
    else:
        return redirect('login')

    # Search functionality
    search = request.GET.get('search')
    if search:
        lectures = lectures.filter(
            Q(allocationid__coursecode__coursename__icontains=search) |
            Q(allocationid__coursecode__coursecode__icontains=search) |
            Q(topic__icontains=search) |
            Q(lectureid__icontains=search)
        )

    # Date filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        lectures = lectures.filter(startingtime__date__gte=start_date)
    if end_date:
        lectures = lectures.filter(startingtime__date__lte=end_date)

    # Venue filtering
    venue = request.GET.get('venue')
    if venue:
        lectures = lectures.filter(venue__icontains=venue)

    # Pagination
    paginator = Paginator(lectures.order_by('-startingtime'), 25)
    page = request.GET.get('page')
    lectures = paginator.get_page(page)

    return render(request, 'faculty/lecture_list.html', {
        'lectures': lectures,
        'can_modify': can_modify
    })


@login_required
@user_passes_test(is_faculty)
def lecture_create(request):
    """Create new lecture - ONLY Faculty can create"""
    if request.method == 'POST':
        form = LectureForm(request.POST)
        if form.is_valid():
            try:
                # Check if faculty is authorized for this allocation
                faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
                allocation = form.cleaned_data['allocationid']

                if allocation.teacherid != faculty:
                    messages.error(request, 'Unauthorized to create lecture for this course')
                else:
                    # Create lecture - let DATABASE auto-generate lectureid
                    lecture = Lecture.objects.create(
                        # lectureid is auto-generated by DATABASE - don't set it!
                        allocationid=allocation,
                        lectureno=form.cleaned_data['lectureno'],
                        venue=form.cleaned_data['venue'],
                        startingtime=form.cleaned_data['startingtime'],
                        endingtime=form.cleaned_data['endingtime'],
                        topic=form.cleaned_data.get('topic', '')
                    )

                    messages.success(request, 'Lecture created successfully')
                    return redirect('faculty:lecture_list')

            except Exception as e:
                messages.error(request, f'Error creating lecture: {str(e)}')
    else:
        # Only show allocations for current faculty
        faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
        form = LectureForm()
        form.fields['allocationid'].queryset = Courseallocation.objects.filter(teacherid=faculty)

    return render(request, 'faculty/lecture_create.html', {'form': form})


@login_required
def lecture_detail(request, lecture_id):
    """View lecture details"""
    lecture = get_object_or_404(Lecture, lectureid=lecture_id)

    # Check authorization
    can_modify = False
    if is_faculty(request.user):
        faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
        can_modify = (lecture.allocationid.teacherid == faculty)
    elif is_admin(request.user):
        can_modify = False

    return render(request, 'faculty/lecture_detail.html', {
        'lecture': lecture,
        'can_modify': can_modify
    })


@login_required
@user_passes_test(is_faculty)
def lecture_update(request, lecture_id):
    """Update lecture - ONLY Faculty can update"""
    lecture = get_object_or_404(Lecture, lectureid=lecture_id)

    # Check authorization
    faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
    if lecture.allocationid.teacherid != faculty:
        messages.error(request, 'Unauthorized')
        return redirect('faculty:lecture_list')

    if request.method == 'POST':
        form = LectureForm(request.POST, instance=lecture)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Lecture updated successfully')
                return redirect('faculty:lecture_list')

            except Exception as e:
                messages.error(request, f'Error updating lecture: {str(e)}')
    else:
        form = LectureForm(instance=lecture)

    return render(request, 'faculty/lecture_edit.html', {'form': form, 'lecture': lecture})


@login_required
@user_passes_test(is_faculty)
def lecture_delete(request, lecture_id):
    """Delete lecture - ONLY Faculty can delete"""
    lecture = get_object_or_404(Lecture, lectureid=lecture_id)

    # Check authorization
    faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
    if lecture.allocationid.teacherid != faculty:
        messages.error(request, 'Unauthorized')
        return redirect('faculty:lecture_list')

    if request.method == 'POST':
        try:
            # Check if lecture has attendance records
            if Attendance.objects.filter(lectureid=lecture).exists():
                messages.error(request, 'Cannot delete lecture with existing attendance records')
            else:
                lecture.delete()
                messages.success(request, 'Lecture deleted successfully')
                return redirect('faculty:lecture_list')

        except Exception as e:
            messages.error(request, f'Error deleting lecture: {str(e)}')

    return render(request, 'faculty/lecture_confirm_delete.html', {'lecture': lecture})


# ===========================================
# ASSESSMENT MANAGEMENT VIEWS (Faculty can CRUD, Admin can VIEW only)
# ===========================================

@login_required
def assessment_list(request):
    """List assessments - faculty can modify their own, admin can view all"""
    if is_faculty(request.user):
        faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
        assessments = Assessment.objects.filter(
            allocationid__teacherid=faculty
        ).select_related('allocationid__coursecode')
        can_modify = True
    elif is_admin(request.user):
        assessments = Assessment.objects.select_related(
            'allocationid__coursecode', 'allocationid__teacherid__employeeid'
        ).all()
        can_modify = False
    else:
        return redirect('login')

    # Search functionality
    search = request.GET.get('search')
    if search:
        assessments = assessments.filter(
            Q(allocationid__coursecode__coursename__icontains=search) |
            Q(allocationid__coursecode__coursecode__icontains=search) |
            Q(assessmentname__icontains=search) |
            Q(assessmenttype__icontains=search)
        )

    # Type filtering
    assessment_type = request.GET.get('type')
    if assessment_type:
        assessments = assessments.filter(assessmenttype=assessment_type)

    # Pagination
    paginator = Paginator(assessments.order_by('-assessmentdate'), 25)
    page = request.GET.get('page')
    assessments = paginator.get_page(page)

    return render(request, 'faculty/assessment_list.html', {
        'assessments': assessments,
        'can_modify': can_modify
    })


@login_required
@user_passes_test(is_faculty)
def assessment_create(request):
    """Create new assessment - ONLY Faculty can create"""
    if request.method == 'POST':
        form = AssessmentForm(request.POST)
        if form.is_valid():
            try:
                # Check if faculty is authorized for this allocation
                faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
                allocation = form.cleaned_data['allocationid']

                if allocation.teacherid != faculty:
                    messages.error(request, 'Unauthorized to create assessment for this course')
                else:
                    form.save()
                    messages.success(request, 'Assessment created successfully')
                    return redirect('faculty:assessment_list')

            except Exception as e:
                messages.error(request, f'Error creating assessment: {str(e)}')
    else:
        # Only show allocations for current faculty
        faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
        form = AssessmentForm()
        form.fields['allocationid'].queryset = Courseallocation.objects.filter(teacherid=faculty)

    return render(request, 'faculty/assessment_create.html', {'form': form})


@login_required
@user_passes_test(is_faculty)
def assessment_update(request, assessment_id):
    """Update assessment - ONLY Faculty can update"""
    assessment = get_object_or_404(Assessment, assessmentid=assessment_id)

    # Check authorization
    faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
    if assessment.allocationid.teacherid != faculty:
        messages.error(request, 'Unauthorized')
        return redirect('faculty:assessment_list')

    if request.method == 'POST':
        form = AssessmentForm(request.POST, instance=assessment)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Assessment updated successfully')
                return redirect('faculty:assessment_list')

            except Exception as e:
                messages.error(request, f'Error updating assessment: {str(e)}')
    else:
        form = AssessmentForm(instance=assessment)

    return render(request, 'faculty/assessment_edit.html', {'form': form, 'assessment': assessment})


@login_required
@user_passes_test(is_faculty)
def assessment_delete(request, assessment_id):
    """Delete assessment - ONLY Faculty can delete"""
    assessment = get_object_or_404(Assessment, assessmentid=assessment_id)

    # Check authorization
    faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
    if assessment.allocationid.teacherid != faculty:
        messages.error(request, 'Unauthorized')
        return redirect('faculty:assessment_list')

    if request.method == 'POST':
        try:
            # Check if assessment has checked records
            if Assessmentchecked.objects.filter(assessmentid=assessment).exists():
                messages.error(request, 'Cannot delete assessment with existing graded records')
            else:
                assessment.delete()
                messages.success(request, 'Assessment deleted successfully')
                return redirect('faculty:assessment_list')

        except Exception as e:
            messages.error(request, f'Error deleting assessment: {str(e)}')

    return render(request, 'faculty/assessment_confirm_delete.html', {'assessment': assessment})


# ===========================================
# ATTENDANCE MANAGEMENT VIEWS (Faculty can modify, Admin can VIEW only)
# ===========================================

@login_required
def attendance_management(request, lecture_id):
    """Manage attendance for a specific lecture"""
    lecture = get_object_or_404(Lecture, lectureid=lecture_id)

    can_modify = False
    if is_faculty(request.user):
        faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
        can_modify = (lecture.allocationid.teacherid == faculty)
    elif is_admin(request.user):
        can_modify = False

    if not can_modify and not is_admin(request.user):
        messages.error(request, 'Unauthorized')
        return redirect('login')

    # Get enrolled students for this course allocation
    enrollments = Enrollment.objects.filter(
        allocationid=lecture.allocationid
    ).select_related('studentid__studentid')

    # Get existing attendance records for this lecture
    attendance_records = Attendance.objects.filter(lectureid=lecture)
    attendance_dict = {att.studentid.studentid.personid: att for att in attendance_records}

    # Prepare student data with attendance status
    students_data = []
    for enrollment in enrollments:
        student = enrollment.studentid.studentid
        attendance_record = attendance_dict.get(student.personid)

        students_data.append({
            'student': student,
            'enrollment': enrollment,
            'is_present': attendance_record is not None,
            'attendance_record': attendance_record
        })

    if request.method == 'POST' and can_modify:
        # Handle attendance marking
        try:
            with transaction.atomic():
                today = timezone.now().date()

                for enrollment in enrollments:
                    student = enrollment.studentid
                    field_name = f'attendance_{student.studentid.personid}'
                    is_present = field_name in request.POST

                    if is_present:
                        # Check if attendance already exists for this student and lecture today
                        existing_attendance = Attendance.objects.filter(
                            lectureid=lecture,
                            studentid=student,
                            attendancedate__date=today
                        )

                        if existing_attendance.exists():
                            # Update existing attendance with current time
                            existing_attendance.update(attendancedate=timezone.now())
                        else:
                            # Create new attendance record
                            Attendance.objects.create(
                                lectureid=lecture,
                                studentid=student,
                                attendancedate=timezone.now()
                            )
                    else:
                        # Remove attendance for this student and lecture today if unchecked
                        Attendance.objects.filter(
                            lectureid=lecture,
                            studentid=student,
                            attendancedate__date=today
                        ).delete()

            messages.success(request, 'Attendance marked successfully')
            return redirect('faculty:lecture_list')

        except Exception as e:
            messages.error(request, f'Error marking attendance: {str(e)}')

    return render(request, 'faculty/attendance_management.html', {
        'lecture': lecture,
        'students_data': students_data,
        'can_modify': can_modify
    })


# ===========================================
# GRADING VIEWS (ONLY FACULTY - Admin has NO ACCESS)
# ===========================================

@login_required
@user_passes_test(is_faculty)
def assessment_grading(request, assessment_id):
    """Grade assessment for enrolled students - ONLY Faculty can access"""
    assessment = get_object_or_404(Assessment, assessmentid=assessment_id)

    # Check authorization
    faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
    if assessment.allocationid.teacherid != faculty:
        messages.error(request, 'Unauthorized')
        return redirect('faculty:assessment_list')

    # Get enrolled students for this course allocation
    enrollments = Enrollment.objects.filter(
        allocationid=assessment.allocationid
    ).select_related('studentid__studentid', 'resultid')

    # Get existing graded records
    graded_records = Assessmentchecked.objects.filter(assessmentid=assessment)
    graded_dict = {record.enrollmentid.enrollmentid: record for record in graded_records}

    # Prepare student data with grades
    students_data = []
    for enrollment in enrollments:
        student = enrollment.studentid.studentid
        graded_record = graded_dict.get(enrollment.enrollmentid)

        students_data.append({
            'enrollment': enrollment,
            'student': student,
            'obtained_marks': float(graded_record.obtained) if graded_record else 0,
            'is_graded': graded_record is not None,
            'graded_record': graded_record
        })

    if request.method == 'POST':
        # Handle grade submission
        try:
            with transaction.atomic():
                for enrollment in enrollments:
                    field_name = f'marks_{enrollment.enrollmentid}'
                    obtained_marks = request.POST.get(field_name, '0')

                    try:
                        obtained_marks = float(obtained_marks)
                    except ValueError:
                        obtained_marks = 0

                    # Validate marks
                    if obtained_marks > assessment.totalmarks:
                        messages.error(request, f'Obtained marks cannot exceed total marks ({assessment.totalmarks})')
                        break

                    # Update or create grade record
                    Assessmentchecked.objects.update_or_create(
                        assessmentid=assessment,
                        enrollmentid=enrollment,
                        defaults={
                            'obtained': obtained_marks,
                            'resultid': enrollment.result
                        }
                    )
                else:
                    messages.success(request, 'Grades submitted successfully')
                    return redirect('faculty:assessment_list')

        except Exception as e:
            messages.error(request, f'Error submitting grades: {str(e)}')

    return render(request, 'faculty/assessment_grading.html', {
        'assessment': assessment,
        'students_data': students_data
    })

# ==========================================
#    STUDENT ATTENDANCE VIEWS
# ==========================================
def is_student(user):
    """Check if user is student"""
    try:
        from StudentModule.models import Student
        return Student.objects.filter(studentid__personid=user.username).exists()
    except:
        return False


@login_required
def student_attendance_view(request, enrollment_id=None):
    """
    View for students to see their own attendance records
    """
    # Check if user is a student
    if not is_student(request.user):
        if is_admin(request.user):
            # Admin can view any student's attendance by providing enrollment_id
            if not enrollment_id:
                messages.error(request, 'Enrollment ID required for admin access')
                return redirect('student:enrollment_list')
            enrollment = get_object_or_404(Enrollment, enrollmentid=enrollment_id)
            student = enrollment.studentid
            is_own_attendance = False
        else:
            messages.error(request, 'Unauthorized access')
            return redirect('login')
    else:
        # Student viewing their own attendance
        student = get_object_or_404(Student, studentid__personid=request.user.username)
        is_own_attendance = True

    # Get all enrollments for this student
    if is_own_attendance:
        enrollments = Enrollment.objects.filter(
            studentid=student
        ).select_related('allocationid__coursecode', 'allocationid__teacherid__employeeid')
    else:
        # Admin viewing specific enrollment
        enrollments = Enrollment.objects.filter(
            studentid=student
        ).select_related('allocationid__coursecode', 'allocationid__teacherid__employeeid')

    # Prepare attendance data for each enrollment
    attendance_data = []

    for enrollment in enrollments:
        # Get all lectures for this course allocation
        lectures = Lecture.objects.filter(
            allocationid=enrollment.allocationid
        ).order_by('startingtime')

        # Get attendance records for this student in these lectures
        attendance_records = Attendance.objects.filter(
            studentid=student,
            lectureid__in=lectures
        ).select_related('lectureid')

        # Create a dictionary for quick lookup
        attendance_dict = {att.lectureid.lectureid: att for att in attendance_records}

        # Prepare lecture data with attendance status
        lecture_attendance = []
        for lecture in lectures:
            attendance_record = attendance_dict.get(lecture.lectureid)
            lecture_attendance.append({
                'lecture': lecture,
                'is_present': attendance_record is not None,
                'attendance_date': attendance_record.attendancedate if attendance_record else None
            })

        # Calculate attendance statistics
        total_lectures = lectures.count()
        attended_lectures = len([la for la in lecture_attendance if la['is_present']])
        attendance_percentage = (attended_lectures / total_lectures * 100) if total_lectures > 0 else 0

        attendance_data.append({
            'enrollment': enrollment,
            'course': enrollment.allocationid.coursecode,
            'teacher': enrollment.allocationid.teacherid.employeeid,
            'session': enrollment.allocationid.session,
            'lecture_attendance': lecture_attendance,
            'total_lectures': total_lectures,
            'attended_lectures': attended_lectures,
            'attendance_percentage': round(attendance_percentage, 2),
            'status': 'Good' if attendance_percentage >= 75 else 'Warning' if attendance_percentage >= 60 else 'Poor'
        })

    # Filter by course if requested
    course_filter = request.GET.get('course')
    if course_filter:
        attendance_data = [ad for ad in attendance_data if ad['course'].coursecode == course_filter]

    # Filter by session if requested
    session_filter = request.GET.get('session')
    if session_filter:
        attendance_data = [ad for ad in attendance_data if ad['session'] == session_filter]

    # Overall statistics
    if attendance_data:
        overall_lectures = sum(ad['total_lectures'] for ad in attendance_data)
        overall_attended = sum(ad['attended_lectures'] for ad in attendance_data)
        overall_percentage = (overall_attended / overall_lectures * 100) if overall_lectures > 0 else 0
    else:
        overall_lectures = overall_attended = overall_percentage = 0

    # Get filter options
    courses = [ad['course'] for ad in attendance_data]
    sessions = list(set(ad['session'] for ad in attendance_data if ad['session']))

    context = {
        'student': student,
        'attendance_data': attendance_data,
        'overall_lectures': overall_lectures,
        'overall_attended': overall_attended,
        'overall_percentage': round(overall_percentage, 2),
        'is_own_attendance': is_own_attendance,
        'courses': courses,
        'sessions': sessions,
        'is_admin': is_admin(request.user)
    }

    return render(request, 'student/student_attendance.html', context)


@login_required
def student_course_attendance(request, enrollment_id):
    """
    Detailed attendance view for a specific course enrollment
    """
    enrollment = get_object_or_404(Enrollment, enrollmentid=enrollment_id)

    # Check authorization
    if is_student(request.user):
        student = get_object_or_404(Student, studentid__personid=request.user.username)
        if enrollment.studentid != student:
            messages.error(request, 'Unauthorized access')
            return redirect('student:student_attendance')
    elif not is_admin(request.user):
        messages.error(request, 'Unauthorized access')
        return redirect('login')

    # Get all lectures for this course allocation
    lectures = Lecture.objects.filter(
        allocationid=enrollment.allocationid
    ).order_by('startingtime')

    # Get attendance records for this student in these lectures
    attendance_records = Attendance.objects.filter(
        studentid=enrollment.studentid,
        lectureid__in=lectures
    ).select_related('lectureid')

    # Create attendance dictionary
    attendance_dict = {att.lectureid.lectureid: att for att in attendance_records}

    # Prepare detailed lecture data
    detailed_attendance = []
    for lecture in lectures:
        attendance_record = attendance_dict.get(lecture.lectureid)
        detailed_attendance.append({
            'lecture': lecture,
            'is_present': attendance_record is not None,
            'attendance_date': attendance_record.attendancedate if attendance_record else None,
            'lecture_date': lecture.startingtime.date(),
            'lecture_time': lecture.startingtime.time(),
            'venue': lecture.venue,
            'topic': lecture.topic
        })

    # Calculate statistics
    total_lectures = lectures.count()
    attended_lectures = len([da for da in detailed_attendance if da['is_present']])
    attendance_percentage = (attended_lectures / total_lectures * 100) if total_lectures > 0 else 0

    # Group by month for better visualization
    from collections import defaultdict
    monthly_attendance = defaultdict(lambda: {'total': 0, 'attended': 0})

    for da in detailed_attendance:
        month_key = da['lecture_date'].strftime('%Y-%m')
        monthly_attendance[month_key]['total'] += 1
        if da['is_present']:
            monthly_attendance[month_key]['attended'] += 1

    # Calculate monthly percentages
    for month_data in monthly_attendance.values():
        month_data['percentage'] = (month_data['attended'] / month_data['total'] * 100) if month_data[
                                                                                               'total'] > 0 else 0

    context = {
        'enrollment': enrollment,
        'course': enrollment.allocationid.coursecode,
        'teacher': enrollment.allocationid.teacherid.employeeid,
        'session': enrollment.allocationid.session,
        'detailed_attendance': detailed_attendance,
        'total_lectures': total_lectures,
        'attended_lectures': attended_lectures,
        'attendance_percentage': round(attendance_percentage, 2),
        'monthly_attendance': dict(monthly_attendance),
        'is_admin': is_admin(request.user)
    }

    return render(request, 'student/course_attendance_detail.html', context)







# ===========================================
# ADMIN VIEW-ONLY FUNCTIONS (for Person/views.py coordination)
# ===========================================

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

    # Calculate attendance statistics
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


# ===========================================
# UTILITY VIEWS
# ===========================================

@login_required
def get_faculty_allocations(request):
    """Get allocations for a specific faculty (AJAX endpoint)"""
    faculty_id = request.GET.get('faculty_id')
    if not faculty_id:
        return JsonResponse({'success': False, 'message': 'Faculty ID required'})

    try:
        faculty = get_object_or_404(Faculty, employeeid__personid=faculty_id)
        allocations = Courseallocation.objects.filter(
            teacherid=faculty,
            status='Active'
        ).select_related('coursecode')

        data = [{
            'allocation_id': alloc.allocationid,
            'course_code': alloc.coursecode.coursecode,
            'course_name': alloc.coursecode.coursename,
            'session': alloc.session
        } for alloc in allocations]

        return JsonResponse({'success': True, 'allocations': data})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def get_course_students(request):
    """Get enrolled students for a course allocation (AJAX endpoint)"""
    allocation_id = request.GET.get('allocation_id')
    if not allocation_id:
        return JsonResponse({'success': False, 'message': 'Allocation ID required'})

    try:
        allocation = get_object_or_404(Courseallocation, allocationid=allocation_id)

        # Check authorization
        if not is_admin(request.user) and is_faculty(request.user):
            faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
            if allocation.teacherid != faculty:
                return JsonResponse({'success': False, 'message': 'Unauthorized'})

        enrollments = Enrollment.objects.filter(
            allocationid=allocation
        ).select_related('studentid__studentid')

        students = [{
            'student_id': enroll.studentid.studentid.personid,
            'student_name': f"{enroll.studentid.studentid.fname} {enroll.studentid.studentid.lname}",
            'enrollment_status': enroll.status
        } for enroll in enrollments]

        return JsonResponse({'success': True, 'students': students})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# ===========================================
# REPORTING VIEWS
# ===========================================

@login_required
def attendance_report(request):
    """Generate attendance reports"""
    if not is_admin(request.user) and not is_faculty(request.user):
        return redirect('login')

    # Filter parameters
    allocation_id = request.GET.get('allocation_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Base queryset
    if is_faculty(request.user):
        faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)
        allocations = Courseallocation.objects.filter(teacherid=faculty)
    else:
        allocations = Courseallocation.objects.all()

    # Apply filters
    if allocation_id:
        allocations = allocations.filter(allocationid=allocation_id)

    attendance_data = []
    for allocation in allocations.select_related('coursecode', 'teacherid__employeeid'):
        # Get lectures for this allocation
        lectures = Lecture.objects.filter(allocationid=allocation)

        if start_date:
            lectures = lectures.filter(startingtime__date__gte=start_date)
        if end_date:
            lectures = lectures.filter(startingtime__date__lte=end_date)

        # Get total students enrolled
        total_students = Enrollment.objects.filter(allocationid=allocation).count()

        # Calculate attendance statistics
        total_lectures = lectures.count()
        total_attendance_records = Attendance.objects.filter(
            lectureid__in=lectures
        ).count()

        if total_lectures > 0 and total_students > 0:
            attendance_percentage = (total_attendance_records / (total_lectures * total_students)) * 100
        else:
            attendance_percentage = 0

        attendance_data.append({
            'allocation': allocation,
            'total_lectures': total_lectures,
            'total_students': total_students,
            'attendance_percentage': round(attendance_percentage, 2),
            'total_attendance_records': total_attendance_records
        })

    context = {
        'attendance_data': attendance_data,
        'allocations': allocations.select_related('coursecode'),
        'is_admin': is_admin(request.user)
    }

    return render(request, 'faculty/attendance_report.html', context)


@login_required
def faculty_performance_report(request):
    """Generate faculty performance reports (Admin only)"""
    if not is_admin(request.user):
        return redirect('login')

    faculty_data = []
    for faculty in Faculty.objects.select_related('employeeid', 'departmentid'):
        # Get statistics
        total_allocations = Courseallocation.objects.filter(teacherid=faculty).count()
        active_allocations = Courseallocation.objects.filter(teacherid=faculty, status='Active').count()
        total_lectures = Lecture.objects.filter(allocationid__teacherid=faculty).count()
        total_assessments = Assessment.objects.filter(allocationid__teacherid=faculty).count()
        total_students = Enrollment.objects.filter(allocationid__teacherid=faculty).count()

        faculty_data.append({
            'faculty': faculty,
            'total_allocations': total_allocations,
            'active_allocations': active_allocations,
            'total_lectures': total_lectures,
            'total_assessments': total_assessments,
            'total_students': total_students
        })

    return render(request, 'faculty/performance_report.html', {
        'faculty_data': faculty_data
    })


# ===========================================
# FACULTY COURSE MANAGEMENT
# ===========================================

@login_required
@user_passes_test(is_admin)
def faculty_course_allocations(request, faculty_id):
    """View course allocations for a specific faculty member"""
    faculty = get_object_or_404(Faculty, employeeid__personid=faculty_id)
    allocations = Courseallocation.objects.filter(teacherid=faculty).select_related('coursecode')

    return render(request, 'faculty/faculty_allocations.html', {
        'faculty': faculty,
        'allocations': allocations
    })


@login_required
@user_passes_test(is_admin)
def faculty_lectures(request, faculty_id):
    """View lectures conducted by a specific faculty member"""
    faculty = get_object_or_404(Faculty, employeeid__personid=faculty_id)
    lectures = Lecture.objects.filter(
        allocationid__teacherid=faculty
    ).select_related('allocationid__coursecode').order_by('-startingtime')

    return render(request, 'faculty/faculty_lectures.html', {
        'faculty': faculty,
        'lectures': lectures
    })


# Add these to your FacultyModule/views.py
@login_required
def faculty_profile_api(request):
    """API endpoint for faculty profile data"""
    if not is_faculty(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)

    data = {
        'name': f"{faculty.employeeid.fname} {faculty.employeeid.lname}",
        'designation': faculty.designation,
        'department': faculty.departmentid.departmentname,
        'initials': f"{faculty.employeeid.fname[0]}{faculty.employeeid.lname[0]}".upper()
    }

    return JsonResponse(data)


@login_required
def faculty_dashboard_stats_api(request):
    """API endpoint for dashboard statistics"""
    if not is_faculty(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    faculty = get_object_or_404(Faculty, employeeid__personid=request.user.username)

    # Get statistics
    total_courses = Courseallocation.objects.filter(
        teacherid=faculty,
        status='Ongoing'
    ).count()

    total_students = Enrollment.objects.filter(
        allocationid__teacherid=faculty
    ).count()

    pending_assessments = Assessment.objects.filter(
        allocationid__teacherid=faculty,
        assessmentdate__gte=timezone.now().date()
    ).count()

    weekly_lectures = Lecture.objects.filter(
        allocationid__teacherid=faculty,
        startingtime__gte=timezone.now() - timedelta(days=7)
    ).count()

    data = {
        'total_courses': total_courses,
        'total_students': total_students,
        'pending_assessments': pending_assessments,
        'weekly_lectures': weekly_lectures
    }

    return JsonResponse(data)