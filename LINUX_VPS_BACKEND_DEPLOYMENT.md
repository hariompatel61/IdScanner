# Linux VPS Production Hosting Guide (Backend API Only)

This guide provides step-by-step instructions for hosting the **FastAPI + RapidOCR Backend API** on a standalone Linux VPS (Ubuntu 22.04 / 24.04 LTS) for production integration with RIMS Hospital.

---

## 1. System Requirements & Environment
- **OS**: Ubuntu 22.04 / 24.04 LTS (x86_64)
- **RAM**: Minimum 4 GB RAM (8 GB recommended for 500+ scans/min)
- **CPU**: 2+ Cores
- **Ports**: 80 (HTTP), 443 (HTTPS), 4500 (Local Uvicorn Backend)

---

## 2. Step 1: Install System Packages
Log in to your Linux VPS via SSH (`ssh root@<VPS_IP>`) and update system packages:

```bash
# Update Ubuntu package repository
sudo apt update && sudo apt upgrade -y

# Install Python 3, venv, Git, NGINX, and Certbot (SSL)
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx
```

---

## 3. Step 2: Clone Repository & Setup Virtual Environment
```bash
# Navigate to deployment directory
cd /root

# Clone the repository
git clone https://github.com/hariompatel61/IdScanner.git
cd IdScanner/backend

# Create & activate Python Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install pinned backend requirements
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Step 3: Create Systemd Service for 24/7 Background Running
To ensure the backend runs continuously and auto-restarts on system reboot, create a Systemd service file:

```bash
sudo nano /etc/systemd/system/idscanner-backend.service
```

Paste the following service definition:

```ini
[Unit]
Description=ID Scanner FastAPI Backend Service
After=network.target

[Service]
User=root
WorkingDirectory=/root/IdScanner/backend
ExecStart=/root/IdScanner/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 4500 --workers 4
Restart=always
RestartSec=5
Environment=APP_ENV=production
Environment=MAX_IMAGE_DIMENSION=960

[Install]
WantedBy=multi-user.target
```

*Save and close: `Ctrl + O` $\rightarrow$ `Enter` $\rightarrow$ `Ctrl + X`.*

### Enable and Start Service
```bash
# Reload Systemd daemon
sudo systemctl daemon-reload

# Enable auto-start on boot & start service now
sudo systemctl enable --now idscanner-backend

# Check service status
sudo systemctl status idscanner-backend
```

---

## 5. Step 4: Configure NGINX Reverse Proxy & Free SSL Certificate (HTTPS)

### 5.1 NGINX Site Configuration
Create an NGINX site configuration file:

```bash
sudo nano /etc/nginx/sites-available/idscanner-backend
```

Paste the following NGINX reverse proxy block:

```nginx
server {
    server_name api.yourdomain.com; # Replace with your actual domain or subdomain

    location / {
        proxy_pass http://127.0.0.1:4500;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase maximum upload limit for high-res images
        client_max_body_size 10M;
        proxy_read_timeout 30s;
        proxy_connect_timeout 30s;
    }
}
```

### 5.2 Activate NGINX Site & SSL Certificate
```bash
# Enable NGINX configuration
sudo ln -s /etc/nginx/sites-available/idscanner-backend /etc/nginx/sites-enabled/

# Test NGINX configuration syntax
sudo nginx -t

# Reload NGINX
sudo systemctl reload nginx

# Issue free Let's Encrypt HTTPS SSL Certificate
sudo certbot --nginx -d api.yourdomain.com
```

---

## 6. Step 5: Verification & Testing

### Test Liveness Endpoint
```bash
curl https://api.yourdomain.com/health
# Expected Output: {"status":"healthy"}
```

### Test Readiness Endpoint
```bash
curl https://api.yourdomain.com/ready
# Expected Output: {"status":"ready","ocr_engine":"rapidocr"}
```

### Test Scan API Endpoint
```bash
curl -X POST "https://api.yourdomain.com/api/v1/scan" \
  -F "image=@/path/to/sample_id.jpg" \
  -F "document_type=pan"
```

---

## 7. Useful Management Commands

| Action | Command |
|---|---|
| **View Live Backend Logs** | `sudo journalctl -u idscanner-backend -f` |
| **Restart Backend Service** | `sudo systemctl restart idscanner-backend` |
| **Stop Backend Service** | `sudo systemctl stop idscanner-backend` |
| **Check NGINX Status** | `sudo systemctl status nginx` |
