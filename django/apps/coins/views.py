"""
코인 앱 뷰
- REST API 뷰: 코인 목록, 가격 히스토리, 최신 가격
- 템플릿 뷰: 대시보드, AI 분석 페이지
"""
import logging
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.conf import settings
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import Coin, CoinPrice
from .serializers import (
    CoinSerializer,
    CoinPriceSerializer,
    LatestCoinPriceSerializer,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# REST API 뷰
# ─────────────────────────────────────────

class CoinListAPIView(generics.ListAPIView):
    """
    GET /api/coins/
    활성화된 코인 목록 반환
    """
    serializer_class = CoinSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_active', 'symbol']
    ordering_fields = ['symbol', 'created_at']
    ordering = ['symbol']

    def get_queryset(self):
        return Coin.objects.filter(is_active=True)


class CoinPriceHistoryAPIView(generics.ListAPIView):
    """
    GET /api/coins/<symbol>/prices/
    특정 코인의 가격 히스토리 반환
    쿼리 파라미터: hours (기본 1시간), limit (기본 100)
    """
    serializer_class = CoinPriceSerializer

    def get_queryset(self):
        symbol = self.kwargs.get('symbol', '').upper()
        # hours 파라미터 (기본 1시간)
        hours = int(self.request.query_params.get('hours', 1))
        limit = int(self.request.query_params.get('limit', 100))

        from django.utils import timezone
        cutoff = timezone.now() - timezone.timedelta(hours=hours)

        return CoinPrice.objects.filter(
            coin__symbol=symbol,
            coin__is_active=True,
            timestamp__gte=cutoff,
        ).select_related('coin').order_by('-timestamp')[:limit]

    def list(self, request, *args, **kwargs):
        symbol = self.kwargs.get('symbol', '').upper()
        # 코인 존재 여부 확인
        if not Coin.objects.filter(symbol=symbol, is_active=True).exists():
            return Response(
                {'error': f'코인 {symbol}을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().list(request, *args, **kwargs)


class LatestPricesAPIView(APIView):
    """
    GET /api/coins/latest/
    전체 활성 코인의 최신 가격 반환 (메인 대시보드용)
    """

    def get(self, request):
        coins = Coin.objects.filter(is_active=True).prefetch_related('prices')
        serializer = LatestCoinPriceSerializer(coins, many=True)
        return Response(serializer.data)


class AIAnalysisAPIView(APIView):
    """
    POST /api/coins/ai-analysis/
    특정 코인의 AI 분석 요청
    Body: {"symbol": "BTCUSDT"}
    """

    def post(self, request):
        from .ai_analyzer import ollama_client

        symbol = request.data.get('symbol', '').upper()
        if not symbol:
            return Response(
                {'error': 'symbol 파라미터가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 최신 가격 데이터 조회
        try:
            coin = Coin.objects.get(symbol=symbol, is_active=True)
            latest_price = coin.prices.first()
            if not latest_price:
                return Response(
                    {'error': f'{symbol}의 가격 데이터가 없습니다.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Coin.DoesNotExist:
            return Response(
                {'error': f'코인 {symbol}을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # EXAONE 분석 요청
        analysis = ollama_client.analyze_price_movement(
            symbol=symbol,
            current_price=float(latest_price.price),
            change_24h=float(latest_price.change_24h),
            volume_24h=float(latest_price.volume_24h),
        )

        return Response({
            'symbol': symbol,
            'price': float(latest_price.price),
            'change_24h': float(latest_price.change_24h),
            'analysis': analysis,
            'timestamp': latest_price.timestamp,
        })


class MarketSummaryAPIView(APIView):
    """
    GET /api/coins/market-summary/
    전체 시장 AI 요약 생성
    """

    def get(self, request):
        from .ai_analyzer import ollama_client

        coins = Coin.objects.filter(is_active=True).prefetch_related('prices')
        coins_data = []

        for coin in coins:
            latest = coin.prices.first()
            if latest:
                coins_data.append({
                    'symbol': coin.symbol,
                    'name': coin.name,
                    'price': float(latest.price),
                    'change_24h': float(latest.change_24h),
                    'volume_24h': float(latest.volume_24h),
                })

        if not coins_data:
            return Response(
                {'error': '가격 데이터가 없습니다. 잠시 후 다시 시도하세요.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        summary = ollama_client.generate_market_summary(coins_data)

        return Response({
            'summary': summary,
            'coins_count': len(coins_data),
            'coins': coins_data,
        })


class OllamaHealthAPIView(APIView):
    """
    GET /api/coins/ollama-health/
    Ollama 서버 상태 확인
    """

    def get(self, request):
        from .ai_analyzer import ollama_client
        is_healthy = ollama_client.health_check()
        return Response({
            'status': 'ok' if is_healthy else 'error',
            'model': settings.OLLAMA_MODEL,
            'base_url': settings.OLLAMA_BASE_URL,
        })


# ─────────────────────────────────────────
# 템플릿 뷰 (프론트엔드)
# ─────────────────────────────────────────

class DashboardView(View):
    """
    GET /
    메인 대시보드 페이지 (코인 가격 카드 + Grafana 임베드)
    """

    def get(self, request):
        coins = Coin.objects.filter(is_active=True).order_by('symbol')
        context = {
            'coins': coins,
            'grafana_url': 'http://localhost:3000',
            'refresh_interval': 30000,  # 30초 (ms)
        }
        return render(request, 'coins/dashboard.html', context)


class AIAnalysisDashboardView(View):
    """
    GET /ai-analysis/
    AI 분석 페이지 (시장 요약 + 개별 코인 분석)
    """

    def get(self, request):
        coins = Coin.objects.filter(is_active=True).order_by('symbol')
        context = {
            'coins': coins,
        }
        return render(request, 'coins/ai_analysis.html', context)
