#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source venv/bin/activate

pip install -q -r requirements.txt

# 首次启动：若尚无 Admin 账号则自动初始化（非注册流程）
python manage.py init_admin 2>/dev/null || true
python manage.py migrate --noinput

PORT="${RUNSERVER_PORT:-9000}"
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
echo "ShareMint 运行于 http://127.0.0.1:${PORT}"
if [ -n "$LAN_IP" ]; then
  echo "手机同一 Wi-Fi 可访问: http://${LAN_IP}:${PORT}/auth/login/"
fi
python manage.py runserver "0.0.0.0:${PORT}"
