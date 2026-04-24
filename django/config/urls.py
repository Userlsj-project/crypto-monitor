"""
URL 설정 - crypto_monitor 프로젝트
API 엔드포인트와 템플릿 뷰 URL을 통합 관리
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    """DB를 거치지 않는 헬스체크 전용 엔드포인트 (Docker healthcheck용)"""
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    # 헬스체크 (DB 미조회 - gunicorn 기동 확인만)
    path('health/', health_check),

    # Django Admin
    path('admin/', admin.site.urls),

    # ─── API 엔드포인트 ───────────────────────
    # 코인 관련 API
    path('api/coins/', include('apps.coins.urls')),
    # 알림 관련 API
    path('api/alerts/', include('apps.alerts.urls')),

    # ─── 템플릿 뷰 (프론트엔드) ──────────────
    # 메인 대시보드
    path('', include('apps.coins.urls_views')),
    # 알림 관리 페이지
    path('alerts/', include('apps.alerts.urls_views')),
]

# 개발 환경에서 미디어 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
