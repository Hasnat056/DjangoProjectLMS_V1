# accounts/views.py - Final working version
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json

from Person.models import Person, Admin
from FacultyModule.models import Faculty
from StudentModule.models import Student
from .forms import RegistrationForm

# Map role strings to model classes
ROLE_MODEL_MAP = {
    "admin": Admin,
    "faculty": Faculty,
    "student": Student,
}

# Role-based redirect URLs
ROLE_REDIRECT_MAP = {
    "Admin": "/person/admin/dashboard/",
    "Faculty": "/faculty/dashboard/",
    "Student": "/person/student/dashboard/",
}


@require_http_methods(["POST"])
def register_view(request):
    """Handle registration via AJAX"""
    try:
        # Get data from POST request
        first_name = request.POST.get("firstName", "").strip()
        last_name = request.POST.get("lastName", "").strip()
        email = request.POST.get("Username", "").lower().strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirmPassword", "")
        chosen_role = request.POST.get("role", "").lower()

        # Basic validation
        if not all([first_name, last_name, email, password, confirm_password]):
            return JsonResponse({"error": "All fields are required"}, status=400)

        if len(password) < 8:
            return JsonResponse({"error": "Password must be at least 8 characters long"}, status=400)

        if password != confirm_password:
            return JsonResponse({"error": "Passwords do not match"}, status=400)

        if chosen_role not in ROLE_MODEL_MAP:
            return JsonResponse({"error": "Invalid role selected"}, status=400)

        # Check if user already exists
        if User.objects.filter(username=email).exists():
            return JsonResponse({"error": "User with this email already exists"}, status=400)

        # Check if Person record exists
        try:
            person = Person.objects.get(
                fname__iexact=first_name,
                lname__iexact=last_name,
                institutionalemail__iexact=email
            )
        except Person.DoesNotExist:
            return JsonResponse({
                "error": "No matching record found for that name and email. Please contact administration."
            }, status=400)

        # Check if person is authorized for this role
        RoleModel = ROLE_MODEL_MAP[chosen_role]
        try:
            if chosen_role in ["admin", "faculty"]:
                # Admin and Faculty models use employeeid field
                role_instance = RoleModel.objects.get(employeeid__personid=person.personid)
            else:
                # Student model uses studentid field
                role_instance = RoleModel.objects.get(studentid__personid=person.personid)

        except RoleModel.DoesNotExist:
            return JsonResponse({
                "error": f"You are not authorized as a {chosen_role}. Please contact administration."
            }, status=400)

        # Check if person hasn't already registered
        if person.user is not None:
            return JsonResponse({"error": "This account has already been registered"}, status=400)

        # Create the user
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )

        # Add user to appropriate group
        role_name = chosen_role.capitalize()
        group_obj, created = Group.objects.get_or_create(name=role_name)
        user.groups.add(group_obj)

        # Set admin privileges if needed
        if chosen_role == "admin":
            user.is_staff = True
            user.save()

        # Link person to user
        person.user = user
        person.save()

        # Auto-login the user
        login(request, user)

        return JsonResponse({
            "success": "Registration successful! Redirecting to your dashboard...",
            "redirect_url": ROLE_REDIRECT_MAP.get(role_name, "/")
        }, status=200)

    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Registration error: {str(e)}")

        return JsonResponse({"error": "Registration failed. Please try again."}, status=500)


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Handle login via standard form submission"""

    if request.method == "GET":
        # Show login form
        return render(request, 'accounts/login.html')  # Replace with your actual template

    # Handle POST request
    try:
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Email and password are required")
            return render(request, 'accounts/login.html')  # Stay on login form with error

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)

                # Determine redirect URL based on user's role
                user_groups = user.groups.values_list('name', flat=True)
                redirect_url = "/"

                for role in ["Admin", "Faculty", "Student"]:
                    if role in user_groups:
                        redirect_url = ROLE_REDIRECT_MAP.get(role, "/")
                        break

                # Add success message
                messages.success(request, "Login successful! Welcome back.")

                # Return HTTP redirect, not JSON
                return redirect(redirect_url)
            else:
                messages.error(request, "Your account has been deactivated")
                return render(request, 'accounts/login.html')
        else:
            messages.error(request, "Invalid email or password")
            return render(request, 'accounts/login.html')

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Login error: {str(e)}")
        messages.error(request, "Login failed. Please try again.")
        return render(request, 'accounts/login.html')


@login_required
def user_logout(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect("accounts:home")