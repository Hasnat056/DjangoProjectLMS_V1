# Generated by Django 5.2.1 on 2025-06-13 07:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AcademicStructure', '0007_alter_semester_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='semesterdetails',
            name='session',
        ),
        migrations.AddField(
            model_name='semester',
            name='session',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
