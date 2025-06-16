# account/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# Change ROLE_CHOICES to capitalized strings ("Admin", "Faculty", "Student"),
# because views.py expects exactly those keys in ROLE_MODEL_MAP.
ROLE_CHOICES = [
    ("Admin", "Admin"),
    ("Faculty", "Faculty"),
    ("Student", "Student"),
]

class RegistrationForm(UserCreationForm):
    # Override “username” so it’s really an EmailField,
    # but label it “Username” on screen
    username = forms.EmailField(
        label="Username",
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com"})
    )

    # Explicitly add first_name / last_name (UserCreationForm doesn’t do this by default)
    first_name = forms.CharField(
        label="First Name",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "First name"})
    )
    last_name = forms.CharField(
        label="Last Name",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Last name"})
    )

    # “role” as a dropdown
    role = forms.ChoiceField(choices=ROLE_CHOICES, required=True)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",   # which is really email
            "password1",
            "password2",
            "role",
        ]

    def clean_username(self):
        """
        Ensure no one has already registered with that email/username.
        """
        email = self.cleaned_data["username"]
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("A user with that email/username already exists.")
        return email

    def save(self, commit=True):
        """
        1. Take first_name/last_name from this form.
        2. Assign user.username ← the email
        3. Assign user.email ← the same email (so that email field is set as well).
        4. If role == "Admin", make user.is_staff = True (optional).
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data["username"]      # store the same email
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]

        # If you want Admins to be staff immediately:
        if self.cleaned_data["role"] == "Admin":
            user.is_staff = True
            # user.is_superuser = True    # uncomment if you want true superuser
        if commit:
            user.save()
        return user
