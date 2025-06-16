import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoProjectLMS_V1.settings')
django.setup()

from django.contrib.auth.models import User

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'rhays056@gmail.com', 'hrsay8581')
    print('Superuser created: username=admin, password=<password>')
else:
    print('Superuser already exists')