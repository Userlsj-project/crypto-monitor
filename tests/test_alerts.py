"""
알림 시스템 통합 테스트
실행: docker exec crypto_django python manage.py test apps.alerts
"""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import unittest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
import json

from apps.coins.models import Coin, CoinPrice
from apps.alerts.models import Alert, AlertLog


class TestAlertAPI(TestCase):
    """알림 REST API 테스트"""

    def setUp(self):
        self.client = Client()
        self.btc = Coin.objects.create(symbol='BTCUSDT', name='Bitcoin', is_active=True)
        self.eth = Coin.objects.create(symbol='ETHUSDT', name='Ethereum', is_active=True)

    def tearDown(self):
        AlertLog.objects.all().delete()
        Alert.objects.all().delete()
        Coin.objects.all().delete()

    def test_01_알림_생성_API(self):
        """POST /api/alerts/ - 알림 생성"""
        print('\n[1] 알림 생성 API 테스트...')
        data = {
            'coin': self.btc.id,
            'condition': 'above',
            'target_price': '90000.00',
        }
        resp = self.client.post(
            '/api/alerts/',
            data=json.dumps(data),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 201)
        result = resp.json()
        self.assertEqual(result['coin'], self.btc.id)
        self.assertEqual(result['condition'], 'above')
        self.assertTrue(result['is_active'])
        print(f'  ✓ 알림 생성 성공: ID={result["id"]}')

    def test_02_알림_목록_조회(self):
        """GET /api/alerts/ - 알림 목록"""
        print('\n[2] 알림 목록 조회 테스트...')
        Alert.objects.create(coin=self.btc, condition='above', target_price=Decimal('90000'))
        Alert.objects.create(coin=self.eth, condition='below', target_price=Decimal('3000'))

        resp = self.client.get('/api/alerts/')
        self.assertEqual(resp.status_code, 200)
        results = resp.json()
        self.assertEqual(len(results), 2)
        print(f'  ✓ 알림 {len(results)}개 조회 성공')

    def test_03_알림_토글(self):
        """PATCH /api/alerts/<id>/toggle/ - 활성화 토글"""
        print('\n[3] 알림 토글 테스트...')
        alert = Alert.objects.create(
            coin=self.btc, condition='above',
            target_price=Decimal('90000'), is_active=True,
        )

        resp = self.client.patch(f'/api/alerts/{alert.id}/toggle/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data['is_active'])  # True → False
        print(f'  ✓ 토글: True → {data["is_active"]}')

        # 다시 토글
        resp2 = self.client.patch(f'/api/alerts/{alert.id}/toggle/')
        data2 = resp2.json()
        self.assertTrue(data2['is_active'])  # False → True
        print(f'  ✓ 재토글: False → {data2["is_active"]}')

    def test_04_알림_삭제(self):
        """DELETE /api/alerts/<id>/ - 알림 삭제"""
        print('\n[4] 알림 삭제 테스트...')
        alert = Alert.objects.create(
            coin=self.btc, condition='above', target_price=Decimal('90000'),
        )
        alert_id = alert.id

        resp = self.client.delete(f'/api/alerts/{alert_id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Alert.objects.filter(id=alert_id).exists())
        print(f'  ✓ 알림 ID={alert_id} 삭제 완료')

    def test_05_알림_로그_조회(self):
        """GET /api/alerts/logs/ - 알림 로그"""
        print('\n[5] 알림 로그 조회 테스트...')
        alert = Alert.objects.create(
            coin=self.btc, condition='above', target_price=Decimal('90000'),
        )
        AlertLog.objects.create(
            alert=alert,
            message='BTC 알림 발동',
            ai_analysis='BTC가 목표가를 돌파했습니다.',
            triggered_price=Decimal('95000'),
        )

        resp = self.client.get('/api/alerts/logs/')
        self.assertEqual(resp.status_code, 200)
        logs = resp.json()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['ai_analysis'], 'BTC가 목표가를 돌파했습니다.')
        print(f'  ✓ 알림 로그 {len(logs)}건 조회 성공')

    def test_06_잘못된_목표가_검증(self):
        """0 이하의 목표가는 거부"""
        print('\n[6] 유효성 검사 - 잘못된 목표가...')
        data = {
            'coin': self.btc.id,
            'condition': 'above',
            'target_price': '-100',
        }
        resp = self.client.post(
            '/api/alerts/',
            data=json.dumps(data),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        print('  ✓ 음수 목표가 거부 확인')


class TestAlertConditionLogic(TestCase):
    """알림 조건 로직 단위 테스트"""

    def setUp(self):
        self.btc = Coin.objects.create(symbol='BTCUSDT', name='Bitcoin')

    def tearDown(self):
        Coin.objects.all().delete()

    def test_above_조건_경계값(self):
        """above 조건 경계값 테스트"""
        alert = Alert(coin=self.btc, condition='above', target_price=Decimal('100000'))
        # 경계값 (= 목표가): 충족
        self.assertTrue(alert.check_condition(100000.0))
        # 경계값 초과: 충족
        self.assertTrue(alert.check_condition(100001.0))
        # 경계값 미만: 미충족
        self.assertFalse(alert.check_condition(99999.99))
        print('  ✓ above 경계값 테스트 통과')

    def test_below_조건_경계값(self):
        """below 조건 경계값 테스트"""
        alert = Alert(coin=self.btc, condition='below', target_price=Decimal('80000'))
        # 경계값: 충족
        self.assertTrue(alert.check_condition(80000.0))
        # 경계값 미만: 충족
        self.assertTrue(alert.check_condition(79999.0))
        # 경계값 초과: 미충족
        self.assertFalse(alert.check_condition(80001.0))
        print('  ✓ below 경계값 테스트 통과')

    def test_소수점_가격_조건(self):
        """소수점이 포함된 목표가 처리"""
        alert = Alert(coin=self.btc, condition='above', target_price=Decimal('0.55123'))
        self.assertTrue(alert.check_condition(0.56))
        self.assertFalse(alert.check_condition(0.54))
        print('  ✓ 소수점 가격 처리 정상')

    def test_알림_str_표현(self):
        """Alert __str__ 메서드"""
        alert = Alert(
            coin=self.btc, condition='above',
            target_price=Decimal('90000'), is_active=True,
        )
        str_repr = str(alert)
        self.assertIn('BTCUSDT', str_repr)
        self.assertIn('이상', str_repr)
        print(f'  ✓ str(): {str_repr}')


class TestAlertN8nWebhook(TestCase):
    """n8n 웹훅 전송 테스트"""

    def setUp(self):
        self.btc = Coin.objects.create(symbol='BTCUSDT', name='Bitcoin')
        self.alert = Alert.objects.create(
            coin=self.btc, condition='above', target_price=Decimal('90000'),
        )
        self.log = AlertLog.objects.create(
            alert=self.alert, message='테스트', triggered_price=Decimal('95000'),
        )

    def tearDown(self):
        AlertLog.objects.all().delete()
        Alert.objects.all().delete()
        Coin.objects.all().delete()

    @patch('apps.alerts.tasks.requests.post')
    def test_웹훅_전송_성공(self, mock_post):
        """n8n 웹훅 전송 테스트"""
        print('\n[웹훅] n8n 웹훅 전송 테스트...')
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        from apps.alerts.tasks import _send_n8n_webhook
        with self.settings(N8N_WEBHOOK_URL='http://n8n:5678/webhook/crypto-alert'):
            _send_n8n_webhook(self.alert, 95000.0, 'AI 분석', self.log)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]['json'] if 'json' in call_kwargs[1] else call_kwargs[0][1]
        self.assertEqual(payload['coin_symbol'], 'BTCUSDT')
        self.assertEqual(payload['current_price'], 95000.0)
        print('  ✓ 웹훅 전송 성공 확인')


if __name__ == '__main__':
    print('=' * 60)
    print('알림 시스템 통합 테스트')
    print('=' * 60)
    unittest.main(verbosity=2)
