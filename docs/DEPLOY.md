# Интернэтэд байршуулах — Oracle Cloud Always Free (Option A)

Локал систем яг хэвээрээ нэг үнэгүй сервер дээр Docker-оор ажиллана:

```
Интернэт ──443──► Caddy (автомат HTTPS)
                    ├─ eb.<IP>.sslip.io   → web (нүүр хуудас, админ, чатбот)
                    └─ n8n.<IP>.sslip.io  → n8n editor (webhook-ууд гаднаас хаалттай)
                  web ─► n8n ─► Gemini API
                   └──► Postgres (гаднаас хаалттай)      n8n ─► Gmail SMTP (жинхэнэ и-мэйл)
```

| Хэсэг | Хаана | Үнэ |
|---|---|---|
| Сервер | Oracle Cloud Always Free — Ampere A1 (ARM), 2 OCPU / 12 GB | үнэгүй (бүртгэлд карт баталгаажуулалт) |
| HTTPS, домэйн | Caddy + `sslip.io` (IP-гээс автомат домэйн) | үнэгүй |
| Docker image | GitHub Actions → `ghcr.io` | үнэгүй |
| И-мэйл | Gmail SMTP + App Password (~500/өдөр) | үнэгүй |
| AI | Gemini API үнэгүй түвшин | үнэгүй |

---

## 0. GitHub руу түлхэх
```bash
git push -u origin main
```
`.github/workflows/docker.yml` автоматаар ажиллаж `ghcr.io/<owner>/energy-balance-web:latest` image үүсгэнэ (GitHub → Actions таб, ~5 мин).
Дараа нь GitHub → профайл → **Packages** → `energy-balance-web` → *Package settings* → **Change visibility → Public** (сервер нэвтрэлгүйгээр татна; image-д нууц утга байхгүй).

## 1. Gmail App Password
1. Систем илгээх Gmail хаягаар нэвтэрнэ (компанийн жинхэнэ хаяг биш, тусдаа хаяг зөвлөнө).
2. myaccount.google.com → **Security** → **2-Step Verification** асаана.
3. myaccount.google.com/apppasswords → нэр: `energy-balance` → 16 үсэгтэй нууц үг гарна. **Зөвхөн серверийн `.env`-д** хадгална.

## 2. Oracle Cloud сервер үүсгэх
1. cloud.oracle.com → **Sign up** (Always Free). Home region-оо ойрхон сонгоно (жишээ нь *South Korea Central (Seoul)* эсвэл *Japan East (Tokyo)*) — дараа солигдохгүй.
2. **Compute → Instances → Create instance**
   - Image: **Canonical Ubuntu 24.04**
   - Shape: **Ampere → VM.Standard.A1.Flex**, 2 OCPU, 12 GB (Always Free хязгаар 4 OCPU / 24 GB)
   - SSH key: *Generate a key pair* → private key-г татаж авна (эсвэл өөрийн `~/.ssh/id_ed25519.pub`)
   - «Out of capacity» гарвал өөр *Availability domain* сонгох эсвэл хэдэн цагийн дараа дахин оролдоно.
3. **Networking → Virtual cloud network → Security List → Add Ingress Rules**:
   Source `0.0.0.0/0`, TCP, Destination port **80** ба **443**.
4. Instance-ийн **Public IP**-г тэмдэглэнэ (жишээ нь `140.238.1.2`).

## 3. Сервер бэлдэх
```bash
ssh -i ~/Downloads/ssh-key.key ubuntu@140.238.1.2

# Oracle-ийн Ubuntu image iptables-аар 80/443-г хаадаг — нээнэ
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && exit     # дахин ssh хийнэ
```

## 4. Төсөл татаж тохируулах
```bash
git clone https://github.com/<owner>/energy_balance_demo.git
cd energy_balance_demo
cp deploy/env.prod.example .env
for k in DB_PASSWORD N8N_ENCRYPTION_KEY SESSION_SECRET INTERNAL_TOKEN; do
  sed -i "s|^$k=.*|$k=$(openssl rand -hex 24)|" .env
done
nano .env
```
`.env`-д бөглөх:
- `140-238-1-2` → өөрийн IP (цэгийг зураасаар): `SITE_DOMAIN`, `N8N_DOMAIN`, `N8N_PUBLIC_URL`, `CHAT_ALLOWED_ORIGINS`
- `WEB_IMAGE` → `ghcr.io/<owner>/energy-balance-web:latest` (owner жижиг үсгээр)
- `GEMINI_API_KEY`, `SMTP_USER` / `SMTP_PASSWORD` / `MAIL_FROM` / `STAFF_EMAIL` (Gmail)
- `ADMIN_EMAIL`, `ADMIN_PASSWORD` — хүчтэй нууц үг

> Private repo бол clone хийхэд GitHub username + Personal Access Token (Settings → Developer settings → Fine-grained token, *Contents: Read*) асууна.

## 5. Асаах
```bash
alias dc='docker compose -f docker-compose.yml -f docker-compose.prod.yml'
dc pull web          # ghcr.io-гоос image татна (амжилтгүй бол: dc build web)
dc up -d
dc ps                # бүгд Up / healthy
dc logs n8n-init     # «✓ n8n бэлэн (gemini)»
```
- Нүүр хуудас: `https://eb.<IP>.sslip.io` · Админ: `/admin`
- n8n: `https://n8n.<IP>.sslip.io`

> **Чухал:** асаасан даруйдаа n8n хаягаар орж **owner бүртгэлээ үүсгэнэ**. Эс бөгөөс тэр хаягийг олсон хэн ч эхэлж owner болох боломжтой.

## 6. Шалгах
1. Нүүр хуудсаас захиалга илгээх → өөрийн и-мэйл рүү баталгаажуулах захидал ирэх (эхний удаа *Spam* хавтас шалгана).
2. Чатбот: «Барилгын аудит хэд вэ?»
3. Админ → Контент → Генерэлэх; Эрчим хүчний тооцоо.

## Шинэчлэх, нөөцлөх
```bash
git pull && dc pull web && dc up -d                       # код/workflow шинэчлэх
dc exec db pg_dump -U eb energybalance > backup_$(date +%F).sql   # өгөгдөл нөөцлөх
```

## Аюулгүй байдал
- DB, n8n, Mailpit-ийн порт гаднаас хаалттай; зөвхөн 80/443.
- n8n-ийн `/webhook/*` замуудыг Caddy гаднаас хаадаг — агентуудыг зөвхөн вэб сервер дотоод сүлжээгээр дууддаг.
- Бүх нууц утга зөвхөн серверийн `.env`-д (git-д орохгүй, Docker image-д орохгүй — `.dockerignore`).
- Чатбот API нээлттэй тул Gemini-ийн үнэгүй квот хэтэрвэл AI түр ажиллахгүй болно — демод хангалттай.
