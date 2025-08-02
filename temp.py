import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoProjectLMS_V1.settings')  # Replace with your project name
django.setup()



from Person.views import reports


if __name__ == '__main__':
    reports()