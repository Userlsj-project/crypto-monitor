"""
코인 앱 API URL 설정
/api/coins/ 하위 경로
"""
from django.urls import path
from .views import (
    CoinListAPIView,
    CoinPriceHistoryAPIView,
    LatestPricesAPIView,
    AIAnalysisAPIView,
    MarketSummaryAPIView,
    OllamaHealthAPIView,
)

urlpatterns = [
    # GET /api/coins/ - 코인 목록
    path('', CoinListAPIView.as_view(), name='coin-list'),

    # GET /api/coins/latest/ - 전체 코인 최신 가격
    path('latest/', LatestPricesAPIView.as_view(), name='coin-latest-prices'),

    # GET /api/coins/<symbol>/prices/ - 특정 코인 가격 히스토리
    path('<str:symbol>/prices/', CoinPriceHistoryAPIView.as_view(), name='coin-price-history'),

    # POST /api/coins/ai-analysis/ - AI 가격 분석
    path('ai-analysis/', AIAnalysisAPIView.as_view(), name='coin-ai-analysis'),

    # GET /api/coins/market-summary/ - 전체 시장 AI 요약
    path('market-summary/', MarketSummaryAPIView.as_view(), name='market-summary'),

    # GET /api/coins/ollama-health/ - Ollama 상태 확인
    path('ollama-health/', OllamaHealthAPIView.as_view(), name='ollama-health'),
]
