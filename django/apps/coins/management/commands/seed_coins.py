"""
초기 코인 데이터 삽입 커맨드
BTC, ETH, BNB, XRP, SOL 코인 정보를 DB에 등록
사용법: python manage.py seed_coins
"""
from django.core.management.base import BaseCommand
from apps.coins.models import Coin


# 수집 대상 코인 초기 데이터
INITIAL_COINS = [
    {
        'symbol': 'BTCUSDT',
        'name': 'Bitcoin',
    },
    {
        'symbol': 'ETHUSDT',
        'name': 'Ethereum',
    },
    {
        'symbol': 'BNBUSDT',
        'name': 'BNB',
    },
    {
        'symbol': 'XRPUSDT',
        'name': 'XRP',
    },
    {
        'symbol': 'SOLUSDT',
        'name': 'Solana',
    },
]


class Command(BaseCommand):
    help = '초기 코인 데이터를 데이터베이스에 삽입합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='기존 코인 데이터를 초기화하고 재삽입',
        )

    def handle(self, *args, **options):
        if options.get('reset'):
            count = Coin.objects.all().delete()[0]
            self.stdout.write(
                self.style.WARNING(f'기존 코인 데이터 {count}건 삭제')
            )

        created_count = 0
        updated_count = 0

        for coin_data in INITIAL_COINS:
            coin, created = Coin.objects.update_or_create(
                symbol=coin_data['symbol'],
                defaults={
                    'name': coin_data['name'],
                    'is_active': True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ {coin.name} ({coin.symbol}) 생성')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.HTTP_INFO(f'  → {coin.name} ({coin.symbol}) 이미 존재')
                )

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'코인 데이터 초기화 완료: '
                f'{created_count}개 생성, {updated_count}개 기존 유지'
            )
        )
