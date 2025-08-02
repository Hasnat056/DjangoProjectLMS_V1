# FacultyModule/forms.py - Complete Django Forms for Faculty Module
from django import forms
from django.utils import timezone
from datetime import  date
from django.core.exceptions import ValidationError
from datetime import datetime
# Model imports
from Person.models import Person,  Address
from .models import Faculty, Courseallocation, Lecture, Assessment
from AcademicStructure.models import Department, Course



class FacultyForm(forms.ModelForm):
    """
    Form for creating/updating Faculty members with Person integration and dynamic qualifications
    """
    # Person fields (for inheritance)
    employeeid = forms.CharField(
        max_length=20,
        label='Employee ID',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter unique employee ID'
        }),
        help_text='This will be used as the Person ID'
    )

    fname = forms.CharField(
        max_length=100,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )

    lname = forms.CharField(
        max_length=100,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )

    institutionalemail = forms.EmailField(
        label='Institutional Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'employee@institution.edu'
        }),
        help_text='Official institutional email address'
    )

    personalemail = forms.EmailField(
        required=False,
        label='Personal Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'personal@email.com'
        })
    )

    cnic = forms.CharField(
        max_length=15,
        required=True,
        label='CNIC',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12345-1234567-1'
        }),
        help_text='National Identity Card Number'
    )

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other')
    ]

    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        initial='M',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    dob = forms.DateField(
        required=False,
        label='Date of Birth',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
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
        model = Faculty
        fields = ['designation', 'departmentid', 'joiningdate']
        widgets = {
            'designation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Assistant Professor, Lecturer'
            }),
            'departmentid': forms.Select(attrs={'class': 'form-control'}),
            'joiningdate': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'designation': 'Designation',
            'departmentid': 'Department',
            'joiningdate': 'Joining Date',
        }
        help_texts = {
            'designation': 'Academic position or title',
            'joiningdate': 'Date when faculty member joined the institution'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set default joining date to today
        if not self.instance.pk:
            self.fields['joiningdate'].initial = date.today()

        self.fields['departmentid'] = forms.ModelChoiceField(
            queryset=Department.objects.all(),
            widget=forms.Select(attrs={'class': 'form-control'}),
            label='Department',
            empty_label="Select Department",
            to_field_name='departmentid',
        )

        # If updating, populate Person fields
        if self.instance.pk and hasattr(self.instance, 'employeeid'):
            person = self.instance.employeeid
            self.fields['employeeid'].initial = person.personid
            self.fields['fname'].initial = person.fname
            self.fields['lname'].initial = person.lname
            self.fields['institutionalemail'].initial = person.institutionalemail
            self.fields['personalemail'].initial = person.personalemail
            self.fields['cnic'].initial = person.cnic
            self.fields['gender'].initial = person.gender
            self.fields['dob'].initial = person.dob
            self.fields['cnumber'].initial = person.cnumber

            # FIXED: Set department value for update
            if self.instance.departmentid:
                self.fields['departmentid'].initial = str(self.instance.departmentid.departmentid)

            # Address fields initial values
            try:
                address = Address.objects.get(personid=person)
                self.fields['country'].initial = address.country
                self.fields['province'].initial = address.province
                self.fields['city'].initial = address.city
                self.fields['zipcode'].initial = address.zipcode
                self.fields['streetaddress'].initial = address.streetaddress
            except Address.DoesNotExist:
                self.fields['country'].initial = 'Pakistan'
                self.fields['province'].initial = ''
                self.fields['city'].initial = ''
                self.fields['zipcode'].initial = 0
                self.fields['streetaddress'].initial = ''

            # Make employee ID read-only for updates
            self.fields['employeeid'].widget.attrs['readonly'] = True

    def clean_employeeid(self):
        employeeid = self.cleaned_data['employeeid']

        # Check if Person with this ID already exists (for create)
        if not self.instance.pk:
            if Person.objects.filter(personid=employeeid).exists():
                raise ValidationError('A person with this Employee ID already exists.')

        return employeeid

    def clean_institutionalemail(self):
        email = self.cleaned_data['institutionalemail']

        # Check for duplicate institutional email
        existing_person = Person.objects.filter(institutionalemail=email)
        if self.instance.pk and hasattr(self.instance, 'employeeid'):
            existing_person = existing_person.exclude(personid=self.instance.employeeid.personid)

        if existing_person.exists():
            raise ValidationError('This institutional email is already in use.')

        return email

    def clean_dob(self):
        dob = self.cleaned_data.get('dob')
        if dob:
            # Check if date of birth is not in the future
            if dob > date.today():
                raise ValidationError('Date of birth cannot be in the future.')

            # Check if person is at least 18 years old
            age = (date.today() - dob).days / 365.25
            if age < 18:
                raise ValidationError('Faculty member must be at least 18 years old.')

        return dob

    def clean_joiningdate(self):
        joining_date = self.cleaned_data.get('joiningdate')
        if joining_date:
            # Joining date cannot be in the future
            if joining_date > date.today():
                raise ValidationError('Joining date cannot be in the future.')

        return joining_date


    def save_with_qualifications(self, qualifications_data, commit=True):
        """
        Custom save method to handle Person, Faculty, Address, and multiple Qualifications
        """
        from django.db import transaction
        from Person.models import Person, Address, Qualification

        if commit:
            with transaction.atomic():
                # Handle new faculty creation
                if not self.instance.pk:
                    # Create Person record
                    person = Person.objects.create(
                        personid=self.cleaned_data['employeeid'],
                        fname=self.cleaned_data['fname'],
                        lname=self.cleaned_data['lname'],
                        institutionalemail=self.cleaned_data['institutionalemail'],
                        personalemail=self.cleaned_data.get('personalemail', ''),
                        cnic=self.cleaned_data.get('cnic', ''),
                        gender=self.cleaned_data.get('gender', 'M'),
                        dob=self.cleaned_data.get('dob'),
                        cnumber=self.cleaned_data.get('cnumber', ''),
                        type='Faculty'
                    )

                    # Create Faculty record
                    self.instance.employeeid = person

                    faculty = super().save(commit=True)

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
                    # Handle existing faculty update
                    person = self.instance.employeeid

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


                    # Update Faculty record
                    faculty = super().save(commit=True)

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

                return faculty
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
                # Handle new faculty creation
                if not self.instance.pk:
                    # Create Person record
                    person = Person.objects.create(
                        personid=self.cleaned_data['employeeid'],
                        fname=self.cleaned_data['fname'],
                        lname=self.cleaned_data['lname'],
                        institutionalemail=self.cleaned_data['institutionalemail'],
                        personalemail=self.cleaned_data.get('personalemail', ''),
                        cnic=self.cleaned_data.get('cnic', ''),
                        gender=self.cleaned_data.get('gender', 'M'),
                        dob=self.cleaned_data.get('dob'),
                        cnumber=self.cleaned_data.get('cnumber', ''),
                        type='Faculty'
                    )

                    # Create Faculty record
                    self.instance.employeeid = person

                    # FIXED: Handle department assignment
                    department_id = self.cleaned_data.get('departmentid')
                    department_id = int(department_id)
                    if department_id:
                        try:
                            department = Department.objects.get(pk=department_id)
                            self.instance.departmentid = department
                        except Department.DoesNotExist:
                            pass

                    faculty = super().save(commit=True)

                    # Create Address record
                    Address.objects.create(
                        personid=person,
                        country=self.cleaned_data.get('country', 'Pakistan'),
                        province=self.cleaned_data.get('province', ''),
                        city=self.cleaned_data.get('city', ''),
                        zipcode=self.cleaned_data.get('zipcode', 0),
                        streetaddress=self.cleaned_data.get('streetaddress', '')
                    )

                else:
                    # Handle existing faculty update
                    person = self.instance.employeeid

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

                    # FIXED: Handle department assignment for update
                    department_id = self.cleaned_data.get('departmentid')
                    if department_id:
                        try:
                            department = Department.objects.get(departmentid=department_id)
                            self.instance.departmentid = department
                        except Department.DoesNotExist:
                            pass

                    # Update Faculty record
                    faculty = super().save(commit=True)

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

                return faculty
        else:
            return super().save(commit=False)

class CourseAllocationForm(forms.ModelForm):
    """
    Form for creating/updating Course Allocations
    """


    class Meta:
        model = Courseallocation
        fields = ['teacherid', 'coursecode', 'session', 'status']
        widgets = {
            'teacherid': forms.Select(attrs={'class': 'form-control'}),
            'coursecode': forms.Select(attrs={'class': 'form-control'}),
            'session': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Spring 2025, Fall 2024'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'teacherid': 'Faculty Member',
            'coursecode': 'Course',
            'session': 'Academic Session',
            'status': 'Allocation Status',
        }
        help_texts = {
            'session': 'Academic session for this allocation',
            'status': 'Current status of the allocation'
        }

    STATUS_CHOICES = [
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate faculty choices with readable names
        self.fields['teacherid'].queryset = Faculty.objects.select_related('employeeid').all()
        self.fields['teacherid'].empty_label = "Select Faculty Member"

        # Custom label for faculty display
        faculty_choices = []
        for faculty in Faculty.objects.select_related('employeeid'):
            label = f"{faculty.employeeid.fname} {faculty.employeeid.lname} ({faculty.designation})"
            faculty_choices.append((faculty.pk, label))

        if faculty_choices:
            self.fields['teacherid'].choices = [('', 'Select Faculty Member')] + faculty_choices

        # Populate course choices
        course_choices = []
        for course in Course.objects.all():
            label = f"{course.coursecode} - {course.coursename}"
            course_choices.append((course.pk, label))

        if course_choices:
            self.fields['coursecode'].choices = [('', 'Select Course')] + course_choices


        self.fields['status'].choices = [('', 'Select Status')] + self.STATUS_CHOICES
        # Only set initial for create, not edit
        if not self.instance.pk:
            self.fields['status'].initial = 'Ongoing'

        # Set default session to current
        if not self.instance.pk:
            current_year = datetime.now().year
            current_month = datetime.now().month
            if current_month >= 8:  # Fall semester
                self.fields['session'].initial = f"Fall {current_year}"
            elif current_month >= 1 and current_month <= 5:  # Spring semester
                self.fields['session'].initial = f"Spring {current_year}"
            else:  # Summer semester
                self.fields['session'].initial = f"Summer {current_year}"

    def clean(self):
        cleaned_data = super().clean()
        teacherid = cleaned_data.get('teacherid')
        coursecode = cleaned_data.get('coursecode')
        session = cleaned_data.get('session')

        # Check for duplicate allocation
        if teacherid and coursecode and session:
            existing = Courseallocation.objects.filter(
                teacherid=teacherid,
                coursecode=coursecode,
                session=session
            )

            # Exclude current instance for updates
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError('This faculty member is already allocated to this course in this session.')

        return cleaned_data


class BulkCourseAllocationForm(forms.Form):
    """
    Form for creating multiple Course Allocations at once
    """

    BULK_MODE_CHOICES = [
        ('faculty_to_course', 'Multiple Faculty → Single Course'),
        ('course_to_faculty', 'Multiple Courses → Single Faculty'),
    ]

    STATUS_CHOICES = [
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    # Mode selection
    bulk_mode = forms.ChoiceField(
        choices=BULK_MODE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'mode-radio'}),
        label='Allocation Mode',
        initial='faculty_to_course'
    )

    # Common fields
    session = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Spring 2025, Fall 2024'
        }),
        label='Academic Session',
        help_text='Academic session for these allocations'
    )

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Allocation Status',
        initial='Ongoing'
    )

    # Mode 1: Multiple Faculty → Single Course
    single_course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        empty_label="Select Course",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Course',
        required=False
    )

    multiple_faculty = forms.ModelMultipleChoiceField(
        queryset=Faculty.objects.select_related('employeeid').all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'faculty-checkbox'}),
        label='Select Faculty Members',
        required=False
    )

    # Mode 2: Multiple Courses → Single Faculty
    single_faculty = forms.ModelChoiceField(
        queryset=Faculty.objects.select_related('employeeid').all(),
        empty_label="Select Faculty Member",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Faculty Member',
        required=False
    )

    multiple_courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'course-checkbox'}),
        label='Select Courses',
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set default session to current
        current_year = datetime.now().year
        current_month = datetime.now().month
        if current_month >= 8:  # Fall semester
            self.fields['session'].initial = f"Fall {current_year}"
        elif current_month >= 1 and current_month <= 5:  # Spring semester
            self.fields['session'].initial = f"Spring {current_year}"
        else:  # Summer semester
            self.fields['session'].initial = f"Summer {current_year}"

        # Customize course choices display
        course_choices = []
        for course in Course.objects.all():
            label = f"{course.coursecode} - {course.coursename}"
            course_choices.append((course.pk, label))

        if course_choices:
            self.fields['single_course'].choices = [('', 'Select Course')] + course_choices

        # Customize faculty choices display
        faculty_choices = []
        for faculty in Faculty.objects.select_related('employeeid'):
            label = f"{faculty.employeeid.fname} {faculty.employeeid.lname} ({faculty.designation})"
            faculty_choices.append((faculty.pk, label))

        if faculty_choices:
            self.fields['single_faculty'].choices = [('', 'Select Faculty Member')] + faculty_choices

    def clean(self):
        cleaned_data = super().clean()
        bulk_mode = cleaned_data.get('bulk_mode')
        session = cleaned_data.get('session')

        if bulk_mode == 'faculty_to_course':
            single_course = cleaned_data.get('single_course')
            multiple_faculty = cleaned_data.get('multiple_faculty')

            if not single_course:
                raise ValidationError('Please select a course for faculty allocation.')

            if not multiple_faculty:
                raise ValidationError('Please select at least one faculty member.')

            # Check for existing allocations
            conflicts = []
            for faculty in multiple_faculty:
                existing = Courseallocation.objects.filter(
                    teacherid=faculty,
                    coursecode=single_course,
                    session=session
                )
                if existing.exists():
                    faculty_name = f"{faculty.employeeid.fname} {faculty.employeeid.lname}"
                    conflicts.append(faculty_name)

            if conflicts:
                conflict_list = ", ".join(conflicts)
                raise ValidationError(
                    f'The following faculty members are already allocated to this course in this session: {conflict_list}')

        elif bulk_mode == 'course_to_faculty':
            single_faculty = cleaned_data.get('single_faculty')
            multiple_courses = cleaned_data.get('multiple_courses')

            if not single_faculty:
                raise ValidationError('Please select a faculty member for course allocation.')

            if not multiple_courses:
                raise ValidationError('Please select at least one course.')

            # Check for existing allocations
            conflicts = []
            for course in multiple_courses:
                existing = Courseallocation.objects.filter(
                    teacherid=single_faculty,
                    coursecode=course,
                    session=session
                )
                if existing.exists():
                    course_name = f"{course.coursecode} - {course.coursename}"
                    conflicts.append(course_name)

            if conflicts:
                conflict_list = ", ".join(conflicts)
                raise ValidationError(
                    f'This faculty member is already allocated to the following courses in this session: {conflict_list}')

        return cleaned_data

    def create_allocations(self):
        """Create the bulk allocations and return the count of created allocations"""
        cleaned_data = self.cleaned_data
        bulk_mode = cleaned_data['bulk_mode']
        session = cleaned_data['session']
        status = cleaned_data['status']

        created_count = 0

        if bulk_mode == 'faculty_to_course':
            single_course = cleaned_data['single_course']
            multiple_faculty = cleaned_data['multiple_faculty']

            for faculty in multiple_faculty:
                Courseallocation.objects.create(
                    teacherid=faculty,
                    coursecode=single_course,
                    session=session,
                    status=status
                )
                created_count += 1

        elif bulk_mode == 'course_to_faculty':
            single_faculty = cleaned_data['single_faculty']
            multiple_courses = cleaned_data['multiple_courses']

            for course in multiple_courses:
                Courseallocation.objects.create(
                    teacherid=single_faculty,
                    coursecode=course,
                    session=session,
                    status=status
                )
                created_count += 1

        return created_count

class LectureForm(forms.ModelForm):
    """
    Form for creating/updating Lectures
    """

    class Meta:
        model = Lecture
        fields = ['allocationid', 'lectureno', 'venue', 'startingtime', 'endingtime', 'topic']
        widgets = {
            'allocationid': forms.Select(attrs={'class': 'form-control'}),
            'lectureno': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Lecture number'
            }),
            'venue': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Room 101, Lab A, Online'
            }),
            'startingtime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'endingtime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'topic': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Lecture topic or description'
            }),
        }
        labels = {
            'allocationid': 'Course Allocation',
            'lectureno': 'Lecture Number',
            'venue': 'Venue',
            'startingtime': 'Start Time',
            'endingtime': 'End Time',
            'topic': 'Lecture Topic',
        }
        help_texts = {
            'lectureno': 'Sequential number of the lecture',
            'venue': 'Location where the lecture will be conducted',
            'topic': 'Brief description of the lecture content'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate allocation choices with readable names
        allocation_choices = []
        for allocation in Courseallocation.objects.select_related('coursecode', 'teacherid__employeeid'):
            label = f"{allocation.coursecode.coursecode} - {allocation.coursecode.coursename} ({allocation.session})"
            allocation_choices.append((allocation.allocationid, label))

        if allocation_choices:
            self.fields['allocationid'].choices = [('', 'Select Course Allocation')] + allocation_choices
        else:
            self.fields['allocationid'].empty_label = "No course allocations available"

        # Set default times
        if not self.instance.pk:
            now = timezone.now()
            # Round to next hour
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timezone.timedelta(hours=1)
            self.fields['startingtime'].initial = next_hour
            self.fields['endingtime'].initial = next_hour + timezone.timedelta(hours=1)

    def clean(self):
        cleaned_data = super().clean()
        startingtime = cleaned_data.get('startingtime')
        endingtime = cleaned_data.get('endingtime')
        allocationid = cleaned_data.get('allocationid')
        lectureno = cleaned_data.get('lectureno')

        # Validate time logic
        if startingtime and endingtime:
            if endingtime <= startingtime:
                raise ValidationError('End time must be after start time.')

            # Check if lecture duration is reasonable (max 4 hours)
            duration = endingtime - startingtime
            if duration.total_seconds() > 4 * 3600:  # 4 hours
                raise ValidationError('Lecture duration cannot exceed 4 hours.')

            # Check if start time is not too far in the past
            if startingtime < timezone.now() - timezone.timedelta(days=1):
                raise ValidationError('Lecture start time cannot be more than 1 day in the past.')

        # Check for duplicate lecture number in the same allocation
        if allocationid and lectureno:
            existing = Lecture.objects.filter(
                allocationid=allocationid,
                lectureno=lectureno
            )

            # Exclude current instance for updates
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError('A lecture with this number already exists for this course allocation.')

        return cleaned_data


class AssessmentForm(forms.ModelForm):
    """
    Form for creating/updating Assessments
    """
    ASSESSMENT_TYPES = [
        ('Quiz', 'Quiz'),
        ('Assignment', 'Assignment'),
        ('Midterm', 'Midterm Exam'),
        ('Final', 'Final Exam'),
        ('Project', 'Project'),
        ('Presentation', 'Presentation'),
        ('Lab', 'Lab Assessment'),
        ('Other', 'Other'),
    ]

    class Meta:
        model = Assessment
        fields = ['allocationid', 'assessmentname', 'assessmenttype', 'assessmentdate', 'weightage', 'totalmarks']
        widgets = {
            'allocationid': forms.Select(attrs={'class': 'form-control'}),
            'assessmentname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Quiz 1, Midterm Exam, Final Project'
            }),
            'assessmenttype': forms.Select(attrs={'class': 'form-control'}),
            'assessmentdate': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'weightage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 100,
                'placeholder': 'Weight percentage (1-100)',
                'step': 1
            }),
            'totalmarks': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 1000,
                'placeholder': 'Total marks for this assessment'
            }),
        }
        labels = {
            'allocationid': 'Course Allocation',
            'assessmentname': 'Assessment Name',
            'assessmenttype': 'Assessment Type',
            'assessmentdate': 'Assessment Date',
            'weightage': 'Weightage (%)',
            'totalmarks': 'Total Marks',
        }
        help_texts = {
            'assessmentname': 'Descriptive name for the assessment',
            'assessmenttype': 'Type/category of the assessment',
            'assessmentdate': 'Date when the assessment will be conducted',
            'weightage': 'Weight percentage of this assessment in final grade (1-100)',
            'totalmarks': 'Maximum marks that can be obtained'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set assessment type choices
        self.fields['assessmenttype'].choices = self.ASSESSMENT_TYPES

        # Populate allocation choices with readable names
        allocation_choices = []
        for allocation in Courseallocation.objects.select_related('coursecode', 'teacherid__employeeid'):
            label = f"{allocation.coursecode.coursecode} - {allocation.coursecode.coursename} ({allocation.session})"
            allocation_choices.append((allocation.allocationid, label))

        if allocation_choices:
            self.fields['allocationid'].choices = [('', 'Select Course Allocation')] + allocation_choices
        else:
            self.fields['allocationid'].empty_label = "No course allocations available"





    def clean_totalmarks(self):
        totalmarks = self.cleaned_data.get('totalmarks')

        if totalmarks is not None:
            if totalmarks <= 0:
                raise ValidationError('Total marks must be greater than 0.')
            if totalmarks > 100:
                raise ValidationError('Total marks cannot exceed 100.')

        return totalmarks

    def clean_weightage(self):
        weightage = self.cleaned_data.get('weightage')

        if weightage is not None:
            if weightage <= 0:
                raise ValidationError('Weightage must be greater than 0.')
            if weightage > 100:
                raise ValidationError('Weightage cannot exceed 100%.')

        return weightage

    def clean(self):
        cleaned_data = super().clean()
        allocationid = cleaned_data.get('allocationid')
        assessmentname = cleaned_data.get('assessmentname')
        assessmentdate = cleaned_data.get('assessmentdate')

        # Check for duplicate assessment name in the same allocation
        if allocationid and assessmentname:
            existing = Assessment.objects.filter(
                allocationid=allocationid,
                assessmentname__iexact=assessmentname  # Case-insensitive
            )

            # Exclude current instance for updates
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError('An assessment with this name already exists for this course allocation.')

        return cleaned_data


class AttendanceMarkingForm(forms.Form):
    """
    Dynamic form for marking attendance for a specific lecture
    """

    def __init__(self, *args, **kwargs):
        lecture = kwargs.pop('lecture', None)
        super().__init__(*args, **kwargs)

        if lecture:
            # Get enrolled students for this lecture's allocation
            from StudentModule.models import Enrollment
            enrollments = Enrollment.objects.filter(
                allocationid=lecture.allocationid
            ).select_related('studentid__studentid')

            # Create a checkbox field for each student
            for enrollment in enrollments:
                student = enrollment.studentid.studentid
                field_name = f'attendance_{student.personid}'

                self.fields[field_name] = forms.BooleanField(
                    required=False,
                    label=f"{student.fname} {student.lname} ({student.personid})",
                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                )


class GradingForm(forms.Form):
    """
    Dynamic form for grading students on an assessment
    """

    def __init__(self, *args, **kwargs):
        assessment = kwargs.pop('assessment', None)
        super().__init__(*args, **kwargs)

        if assessment:
            # Get enrolled students for this assessment's allocation
            from StudentModule.models import Enrollment
            enrollments = Enrollment.objects.filter(
                allocationid=assessment.allocationid
            ).select_related('studentid__studentid')

            # Create a number field for each student
            for enrollment in enrollments:
                student = enrollment.studentid.studentid
                field_name = f'marks_{enrollment.enrollmentid}'

                self.fields[field_name] = forms.DecimalField(
                    required=True,
                    label=f"{student.fname} {student.lname} ({student.personid})",
                    max_digits=6,
                    decimal_places=2,
                    min_value=0,
                    max_value=assessment.totalmarks,
                    initial=0,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'step': '0.01',
                        'min': '0',
                        'max': str(assessment.totalmarks),
                        'placeholder': f'0 - {assessment.totalmarks}'
                    })
                )

    def clean(self):
        cleaned_data = super().clean()

        # Validate that all marks are within the valid range
        for field_name, value in cleaned_data.items():
            if field_name.startswith('marks_') and value is not None:
                # Additional validation can be added here if needed
                pass

        return cleaned_data


class FacultySearchForm(forms.Form):
    """
    Form for searching and filtering faculty members
    """
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, email, or employee ID...'
        }),
        label='Search Faculty'
    )

    department = forms.ModelChoiceField(
        required=False,
        queryset=Department.objects.all(),
        empty_label="All Departments",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Department'
    )

    designation = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Professor, Lecturer'
        }),
        label='Designation'
    )


class AllocationSearchForm(forms.Form):
    """
    Form for searching and filtering course allocations
    """
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by course, faculty, or session...'
        }),
        label='Search Allocations'
    )

    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + CourseAllocationForm.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Status'
    )

    department = forms.ModelChoiceField(
        required=False,
        queryset=Department.objects.all(),
        empty_label="All Departments",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Department'
    )

    session = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Spring 2025'
        }),
        label='Session'
    )

