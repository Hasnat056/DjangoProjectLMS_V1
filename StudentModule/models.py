from django.db import models
from django.db.models import Q
from django.db.models.constraints import CheckConstraint

import Person.models
from Person.models import *
from AcademicStructure.models import *
# Create your models here.


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Dropped', 'Dropped'),
    ]
    enrollmentid = models.AutoField(db_column='enrollmentID', primary_key=True)  # Field name made lowercase.
    studentid = models.ForeignKey('Student', on_delete=models.CASCADE, db_column='studentID')  # Field name made lowercase.
    allocationid = models.ForeignKey('FacultyModule.Courseallocation', on_delete=models.CASCADE, db_column='allocationID')  # Field name made lowercase.
    enrollmentdate = models.DateTimeField(db_column='enrollmentDate')  # Field name made lowercase.
    status = models.CharField(max_length=9, default='Active', choices=STATUS_CHOICES, db_column='status')

    class Meta:
        db_table = 'enrollment'
        unique_together = (('studentid', 'allocationid'),)


class Reviews(models.Model):
    reviewid = models.AutoField(db_column='reviewID', primary_key=True)  # Field name made lowercase.
    enrollmentid = models.ForeignKey(Enrollment, on_delete=models.CASCADE, db_column='enrollmentID')  # Field name made lowercase.
    reviewtext = models.TextField(db_column='reviewText')  # Field name made lowercase.
    createdate = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.

    class Meta:
        db_table = 'reviews'


class Result(models.Model):
    resultid = models.AutoField(db_column='resultID', primary_key=True)  # Field name made lowercase.
    enrollmentid = models.OneToOneField(Enrollment, on_delete=models.CASCADE, db_column='enrollmentID')  # Field name made lowercase.
    coursegpa = models.DecimalField(db_column='courseGPA', max_digits=4, decimal_places=2)  # Field name made lowercase.
    obtainedmarks = models.DecimalField(db_column='obtainedMarks', max_digits=4, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'result'
        constraints = [
            CheckConstraint(
                check=Q(obtainedmarks__gte=0) & Q(obtainedmarks__lte=100),
                name='valid_obtained_marks_range'
            )
        ]


class Student(models.Model):
    STATUS_CHOICES = [
        ('Enrolled', 'Enrolled'),
        ('Graduated', 'Graduated'),
        ('Dropped', 'Dropped'),
    ]
    studentid = models.OneToOneField('Person.Person', on_delete=models.CASCADE, db_column='studentID', primary_key=True)  # Field name made lowercase.
    classid = models.ForeignKey('AcademicStructure.Class', on_delete=models.SET_NULL, db_column='classID', blank=True, null=True)  # Field name made lowercase.
    programid = models.ForeignKey('AcademicStructure.Program', on_delete=models.SET_NULL, db_column='programID', blank=True, null=True)  # Field name made lowercase.
    status = models.CharField(max_length=9,choices=STATUS_CHOICES,default='Enrolled')

    class Meta:
        db_table = 'student'


class Transcript(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)
    studentid = models.ForeignKey(Student, on_delete=models.CASCADE, db_column='studentID')  # Field name made lowercase.
    semesterid = models.ForeignKey('AcademicStructure.Semester', on_delete=models.CASCADE, db_column='semesterID')  # Field name made lowercase.
    totalcredits = models.IntegerField(db_column='totalCredits')  # Field name made lowercase.
    semestergpa = models.DecimalField(db_column='semesterGPA', max_digits=4, decimal_places=2)  # Field name made lowercase.

    class Meta:
        db_table = 'transcript'
        unique_together = (('studentid', 'semesterid'),)
