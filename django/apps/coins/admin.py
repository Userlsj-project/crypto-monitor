"""
코인 앱 관리자 페이지 설정
Django Admin에서 코인 및 가격 데이터 관리
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Coin, CoinPrice


@admin.register(Coin)
class CoinAdmin(admin.ModelAdmin):
    """코인 목록 관리자"""
    list_display = ['symbol', 'name', 'is_active', 'is_active_badge', 'created_at']
    list_filter = ['is_active']
    search_fields = ['symbol', 'name']
    list_editable = ['is_active']  # 목록에서 직접 편집 가능
    ordering = ['symbol']

    def is_active_badge(self, obj):
        """활성화 상태를 색상 배지로 표시"""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ 활성</span>'
            )
        return format_html(
            '<span style="color: red;">✗ 비활성</span>'
        )
    is_active_badge.short_description = '상태'


@admin.register(CoinPrice)
class CoinPriceAdmin(admin.ModelAdmin):
    """코인 가격 내역 관리자"""
    list_display = [
        'coin', 'price_display', 'change_24h_display',
        'volume_24h', 'timestamp'
    ]
    list_filter = ['coin', 'timestamp']
    search_fields = ['coin__symbol', 'coin__name']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']

    # 최근 1000건만 표시 (성능 최적화)
    list_per_page = 50
    show_full_result_count = False

    def price_display(self, obj):
        """가격을 달러 형식으로 표시"""
        return f'${obj.price:,.2f}'
    price_display.short_description = '현재가 (USDT)'
    price_display.admin_order_field = 'price'

    def change_24h_display(self, obj):
        """등락률을 색상으로 표시"""
        if obj.change_24h > 0:
            return format_html(
                '<span style="color: green;">▲ {:.2f}%</span>',
                obj.change_24h
            )
        elif obj.change_24h < 0:
            return format_html(
                '<span style="color: red;">▼ {:.2f}%</span>',
                abs(obj.change_24h)
            )
        return format_html('<span>— 0.00%</span>')
    change_24h_display.short_description = '24h 등락률'
    change_24h_display.admin_order_field = 'change_24h'
