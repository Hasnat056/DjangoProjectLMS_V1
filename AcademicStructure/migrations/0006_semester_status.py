# Generated by Django 5.2.1 on 2025-06-12 18:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AcademicStructure', '0005_remove_semester_fee_program_fee'),
    ]

    operations = [
        migrations.AddField(
            model_name='semester',
            name='status',
            field=models.CharField(blank=True, default='Inactive', max_length=9),
        ),
    ]
