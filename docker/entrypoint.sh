#!/bin/sh
set -e

cd /app

# 尝试修复权限
echo "DEBUG: Attempting to fix database permissions..."
chmod 666 db.sqlite3 2>/dev/null || true
chmod 777 . 2>/dev/null || true

python manage.py migrate --noinput
# 如果数据库被占用，init_admin 可能会报错，这里加个容错
python manage.py init_admin 2>/dev/null || echo "INFO: init_admin skipped or failed"
python manage.py collectstatic --noinput

exec gunicorn core.wsgi:application \
  --bind "0.0.0.0:${RUNSERVER_PORT:-9000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout 120
