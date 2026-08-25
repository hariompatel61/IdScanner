# 🚀 Linux VPS Backend Hosting Guide with NGINX & SSL

Yeh complete step-by-step guide hai **IDScanner Backend (FastAPI + RapidOCR)** ko Linux VPS (Ubuntu 22.04 / 24.04 LTS) par **NGINX Reverse Proxy, Systemd Service, aur Free SSL (Certbot)** ke saath production me live host karne ke liye.

---

## 📋 1. System Requirements & Prerequisites

- **Server OS**: Ubuntu 22.04 LTS ya Ubuntu 24.04 LTS
- **Server Specs**:
  - Minimum: 2 Core CPU, 4 GB RAM
  - Recommended (High Traffic / 500+ scans/min): 4+ Core CPU, 8 GB RAM
- **Domain Name**: Domain ka `A` record aapke Linux Server ke Public IP par point hona chahiye (Jaise: `api.yourdomain.com` $\rightarrow$ `123.45.67.89`).

---

## 🛠️ 2. Step 1: Server Update & System Dependencies Install Karein

Apne Linux VPS me SSH se login karein (`ssh root@<YOUR_SERVER_IP>`) aur yeh commands run karein:

```bash
# 1. System packages update karein
sudo apt update && sudo apt upgrade -y

# 2. Python 3, venv, pip, Git, NGINX, Certbot aur OpenCV libraries install karein
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx libgl1 libglib2.0-0 build-essential
```

---

## 📂 3. Step 2: Code Deploy & Python Virtual Environment Setup

Code ko `/var/www/idscanner` directory me setup karein:

```bash
# 1. Directory banayein aur permissions set karein
sudo mkdir -p /var/www/idscanner
sudo chown -R $USER:$USER /var/www/idscanner

# 2. Repository clone karein
cd /var/www/idscanner
git clone https://github.com/hariompatel61/IdScanner.git .

# 3. Backend folder me jayein
cd backend

# 4. Isolated Python Virtual Environment create karein
python3 -m venv venv
source venv/bin/activate

# 5. Dependencies install karein
pip install --upgrade pip
pip install -r requirements.txt
```

---

## ⚙️ 4. Step 3: Production `.env` File Configure Karein

Backend folder (`/var/www/idscanner/backend`) ke andar `.env` file banayein:

```bash
nano .env
```

Neeche diye gaye settings paste karein (Apna domain name update karein):

```ini
APP_ENV=production
LOG_LEVEL=INFO

# Aapke Frontend domain aur localhost ko allow karein (CORS)
CORS_ORIGINS=["http://localhost:3233", "https://yourfrontenddomain.com", "https://api.yourdomain.com"]

# Image limits
MAX_IMAGE_SIZE_MB=10
MAX_IMAGE_DIMENSION=1920

# OCR Worker threads
OCR_DEVICE=cpu
OCR_WORKERS=4

# Thresholds
HIGH_CONFIDENCE_THRESHOLD=0.85
RETRY_THRESHOLD=0.70

# Server Binding (Localhost internal port 8000)
API_HOST=127.0.0.1
API_PORT=8000
API_TIMEOUT_SECONDS=30
```

`Ctrl + O` fir `Enter` dabayein save karne ke liye, aur `Ctrl + X` dabayein exit karne ke liye.

---

## 🔄 5. Step 4: Systemd Background Service Banayein (Auto-Restart on Crash)

Yeh service ensure karegi ki aapka backend background me 24/7 run kare aur server reboot hone par automatically start ho jaye.

```bash
sudo nano /etc/systemd/system/idscanner.service
```

Neeche diya gaya configuration paste karein:

```ini
[Unit]
Description=IDScanner FastAPI High-Performance Backend Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/idscanner/backend
Environment="PATH=/var/www/idscanner/backend/venv/bin"
EnvironmentFile=/var/www/idscanner/backend/.env

# 4 Worker processes ke saath Uvicorn start karein
ExecStart=/var/www/idscanner/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips='*'

# Auto-restart settings
Restart=always
RestartSec=3
KillSignal=SIGQUIT
Type=notify
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Permissions aur Service start karein:

```bash
# Permissions www-data user ko dein
sudo chown -R www-data:www-data /var/www/idscanner

# Systemd reload karein aur service enable karein
sudo systemctl daemon-reload
sudo systemctl enable idscanner
sudo systemctl start idscanner

# Status check karein (Active: running aana chahiye)
sudo systemctl status idscanner
```

---

## 🌐 6. Step 5: NGINX Reverse Proxy Configure Karein

NGINX incoming HTTPS requests (Port 443) ko backend (Port 8000) par securely route karega.

```bash
sudo nano /etc/nginx/sites-available/idscanner
```

Neeche diya gaya configuration paste karein (Apna actual domain `server_name` me daalein):

```nginx
server {
    listen 80;
    server_name api.yourdomain.com; # <-- Apna domain / subdomain yahan daalein

    # Mobile high-res camera uploads allow karne ke liye (Max 15MB)
    client_max_body_size 15M;

    # Timeouts for heavy OCR image processing
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        
        # Real Client IP forward karein
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static assets / logs direct access block karein
    location ~ /\. {
        deny all;
    }
}
```

Site enable karein aur NGINX reload karein:

```bash
# Site enable link banayein
sudo ln -s /etc/nginx/sites-available/idscanner /etc/nginx/sites-enabled/

# NGINX syntax check karein
sudo nginx -t

# NGINX restart karein
sudo systemctl restart nginx
```

---

## 🔒 7. Step 6: Free SSL Certificate Setup (HTTPS via Let's Encrypt)

Certbot use karke 1 minute me automatic free SSL activate karein:

```bash
sudo certbot --nginx -d api.yourdomain.com
```

- Email maangne par apna email daalein.
- Terms accept karein (`Y`).
- HTTPS automatic redirect select karein.
- Certbot automatically NGINX config ko HTTPS ke saath update kar dega!

SSL Auto-renewal check karein:
```bash
sudo certbot renew --dry-run
```

---

## 🛡️ 8. Step 7: Linux Firewall (UFW) Security Setup

Server par unauthorized ports block karein aur sirf SSH, HTTP, HTTPS allow karein:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

Status check karein:
```bash
sudo ufw status
```

---

## ✅ 9. Step 8: Live API Test Karein

Aapka backend live ho chuka hai! Ab test karein:

### 1. Health Check Test
```bash
curl https://api.yourdomain.com/health
# Response: {"status":"healthy"}
```

### 2. Readiness Check (RapidOCR Pre-warmed)
```bash
curl https://api.yourdomain.com/ready
# Response: {"status":"ready","ocr_engine":"rapidocr"}
```

### 3. Live Document Scan Test (cURL)
```bash
curl -X POST "https://api.yourdomain.com/api/v1/scan" \
  -F "image=@/path/to/sample_aadhaar.jpeg"
```

---

## 🧰 10. Useful Maintenance Commands Cheat Sheet

| Task | Command |
|---|---|
| **Backend status check** | `sudo systemctl status idscanner` |
| **Backend restart karna** | `sudo systemctl restart idscanner` |
| **Backend stop karna** | `sudo systemctl stop idscanner` |
| **Realtime Live logs dekhna** | `sudo journalctl -u idscanner -f` |
| **NGINX restart karna** | `sudo systemctl restart nginx` |
| **NGINX error logs dekhna** | `sudo tail -f /var/log/nginx/error.log` |
| **Code update karna (Git Pull)** | `cd /var/www/idscanner && git pull && sudo systemctl restart idscanner` |

---

## 🚀 Ho Gaya!
Aapka high-performance IDScanner backend ab Linux VPS par NGINX aur SSL ke saath 100% production-ready live chal raha hai!
