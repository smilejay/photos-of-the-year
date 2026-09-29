#!/bin/bash
# Deployment script for Photos of the Year

set -e

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
echo "Project directory: $PROJECT_DIR"

echo "=== Step 1: Create Python virtual environment ==="
cd "$PROJECT_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "=== Step 2: Install frontend dependencies ==="
cd "$PROJECT_DIR/frontend"
npm install

echo "=== Step 3: Build frontend ==="
VITE_BASE_PATH="${VITE_BASE_PATH:-/}" npm run build

echo "=== Step 4: Create uploads directory ==="
mkdir -p "$PROJECT_DIR/backend/uploads"
chmod 755 "$PROJECT_DIR/backend/uploads"

echo "=== Step 5: Initialize database ==="
cd "$PROJECT_DIR/deploy"
python3 init_db.py

echo "=== Step 6: Done ==="
echo ""
echo "Next steps:"
echo "1. Make sure MySQL is running and create database 'photos_of_the_year'"
echo "   mysql -u root -p -e 'CREATE DATABASE IF NOT EXISTS photos_of_the_year CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'"
echo ""
echo "2. Start gunicorn:"
echo "   cd $PROJECT_DIR/backend && gunicorn --bind 127.0.0.1:8000 wsgi:application"
echo ""
echo "3. Install the Nginx location snippet and include it in the HTTPS server block:"
echo "   sudo mkdir -p /etc/nginx/snippets"
echo "   sudo cp $PROJECT_DIR/deploy/nginx/photos-of-the-year.locations.conf /etc/nginx/snippets/photos-of-the-year.conf"
echo "   sudo nginx -t && sudo systemctl reload nginx"
