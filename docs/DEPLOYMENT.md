# Production Deployment & Operations Guide

## 1. Quick Start: Docker Compose (Recommended)

The easiest way to run IDScanner in production is via `docker-compose`.

### Prerequisites
- Docker Engine $\ge 24.0$
- Docker Compose $\ge 2.20$

### Steps
1. Clone the repository:
   ```bash
   git clone <REPO_URL>
   cd IDScanner
   ```
2. Configure environment:
   ```bash
   cp .env.example .env
   ```
3. Start the application stack:
   ```bash
   docker-compose up -d --build
   ```
4. Verify health status:
   ```bash
   curl http://localhost:4500/ready
   # Expected response: {"status":"ready","ocr_engine":"rapidocr"}
   ```

---

## 2. Linux VPS / Standalone Host Deployment

For hosting on a cloud VPS (Ubuntu 22.04 / 24.04 LTS):

### 2.1 Install System Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx libgl1 libglib2.0-0
```

### 2.2 Setup Backend Service
```bash
cd /opt
git clone <REPO_URL> IDScanner
cd IDScanner/backend

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.3 Systemd Service Setup (`/etc/systemd/system/idscanner.service`)
```ini
[Unit]
Description=IDScanner High-Throughput API Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/IDScanner/backend
Environment="PATH=/opt/IDScanner/backend/venv/bin"
ExecStart=/opt/IDScanner/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now idscanner
```

---

## 3. NGINX Reverse Proxy & SSL Configuration

```nginx
server {
    server_name api.yourdomain.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Obtain Let's Encrypt SSL:
```bash
sudo certbot --nginx -d api.yourdomain.com
```

---

## 4. Horizontal Scaling for 500+ Scans/Minute

To support 500+ concurrent scans/min, scale the API replicas behind Docker Compose or a load balancer:

```bash
docker-compose up -d --scale scanner-api=4
```
