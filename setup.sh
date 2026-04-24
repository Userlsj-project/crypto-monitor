#!/bin/bash
# ============================================================
# crypto_monitor 초기 환경 세팅 스크립트
# WSL Ubuntu 24.04 전용
# 실행: chmod +x setup.sh && ./setup.sh
# ============================================================

set -e  # 오류 발생 시 즉시 중단

# ─── 색상 코드 ────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'  # 색상 리셋

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error()   { echo -e "${RED}[✗]${NC} $1"; }
log_step()    { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}"; }

# ─── 실행 위치 확인 ───────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
log_info "작업 디렉토리: $SCRIPT_DIR"

# ─── 1. 시스템 패키지 업데이트 ───────────────────────────
log_step "1. 시스템 패키지 업데이트"
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    apt-transport-https
log_success "시스템 패키지 업데이트 완료"

# ─── 2. Docker 설치 ───────────────────────────────────────
log_step "2. Docker 설치 확인"
if command -v docker &>/dev/null; then
    DOCKER_VER=$(docker --version)
    log_success "Docker 이미 설치됨: $DOCKER_VER"
else
    log_info "Docker 설치 중..."
    # Docker 공식 GPG 키 추가
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    # Docker 저장소 추가
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -qq
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin

    # 현재 사용자를 docker 그룹에 추가
    sudo usermod -aG docker "$USER"
    log_success "Docker 설치 완료 (재로그인 후 sudo 없이 사용 가능)"
fi

# ─── 3. Docker Compose 확인 ───────────────────────────────
log_step "3. Docker Compose 확인"
if docker compose version &>/dev/null; then
    COMPOSE_VER=$(docker compose version --short)
    log_success "Docker Compose Plugin 사용 가능: v$COMPOSE_VER"
elif command -v docker-compose &>/dev/null; then
    log_success "docker-compose 사용 가능"
else
    log_info "Docker Compose v2 설치 중..."
    sudo apt-get install -y docker-compose-plugin
    log_success "Docker Compose 설치 완료"
fi

# ─── 4. Ollama 설치 ───────────────────────────────────────
log_step "4. Ollama 설치 (호스트 PC - 선택사항)"
if command -v ollama &>/dev/null; then
    OLLAMA_VER=$(ollama --version 2>/dev/null || echo "설치됨")
    log_success "Ollama 이미 설치됨: $OLLAMA_VER"
else
    log_info "Ollama 설치 중 (Docker 방식 사용 시 스킵 가능)..."
    log_warn "Ollama는 Docker 컨테이너로도 실행됩니다."
    log_warn "호스트 Ollama가 필요하다면: curl -fsSL https://ollama.com/install.sh | sh"
    # 자동 설치하려면 아래 주석 해제:
    # curl -fsSL https://ollama.com/install.sh | sh
fi

# ─── 5. 디렉토리 구조 생성 ────────────────────────────────
log_step "5. 프로젝트 디렉토리 구조 생성"
mkdir -p \
    django/staticfiles \
    django/media \
    django/static \
    grafana/provisioning/datasources \
    grafana/provisioning/dashboards \
    n8n/workflows \
    nginx \
    tests

log_success "디렉토리 구조 생성 완료"

# ─── 6. .env 파일 생성 ────────────────────────────────────
log_step "6. 환경 변수 파일 설정"
if [ -f ".env" ]; then
    log_warn ".env 파일이 이미 존재합니다. 덮어쓰지 않습니다."
else
    cp .env.example .env
    # 랜덤 SECRET_KEY 생성
    SECRET_KEY=$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*') for _ in range(50)))" 2>/dev/null || openssl rand -hex 25)
    sed -i "s/your-very-secret-key-change-this-in-production/$SECRET_KEY/" .env
    log_success ".env 파일 생성 완료 (SECRET_KEY 자동 생성)"
    log_warn "SMTP 설정은 .env 파일에서 직접 수정하세요."
fi

# ─── 7. 파일 권한 설정 ────────────────────────────────────
log_step "7. 스크립트 파일 권한 설정"
chmod +x setup.sh start.sh demo.sh 2>/dev/null || true
log_success "실행 권한 설정 완료"

# ─── 8. WSL 메모리 설정 권고 ─────────────────────────────
log_step "8. WSL 메모리 설정 (EXAONE 3.5 2.4B 실행용)"
WSLCONFIG="$HOME/.wslconfig"
if [ ! -f "$WSLCONFIG" ]; then
    cat > "$WSLCONFIG" <<'EOF'
[wsl2]
# EXAONE 3.5 2.4B 모델 실행을 위해 최소 8GB 권장
memory=10GB
# CPU 코어 수 (선택사항)
# processors=8
# swap 영역
swap=4GB
EOF
    log_success "~/.wslconfig 생성 완료 (메모리: 10GB)"
    log_warn "WSL 메모리 설정 적용을 위해 PowerShell에서 'wsl --shutdown' 실행 후 재시작하세요."
else
    log_info "~/.wslconfig 이미 존재합니다."
fi

# ─── 9. Docker 서비스 시작 ────────────────────────────────
log_step "9. Docker 서비스 상태 확인"
if ! sudo systemctl is-active --quiet docker 2>/dev/null; then
    log_info "Docker 서비스 시작 중..."
    sudo service docker start 2>/dev/null || sudo systemctl start docker 2>/dev/null || true
fi

# WSL에서는 systemctl이 없을 수 있음
if docker info &>/dev/null; then
    log_success "Docker 서비스 실행 중"
else
    log_warn "Docker 서비스를 시작할 수 없습니다."
    log_warn "WSL에서: sudo service docker start"
    log_warn "또는 Docker Desktop을 시작하세요."
fi

# ─── 완료 메시지 ──────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║          초기 환경 세팅 완료!                        ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "다음 단계:"
echo -e "  ${CYAN}1.${NC} .env 파일의 SMTP 설정 수정 (이메일 알림 필요 시)"
echo -e "  ${CYAN}2.${NC} ${BOLD}./start.sh${NC} 실행으로 전체 서비스 시작"
echo -e "  ${CYAN}3.${NC} EXAONE 모델 pull: ${BOLD}docker exec crypto_ollama ollama pull exaone3.5:2.4b${NC}"
echo ""
echo -e "접속 주소:"
echo -e "  Django:  ${BOLD}http://localhost${NC}"
echo -e "  Grafana: ${BOLD}http://localhost:3000${NC}"
echo -e "  n8n:     ${BOLD}http://localhost:5678${NC}"
echo -e "  Ollama:  ${BOLD}http://localhost:11434${NC}"
echo ""
