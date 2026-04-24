"""
알림 앱 관리자 페이지 설정
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Alert, AlertLog


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """가격 알림 관리자"""
    list_display = [
        'coin', 'condition_badge', 'target_price_display',
        'is_active', 'is_active_badge', 'triggered_at', 'created_at',
    ]
    list_filter = ['coin', 'condition', 'is_active']
    search_fields = ['coin__symbol', 'coin__name']
    list_editable = ['is_active']
    ordering = ['-created_at']
    readonly_fields = ['triggered_at', 'created_at', 'updated_at']

    def condition_badge(self, obj):
        if obj.condition == 'above':
            return format_html(
                '<span style="color: green; font-weight: bold;">▲ 이상</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">▼ 이하</span>'
        )
    condition_badge.short_description = '조건'

    def target_price_display(self, obj):
        return f'${obj.target_price:,.2f}'
    target_price_display.short_description = '목표가'
    target_price_display.admin_order_field = 'target_price'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">● 활성</span>')
        return format_html('<span style="color: gray;">○ 비활성</span>')
    is_active_badge.short_description = '상태'


@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    """알림 발동 기록 관리자"""
    list_display = [
        'alert', 'triggered_price_display', 'message_preview',
        'has_ai_analysis', 'created_at',
    ]
    list_filter = ['alert__coin', 'created_at']
    search_fields = ['alert__coin__symbol', 'message', 'ai_analysis']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    list_per_page = 50

    def triggered_price_display(self, obj):
        if obj.triggered_price:
            return f'${obj.triggered_price:,.2f}'
        return '-'
    triggered_price_display.short_description = '트리거 가격'

    def message_preview(self, obj):
        """메시지 앞 50자만 표시"""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = '메시지 (미리보기)'

    def has_ai_analysis(self, obj):
        if obj.ai_analysis:
            return format_html('<span style="color: green;">✓ 있음</span>')
        return format_html('<span style="color: gray;">✗ 없음</span>')
    has_ai_analysis.short_description = 'AI 분석'
