"""
코인 앱 직렬화기
DRF Serializer를 사용한 JSON 변환
"""
from rest_framework import serializers
from .models import Coin, CoinPrice


class CoinSerializer(serializers.ModelSerializer):
    """코인 정보 직렬화기"""
    base_symbol = serializers.ReadOnlyField()

    class Meta:
        model = Coin
        fields = [
            'id', 'symbol', 'name', 'base_symbol',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CoinPriceSerializer(serializers.ModelSerializer):
    """코인 가격 데이터 직렬화기"""
    coin_symbol = serializers.CharField(source='coin.symbol', read_only=True)
    coin_name = serializers.CharField(source='coin.name', read_only=True)
    change_direction = serializers.ReadOnlyField()

    class Meta:
        model = CoinPrice
        fields = [
            'id', 'coin', 'coin_symbol', 'coin_name',
            'price', 'volume_24h', 'change_24h',
            'high_24h', 'low_24h',
            'change_direction', 'timestamp',
        ]
        read_only_fields = ['id', 'timestamp']


class CoinPriceSimpleSerializer(serializers.ModelSerializer):
    """경량화된 가격 직렬화기 (목록 조회용)"""

    class Meta:
        model = CoinPrice
        fields = ['price', 'volume_24h', 'change_24h', 'timestamp']


class LatestCoinPriceSerializer(serializers.ModelSerializer):
    """최신 가격 포함 코인 직렬화기 (메인 대시보드용)"""
    latest_price = serializers.SerializerMethodField()
    base_symbol = serializers.ReadOnlyField()

    class Meta:
        model = Coin
        fields = ['id', 'symbol', 'base_symbol', 'name', 'is_active', 'latest_price']

    def get_latest_price(self, obj):
        """해당 코인의 가장 최근 가격 데이터 반환"""
        latest = obj.prices.first()  # ordering = ['-timestamp']
        if latest:
            return CoinPriceSimpleSerializer(latest).data
        return None
