"""
Binance 공개 API 연결 및 데이터 수집 테스트
Docker 환경 외부에서 직접 실행 가능 (인터넷 연결 필요)
실행: python tests/test_binance_api.py
"""
import sys
import json
import time
import unittest
import requests

BINANCE_API_URL = 'https://api.binance.com/api/v3/ticker/24hr'
TARGET_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'SOLUSDT']


class TestBinanceAPI(unittest.TestCase):
    """Binance 공개 API 테스트"""

    def test_01_api_연결(self):
        """API 서버에 연결 가능한지 확인"""
        print('\n[1] Binance API 연결 테스트...')
        try:
            resp = requests.get(
                'https://api.binance.com/api/v3/ping',
                timeout=10,
            )
            self.assertEqual(resp.status_code, 200)
            print('  ✓ Binance API 연결 성공')
        except Exception as e:
            self.fail(f'Binance API 연결 실패: {e}')

    def test_02_단일_코인_조회(self):
        """단일 코인(BTCUSDT) 데이터 조회"""
        print('\n[2] 단일 코인 조회 테스트...')
        resp = requests.get(
            BINANCE_API_URL,
            params={'symbol': 'BTCUSDT'},
            timeout=10,
        )
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertIn('symbol', data)
        self.assertEqual(data['symbol'], 'BTCUSDT')
        self.assertIn('lastPrice', data)
        self.assertIn('priceChangePercent', data)
        self.assertIn('quoteVolume', data)

        price = float(data['lastPrice'])
        self.assertGreater(price, 0)
        print(f'  ✓ BTC 현재가: ${price:,.2f} USDT')

    def test_03_다중_코인_조회(self):
        """여러 코인 동시 조회 (symbols 파라미터)"""
        print('\n[3] 다중 코인 조회 테스트...')
        symbols_json = '["BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","SOLUSDT"]'
        resp = requests.get(
            BINANCE_API_URL,
            params={'symbols': symbols_json},
            timeout=15,
        )
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 5)

        returned_symbols = {item['symbol'] for item in data}
        for sym in TARGET_SYMBOLS:
            self.assertIn(sym, returned_symbols)
            print(f'  ✓ {sym}: ${float(next(d["lastPrice"] for d in data if d["symbol"] == sym)):,.4f}')

    def test_04_응답_데이터_구조(self):
        """응답 데이터에 필요한 필드가 모두 있는지 확인"""
        print('\n[4] 데이터 구조 유효성 테스트...')
        resp = requests.get(BINANCE_API_URL, params={'symbol': 'ETHUSDT'}, timeout=10)
        data = resp.json()

        required_fields = [
            'symbol', 'lastPrice', 'priceChangePercent',
            'quoteVolume', 'highPrice', 'lowPrice',
        ]
        for field in required_fields:
            self.assertIn(field, data, f'필드 누락: {field}')
            print(f'  ✓ {field}: {data[field]}')

    def test_05_가격_유효성(self):
        """모든 코인의 가격이 0보다 큰지 확인"""
        print('\n[5] 가격 유효성 테스트...')
        symbols_json = str(TARGET_SYMBOLS).replace("'", '"').replace(' ', '')
        resp = requests.get(BINANCE_API_URL, params={'symbols': symbols_json}, timeout=15)
        data = resp.json()

        for item in data:
            price = float(item['lastPrice'])
            self.assertGreater(price, 0, f'{item["symbol"]}: 가격이 0이하')
            print(f'  ✓ {item["symbol"]}: ${price:,.4f} (유효)')

    def test_06_응답_속도(self):
        """API 응답 속도가 3초 이내인지 확인"""
        print('\n[6] API 응답 속도 테스트...')
        start = time.time()
        resp = requests.get(BINANCE_API_URL, params={'symbol': 'BTCUSDT'}, timeout=10)
        elapsed = time.time() - start

        self.assertLess(elapsed, 3.0, f'응답 시간 초과: {elapsed:.2f}초')
        print(f'  ✓ 응답 시간: {elapsed:.3f}초')

    def test_07_API_키_불필요_확인(self):
        """API 키 없이 요청해도 성공하는지 확인 (헤더 없이 요청)"""
        print('\n[7] 익명 요청 (API 키 없음) 테스트...')
        resp = requests.get(
            BINANCE_API_URL,
            params={'symbol': 'BTCUSDT'},
            timeout=10,
            headers={'User-Agent': 'CryptoMonitor-Test/1.0'},
            # Authorization 헤더 없음
        )
        self.assertEqual(resp.status_code, 200)
        print('  ✓ API 키 없이 성공적으로 요청됨')


if __name__ == '__main__':
    print('=' * 60)
    print('Binance 공개 API 테스트')
    print('=' * 60)
    unittest.main(verbosity=0, exit=True)
