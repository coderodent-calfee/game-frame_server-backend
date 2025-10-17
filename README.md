 npm install --global yarn
 # 🔒 HTTPS Setup for Django + Daphne with Caddy

This guide shows how to go from **plain HTTP → HTTPS** in local development, with a setup that also works in production (Google Cloud, AWS, Azure, etc.).

We’ll use:

- [**Caddy**](https://caddyserver.com/) → reverse proxy + HTTPS server  
- [**mkcert**](https://github.com/FiloSottile/mkcert) → local trusted certificates  

---

## 📋 Overview

[ Client (Browser / Android / LAN) ]
|
HTTPS 🔒
|
(Caddy Proxy)
|
HTTP
|
Daphne (ASGI)
|
Django Backend


- **Dev (local/LAN/Android):** mkcert generates trusted certs.  
- **Prod (cloud):** swap mkcert for Let’s Encrypt (Caddy handles it automatically).  

---

## 1. Install Prerequisites

### mkcert
Install mkcert:

**Linux (Debian/Ubuntu):**

sudo apt install libnss3-tools

**macOS (Homebrew):**

brew install mkcert nss


**Windows (Chocolatey):**

choco install mkcert


*Initialize mkcert:*

mkcert -install


This creates a local Certificate Authority (CA) and adds it to your system/browser trust store.

Caddy

Install Caddy:

Linux (Debian/Ubuntu):

sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo tee /etc/apt/trusted.gpg.d/caddy-stable.asc
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy


macOS (Homebrew):

brew install caddy


Windows (Chocolatey):

choco install caddy

2. Generate a Certificate for Your LAN IP

Find your local IP (example: 192.168.0.249), then run:

mkcert 192.168.0.249


This generates:

192.168.0.249.pem (certificate)

192.168.0.249-key.pem (private key)

3. Configure Caddy

Create a file named Caddyfile in your project root:

https://192.168.0.249 {
    tls ./192.168.0.249.pem ./192.168.0.249-key.pem
    reverse_proxy 127.0.0.1:8000
}


Explanation:

https://192.168.0.249 → Public HTTPS endpoint

tls ... → Use mkcert-generated certificate

reverse_proxy → Forwards requests to Daphne running on port 8000

4. Run the Backend

Start Daphne normally:

daphne -p 8000 server_backend.asgi:application

5. Run Caddy

In the directory with your Caddyfile:

caddy run


Your API is now available at:

https://192.168.0.249

6. Test on Local Machine

Open in a browser:

https://192.168.0.249/api/accounts/


You should see a secure 🔒 lock icon.
If you get a warning, confirm you ran mkcert -install.

7. Test on Other LAN Computers

On another computer:

Copy the mkcert root CA:

Linux: ~/.local/share/mkcert/rootCA.pem

macOS: ~/Library/Application Support/mkcert

Windows: %LOCALAPPDATA%\mkcert

Install it into that machine’s trust store (double-click on macOS/Windows, or import manually on Linux).

Now that computer will trust your local HTTPS cert.

8. Test on Android (Emulator or USB Device)

Push the root CA to the device:

adb push "$(mkcert -CAROOT)/rootCA.pem" /sdcard/


On the Android device/emulator:

Go to Settings → Security → Encryption & credentials → Install a certificate → CA certificate

Select rootCA.pem from /sdcard

Confirm install

Now Android trusts your HTTPS certs.
You can use Chrome or your React Native app to hit:

https://192.168.0.249

9. Cloud Deployment (Later)

When you deploy to Google/Azure/AWS:

Install Caddy on your server

Update your Caddyfile with your domain:

https://mygameapi.example.com {
    reverse_proxy 127.0.0.1:8000
}


Do not specify tls ... → Caddy will automatically fetch and renew free Let’s Encrypt certificates.

Your API will then be available globally with trusted HTTPS.

✅ Summary

Local Dev (LAN, Android):
mkcert + Caddy = trusted HTTPS everywhere

Production (Cloud):
Let’s Encrypt + Caddy = automatic free HTTPS

Same architecture, no major code changes:

Client → HTTPS (Caddy) → HTTP (Daphne) → Django

