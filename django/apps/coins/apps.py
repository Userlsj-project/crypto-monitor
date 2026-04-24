from django.apps import AppConfig


class CoinsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.coins'
    verbose_name = '코인 가격 모니터링'

    def ready(self):
        """앱 시작 시 시그널 등록 등 초기화 작업"""
        pass
