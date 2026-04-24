# Crypto Monitor

실시간 암호화폐 가격 모니터링 및 AI 분석 알림 플랫폼

Binance 공개 API로 5개 코인(BTC, ETH, BNB, XRP, SOL)의 가격을 30초마다 자동 수집하고, 사용자 정의 조건 충족 시 EXAONE AI 분석과 함께 알림을 발송합니다.

---

## 시스템 아키텍처

```mermaid
graph TB
    subgraph External["외부 서비스"]
        BINANCE["🌐 Binance Public API<br/>(30초마다 가격 수집)"]
        EMAIL["📧 이메일 서버<br/>(Gmail SMTP)"]
    end

    subgraph Docker["Docker Compose 스택"]
        NGINX["🔀 Nginx<br/>리버스 프록시 :80"]

        subgraph App["애플리케이션 레이어"]
            DJANGO["⚙️ Django + Gunicorn<br/>웹 서버 :8000"]
            CELERY_W["👷 Celery Worker<br/>비동기 태스크"]
            CELERY_B["⏰ Celery Beat<br/>스케줄러"]
        end

        subgraph Data["데이터 레이어"]
            PG["🗄️ PostgreSQL 15<br/>가격·알림 데이터"]
            REDIS["⚡ Redis 7<br/>메시지 브로커·캐시"]
        end

        subgraph Intelligence["분석·자동화"]
            OLLAMA["🤖 Ollama<br/>EXAONE 3.5 2.4B LLM"]
            N8N["🔄 n8n<br/>워크플로우 자동화 :5678"]
        end

        GRAFANA["📊 Grafana<br/>시각화 대시보드 :3000"]
    end

    BROWSER["👤 사용자 브라우저"]

    BROWSER --> NGINX
    NGINX --> DJANGO
    BINANCE -->|"가격 데이터"| CELERY_W
    CELERY_B -->|"30초 스케줄"| CELERY_W
    CELERY_W -->|"가격 저장"| PG
    CELERY_W -->|"알림 조건 체크"| OLLAMA
    OLLAMA -->|"AI 분석 텍스트"| CELERY_W
    CELERY_W -->|"웹훅"| N8N
    N8N -->|"알림 발송"| EMAIL
    DJANGO <--> PG
    DJANGO <--> REDIS
    CELERY_W <--> REDIS
    PG -->|"시계열 쿼리"| GRAFANA
    GRAFANA -->|"iframe 임베드"| DJANGO
```

---

## 데이터 수집 및 알림 흐름

```mermaid
sequenceDiagram
    participant Beat as Celery Beat
    participant Worker as Celery Worker
    participant Binance as Binance API
    participant DB as PostgreSQL
    participant AI as EXAONE (Ollama)
    participant n8n as n8n
    participant Email as 이메일

    loop 30초마다
        Beat->>Worker: fetch_coin_prices 태스크 발행
        Worker->>Binance: GET /api/v3/ticker/24hr<br/>[BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, SOLUSDT]
        Binance-->>Worker: 현재가·거래량·등락률
        Worker->>DB: CoinPrice 레코드 저장 (5건)
    end

    loop 1분마다
        Beat->>Worker: check_alerts 태스크 발행
        Worker->>DB: 활성 알림 & 최신 가격 조회
        alt 조건 충족 (목표가 이상/이하)
            Worker->>AI: 시장 분석 요청
            AI-->>Worker: 분석 텍스트 반환
            Worker->>DB: AlertLog 저장
            Worker->>n8n: 웹훅 POST
            n8n->>Email: 알림 이메일 발송
        end
    end
```

---

## 핵심 기능

### 실시간 가격 모니터링
- **수집 주기**: 30초
- **대상 코인**: BTC, ETH, BNB, XRP, SOL (Binance USDT 페어)
- **수집 항목**: 현재가·24시간 거래량·등락률·최고/최저가
- **데이터 보관**: 최근 48시간 (자동 정리)

### AI 알림 시스템
- **알림 조건**: 코인별 목표가 이상/이하 설정
- **AI 분석**: 조건 충족 시 EXAONE 3.5 2.4B가 시장 상황 분석
- **알림 전달**: n8n 워크플로우 → Gmail 이메일 발송

### 시각화 대시보드
- **실시간 카드**: 30초 자동 갱신, 가격 상승/하락 애니메이션
- **Grafana 임베드**: iframe으로 상세 시계열 차트 통합
- **시장 요약**: 상승·하락 코인 수, 평균 변동률

---

## 데이터베이스 구조

```mermaid
erDiagram
    Coin {
        int id PK
        varchar symbol "BTCUSDT"
        varchar name "Bitcoin"
        bool is_active
        datetime created_at
    }
    CoinPrice {
        int id PK
        int coin_id FK
        decimal price
        decimal volume_24h
        decimal change_24h
        decimal high_24h
        decimal low_24h
        datetime timestamp
    }
    Alert {
        int id PK
        int coin_id FK
        varchar condition "above / below"
        decimal target_price
        bool is_active
        datetime triggered_at
    }
    AlertLog {
        int id PK
        int alert_id FK
        text message
        text ai_analysis
        decimal triggered_price
        datetime created_at
    }

    Coin ||--o{ CoinPrice : "1:N"
    Coin ||--o{ Alert : "1:N"
    Alert ||--o{ AlertLog : "1:N"
```

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| **백엔드** | Django 4.2, Django REST Framework, Gunicorn |
| **비동기** | Celery 5.3, Celery Beat |
| **데이터베이스** | PostgreSQL 15 |
| **캐시·브로커** | Redis 7 |
| **AI** | Ollama + EXAONE 3.5 2.4B |
| **자동화** | n8n |
| **시각화** | Grafana 10.2 |
| **프록시** | Nginx |
| **컨테이너** | Docker Compose |

---

## 서비스 실행 순서

```mermaid
flowchart LR
    PG["PostgreSQL\n(healthy)"]
    REDIS["Redis\n(healthy)"]
    DJANGO["Django\nmigrate + seed\n(healthy)"]
    CELERY_W["Celery\nWorker"]
    CELERY_B["Celery\nBeat"]
    GRAFANA["Grafana\n(healthy)"]
    GINIT["grafana-init\n공개 대시보드 생성"]
    OLLAMA["Ollama\n(healthy)"]
    OINIT["ollama-init\nEXAONE 모델 pull"]
    N8N["n8n"]
    NGINX["Nginx"]

    PG --> DJANGO
    REDIS --> DJANGO
    DJANGO --> CELERY_W
    DJANGO --> CELERY_B
    GRAFANA --> GINIT
    OLLAMA --> OINIT
    DJANGO --> NGINX
```

---

## 빠른 시작

### 1. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일을 열어 비밀번호와 이메일 설정 입력
```

### 2. 실행
```bash
docker compose up -d
```

### 3. 접속

| 서비스 | URL |
|--------|-----|
| 메인 대시보드 | http://localhost |
| Grafana | http://localhost:3000 |
| n8n | http://localhost:5678 |
| Django Admin | http://localhost/admin |

> 첫 실행 시 Django migrate, 코인 데이터 seed, EXAONE 모델 다운로드가 자동으로 진행됩니다 (5~10분 소요).

---

## 환경 변수 (.env)

```env
# Django
SECRET_KEY=your-django-secret-key
DEBUG=False

# PostgreSQL
POSTGRES_DB=crypto_monitor
POSTGRES_USER=your-db-user
POSTGRES_PASSWORD=your-db-password

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your-grafana-password

# n8n
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your-n8n-password

# 이메일 알림 (Gmail)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# n8n 웹훅 URL (n8n에서 생성 후 입력)
N8N_WEBHOOK_URL=http://n8n:5678/webhook/your-webhook-id
```
