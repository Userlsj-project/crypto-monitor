"""
EXAONE 3.5 2.4B (via Ollama) AI 분석 모듈
코인 가격 변동 분석, 알림 트리거 설명, 시장 요약 기능 제공
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Ollama API 클라이언트
    EXAONE 3.5 2.4B 모델을 사용하여 한국어 분석 텍스트 생성
    """

    def __init__(self):
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://ollama:11434')
        self.model = getattr(settings, 'OLLAMA_MODEL', 'exaone3.5:2.4b')
        self.timeout = getattr(settings, 'OLLAMA_TIMEOUT', 30)
        self.generate_url = f'{self.base_url}/api/generate'

    def _generate(self, prompt: str, system_prompt: str = '') -> str:
        """
        Ollama API 호출 - 텍스트 생성
        :param prompt: 사용자 입력 프롬프트
        :param system_prompt: 시스템 지시 프롬프트
        :return: 생성된 텍스트 (실패 시 fallback 메시지)
        """
        payload = {
            'model': self.model,
            'prompt': prompt,
            'system': system_prompt,
            'stream': False,  # 스트리밍 비활성화 (동기 처리)
            'options': {
                'temperature': 0.7,     # 창의성 수준
                'top_p': 0.9,
                'num_predict': 300,     # 최대 토큰 수 (200자 한국어 기준)
                'stop': ['\n\n\n'],     # 과도한 개행 방지
            },
        }

        try:
            logger.debug(f'Ollama API 호출: model={self.model}, prompt_len={len(prompt)}')
            response = requests.post(
                self.generate_url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()
            text = result.get('response', '').strip()
            logger.debug(f'Ollama 응답: {len(text)}자')
            return text

        except requests.exceptions.ConnectionError:
            logger.warning('Ollama 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.')
            return '[AI 분석 불가: Ollama 서버 연결 실패]'

        except requests.exceptions.Timeout:
            logger.warning(f'Ollama API 타임아웃 ({self.timeout}초)')
            return '[AI 분석 불가: 응답 시간 초과]'

        except requests.exceptions.HTTPError as e:
            logger.error(f'Ollama API HTTP 오류: {e}')
            return f'[AI 분석 불가: HTTP 오류 {e.response.status_code}]'

        except Exception as e:
            logger.error(f'Ollama API 예상치 못한 오류: {e}', exc_info=True)
            return '[AI 분석 불가: 알 수 없는 오류]'

    def analyze_price_movement(
        self,
        symbol: str,
        current_price: float,
        change_24h: float,
        volume_24h: float,
    ) -> str:
        """
        코인 가격 변동 원인 분석
        :param symbol: 코인 심볼 (예: BTCUSDT)
        :param current_price: 현재 가격 (USDT)
        :param change_24h: 24시간 등락률 (%)
        :param volume_24h: 24시간 거래량
        :return: 분석 텍스트 (한국어, 200자 이내)
        """
        base_symbol = symbol.replace('USDT', '')
        direction = '상승' if change_24h >= 0 else '하락'
        abs_change = abs(change_24h)

        system_prompt = (
            "당신은 암호화폐 시장을 분석하는 전문 애널리스트입니다. "
            "제공된 데이터를 바탕으로 간결하고 객관적인 시장 분석을 제공합니다. "
            "응답은 반드시 한국어로, 200자 이내로 작성하세요. "
            "투자 조언이나 매매 추천은 절대 하지 마세요. "
            "현재 시장 상황만 분석하세요."
        )

        prompt = (
            f"{base_symbol} 현재 시장 데이터:\n"
            f"- 현재가: ${current_price:,.2f} USDT\n"
            f"- 24시간 변동률: {'+' if change_24h >= 0 else ''}{change_24h:.2f}% ({direction})\n"
            f"- 24시간 거래량: ${volume_24h:,.0f} USDT\n\n"
            f"위 데이터를 바탕으로 {base_symbol}의 현재 가격 {direction} 상황을 200자 이내로 분석해주세요. "
            f"투자 조언은 하지 마세요."
        )

        return self._generate(prompt, system_prompt)

    def analyze_alert_trigger(
        self,
        symbol: str,
        target_price: float,
        current_price: float,
        condition: str,
    ) -> str:
        """
        알림 트리거 시 상황 설명 생성
        :param symbol: 코인 심볼
        :param target_price: 설정된 목표 가격
        :param current_price: 현재 가격
        :param condition: 조건 ('above' 또는 'below')
        :return: 상황 설명 텍스트 (한국어, 200자 이내)
        """
        base_symbol = symbol.replace('USDT', '')
        condition_text = '이상' if condition == 'above' else '이하'
        diff = current_price - target_price
        diff_pct = (diff / target_price) * 100

        system_prompt = (
            "당신은 암호화폐 가격 알림 시스템의 분석 모듈입니다. "
            "설정된 가격 조건이 충족되었을 때 간결한 상황 요약을 제공합니다. "
            "응답은 반드시 한국어로, 200자 이내로 작성하세요. "
            "투자 조언이나 매매 추천은 하지 마세요."
        )

        prompt = (
            f"[{base_symbol} 가격 알림 발동]\n"
            f"- 알림 조건: 목표가 ${target_price:,.2f} {condition_text}\n"
            f"- 현재가: ${current_price:,.2f} USDT\n"
            f"- 목표가 대비: {'+' if diff >= 0 else ''}{diff_pct:.2f}%\n\n"
            f"이 알림 상황을 200자 이내로 간결하게 설명해주세요. "
            f"투자 조언은 제외하세요."
        )

        return self._generate(prompt, system_prompt)

    def generate_market_summary(self, coins_data: list) -> str:
        """
        전체 시장 요약 생성
        :param coins_data: 코인 데이터 리스트
            [{'symbol': 'BTCUSDT', 'price': 95000, 'change_24h': 2.5, 'volume_24h': 1000000}, ...]
        :return: 시장 요약 텍스트 (한국어, 200자 이내)
        """
        if not coins_data:
            return '[분석할 데이터가 없습니다]'

        system_prompt = (
            "당신은 암호화폐 시장 전체를 분석하는 전문 애널리스트입니다. "
            "여러 코인의 데이터를 종합하여 전반적인 시장 동향을 분석합니다. "
            "응답은 반드시 한국어로, 200자 이내로 작성하세요. "
            "투자 조언이나 매매 추천은 절대 하지 마세요."
        )

        # 코인 데이터 문자열 구성
        coins_str_parts = []
        for coin in coins_data:
            base = coin['symbol'].replace('USDT', '')
            change = coin.get('change_24h', 0)
            price = coin.get('price', 0)
            coins_str_parts.append(
                f"  - {base}: ${price:,.2f} ({'+' if change >= 0 else ''}{change:.2f}%)"
            )
        coins_str = '\n'.join(coins_str_parts)

        # 시장 전체 통계
        changes = [c.get('change_24h', 0) for c in coins_data]
        rising = sum(1 for c in changes if c > 0)
        falling = sum(1 for c in changes if c < 0)
        avg_change = sum(changes) / len(changes) if changes else 0

        prompt = (
            f"현재 암호화폐 시장 현황:\n{coins_str}\n\n"
            f"전체 통계: 상승 {rising}종목 / 하락 {falling}종목 / 평균 변동률 {avg_change:+.2f}%\n\n"
            f"위 데이터를 바탕으로 현재 시장 전반적인 동향을 200자 이내로 요약해주세요. "
            f"투자 조언은 제외하세요."
        )

        return self._generate(prompt, system_prompt)

    def health_check(self) -> bool:
        """
        Ollama 서버 상태 확인
        :return: 서버 정상 여부
        """
        try:
            response = requests.get(
                f'{self.base_url}/api/tags',
                timeout=5,
            )
            return response.status_code == 200
        except Exception:
            return False


# 싱글턴 인스턴스 (앱 전역에서 재사용)
ollama_client = OllamaClient()
