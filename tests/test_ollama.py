"""
EXAONE 3.5 (Ollama) 연결 및 AI 분석 테스트
실행: docker exec crypto_django python tests/test_ollama.py
또는: python tests/test_ollama.py (OLLAMA_BASE_URL 환경변수 필요)
"""
import os
import sys
import time
import requests
import unittest

# Ollama 서버 URL (환경변수로 재정의 가능)
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'exaone3.5:2.4b')


class TestOllamaConnection(unittest.TestCase):
    """Ollama 서버 연결 테스트"""

    def test_01_서버_연결(self):
        """Ollama 서버 ping 테스트"""
        print(f'\n[1] Ollama 서버 연결 테스트 ({OLLAMA_BASE_URL})...')
        try:
            resp = requests.get(f'{OLLAMA_BASE_URL}/api/tags', timeout=10)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            models = [m['name'] for m in data.get('models', [])]
            print(f'  ✓ Ollama 서버 연결 성공')
            print(f'  설치된 모델: {", ".join(models) if models else "없음"}')
        except requests.exceptions.ConnectionError:
            self.skipTest(
                f'Ollama 서버({OLLAMA_BASE_URL})에 연결할 수 없습니다. '
                'Docker 컨테이너가 실행 중인지 확인하세요.'
            )

    def test_02_모델_설치_확인(self):
        """EXAONE 모델 설치 여부 확인"""
        print(f'\n[2] {OLLAMA_MODEL} 모델 설치 확인...')
        try:
            resp = requests.get(f'{OLLAMA_BASE_URL}/api/tags', timeout=10)
            if resp.status_code != 200:
                self.skipTest('Ollama 서버 응답 없음')

            data = resp.json()
            models = [m['name'] for m in data.get('models', [])]

            if OLLAMA_MODEL not in models:
                print(f'  ⚠ {OLLAMA_MODEL} 미설치. 설치 명령:')
                print(f'    docker exec crypto_ollama ollama pull {OLLAMA_MODEL}')
                self.skipTest(f'{OLLAMA_MODEL} 모델이 설치되지 않았습니다.')
            else:
                print(f'  ✓ {OLLAMA_MODEL} 설치됨')
        except requests.exceptions.ConnectionError:
            self.skipTest('Ollama 서버 연결 불가')


class TestOllamaAnalysis(unittest.TestCase):
    """EXAONE AI 분석 기능 테스트"""

    @classmethod
    def setUpClass(cls):
        """Ollama 서버 연결 확인 후 모든 테스트 실행"""
        try:
            resp = requests.get(f'{OLLAMA_BASE_URL}/api/tags', timeout=5)
            if resp.status_code != 200:
                raise Exception('서버 오류')
            models = [m['name'] for m in resp.json().get('models', [])]
            if OLLAMA_MODEL not in models:
                cls._skip = True
                print(f'\n⚠ {OLLAMA_MODEL} 미설치 - AI 분석 테스트 스킵')
            else:
                cls._skip = False
        except Exception:
            cls._skip = True
            print('\n⚠ Ollama 서버 연결 불가 - AI 분석 테스트 스킵')

    def setUp(self):
        if self.__class__._skip:
            self.skipTest('Ollama 또는 EXAONE 모델 사용 불가')

    def _generate(self, prompt, system=''):
        """Ollama API 직접 호출"""
        payload = {
            'model': OLLAMA_MODEL,
            'prompt': prompt,
            'system': system,
            'stream': False,
            'options': {
                'temperature': 0.7,
                'num_predict': 200,
            },
        }
        resp = requests.post(
            f'{OLLAMA_BASE_URL}/api/generate',
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get('response', '').strip()

    def test_03_기본_생성(self):
        """기본 텍스트 생성 테스트"""
        print(f'\n[3] 기본 텍스트 생성 테스트...')
        start = time.time()
        result = self._generate('안녕하세요. 한 문장으로 자기소개해주세요.')
        elapsed = time.time() - start

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        print(f'  ✓ 응답 생성 성공 ({elapsed:.1f}초): {result[:80]}...')

    def test_04_가격_분석(self):
        """가격 변동 분석 테스트"""
        print(f'\n[4] 가격 분석 테스트...')

        system = (
            '당신은 암호화폐 분석가입니다. '
            '한국어로 200자 이내로 답변하세요. '
            '투자 조언은 하지 마세요.'
        )
        prompt = (
            'BTC 현재가: $95,000 USDT\n'
            '24시간 변동률: +2.5%\n'
            '24시간 거래량: $1.5B USDT\n'
            '위 데이터를 바탕으로 현재 시장 상황을 200자 이내로 분석해주세요.'
        )

        result = self._generate(prompt, system)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 10)
        print(f'  ✓ 분석 결과 ({len(result)}자):\n  {result}')

    def test_05_시장_요약(self):
        """시장 요약 생성 테스트"""
        print(f'\n[5] 시장 요약 테스트...')

        system = (
            '당신은 암호화폐 시장 분석가입니다. '
            '한국어로 200자 이내로 답변하세요. '
            '투자 조언 금지.'
        )
        prompt = (
            '암호화폐 시장 현황:\n'
            '- BTC: $95,000 (+2.5%)\n'
            '- ETH: $3,200 (-1.2%)\n'
            '- BNB: $420 (+0.8%)\n'
            '- XRP: $0.55 (-2.1%)\n'
            '- SOL: $180 (+3.2%)\n'
            '상승 3종목, 하락 2종목. 200자 이내로 시장 동향을 요약해주세요.'
        )

        result = self._generate(prompt, system)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 10)
        print(f'  ✓ 시장 요약 ({len(result)}자):\n  {result}')

    def test_06_ai_analyzer_클래스(self):
        """OllamaClient 클래스 직접 테스트"""
        print(f'\n[6] OllamaClient 클래스 테스트...')

        # OLLAMA_BASE_URL을 localhost로 임시 설정
        sys.path.insert(0, '/app')

        try:
            os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
            import django
            django.setup()
            from apps.coins.ai_analyzer import OllamaClient

            client = OllamaClient()
            client.base_url = OLLAMA_BASE_URL

            # health check
            is_healthy = client.health_check()
            self.assertTrue(is_healthy)
            print(f'  ✓ health_check(): {is_healthy}')

            # 가격 분석
            result = client.analyze_price_movement(
                symbol='BTCUSDT',
                current_price=95000.0,
                change_24h=2.5,
                volume_24h=1500000000.0,
            )
            self.assertIsInstance(result, str)
            self.assertNotIn('[AI 분석 불가', result)
            print(f'  ✓ analyze_price_movement(): {len(result)}자 응답')

        except ImportError:
            self.skipTest('Django 환경 없음 - OllamaClient 직접 테스트 스킵')


if __name__ == '__main__':
    print('=' * 60)
    print(f'EXAONE 3.5 (Ollama) 연결 테스트')
    print(f'서버: {OLLAMA_BASE_URL}')
    print(f'모델: {OLLAMA_MODEL}')
    print('=' * 60)
    unittest.main(verbosity=0)
