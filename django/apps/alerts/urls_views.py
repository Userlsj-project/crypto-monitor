"""
알림 앱 템플릿 뷰 URL 설정
"""
from django.urls import path
from .views import AlertsPageView

urlpatterns = [
    # GET /alerts/ - 알림 관리 페이지
    path('', AlertsPageView.as_view(), name='alerts-page'),
]
