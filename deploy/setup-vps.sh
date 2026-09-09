#!/bin/bash
set -e

APP_DIR=/opt/trading-bot

echo "==> Updating system and installing dependencies"
apt-get update -y
apt-get install -y python3-venv python3-pip ufw

echo "==> Creating service user"
id -u tradingbot &>/dev/null || useradd -r -s /usr/sbin/nologin -d "$APP_DIR" tradingbot

echo "==> Setting up Python virtual environment"
cd "$APP_DIR"
python3 -m venv venv
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q

echo "==> Setting permissions"
chown -R tradingbot:tradingbot "$APP_DIR"
chmod 600 "$APP_DIR/.env"

echo "==> Installing systemd service"
cat > /etc/systemd/system/trading-bot.service <<'EOF'
[Unit]
Description=Trading Platform Backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=tradingbot
WorkingDirectory=/opt/trading-bot
ExecStart=/opt/trading-bot/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable trading-bot
systemctl restart trading-bot

echo "==> Configuring firewall"
ufw allow OpenSSH
ufw allow 8000/tcp
ufw --force enable

sleep 2
echo "==> Service status"
systemctl status trading-bot --no-pager -l | head -15

echo "==> Done. Backend should be reachable at http://<server-ip>:8000"
