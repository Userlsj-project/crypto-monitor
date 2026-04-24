"""
코인 앱 템플릿 뷰 URL 설정
"""
from django.urls import path
from .views import DashboardView, AIAnalysisDashboardView

urlpatterns = [
    # GET / - 메인 대시보드
    path('', DashboardView.as_view(), name='dashboard'),

    # GET /ai-analysis/ - AI 분석 페이지
    path('ai-analysis/', AIAnalysisDashboardView.as_view(), name='ai-analysis'),
]
