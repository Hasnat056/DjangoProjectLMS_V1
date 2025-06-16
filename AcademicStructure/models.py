from django.db import models
from FacultyModule.models import *
# Create your models here.
class Department(models.Model):
    departmentid = models.AutoField(db_column='departmentID', primary_key=True)  # Field name made lowercase.
    departmentname = models.CharField(db_column='departmentName', max_length=50)  # Field name made lowercase.
    hod = models.ForeignKey('FacultyModule.Faculty', on_delete=models.SET_NULL, db_column='HOD', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        db_table = 'department'

    def __str__(self):
        return self.departmentname

class Program(models.Model):
    programid = models.CharField(db_column='programID', primary_key=True, max_length=10)  # Field name made lowercase.
    programname = models.CharField(db_column='programName', max_length=50)  # Field name made lowercase.
    fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    totalsemesters = models.IntegerField(db_column='totalSemesters')  # Field name made lowercase.
    departmentid = models.ForeignKey(Department, on_delete=models.RESTRICT, db_column='departmentID')  # Field name made lowercase.

    class Meta:
        db_table = 'program'

    def __str__(self):
        return self.programname


class Course(models.Model):
    coursecode = models.CharField(db_column='courseCode', primary_key=True, max_length=20)
    coursename = models.CharField(db_column='courseName', max_length=100)
    credithours = models.IntegerField(db_column='creditHours')
    prerequisite = models.ForeignKey('self', on_delete=models.SET_NULL, db_column='preRequisite', blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'course'




class Semester(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Completed', 'Completed'),
    ]
    semesterid = models.AutoField(db_column='semesterID', primary_key=True)  # Field name made lowercase.
    programid = models.ForeignKey(Program, on_delete=models.RESTRICT, db_column='programID')  # Field name made lowercase.
    semesterno = models.IntegerField(db_column='semesterNo')  # Field name made lowercase.
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Inactive')
    session = models.CharField(max_length=15, blank=True, null=True)

    class Meta:
        db_table = 'semester'


class Class(models.Model):
    classid = models.AutoField(db_column='classID', primary_key=True)  # Field name made lowercase.
    programid = models.ForeignKey('Program', on_delete=models.RESTRICT, db_column='programID')  # Field name made lowercase.
    batchyear = models.TextField(db_column='batchYear')  # Field name made lowercase. This field type is a guess.

    class Meta:
        db_table = 'class'

    def __str__(self):
        return f"{self.programid.programid}-{self.batchyear}"


class Semesterdetails(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)
    semesterid = models.ForeignKey(Semester, on_delete=models.CASCADE, db_column='semesterID')  # Field name made lowercase.
    coursecode = models.ForeignKey(Course, on_delete=models.RESTRICT, db_column='courseCode')  # Field name made lowercase.
    classid = models.ForeignKey(Class, on_delete=models.RESTRICT, db_column='classID')  # Field name made lowercase.


    class Meta:
        db_table = 'semesterdetails'
        unique_together = ('semesterid', 'coursecode', 'classid')