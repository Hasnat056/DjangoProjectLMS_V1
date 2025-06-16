from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Audittrail, Person, Admin, Salary, Qualification, Address
from StudentModule.models import Student, Enrollment, Result, Reviews, Transcript
from FacultyModule.models import Faculty, Courseallocation, Lecture, Assessment, Attendance, Assessmentchecked
from AcademicStructure.models import Program, Course, Semester, Semesterdetails, Class


# Get client IP address helper function
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# Store request in thread local storage for access in signals
import threading
_thread_locals = threading.local()

def set_current_request(request):
    _thread_locals.request = request

def get_current_request():
    return getattr(_thread_locals, 'request', None)


# Helper function to get current user's Person record
def get_current_user_person(request):
    """Get the Person record of the currently logged-in user (admin/faculty/student)"""
    if not request or not request.user.is_authenticated:
        return None

    try:
        # Username is institutional email, find the Person record
        person = Person.objects.get(institutionalemail=request.user.username)
        return person
    except Person.DoesNotExist:
        return None


# Universal audit logging function
def log_audit_trail(request, action_type, entity_name, target_id=None):
    """Universal function to log audit trail for any action"""
    current_user_person = get_current_user_person(request)

    if current_user_person:
        Audittrail.objects.create(
            userid=current_user_person,  # WHO performed the action
            actiontype=action_type,  # CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT
            entityname=entity_name,  # What entity was affected
            timestamp=timezone.now(),
            ipaddress=get_client_ip(request) if request else '127.0.0.1',
            useragent=request.META.get('HTTP_USER_AGENT', '') if request else ''
        )



# ADMIN SIGNALS
@receiver(post_save, sender=Admin)
def log_admin_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Admin')


# STUDENT SIGNALS
@receiver(post_save, sender=Student)
def log_student_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Student')


@receiver(post_delete, sender=Student)
def log_student_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Student')


# FACULTY SIGNALS
@receiver(post_save, sender=Faculty)
def log_faculty_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Faculty')


@receiver(post_delete, sender=Faculty)
def log_faculty_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Faculty')


# ENROLLMENT SIGNALS
@receiver(post_save, sender=Enrollment)
def log_enrollment_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Enrollment')


@receiver(post_delete, sender=Enrollment)
def log_enrollment_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Enrollment')


# COURSE ALLOCATION SIGNALS
@receiver(post_save, sender=Courseallocation)
def log_allocation_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'CourseAllocation')


@receiver(post_delete, sender=Courseallocation)
def log_allocation_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'CourseAllocation')


# COURSE SIGNALS
@receiver(post_save, sender=Course)
def log_course_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Course')


@receiver(post_delete, sender=Course)
def log_course_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Course')


# PROGRAM SIGNALS
@receiver(post_save, sender=Program)
def log_program_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Program')


@receiver(post_delete, sender=Program)
def log_program_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Program')


# Lecture SIGNALS
@receiver(post_save, sender=Lecture)
def log_lecture_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Lecture')


@receiver(post_delete, sender=Lecture)
def log_lecture_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Lecture')

# Attendance SIGNALS
@receiver(post_save, sender=Attendance)
def log_attendance_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Attendance')


@receiver(post_delete, sender=Attendance)
def log_attendance_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Attendance')

# Assessment SIGNALS
@receiver(post_save, sender=Assessment)
def log_assessment_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Assessment')


@receiver(post_delete, sender=Assessment)
def log_assessment_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Assessment')

# AssessmentChecked SIGNALS
@receiver(post_save, sender=Assessmentchecked)
def log_assessmentChecked_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Assessmentchecked')


@receiver(post_delete, sender=Assessmentchecked)
def log_assessmentChecked_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Assessmentchecked')

# RESULT SIGNALS
@receiver(post_save, sender=Result)
def log_result_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Result')


@receiver(post_delete, sender=Result)
def log_result_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Result')

# TRANSCRIPT SIGNALS
@receiver(post_save, sender=Transcript)
def log_transcript_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Transcript')


@receiver(post_delete, sender=Transcript)
def log_transcript_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Transcript')

# REVIEWS SIGNALS
@receiver(post_save, sender=Reviews)
def log_reviews_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Reviews')


@receiver(post_delete, sender=Reviews)
def log_reviews_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Reviews')

# Salary SIGNALS
@receiver(post_save, sender=Salary)
def log_salary_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Salary')


@receiver(post_delete, sender=Salary)
def log_salary_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Salary')

# SEMESTER SIGNALS
@receiver(post_save, sender=Semester)
def log_semester_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Semester')


@receiver(post_delete, sender=Semester)
def log_semester_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Semester')


# SEMESTERDETAILS SIGNALS
@receiver(post_save, sender=Semesterdetails)
def log_semesterdetails_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Semesterdetails')


@receiver(post_delete, sender=Semesterdetails)
def log_semesterdetails_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Semesterdetails')


# QUALIFICATIONS SIGNALS
@receiver(post_save, sender=Qualification)
def log_qualification_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Qualification')


@receiver(post_delete, sender=Qualification)
def log_qualification_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Qualification')

# ADDRESS SIGNALS
@receiver(post_save, sender=Address)
def log_address_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Address')


@receiver(post_delete, sender=Address)
def log_address_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Address')


# CLASS SIGNALS
@receiver(post_save, sender=Class)
def log_class_audit(sender, instance, created, **kwargs):
    request = get_current_request()
    action_type = 'CREATE' if created else 'UPDATE'
    log_audit_trail(request, action_type, 'Class')


@receiver(post_delete, sender=Class)
def log_class_delete_audit(sender, instance, **kwargs):
    request = get_current_request()
    log_audit_trail(request, 'DELETE', 'Class')

# LOGIN/LOGOUT SIGNALS
from django.contrib.auth.signals import user_logged_in, user_logged_out


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    log_audit_trail(request, 'LOGIN', 'User')


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    log_audit_trail(request, 'LOGOUT', 'User')