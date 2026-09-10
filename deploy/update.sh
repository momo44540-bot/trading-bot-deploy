#!/bin/bash
set -e

cd ~/tbot
git pull
cp -r backend/app/. /opt/trading-bot/app/
chown -R tradingbot:tradingbot /opt/trading-bot/app
systemctl restart trading-bot
sleep 2
systemctl status trading-bot --no-pager -l | head -10
echo "==> Update deployed"
