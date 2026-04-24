"""
Django 설정 파일 - crypto_monitor 프로젝트
환경 변수는 python-decouple로 관리 (.env 파일)
"""
import os
from pathlib import Path
from decouple import config, Csv

# ─────────────────────────────────────────
# 기본 경로 설정
# ─────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────
# 보안 설정
# ─────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production-12345')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0', cast=Csv())

# ─────────────────────────────────────────
# 설치된 앱
# ─────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 서드파티 앱
    'rest_framework',
    'corsheaders',
    'django_filters',
    'django_celery_beat',
    'django_celery_results',

    # 로컬 앱
    'apps.coins',
    'apps.alerts',
]

# ─────────────────────────────────────────
# 미들웨어
# ─────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS는 CommonMiddleware 앞에 위치
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ─────────────────────────────────────────
# 템플릿 설정
# ─────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ─────────────────────────────────────────
# PostgreSQL 데이터베이스 설정
# ─────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='crypto_monitor'),
        'USER': config('POSTGRES_USER', default='crypto_user'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='crypto_password'),
        'HOST': config('POSTGRES_HOST', default='postgres'),
        'PORT': config('POSTGRES_PORT', default='5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
        'CONN_MAX_AGE': 60,  # 커넥션 재사용 (초)
    }
}

# ─────────────────────────────────────────
# Redis 캐시 설정
# ─────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 300,  # 5분 기본 캐시 만료
    }
}

# ─────────────────────────────────────────
# Celery 설정
# ─────────────────────────────────────────
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://redis:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 태스크 최대 실행 시간 (초)
CELERY_TASK_SOFT_TIME_LIMIT = 270
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # 공정한 태스크 분배

# Celery Beat 주기 스케줄 (DatabaseScheduler 사용)
CELERY_BEAT_SCHEDULE = {
    # 30초마다 Binance에서 코인 가격 수집
    'fetch-coin-prices-every-30s': {
        'task': 'apps.coins.tasks.fetch_coin_prices',
        'schedule': 30.0,
        'options': {'queue': 'coins'},
    },
    # 1분마다 알림 조건 체크
    'check-alerts-every-minute': {
        'task': 'apps.alerts.tasks.check_alerts',
        'schedule': 60.0,
        'options': {'queue': 'alerts'},
    },
}

# Celery 큐 정의
CELERY_TASK_ROUTES = {
    'apps.coins.tasks.*': {'queue': 'coins'},
    'apps.alerts.tasks.*': {'queue': 'alerts'},
}

# ─────────────────────────────────────────
# Django REST Framework 설정
# ─────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S',
}

# ─────────────────────────────────────────
# CORS 설정
# ─────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = DEBUG  # 개발 환경에서는 모든 도메인 허용
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',   # Grafana
    'http://localhost:5678',   # n8n
    'http://localhost:8000',   # Django 자체
    'http://127.0.0.1:8000',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']

# Grafana iframe 임베드 허용
X_FRAME_OPTIONS = 'SAMEORIGIN'

# ─────────────────────────────────────────
# Ollama / EXAONE AI 설정
# ─────────────────────────────────────────
OLLAMA_BASE_URL = config('OLLAMA_BASE_URL', default='http://ollama:11434')
OLLAMA_MODEL = config('OLLAMA_MODEL', default='exaone3.5:2.4b')
OLLAMA_TIMEOUT = config('OLLAMA_TIMEOUT', default=30, cast=int)

# ─────────────────────────────────────────
# n8n 웹훅 설정
# ─────────────────────────────────────────
N8N_WEBHOOK_URL = config('N8N_WEBHOOK_URL', default='http://n8n:5678/webhook/crypto-alert')

# ─────────────────────────────────────────
# Binance API 설정
# ─────────────────────────────────────────
BINANCE_API_BASE_URL = config('BINANCE_API_BASE_URL', default='https://api.binance.com')

# 수집 대상 코인 (USDT 페어)
MONITORED_COINS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'SOLUSDT']

# ─────────────────────────────────────────
# 비밀번호 유효성 검사
# ─────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─────────────────────────────────────────
# 국제화 설정
# ─────────────────────────────────────────
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# ─────────────────────────────────────────
# 정적 파일 설정
# ─────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─────────────────────────────────────────
# 기본 PK 타입
# ─────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─────────────────────────────────────────
# 로깅 설정
# ─────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps.coins': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'apps.alerts': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
