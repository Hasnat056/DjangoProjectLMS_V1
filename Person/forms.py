# Person/forms.py - Minimal Django Forms for Person Module
from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime

# Model imports
from .models import Person, Admin, Salary, Alumni


# Fixed AdminProfileForm - Compatible with Models and Views

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from datetime import datetime
from .models import Person, Admin, Address, Qualification


class AdminProfileForm(forms.Form):
    """
    Simplified form for Admin to edit their own profile
    Only editable fields are included as form fields
    """

    # Editable fields only
    personalemail = forms.EmailField(
        required=False,
        label='Personal Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'personal@email.com'
        })
    )

    cnumber = forms.CharField(
        max_length=15,
        required=False,
        label='Contact Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+92-300-1234567'
        })
    )

    leavingdate = forms.DateField(
        required=False,
        label='Leaving Date',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text='Optional - leave blank if still employed'
    )

    officelocation = forms.CharField(
        max_length=100,
        required=False,
        label='Office Location',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Admin Block, Room 101'
        }),
        help_text='Current office location'
    )

    # Address fields
    country = forms.CharField(
        max_length=50,
        initial='Pakistan',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Country'
        })
    )

    province = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Province'
        })
    )

    city = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City'
        })
    )

    zipcode = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'ZIP Code'
        })
    )

    streetaddress = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Street Address'
        })
    )

    def __init__(self, *args, **kwargs):
        # Extract the admin instance
        self.instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)

        # Pre-populate fields if editing existing admin
        if self.instance and self.instance.pk:
            person = self.instance.employeeid

            # Pre-populate editable fields
            self.fields['personalemail'].initial = person.personalemail
            self.fields['cnumber'].initial = person.cnumber

            # Pre-populate Admin fields
            self.fields['leavingdate'].initial = self.instance.leavingdate
            self.fields['officelocation'].initial = self.instance.officelocation

            # Pre-populate Address fields
            try:
                address = Address.objects.get(personid=person)
                self.fields['country'].initial = address.country
                self.fields['province'].initial = address.province
                self.fields['city'].initial = address.city
                self.fields['zipcode'].initial = address.zipcode
                self.fields['streetaddress'].initial = address.streetaddress
            except Address.DoesNotExist:
                self.fields['country'].initial = 'Pakistan'

    def save(self, commit=True):
        """
        Custom save method to handle multiple models
        """
        if not self.instance or not self.instance.pk:
            raise ValueError("This form requires an existing Admin instance")

        admin = self.instance
        person = admin.employeeid

        if commit:
            with transaction.atomic():
                # Update only editable Person fields
                person.personalemail = self.cleaned_data.get('personalemail', '')
                person.cnumber = self.cleaned_data.get('cnumber', '')
                person.save()

                # Update Admin fields
                admin.leavingdate = self.cleaned_data.get('leavingdate')
                admin.officelocation = self.cleaned_data.get('officelocation', '')
                admin.save()

                # Update or create Address
                address, created = Address.objects.get_or_create(
                    personid=person,
                    defaults={
                        'country': self.cleaned_data.get('country', 'Pakistan'),
                        'province': self.cleaned_data.get('province', ''),
                        'city': self.cleaned_data.get('city', ''),
                        'zipcode': self.cleaned_data.get('zipcode', 0),
                        'streetaddress': self.cleaned_data.get('streetaddress', ''),
                    }
                )
                if not created:
                    address.country = self.cleaned_data.get('country', 'Pakistan')
                    address.province = self.cleaned_data.get('province', '')
                    address.city = self.cleaned_data.get('city', '')
                    address.zipcode = self.cleaned_data.get('zipcode', 0)
                    address.streetaddress = self.cleaned_data.get('streetaddress', '')
                    address.save()

        return admin

class AlumniForm(forms.ModelForm):
    """
    Form for managing Alumni records - Admin use only
    """

    class Meta:
        model = Alumni
        fields = ['alumniid', 'graduationdate', 'email', 'employmentinfo']
        widgets = {
            'alumniid': forms.Select(attrs={'class': 'form-control'}),
            'graduationdate': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'alumni@email.com'
            }),
            'employmentinfo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Current employment details, company, position, etc.'
            }),
        }
        labels = {
            'alumniid': 'Student (Now Alumni)',
            'graduationdate': 'Graduation Date',
            'email': 'Alumni Email',
            'employmentinfo': 'Employment Information',
        }
        help_texts = {
            'alumniid': 'Select the student who has graduated',
            'graduationdate': 'Date when the student graduated',
            'email': 'Current email address of the alumni',
            'employmentinfo': 'Current job details, company, achievements, etc.'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate alumni choices (only graduated students)
        from StudentModule.models import Student

        # Get students who are graduated but not yet in alumni table
        graduated_students = Student.objects.filter(status='Graduated').select_related('studentid')
        existing_alumni = Alumni.objects.values_list('alumniid', flat=True)

        available_students = graduated_students.exclude(studentid__in=existing_alumni)

        student_choices = []
        for student in available_students:
            label = f"{student.studentid.fname} {student.studentid.lname} ({student.studentid.personid}) - {student.programid.programname if student.programid else 'No Program'}"
            student_choices.append((student.studentid, label))

        # For updates, include the current alumni student
        if self.instance.pk:
            current_student = self.instance.alumniid
            current_label = f"{current_student.studentid.fname} {current_student.studentid.lname} ({current_student.studentid.personid}) - {current_student.programid.programname if current_student.programid else 'No Program'}"
            student_choices.insert(0, (current_student.studentid, current_label))

        if student_choices:
            self.fields['alumniid'].choices = [('', 'Select Graduated Student')] + student_choices
        else:
            self.fields['alumniid'].empty_label = "No graduated students available"

        # Set default graduation date to today
        if not self.instance.pk:
            self.fields['graduationdate'].initial = datetime.now().date()

    def clean_graduationdate(self):
        graduation_date = self.cleaned_data.get('graduationdate')

        if graduation_date:
            # Graduation date cannot be in the future
            if graduation_date > datetime.now().date():
                raise ValidationError('Graduation date cannot be in the future.')

            # Graduation date should not be too old (reasonable check)
            from datetime import timedelta
            if graduation_date < datetime.now().date() - timedelta(days=365 * 10):  # 10 years ago
                raise ValidationError('Graduation date seems too old. Please verify.')

        return graduation_date

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if email:
            # Check for duplicate alumni email (excluding current instance)
            existing = Alumni.objects.filter(email=email)
            if self.instance.pk:
                existing = existing.exclude(alumniid=self.instance.alumniid)

            if existing.exists():
                raise ValidationError('This email is already registered for another alumni.')

        return email

    def clean_alumniid(self):
        alumniid = self.cleaned_data.get('alumniid')

        if alumniid:
            # For new records, check if student is already an alumni
            if not self.instance.pk:
                existing = Alumni.objects.filter(alumniid=alumniid)
                if existing.exists():
                    raise ValidationError('This student is already registered as alumni.')

            # Check if the selected student is actually graduated
            if alumniid.status != 'Graduated':
                raise ValidationError('Only graduated students can be added as alumni.')

        return alumniid


class SalaryForm(forms.ModelForm):
    """
    Form for managing salary records - FIXED VERSION
    """
    MONTH_CHOICES = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]

    class Meta:
        model = Salary
        fields = ['employeeid', 'year', 'month', 'amount', 'paymentdate']
        widgets = {
            'employeeid': forms.Select(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 2000,
                'max': 2030,
                'placeholder': 'Salary year'
            }),
            'month': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Salary amount'
            }),
            'paymentdate': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'employeeid': 'Employee',
            'year': 'Year',
            'month': 'Month',
            'amount': 'Amount',
            'paymentdate': 'Payment Date',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set month choices
        self.fields['month'].choices = self.MONTH_CHOICES

        # FIXED: Populate employee choices correctly
        employee_choices = []
        for person in Person.objects.filter(type__in=['Faculty', 'Admin']):
            label = f"{person.fname} {person.lname} ({person.personid})"
            # FIXED: Use Person instance, not personid string
            employee_choices.append((person.personid, label))

        if employee_choices:
            self.fields['employeeid'].choices = [('', 'Select Employee')] + employee_choices

        # FIXED: Handle queryset for ModelChoiceField behavior
        self.fields['employeeid'].queryset = Person.objects.filter(type__in=['Faculty', 'Admin'])

        # Set default year and month
        if not self.instance.pk:
            now = datetime.now()
            self.fields['year'].initial = now.year
            self.fields['month'].initial = now.month
            self.fields['paymentdate'].initial = now.date()

    def clean_year(self):
        year = self.cleaned_data.get('year')
        current_year = datetime.now().year

        if year:
            if year < 2000:
                raise ValidationError('Year cannot be before 2000.')
            if year > current_year + 1:
                raise ValidationError('Year cannot be more than 1 year in the future.')

        return year

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        if amount is not None:
            if amount <= 0:
                raise ValidationError('Salary amount must be greater than 0.')

        return amount

    def clean(self):
        cleaned_data = super().clean()
        employeeid = cleaned_data.get('employeeid')
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')

        # Check for duplicate salary record
        if employeeid and month and year:
            existing = Salary.objects.filter(
                employeeid=employeeid,
                month=month,
                year=year
            )

            if self.instance.pk:
                existing = existing.exclude(salaryid=self.instance.salaryid)

            if existing.exists():
                raise ValidationError('Salary record already exists for this employee in this month/year.')

        return cleaned_data