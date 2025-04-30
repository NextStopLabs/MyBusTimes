# MyBusTimes Installation & NGINX Setup

## Linux Setup (Debian/Ubuntu)

```bash
sudo apt-get update && sudo apt-get upgrade -y
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt install -y nodejs git python3 python3-venv nginx python3-pip
sudo npm install pm2 -g
```

Clone the repo:

```bash
git clone https://github.com/Kai-codin/MyBusTimes.git
cd MyBusTimes
chmod +x setup.sh run.sh dbupdate.sh
./setup.sh
```

Run with PM2:

```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

---

## Windows Setup

Clone the repo:

```bash
git clone https://github.com/Kai-codin/MyBusTimes.git
cd MyBusTimes
```

Then run:

```bash
setup.bat
run.bat
```

---

## NGINX Configuration

> For windows download the latest version of nginx from here:
> [https://nginx.org/en/download.html](https://nginx.org/en/download.html)

### Edit `nginx.conf`

```bash
sudo nano /etc/nginx/nginx.conf
```

Paste the following:

```nginx
#user  nobody;
worker_processes  1;

events {
    worker_connections  1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  65;

    server {
        listen 80;
        server_name localhost;

        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;
        server_name localhost;

        ssl_certificate /etc/nginx/ssl/nginx-selfsigned.crt;
        ssl_certificate_key /etc/nginx/ssl/nginx-selfsigned.key;
        # On windows change this to wherever you generated your keys

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        location /api/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /admin/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /media/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /static/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            proxy_pass http://127.0.0.1:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        error_page 500 502 503 504 /50x.html;
        location = /50x.html {
            root html;
        }
    }
}
```

---

## Generate Self-Signed SSL Certificate

```bash
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout nginx-selfsigned.key \
  -out nginx-selfsigned.crt \
  -subj "/C=US/ST=State/L=City/O=Org/OU=OrgUnit/CN=localhost"
```

Move certs:

```bash
sudo mkdir -p /etc/nginx/ssl
sudo mv nginx-selfsigned.crt /etc/nginx/ssl/
sudo mv nginx-selfsigned.key /etc/nginx/ssl/
```

---

## Start NGINX

```bash
sudo nginx -t
sudo systemctl start nginx
```

---

## Notes

Make sure to **add your server’s IP** to:

``` bash
nano mybustimesAPI/mybustimesAPI/settings.py
```

Inside the `ALLOWED_HOSTS` list, like:

```python
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.x.x"]
```

### Add a superuser

Linux
```python
source env/bin/activate
python3 mybustimesAPI/manage.py createsuperuser 
```

Windows
```python
env\Scripts\activate
python mybustimesAPI/manage.py createsuperuser 
```
