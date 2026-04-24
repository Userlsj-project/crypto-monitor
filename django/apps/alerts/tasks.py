"""
알림 조건 체크 Celery 태스크
1분마다 활성 알림의 조건을 확인하고
조건 충족 시 EXAONE AI 분석 후 n8n으로 웹훅 전송
"""
import logging
import requests
from django.conf import settings
from django.utils import timezone
from celery import shared_task
from decimal import Decimal

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.alerts.tasks.check_alerts',
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue='alerts',
)
def check_alerts(self):
    """
    1분마다 실행: 모든 활성 알림의 가격 조건 체크
    조건 충족 시:
    1. EXAONE AI 분석 요청
    2. AlertLog 저장
    3. n8n 웹훅으로 알림 전송
    """
    from .models import Alert, AlertLog
    from apps.coins.models import CoinPrice

    logger.info('알림 조건 체크 시작')

    # 활성화된 알림 목록 조회 (관련 코인도 prefetch)
    active_alerts = Alert.objects.filter(
        is_active=True,
        coin__is_active=True,
    ).select_related('coin')

    if not active_alerts.exists():
        logger.debug('활성 알림 없음 - 스킵')
        return {'checked': 0, 'triggered': 0}

    triggered_count = 0

    for alert in active_alerts:
        try:
            # 해당 코인의 최신 가격 조회
            latest_price = CoinPrice.objects.filter(
                coin=alert.coin,
            ).order_by('-timestamp').first()

            if not latest_price:
                logger.debug(f'{alert.coin.symbol}: 가격 데이터 없음 - 스킵')
                continue

            current_price = float(latest_price.price)

            # 알림 조건 체크
            if not alert.check_condition(current_price):
                continue  # 조건 미충족 - 다음 알림으로

            # ── 조건 충족! ──────────────────────────
            logger.info(
                f'알림 발동: {alert.coin.symbol} '
                f'현재가 ${current_price:,.2f} / '
                f'목표가 ${alert.target_price} ({alert.get_condition_display()})'
            )

            # 1. EXAONE AI 분석 요청
            ai_analysis = _get_ai_analysis(alert, current_price)

            # 2. 알림 메시지 생성
            condition_text = '이상' if alert.condition == 'above' else '이하'
            message = (
                f'{alert.coin.name} ({alert.coin.symbol}) 가격 알림\n'
                f'현재가: ${current_price:,.2f} USDT\n'
                f'조건: 목표가 ${alert.target_price} {condition_text}\n'
                f'시각: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'
            )

            # 3. AlertLog 저장
            alert_log = AlertLog.objects.create(
                alert=alert,
                message=message,
                ai_analysis=ai_analysis,
                triggered_price=Decimal(str(current_price)),
            )

            # 4. Alert 트리거 시각 업데이트
            alert.triggered_at = timezone.now()
            alert.save(update_fields=['triggered_at'])

            # 5. n8n 웹훅으로 알림 전송
            _send_n8n_webhook(alert, current_price, ai_analysis, alert_log)

            triggered_count += 1

        except Exception as e:
            logger.error(
                f'알림 ID={alert.id} 처리 중 오류: {e}',
                exc_info=True,
            )
            continue

    logger.info(
        f'알림 조건 체크 완료: '
        f'{active_alerts.count()}개 확인 / {triggered_count}개 발동'
    )
    return {
        'checked': active_alerts.count(),
        'triggered': triggered_count,
    }


def _get_ai_analysis(alert, current_price: float) -> str:
    """
    EXAONE AI에 알림 트리거 분석 요청
    실패 시 빈 문자열 반환 (알림 저장은 계속 진행)
    """
    from apps.coins.ai_analyzer import ollama_client
    try:
        return ollama_client.analyze_alert_trigger(
            symbol=alert.coin.symbol,
            target_price=float(alert.target_price),
            current_price=current_price,
            condition=alert.condition,
        )
    except Exception as e:
        logger.warning(f'AI 분석 실패 (알림은 저장됨): {e}')
        return ''


def _send_n8n_webhook(alert, current_price: float, ai_analysis: str, alert_log) -> None:
    """
    n8n 웹훅으로 알림 데이터 전송
    Django → n8n → 이메일 발송
    실패해도 예외 전파하지 않음
    """
    webhook_url = getattr(settings, 'N8N_WEBHOOK_URL', '')
    if not webhook_url:
        logger.debug('N8N_WEBHOOK_URL 미설정 - 웹훅 스킵')
        return

    payload = {
        'alert_id': alert.id,
        'coin_symbol': alert.coin.symbol,
        'coin_name': alert.coin.name,
        'condition': alert.condition,
        'condition_text': alert.get_condition_display(),
        'target_price': str(alert.target_price),
        'current_price': current_price,
        'ai_analysis': ai_analysis,
        'triggered_at': timezone.now().isoformat(),
        'alert_log_id': alert_log.id,
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        logger.info(f'n8n 웹훅 전송 완료: 알림 ID={alert.id}')
    except requests.exceptions.ConnectionError:
        logger.warning('n8n 웹훅 전송 실패: 서버 연결 불가')
    except requests.exceptions.Timeout:
        logger.warning('n8n 웹훅 전송 실패: 타임아웃')
    except Exception as e:
        logger.error(f'n8n 웹훅 전송 실패: {e}')
