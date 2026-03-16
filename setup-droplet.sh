#!/bin/bash
set -euo pipefail

########################################################################
# Conquistador Oil — DigitalOcean Droplet Setup Script
# Run as root on a fresh Ubuntu 22.04/24.04 droplet:
#   curl -sSL <raw-url> | bash
#   — or —
#   scp setup-droplet.sh root@<IP>:~ && ssh root@<IP> bash setup-droplet.sh
#
# BEFORE RUNNING: Fill in the variables in the section below.
########################################################################

# =====================================================================
# >>>  FILL THESE IN BEFORE RUNNING  <<<
# =====================================================================
DB_PASSWORD="010120QueenConquistador"             # PostgreSQL password
SECRET_KEY="$(openssl rand -hex 32)"            # Auto-generated JWT secret
DOMAIN="conquistadoroil.com"                    # Your domain (or droplet IP)

# AI
AI_PROVIDER="nvidia"
AI_MODEL="moonshotai/kimi-k2.5"
NVIDIA_API_KEY="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"  # Get from build.nvidia.com

# Email (Zoho Mail)
EMAIL_HOST="smtp.zoho.com"
EMAIL_PORT="465"
EMAIL_USER="info@conquistadoroil.com"            # e.g. leads@conquistadoroil.com
EMAIL_PASS="010120Meyer@"                        # Zoho app password
EMAIL_FROM="Conquistador Oil <leads@conquistadoroil.com>"

# Telegram
TELEGRAM_BOT_TOKEN="8777210697:AAGxMps-wlhP3StSr481vE_m4dUlQU5av_"
ADMIN_TELEGRAM_CHAT_ID="7009194853"              # Get from @userinfobot

# =====================================================================
# >>>  END OF USER CONFIG — everything below is automatic  <<<
# =====================================================================

APP_DIR="/opt/conquistador"
APP_USER="conquistador"
REPO_URL="https://github.com/khemia0101-del/conquistador.git"

echo "============================================"
echo "  Conquistador Oil — Server Setup"
echo "============================================"

# -------------------------------------------------------------------
# 1. System packages
# -------------------------------------------------------------------
echo "[1/10] Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
  python3 python3-pip python3-venv \
  postgresql postgresql-contrib \
  redis-server \
  nginx certbot python3-certbot-nginx \
  nodejs npm \
  git curl ufw

# -------------------------------------------------------------------
# 2. Firewall
# -------------------------------------------------------------------
echo "[2/10] Configuring firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# -------------------------------------------------------------------
# 3. Create app user
# -------------------------------------------------------------------
echo "[3/10] Creating app user..."
if ! id "$APP_USER" &>/dev/null; then
  useradd -r -m -s /bin/bash "$APP_USER"
fi

# -------------------------------------------------------------------
# 4. PostgreSQL
# -------------------------------------------------------------------
echo "[4/10] Setting up PostgreSQL..."

# Configure PostgreSQL to use md5 password authentication for local connections
PG_HBA=$(sudo -u postgres psql -tc "SHOW hba_file;" | xargs)
if grep -q "local.*all.*all.*peer" "$PG_HBA"; then
  sed -i 's/^local\s\+all\s\+all\s\+peer/local   all             all                                     md5/' "$PG_HBA"
  systemctl restart postgresql
  echo "  → Switched PostgreSQL local auth from peer to md5"
fi

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='conquistador'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER conquistador WITH PASSWORD '${DB_PASSWORD}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='conquistador'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE conquistador OWNER conquistador;"

# -------------------------------------------------------------------
# 5. Clone repo & set up Python env
# -------------------------------------------------------------------
echo "[5/10] Cloning repository..."
git config --global --add safe.directory "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  cd "$APP_DIR" && git pull origin main
fi
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

echo "[5/10] Setting up Python virtual environment..."
sudo -u "$APP_USER" bash -c "
  cd $APP_DIR
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  pip install -e .
"

# -------------------------------------------------------------------
# 6. Build frontend (Tailwind CSS)
# -------------------------------------------------------------------
echo "[6/10] Building frontend assets..."
cd "$APP_DIR"
sudo -u "$APP_USER" bash -c "
  cd $APP_DIR
  npm install
  npm run build
"

# -------------------------------------------------------------------
# 7. Environment file
# -------------------------------------------------------------------
echo "[7/10] Writing .env file..."
cat > "$APP_DIR/.env" << ENVEOF
# Database
DATABASE_URL=postgresql+asyncpg://conquistador:${DB_PASSWORD}@localhost:5432/conquistador
DATABASE_URL_SYNC=postgresql://conquistador:${DB_PASSWORD}@localhost:5432/conquistador
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=${SECRET_KEY}

# AI
AI_PROVIDER=${AI_PROVIDER}
AI_MODEL=${AI_MODEL}
NVIDIA_API_KEY=${NVIDIA_API_KEY}

# Email (Zoho SMTP)
EMAIL_HOST=${EMAIL_HOST}
EMAIL_PORT=${EMAIL_PORT}
EMAIL_USER=${EMAIL_USER}
EMAIL_PASS=${EMAIL_PASS}
EMAIL_FROM=${EMAIL_FROM}

# Telegram
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
ADMIN_TELEGRAM_CHAT_ID=${ADMIN_TELEGRAM_CHAT_ID}

# Business
BUSINESS_PHONE=717-397-9800
BUSINESS_ADDRESS=931 N Shippen St, Lancaster, PA 17602
BUSINESS_NAME=Conquistador Oil, Heating & Air Conditioning Inc.
ENVEOF
chown "$APP_USER":"$APP_USER" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

# -------------------------------------------------------------------
# 8. Run database migrations
# -------------------------------------------------------------------
echo "[8/10] Running database migrations..."
sudo -u "$APP_USER" bash -c "
  cd $APP_DIR
  source venv/bin/activate
  alembic upgrade head
"

# -------------------------------------------------------------------
# 9. Systemd services
# -------------------------------------------------------------------
echo "[9/10] Creating systemd services..."

# --- Web (FastAPI + Uvicorn) ---
cat > /etc/systemd/system/conquistador-web.service << 'SVCEOF'
[Unit]
Description=Conquistador Web (FastAPI)
After=network.target postgresql.service redis-server.service

[Service]
User=conquistador
Group=conquistador
WorkingDirectory=/opt/conquistador
Environment=PATH=/opt/conquistador/venv/bin:/usr/bin
ExecStart=/opt/conquistador/venv/bin/uvicorn conquistador.web.app:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

# --- Celery Worker ---
cat > /etc/systemd/system/conquistador-celery.service << 'SVCEOF'
[Unit]
Description=Conquistador Celery Worker
After=network.target redis-server.service

[Service]
User=conquistador
Group=conquistador
WorkingDirectory=/opt/conquistador
Environment=PATH=/opt/conquistador/venv/bin:/usr/bin
ExecStart=/opt/conquistador/venv/bin/celery -A conquistador.tasks worker -l info --concurrency=2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

# --- Celery Beat (Scheduler) ---
cat > /etc/systemd/system/conquistador-celerybeat.service << 'SVCEOF'
[Unit]
Description=Conquistador Celery Beat
After=network.target redis-server.service

[Service]
User=conquistador
Group=conquistador
WorkingDirectory=/opt/conquistador
Environment=PATH=/opt/conquistador/venv/bin:/usr/bin
ExecStart=/opt/conquistador/venv/bin/celery -A conquistador.tasks beat -l info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable conquistador-web conquistador-celery conquistador-celerybeat
systemctl start conquistador-web conquistador-celery conquistador-celerybeat

# -------------------------------------------------------------------
# 10. Nginx reverse proxy + SSL
# -------------------------------------------------------------------
echo "[10/10] Configuring Nginx..."

cat > /etc/nginx/sites-available/conquistador << NGINXEOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # WebSocket support for chatbot
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 86400;
    }

    # Static files
    location /static/ {
        alias /opt/conquistador/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/conquistador /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "============================================"
echo "  SETUP COMPLETE!"
echo "============================================"
echo ""
echo "Services running:"
echo "  - Web:         http://${DOMAIN}"
echo "  - Celery:      background worker"
echo "  - Celery Beat: scheduled tasks"
echo ""
echo "Next steps:"
echo "  1. Point your domain DNS (A record) to this droplet's IP"
echo "  2. Run: certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
echo "     (this adds free HTTPS via Let's Encrypt)"
echo "  3. Test: curl http://localhost:8000/health"
echo ""
echo "Manage services:"
echo "  systemctl status conquistador-web"
echo "  systemctl restart conquistador-web"
echo "  journalctl -u conquistador-web -f   # live logs"
echo ""
echo "Redeploy after code changes:"
echo "  cd /opt/conquistador && git pull origin main"
echo "  source venv/bin/activate && pip install -r requirements.txt"
echo "  alembic upgrade head"
echo "  systemctl restart conquistador-web conquistador-celery conquistador-celerybeat"
echo "============================================"
