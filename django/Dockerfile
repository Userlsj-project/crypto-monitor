FROM python:3.11-slim

# 환경 변수 설정 (Python 최적화)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (psycopg2 빌드용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 먼저 설치 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 정적 파일 디렉토리 생성 + entrypoint 실행 권한
RUN mkdir -p /app/staticfiles /app/media && \
    chmod +x /app/entrypoint.sh /app/entrypoint-beat.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
