"""
Celery 태스크 테스트
Django 환경에서 실행: docker exec crypto_django python manage.py test apps.coins apps.alerts
또는: docker exec crypto_django python tests/test_celery_tasks.py
"""
import os
import sys
import django
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Django 환경 설정
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import unittest
from django.test import TestCase
from apps.coins.models import Coin, CoinPrice
from apps.alerts.models import Alert, AlertLog


class TestFetchCoinPricesTask(TestCase):
    """Binance 가격 수집 태스크 테스트"""

    def setUp(self):
        """테스트용 코인 데이터 생성"""
        self.btc = Coin.objects.create(symbol='BTCUSDT', name='Bitcoin', is_active=True)
        self.eth = Coin.objects.create(symbol='ETHUSDT', name='Ethereum', is_active=True)

    def tearDown(self):
        Coin.objects.all().delete()

    @patch('apps.coins.tasks.requests.get')
    def test_01_가격_수집_성공(self, mock_get):
        """정상 API 응답 시 가격 저장 확인"""
        print('\n[1] 가격 수집 태스크 - 정상 케이스...')

        # Binance API 응답 Mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'symbol': 'BTCUSDT',
                'lastPrice': '95000.12',
                'priceChangePercent': '2.35',
                'quoteVolume': '1500000000',
                'highPrice': '96000.00',
                'lowPrice': '93000.00',
            },
            {
                'symbol': 'ETHUSDT',
                'lastPrice': '3200.50',
                'priceChangePercent': '-1.20',
                'quoteVolume': '800000000',
                'highPrice': '3300.00',
                'lowPrice': '3150.00',
            },
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from apps.coins.tasks import fetch_coin_prices
        result = fetch_coin_prices()

        # 저장된 가격 확인
        btc_prices = CoinPrice.objects.filter(coin=self.btc)
        eth_prices = CoinPrice.objects.filter(coin=self.eth)

        self.assertEqual(btc_prices.count(), 1)
        self.assertEqual(eth_prices.count(), 1)
        self.assertEqual(float(btc_prices.first().price), 95000.12)
        self.assertEqual(float(eth_prices.first().change_24h), -1.20)

        print(f'  ✓ BTC 가격 저장: ${btc_prices.first().price}')
        print(f'  ✓ ETH 가격 저장: ${eth_prices.first().price}')

    @patch('apps.coins.tasks.requests.get')
    def test_02_API_연결_실패_재시도(self, mock_get):
        """API 연결 실패 시 재시도 로직 확인"""
        print('\n[2] API 연결 실패 재시도 테스트...')
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError('연결 실패')

        from apps.coins.tasks import fetch_coin_prices
        # Celery retry는 실제 테스트에서 예외 발생
        # 여기서는 기본 동작만 확인
        try:
            fetch_coin_prices()
        except Exception:
            pass  # 재시도 예외는 정상

        # 가격이 저장되지 않아야 함
        self.assertEqual(CoinPrice.objects.count(), 0)
        print('  ✓ API 실패 시 가격 미저장 확인')

    @patch('apps.coins.tasks.requests.get')
    def test_03_비활성_코인_스킵(self, mock_get):
        """비활성화된 코인은 수집 스킵"""
        print('\n[3] 비활성 코인 스킵 테스트...')

        # BTC를 비활성화
        self.btc.is_active = False
        self.btc.save()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'symbol': 'BTCUSDT',
                'lastPrice': '95000.00',
                'priceChangePercent': '1.0',
                'quoteVolume': '1000000',
                'highPrice': '96000.00',
                'lowPrice': '94000.00',
            }
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from apps.coins.tasks import fetch_coin_prices
        fetch_coin_prices()

        # 비활성 코인 가격은 저장되면 안 됨
        btc_prices = CoinPrice.objects.filter(coin=self.btc)
        self.assertEqual(btc_prices.count(), 0)
        print('  ✓ 비활성 코인(BTC) 가격 미저장 확인')


class TestCheckAlertsTask(TestCase):
    """알림 조건 체크 태스크 테스트"""

    def setUp(self):
        self.btc = Coin.objects.create(symbol='BTCUSDT', name='Bitcoin', is_active=True)
        # 현재가 시뮬레이션용 가격 데이터
        self.btc_price = CoinPrice.objects.create(
            coin=self.btc,
            price=Decimal('95000.00'),
            volume_24h=Decimal('1500000000'),
            change_24h=Decimal('2.50'),
        )

    def tearDown(self):
        AlertLog.objects.all().delete()
        Alert.objects.all().delete()
        CoinPrice.objects.all().delete()
        Coin.objects.all().delete()

    @patch('apps.alerts.tasks._get_ai_analysis')
    @patch('apps.alerts.tasks._send_n8n_webhook')
    def test_01_조건_충족_알림_발동(self, mock_webhook, mock_ai):
        """현재가가 목표가 이상일 때 알림 발동"""
        print('\n[1] 알림 조건 충족 테스트 (above)...')
        mock_ai.return_value = 'BTC가 목표가에 도달했습니다.'

        # 목표가 90000 이상 → 현재가 95000 → 조건 충족
        alert = Alert.objects.create(
            coin=self.btc,
            condition='above',
            target_price=Decimal('90000.00'),
            is_active=True,
        )

        from apps.alerts.tasks import check_alerts
        result = check_alerts()

        # AlertLog 생성 확인
        self.assertEqual(AlertLog.objects.count(), 1)
        log = AlertLog.objects.first()
        self.assertIn('BTC', log.message)
        self.assertEqual(log.ai_analysis, 'BTC가 목표가에 도달했습니다.')
        self.assertEqual(float(log.triggered_price), 95000.00)

        print(f'  ✓ 알림 발동: {log.message[:50]}...')
        print(f'  ✓ AI 분석: {log.ai_analysis}')

    @patch('apps.alerts.tasks._get_ai_analysis')
    @patch('apps.alerts.tasks._send_n8n_webhook')
    def test_02_조건_미충족_알림_미발동(self, mock_webhook, mock_ai):
        """현재가가 목표가 미만일 때 알림 미발동"""
        print('\n[2] 알림 조건 미충족 테스트 (above)...')

        # 목표가 100000 이상 → 현재가 95000 → 조건 미충족
        Alert.objects.create(
            coin=self.btc,
            condition='above',
            target_price=Decimal('100000.00'),
            is_active=True,
        )

        from apps.alerts.tasks import check_alerts
        check_alerts()

        self.assertEqual(AlertLog.objects.count(), 0)
        print('  ✓ 조건 미충족 시 알림 미발동 확인')

    @patch('apps.alerts.tasks._get_ai_analysis')
    @patch('apps.alerts.tasks._send_n8n_webhook')
    def test_03_below_조건_테스트(self, mock_webhook, mock_ai):
        """현재가가 목표가 이하일 때 below 조건 발동"""
        print('\n[3] 알림 조건 충족 테스트 (below)...')
        mock_ai.return_value = 'BTC가 목표가 이하로 하락했습니다.'

        # 목표가 96000 이하 → 현재가 95000 → 조건 충족
        Alert.objects.create(
            coin=self.btc,
            condition='below',
            target_price=Decimal('96000.00'),
            is_active=True,
        )

        from apps.alerts.tasks import check_alerts
        check_alerts()

        self.assertEqual(AlertLog.objects.count(), 1)
        print('  ✓ below 조건 알림 발동 확인')

    def test_04_비활성_알림_체크_제외(self):
        """비활성화된 알림은 체크에서 제외"""
        print('\n[4] 비활성 알림 제외 테스트...')

        Alert.objects.create(
            coin=self.btc,
            condition='above',
            target_price=Decimal('90000.00'),
            is_active=False,  # 비활성화
        )

        from apps.alerts.tasks import check_alerts
        result = check_alerts()

        self.assertEqual(result['triggered'], 0)
        self.assertEqual(AlertLog.objects.count(), 0)
        print('  ✓ 비활성 알림 체크 제외 확인')


class TestAlertModel(TestCase):
    """Alert 모델 단위 테스트"""

    def setUp(self):
        self.btc = Coin.objects.create(symbol='BTCUSDT', name='Bitcoin')

    def tearDown(self):
        Coin.objects.all().delete()

    def test_above_조건_체크(self):
        """above 조건: 현재가 >= 목표가"""
        alert = Alert(coin=self.btc, condition='above', target_price=Decimal('90000'))
        self.assertTrue(alert.check_condition(95000))    # 충족
        self.assertTrue(alert.check_condition(90000))    # 경계값
        self.assertFalse(alert.check_condition(89999))   # 미충족
        print('  ✓ above 조건 체크 정상 동작')

    def test_below_조건_체크(self):
        """below 조건: 현재가 <= 목표가"""
        alert = Alert(coin=self.btc, condition='below', target_price=Decimal('90000'))
        self.assertTrue(alert.check_condition(85000))    # 충족
        self.assertTrue(alert.check_condition(90000))    # 경계값
        self.assertFalse(alert.check_condition(90001))   # 미충족
        print('  ✓ below 조건 체크 정상 동작')


if __name__ == '__main__':
    print('=' * 60)
    print('Celery 태스크 테스트 (Django TestCase)')
    print('실행 방법: docker exec crypto_django python manage.py test')
    print('=' * 60)
    unittest.main(verbosity=2)
