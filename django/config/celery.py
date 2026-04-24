"""
Celery 설정 파일
Django와 통합된 비동기 태스크 처리 설정
"""
import os
from celery import Celery
from celery.schedules import crontab

# Django 설정 모듈 지정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Celery 앱 인스턴스 생성
app = Celery('crypto_monitor')

# Django 설정에서 Celery 설정 로드 (CELERY_ 접두사 사용)
app.config_from_object('django.conf:settings', namespace='CELERY')

# 등록된 Django 앱에서 태스크 자동 탐색
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """디버그용 태스크 - Celery 연결 확인"""
    print(f'Request: {self.request!r}')
