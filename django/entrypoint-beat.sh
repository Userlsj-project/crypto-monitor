#!/bin/sh
set -e

echo "=== Celery Beat 시작 ==="
exec celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
