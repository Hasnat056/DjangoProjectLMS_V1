from django.db import models
from StudentModule.models import *
from django.contrib.auth.models import User

class Person(models.Model):
    personid = models.CharField(db_column='personID', primary_key=True, max_length=20)
    fname = models.CharField(db_column='fname', max_length=50)
    lname = models.CharField(db_column='lname', max_length=50)
    personalemail = models.CharField(db_column='personalEmail', max_length=50, blank=True, null=True)
    institutionalemail = models.CharField(db_column='institutionalEmail', unique=True, max_length=50)
    cnic = models.CharField(db_column='CNIC', max_length=15)
    gender = models.CharField(db_column='gender', max_length=1)
    dob = models.DateField(db_column='DOB')
    cnumber = models.CharField(db_column='cNumber', max_length=15)
    type = models.CharField(db_column='type', max_length=7)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='userID',
    )

    class Meta:
        db_table = 'person'


class Admin(models.Model):
    employeeid = models.OneToOneField(
        'Person',
        on_delete=models.CASCADE,
        db_column='employeeID',
        primary_key=True
    )
    joiningdate = models.DateField(db_column='joiningDate')
    leavingdate = models.DateField(db_column='leavingDate', blank=True, null=True)
    officelocation = models.CharField(db_column='officeLocation', max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'admin'


class Alumni(models.Model):
    alumniid = models.OneToOneField('StudentModule.Student', on_delete=models.CASCADE, db_column='alumniID',primary_key=True)
    graduationdate = models.DateField(db_column='graduationDate')
    email = models.CharField(max_length=100, blank=True, null=True)
    employmentinfo = models.TextField(db_column='employmentInfo', blank=True, null=True)

    class Meta:
        db_table = 'alumni'


class Address(models.Model):
    personid = models.OneToOneField(
        'Person',
        on_delete=models.CASCADE,
        db_column='personID',
        primary_key=True
    )
    country = models.CharField(max_length=50)
    province = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50)
    zipcode = models.IntegerField(db_column='zipCode')
    streetaddress = models.CharField(db_column='streetAddress', max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'address'


class Audittrail(models.Model):
    auditid = models.AutoField(db_column='auditID', primary_key=True)
    userid = models.ForeignKey(
        'Person',
        on_delete=models.CASCADE,
        db_column='userID'
    )
    actiontype = models.CharField(db_column='actionType', max_length=6)
    entityname = models.CharField(db_column='entityName', max_length=50)
    timestamp = models.DateTimeField(db_column='timeStamp')
    ipaddress = models.CharField(db_column='IPaddress', max_length=45)
    useragent = models.CharField(db_column='userAgent', max_length=255)

    class Meta:
        db_table = 'audittrail'


class Qualification(models.Model):
    qualificationid = models.AutoField(db_column='qualificationID', primary_key=True)
    personid = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        db_column='personID'
    )
    degreetitle = models.CharField(db_column='degreeTitle', max_length=50)
    educationboard = models.CharField(db_column='educationBoard', max_length=20, blank=True, null=True)
    institution = models.CharField(max_length=50)
    passingyear = models.TextField(db_column='passingYear', blank=True, null=True)
    totalmarks = models.IntegerField(db_column='totalMarks', blank=True, null=True)
    obtainedmarks = models.IntegerField(db_column='obtainedMarks', blank=True, null=True)
    iscurrent = models.IntegerField(db_column='isCurrent', blank=True, null=True)

    class Meta:
        db_table = 'qualification'


class Salary(models.Model):
    salaryid = models.AutoField(db_column='salaryID', primary_key=True)
    employeeid = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        db_column='employeeID'
    )
    year = models.SmallIntegerField(blank=True, null=True)
    month = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paymentdate = models.DateField(db_column='paymentDate')

    class Meta:
        db_table = 'salary'
        unique_together = (('employeeid', 'year', 'month'),)
