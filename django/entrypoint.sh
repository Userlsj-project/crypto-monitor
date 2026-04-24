#!/bin/sh
set -e

echo "=== Django 초기화 시작 ==="

echo "[1/4] 데이터베이스 마이그레이션..."
python manage.py makemigrations coins alerts --noinput
python manage.py migrate --noinput

echo "[2/4] 정적 파일 수집..."
python manage.py collectstatic --noinput

echo "[3/4] 초기 코인 데이터 삽입..."
python manage.py seed_coins

echo "[4/4] Gunicorn 서버 시작..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile -
