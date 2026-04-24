#!/bin/bash
# ============================================================
# crypto_monitor 데모 시나리오 스크립트
# 동영상 촬영/시연용: 테스트 데이터 삽입, 알림 즉시 트리거, AI 분석
# 실행: ./demo.sh [시나리오]
# 시나리오:
#   all           전체 시나리오 실행 (기본값)
#   seed-prices   테스트 가격 데이터 강제 삽입
#   trigger-alert 알림 조건 즉시 트리거
#   ai-analysis   AI 분석 즉시 실행
#   stress        30초 동안 빠른 가격 업데이트 시뮬레이션
#   reset         데모 데이터 초기화
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_step()    { echo -e "\n${BOLD}${CYAN}═══ $1 ═══${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DJANGO_EXEC="docker compose exec -T django python manage.py shell -c"

# ─── Django shell 명령 헬퍼 ───────────────────────────────
run_django() {
    docker compose exec -T django python manage.py shell -c "$1"
}

# ─── 시나리오 1: 테스트 가격 데이터 삽입 ─────────────────
demo_seed_prices() {
    log_step "시나리오 1: 테스트 가격 데이터 강제 삽입"
    log_info "BTC, ETH, BNB, XRP, SOL 가격 데이터를 시뮬레이션합니다..."

    run_django "
from apps.coins.models import Coin, CoinPrice
from decimal import Decimal
from django.utils import timezone
import datetime, random

# 시뮬레이션 가격 데이터 (현실적인 값)
demo_prices = {
    'BTCUSDT': {'price': 95432.50, 'change': 2.35, 'volume': 1523456789},
    'ETHUSDT': {'price': 3245.80, 'change': -1.28, 'volume': 823456789},
    'BNBUSDT': {'price': 425.60, 'change': 0.85, 'volume': 423456789},
    'XRPUSDT': {'price': 0.5512, 'change': -2.10, 'volume': 623456789},
    'SOLUSDT': {'price': 182.35, 'change': 3.45, 'volume': 523456789},
}

now = timezone.now()
count = 0

# 최근 1시간치 데이터 (2분 간격, 30개 포인트)
for i in range(30, -1, -1):
    ts = now - datetime.timedelta(minutes=i*2)
    for symbol, base_data in demo_prices.items():
        try:
            coin = Coin.objects.get(symbol=symbol, is_active=True)
        except Coin.DoesNotExist:
            print(f'  스킵: {symbol} (미등록)')
            continue

        # 랜덤 가격 변동 ±1%
        noise = random.uniform(-0.01, 0.01)
        price = Decimal(str(base_data['price'] * (1 + noise)))
        change = Decimal(str(base_data['change'] + random.uniform(-0.5, 0.5)))
        volume = Decimal(str(base_data['volume'] * random.uniform(0.9, 1.1)))
        high = price * Decimal('1.005')
        low = price * Decimal('0.995')

        CoinPrice.objects.create(
            coin=coin,
            price=price,
            change_24h=change,
            volume_24h=volume,
            high_24h=high,
            low_24h=low,
            timestamp=ts,
        )
        count += 1

print(f'  ✓ 총 {count}개 가격 데이터 삽입 완료')
print(f'  기간: {(now - datetime.timedelta(hours=1)).strftime(\"%H:%M\")} ~ {now.strftime(\"%H:%M\")}')
"
    log_success "테스트 가격 데이터 삽입 완료"
    echo ""
    log_info "Grafana에서 확인: http://localhost:3000"
    log_info "API에서 확인: http://localhost/api/coins/latest/"
}

# ─── 시나리오 2: 알림 즉시 트리거 ────────────────────────
demo_trigger_alert() {
    log_step "시나리오 2: 알림 조건 즉시 트리거"
    log_info "현재 BTC 가격보다 낮은 목표가로 알림을 생성하고 즉시 트리거..."

    run_django "
from apps.coins.models import Coin, CoinPrice
from apps.alerts.models import Alert, AlertLog
from decimal import Decimal

# 현재 BTC 가격 조회
try:
    btc = Coin.objects.get(symbol='BTCUSDT', is_active=True)
    latest = btc.prices.first()
    if not latest:
        print('  ✗ BTC 가격 데이터 없음. seed-prices 먼저 실행하세요.')
        exit(1)

    current_price = float(latest.price)
    # 현재가보다 낮은 목표가 설정 (즉시 above 조건 충족)
    trigger_price = Decimal(str(current_price * 0.98))  # 2% 낮게

    # 기존 데모 알림 삭제
    Alert.objects.filter(coin=btc, target_price=trigger_price).delete()

    # 새 알림 생성
    alert = Alert.objects.create(
        coin=btc,
        condition='above',
        target_price=trigger_price,
        is_active=True,
    )
    print(f'  ✓ 알림 생성: BTC \${current_price:,.2f} >= \${trigger_price} 조건')

    # AI 분석 Mock (Ollama 없어도 동작)
    ai_text = f'BTC가 목표가 \${trigger_price}를 상회하여 \${current_price:,.2f}에 도달했습니다. 강한 매수세가 지속되고 있습니다.'

    # AlertLog 직접 생성 (즉시 트리거)
    log = AlertLog.objects.create(
        alert=alert,
        message=f'BTC/USDT 가격 알림: 현재가 \${current_price:,.2f}가 목표가 \${trigger_price} 이상',
        ai_analysis=ai_text,
        triggered_price=latest.price,
    )
    print(f'  ✓ 알림 발동 로그 생성: ID={log.id}')
    print(f'  ✓ AI 분석: {ai_text[:60]}...')
except Exception as e:
    print(f'  ✗ 오류: {e}')
"
    log_success "알림 트리거 완료"
    echo ""
    log_info "알림 관리 페이지: http://localhost/alerts/"
    log_info "API: http://localhost/api/alerts/logs/"
}

# ─── 시나리오 3: AI 분석 즉시 실행 ───────────────────────
demo_ai_analysis() {
    log_step "시나리오 3: AI 분석 즉시 실행"
    log_info "BTC, ETH, SOL 개별 분석 + 시장 전체 요약..."

    # Ollama health check
    if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        log_info "Ollama 서버 미실행 - Mock 분석 결과 삽입"
        run_django "
from apps.coins.models import Coin, CoinPrice
from apps.alerts.models import Alert, AlertLog

mock_analyses = {
    'BTCUSDT': 'BTC는 95,000달러 구간에서 강력한 지지를 받으며 상승 흐름을 유지하고 있습니다. 거래량이 평균 대비 15% 증가한 상태입니다.',
    'ETHUSDT': 'ETH는 단기 조정 후 반등 시도 중입니다. 3,200달러 지지선 근처에서 매수세가 유입되고 있습니다.',
    'SOLUSDT': 'SOL이 3.45% 급등하며 상위권 코인 중 가장 강한 상승세를 보이고 있습니다. 생태계 확장 기대감이 반영된 것으로 분석됩니다.',
}

for symbol, analysis in mock_analyses.items():
    try:
        coin = Coin.objects.get(symbol=symbol, is_active=True)
        latest = coin.prices.first()
        if latest:
            print(f'  ✓ {symbol}: {analysis[:50]}...')
    except:
        pass

print('  ✓ Mock AI 분석 완료 (Ollama 없이 시뮬레이션)')
"
    else
        log_info "Ollama 서버 실행 중 - 실제 EXAONE 분석 요청..."
        # API를 통해 분석 요청
        for SYMBOL in BTCUSDT ETHUSDT SOLUSDT; do
            echo -n "  $SYMBOL 분석 중..."
            RESULT=$(curl -sf -X POST http://localhost/api/coins/ai-analysis/ \
                -H "Content-Type: application/json" \
                -d "{\"symbol\": \"$SYMBOL\"}" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('analysis','')[:60])" 2>/dev/null || echo "분석 실패")
            echo " $RESULT"
        done

        echo ""
        log_info "시장 전체 요약 요청..."
        SUMMARY=$(curl -sf http://localhost/api/coins/market-summary/ 2>/dev/null \
            | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('summary','')[:80])" 2>/dev/null || echo "요약 실패")
        echo "  $SUMMARY"
    fi

    log_success "AI 분석 시나리오 완료"
    echo ""
    log_info "AI 분석 페이지: http://localhost/ai-analysis/"
}

# ─── 시나리오 4: 가격 변동 스트레스 테스트 ───────────────
demo_stress() {
    log_step "시나리오 4: 빠른 가격 업데이트 시뮬레이션 (30초)"
    log_info "5초마다 가격 데이터를 업데이트합니다..."

    for i in $(seq 1 6); do
        run_django "
from apps.coins.models import Coin, CoinPrice
from decimal import Decimal
from django.utils import timezone
import random

coins = Coin.objects.filter(is_active=True)
now = timezone.now()
for coin in coins:
    latest = coin.prices.first()
    if latest:
        # 이전 가격 기준 ±0.5% 변동
        factor = random.uniform(0.995, 1.005)
        new_price = latest.price * Decimal(str(factor))
        change = float(latest.change_24h) + random.uniform(-0.1, 0.1)
        CoinPrice.objects.create(
            coin=coin,
            price=new_price,
            change_24h=Decimal(str(change)),
            volume_24h=latest.volume_24h * Decimal(str(random.uniform(0.95, 1.05))),
            high_24h=max(latest.high_24h, new_price),
            low_24h=min(latest.low_24h, new_price),
            timestamp=now,
        )
        print(f'  {coin.symbol}: \${float(new_price):,.4f}')
" 2>/dev/null
        echo "  [$i/6] 업데이트 완료. 5초 대기..."
        sleep 5
    done
    log_success "스트레스 테스트 완료 (대시보드에서 변화 확인)"
}

# ─── 시나리오 5: 데모 데이터 초기화 ─────────────────────
demo_reset() {
    log_step "데모 데이터 초기화"
    log_info "테스트로 삽입된 가격 데이터와 알림 로그 삭제..."

    run_django "
from apps.coins.models import CoinPrice
from apps.alerts.models import AlertLog, Alert

prices_deleted = CoinPrice.objects.all().delete()[0]
logs_deleted = AlertLog.objects.all().delete()[0]
alerts_deleted = Alert.objects.all().delete()[0]
print(f'  ✓ 가격 데이터: {prices_deleted}건 삭제')
print(f'  ✓ 알림 로그: {logs_deleted}건 삭제')
print(f'  ✓ 알림: {alerts_deleted}건 삭제')
"
    log_success "초기화 완료 (Celery Beat가 30초 내 새 데이터 수집 시작)"
}

# ─── 전체 시나리오 ────────────────────────────────────────
demo_all() {
    log_step "전체 데모 시나리오 시작"
    echo ""
    echo -e "${YELLOW}시나리오 순서:${NC}"
    echo "  1. 테스트 가격 데이터 삽입"
    echo "  2. 알림 조건 즉시 트리거"
    echo "  3. AI 분석 실행"
    echo ""

    demo_seed_prices
    sleep 2
    demo_trigger_alert
    sleep 2
    demo_ai_analysis

    echo ""
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}  전체 데모 시나리오 완료!${NC}"
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "지금 확인하세요:"
    echo -e "  🌐 대시보드:    ${CYAN}http://localhost${NC}"
    echo -e "  📊 Grafana:     ${CYAN}http://localhost:3000${NC}"
    echo -e "  🔔 알림 관리:   ${CYAN}http://localhost/alerts/${NC}"
    echo -e "  🤖 AI 분석:     ${CYAN}http://localhost/ai-analysis/${NC}"
}

# ─── 진입점 ───────────────────────────────────────────────
SCENARIO="${1:-all}"
case "$SCENARIO" in
    all)           demo_all ;;
    seed-prices)   demo_seed_prices ;;
    trigger-alert) demo_trigger_alert ;;
    ai-analysis)   demo_ai_analysis ;;
    stress)        demo_stress ;;
    reset)         demo_reset ;;
    *)
        echo "사용법: ./demo.sh [all|seed-prices|trigger-alert|ai-analysis|stress|reset]"
        exit 1
        ;;
esac
