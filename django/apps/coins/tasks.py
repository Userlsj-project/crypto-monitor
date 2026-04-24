"""
코인 가격 수집 Celery 태스크
Binance 공개 API에서 30초마다 BTC, ETH, BNB, XRP, SOL 가격 수집
API 키 불필요 (익명 요청)
"""
import logging
import requests
from decimal import Decimal, InvalidOperation
from django.conf import settings
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# 수집 대상 코인 심볼 (Binance USDT 페어)
TARGET_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'SOLUSDT']

# Binance 24hr 티커 API 엔드포인트
BINANCE_API_URL = 'https://api.binance.com/api/v3/ticker/24hr'


def safe_decimal(value, default=0) -> Decimal:
    """문자열/숫자를 Decimal로 안전하게 변환"""
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(str(default))


@shared_task(
    name='apps.coins.tasks.fetch_coin_prices',
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue='coins',
)
def fetch_coin_prices(self):
    """
    Binance Public API에서 코인 가격 수집 (30초마다 실행)
    수집 대상: BTC, ETH, BNB, XRP, SOL (USDT 페어)
    수집 후 PostgreSQL에 저장
    """
    from .models import Coin, CoinPrice

    logger.info(f'코인 가격 수집 시작: {", ".join(TARGET_SYMBOLS)}')

    try:
        # Binance API 호출 (API 키 불필요)
        params = [('symbol', s) for s in TARGET_SYMBOLS]
        # 여러 심볼을 한 번에 조회하기 위해 symbols 배열 파라미터 사용
        symbols_json = str(TARGET_SYMBOLS).replace("'", '"').replace(' ', '')
        response = requests.get(
            BINANCE_API_URL,
            params={'symbols': symbols_json},
            timeout=15,
            headers={'User-Agent': 'CryptoMonitor/1.0'},
        )
        response.raise_for_status()
        ticker_list = response.json()

    except requests.exceptions.ConnectionError as exc:
        logger.error(f'Binance API 연결 실패: {exc}')
        raise self.retry(exc=exc, countdown=15)

    except requests.exceptions.Timeout as exc:
        logger.error('Binance API 타임아웃')
        raise self.retry(exc=exc, countdown=10)

    except requests.exceptions.HTTPError as exc:
        logger.error(f'Binance API HTTP 오류: {exc}')
        raise self.retry(exc=exc, countdown=30)

    except Exception as exc:
        logger.error(f'Binance API 예상치 못한 오류: {exc}', exc_info=True)
        raise self.retry(exc=exc)

    # 응답이 단일 객체인 경우 리스트로 변환
    if isinstance(ticker_list, dict):
        ticker_list = [ticker_list]

    saved_count = 0
    now = timezone.now()

    for ticker in ticker_list:
        symbol = ticker.get('symbol', '')

        # 수집 대상 코인만 처리
        if symbol not in TARGET_SYMBOLS:
            continue

        try:
            # 코인 객체 조회 (없으면 스킵 - seed_coins로 미리 등록 필요)
            try:
                coin = Coin.objects.get(symbol=symbol, is_active=True)
            except Coin.DoesNotExist:
                logger.warning(f'등록되지 않은 코인: {symbol} (seed_coins 명령 실행 필요)')
                continue

            # Binance 응답 데이터 파싱
            price = safe_decimal(ticker.get('lastPrice', 0))
            volume_24h = safe_decimal(ticker.get('quoteVolume', 0))  # USDT 기준 거래량
            change_24h = safe_decimal(ticker.get('priceChangePercent', 0))
            high_24h = safe_decimal(ticker.get('highPrice', 0))
            low_24h = safe_decimal(ticker.get('lowPrice', 0))

            # 유효성 검사
            if price <= 0:
                logger.warning(f'{symbol}: 유효하지 않은 가격 ({price})')
                continue

            # 가격 데이터 저장
            CoinPrice.objects.create(
                coin=coin,
                price=price,
                volume_24h=volume_24h,
                change_24h=change_24h,
                high_24h=high_24h,
                low_24h=low_24h,
                timestamp=now,
            )
            saved_count += 1
            logger.debug(f'{symbol}: ${price} ({change_24h:+.2f}%) 저장 완료')

        except Exception as e:
            logger.error(f'{symbol} 가격 저장 실패: {e}', exc_info=True)
            continue

    logger.info(f'코인 가격 수집 완료: {saved_count}/{len(TARGET_SYMBOLS)}개 저장')

    # 오래된 데이터 정리 (24시간 이상 된 데이터 삭제 - 옵션)
    _cleanup_old_prices()

    return {'saved': saved_count, 'total': len(TARGET_SYMBOLS)}


def _cleanup_old_prices():
    """
    오래된 가격 데이터 정리 (48시간 초과 데이터 삭제)
    Grafana 대시보드는 최근 1시간 데이터를 주로 조회하므로
    DB 용량 관리를 위해 48시간 이상 된 데이터 제거
    """
    from .models import CoinPrice
    cutoff = timezone.now() - timezone.timedelta(hours=48)
    deleted_count, _ = CoinPrice.objects.filter(timestamp__lt=cutoff).delete()
    if deleted_count > 0:
        logger.info(f'오래된 가격 데이터 {deleted_count}건 삭제 완료')
