"""
알림 앱 API URL 설정
/api/alerts/ 하위 경로
"""
from django.urls import path
from .views import (
    AlertListCreateAPIView,
    AlertDetailAPIView,
    AlertToggleAPIView,
    AlertLogListAPIView,
)

urlpatterns = [
    # GET/POST /api/alerts/ - 알림 목록 및 생성
    path('', AlertListCreateAPIView.as_view(), name='alert-list-create'),

    # GET /api/alerts/logs/ - 알림 발동 기록
    path('logs/', AlertLogListAPIView.as_view(), name='alert-log-list'),

    # GET/PUT/DELETE /api/alerts/<id>/ - 알림 상세/수정/삭제
    path('<int:pk>/', AlertDetailAPIView.as_view(), name='alert-detail'),

    # PATCH /api/alerts/<id>/toggle/ - 활성화 토글
    path('<int:pk>/toggle/', AlertToggleAPIView.as_view(), name='alert-toggle'),
]
