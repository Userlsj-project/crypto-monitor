#!/bin/bash
# ============================================================
# crypto_monitor 프로젝트 실행 스크립트
# 실행: ./start.sh [옵션]
# 옵션:
#   --build    Docker 이미지 강제 재빌드
#   --fresh    볼륨 삭제 후 완전 초기화
#   --stop     모든 서비스 중지
#   --logs     서비스 로그 출력
#   --pull-model  EXAONE 모델 pull (시간 오래 걸림)
# ============================================================

set -e

# ─── 색상 코드 ────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_step()    { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ─── 옵션 파싱 ────────────────────────────────────────────
BUILD_FLAG=""
FRESH=false
PULL_MODEL=false

for arg in "$@"; do
    case $arg in
        --build)      BUILD_FLAG="--build"; shift ;;
        --fresh)      FRESH=true; shift ;;
        --stop)
            log_step "서비스 중지"
            docker compose down
            log_success "모든 서비스 중지 완료"
            exit 0
            ;;
        --logs)
            docker compose logs -f --tail=100
            exit 0
            ;;
        --pull-model) PULL_MODEL=true; shift ;;
        --status)
            docker compose ps
            exit 0
            ;;
    esac
done

echo -e "${BOLD}${CYAN}"
echo "  ██████╗██████╗ ██╗   ██╗██████╗ ████████╗ ██████╗ "
echo " ██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗"
echo " ██║     ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║   ██║"
echo " ██║     ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║   ██║"
echo " ╚██████╗██║  ██║   ██║   ██║        ██║   ╚██████╔╝"
echo "  ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝    ╚═════╝ "
echo "           MONITOR  |  Django + EXAONE 3.5            "
echo -e "${NC}"

# ─── .env 파일 확인 ───────────────────────────────────────
log_step "환경 변수 파일 확인"
if [ ! -f ".env" ]; then
    log_warn ".env 파일이 없습니다. .env.example에서 복사합니다."
    cp .env.example .env
    log_success ".env 파일 생성됨"
else
    log_success ".env 파일 확인됨"
fi

# ─── 완전 초기화 옵션 ─────────────────────────────────────
if [ "$FRESH" = true ]; then
    log_step "완전 초기화 (볼륨 포함 삭제)"
    log_warn "모든 데이터가 삭제됩니다. 5초 후 시작합니다... (Ctrl+C로 취소)"
    sleep 5
    docker compose down -v --remove-orphans
    log_success "기존 컨테이너 및 볼륨 삭제 완료"
    BUILD_FLAG="--build"
fi

# ─── Docker 실행 확인 ─────────────────────────────────────
log_step "Docker 상태 확인"
if ! docker info &>/dev/null; then
    log_warn "Docker가 실행 중이 아닙니다. 시작 시도 중..."
    sudo service docker start 2>/dev/null || true
    sleep 3
    if ! docker info &>/dev/null; then
        echo -e "${RED}Docker를 시작할 수 없습니다.${NC}"
        echo "WSL에서: sudo service docker start"
        echo "또는 Docker Desktop을 시작하세요."
        exit 1
    fi
fi
log_success "Docker 실행 중"

# ─── Docker Compose 서비스 시작 ───────────────────────────
log_step "Docker Compose 서비스 시작"
log_info "서비스: postgres, redis, django, celery_worker, celery_beat, grafana, n8n, ollama, nginx"

if docker compose version &>/dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# 인프라 서비스 먼저 시작 (postgres, redis)
log_info "1/3 인프라 서비스 시작 (postgres, redis)..."
$COMPOSE_CMD up -d postgres redis $BUILD_FLAG

# postgres와 redis가 준비될 때까지 대기
log_info "PostgreSQL 준비 대기..."
MAX_WAIT=60
COUNT=0
until $COMPOSE_CMD exec -T postgres pg_isready -U crypto_user -d crypto_monitor -q 2>/dev/null; do
    COUNT=$((COUNT + 1))
    if [ $COUNT -ge $MAX_WAIT ]; then
        echo -e "${RED}PostgreSQL 시작 타임아웃 (${MAX_WAIT}초)${NC}"
        $COMPOSE_CMD logs postgres
        exit 1
    fi
    printf '.'
    sleep 1
done
echo ""
log_success "PostgreSQL 준비 완료"

log_info "Redis 준비 대기..."
COUNT=0
until $COMPOSE_CMD exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; do
    COUNT=$((COUNT + 1))
    if [ $COUNT -ge 30 ]; then
        echo -e "${RED}Redis 시작 타임아웃${NC}"
        exit 1
    fi
    printf '.'
    sleep 1
done
echo ""
log_success "Redis 준비 완료"

# Ollama 시작
log_info "2/3 Ollama LLM 서버 시작..."
$COMPOSE_CMD up -d ollama $BUILD_FLAG

# Django, Celery 시작
log_info "3/3 Django, Celery, Grafana, n8n, Nginx 시작..."
$COMPOSE_CMD up -d django celery_worker celery_beat grafana n8n nginx $BUILD_FLAG

# ─── Django 마이그레이션 완료 대기 ────────────────────────
log_step "Django 초기화 대기"
log_info "마이그레이션 및 초기 데이터 삽입 대기..."
MAX_WAIT=120
COUNT=0
until $COMPOSE_CMD exec -T django python manage.py check --deploy 2>/dev/null | grep -q "no critical issues" || \
      $COMPOSE_CMD exec -T django python -c "import django; django.setup()" 2>/dev/null; do
    COUNT=$((COUNT + 1))
    if [ $COUNT -ge $MAX_WAIT ]; then
        log_warn "Django 준비 타임아웃 - 로그를 확인하세요."
        $COMPOSE_CMD logs django --tail=20
        break
    fi
    printf '.'
    sleep 2
done
echo ""

# ─── Celery Beat 스케줄 확인 ──────────────────────────────
log_step "Celery Beat 스케줄 등록 확인"
sleep 5
if $COMPOSE_CMD exec -T django python -c "
import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()
from django_celery_beat.models import PeriodicTask
count = PeriodicTask.objects.count()
print(f'등록된 태스크: {count}개')
" 2>/dev/null; then
    log_success "Celery Beat 스케줄 확인 완료"
else
    log_warn "Celery Beat 스케줄 확인 실패 (서비스는 계속 실행 중)"
fi

# ─── EXAONE 모델 Pull (옵션) ──────────────────────────────
if [ "$PULL_MODEL" = true ]; then
    log_step "EXAONE 3.5 2.4B 모델 다운로드"
    log_warn "모델 크기: ~1.7GB, 시간이 걸립니다..."
    log_info "Ollama 준비 대기..."
    sleep 10
    $COMPOSE_CMD exec ollama ollama pull exaone3.5:2.4b
    log_success "EXAONE 3.5 2.4B 모델 다운로드 완료"
else
    log_warn "EXAONE 모델 pull 스킵 (아직 미설치 시 AI 분석 비활성)"
    log_warn "수동 설치: docker exec crypto_ollama ollama pull exaone3.5:2.4b"
fi

# ─── 서비스 상태 출력 ─────────────────────────────────────
log_step "서비스 상태"
$COMPOSE_CMD ps

# ─── 완료 메시지 ──────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║            서비스 시작 완료!                              ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}접속 주소:${NC}"
echo -e "  🌐 대시보드:  ${CYAN}http://localhost${NC}"
echo -e "  📊 Grafana:   ${CYAN}http://localhost:3000${NC}  (admin / admin123)"
echo -e "  🔄 n8n:       ${CYAN}http://localhost:5678${NC}  (admin / n8n_password)"
echo -e "  🤖 Ollama:    ${CYAN}http://localhost:11434${NC}"
echo -e "  ⚙  Admin:     ${CYAN}http://localhost/admin/${NC}"
echo ""
echo -e "${BOLD}유용한 명령어:${NC}"
echo -e "  로그 확인:    ${YELLOW}./start.sh --logs${NC}"
echo -e "  서비스 중지:  ${YELLOW}./start.sh --stop${NC}"
echo -e "  재빌드:       ${YELLOW}./start.sh --build${NC}"
echo -e "  전체 초기화:  ${YELLOW}./start.sh --fresh${NC}"
echo -e "  모델 pull:    ${YELLOW}docker exec crypto_ollama ollama pull exaone3.5:2.4b${NC}"
echo ""
echo -e "${BOLD}개별 서비스 로그:${NC}"
echo -e "  ${YELLOW}docker compose logs -f django${NC}"
echo -e "  ${YELLOW}docker compose logs -f celery_worker${NC}"
echo -e "  ${YELLOW}docker compose logs -f celery_beat${NC}"
echo ""
