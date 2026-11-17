# Railway дээр байршуулсан систем

| Үйлчилгээ | Хаяг | Тэмдэглэл |
|---|---|---|
| Нүүр хуудас + чатбот | https://web-production-759272bf.up.railway.app | |
| Админ самбар | https://web-production-759272bf.up.railway.app/admin | нэвтрэх мэдээлэл: `.env.railway` (git-д ордоггүй) |
| n8n editor | https://n8n-production-0a370bb0.up.railway.app | owner бүртгэлээ эхэлж үүсгэнэ |
| И-мэйл хайрцаг (Mailpit) | https://mailpit-production-23ec243f.up.railway.app | нэр `mail`, нууц үг `.env.railway` → `MAILPIT_PASSWORD` |

```
Railway project «energy-balance-ebrd»
  web      (web/Dockerfile)  ─ private ─►  n8n (n8n/Dockerfile) ─► Gemini API
     └──► Postgres ◄────────────────────────┘ └──► mailpit (SMTP 1025, private)
```

- **И-мэйл:** Railway-ийн Free/Trial/Hobby багцад гадагш SMTP (Gmail) хаалттай. Тиймээс бүх и-мэйл Mailpit хайрцагт очно (хичээлийн «Gmail»-ийн орлуулагч). Жинхэнэ и-мэйл хэрэгтэй бол Railway Pro эсвэл HTTPS API-тай үйлчилгээ (Brevo, Resend) руу шилжүүлнэ.
- **Өгөгдлийн сан:** Postgres гаднаас хаалттай. Анх асахад вэб сервер `db/init/*.sql`-ийг автоматаар ачаална.
- **Аюулгүй байдал:** n8n webhook-ууд `X-Internal-Token` header-гүй дуудлагыг 403-аар татгалзана; бүх нууц утга Railway variables болон локал `.env.railway`-д.

## Шинэчлэх
```bash
railway up --service web --ci     # вэб код өөрчлөгдсөн бол
python3 n8n/build_workflows.py && railway up --service n8n --ci   # workflow өөрчлөгдсөн бол
railway logs --service n8n        # лог харах
```
Хувьсагч: `railway variables --service n8n` (жишээ нь `GEMINI_API_KEY` солих → `railway variables --service n8n --set GEMINI_API_KEY=...`).
