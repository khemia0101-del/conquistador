#!/bin/bash
# deploy.sh — run from Termius
# Usage: ./deploy.sh <droplet-ip>

DROPLET_IP=${1:-"your-droplet-ip"}

ssh conquistador@$DROPLET_IP << 'EOF'
  cd /opt/conquistador
  git pull origin main
  source venv/bin/activate
  pip install -r requirements.txt
  pip install -e .
  alembic upgrade head
  sudo systemctl restart conquistador-web
  sudo systemctl restart conquistador-celery
  sudo systemctl restart conquistador-celerybeat
  echo 'Deploy complete.'
EOF
