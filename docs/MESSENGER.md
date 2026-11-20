# Facebook Messenger → чат агент

Facebook хуудас руу бичсэн мессежид вэб чаттай **ижил AI агент** (Агент 2) хариулна. Яриа админ «Чат» хэсэгт «Messenger» тэмдэгтэй харагдана.

```
Харилцагч (Messenger) ─► Meta ─► /webhooks/messenger (вэб сервер) ─► n8n чат агент ─► Gemini
                                        └──────── хариу: Graph API /me/messages ◄────────┘
```

Код: `web/app/messenger.py`. Вэб сервер Meta-д шууд 200 буцааж, хариуг ард нь илгээнэ; давтагдсан хүргэлтийг `fb_events` хүснэгтээр шүүнэ.

## Тохируулах (нэг удаа, ~15 минут)

Шаардлагатай: Facebook хуудас (Page) ба түүний админ эрх.

1. [developers.facebook.com/apps](https://developers.facebook.com/apps) → **Create app** → use case: **Engage with customers on Messenger from Meta** (эсвэл «Other» → «Business»).
2. App dashboard → **Messenger → Messenger API Settings**.
3. **Configure webhooks**:
   - Callback URL: `https://web-production-759272bf.up.railway.app/webhooks/messenger`
   - Verify token: `.env.railway` доторх `FB_VERIFY_TOKEN`-ийн утга
   - **Verify and save** → Webhook fields: `messages`, `messaging_postbacks`-ыг сонгоно.
4. **Generate access tokens** → хуудсаа холбоно (**Connect / Add Page**) → **Generate** → Page access token-ийг хуулна. Хуудасны мөрөнд webhook subscription-д `messages` идэвхтэй байгаа эсэхийг шалгана.
5. (Сонголттой, зөвлөмжтэй) **App settings → Basic → App secret**-ийг хуулна.
6. Railway-д тохируулна (вэб автоматаар дахин асна):
   ```bash
   railway variables --service web --set FB_PAGE_TOKEN=EAAG... --set FB_APP_SECRET=...
   ```
7. Хуудас руугаа Messenger-ээр «Барилгын аудит хэд вэ?» гэж бичээд шалгана.

## Анхаарах

- **Development mode:** App Review хийлгээгүй апп зөвхөн тухайн app-ийн админ, developer, tester эрхтэй Facebook хэрэглэгчдэд хариулна. Хамгаалалтын демод хангалттай (өөрийн бүртгэлээр бичнэ). Бусад хүнд хариулуулах бол **App roles → Roles**-д tester болгож нэмнэ; бүх хүнд нээх бол `pages_messaging` эрхээр App Review + Business verification шаардана.
- Page access token нь хуудасны нэрийн өмнөөс мессеж илгээх эрхтэй — зөвхөн Railway variables-д хадгална, git-д оруулахгүй.
- Локалд турших бол Meta нь `localhost`-д хүрч чадахгүй; онлайн (Railway) хаягийг ашиглана.
- Унтраах: `FB_PAGE_TOKEN`-г устгана — webhook мессежийг хүлээн аваад хариулахгүй.
