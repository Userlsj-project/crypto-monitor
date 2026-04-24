"""
알림 앱 뷰
- REST API 뷰: 알림 CRUD, 알림 로그 조회
- 템플릿 뷰: 알림 관리 페이지
"""
import logging
from django.shortcuts import render
from django.views import View
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from apps.coins.models import Coin
from .models import Alert, AlertLog
from .serializers import AlertSerializer, AlertCreateSerializer, AlertLogSerializer

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# REST API 뷰
# ─────────────────────────────────────────

class AlertListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  /api/alerts/     - 알림 목록 조회
    POST /api/alerts/     - 알림 생성
    """
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_active', 'coin__symbol', 'condition']
    ordering_fields = ['created_at', 'target_price']
    ordering = ['-created_at']

    def get_queryset(self):
        return Alert.objects.select_related('coin').all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AlertCreateSerializer
        return AlertSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alert = serializer.save()
        # 응답은 전체 데이터 포함한 AlertSerializer로
        response_serializer = AlertSerializer(alert)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class AlertDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/alerts/<id>/ - 알림 상세 조회
    PUT    /api/alerts/<id>/ - 알림 전체 수정
    PATCH  /api/alerts/<id>/ - 알림 부분 수정 (활성화/비활성화 토글 등)
    DELETE /api/alerts/<id>/ - 알림 삭제
    """
    queryset = Alert.objects.select_related('coin').all()
    serializer_class = AlertSerializer

    def destroy(self, request, *args, **kwargs):
        alert = self.get_object()
        alert_info = str(alert)
        alert.delete()
        return Response(
            {'message': f'알림 삭제 완료: {alert_info}'},
            status=status.HTTP_200_OK,
        )


class AlertToggleAPIView(APIView):
    """
    PATCH /api/alerts/<id>/toggle/
    알림 활성화/비활성화 토글
    """

    def patch(self, request, pk):
        try:
            alert = Alert.objects.get(pk=pk)
        except Alert.DoesNotExist:
            return Response(
                {'error': '알림을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        alert.is_active = not alert.is_active
        alert.save(update_fields=['is_active'])
        return Response({
            'id': alert.id,
            'is_active': alert.is_active,
            'message': f'알림 {"활성화" if alert.is_active else "비활성화"} 완료',
        })


class AlertLogListAPIView(generics.ListAPIView):
    """
    GET /api/alerts/logs/ - 알림 발동 기록 목록
    쿼리 파라미터: coin (코인 심볼 필터), limit (기본 50)
    """
    serializer_class = AlertLogSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['alert__coin__symbol']
    ordering = ['-created_at']

    def get_queryset(self):
        limit = int(self.request.query_params.get('limit', 50))
        return AlertLog.objects.select_related(
            'alert', 'alert__coin'
        ).all()[:limit]


# ─────────────────────────────────────────
# 템플릿 뷰 (프론트엔드)
# ─────────────────────────────────────────

class AlertsPageView(View):
    """
    GET /alerts/
    알림 관리 페이지
    """

    def get(self, request):
        coins = Coin.objects.filter(is_active=True).order_by('symbol')
        alerts = Alert.objects.select_related('coin').order_by('-created_at')
        recent_logs = AlertLog.objects.select_related(
            'alert', 'alert__coin'
        ).order_by('-created_at')[:20]

        context = {
            'coins': coins,
            'alerts': alerts,
            'recent_logs': recent_logs,
        }
        return render(request, 'alerts/alerts.html', context)
