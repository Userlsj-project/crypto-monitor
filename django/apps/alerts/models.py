"""
알림 앱 모델
- Alert: 가격 알림 조건 설정
- AlertLog: 알림 발동 기록 (AI 분석 포함)
"""
from django.db import models
from apps.coins.models import Coin


class Alert(models.Model):
    """
    가격 알림 조건 설정
    특정 코인이 목표가 이상/이하가 되면 알림 발동
    """

    CONDITION_ABOVE = 'above'
    CONDITION_BELOW = 'below'
    CONDITION_CHOICES = [
        (CONDITION_ABOVE, '이상 (목표가 이상)'),
        (CONDITION_BELOW, '이하 (목표가 이하)'),
    ]

    coin = models.ForeignKey(
        Coin,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name='코인',
    )
    condition = models.CharField(
        max_length=10,
        choices=CONDITION_CHOICES,
        verbose_name='조건',
        help_text='above: 목표가 초과 시 알림 / below: 목표가 미만 시 알림',
    )
    target_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        verbose_name='목표가 (USDT)',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화',
        help_text='비활성화 시 조건 체크 제외',
    )
    triggered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='마지막 트리거 시각',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일',
    )

    class Meta:
        db_table = 'alerts_alert'
        verbose_name = '가격 알림'
        verbose_name_plural = '가격 알림 목록'
        ordering = ['-created_at']

    def __str__(self):
        condition_label = '이상' if self.condition == self.CONDITION_ABOVE else '이하'
        return (
            f'{self.coin.symbol} {condition_label} '
            f'${self.target_price} 알림 '
            f'({"활성" if self.is_active else "비활성"})'
        )

    def check_condition(self, current_price: float) -> bool:
        """
        현재 가격이 알림 조건을 충족하는지 확인
        :param current_price: 현재 코인 가격
        :return: 조건 충족 여부
        """
        target = float(self.target_price)
        if self.condition == self.CONDITION_ABOVE:
            return current_price >= target
        elif self.condition == self.CONDITION_BELOW:
            return current_price <= target
        return False


class AlertLog(models.Model):
    """
    알림 발동 기록
    조건 충족 시 EXAONE AI 분석 결과와 함께 저장
    """
    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='알림',
    )
    message = models.TextField(
        verbose_name='알림 메시지',
        help_text='알림 발동 시 자동 생성된 메시지',
    )
    ai_analysis = models.TextField(
        blank=True,
        default='',
        verbose_name='AI 분석 결과',
        help_text='EXAONE 3.5가 생성한 시장 분석 텍스트',
    )
    triggered_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name='트리거 발동 가격',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='발생 시각',
        db_index=True,
    )

    class Meta:
        db_table = 'alerts_alertlog'
        verbose_name = '알림 발동 기록'
        verbose_name_plural = '알림 발동 기록 목록'
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'[{self.created_at:%Y-%m-%d %H:%M}] '
            f'{self.alert.coin.symbol} 알림 발동'
        )
