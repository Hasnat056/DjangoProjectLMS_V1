# StudentModule/forms.py - Complete Form Definitions (Model-Compatible)
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, RegexValidator
from datetime import datetime, date
from decimal import Decimal

# Model imports
from Person.models import Person, Qualification, Address
from .models import Student, Enrollment, Result, Reviews, Transcript
from AcademicStructure.models import Program, Class, Semester
from FacultyModule.models import Courseallocation


class StudentForm(forms.ModelForm):
    """Form for creating/updating students with Person integration and dynamic qualifications"""

    # Person fields (not in Student model directly)
    studentid = forms.CharField(
        max_length=20,
        label='Student ID',
        help_text='Unique student identifier',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., NUM-BSCS-2023-01',
            'pattern': '[A-Z]{3}-[A-Z]{3,8}-[0-9]{4}-[0-9]{2}',
            'title': 'Format: NUM-BSCS-2023-01',
        })
    )

    fname = forms.CharField(
        max_length=50,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )

    lname = forms.CharField(
        max_length=50,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )

    institutionalemail = forms.EmailField(
        max_length=50,
        label='Institutional Email',
        validators=[EmailValidator()],
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'student@university.edu'
        })
    )

    personalemail = forms.EmailField(
        max_length=50,
        label='Personal Email',
        required=False,
        validators=[EmailValidator()],
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'personal@email.com (optional)'
        })
    )

    cnic = forms.CharField(
        max_length=15,
        label='CNIC',
        validators=[RegexValidator(
            regex=r'^\d{5}-\d{7}-\d{1}$',
            message='CNIC must be in format: 12345-1234567-1'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12345-1234567-1',
            'pattern': '[0-9]{5}-[0-9]{7}-[0-9]{1}'
        })
    )

    gender = forms.ChoiceField(
        choices=[('M', 'Male'), ('F', 'Female')],
        label='Gender',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    dob = forms.DateField(
        label='Date of Birth',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    cnumber = forms.CharField(
        max_length=15,
        label='Contact Number',
        validators=[RegexValidator(
            regex=r'^\+92[0-9]{10}$|^0[0-9]{10}$',
            message='Phone must be in format: +92xxxxxxxxxx or 0xxxxxxxxxx'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+92xxxxxxxxxx or 0xxxxxxxxxx'
        })
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

    # Province choices
    PROVINCE_CHOICES = [
        ('', 'Select Province'),
        ('Islamabad', 'Islamabad'),
        ('Punjab', 'Punjab'),
        ('Sindh', 'Sindh'),
        ('Khyber Pakhtunkhwa', 'Khyber Pakhtunkhwa'),
        ('Balochistan', 'Balochistan'),
        ('Azad Jammu and Kashmir', 'Azad Jammu and Kashmir'),
    ]


    province = forms.ChoiceField(
        choices=PROVINCE_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'onchange': 'filterEducationBoards(this.value)'
        }),
        label='Province'
    )

    city = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City'
        })
    )

    zipcode = forms.IntegerField(
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

    class Meta:
        model = Student
        fields = ['programid', 'classid', 'status']
        widgets = {
            'programid': forms.Select(attrs={
                'class': 'form-control',
                'onchange': 'loadProgramClasses(this.value)'
            }),
            'classid': forms.Select(attrs={
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set choices for status
        self.fields['status'].choices = [
            ('', 'Select Status'),
            ('Enrolled', 'Enrolled'),
            ('Graduated', 'Graduated'),
            ('Dropped', 'Dropped')
        ]

        # Load program choices
        self.fields['programid'].queryset = Program.objects.all()
        self.fields['programid'].empty_label = "Select Program"

        # Load class choices
        self.fields['classid'].queryset = Class.objects.all()
        self.fields['classid'].empty_label = "Select Class"
        self.fields['classid'].required = False

        # If editing existing student, populate Person fields
        if self.instance and self.instance.pk:
            person = self.instance.studentid
            self.fields['studentid'].initial = person.personid
            self.fields['fname'].initial = person.fname
            self.fields['lname'].initial = person.lname
            self.fields['institutionalemail'].initial = person.institutionalemail
            self.fields['personalemail'].initial = person.personalemail
            self.fields['cnic'].initial = person.cnic
            self.fields['gender'].initial = person.gender
            self.fields['dob'].initial = person.dob
            self.fields['cnumber'].initial = person.cnumber

            # Address fields initial values
            try:
                address = Address.objects.get(personid=person)
                self.fields['country'].initial = address.country
                self.fields['province'].initial = address.province
                self.fields['city'].initial = address.city
                self.fields['zipcode'].initial = address.zipcode
                self.fields['streetaddress'].initial = address.streetaddress
            except Address.DoesNotExist:
                # Set defaults if no address exists
                self.fields['country'].initial = ''
                self.fields['province'].initial = ''
                self.fields['city'].initial = ''
                self.fields['zipcode'].initial = ''
                self.fields['streetaddress'].initial = ''

            # Make studentid read-only for existing records
            self.fields['studentid'].widget.attrs['readonly'] = True

    def clean_dob(self):
        dob = self.cleaned_data.get('dob')
        if dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 16:
                raise ValidationError('Student must be at least 16 years old')
            if age > 80:
                raise ValidationError('Invalid date of birth')
        return dob

    def clean_institutionalemail(self):
        email = self.cleaned_data.get('institutionalemail')
        if email:
            # Check for unique institutional email (excluding current instance)
            existing = Person.objects.filter(institutionalemail=email)
            if self.instance and self.instance.pk:
                existing = existing.exclude(personid=self.instance.studentid.personid)
            if existing.exists():
                raise ValidationError('This institutional email is already in use')
        return email

    def clean_studentid(self):
        studentid = self.cleaned_data.get('studentid')
        if studentid:
            # Check for unique student ID (excluding current instance)
            existing = Person.objects.filter(personid=studentid)
            if self.instance and self.instance.pk:
                existing = existing.exclude(personid=self.instance.studentid.personid)
            if existing.exists():
                raise ValidationError('This student ID is already in use')
        return studentid

    def save_with_qualifications(self, qualifications_data, commit=True):
        """
        Custom save method to handle Person, Student, Address, and multiple Qualifications
        """
        from django.db import transaction
        from Person.models import Person, Address, Qualification

        if commit:
            with transaction.atomic():
                # Handle new student creation
                if not self.instance.pk:
                    # Create Person record
                    person = Person.objects.create(
                        personid=self.cleaned_data['studentid'],
                        fname=self.cleaned_data['fname'],
                        lname=self.cleaned_data['lname'],
                        institutionalemail=self.cleaned_data['institutionalemail'],
                        personalemail=self.cleaned_data.get('personalemail', ''),
                        cnic=self.cleaned_data.get('cnic', ''),
                        gender=self.cleaned_data.get('gender', 'M'),
                        dob=self.cleaned_data.get('dob'),
                        cnumber=self.cleaned_data.get('cnumber', ''),
                        type='Student'
                    )

                    # Create Student record
                    self.instance.studentid = person
                    student = super().save(commit=True)

                    # Create Address record
                    Address.objects.create(
                        personid=person,
                        country=self.cleaned_data.get('country', 'Pakistan'),
                        province=self.cleaned_data.get('province', ''),
                        city=self.cleaned_data.get('city', ''),
                        zipcode=self.cleaned_data.get('zipcode', 0),
                        streetaddress=self.cleaned_data.get('streetaddress', '')
                    )

                    # Create multiple Qualification records
                    for qual_data in qualifications_data:
                        if qual_data.get('degreetitle'):  # Only create if degree title exists
                            Qualification.objects.create(
                                personid=person,
                                degreetitle=qual_data.get('degreetitle', ''),
                                educationboard=qual_data.get('educationboard', ''),
                                institution=qual_data.get('institution', ''),
                                passingyear=qual_data.get('passingyear', ''),
                                totalmarks=qual_data.get('totalmarks'),
                                obtainedmarks=qual_data.get('obtainedmarks'),
                                iscurrent=1 if qual_data.get('iscurrent', False) else 0
                            )

                else:
                    # Handle existing student update
                    person = self.instance.studentid

                    # Update Person record
                    person.fname = self.cleaned_data['fname']
                    person.lname = self.cleaned_data['lname']
                    person.institutionalemail = self.cleaned_data['institutionalemail']
                    person.personalemail = self.cleaned_data.get('personalemail', '')
                    person.cnic = self.cleaned_data.get('cnic', '')
                    person.gender = self.cleaned_data.get('gender')
                    person.cnumber = self.cleaned_data.get('cnumber', '')
                    if self.cleaned_data.get('dob'):
                        person.dob = self.cleaned_data['dob']
                    person.save()

                    # Update Student record
                    student = super().save(commit=True)

                    # Update or create Address
                    Address.objects.update_or_create(
                        personid=person,
                        defaults={
                            'country': self.cleaned_data.get('country', 'Pakistan'),
                            'province': self.cleaned_data.get('province', ''),
                            'city': self.cleaned_data.get('city', ''),
                            'zipcode': self.cleaned_data.get('zipcode', 0),
                            'streetaddress': self.cleaned_data.get('streetaddress', '')
                        }
                    )

                    # Handle qualifications update
                    # Delete existing qualifications
                    Qualification.objects.filter(personid=person).delete()

                    # Create new qualifications from the dynamic form data
                    for qual_data in qualifications_data:
                        if qual_data.get('degreetitle'):
                            Qualification.objects.create(
                                personid=person,
                                degreetitle=qual_data.get('degreetitle', ''),
                                educationboard=qual_data.get('educationboard', ''),
                                institution=qual_data.get('institution', ''),
                                passingyear=qual_data.get('passingyear', ''),
                                totalmarks=qual_data.get('totalmarks'),
                                obtainedmarks=qual_data.get('obtainedmarks'),
                                iscurrent=1 if qual_data.get('iscurrent', False) else 0
                            )

                return student
        else:
            return super().save(commit=False)

    def save(self, commit=True):
        """
        Keep the original save method for backward compatibility
        This method handles single qualification (for cases where dynamic qualifications aren't used)
        """
        from django.db import transaction
        from Person.models import Person, Address, Qualification

        if commit:
            with transaction.atomic():
                # Handle new student creation
                if not self.instance.pk:
                    # Create Person record
                    person = Person.objects.create(
                        personid=self.cleaned_data['studentid'],
                        fname=self.cleaned_data['fname'],
                        lname=self.cleaned_data['lname'],
                        institutionalemail=self.cleaned_data['institutionalemail'],
                        personalemail=self.cleaned_data.get('personalemail', ''),
                        cnic=self.cleaned_data.get('cnic', ''),
                        gender=self.cleaned_data.get('gender', 'M'),
                        dob=self.cleaned_data.get('dob'),
                        cnumber=self.cleaned_data.get('cnumber', ''),
                        type='Student'
                    )

                    # Create Student record
                    self.instance.studentid = person
                    student = super().save(commit=True)

                    # Create Address record
                    Address.objects.create(
                        personid=person,
                        country=self.cleaned_data.get('country', 'Pakistan'),
                        province=self.cleaned_data.get('province', ''),
                        city=self.cleaned_data.get('city', ''),
                        zipcode=self.cleaned_data.get('zipcode', 0),
                        streetaddress=self.cleaned_data.get('streetaddress', '')
                    )

                    # Note: No qualification created in basic save method
                    # Qualifications should be handled by save_with_qualifications method

                else:
                    # Handle existing student update
                    person = self.instance.studentid

                    # Update Person record
                    person.fname = self.cleaned_data['fname']
                    person.lname = self.cleaned_data['lname']
                    person.institutionalemail = self.cleaned_data['institutionalemail']
                    person.personalemail = self.cleaned_data.get('personalemail', '')
                    person.cnic = self.cleaned_data.get('cnic', '')
                    person.gender = self.cleaned_data.get('gender')
                    person.cnumber = self.cleaned_data.get('cnumber', '')
                    if self.cleaned_data.get('dob'):
                        person.dob = self.cleaned_data['dob']
                    person.save()

                    # Update Student record
                    student = super().save(commit=True)

                    # Update or create Address
                    Address.objects.update_or_create(
                        personid=person,
                        defaults={
                            'country': self.cleaned_data.get('country', 'Pakistan'),
                            'province': self.cleaned_data.get('province', ''),
                            'city': self.cleaned_data.get('city', ''),
                            'zipcode': self.cleaned_data.get('zipcode', 0),
                            'streetaddress': self.cleaned_data.get('streetaddress', '')
                        }
                    )

                return student
        else:
            return super().save(commit=False)

class EnrollmentForm(forms.ModelForm):
    """Form for creating/updating enrollments"""

    class Meta:
        model = Enrollment
        fields = ['studentid', 'allocationid', 'status']
        widgets = {
            'studentid': forms.Select(attrs={
                'class': 'form-control'
            }),
            'allocationid': forms.Select(attrs={
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set choices for status
        self.fields['status'].choices = [
            ('Active', 'Active'),
            ('Completed', 'Completed'),
            ('Dropped', 'Dropped'),
        ]

        # Load student choices with names
        self.fields['studentid'].queryset = Student.objects.select_related('studentid').all()
        self.fields['studentid'].empty_label = "Select Student"

        # Load active allocation choices
        self.fields['allocationid'].queryset = Courseallocation.objects.filter(
            status='Active'
        ).select_related('coursecode', 'teacherid__employeeid')
        self.fields['allocationid'].empty_label = "Select Course Allocation"

        # Custom labels for better display
        self.fields['studentid'].label_from_instance = lambda \
            obj: f"{obj.studentid.fname} {obj.studentid.lname} ({obj.studentid.personid})"
        self.fields['allocationid'].label_from_instance = lambda \
            obj: f"{obj.coursecode.coursename} - {obj.teacherid.employeeid.fname} {obj.teacherid.employeeid.lname} ({obj.session})"

    def clean(self):
        cleaned_data = super().clean()
        studentid = cleaned_data.get('studentid')
        allocationid = cleaned_data.get('allocationid')

        if studentid and allocationid:
            # Check for existing enrollment
            existing = Enrollment.objects.filter(
                studentid=studentid,
                allocationid=allocationid
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(enrollmentid=self.instance.enrollmentid)

            if existing.exists():
                raise ValidationError('Student is already enrolled in this course allocation')

        return cleaned_data


class ReviewForm(forms.ModelForm):
    """Form for creating/updating course reviews"""

    class Meta:
        model = Reviews
        fields = ['enrollmentid', 'reviewtext']
        widgets = {
            'enrollmentid': forms.Select(attrs={
                'class': 'form-control'
            }),
            'reviewtext': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Write your review about the course, teaching, and overall experience...'
            })
        }

    def __init__(self, *args, **kwargs):
        # Get current user if passed (make it optional)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Load enrollment choices based on user type
        if user and hasattr(user, 'username'):
            # If user is a student, only show their enrollments
            try:
                student = Student.objects.get(studentid__personid=user.username)
                self.fields['enrollmentid'].queryset = Enrollment.objects.filter(
                    studentid=student
                ).select_related('allocationid__coursecode')
            except Student.DoesNotExist:
                # If admin or user not found, show all enrollments
                self.fields['enrollmentid'].queryset = Enrollment.objects.select_related(
                    'studentid__studentid', 'allocationid__coursecode'
                ).all()
        else:
            # If no user provided, show all enrollments (default)
            self.fields['enrollmentid'].queryset = Enrollment.objects.select_related(
                'studentid__studentid', 'allocationid__coursecode'
            ).all()

        self.fields['enrollmentid'].empty_label = "Select Enrollment"

        # Custom label for enrollments
        self.fields['enrollmentid'].label_from_instance = lambda \
            obj: f"{obj.allocationid.coursecode.coursename} - {obj.studentid.studentid.fname} {obj.studentid.studentid.lname}"

    def clean_reviewtext(self):
        reviewtext = self.cleaned_data.get('reviewtext')
        if reviewtext:
            if len(reviewtext) < 10:
                raise ValidationError('Review must be at least 10 characters long')
            if len(reviewtext) > 2000:
                raise ValidationError('Review cannot exceed 2000 characters')
        return reviewtext

    def clean_enrollmentid(self):
        enrollmentid = self.cleaned_data.get('enrollmentid')
        if enrollmentid:
            # Check if review already exists for this enrollment
            existing = Reviews.objects.filter(enrollmentid=enrollmentid)
            if self.instance and self.instance.pk:
                existing = existing.exclude(reviewid=self.instance.reviewid)

            if existing.exists():
                raise ValidationError('A review already exists for this enrollment')

        return enrollmentid

class TranscriptForm(forms.ModelForm):
    """Form for creating/updating transcript records"""

    class Meta:
        model = Transcript
        fields = ['studentid', 'semesterid', 'totalcredits', 'semestergpa']
        widgets = {
            'studentid': forms.Select(attrs={
                'class': 'form-control'
            }),
            'semesterid': forms.Select(attrs={
                'class': 'form-control'
            }),
            'totalcredits': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '30'
            }),
            'semestergpa': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.00',
                'max': '4.00',
                'step': '0.01'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load student choices
        self.fields['studentid'].queryset = Student.objects.select_related('studentid').all()
        self.fields['studentid'].empty_label = "Select Student"

        # Load semester choices
        self.fields['semesterid'].queryset = Semester.objects.select_related('programid').all()
        self.fields['semesterid'].empty_label = "Select Semester"

        # Custom labels
        self.fields['studentid'].label_from_instance = lambda \
            obj: f"{obj.studentid.fname} {obj.studentid.lname} ({obj.studentid.personid})"
        self.fields['semesterid'].label_from_instance = lambda \
            obj: f"{obj.programid.programname} - Semester {obj.semesterno}"

    def clean_totalcredits(self):
        credits = self.cleaned_data.get('totalcredits')
        if credits is not None:
            if credits < 0:
                raise ValidationError('Total credits cannot be negative')
            if credits > 30:
                raise ValidationError('Total credits cannot exceed 30 per semester')
        return credits

    def clean_semestergpa(self):
        gpa = self.cleaned_data.get('semestergpa')
        if gpa is not None:
            if gpa < Decimal('0.00'):
                raise ValidationError('GPA cannot be negative')
            if gpa > Decimal('4.00'):
                raise ValidationError('GPA cannot exceed 4.00')
        return gpa

    def clean(self):
        cleaned_data = super().clean()
        studentid = cleaned_data.get('studentid')
        semesterid = cleaned_data.get('semesterid')

        if studentid and semesterid:
            # Check for existing transcript record
            existing = Transcript.objects.filter(
                studentid=studentid,
                semesterid=semesterid
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(id=self.instance.id)

            if existing.exists():
                raise ValidationError('Transcript record already exists for this student and semester')

            # Validate that semester belongs to student's program
            if studentid.programid and semesterid.programid != studentid.programid:
                raise ValidationError('Selected semester does not belong to student\'s program')

        return cleaned_data


class ResultUpdateForm(forms.ModelForm):
    """Form for updating result GPA (Admin only)"""

    class Meta:
        model = Result
        fields = ['coursegpa']
        widgets = {
            'coursegpa': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.00',
                'max': '4.00',
                'step': '0.01'
            })
        }

    def clean_coursegpa(self):
        gpa = self.cleaned_data.get('coursegpa')
        if gpa is not None:
            if gpa < Decimal('0.00'):
                raise ValidationError('Course GPA cannot be negative')
            if gpa > Decimal('4.00'):
                raise ValidationError('Course GPA cannot exceed 4.00')
        return gpa


class StudentSearchForm(forms.Form):
    """Form for searching students"""

    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, email, or student ID...'
        })
    )

    program = forms.ModelChoiceField(
        queryset=Program.objects.all(),
        required=False,
        empty_label="All Programs",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    status = forms.ChoiceField(
        choices=[
            ('', 'All Statuses'),
            ('Active', 'Active'),
            ('Inactive', 'Inactive'),
            ('Graduated', 'Graduated'),
            ('Suspended', 'Suspended'),
            ('Dropped', 'Dropped')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class_filter = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        required=False,
        empty_label="All Classes",
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class EnrollmentSearchForm(forms.Form):
    """Form for searching enrollments"""

    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by student name or course...'
        })
    )

    status = forms.ChoiceField(
        choices=[
            ('', 'All Statuses'),
            ('Active', 'Active'),
            ('Completed', 'Completed'),
            ('Dropped', 'Dropped'),
            ('Withdrawn', 'Withdrawn')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    session = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Spring 2025'
        })
    )


class BulkStudentOperationForm(forms.Form):
    """Form for bulk student operations"""

    operation = forms.ChoiceField(
        choices=[
            ('activate', 'Activate Students'),
            ('deactivate', 'Deactivate Students'),
            ('graduate', 'Mark as Graduated'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    student_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )

    def clean_student_ids(self):
        student_ids = self.cleaned_data.get('student_ids')
        if student_ids:
            try:
                # Convert comma-separated string to list
                id_list = [id.strip() for id in student_ids.split(',') if id.strip()]
                if not id_list:
                    raise ValidationError('No students selected')
                return id_list
            except:
                raise ValidationError('Invalid student ID format')
        raise ValidationError('No students selected')


# ===========================================
# UTILITY FORMS
# ===========================================

class StudentGradeFilterForm(forms.Form):
    """Form for filtering student grades"""

    min_gpa = forms.DecimalField(
        max_digits=4,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'min': '0.00',
            'max': '4.00',
            'step': '0.01'
        })
    )

    max_gpa = forms.DecimalField(
        max_digits=4,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '4.00',
            'min': '0.00',
            'max': '4.00',
            'step': '0.01'
        })
    )


class AcademicProgressFilterForm(forms.Form):
    """Form for filtering academic progress reports"""

    program = forms.ModelChoiceField(
        queryset=Program.objects.all(),
        required=False,
        empty_label="All Programs",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    semester = forms.ModelChoiceField(
        queryset=Semester.objects.all(),
        required=False,
        empty_label="All Semesters",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    min_gpa = forms.DecimalField(
        max_digits=4,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimum GPA',
            'min': '0.00',
            'max': '4.00',
            'step': '0.01'
        })
    )
