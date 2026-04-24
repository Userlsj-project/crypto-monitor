"""
WSGI 설정 파일
Gunicorn이 Django 앱을 서빙하기 위한 진입점
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
