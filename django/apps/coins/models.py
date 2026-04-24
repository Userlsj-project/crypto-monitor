"""
코인 가격 모니터링 모델
- Coin: 추적 대상 코인 정보
- CoinPrice: 수집된 가격 데이터 (시계열)
"""
from django.db import models
from django.utils import timezone


class Coin(models.Model):
    """
    추적 대상 코인 정보
    심볼(BTCUSDT), 이름(Bitcoin), 활성화 여부를 관리
    """
    symbol = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='심볼',
        help_text='Binance 거래 페어 (예: BTCUSDT)',
    )
    name = models.CharField(
        max_length=100,
        verbose_name='코인명',
        help_text='코인 전체 이름 (예: Bitcoin)',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화',
        help_text='가격 수집 활성화 여부',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일',
    )

    class Meta:
        db_table = 'coins_coin'
        verbose_name = '코인'
        verbose_name_plural = '코인 목록'
        ordering = ['symbol']

    def __str__(self):
        return f'{self.name} ({self.symbol})'

    @property
    def base_symbol(self):
        """USDT를 제거한 기본 심볼 반환 (BTCUSDT → BTC)"""
        return self.symbol.replace('USDT', '')


class CoinPrice(models.Model):
    """
    코인 가격 데이터 (시계열)
    Binance API에서 30초마다 수집
    """
    coin = models.ForeignKey(
        Coin,
        on_delete=models.CASCADE,
        related_name='prices',
        verbose_name='코인',
    )
    price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        verbose_name='현재가 (USDT)',
    )
    volume_24h = models.DecimalField(
        max_digits=30,
        decimal_places=2,
        verbose_name='24시간 거래량',
        default=0,
    )
    change_24h = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name='24시간 등락률 (%)',
        default=0,
    )
    high_24h = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        verbose_name='24시간 최고가',
        default=0,
    )
    low_24h = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        verbose_name='24시간 최저가',
        default=0,
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name='수집 시각',
        db_index=True,  # 시계열 쿼리 최적화
    )

    class Meta:
        db_table = 'coins_coinprice'
        verbose_name = '코인 가격'
        verbose_name_plural = '코인 가격 내역'
        ordering = ['-timestamp']
        # 최근 데이터 조회 성능 향상
        indexes = [
            models.Index(fields=['coin', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f'{self.coin.symbol}: ${self.price} ({self.timestamp:%Y-%m-%d %H:%M:%S})'

    @property
    def change_direction(self):
        """등락 방향 반환 (up/down/neutral)"""
        if self.change_24h > 0:
            return 'up'
        elif self.change_24h < 0:
            return 'down'
        return 'neutral'
