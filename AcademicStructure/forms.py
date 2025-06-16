# AcademicStructure/forms.py - Complete Django Forms for Academic Structure
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, date

# Model imports
from .models import Department, Program, Course, Semester, Semesterdetails, Class


class ProgramForm(forms.ModelForm):
    """
    Form for creating/updating Academic Programs
    """

    class Meta:
        model = Program
        fields = ['programid', 'programname', 'departmentid', 'totalsemesters','fee']
        widgets = {
            'programid': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., CS-BS, EE-MS',
                'maxlength': 20
            }),
            'programname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Bachelor of Science in Computer Science'
            }),
            'departmentid': forms.Select(attrs={'class': 'form-control'}),
            'totalsemesters': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 12,
                'placeholder': 'Number of semesters in the program'
            }),
            'fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'placeholder': 'Semester fee (optional)'
            }),
        }
        labels = {
            'programid': 'Program ID',
            'programname': 'Program Name',
            'departmentid': 'Department',
            'totalsemesters': 'Total Semesters',
            'fee': 'Fee per Semester',
        }
        help_texts = {
            'programid': 'Unique identifier for the program (e.g., CS-BS)',
            'programname': 'Full name of the academic program',
            'totalsemesters': 'Number of semesters in the complete program',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate department choices
        self.fields['departmentid'].queryset = Department.objects.all()
        self.fields['departmentid'].empty_label = "Select Department"

        # Make program ID readonly for updates
        if self.instance.pk:
            self.fields['programid'].widget.attrs['readonly'] = True
            self.fields['programid'].help_text = 'Program ID cannot be changed after creation'

    def clean_programid(self):
        programid = self.cleaned_data['programid'].upper()

        # Check if Program ID already exists (for create)
        if not self.instance.pk:
            if Program.objects.filter(programid=programid).exists():
                raise ValidationError('A program with this ID already exists.')

        # Validate format (should contain letters and possibly hyphens)
        if not programid.replace('-', '').isalnum():
            raise ValidationError('Program ID should contain only letters, numbers, and hyphens.')

        return programid

    def clean_totalsemesters(self):
        total_semesters = self.cleaned_data.get('totalsemesters')

        if total_semesters:
            if total_semesters < 1:
                raise ValidationError('Total semesters must be at least 1.')
            if total_semesters > 12:
                raise ValidationError('Total semesters cannot exceed 12.')

        return total_semesters


    def clean(self):
        cleaned_data = super().clean()

        return cleaned_data


class CourseForm(forms.ModelForm):
    """
    Form for creating/updating Courses
    """

    class Meta:
        model = Course
        fields = ['coursecode', 'coursename', 'credithours', 'description', 'prerequisite']
        widgets = {
            'coursecode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., CS101, MATH201',
                'maxlength': 20
            }),
            'coursename': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Introduction to Programming'
            }),
            'credithours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 6,
                'placeholder': 'Credit hours (1-6)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Brief description of the course content and objectives'
            }),
            'prerequisite': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'coursecode': 'Course Code',
            'coursename': 'Course Name',
            'credithours': 'Credit Hours',
            'description': 'Course Description',
            'prerequisite': 'Prerequisite Course',
        }
        help_texts = {
            'coursecode': 'Unique course identifier (e.g., CS101)',
            'coursename': 'Full name of the course',
            'credithours': 'Number of credit hours for this course',
            'description': 'Detailed description of course content',
            'prerequisite': 'Course that must be completed before taking this course'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate prerequisite choices (exclude self)
        courses_queryset = Course.objects.all()
        if self.instance.pk:
            courses_queryset = courses_queryset.exclude(coursecode=self.instance.coursecode)

        self.fields['prerequisite'].queryset = courses_queryset
        self.fields['prerequisite'].empty_label = "No Prerequisite"

        # Make course code readonly for updates
        if self.instance.pk:
            self.fields['coursecode'].widget.attrs['readonly'] = True
            self.fields['coursecode'].help_text = 'Course code cannot be changed after creation'

    def clean_coursecode(self):
        coursecode = self.cleaned_data['coursecode'].upper()

        # Check if Course Code already exists (for create)
        if not self.instance.pk:
            if Course.objects.filter(coursecode=coursecode).exists():
                raise ValidationError('A course with this code already exists.')

        # Validate format (should start with letters followed by numbers)
        import re
        if not re.match(r'^[A-Z]{2,4}\d{3,4}$', coursecode):
            raise ValidationError(
                'Course code should be in format like CS101, MATH1001 (2-4 letters followed by 3-4 digits).')

        return coursecode

    def clean_credithours(self):
        credithours = self.cleaned_data.get('credithours')

        if credithours:
            if credithours < 1:
                raise ValidationError('Credit hours must be at least 1.')
            if credithours > 6:
                raise ValidationError('Credit hours cannot exceed 6.')

        return credithours

    def clean_prerequisite(self):
        prerequisite = self.cleaned_data.get('prerequisite')

        # Prevent circular prerequisites
        if prerequisite and self.instance.pk:
            if prerequisite.coursecode == self.instance.coursecode:
                raise ValidationError('A course cannot be its own prerequisite.')

            # Check for circular dependency (prerequisite's prerequisite is this course)
            if prerequisite.prerequisite and prerequisite.prerequisite.coursecode == self.instance.coursecode:
                raise ValidationError('This would create a circular prerequisite dependency.')

        return prerequisite


class SemesterForm(forms.ModelForm):
    """
    Form for creating/updating Semesters
    """

    class Meta:
        model = Semester
        fields = ['programid', 'semesterno','session']
        widgets = {
            'programid': forms.Select(attrs={'class': 'form-control'}),
            'semesterno': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10,
                'placeholder': 'Semester number'
            }),
            'session': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Fall2024, Spring2025',
                'maxlength': 15
            })
        }
        labels = {
            'programid': 'Program',
            'semesterno': 'Semester Number',
            'session': 'Academic Session',
        }
        help_texts = {
            'programid': 'Academic program this semester belongs to',
            'semesterno': 'Sequential number of the semester (1, 2, 3, ...)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate program choices with readable names
        self.fields['programid'].queryset = Program.objects.select_related('departmentid').all()
        self.fields['programid'].empty_label = "Select Program"

        # Custom labels for programs
        program_choices = []
        for program in Program.objects.select_related('departmentid'):
            label = f"{program.programname} ({program.departmentid.departmentname})"
            program_choices.append((program.programid, label))

        if program_choices:
            self.fields['programid'].choices = [('', 'Select Program')] + program_choices

    def clean(self):
        cleaned_data = super().clean()
        programid = cleaned_data.get('programid')
        semesterno = cleaned_data.get('semesterno')

        if programid and semesterno:
            # Check if semester number is within program's total semesters
            if semesterno > programid.totalsemesters:
                raise ValidationError(f'Semester number cannot exceed {programid.totalsemesters} for this program.')

            # Check if semester already exists for this program
            existing = Semester.objects.filter(programid=programid, semesterno=semesterno)
            if self.instance.pk:
                existing = existing.exclude(semesterid=self.instance.semesterid)

            if existing.exists():
                raise ValidationError(f'Semester {semesterno} already exists for this program.')

        return cleaned_data


class SemesterdetailsForm(forms.ModelForm):
    """
    Form for creating/updating Semester Details (Course assignments to semesters)
    """

    class Meta:
        model = Semesterdetails
        fields = ['semesterid', 'coursecode', 'classid']
        widgets = {
            'semesterid': forms.Select(attrs={'class': 'form-control'}),
            'coursecode': forms.Select(attrs={'class': 'form-control'}),
            'classid': forms.Select(attrs={'class': 'form-control'}),

        }
        labels = {
            'semesterid': 'Semester',
            'coursecode': 'Course',
            'classid': 'Class',

        }
        help_texts = {
            'semesterid': 'Semester to assign the course to',
            'coursecode': 'Course to be offered in this semester',
            'classid': 'Class that will take this course'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate semester choices with readable names
        semester_choices = []
        for semester in Semester.objects.select_related('programid'):
            label = f"{semester.programid.programname} - Semester {semester.semesterno}"
            semester_choices.append((semester.semesterid, label))

        if semester_choices:
            self.fields['semesterid'].choices = [('', 'Select Semester')] + semester_choices
        else:
            self.fields['semesterid'].empty_label = "No semesters available"

        # Populate course choices
        self.fields['coursecode'].queryset = Course.objects.all()
        self.fields['coursecode'].empty_label = "Select Course"

        # Populate class choices with readable names
        class_choices = []
        for class_obj in Class.objects.select_related('programid'):
            label = f"{class_obj.programid.programname} - {class_obj.batchyear}"
            class_choices.append((class_obj.classid, label))

        if class_choices:
            self.fields['classid'].choices = [('', 'Select Class')] + class_choices
        else:
            self.fields['classid'].empty_label = "No classes available"

    def clean(self):
        cleaned_data = super().clean()
        semesterid = cleaned_data.get('semesterid')
        coursecode = cleaned_data.get('coursecode')
        classid = cleaned_data.get('classid')

        if semesterid and coursecode and classid:
            # Check for duplicate assignment
            existing = Semesterdetails.objects.filter(
                semesterid=semesterid,
                coursecode=coursecode,
                classid=classid
            )

            if self.instance.pk:
                existing = existing.exclude(id=self.instance.id)

            if existing.exists():
                raise ValidationError('This course is already assigned to this semester and class.')

            # Validate that class belongs to same program as semester
            if semesterid.programid != classid.programid:
                raise ValidationError('The selected class does not belong to the same program as the semester.')

        return cleaned_data


class ClassForm(forms.ModelForm):
    """
    Form for creating/updating Classes
    """

    class Meta:
        model = Class
        fields = ['programid', 'batchyear']
        widgets = {
            'programid': forms.Select(attrs={'class': 'form-control'}),
            'batchyear': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 2000,
                'max': 3000,
                'placeholder': 'e.g., 2024'
            }),
        }
        labels = {
            'programid': 'Program',
            'batchyear': 'Batch Year',
        }
        help_texts = {
            'programid': 'Academic program this class belongs to',
            'batchyear': 'Year when this batch started (e.g., 2024)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate program choices with readable names
        self.fields['programid'].queryset = Program.objects.select_related('departmentid').all()
        self.fields['programid'].empty_label = "Select Program"

        # Custom labels for programs
        program_choices = []
        for program in Program.objects.select_related('departmentid'):
            label = f"{program.programname} ({program.departmentid.departmentname})"
            program_choices.append((program.programid, label))

        if program_choices:
            self.fields['programid'].choices = [('', 'Select Program')] + program_choices

        # Set default batch year to current year
        if not self.instance.pk:
            self.fields['batchyear'].initial = datetime.now().year

    def clean_batchyear(self):
        batchyear = self.cleaned_data.get('batchyear')
        current_year = datetime.now().year

        if batchyear:
            # Convert to integer for comparison
            try:
                batchyear = int(batchyear)
            except (ValueError, TypeError):
                raise ValidationError('Please enter a valid year.')

            if batchyear < 2000:
                raise ValidationError('Batch year cannot be before 2000.')
            if batchyear > current_year + 5:
                raise ValidationError(f'Batch year cannot be more than 5 years in the future.')

        return str(batchyear) if batchyear else None

    def clean(self):
        cleaned_data = super().clean()
        programid = cleaned_data.get('programid')
        batchyear = cleaned_data.get('batchyear')

        if programid and batchyear:
            # Check if class already exists for this program and batch year
            existing = Class.objects.filter(programid=programid, batchyear=batchyear)
            if self.instance.pk:
                existing = existing.exclude(classid=self.instance.classid)

            if existing.exists():
                raise ValidationError(f'A class for {programid.programname} batch {batchyear} already exists.')

        return cleaned_data


class DepartmentSearchForm(forms.Form):
    """
    Form for searching and filtering departments
    """
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by department name or HOD...'
        }),
        label='Search Departments'
    )


class ProgramSearchForm(forms.Form):
    """
    Form for searching and filtering programs
    """
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by program name or ID...'
        }),
        label='Search Programs'
    )

    department = forms.ModelChoiceField(
        required=False,
        queryset=Department.objects.all(),
        empty_label="All Departments",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Department'
    )


class CourseSearchForm(forms.Form):
    """
    Form for searching and filtering courses
    """
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by course name, code, or description...'
        }),
        label='Search Courses'
    )

    CREDIT_CHOICES = [
        ('', 'All Credit Hours'),
        (1, '1 Credit Hour'),
        (2, '2 Credit Hours'),
        (3, '3 Credit Hours'),
        (4, '4 Credit Hours'),
        (5, '5 Credit Hours'),
        (6, '6 Credit Hours'),
    ]

    credits = forms.ChoiceField(
        required=False,
        choices=CREDIT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Credit Hours'
    )

    STATUS_CHOICES = [
        ('', 'All Courses'),
        ('active', 'Actively Allocated'),
        ('inactive', 'Not Currently Allocated'),
        ('unallocated', 'Never Allocated'),
    ]

    status = forms.ChoiceField(
        required=False,
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Allocation Status'
    )


class SemesterSearchForm(forms.Form):
    """
    Form for searching and filtering semesters
    """
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by program name or ID...'
        }),
        label='Search Semesters'
    )

    program = forms.ModelChoiceField(
        required=False,
        queryset=Program.objects.all(),
        empty_label="All Programs",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Program'
    )


class SemesterdetailsSearchForm(forms.Form):
    """
    Form for searching and filtering semester details
    """
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by program, course name, or code...'
        }),
        label='Search Semester Details'
    )

    program = forms.ModelChoiceField(
        required=False,
        queryset=Program.objects.all(),
        empty_label="All Programs",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Program'
    )

    semester = forms.ModelChoiceField(
        required=False,
        queryset=Semester.objects.select_related('programid').all(),
        empty_label="All Semesters",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Semester'
    )

    class_filter = forms.ModelChoiceField(
        required=False,
        queryset=Class.objects.select_related('programid').all(),
        empty_label="All Classes",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Class'
    )


class ClassSearchForm(forms.Form):
    """
    Form for searching and filtering classes
    """
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by program name or batch year...'
        }),
        label='Search Classes'
    )

    program = forms.ModelChoiceField(
        required=False,
        queryset=Program.objects.all(),
        empty_label="All Programs",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Program'
    )


class BulkSemesterCreateForm(forms.Form):
    """
    Form for creating multiple semesters for a program at once
    """
    programid = forms.ModelChoiceField(
        queryset=Program.objects.all(),
        empty_label="Select Program",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Program',
        help_text='Program to create semesters for'
    )

    start_semester = forms.IntegerField(
        min_value=1,
        max_value=12,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Starting semester number'
        }),
        label='Start From Semester',
        help_text='Starting semester number (default: 1)'
    )

    create_all = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Create All Remaining Semesters',
        help_text='Create all semesters up to the program total'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Custom labels for programs
        program_choices = []
        for program in Program.objects.select_related('departmentid'):
            label = f"{program.programname} ({program.totalsemesters} semesters)"
            program_choices.append((program.programid, label))

        if program_choices:
            self.fields['programid'].choices = [('', 'Select Program')] + program_choices

    def clean(self):
        cleaned_data = super().clean()
        programid = cleaned_data.get('programid')
        start_semester = cleaned_data.get('start_semester')

        if programid and start_semester:
            if start_semester > programid.totalsemesters:
                raise ValidationError(f'Start semester cannot exceed {programid.totalsemesters} for this program.')

            # Check if any semesters already exist
            existing_semesters = Semester.objects.filter(
                programid=programid,
                semesterno__gte=start_semester
            ).values_list('semesterno', flat=True)

            if existing_semesters:
                existing_list = ', '.join(map(str, sorted(existing_semesters)))
                raise ValidationError(f'Some semesters already exist for this program: {existing_list}')

        return cleaned_data
