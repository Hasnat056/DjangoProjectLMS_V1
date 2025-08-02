from django.db import models
from AcademicStructure.models import *
from StudentModule.models import *

# Create your models here.
class Faculty(models.Model):
    employeeid = models.OneToOneField('Person.Person', on_delete=models.CASCADE, db_column='employeeID', primary_key=True)  # Field name made lowercase.
    designation = models.CharField(max_length=50)
    departmentid = models.ForeignKey('AcademicStructure.Department', on_delete=models.RESTRICT, db_column='departmentID')  # Field name made lowercase.
    joiningdate = models.DateField(db_column='joiningDate')  # Field name made lowercase.

    class Meta:
        db_table = 'faculty'


class Courseallocation(models.Model):

    STATUS_CHOICES = [
        ('Ongoing','Ongoing'),
        ('Completed','Completed'),
        ('Cancelled','Cancelled'),
    ]
    allocationid = models.AutoField(db_column='allocationID', primary_key=True)  # Field name made lowercase.
    teacherid = models.ForeignKey('FacultyModule.Faculty', on_delete=models.RESTRICT, db_column='teacherID')  # Field name made lowercase.
    coursecode = models.ForeignKey('AcademicStructure.Course', on_delete=models.RESTRICT, db_column='courseCode')  # Field name made lowercase.
    session = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=9, choices=STATUS_CHOICES, default='Ongoing', db_column='status')

    class Meta:
        db_table = 'courseallocation'


class Lecture(models.Model):
    allocationid = models.ForeignKey(Courseallocation, on_delete=models.CASCADE, db_column='allocationID')  # Field name made lowercase.
    lectureno = models.IntegerField(db_column='lectureNo')  # Field name made lowercase.
    lectureid = models.CharField(db_column='lectureID', primary_key=True, max_length=10)  # Field name made lowercase.
    venue = models.CharField(max_length=50)
    startingtime = models.DateTimeField(db_column='startingTime')  # Field name made lowercase.
    endingtime = models.DateTimeField(db_column='endingTime')  # Field name made lowercase.
    topic = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'lecture'


class Assessment(models.Model):
    assessmentid = models.AutoField(db_column='assessmentID', primary_key=True)  # Field name made lowercase.
    allocationid = models.ForeignKey('FacultyModule.Courseallocation', on_delete=models.CASCADE, db_column='allocationID')  # Field name made lowercase.
    assessmenttype = models.CharField(db_column='assessmentType', max_length=10)  # Field name made lowercase.
    assessmentname = models.CharField(db_column='assessmentName', max_length=20)  # Field name made lowercase.
    weightage = models.IntegerField()
    assessmentdate = models.DateField(db_column='assessmentDate', blank=True, null=True)  # Field name made lowercase.
    totalmarks = models.IntegerField(db_column='totalMarks')  # Field name made lowercase.

    class Meta:
        db_table = 'assessment'


class Assessmentchecked(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)
    assessmentid = models.ForeignKey(Assessment, on_delete=models.CASCADE, db_column='assessmentID')  # Field name made lowercase.
    enrollmentid = models.ForeignKey('StudentModule.Enrollment', on_delete=models.CASCADE, db_column='enrollmentID')  # Field name made lowercase.
    resultid = models.ForeignKey('StudentModule.Result', on_delete=models.CASCADE, db_column='resultID')  # Field name made lowercase.
    obtained = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'assessmentchecked'
        unique_together = (('assessmentid', 'enrollmentid'),)


class Attendance(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)
    attendancedate = models.DateTimeField(db_column='attendanceDate')  # Field name made lowercase.
    studentid = models.ForeignKey('StudentModule.Student', on_delete=models.CASCADE, db_column='studentID')  # Field name made lowercase.
    lectureid = models.ForeignKey('Lecture', on_delete=models.CASCADE, db_column='lectureID')  # Field name made lowercase.

    class Meta:
        db_table = 'attendance'
        unique_together = (('attendancedate', 'studentid','lectureid'),)
