"""
알림 앱 직렬화기
DRF Serializer를 사용한 JSON 변환
"""
from rest_framework import serializers
from apps.coins.models import Coin
from .models import Alert, AlertLog


class AlertSerializer(serializers.ModelSerializer):
    """가격 알림 직렬화기"""
    coin_symbol = serializers.CharField(source='coin.symbol', read_only=True)
    coin_name = serializers.CharField(source='coin.name', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)

    class Meta:
        model = Alert
        fields = [
            'id', 'coin', 'coin_symbol', 'coin_name',
            'condition', 'condition_display',
            'target_price', 'is_active',
            'triggered_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'triggered_at', 'created_at', 'updated_at']

    def validate_target_price(self, value):
        """목표가 유효성 검사: 0보다 커야 함"""
        if value <= 0:
            raise serializers.ValidationError('목표가는 0보다 커야 합니다.')
        return value

    def validate_coin(self, value):
        """활성화된 코인만 알림 설정 가능"""
        if not value.is_active:
            raise serializers.ValidationError(
                f'{value.symbol}은 현재 비활성화된 코인입니다.'
            )
        return value


class AlertCreateSerializer(serializers.ModelSerializer):
    """알림 생성 직렬화기 (coin_symbol로 코인 지정 가능)"""
    coin_symbol = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Alert
        fields = [
            'id', 'coin', 'coin_symbol', 'condition',
            'target_price', 'is_active',
        ]
        read_only_fields = ['id']

    def validate(self, data):
        # coin_symbol로 Coin 객체 조회
        coin_symbol = data.pop('coin_symbol', None)
        if coin_symbol and 'coin' not in data:
            try:
                data['coin'] = Coin.objects.get(
                    symbol=coin_symbol.upper(),
                    is_active=True,
                )
            except Coin.DoesNotExist:
                raise serializers.ValidationError(
                    {'coin_symbol': f'{coin_symbol} 코인을 찾을 수 없습니다.'}
                )
        return data


class AlertLogSerializer(serializers.ModelSerializer):
    """알림 발동 기록 직렬화기"""
    alert_coin_symbol = serializers.CharField(source='alert.coin.symbol', read_only=True)
    alert_condition = serializers.CharField(source='alert.get_condition_display', read_only=True)
    alert_target_price = serializers.DecimalField(
        source='alert.target_price',
        max_digits=20,
        decimal_places=8,
        read_only=True,
    )

    class Meta:
        model = AlertLog
        fields = [
            'id', 'alert', 'alert_coin_symbol',
            'alert_condition', 'alert_target_price',
            'message', 'ai_analysis',
            'triggered_price', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
