# Crypto Monitor 트러블슈팅 가이드

WSL Ubuntu 24.04 환경에서 자주 발생하는 문제와 해결 방법입니다.

---

## 목차
1. [Docker 관련 문제](#1-docker-관련-문제)
2. [PostgreSQL 연결 문제](#2-postgresql-연결-문제)
3. [Redis / Celery 문제](#3-redis--celery-문제)
4. [Ollama / EXAONE 문제](#4-ollama--exaone-문제)
5. [Django / Gunicorn 문제](#5-django--gunicorn-문제)
6. [Grafana 문제](#6-grafana-문제)
7. [n8n 문제](#7-n8n-문제)
8. [WSL 네트워크 이슈](#8-wsl-네트워크-이슈)
9. [성능 최적화](#9-성능-최적화)

---

## 1. Docker 관련 문제

### Docker daemon 연결 실패
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```
**원인**: WSL에서 Docker 서비스가 중지됨  
**해결**:
```bash
# Docker 서비스 시작
sudo service docker start

# 또는 Docker Desktop 시작 후
wsl --shutdown
# WSL 재시작
```

### 권한 오류: permission denied while trying to connect to the Docker daemon
**원인**: 현재 사용자가 docker 그룹에 없음  
**해결**:
```bash
sudo usermod -aG docker $USER
# 로그아웃 후 재로그인 필요
newgrp docker  # 재로그인 없이 그룹 적용
```

### 포트 충돌 (Port already in use)
```
Bind for 0.0.0.0:5432 failed: port is already allocated
```
**해결**:
```bash
# 충돌 포트 사용 중인 프로세스 확인
sudo lsof -i :5432
# 또는
sudo netstat -tlnp | grep 5432

# 기존 컨테이너 정리
docker compose down
docker ps -a | grep Exit | awk '{print $1}' | xargs docker rm -f 2>/dev/null

# 호스트 PostgreSQL 중지
sudo service postgresql stop
```

### 컨테이너가 계속 재시작됨 (CrashLoopBackOff)
```bash
# 컨테이너 로그 확인
docker compose logs django --tail=50
docker compose logs celery_worker --tail=50

# 강제 재빌드
docker compose down
docker compose build --no-cache django
docker compose up -d
```

### 이미지 빌드 실패 (no space left on device)
**해결**:
```bash
# 사용하지 않는 Docker 리소스 정리
docker system prune -af --volumes

# WSL 디스크 공간 확인
df -h /
```

---

## 2. PostgreSQL 연결 문제

### Django: `could not translate host name "postgres" to address`
**원인**: Django 컨테이너가 PostgreSQL 컨테이너보다 먼저 시작됨  
**해결**: `docker compose restart django celery_worker celery_beat`

### `FATAL: password authentication failed for user "crypto_user"`
**원인**: `.env`의 PostgreSQL 비밀번호와 실제 볼륨 데이터 불일치  
**해결**:
```bash
# 볼륨 삭제 후 재생성
docker compose down -v
docker compose up -d postgres
sleep 10
docker compose up -d
```

### 마이그레이션 오류
```bash
# Django 컨테이너에서 직접 마이그레이션
docker exec crypto_django python manage.py migrate --verbosity=2

# 마이그레이션 상태 확인
docker exec crypto_django python manage.py showmigrations
```

---

## 3. Redis / Celery 문제

### Celery Worker가 태스크를 처리하지 않음
```bash
# Worker 상태 확인
docker compose logs celery_worker --tail=30

# Worker 재시작
docker compose restart celery_worker

# 태스크 수동 실행 테스트
docker exec crypto_django celery -A config call apps.coins.tasks.fetch_coin_prices
```

### Celery Beat가 스케줄 등록을 못 함
```bash
# Beat 로그 확인
docker compose logs celery_beat --tail=30

# Django shell에서 확인
docker exec crypto_django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
print('등록된 태스크:', PeriodicTask.objects.count())
for t in PeriodicTask.objects.all():
    print(f'  - {t.name}: {t.enabled}')
"
```

### Redis 메모리 부족
```
NOEVICT You've reached the maximum memory usage
```
**해결**:
```bash
# Redis 캐시 플러시
docker exec crypto_redis redis-cli FLUSHALL

# Redis 메모리 사용량 확인
docker exec crypto_redis redis-cli INFO memory | grep used_memory_human
```

---

## 4. Ollama / EXAONE 문제

### EXAONE 모델이 없음 (model not found)
```bash
# 모델 목록 확인
docker exec crypto_ollama ollama list

# EXAONE 3.5 2.4B 모델 pull (약 1.7GB, 시간 소요)
docker exec crypto_ollama ollama pull exaone3.5:2.4b

# Pull 진행 상황 확인 (백그라운드 실행 중인 경우)
docker exec crypto_ollama ollama list
```

### Ollama 메모리 부족 (OOM Kill)
**증상**: Ollama 컨테이너가 계속 종료됨  
**원인**: WSL 메모리 제한 또는 시스템 RAM 부족

**해결 방법 1 - WSL 메모리 증가**:
```ini
# ~/.wslconfig 파일 수정 (PowerShell에서)
[wsl2]
memory=12GB
swap=4GB
```
```powershell
# PowerShell에서 WSL 재시작
wsl --shutdown
```

**해결 방법 2 - 더 작은 모델 사용**:
```bash
# EXAONE 3.5 대신 더 작은 모델 (약 500MB)
docker exec crypto_ollama ollama pull exaone3.5:2.4b-q4_K_M

# .env 파일에서 모델명 변경
sed -i 's/OLLAMA_MODEL=exaone3.5:2.4b/OLLAMA_MODEL=exaone3.5:2.4b-q4_K_M/' .env
docker compose restart django celery_worker
```

**해결 방법 3 - Ollama 메모리 제한 조정**:
```yaml
# docker-compose.yml의 ollama 서비스에 추가
deploy:
  resources:
    limits:
      memory: 6G
```

### Ollama API 타임아웃 (30초)
**원인**: 모델 첫 로딩 시 시간이 더 걸림  
**해결**:
```bash
# .env에서 타임아웃 증가
sed -i 's/OLLAMA_TIMEOUT=30/OLLAMA_TIMEOUT=120/' .env
docker compose restart django celery_worker

# 또는 모델을 미리 워밍업
docker exec crypto_ollama ollama run exaone3.5:2.4b "안녕하세요"
```

### Ollama 연결 실패 (AI 분석 비활성)
```bash
# Ollama 컨테이너 상태 확인
docker compose ps ollama
docker compose logs ollama --tail=20

# 직접 API 테스트
curl http://localhost:11434/api/tags
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"exaone3.5:2.4b","prompt":"테스트","stream":false}'
```

---

## 5. Django / Gunicorn 문제

### Static files 404 오류
```bash
# 정적 파일 재수집
docker exec crypto_django python manage.py collectstatic --noinput --clear

# Nginx 설정 확인
docker compose logs nginx --tail=20
```

### `DisallowedHost` 오류
```
Invalid HTTP_HOST header: '...'
```
**해결**: `.env`의 `ALLOWED_HOSTS`에 해당 호스트 추가
```bash
# 예: IP 주소 추가
echo "ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,192.168.1.100" >> .env
docker compose restart django
```

### Django Admin 계정 생성
```bash
docker exec -it crypto_django python manage.py createsuperuser
```

### seed_coins 실패
```bash
# 수동으로 seed 실행
docker exec crypto_django python manage.py seed_coins

# 재삽입 (기존 데이터 초기화)
docker exec crypto_django python manage.py seed_coins --reset
```

---

## 6. Grafana 문제

### Grafana가 PostgreSQL에 연결 못 함
```
pq: password authentication failed
```
**해결**: `grafana/provisioning/datasources/postgres.yml`의 비밀번호를 `.env`와 일치시킴
```bash
# 현재 .env 비밀번호 확인
grep POSTGRES_PASSWORD .env

# datasource 파일 수정 후 Grafana 재시작
docker compose restart grafana
```

### 대시보드가 표시되지 않음
```bash
# Grafana 로그 확인
docker compose logs grafana --tail=30

# 프로비저닝 파일 권한 확인
ls -la grafana/provisioning/dashboards/

# Grafana 재시작
docker compose restart grafana
```

### iframe 임베드 거부 (X-Frame-Options)
**원인**: Grafana의 iframe 보안 설정  
**해결**: `docker-compose.yml`의 Grafana 환경변수에 추가:
```yaml
- GF_SECURITY_ALLOW_EMBEDDING=true
- GF_AUTH_ANONYMOUS_ENABLED=true
```

---

## 7. n8n 문제

### Webhook이 작동하지 않음
```bash
# n8n 로그 확인
docker compose logs n8n --tail=30

# Webhook URL 테스트
curl -X POST http://localhost:5678/webhook/crypto-alert \
  -H "Content-Type: application/json" \
  -d '{"coin_symbol":"BTCUSDT","current_price":95000}'
```

### SMTP 이메일 발송 실패
1. n8n 웹 UI (http://localhost:5678) 접속
2. **Credentials** → **SMTP** 계정 추가
   - Host: `smtp.gmail.com`, Port: `587`
   - User: Gmail 주소
   - Password: Gmail 앱 비밀번호 (일반 비밀번호 X)
3. Gmail 앱 비밀번호 발급: Google 계정 → 보안 → 2단계 인증 → 앱 비밀번호

### 워크플로우 임포트 방법
1. n8n 웹 UI 접속: http://localhost:5678
2. 좌측 메뉴 → **Workflows** → **Import from File**
3. `n8n/workflows/alert_notification.json` 파일 선택
4. **Save** 후 **Activate** 토글 활성화

---

## 8. WSL 네트워크 이슈

### Windows에서 localhost로 접속 안 됨
**원인**: WSL2의 IP가 `localhost`와 다를 수 있음  
**해결**:
```powershell
# PowerShell에서 WSL IP 확인
wsl hostname -I

# Windows hosts 파일에 추가 (관리자 권한)
# C:\Windows\System32\drivers\etc\hosts
# <WSL-IP> crypto.local
```

### Docker 네트워크 내 컨테이너 간 통신 실패
```bash
# 네트워크 상태 확인
docker network ls
docker network inspect crypto_monitor_crypto_network

# 컨테이너 내에서 다른 컨테이너 ping
docker exec crypto_django ping -c 3 postgres
docker exec crypto_django ping -c 3 redis
docker exec crypto_django ping -c 3 ollama
```

### DNS 해석 실패 (api.binance.com)
**원인**: WSL DNS 설정 문제  
**해결**:
```bash
# /etc/resolv.conf 수정
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

# WSL DNS 자동 생성 비활성화
sudo tee /etc/wsl.conf << 'EOF'
[network]
generateResolvConf = false
EOF
```

---

## 9. 성능 최적화

### 전체 서비스 메모리 사용량 최적화
```yaml
# docker-compose.yml에 메모리 제한 추가
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 6G    # EXAONE 2.4B: 약 4-5GB 필요
  django:
    deploy:
      resources:
        limits:
          memory: 512M
  celery_worker:
    deploy:
      resources:
        limits:
          memory: 256M
```

### PostgreSQL 오래된 데이터 수동 정리
```bash
docker exec crypto_django python manage.py shell -c "
from apps.coins.models import CoinPrice
from django.utils import timezone

# 48시간 이상 된 데이터 삭제
cutoff = timezone.now() - timezone.timedelta(hours=48)
deleted, _ = CoinPrice.objects.filter(timestamp__lt=cutoff).delete()
print(f'{deleted}건 삭제됨')
"
```

### Celery Worker 수 조정
```bash
# docker-compose.yml의 celery_worker command 수정
# --concurrency=2  (메모리 절약)
# --concurrency=8  (고성능)
```

---

## 빠른 진단 명령어

```bash
# 전체 서비스 상태 확인
docker compose ps

# 각 서비스 로그 실시간 확인
docker compose logs -f django
docker compose logs -f celery_worker
docker compose logs -f celery_beat
docker compose logs -f ollama

# API 엔드포인트 테스트
curl -s http://localhost/api/coins/latest/ | python3 -m json.tool | head -30
curl -s http://localhost/api/coins/ollama-health/

# Django 쉘 접속
docker exec -it crypto_django python manage.py shell

# PostgreSQL 접속
docker exec -it crypto_postgres psql -U crypto_user -d crypto_monitor

# Redis 접속
docker exec -it crypto_redis redis-cli

# Celery 활성 태스크 확인
docker exec crypto_django celery -A config inspect active

# 전체 서비스 재시작
docker compose restart
```
