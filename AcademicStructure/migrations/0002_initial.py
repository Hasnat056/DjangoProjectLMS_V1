# Generated by Django 5.2.1 on 2025-06-03 11:13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('AcademicStructure', '0001_initial'),
        ('FacultyModule', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='department',
            name='hod',
            field=models.ForeignKey(blank=True, db_column='HOD', null=True, on_delete=django.db.models.deletion.SET_NULL, to='FacultyModule.faculty'),
        ),
        migrations.AddField(
            model_name='program',
            name='departmentid',
            field=models.ForeignKey(db_column='departmentID', on_delete=django.db.models.deletion.RESTRICT, to='AcademicStructure.department'),
        ),
        migrations.AddField(
            model_name='course',
            name='programid',
            field=models.ForeignKey(db_column='programID', on_delete=django.db.models.deletion.RESTRICT, to='AcademicStructure.program'),
        ),
        migrations.AddField(
            model_name='class',
            name='programid',
            field=models.ForeignKey(db_column='programID', on_delete=django.db.models.deletion.RESTRICT, to='AcademicStructure.program'),
        ),
        migrations.AddField(
            model_name='semester',
            name='programid',
            field=models.ForeignKey(db_column='programID', on_delete=django.db.models.deletion.RESTRICT, to='AcademicStructure.program'),
        ),
        migrations.AddField(
            model_name='semesterdetails',
            name='classid',
            field=models.ForeignKey(db_column='classID', on_delete=django.db.models.deletion.RESTRICT, to='AcademicStructure.class'),
        ),
        migrations.AddField(
            model_name='semesterdetails',
            name='coursecode',
            field=models.ForeignKey(db_column='courseCode', on_delete=django.db.models.deletion.RESTRICT, to='AcademicStructure.course'),
        ),
        migrations.AddField(
            model_name='semesterdetails',
            name='semesterid',
            field=models.ForeignKey(db_column='semesterID', on_delete=django.db.models.deletion.CASCADE, to='AcademicStructure.semester'),
        ),
        migrations.AlterUniqueTogether(
            name='semesterdetails',
            unique_together={('semesterid', 'coursecode', 'classid')},
        ),
    ]
